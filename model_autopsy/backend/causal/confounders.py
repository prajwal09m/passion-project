"""Confounder identification (M9 Workstream 3.3).

Two hypotheses can both match one observation because a third factor
produces both. This module makes that structure explicit instead of
letting two supports stand unexamined:

1. Shared-evidence analysis: when one ran action supports 2+
   hypotheses whose mechanisms differ, record a common-cause candidate
   naming the shared observation and the competing mechanisms.
2. Artifact-grounded confounder checklist: from recon facts (segments,
   temporal span, schema notes, collection hints in the brief), list
   candidate third factors with what measurement would rule each out.
3. Discriminating-measurement proposals: for each candidate, the tool
   + args + interpretation rule that separates the mechanisms.

Nothing here names projects, segments, or benchmark answers. The
rent schema-vs-district case is the regression test, not a special
case: any shared-supports pattern triggers the same analysis.
"""
from __future__ import annotations


def _primary_family(text: str) -> str:
    from .selection import _family_of
    return _family_of(text or "")


def shared_evidence_candidates(hypotheses: list[dict]) -> list[dict]:
    """Find actions supporting 2+ different-mechanism hypotheses.

    Each hypothesis dict: {id, text, evidence_refs:[{action_id, tool,
    relation}]}. Returns common-cause candidates.
    """
    by_action: dict[str, list[dict]] = {}
    for h in hypotheses:
        for r in (h.get("evidence_refs") or []):
            if r.get("relation") != "supports":
                continue
            by_action.setdefault(r.get("action_id") or "",
                                 []).append(h)
    out = []
    for aid, hs in by_action.items():
        if len(hs) < 2:
            continue
        fams = {_primary_family(h.get("text", "")) for h in hs}
        if len(fams) < 2:
            continue  # same mechanism twice: corroboration, not confounding
        tools = sorted({(r.get("tool") or "")
                        for h in hs for r in (h.get("evidence_refs") or [])
                        if r.get("action_id") == aid})
        out.append({"action_id": aid, "tool": tools[0] if tools else "?",
                    "hypothesis_ids": [h.get("id") for h in hs],
                    "mechanisms": sorted(fams),
                    "note": ("one observation supports two different "
                             "mechanisms; a shared third factor may produce "
                             "both — discriminate before concluding")})
    return out


CONFOUNDER_CHECKLIST = (
    ("composition", "subgroup sizes / prevalence differ across segments",
     "per-segment n and base rates"),
    ("collection", "data collected differently per segment or period",
     "collection metadata or time/segment splits"),
    ("temporal", "effect coincides with a known change or drift",
     "changepoint scan aligned to the change date"),
    ("preprocessing", "a pipeline/schema change touched some rows only",
     "before/after comparison on unaffected rows"),
    ("metric", "the metric hides the failure (pooled vs segmented)",
     "the same metric computed per segment"),
    ("leakage", "a feature carries label information in one segment",
     "feature-target screen per segment"),
)


def checklist(recon_facts: dict) -> list[dict]:
    """Artifact-grounded confounder candidates.

    `recon_facts`: {segments:[...], temporal:bool, schema_note:str,
    brief:str}. Candidates whose preconditions are absent are marked
    inapplicable, never silently dropped.
    """
    segs = recon_facts.get("segments") or []
    temporal = bool(recon_facts.get("temporal"))
    brief = (recon_facts.get("brief") or "").lower()
    schema_hint = bool(recon_facts.get("schema_note")) or any(
        w in brief for w in ("schema", "pipeline", "update", "change"))
    out = []
    for name, what, rules_out in CONFOUNDER_CHECKLIST:
        applicable = True
        if name == "composition" and not segs:
            applicable = False
        if name == "temporal" and not temporal:
            applicable = False
        if name == "preprocessing" and not schema_hint:
            applicable = False
        out.append({"confounder": name, "what": what,
                    "ruled_out_by": rules_out, "applicable": applicable})
    return out


def discriminating_measurements(candidate: dict, available_tools: list[str],
                                artifact: str, segments: list[str],
                                temporal_col: str | None = None,
                                split_col: str | None = None) -> list[dict]:
    """Measurements that separate the candidate's mechanisms.

    Each states what outcome favors which mechanism (interpretation
    rule) — the experiment is worth running only because its outcomes
    discriminate.
    """
    tools = set(available_tools or [])
    out = []
    if "regression_metrics" in tools and segments:
        out.append({
            "tool": "regression_metrics",
            "args": {"predictions_path": artifact,
                     "group_column": segments[0]},
            "distinguishes": ("segment-concentrated error vs uniform error"),
            "interpretation": ("concentrated (ratio >= 1.5): segment "
                               "mechanism favored; uniform (ratio < 1.15): "
                               "global mechanism favored; between: "
                               "inconclusive, do not conclude"),
            "confounder_addressed": "composition/metric masking"})
    if "classification_metrics" in tools and segments:
        out.append({
            "tool": "classification_metrics",
            "args": {"predictions_path": artifact,
                     "score_column": "score", "split_by": segments[0]},
            "distinguishes": ("segment-varying vs uniform ranking quality"),
            "interpretation": ("per-segment spread >= 0.10: segment "
                               "mechanism favored; < 0.03: uniform "
                               "mechanism favored; between: inconclusive"),
            "confounder_addressed": "composition/metric masking"})
    if "temporal_changepoint_scan" in tools and temporal_col:
        out.append({
            "tool": "temporal_changepoint_scan",
            "args": {"predictions_path": artifact,
                     "date_column": temporal_col},
            "distinguishes": ("abrupt change at a known date vs gradual "
                              "drift vs no break"),
            "interpretation": ("break aligned with the suspected change: "
                               "event-driven mechanism favored; no break: "
                               "event mechanism weakened"),
            "confounder_addressed": "temporal/preprocessing"})
    if "distribution_shift_profile" in tools and split_col:
        out.append({
            "tool": "distribution_shift_profile",
            "args": {"predictions_path": artifact,
                     "split_column": split_col},
            "distinguishes": ("covariate/target shift vs stable population"),
            "interpretation": ("material shift: shift mechanism favored; "
                               "negligible: shift weakened"),
            "confounder_addressed": "collection/distribution"})
    if "feature_target_suspiciousness" in tools:
        out.append({
            "tool": "feature_target_suspiciousness",
            "args": {"feature_csv": artifact, "label_csv": artifact},
            "distinguishes": ("label-duplicate input vs clean inputs"),
            "interpretation": ("non-score |r| >= 0.95: leakage favored; "
                               "< 0.5: leakage weakened; between: "
                               "inconclusive"),
            "confounder_addressed": "leakage"})
    return out


def analyze(hypotheses: list[dict], recon_facts: dict,
            available_tools: list[str], artifact: str) -> dict:
    """Full confounder pass; everything recorded, nothing concluded."""
    shared = shared_evidence_candidates(hypotheses)
    checks = checklist(recon_facts)
    segs = recon_facts.get("segments") or []
    disc = discriminating_measurements(
        {}, available_tools, artifact, segs,
        temporal_col=recon_facts.get("temporal_col"),
        split_col=recon_facts.get("split_col"))
    return {"shared_evidence": shared, "checklist": checks,
            "discriminating_measurements": disc,
            "needs_discrimination": bool(shared)}
