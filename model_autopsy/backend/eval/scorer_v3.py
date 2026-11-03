"""Eval scorer v3: separated diagnostic dimensions (Stage 2).

v2 (`scorer.py`) is frozen and untouched. v3 measures four distinct
achievements v2 conflates — discovery, evidence, verification,
confirmation — plus efficiency and reproducibility.

Pure function of (report, truth, hypotheses): no DB, no network.
Anything absent from the record yields dimension `None`
("unavailable"), never a silent zero — except an explicitly empty
verification record, which means "no verification recorded".

Every scorecard carries `"rubric_version": "v3"`.
"""
from __future__ import annotations

import re

from . import rubric_v3 as R
from .normalize import canonical_gap
from .scorer import DISTRACTOR_MARKERS, MECHANISMS

_MOVING = ("supports", "contradicts")

_STOP = frozenset(
    "the a an of to in for on with and or is are was were be by as at "
    "it its this that these those from into over under than then than "
    "not no any every across within without which what when where how "
    "does did has have had will would could should may also such via "
    "per top far below under due reflects apparent underperforms "
    "performs receives systematically healthy pooled mean items content "
    "catalog results stays stay relevant stay".split())


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", (text or "").lower())
    out: set[str] = set()
    for w in words:
        for part in re.split(r"[-_]", w):
            if len(part) > 3 and part not in _STOP:
                out.add(part)
    return out


def _family_words(family: str | None) -> list[str]:
    return {"subgroup": ["subgroup", "ward", "region", "slice"],
            "segment": ["segment", "bias", "district"],
            "drift": ["drift", "split", "stale", "shift", "level"],
            "instability": ["unstab", "separat", "silhouette", "balance"],
            "slice": ["slice", "rank", "cold", "position", "p@k"],
            "input_dependence": ["bias", "segment", "mismatch", "stale",
                                 "lag", "input", "device",
                                 "dependence"]}.get(family or "", [])


def _collect_hypotheses(report: dict) -> list[dict]:
    """All hypotheses with status + refs from any report shape.

    v3 lists first; v2 adapter shapes mapped (confirmed_findings ->
    confirmed; rejected_hypotheses -> rejected; inconclusive -> investigating;
    deterministic-fallback evidence_for_each_finding keeps its finding_state).
    """
    seen: dict[str, dict] = {}

    def add(hid, text, status, refs):
        key = (re.sub(r"\s+", " ", (text or "")).strip().lower()
               or f"id:{hid}")
        if key in seen:
            # A ref-less v2 list entry must not shadow a ref-rich record
            # of the same hypothesis (e.g. fallback evidence detail).
            if not seen[key].get("refs") and refs:
                seen[key] = {"id": hid or seen[key]["id"],
                             "text": seen[key]["text"], "status": status,
                             "refs": refs, "duplicate_of": True}
            else:
                seen[key]["duplicate_of"] = True
            return
        seen[key] = {"id": hid, "text": text or "", "status": status,
                     "refs": refs or []}

    for h in report.get("hypotheses", []) or []:
        add(h.get("id") or h.get("hypothesis_id"), h.get("text"),
            h.get("status", "proposed"), h.get("evidence_refs"))
    for c in report.get("confirmed_findings", []) or []:
        add(c.get("hypothesis_id"), c.get("title"), "confirmed",
            c.get("evidence_refs"))
    for c in report.get("likely_findings", []) or []:
        add(c.get("hypothesis_id"), c.get("title"), "likely",
            c.get("evidence_refs"))
    for h in report.get("supported_hypotheses", []) or []:
        add(h.get("hypothesis_id") or h.get("id"), h.get("title",
            h.get("text")), "supported", h.get("evidence_refs"))
    for h in report.get("rejected_hypotheses", []) or []:
        add(h.get("hypothesis_id"), h.get("title") or h.get("text"),
            "rejected", h.get("evidence_refs"))
    for h in report.get("inconclusive", []) or []:
        add(h.get("hypothesis_id"), h.get("title") or h.get("text"),
            h.get("status", "investigating") if isinstance(h, dict)
            else "investigating", h.get("evidence_refs"))
    for h in report.get("unresolved_hypotheses", []) or []:
        add(h.get("hypothesis_id"), h.get("text"), h.get("status",
            "investigating"), h.get("evidence_refs"))
    fb = report.get("deterministic_fallback") or {}
    for h in fb.get("evidence_for_each_finding", []) or []:
        state = {"supported": "supported", "rejected": "rejected"}.get(
            h.get("finding_state"), "investigating")
        add(h.get("hypothesis_id"), h.get("text"), state,
            h.get("evidence_refs"))
    for h in fb.get("supported_but_unconfirmed", []) or []:
        add(h.get("hypothesis_id"), h.get("text"), "supported",
            h.get("evidence_refs"))
    return list(seen.values())


