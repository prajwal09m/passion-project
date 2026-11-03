"""Evidence-preserving report consistency checks (M20 Phase 4).

Boundary between authoritative science and generated prose: recorded tool
executions, measurements, hypothesis states, verification records, the
resolution contract and budget accounting are authoritative. A model
summary may EXPLAIN them but can never override them.

Pure functions of (summary, authoritative snapshot) plus small snapshot
builders. Read-only: nothing here writes to the session. Offline,
deterministic, no model calls.
"""
from __future__ import annotations

import json
import re

# Statuses the model may recommend (same vocabulary the validator uses).
RECOMMENDABLE = ("proposed", "investigating", "supported",
                 "rejected", "inconclusive", "blocked")

# Authoritative terminal states a repair must not move.
TERMINAL_STATES = ("supported", "rejected")

# Hypotheses that count as still open.
UNRESOLVED_STATES = ("proposed", "investigating", "inconclusive")

_CONFIRM_RE = re.compile(r"confirm", re.IGNORECASE)
_VERIFY_CLAIM_RE = re.compile(
    r"independent(ly)?\s+(verif|confirm|probe|replicat)|"
    r"verif\w*\s+(confirm|success|passed|passed)|"
    r"replicat\w*\s+confirm|second\s+probe\s+confirm",
    re.IGNORECASE)
_DECIMAL_RE = re.compile(r"\d+\.\d+\s*%?")
_COUNT_RE = re.compile(r"(\d+)\s+(tool[\s-]?calls?|experiments?|"
                       r"diagnostics?|actions?|rounds?|hypotheses?)",
                       re.IGNORECASE)


def build_snapshot(session, inv) -> dict:
    """Authoritative facts a report must be consistent with."""
    from ..db import Action, Event, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    hyp_by_id = {}
    contradict_ids: set[str] = set()
    contradict_aids: set[str] = set()
    for h in hyps:
        refs = h.evidence_refs or []
        hyp_by_id[h.id] = {"status": h.status, "text": h.text or "",
                           "refs": refs}
        if any(r.get("relation") == "contradicts" for r in refs
               if isinstance(r, dict)):
            contradict_ids.add(h.id)
        for r in refs:
            if isinstance(r, dict) and r.get("relation") == "contradicts" \
                    and r.get("action_id"):
                contradict_aids.add(str(r["action_id"]))
    corpus_bits: list[str] = []
    action_ids: set[str] = set()
    ran_ids: set[str] = set()
    tools: set[str] = set()
    for a in acts:
        action_ids.add(a.id)
        if a.tool_name:
            tools.add(a.tool_name)
        if a.status == "ran":
            ran_ids.add(a.id)
            try:
                corpus_bits.append(json.dumps(a.result or {}, sort_keys=True,
                                              default=str))
            except Exception:
                corpus_bits.append(str(a.result or ""))
    corpus_bits.extend(h.text or "" for h in hyps)
    verification_confirmed = False
    has_probe_record = False
    resolution_status = None
    for e in session.query(Event).filter(
            Event.investigation_id == inv.id).all():
        p = e.payload or {}
        if e.kind == "verification":
            has_probe_record = True
            if p.get("confirmed"):
                verification_confirmed = True
        elif e.kind == "resolution" and p.get("status"):
            resolution_status = p["status"]
    return {
        "hyp_by_id": hyp_by_id,
        "unresolved_ids": {i for i, h in hyp_by_id.items()
                           if h["status"] in UNRESOLVED_STATES},
        "terminal": {i: h["status"] for i, h in hyp_by_id.items()
                     if h["status"] in TERMINAL_STATES},
        "contradict_ids": contradict_ids,
        "contradict_aids": contradict_aids,
        "action_ids": action_ids,
        "ran_ids": ran_ids,
        "ledger_tools": tools,
        "ran_count": len(ran_ids),
        "corpus": "\n".join(corpus_bits),
        "verification_confirmed": verification_confirmed,
        "has_probe_record": has_probe_record,
        "resolution_status": resolution_status,
        "tool_calls_used": inv.tool_call_count,
        "max_tool_calls": inv.max_tool_calls,
    }