def _discovery(truth_mech: str, family: str | None,
               hyps: list[dict], markers: list[str]) -> tuple[float, str]:
    t = _tokens(truth_mech)
    if not t:
        return 0.0, "no truth keywords; cannot score discovery"
    fam = _family_words(family)
    best, why = 0.0, "mechanism absent from hypothesis set"
    for h in hyps:
        toks = _tokens(h["text"])
        if not toks:
            continue
        overlap = len(toks & t) / len(t)
        named = overlap >= R.MATCH_TOKEN_OVERLAP and any(
            w in h["text"].lower() for w in fam)
        if not named:
            continue
        credit = R.DISCOVERY_CREDIT.get(h["status"], 0.4)
        if credit > best:
            best = credit
            why = (f"matched {h['status']} hypothesis "
                   f"(overlap {overlap:.2f}): {(h['text'] or '')[:100]}")
    for h in hyps:
        if h["status"] in ("confirmed", "likely") and any(
                m in (h["text"] or "").lower() for m in markers):
            best = max(0.0, best - R.FALSE_POSITIVE_PENALTY)
            why += "; confirmed distractor penalized"
    return round(best, 3), why


def _numbers(report: dict) -> list[dict]:
    return [e.get("numbers", {}) for e in report.get("experiments", [])]


def _v3_numbers_ok(family: str | None, report: dict) -> tuple[bool, str]:
    """Practical + statistical significance gate (rubric v3 §calibration)."""
    if family == "slice":
        gate = R.NUMERIC_GATES["slice"]
        gaps = [canonical_gap(n) for n in _numbers(report)]
        gaps = [g for g in gaps if g is not None]
        if not gaps:
            return False, "no gap measurement present (absent != 0)"
        best = max(gaps)
        if best < gate["min_gap"]:
            return False, f"max slice gap={best} below v3 band 0.15"
        pvals = [n.get("p_value") for n in _numbers(report)
                 if isinstance(n.get("p_value"), (int, float))]
        if pvals and min(pvals) >= R.SIGNIFICANCE_ALPHA:
            return False, f"gap present but not significant (p={min(pvals)})"
        sig = f" + p={min(pvals)}" if pvals else " (no significance test)"
        return True, f"max slice gap={best}{sig}"
    # Other families: inherit v2 bands (self-contained comparison).
    return _generic_numbers_ok(family, report)


def _generic_numbers_ok(family: str | None,
                       report: dict) -> tuple[bool, str]:
    nums = _numbers(report)
    rel = [n for n in nums if n] or []
    if family == "subgroup":
        gaps = [n.get("group_gap", 0) for n in nums]
        ok = any(g >= R.NUMERIC_GATES["subgroup"]["min_gap"] for g in gaps)
        return ok, f"max group_gap={max(gaps) if gaps else None}"
    return bool(rel), "generic numbers present"


def _evidence(report: dict) -> tuple[float, str]:
    exps = [e for e in report.get("experiments", [])
            if e.get("tool") != "propose_hypothesis"]
    ran = [e for e in exps if e.get("experiment_id")]
    refs = [r for h in _collect_hypotheses(report) for r in (h["refs"] or [])
            if isinstance(r, dict) and r.get("relation") in _MOVING]
    if not ran:
        return 0.0, "no diagnostic experiments on record"
    if not refs:
        return 0.0, "diagnostics ran but no moving evidence refs"
    linked = {str(e.get("experiment_id")) for e in ran} & \
        {str(r.get("action_id")) for r in refs if r.get("action_id")}
    # Repeats (identical numeric digests) noted, not double-counted.
    digests = [repr(sorted((e.get("numbers") or {}).items())) for e in ran]
    notes = ("; repeat measurements present (not double-counted)"
             if len(set(digests)) < len(digests) else "")
    a = 0.4
    rels = {r.get("relation") for r in refs}
    b = 0.3 if {"supports", "contradicts"} <= rels else 0.0
    c = round(0.3 * len(linked) / len(ran), 3)
    disc = ("both support+contradict present" if b else
            f"only {sorted(rels)} relations")
    return round(a + b + c, 3), (
        f"{len(linked)}/{len(ran)} ran diagnostics linked; {disc}{notes}")


def _verification(report: dict) -> tuple[float, str]:
    entries = report.get("verification", []) or []
    if not entries:
        return 0.0, "no verification recorded"
    executed = [e for e in entries
                if isinstance(e, dict) and e.get("action_id")
                and (e.get("result") is not None or e.get("outcome"))]
    errored = [e for e in entries
               if isinstance(e, dict) and not e.get("action_id")
               and ("error" in e or "failed" in str(e.get("status", "")))]
    planned = [e for e in entries if isinstance(e, dict)
               and not e.get("action_id")]
    if executed:
        return 1.0, f"{len(executed)} probe(s) executed, linked, recorded"
    if errored and not planned:
        return 0.4, "probe executed but errored; no result recorded"
    if planned:
        return 0.2, (f"probe planned but unexecuted "
                     f"({len(planned)} plan(s) on record)")
    return 0.0, "verification entries carry no executable record"


def _confirmation(report: dict, discovery: float,
                  numbers_ok: bool) -> tuple[float, str]:
    confirmed = report.get("confirmed_findings", []) or []
    hyps = _collect_hypotheses(report)
    contradicted = any(
        r.get("relation") == "contradicts" for h in hyps
        for r in (h["refs"] or []) if isinstance(r, dict))
    if confirmed:
        if contradicted or not numbers_ok:
            return 0.0, ("confirmation despite contradicting evidence or "
                         "failing numbers gate: unsupported")
        return 1.0, "confirmed with supporting numbers, no contradiction"
    # No confirmation: honest partial/inconclusive vs empty stall.
    open_h = report.get("inconclusive", []) or report.get(
        "unresolved_hypotheses", []) or []
    fb = report.get("deterministic_fallback") or {}
    open_h = open_h or fb.get("unresolved_hypotheses", []) or []
    honest = bool(open_h) or any(
        "unresolv" in (lim or "").lower() or "no " in (lim or "").lower()
        for lim in report.get("limitations", []) or [])
    if discovery > 0 and honest:
        return 0.7, ("no confirmation, but discovery on record and "
                     "uncertainty stated honestly")
    if honest:
        return 0.4, "honest inconclusive Stall with no discovery"
    return 0.4, "no confirmation and no stated uncertainty basis"