def _mentions(text: str, hyp_id: str) -> bool:
    t = text or ""
    return hyp_id in t or (len(hyp_id) >= 8 and hyp_id[:8] in t)


def check(summary: dict | None, snapshot: dict) -> dict:
    """Validate generated prose against authoritative state.

    Returns {'passed': bool, 'failures': [...], 'warnings': [...]}.
    Every failure names the violated guarantee; warnings flag
    soft discrepancies that do not reject a repair.
    """
    failures: list[str] = []
    warnings: list[str] = []
    if not isinstance(summary, dict):
        return {"passed": False,
                "failures": ["no structured summary to check"],
                "warnings": warnings}
    snap_ids: set[str] = set(snapshot.get("hyp_by_id") or {})
    action_ids: set[str] = set(snapshot.get("action_ids") or {})
    corpus: str = snapshot.get("corpus") or ""
    conclusion = str(summary.get("conclusion") or "")
    recommended_next = str(summary.get("recommended_next") or "")
    uncertainties = summary.get("uncertainties")
    unc_text = "\n".join(u for u in (uncertainties or [])
                         if isinstance(u, str))
    recs = summary.get("status_recommendations") or []
    if not isinstance(recs, list):
        return {"passed": False,
                "failures": ["status_recommendations must be a list"],
                "warnings": warnings}
    rec_ids: set[str] = set()
    for r in recs:
        if not isinstance(r, dict):
            failures.append("each status_recommendation must be an object")
            continue
        hid = str(r.get("hypothesis_id") or "")
        matches = [k for k in snap_ids if k == hid or (hid and k.startswith(hid))]
        if len(matches) != 1:
            failures.append(f"recommendation cites unknown hypothesis {hid!r}")
            continue
        rec_ids.add(matches[0])
        status = r.get("status")
        if status not in RECOMMENDABLE:
            failures.append(f"unsupported recommended status {status!r}")
        elif status == "confirmed":
            failures.append("prose cannot confirm: 'confirmed' is not "
                            "recommendable; confirmation comes only from "
                            "the resolution contract")
        terminal = (snapshot.get("terminal") or {}).get(matches[0])
        if terminal is not None and status != terminal:
            failures.append(
                f"repair moves terminal state of {matches[0][:8]} "
                f"({terminal} -> {status}); recorded conclusions stand")
        for key in ("basis", "basis_action_ids"):
            for aid in (r.get(key) or []):
                if str(aid) not in action_ids:
                    failures.append(
                        f"recommendation cites unknown evidence "
                        f"reference {str(aid)!r}")
                elif str(aid) not in (snapshot.get("ran_ids") or set()):
                    warnings.append(
                        f"basis {str(aid)!r} cites a non-ran action; "
                        f"only ran measurements ground claims")
    for key in ("evidence_action_ids", "evidence_cited"):
        for aid in (summary.get(key) or []):
            if str(aid) not in action_ids:
                failures.append(f"unknown evidence reference {str(aid)!r}")
    if _CONFIRM_RE.search(conclusion) \
            and snapshot.get("resolution_status") != "confirmed":
        failures.append(
            "conclusion claims confirmation but the resolution contract "
            f"is {snapshot.get('resolution_status')!r}; only a 'confirmed' "
            "contract authorizes confirmation language")
    if _VERIFY_CLAIM_RE.search(conclusion + "\n" + recommended_next) \
            and not snapshot.get("verification_confirmed"):
        failures.append("independent verification claimed without a "
                        "confirmed independent-probe record")
    prose_numbers = set(_DECIMAL_RE.findall(conclusion + "\n"
                                            + recommended_next))
    for num in prose_numbers:
        bare = num.rstrip(" %")
        if bare and bare not in corpus and num not in corpus:
            failures.append(f"unsupported numeric claim {num!r}: no recorded "
                            f"measurement contains it")
    for hyp_id in snap_ids:
        if hyp_id not in rec_ids and not _mentions(unc_text + "\n"
                                                   + conclusion, hyp_id):
            failures.append(f"hypothesis {hyp_id[:8]} silently dropped: "
                            f"neither recommended nor carried as uncertainty")
    _cited_aids: set[str] = set()
    for r in recs:
        if isinstance(r, dict):
            for key in ("basis", "basis_action_ids"):
                for aid in (r.get(key) or []):
                    _cited_aids.add(str(aid))
    _contra_mentioned = "contradict" in (
        unc_text + "\n" + conclusion).lower()
    for hyp_id in (snapshot.get("contradict_ids") or set()):
        if hyp_id not in rec_ids and not _contra_mentioned:
            failures.append(
                f"contradictory evidence for {hyp_id[:8]} not preserved")
    for aid in (snapshot.get("contradict_aids") or set()):
        if aid not in _cited_aids and not _contra_mentioned:
            failures.append(
                f"contradictory evidence from {aid[:8]} not preserved: "
                f"the contradicting measurement is cited nowhere")
    if (snapshot.get("unresolved_ids") or set()) and not (
            isinstance(uncertainties, list) and uncertainties):
        failures.append("open hypotheses exist but uncertainties are missing; "
                        "limitations must be preserved")
    for match in _COUNT_RE.finditer(conclusion):
        claimed, kind = int(match.group(1)), match.group(2).lower()
        actual = (snapshot.get("tool_calls_used")
                  if "tool" in kind else snapshot.get("ran_count"))
        if "hypothes" in kind:
            actual = len(snap_ids)
        if actual is not None and claimed != actual:
            failures.append(f"incorrect {kind} figure {claimed} "
                            f"(recorded: {actual})")
    for tool in sorted(snapshot.get("ledger_tools") or set()):
        pass
    for word in set(re.findall(r"[a-z][a-z0-9_]+", conclusion.lower())):
        if word.endswith("_diagnostics") or word.endswith("_probe"):
            if word not in (snapshot.get("ledger_tools") or set()):
                warnings.append(f"conclusion names tool {word!r} with no "
                                f"ledger entry")
    extra = {k for k in summary
             if k not in ("conclusion", "status_recommendations",
                          "uncertainties", "recommended_next", "confidence",
                          "evidence_action_ids", "evidence_cited",
                          "schema_version", "kind", "fallback_version",
                          "model_summary_errors", "provenance")}
    if extra:
        warnings.append(f"unexpected fields ignored by readers: "
                        f"{sorted(extra)}")
    return {"passed": not failures, "failures": failures,
            "warnings": warnings}