def score_v3(pid: str, report: dict, truth: dict,
             hypotheses: list[dict] | None = None) -> dict:
    """Score one eval report under rubric v3. See module docstring."""
    dims: dict[str, float | None] = {}
    notes: dict[str, str] = {}
    unavailable: list[str] = []
    t = (truth or {}).get(pid)
    if not t:
        return {"project": pid, "rubric_version": R.RUBRIC_VERSION,
                "verdict": "unscored", "overall": None,
                "dimensions": {}, "weights": dict(R.WEIGHTS),
                "notes": {"truth": "no ground truth for project"},
                "unavailable": ["all"], "assessment": "insufficient data"}
    fam = MECHANISMS.get(pid, {}).get("family")
    hyps = hypotheses if hypotheses is not None else _collect_hypotheses(
        report)
    markers = DISTRACTOR_MARKERS.get(pid, [])
    if t.get("failure"):
        d, dn = _discovery(t.get("mechanism", ""), fam, hyps, markers)
        dims["discovery"], notes["discovery"] = d, dn
        nok, nokn = _v3_numbers_ok(fam, report)
        notes["numbers_gate"] = nokn
    else:
        confirmed = report.get("confirmed_findings", []) or []
        if not confirmed:
            dims["discovery"], notes["discovery"] = 1.0, \
                "correct null: no material issue established"
        else:
            dims["discovery"], notes["discovery"] = 0.0, \
                "false positive on a no-failure project"
        nok = True
    e, en = _evidence(report)
    dims["evidence"], notes["evidence"] = e, en
    v, vn = _verification(report)
    dims["verification"], notes["verification"] = v, vn
    c, cn = _confirmation(report, dims["discovery"] or 0.0,
                          nok if t.get("failure") else True)
    dims["confirmation"], notes["confirmation"] = c, cn
    # Efficiency: count-based base (v2 concept) discounted by duplicate
    # work (identical result digests among ran diagnostics waste budget).
    # Deterministic and recorded-data-only; does not reward fewer calls
    # per se (a single linked experiment still needs evidence credit
    # elsewhere) nor punish exploration that produces distinct numbers.
    n_exp = len(report.get("experiments", []))
    base = 1.0 if n_exp <= 4 else max(0.0, 1.0 - 0.2 * (n_exp - 4))
    diag = [e for e in report.get("experiments", [])
            if e.get("tool") != "propose_hypothesis"]
    digests = [repr(sorted((e.get("numbers", {}) or {}).items()))
               for e in diag]
    dup_frac = (1.0 - len(set(digests)) / len(digests)) if digests else 0.0
    dims["efficiency"] = round(base * (1.0 - 0.5 * dup_frac), 3)
    notes["efficiency"] = (f"{n_exp} experiments on record; "
                             f"duplicate-result fraction {dup_frac:.2f}")
    spent = None
    for key in ("token_financial_usage", "budget", "usage"):
        blk = report.get(key) or {}
        if isinstance(blk, dict):
            for k in ("spent", "cost_usd", "total_cost"):
                if isinstance(blk.get(k), (int, float)):
                    spent = blk[k]
    notes["cost"] = (f"actual recorded spend {spent}" if spent is not None
                     else "usage data missing: cost unknown, not assumed 0")
    rep = report.get("executive_summary") and all(
        bool(e.get("experiment_id")) for e in
        report.get("experiments", []))
    dims["reproducibility"] = 1.0 if rep else 0.0
    notes["reproducibility"] = ("summary + experiment ids preserved"
                                if rep else "record incomplete")
    avail = {k: v for k, v in dims.items() if v is not None}
    missing_core = [k for k in ("discovery", "evidence", "verification",
                                "confirmation") if dims.get(k) is None]
    if len(missing_core) > 1:
        overall = None
        verdict = "insufficient_data"
    else:
        wsum = sum(R.WEIGHTS[k] for k in avail)
        overall = round(sum(avail[k] * R.WEIGHTS[k] for k in avail) / wsum, 3)
        verdict = ("confirmed" if dims.get("confirmation") == 1.0
                   else "honest_partial" if (dims.get("confirmation") or 0)
                   >= 0.7 else "unresolved")
    return {"project": pid, "rubric_version": R.RUBRIC_VERSION,
            "verdict": verdict, "overall": overall,
            "dimensions": dims, "weights": dict(R.WEIGHTS),
            "notes": notes, "unavailable": unavailable,
            "formula": R.AGGREGATE_FORMULA,
            "assessment": "deterministic; LLM/human reserved"}