def state_fingerprint(session, inv) -> tuple:
    """Hashable read-only fingerprint of SCIENTIFIC state.

    Covers hypothesis statuses/texts/refs, the action ledger, tool-call
    accounting and findings. Deliberately excludes inv.status and
    inv.final_report: finalize()'s defined job is to mark the
    investigation complete and store the assembled report. What the
    assembler must never do is change hypotheses, actions, counts or
    findings - this fingerprint proves exactly that."""
    from ..db import Action, Hypothesis
    hyps = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    acts = session.query(Action).filter(
        Action.investigation_id == inv.id).all()
    return (tuple(sorted(
                (h.id, h.status, h.text,
                 json.dumps(h.evidence_refs or [], sort_keys=True,
                            default=str)) for h in hyps)),
            tuple(sorted((a.id, a.status, a.tool_name) for a in acts)),
            inv.tool_call_count, inv.iteration_count,
            json.dumps(inv.latest_findings or [], sort_keys=True,
                       default=str))


def check_repaired_summary(session, inv, repaired: dict | None) -> dict:
    """Repair-acceptance gate (M20 Phase 3.4): parsing/schema are already
    enforced by validate_structured_summary; this adds the authoritative
    consistency gates. A repaired summary must pass ALL of them."""
    if not isinstance(repaired, dict) or not repaired.get("valid"):
        return {"passed": False,
                "failures": ["repaired summary failed base validation"],
                "warnings": []}
    return check(repaired.get("summary"), build_snapshot(session, inv))
