"""Tool-calling investigation loop for Meta (Muse Spark).

Bounded orchestration that drives one investigation segment:
  1. Build honest investigation context (engine-recorded evidence only).
  2. Ask Meta to act, with the mode's tool schemas.
  3. Validate every requested tool call against the allowlist.
  4. Execute approved tools with real inputs; record evidence.
  5. Return results to Meta with `function_call_output` items.
  6. Repeat while Meta keeps calling tools and budgets remain.
  7. Record Meta's final message verbatim as the interpretation.

Meta is never a source of truth by confidence alone — every hypothesis,
finding and metric must trace to a recorded action or be absent.
"""
from __future__ import annotations

import hashlib
import json
import re

from sqlalchemy.orm import Session

from .. import config, engine, tools_registry
from ..db import Action, Hypothesis, Investigation, record_event, to_json_blob
from . import client as meta_client

# M20 Phase 2: compact reporting contract. Replaces the one-clause format
# hint with a schema table (required vs optional), the status vocabulary,
# representation rules per finding state, and explicit prohibitions. Kept
# short on purpose: one block, one tiny example, no new round trips.
_SUMMARY_CONTRACT = (
    "Final message: describe the investigation, then end with a fenced block "
    "```investigation_summary\\n{...}\\n``` holding ONE compact JSON object. "
    "REQUIRED: \"conclusion\" (non-empty string, your verdict in plain words). "
    "OPTIONAL but expected: \"status_recommendations\" (list of "
    "{\"hypothesis_id\": an id from the backend roster, \"status\": one of "
    "proposed/investigating/supported/rejected/inconclusive/blocked, "
    "\"basis\": recorded action ids that support the recommendation}), "
    "\"uncertainties\" (list of strings; may be empty only if nothing is "
    "open), \"recommended_next\" (string; may be empty), \"confidence\" "
    "(0-99, never 100). Represent states honestly: confirmed findings need a "
    "resolution-backed status AND cited action ids; supported-but-unconfirmed "
    "stays \"supported\"; contradicted evidence stays listed, never dropped; "
    "open questions stay \"proposed\"/\"investigating\"/\"inconclusive\" "
    "with the missing measurement named. Observations (measured numbers with "
    "action ids) stay separate from interpretations (what you infer). A metric "
    "alone proves neither validity nor cause; association is not causation. "
    "PROHIBITED: inventing evidence, tool executions, action ids, numbers, or "
    "independent verification; changing any hypothesis status yourself (you only "
    "recommend); upgrading supported to confirmed; hiding contradictory "
    "evidence or unresolved questions; treating interpretation as measurement. "
    "You describe the recorded investigation; you do not run a new one. "
    "Example: {\"conclusion\": \"Slice diagnostics show a 0.17 precision "
    "gap (act_1); mechanism unconfirmed.\", \"status_recommendations\": "
    "[{\"hypothesis_id\": \"<id from roster>\", \"status\": "
    "\"investigating\", \"basis\": [\"<action id>\"]}], "
    "\"uncertainties\": [\"cause of the gap is unmeasured\"], "
    "\"recommended_next\": \"collect slice-level labels\"}")


MODE_INSTRUCTIONS = {
    "software": (
        "You are the runtime investigator of Model Autopsy, a software autopsy. "
        "Review the supplied git change set against the stated objective. Use the "
        "provided tools to inspect files or run the automated test suite (read-only "
        "operations; you cannot choose the command). Report concrete defects with "
        "file/line references, and register them using the propose_hypothesis tool "
        "(one call per hypothesis, with a falsifiable statement and predicted "
        "observation). When a fix is warranted, record a propose_revision_instructions "
        "bundle for a HUMAN reviewer — applying changes is never automatic. Be "
        "explicit when evidence is missing. Never claim a test passed unless you "
        "requested the test tool and saw its recorded result."),
    "ml": (
        "You investigate an ML model failure. Facts come only from recorded "
        "context and tool results — cite their action ids; never invent "
        "datasets, metrics, runs, evidence ids, or numbers you cannot derive; "
        "your prose is never evidence. Mark claims fact / hypothesis / "
        "conclusion. Questions blocked by missing data or historical artifacts "
        "are UNRESOLVED; keep such historical narratives separate from this "
        "artifact's evidence.\n"
        "Method:\n"
        "1. propose_hypothesis x2-3: genuinely competing explanations — distinct "
        "mechanism, why plausible now, what observation would contradict it, "
        "uncalibrated confidence. No rewordings of one explanation; don't assume "
        "the requester's theory is right.\n"
        "2. One diagnostic at a time: the tool that best DISCRIMINATES the live "
        "hypotheses. Skip what an already-recorded result answers (duplicate "
        "requests return the prior result, not new data).\n"
        "3. After each result: compare it with the hypothesis's predicted "
        "observation; state whether it supports, contradicts, or leaves it "
        "open; on contradiction, demote that hypothesis — no narrative rescue. "
        "A high or low metric alone proves neither validity nor cause.\n"
        "4. Statuses (proposed/investigating/supported/rejected/"
        "inconclusive/blocked): the backend updates them server-side after "
        "every diagnostic — re-check the roster each turn. Recommend final "
        "changes only in the summary; basis = recorded action ids; you "
        "cannot set them yourself.\n"
        "5. Follow the selection_brief order: run the top diagnostic first "
        "unless recorded evidence answers it; if you deviate, say why in "
        "one sentence. Never re-run a ledger tool.\n"
        + " " + _SUMMARY_CONTRACT + " Only reference hypothesis ids the "
        "backend reported. Stop requesting tools when evidence suffices, "
        "budget is low, or no diagnostic could change the conclusion."),
}


def _compact_findings(inv: Investigation) -> list[dict]:
    """Deduplicated, compacted evidence list (no duplicated copies)."""
    seen: set[tuple] = set()
    out: list[dict] = []
    for f in (inv.latest_findings or []):
        key = (f.get("summary"), f.get("status"))
        if key in seen:
            continue
        seen.add(key)
        out.append({"status": f.get("status"),
                    "summary": str(f.get("summary"))[:220],
                    "evidence_action_id": f.get("evidence_action_id")})
    return out


def _experiments_ledger(session: Session, inv: Investigation,
                        limit: int = 10) -> list[dict]:
    """Compact record of what already ran, so the model cannot re-ask."""
    actions = (session.query(Action)
               .filter(Action.investigation_id == inv.id)
               .order_by(Action.seq.asc()).all())[-limit:]
    out: list[dict] = []
    for a in actions:
        entry = {"action_id": a.id, "tool": a.tool_name, "status": a.status}
        args = to_json_blob(a.arguments or {}) or {}
        canonical = json.dumps(args, sort_keys=True, default=str)
        if len(canonical) > 2:
            entry["args"] = canonical[:140]
        if a.status == "ran":
            entry["result_digest"] = json.dumps(
                {k: v for k, v in (to_json_blob(a.result or {}) or {}).items()
                 if k != "_dedup"}, sort_keys=True, default=str)[:200]
        elif a.error:
            entry["error_digest"] = a.error[:160]
        out.append(entry)
    return out


def _hypotheses_roster(session: Session, inv: Investigation) -> list[dict]:
    """Hypothesis ids the model may reference in its structured summary."""
    hyps = (session.query(Hypothesis)
            .filter(Hypothesis.investigation_id == inv.id)
            .order_by(Hypothesis.id.asc()).all())
    return [{"id": h.id, "status": h.status,
             "text": h.text[:120]} for h in hyps]


def _compact_context(inv: Investigation) -> dict:
    context = dict(to_json_blob((inv.config or {}).get("context") or {}) or {})
    # Bulk lists (full column names etc.) are already visible through the
    # artifact tools; sending them again bloats every prompt.
    for key in ("columns", "not_a_model_column", "folds_present"):
        if key in context and isinstance(context[key], list):
            context[key] = {"count": len(context[key])}
    return context


def _initial_context_items(session: Session, inv: Investigation) -> list[dict]:
    items = [
        {"role": "user", "content": json.dumps({
            "mode": inv.mode, "objective": inv.question,
            "recorded_context": _compact_context(inv),
            "hypotheses": _hypotheses_roster(session, inv),
            "findings": _compact_findings(inv),
            "experiments_ledger": _experiments_ledger(session, inv),
            "budget": {"iterations_used": inv.iteration_count,
                       "max_iterations": inv.max_iterations,
                       "tool_calls_used": inv.tool_call_count,
                       "max_tool_calls": inv.max_tool_calls}}, sort_keys=True)}]
    return items


def _continuation_delta_items(session: Session, inv: Investigation) -> list[dict]:
    """Fresh state delta for a CHAINED continuation turn (verified Meta docs:
    "the server appends your new input to stored history, so you send only
    what changed"; usage "reports only the new turn's input_tokens").

    The turn-invariant content (mode, objective, recorded corpus context) is
    already in the provider's stored chain, so resending it would re-bill
    tokens for information the provider retains without any benefit. What can
    change between turns — roster, findings, ledger, budget — is sent fresh
    and completely, so every decision remains evidence-backed with intact
    action-id traceability. No valid chain => use `_initial_context_items`."""
    items = [{"role": "user", "content": json.dumps({
        "mode": inv.mode, "objective": inv.question,
        "context_source": (
            "retained server-side conversation history; the full recorded "
            "context was supplied in an earlier chained turn. This message is "
            "the current state delta only."),
        "hypotheses": _hypotheses_roster(session, inv),
        "findings": _compact_findings(inv),
        "experiments_ledger": _experiments_ledger(session, inv),
        "budget": {"iterations_used": inv.iteration_count,
                   "max_iterations": inv.max_iterations,
                   "tool_calls_used": inv.tool_call_count,
                   "max_tool_calls": inv.max_tool_calls}}, sort_keys=True)}]
    return items


def _wrapup_item(round_no: int, max_rounds: int, inv: Investigation) -> dict | None:
    """Folded into the EXISTING function_call_output round — not a new call.
    Sent when tool budget is nearly gone or this was the last loop round."""
    nearly_out = (inv.max_tool_calls - inv.tool_call_count) <= 2
    if not (nearly_out or round_no >= max_rounds):
        return None
    return {"role": "user", "content": (
        "Budget/rounds are nearly exhausted. Do not request further experiments "
        "unless one could still change the conclusion. Finish now: interpret the "
        "recorded results honestly. " + _SUMMARY_CONTRACT)}


_TOOL_OUTPUT_LIMIT = 2000
_TOOL_OUTPUT_PREFIX = 400


def _notice_for_omitted(value: str) -> dict:
    """F8: structured truncation notice for one oversized string field."""
    return {"truncated": True,
            "omitted_chars": max(len(value), 0) - _TOOL_OUTPUT_PREFIX,
            "sha256": hashlib.sha256(
                value.encode("utf-8", "replace")).hexdigest(),
            "prefix": value[:_TOOL_OUTPUT_PREFIX]}


def _truncate_tool_payload(packet: dict,
                           max_chars: int = _TOOL_OUTPUT_LIMIT) -> dict:
    """F8: keep tool-result packets small WITHOUT emitting invalid JSON.

    Arbitrary character truncation can cut a serialized object mid-token and
    hand the model broken JSON. Compaction here replaces oversized string
    fields with a structured notice (explicit `truncated`, omitted character
    count, sha256 digest of the omitted content, and a kept prefix), so the
    model sees a self-describing boundary it can act on rather than malformed
    text. Only applied once the packet would exceed the limit; small results
    pass through untouched."""
    if not isinstance(packet, dict):
        return {"error": "non-dict tool payload"}

    def _size(p: dict) -> int:
        return len(json.dumps(p, sort_keys=True, default=str))

    if _size(packet) <= max_chars:
        return packet
    for key in ("result", "error"):
        value = packet.get(key)
        if isinstance(value, str):
            packet[key] = _notice_for_omitted(value)
    if _size(packet) <= max_chars:
        return packet
    for key in ("result", "error"):  # oversized structured results too
        value = packet.get(key)
        if isinstance(value, (dict, list)):
            packet[key] = _notice_for_omitted(
                json.dumps(value, sort_keys=True, default=str))
    return packet


_SUMMARY_REPAIR_TOKENS = 1200


def _usable_response_id(value) -> str | None:
    """A non-empty string id is a usable continuation handle; anything else
    (missing, null, non-string, blank) is NOT — never pass it back to the
    provider as `previous_response_id`."""
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            return candidate
    return None


def _dispatch_est_input(items) -> int:
    """M17 headroom: honest input-size estimate (chars/4) for one dispatch."""
    try:
        return max(1, len(json.dumps(items, sort_keys=True,
                                     default=str)) // 4)
    except Exception:
        return 4000


def _classify_turn_progress(*, new_hypotheses: int, executed_any: bool,
                            ran_new: int, verify_ready: bool) -> str:
    """M22 P1: turn progress in four evidence-based states.

    no-activity: nothing proposed, nothing executed.
    activity-without-evidence: calls made but no new ran measurement
      (failures, dedup reuses, hypothesis ops only).
    diagnostic-progress: at least one newly ran diagnostic measurement.
    sufficient-evidence: a hypothesis is verification-eligible (>=1
      moving support, zero contradicts) — the state that can support a
      conclusion. A tool call alone never qualifies.
    """
    if verify_ready:
        return "sufficient-evidence"
    if ran_new > 0:
        return "diagnostic-progress"
    if executed_any or new_hypotheses > 0:
        return "activity-without-evidence"
    return "no-activity"


def _attempt_summary_repair(session: Session, inv: Investigation,
                            invalid_summary: dict,
                            previous_response_id: str | None = None,
                            budget=None) -> tuple[dict, str, dict]:
    """F4/M8: exactly ONE bounded repair request for an invalid summary.

    M8 redesign: the repair is a FRESH full-context request (no
    previous_response_id chain). Chaining from the turn's last response
    fails whenever that response's tool calls were never answered — the
    exact shape in which every M7 repair died with HTTP 400. The repair
    carries compact recorded state (roster, ledger, budget) so it needs
    no provider memory. Guarded by the shared budget; MetaUnavailable
    propagates to the caller (which records it and composes the
    deterministic fallback). No tools are offered.

    Returns (summary, text, perf) where perf carries attempt/latency/usage
    facts for the usage rollup, plus the repair response's own id."""
    allowed_ids = [h["id"] for h in _hypotheses_roster(session, inv)]
    rules = [
        "re-emit ONLY the fenced ```investigation_summary block as valid "
        "compact JSON — no prose around it",
        "conclusion must be a non-empty string",
        "status values must be one of: "
        + ", ".join(engine.HYPOTHESIS_RECOMMENDABLE_STATUSES),
        "every status_recommendations.hypothesis_id must be an id from "
        "allowed_hypothesis_ids (the key may be an empty list when none apply)",
        "status_recommendations.basis must cite recorded action ids you "
        "already received",
        "uncertainties is a list of strings; recommended_next is a string",
        "explain ONLY grounded_facts: do not invent hypothesis ids, "
        "statuses, action ids, or measured numbers",
    ]
    # M20 Phase 3.2: the repair transforms existing material into a valid
    # block — it must not reinterpret the investigation or discover new
    # findings. Authoritative facts (statuses, ledger, budget) are
    # supplied; prohibitions + a minimal example keep the single attempt
    # well-formed without extra round trips.
    prohibitions = [
        "do not invent evidence, tool executions, action ids, measured "
        "numbers, or independent verification",
        "do not change any hypothesis status yourself; recommend only, "
        "using the recorded statuses below as the starting point",
        "do not upgrade supported findings to confirmed and do not hide "
        "contradictory evidence or unresolved questions",
        "do not claim causality when only association was measured; keep "
        "observations (with action ids) separate from interpretations",
    ]
    state = {"hypotheses": _hypotheses_roster(session, inv),
               "grounded_facts": engine.grounded_summary(session, inv),
               "experiments_ledger": _experiments_ledger(session, inv),
               "budget": {"tool_calls_used": inv.tool_call_count,
                          "max_tool_calls": inv.max_tool_calls}}
    prompt = json.dumps({
        "error": (invalid_summary.get("errors") or [])[:8],
        "problem": ("the ```investigation_summary block in your final message "
                    "was rejected by the backend validator; transform that "
                    "material into one corrected block now — restate, do not "
                    "reinterpret; no new findings, no new tool claims"),
        "original_output_class": invalid_summary.get("output_class"),
        "allowed_hypothesis_ids": allowed_ids,
        "rules": rules,
        "prohibitions": prohibitions,
        "summary_schema": {"conclusion": "str (required)",
                           "status_recommendations":
                           "[{hypothesis_id, status, basis}] (optional)",
                           "uncertainties": "[str] (expected)",
                           "recommended_next": "str (may be empty)",
                           "confidence": "0-99 or omitted (never 100)"},
        "example": {"conclusion": "Slice diagnostics show a 0.17 "
                     "precision gap (act_1); mechanism unconfirmed.",
                     "status_recommendations": [
                         {"hypothesis_id": "<id from allowed list>",
                          "status": "investigating",
                          "basis": ["<recorded action id>"]}],
                     "uncertainties": ["cause of the gap is unmeasured"],
                     "recommended_next": "collect slice-level labels"},
        "recorded_state": state,
    }, sort_keys=True)
    # M17 headroom before the repair dispatch (refusal propagates to the
    # caller, which records "refused by budget"; nothing is settled
    # because nothing was sent).
    if budget is not None:
        budget.check_dispatch(_dispatch_est_input(
            [{"role": "user", "content": "repair"}]))
    _tok = budget.reserve("attempts", 1, note="summary-repair") \
        if budget is not None else None
    try:
        response = meta_client.create_response(
            model=config.meta_model_id(),
            input_items=[{"role": "user", "content": prompt}],
            tools=[], previous_response_id=None,
            instructions=MODE_INSTRUCTIONS[inv.mode],
            max_output_tokens=_SUMMARY_REPAIR_TOKENS)
    except Exception:
        if _tok is not None:
            budget.settle(_tok, 1)  # conservative: it went out
        raise
    if _tok is not None:
        perf_raw0 = response.get("_request_perf") or {}
        budget.settle(_tok, int(perf_raw0.get("attempts") or 1))
    perf_raw = response.get("_request_perf") or {}
    text = meta_client.extract_message_text(response)
    usage = meta_client.usage(response)
    summary = engine.validate_structured_summary(session, inv, text)
    return (summary, text,
            {"attempts": int(perf_raw.get("attempts") or 1),
             "latency_s": float(perf_raw.get("latency_s") or 0.0),
             "usage": usage,
             "response_id": _usable_response_id(
                 meta_client.response_id(response))})


def maybe_reserve_end_of_turn(session: Session, inv: Investigation,
                                budget, experiments_left=None):
    """M17 Phase 1: once-per-investigation reservation, end of turn.

    Called after the round loop when round-1 hypotheses are on record.
    The `reservation`-event guard enforces exactly-once across turns;
    the shared Budget gates dispatch inside `run_reserved`. Returns the
    reservation record, or None when already decided in a prior turn.
    """
    from ..db import Event as _Event
    _already = session.query(_Event).filter(
        _Event.investigation_id == inv.id,
        _Event.kind == "reservation").count()
    if _already:
        return None
    from ..research import invention as _INV
    from ..live import reserve as _reserve
    _facts = _INV.artifact_facts(
        (inv.config or {}).get("predictions_path") or "")
    return _reserve.run_reserved(
        session, inv, _facts, budget, experiments_left)


def run_meta_turn(session: Session, inv: Investigation,
                  max_rounds: int = 3,
                  previous_response_id: str | None = None,
                  experiments_left: int | None = None,
                  budget=None) -> dict:
    """One bounded Meta turn: tool calls loop up to `max_rounds` rounds.

    M8 safety: every provider request reserves 1 attempt and every tool
    execution reserves 1 experiment on the shared budget BEFORE dispatch
    (settled with actuals after). When no budget is passed, an ephemeral
    standard-capped one bounds the turn, so no caller can spend unbounded.
    """
    from ..live import governor as _governor
    if budget is None:
        budget = _governor.Budget()
    _exceeded = _governor.BudgetExceeded
    if inv.tool_call_count >= inv.max_tool_calls:
        return {"status": "tool_budget_exhausted", "message_text": "",
                "tool_calls": []}
    tools = tools_registry.meta_tool_schemas(inv.mode)
    context_mode = "delta" if previous_response_id else "full"
    input_items = (_continuation_delta_items(session, inv)
                   if previous_response_id
                   else _initial_context_items(session, inv))
    # M7 closed loop: selection brief from recorded state (compact top-3),
    # recorded as an event so adherence can be audited post-turn.
    from ..causal import planning as _planning
    _hviews = [{"id": h.id, "text": h.text, "status": h.status,
                 "evidence_refs": h.evidence_refs or []}
                for h in session.query(Hypothesis).filter(
                    Hypothesis.investigation_id == inv.id).all()]
    _ran_names = {a.tool_name for a in session.query(Action).filter(
        Action.investigation_id == inv.id, Action.status == "ran").all()
        if a.tool_name}
    _failed_names = {a.tool_name for a in session.query(Action).filter(
        Action.investigation_id == inv.id, Action.status == "failed").all()
        if a.tool_name}
    _brief = _planning.plan_next(
        _hviews, _ran_names,
        {"tool_calls_used": inv.tool_call_count,
         "tool_calls_max": inv.max_tool_calls},
        already_failed=_failed_names)
    _top_names = [r["tool"] for r in _brief["recommended"]]
    input_items = list(input_items) + [{
        "role": "user", "content": json.dumps({
            "selection_brief": {
                "recommended": _brief["recommended"],
                "open_hypotheses": _brief["open"],
                "untested": _brief["untested"],
                "instruction": (
                    "Run the top recommended diagnostic first unless "
                    "recorded evidence already answers it; if you deviate, "
                    "state why in one sentence. "
                    "Choose the diagnostic that best DISCRIMINATES the live "
                    "hypotheses (highest expected value), measures the "
                    "actual claim (metric and granularity must match), uses "
                    "a tool independent of already-ran measurements, and "
                    "fits the remaining budget. "
                    "After proposing hypotheses, always decide explicitly: "
                    "run a diagnostic, or record why none is justified "
                    "(no suitable measurement / evidence sufficient / "
                    "redundant / budget insufficient). "
                    "A turn with new hypotheses, no diagnostic, and no "
                    "reason is incomplete.")}}, sort_keys=True)}]
    record_event(session, inv.id, "selection",
                 f"Selection brief: top={(_top_names[:1] or ['none'])[0]}",
                 payload={"recommended": _top_names,
                          "open": [h["id"] for h in _brief["open"]]})
    session.commit()
    last_id = previous_response_id
    fallback_used = False
    _nudge_sent = False
    _zero_recovery_sent = False  # M22 P0: one zero-action recovery/turn
    _ran_new_turn = 0  # M22 P1: newly ran diagnostic measurements
    _hyps_before = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).count()
    round_no = 0
    api_calls = 0
    api_attempts = 0
    latency_total = 0.0
    repairs = 0
    fallback: dict | None = None
    # Explicit continuation-state audit: which response the NEXT turn may chain
    # from. "original" = no repair (or a repair that did not win); "repair" =
    # the repaired response; "unavailable" = repair won but returned no usable
    # id, so no continuation state exists.
    repair_state = {"attempted": False, "valid": None,
                    "response_id_source": "original"}
    executed: list[dict] = []
    reused_count = 0
    text_out = ""
    usage: dict | None = None
    token_totals: dict[str, int] = {}

    # M19 Phase 1: request validation + single-fallback recovery.
    from . import requests as _RQ

    class _FallbackFailed(RuntimeError):
        """Reconstruction or re-send failed; caller stops honestly."""

    def _recovery_items() -> list[dict]:
        """Full-context rebuild preserving recorded tool state, no chain.

        Executed tool calls are summarized from the durable record (never
        re-sent as chain-referencing outputs, which a chainless request
        cannot anchor). Re-requests hit engine dedup and reuse."""
        items = _initial_context_items(session, inv)
        if executed:
            lines = []
            for e in executed:
                out = e.get("outcome") or {}
                lines.append({
                    "call": e.get("name"),
                    "ok": bool(out.get("ok")),
                    "reused": bool(out.get("reused")),
                    "action_id": out.get("action_id"),
                    "note": ("already recorded; do not re-request — "
                             "re-requests return the recorded result")})
            items = list(items) + [{
                "role": "user", "content": json.dumps({
                    "already_executed_this_turn": lines,
                    "instruction": (
                        "These tool calls already ran and are recorded. "
                        "Continue from recorded state; request only "
                        "genuinely new work.")}, sort_keys=True)}]
        return items

    def _run_one_fallback(title: str, failure: str) -> dict:
        """One budgeted full-context re-send without chain reference.

        Raises _FallbackFailed when reconstruction, budgets, validation,
        or the re-send itself fails. Never retries the same invalid shape.
        """
        nonlocal input_items, last_id, context_mode
        nonlocal api_calls, api_attempts, latency_total, fallback_used
        fallback_used = True
        input_items = _recovery_items()
        last_id = None
        context_mode = "delta_fallback"
        bad = _RQ.validate_request(input_items, None, tools)["problems"]
        if bad:
            record_event(
                session, inv.id, "meta_request",
                "Fallback refused: reconstructed request invalid",
                payload={"failure_category": failure,
                         "reconstructed_mode": "full",
                         "problems": bad[:4],
                         "succeeded": False})
            session.commit()
            raise _FallbackFailed(
                "reconstructed request invalid: " + "; ".join(bad)[:200])
        try:
            budget.check_dispatch(_dispatch_est_input(input_items))
            _ftok = budget.reserve("attempts", 1, note="fallback")
        except _exceeded as fexc:
            record_event(session, inv.id, "budget",
                         f"Fallback refused: {fexc}",
                         payload={"label": "fallback",
                                 "failure_category": failure})
            session.commit()
            raise
        try:
            resp = meta_client.create_response(
                model=config.meta_model_id(), input_items=input_items,
                tools=tools, previous_response_id=None,
                instructions=MODE_INSTRUCTIONS[inv.mode])
        except meta_client.MetaUnavailable as exc2:
            budget.settle(_ftok, 1)
            record_event(session, inv.id, "meta_request",
                         "Meta unavailable (fallback also failed)",
                         detail=str(exc2)[:300],
                         payload={"failure_category": _RQ.failure_category(
                             exc2.status_code, False),
                                 "reconstructed_mode": "full",
                                 "succeeded": False})
            session.commit()
            raise _FallbackFailed(str(exc2))
        api_calls += 1
        fperf = resp.get("_request_perf") or {}
        api_attempts += int(fperf.get("attempts") or 1)
        latency_total += float(fperf.get("latency_s") or 0.0)
        budget.settle(_ftok, int(fperf.get("attempts") or 1))
        record_event(session, inv.id, "meta_request",
                     "Full-context fallback succeeded",
                     payload={"failure_category": failure,
                              "fallback_eligible": True,
                              "reconstructed_mode": "full",
                              "chain_cleared": True,
                              "executed_preserved": len(executed),
                              "succeeded": True})
        session.commit()
        return resp

    # M19: the rollup reports how the turn opened and whether it was
    # recovered; per-round events report the actual chaining in play
    # (the M18 audit found round ≥ 2 mislabeled "full" while chained).
    _turn_open_mode = context_mode
    while round_no < max_rounds:
        round_no += 1
        _round_mode = ("delta" if (last_id and context_mode == "full")
                       else context_mode)
        record_event(session, inv.id, "meta_request",
                     f"Meta round {round_no} (mode={inv.mode})",
                     payload={"round": round_no, "tools_offered": [t["name"] for t in tools],
                              "context_mode": _round_mode})
        # M19 Phase 1: pre-dispatch validation. A known-invalid request
        # (e.g. the M18 chained empty-input shape) is refused LOCALLY —
        # no attempt reserved, nothing billed — and routed straight to the
        # single full-context fallback. Unknown-good shapes always pass.
        rq = _RQ.validate_request(input_items, last_id, tools)
        if rq["problems"]:
            record_event(session, inv.id, "meta_request",
                         "Request invalid — refused before dispatch",
                         detail="; ".join(rq["problems"])[:300],
                         payload={"request_mode": rq["mode"],
                                  "problems": rq["problems"][:4],
                                  "attempt_spent": False})
            session.commit()
            if rq["mode"] == "chained" and not fallback_used:
                try:
                    response = _run_one_fallback(
                        "Pre-dispatch invalid — one full-context fallback",
                        "local-validation")
                except _exceeded as bexc:
                    return {"status": "budget_exceeded",
                            "message_text": text_out,
                            "tool_calls": executed, "error": str(bexc)}
                except _FallbackFailed as fbf:
                    return {"status": "meta_unavailable",
                            "message_text": text_out,
                            "tool_calls": executed, "error": str(fbf)}
            else:
                return {"status": "meta_unavailable",
                        "message_text": text_out,
                        "tool_calls": executed,
                        "error": "invalid request: "
                                 + "; ".join(rq["problems"])[:200]}
        else:
            try:
                _tok = budget.reserve("attempts", 1,
                                      note=f"round-{round_no}")
            except _exceeded as exc:
                record_event(session, inv.id, "budget",
                             f"Attempt refused: {exc}",
                             payload={"label": f"round-{round_no}"})
                session.commit()
                return {"status": "budget_exceeded",
                        "message_text": text_out,
                        "tool_calls": executed, "error": str(exc)}
            try:
                # M17 headroom: refuse the dispatch while the projection
                # would breach the nominal token cap (honest stop, recorded).
                # The round's attempt hold is released: nothing was sent.
                try:
                    budget.check_dispatch(_dispatch_est_input(input_items))
                except _exceeded as hexc:
                    budget.release(_tok, f"headroom refused: {hexc}")
                    record_event(session, inv.id, "budget",
                                 f"Dispatch refused by token headroom: {hexc}",
                                 payload={"label": f"round-{round_no}"})
                    session.commit()
                    return {"status": "budget_exceeded",
                            "message_text": text_out,
                            "tool_calls": executed, "error": str(hexc)}
                response = meta_client.create_response(
                    model=config.meta_model_id(), input_items=input_items,
                    tools=tools, previous_response_id=last_id,
                    instructions=MODE_INSTRUCTIONS[inv.mode])
                api_calls += 1
                perf = response.get("_request_perf") or {}
                api_attempts += int(perf.get("attempts") or 1)
                latency_total += float(perf.get("latency_s") or 0.0)
                budget.settle(_tok, int(perf.get("attempts") or 1))
            except meta_client.MetaUnavailable as exc:
                # Conservative: the request went out (or may have).
                budget.settle(_tok, 1)
                # M19: unified fallback policy for cross-turn AND in-turn
                # chained failures (the M18 round-2 400 died here with no
                # recovery). At most one fallback per turn, chain-status
                # only, budgets rechecked inside _run_one_fallback.
                _had_chain = (bool(previous_response_id) if round_no == 1
                              else bool(last_id))
                _cat = _RQ.failure_category(exc.status_code, _had_chain)
                _elig, _why = _RQ.fallback_eligible(
                    exc.status_code, _had_chain, fallback_used)
                if _elig:
                    record_event(session, inv.id, "meta_request",
                                 "Continuation state refused — one "
                                 "full-context fallback",
                                 detail=str(exc)[:300],
                                 payload={"failure_category": _cat,
                                          "fallback_eligible": True,
                                          "round": round_no})
                    session.commit()
                    try:
                        response = _run_one_fallback(
                            "Continuation state refused — one "
                            "full-context fallback", _cat)
                    except _exceeded as bexc:
                        return {"status": "budget_exceeded",
                                "message_text": text_out,
                                "tool_calls": executed, "error": str(bexc)}
                    except _FallbackFailed as fbf:
                        return {"status": "meta_unavailable",
                                "message_text": text_out,
                                "tool_calls": executed, "error": str(fbf)}
                else:
                    record_event(session, inv.id, "meta_request",
                                 "Meta unavailable", detail=str(exc)[:300],
                                 payload={"failure_category": _cat,
                                          "fallback_eligible": False,
                                          "eligibility_reason": _why[:160]})
                    session.commit()
                    return {"status": "meta_unavailable",
                            "message_text": text_out,
                            "tool_calls": executed, "error": str(exc)}
        last_id = _usable_response_id(meta_client.response_id(response))
        usage = meta_client.usage(response)
        for key, value in (usage or {}).items():
            if isinstance(value, (int, float)):
                token_totals[key] = token_totals.get(key, 0) + int(value)
        text_out = meta_client.extract_message_text(response)
        calls = meta_client.extract_function_calls(response)
        # R2/req-4: the COMPLETE assistant text is persisted verbatim in the
        # event payload (durable record); `detail` stays a truncated display
        # head for timeline presentation only.
        record_event(session, inv.id, "meta_response",
                     f"Meta round {round_no} response",
                     detail=text_out[:600] or "(tool call only)",
                     payload={"response_id": last_id, "n_tool_calls": len(calls),
                              "usage": usage, "text": text_out or ""})
        if not calls:
            # M22 P0: bounded zero-action recovery. A round with no tool
            # calls while NOTHING exists on record (no hypotheses, no new
            # experiments this turn) is total inaction, not a stopping
            # signal: one targeted resume opportunity. Strictly once per
            # turn; all budget/headroom gates still apply on re-dispatch.
            from ..live import accounting as _RACCT
            _hyps_on_record = session.query(Hypothesis).filter(
                Hypothesis.investigation_id == inv.id).count()
            _exp_this_turn = sum(
                1 for e in executed
                if _RACCT.is_experiment(e.get("name"))
                and not (e.get("outcome") or {}).get("reused"))
            # M22 refinement: fire only for the M21 shape — substantive
            # prose with NO structured candidate. A response carrying a
            # candidate block (valid or not) stays on the normal
            # validate/repair path, preserving long-standing reporting
            # behavior (M8 valid-summary turns, M20 repair flows).
            from ..causal import summary_class as _SCC
            _round_class = _SCC.classify(text_out, None)["class"]
            if (not _zero_recovery_sent and round_no < max_rounds
                    and _hyps_on_record == 0 and _exp_this_turn == 0
                    and _round_class == _SCC.PROSE_WITHOUT_BLOCK):
                _zero_recovery_sent = True
                _recovery = {
                    "role": "user", "content": json.dumps({
                        "zero_action_recovery": {
                            "situation": (
                                "Your last response contained no tool calls "
                                "and no hypotheses are on record: the "
                                "investigation has produced no diagnostic "
                                "progress."),
                            "required": (
                                "Resume the investigation now: propose 2-3 "
                                "competing hypotheses with the "
                                "propose_hypothesis tool, then run the most "
                                "discriminating diagnostic from the "
                                "selection brief "
                                f"(top: {(_top_names[:1] or ['none'])[0]})."),
                            "constraints": (
                                "Use only recorded evidence and the tools "
                                "offered; cite action ids you receive; "
                                f"budget left: "
                                f"{inv.max_tool_calls - inv.tool_call_count} "
                                "tool calls.")}}, sort_keys=True)}
                record_event(session, inv.id, "decision_prompt",
                             "Zero-action recovery: nothing recorded yet — "
                             "one bounded resume opportunity",
                             payload={"round": round_no,
                                      "hypotheses_on_record": 0,
                                      "experiments_this_turn": 0})
                session.commit()
                input_items = [_recovery]
                continue
            break
        call_outputs = []
        # M18 Phase 1: hypothesis ops bypass the experiment budget;
        # only actual measurements go through the shared allocator.
        from ..live import accounting as _ACCT
        # M18: the call-list slice is governed ONLY by the tool-call
        # (attempts) budget. The experiment cap is enforced per-dispatch
        # by the shared allocator: hypothesis ops always pass through,
        # experiment dispatches refuse (with a recorded error) when the
        # cap or the verification hold would break.
        remaining = inv.max_tool_calls - inv.tool_call_count
        _exec_before = len(executed)
        _exp_spent_turn = 0
        for call in calls[: max(0, remaining)]:
            _is_exp = _ACCT.is_experiment(call["name"])
            _etok = None
            _kind = "model-diagnostic"
            if _is_exp:
                # Caller budget minus experiments already settled this
                # turn (executed holds whole-turn history; _exp_spent_turn
                # counts this round's settles since budget.used lags by
                # construction — both subtracted would double-count, so
                # use the executed-list count as the single source).
                _left = None
                if experiments_left is not None:
                    _settled_turn = sum(
                        1 for e in executed
                        if _ACCT.is_experiment(e.get("name"))
                        and not (e.get("outcome") or {}).get("reused"))
                    _left = max(0, experiments_left - _settled_turn)
                try:
                    _etok = _ACCT.reserve_experiment(
                        session, inv, budget, call["name"],
                        purpose="model-requested diagnostic",
                        kind="model-diagnostic",
                        experiments_left=_left)
                except (_exceeded, ValueError) as exc:
                    record_event(session, inv.id, "budget",
                                 f"Execution refused: {exc}",
                                 payload={"tool": call["name"]})
                    call_outputs.append({
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(
                            {"error": "experiment_budget_exhausted",
                             "detail": str(exc)[:160]})})
                    break
            outcome = engine.run_tool(session, inv, call["name"],
                                      dict(call.get("arguments") or {}),
                                      source_meta=True)
            executed.append({"call_id": call["call_id"], "name": call["name"],
                             "outcome": outcome})
            if not _is_exp:
                continue  # hypothesis op: zero experiment slots consumed
            if outcome.get("reused"):
                reused_count += 1
                _ACCT.release_experiment(
                    session, inv, budget, _etok, call["name"],
                    "model-diagnostic", "dedup reuse: no new execution")
            else:
                # Started = counted, even on failure (M8 rule).
                _ACCT.settle_experiment(
                    session, inv, budget, _etok, call["name"],
                    "model-diagnostic", bool(outcome.get("ok")),
                    action_id=outcome.get("action_id"),
                    error=outcome.get("error"))
                _exp_spent_turn += 1
                if outcome.get("ok"):
                    _ran_new_turn += 1  # M22 P1: new ran measurement
            packet = {"tool": call["name"],
                      "result": outcome.get("result"),
                      "ok": outcome.get("ok", False),
                      "reused": outcome.get("reused") or None,
                      "error": outcome.get("error")}
            packet = _truncate_tool_payload(packet)  # F8: valid-JSON truncation
            call_outputs.append({
                "type": "function_call_output", "call_id": call["call_id"],
                "output": json.dumps(packet, sort_keys=True, default=str)})
        if len(calls) > remaining:
            for call in calls[remaining:]:
                call_outputs.append({
                    "type": "function_call_output", "call_id": call["call_id"],
                    "output": json.dumps({"error": "tool_call_budget_exhausted"})})
        # M7 closed loop: backend links each executed tool result to the
        # hypotheses it bears on (recorded, justified; failures never link).
        from ..causal import linker as _linker
        for entry in executed[_exec_before:]:
            aid = (entry.get("outcome") or {}).get("action_id")
            if not aid:
                continue
            act = session.get(Action, aid)
            if act is not None and act.investigation_id == inv.id:
                _linker.link_tool_result(session, inv, act)
        if inv.tool_call_count >= inv.max_tool_calls:
            record_event(session, inv.id, "status_change",
                         f"Tool-call budget exhausted ({inv.max_tool_calls})")
        # M19 Phase 2: post-hypothesis decision nudge. A round that ends
        # with newly proposed hypotheses but zero executed experiments and
        # rounds remaining gets one explicit decision prompt. Declining
        # with a reason is a valid outcome — silence is not.
        _new_hyps_round = [
            e for e in executed[_exec_before:]
            if e.get("name") == "propose_hypothesis"
            and (e.get("outcome") or {}).get("ok")]
        _exp_turn = sum(
            1 for e in executed
            if _ACCT.is_experiment(e.get("name"))
            and not (e.get("outcome") or {}).get("reused"))
        if (_new_hyps_round and _exp_turn == 0
                and round_no < max_rounds and not _nudge_sent):
            _nudge_sent = True
            _nudge = {
                "role": "user", "content": json.dumps({
                    "decision_required": {
                        "situation": (
                            f"{len(_new_hyps_round)} new hypothesis(es) "
                            "proposed, no diagnostic executed yet."),
                        "decide": ("Run the discriminating diagnostic from "
                                   "the selection brief (or name your "
                                   "different tool with a one-sentence "
                                   "reason), OR record why no diagnostic "
                                   "is justified: what measurement would "
                                   "discriminate and why no available tool "
                                   "fits, or why evidence/budget forbids "
                                   "it."),
                        "incomplete": ("New hypotheses with no diagnostic "
                                        "and no recorded reason leave the "
                                        "turn incomplete.")}}, sort_keys=True)}
            record_event(session, inv.id, "decision_prompt",
                         "Decision required: hypotheses need a next action",
                         payload={"new_hypotheses": len(_new_hyps_round),
                                  "experiments_so_far": _exp_turn})
            session.commit()
            wrapup = _wrapup_item(round_no, max_rounds, inv)
            input_items = (call_outputs + ([wrapup] if wrapup else [])
                           + [_nudge])
        else:
            wrapup = _wrapup_item(round_no, max_rounds, inv)
            input_items = call_outputs + ([wrapup] if wrapup else [])
        session.commit()
    session.commit()
    # M17 Phase 1: reservation AFTER hypotheses exist (see helper).
    maybe_reserve_end_of_turn(session, inv, budget, experiments_left)
    # M16 P1-3: skeptic-lite pass over the turn's recorded evidence.
    # Budgeted (reuses reservation when the probe matches); dissent is
    # preserved when evidence cannot resolve it. Arm flag: comparison
    # arms may disable it via inv.config["m16_skeptic"] = False.
    from ..live import skeptic as _sk_flag
    _skeptic_on = _sk_flag.enabled(inv.config)
    if not _skeptic_on:
        record_event(session, inv.id, "skeptic",
                     "Skeptic-lite disabled by arm flag (comparison arm)",
                     payload={"m16_skeptic": False})
        session.commit()
    else:
        try:
            from ..research import invention as _INV2
            from ..live import skeptic as _sk
            _sk_facts = _INV2.artifact_facts(
                (inv.config or {}).get("predictions_path") or "")
            _sk.review(session, inv, budget, experiments_left,
                       _sk_facts if _sk_facts.get("readable") else None)
        except Exception as _sk_exc:  # review never breaks the turn
            record_event(session, inv.id, "skeptic",
                         f"Skeptic-lite skipped: {type(_sk_exc).__name__}",
                         payload={"reason": str(_sk_exc)[:200]})
            session.commit()
    # M16 P1-2: grounded facts the model must explain, not regenerate.
    _grounded = engine.grounded_summary(session, inv)
    record_event(session, inv.id, "grounded",
                 f"Grounded summary: {len(_grounded['hypotheses'])} "
                 f"hypotheses, {len(_grounded['actions'])} actions",
                 payload=_grounded)
    session.commit()

    summary = engine.validate_structured_summary(session, inv, text_out)
    repair_records: list[dict] = []
    if not summary.get("valid"):
        # F4: one bounded repair attempt; recorded either way. The record
        # survives in the turn result so benchmark recorders can persist a
        # dedicated repair artifact (the exchange itself is also in the
        # provider-response log via the wrapped client).
        # M20 Phase 3.1: repair eligibility from the output class. Empty
        # output and provider failures go straight to deterministic
        # fallback — retrying the model cannot fix them. Strictly one
        # attempt: no loops, no recursion (this block runs at most once
        # per turn by construction).
        from ..causal import summary_class as _SC
        _out_class = summary.get("output_class") or _SC.classify(
            text_out, summary)["class"]
        if not _SC.repair_eligible_for(_out_class):
            repair_state["attempted"] = False
            repair_state["valid"] = None
            record_event(session, inv.id, "summary_repair",
                         "Summary repair not eligible "
                         f"({_out_class}) — deterministic fallback",
                         payload={"output_class": _out_class,
                                  "errors": (summary.get("errors") or [])[:8]})
            from ..causal import fallback as _fallback0
            _fb_report0 = engine.build_report(session, inv)
            fallback = _fallback0.compose(
                inv, _fb_report0, (summary.get("errors") or []),
                session=session,
                usage={"tokens": dict(token_totals)})
            record_event(session, inv.id, "fallback",
                         "Deterministic fallback composed from records",
                         payload={"fallback_version":
                                  fallback["fallback_version"]})
        else:
         repairs = 1
         repair_state["attempted"] = True
         record_event(session, inv.id, "summary_repair",
                      "Structured summary invalid — one repair attempt",
                      payload={"output_class": _out_class,
                               "errors": (summary.get("errors") or [])[:8]})
         try:
            errors_before = (summary.get("errors") or [])[:8]
            r_summary, r_text, r_perf = _attempt_summary_repair(
                session, inv, summary, budget=budget)
            repair_records.append({
                "valid": bool(r_summary.get("valid")),
                "repair_text": r_text,
                "response_id": r_perf.get("response_id"),
                "usage": r_perf.get("usage") or {},
                "errors_before": errors_before,
                "errors_after": (r_summary.get("errors") or [])[:8],
                "continuation": None,  # filled below once decided
            })
            api_calls += 1
            api_attempts += int(r_perf.get("attempts") or 1)
            latency_total += float(r_perf.get("latency_s") or 0.0)
            for key, value in (r_perf.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    token_totals[key] = token_totals.get(key, 0) + int(value)             # M20 Phase 3.4/4: a repaired summary must ALSO pass the
            # authoritative consistency gates (refs, measurements,
            # terminal states, verification, contradictions, budget).
            # Good prose is not enough — reject and fall back instead.
            _consistency = None
            if r_summary.get("valid"):
                from ..causal import report_consistency as _RC
                _consistency = _RC.check_repaired_summary(
                    session, inv, r_summary)
                repair_records[-1]["consistency"] = {
                    "passed": _consistency["passed"],
                    "failures": _consistency["failures"][:8]}
                record_event(
                    session, inv.id, "summary_repair",
                    "Repaired summary consistency: "
                    + ("passed" if _consistency["passed"]
                       else "FAILED — repair rejected"),
                    payload={"passed": _consistency["passed"],
                             "failures": _consistency["failures"][:8]})
            if r_summary.get("valid") and _consistency.get("passed"):
                text_out = r_text
                summary = r_summary
                # M20 Phase 6: mark the repaired origin for provenance.
                summary["repaired_via"] = "summary_repair"
                repair_state["valid"] = True
                repair_id = _usable_response_id(r_perf.get("response_id"))
                if repair_id:
                    # The repaired response is now the last provider state.
                    last_id = repair_id
                    repair_state["response_id_source"] = "repair"
                    repair_records[-1]["continuation"] = "repair"
                    record_event(
                        session, inv.id, "summary_repair",
                        "Summary repair produced a valid structured summary",
                        payload={"valid": True, "continuation": "repair",
                                 "output_class":
                                 r_summary.get("output_class"),
                                 "repair_text_head": (r_text or "")[:600]})
                else:
                    # A repair we cannot address cannot seed the next turn;
                    # chaining from the pre-repair response would silently
                    # discard the repair, so declare the state unavailable.
                    last_id = None
                    repair_state["response_id_source"] = "unavailable"
                    repair_records[-1]["continuation"] = "unavailable"
                    record_event(
                        session, inv.id, "summary_repair",
                        "Summary repair produced no usable response id — "
                        "continuation state not established",
                        payload={"valid": True, "continuation": "unavailable",
                                 "output_class":
                                 r_summary.get("output_class"),
                                 "repair_text_head": (r_text or "")[:600]})
            else:
                # The original invalid verdict AND its response id stand: the
                # returned text is the original message, so continuing from
                # the original response is the honest state. This also
                # covers valid-but-inconsistent repairs (M20 3.4).
                repair_state["valid"] = False
                repair_records[-1]["continuation"] = "original"
                _cons_fail = ((_consistency or {}).get("failures") or [])[:8]
                record_event(session, inv.id, "summary_repair",
                             "Summary repair rejected — original verdict stands",
                             payload={"valid": False,
                                      "continuation": "original",
                                      "output_class":
                                      r_summary.get("output_class"),
                                      "repair_text_head": (r_text or "")[:600],
                                      "errors": (r_summary.get("errors") or [])[:8],
                                      "consistency_failures": _cons_fail})
                from ..causal import fallback as _fallback2
                _fb_report2 = engine.build_report(session, inv)
                fallback = _fallback2.compose(
                    inv, _fb_report2, (r_summary.get("errors") or []),
                    session=session,
                    usage={"tokens": dict(token_totals)})
                record_event(session, inv.id, "fallback",
                             "Deterministic fallback composed from records",
                             payload={"fallback_version":
                                      fallback["fallback_version"]})
         except (meta_client.MetaUnavailable, _exceeded) as exc:
            from ..live import governor as _gov
            _budget_refused = isinstance(exc, _gov.BudgetExceeded)
            repair_state["valid"] = None
            repair_records.append({
                "valid": None,
                "repair_text": None,
                "response_id": None,
                "usage": {},
                "errors_before": (summary.get("errors") or [])[:8],
                "errors_after": [],
                "continuation": "original",
                "unavailable_reason": str(exc)[:300],
            })
            record_event(session, inv.id, "summary_repair",
                         ("Summary repair refused by budget — original "
                          "verdict stands" if _budget_refused else
                          "Summary repair unavailable — original verdict stands"),
                         detail=str(exc)[:300])
            # M8 deterministic fallback: composed from records only,
            # explicitly labeled; the invalid original is preserved.
            from ..causal import fallback as _fallback
            _fb_report = engine.build_report(session, inv)
            fallback = _fallback.compose(
                inv, _fb_report, (summary.get("errors") or []),
                session=session,
                usage={"tokens": dict(token_totals)})
            record_event(session, inv.id, "fallback",
                         "Deterministic fallback composed from records",
                         payload={"fallback_version":
                                  fallback["fallback_version"]})
    usage_roll = {"rounds": round_no, "api_calls": api_calls,
                  "api_attempts": api_attempts,
                  "latency_s": round(latency_total, 3) or None,
                  "summary_repair_attempts": repairs,
                  "summary_repair_continuation": repair_state["response_id_source"],
                  "fallback_used": fallback_used,
                  "context_mode": ("delta_fallback" if fallback_used
                                   else _turn_open_mode),
                  "tool_calls_executed": len(executed) - reused_count,
                  "tool_calls_reused": reused_count,
                  "tokens": token_totals or None,
                  "fallback_composed": fallback is not None}
    record_event(session, inv.id, "meta_usage", "Turn usage rollup",
                 payload=usage_roll)
    # M7 closed loop: adherence of this turn's choices to the brief.
    _diag_done = [e["name"] for e in executed
                  if e["name"] != "propose_hypothesis"]
    if not _diag_done:
        record_event(session, inv.id, "selection",
                     "Adherence: n/a (no diagnostics requested this turn)",
                     payload={"recommended": _top_names,
                              "executed_diagnostics": [],
                              "followed": None})
    else:
        _followed = _diag_done[0] in _top_names[:2]
        record_event(session, inv.id, "selection",
                     f"Adherence: {'followed' if _followed else 'deviated'} "
                     f"(chose={_diag_done[0]}, "
                     f"recommended={(_top_names[:1] or ['none'])[0]})",
                     payload={"recommended": _top_names,
                              "executed_diagnostics": _diag_done,
                              "followed": _followed})
    # M19 Phase 2: explicit per-turn investigator decision (accountability).
    # Derived from the record, never invented: what ran, what was chosen,
    # why (or the marked absence of a reason). Declining with a recorded
    # reason is valid; hypotheses + no diagnostic + no reason = incomplete.
    from ..live import accounting as _ACCT
    _hyps_now = session.query(Hypothesis).filter(
        Hypothesis.investigation_id == inv.id).all()
    _open = [{"id": h.id, "text": (h.text or "")[:140],
               "status": h.status} for h in _hyps_now
              if h.status in ("proposed", "investigating", "supported")]
    _exp_names = [e["name"] for e in executed
                   if _ACCT.is_experiment(e.get("name"))
                   and not (e.get("outcome") or {}).get("reused")]
    _new_total_all = len(_hyps_now) - _hyps_before
    # M22 P0: total inaction — the turn proposed nothing and executed no
    # new experiment. Made visible to orchestration and completion logic;
    # a turn that did nothing is never recorded as completed progression.
    _total_inaction = (len(_exp_names) == 0 and _new_total_all == 0)
    _verify_ready = any(
        h.status in ("investigating", "supported")
        and sum(1 for r in (h.evidence_refs or [])
                if r.get("relation") == "supports") >= 1
        and not any(r.get("relation") == "contradicts"
                    for r in (h.evidence_refs or []))
        for h in _hyps_now)
    _progress = _classify_turn_progress(
        new_hypotheses=_new_total_all,
        executed_any=len(executed) > 0,
        ran_new=_ran_new_turn, verify_ready=_verify_ready)
    _rec_next = ""
    try:
        _rec_next = str((summary.get("summary") or {}).get(
            "recommended_next") or "")[:300]
    except Exception:
        _rec_next = ""
    if _exp_names:
        # Score the executed tool against FINAL recorded state, excluding
        # its own run from the ran set: this recovers the prospective
        # discrimination rationale (the turn-start brief predates the
        # hypotheses proposed this turn, so it cannot supply it).
        from ..db import Action as _DecisionAction
        from ..causal import selection as _SEL
        _final_hviews = [{"id": h.id, "text": h.text,
                          "status": h.status,
                          "evidence_refs": h.evidence_refs or []}
                         for h in _hyps_now]
        _final_ran = {a.tool_name for a in session.query(
            _DecisionAction).filter(
            _DecisionAction.investigation_id == inv.id,
            _DecisionAction.status == "ran").all() if a.tool_name}
        try:
            _brief_hit = _SEL.score_candidate(
                _exp_names[0], _final_hviews,
                set(_final_ran) - {_exp_names[0]})
        except Exception:
            _brief_hit = {}
        _decision = {
            "next_action": "diagnostic-executed",
            "tool": _exp_names[0],
            "target_hypothesis": None,
            "question": (_brief_hit.get("reason") or "")[:200],
            "expected_info_value": _brief_hit.get("expected_value"),
            "distinctions": _brief_hit.get("covers"),
            "rationale": "model executed a diagnostic this turn",
            "executed": True, "outcome": "completed-turn",
            "incomplete_progression": False}
    elif _rec_next:
        _decision = {
            "next_action": "deferred: " + _rec_next[:160],
            "tool": None, "target_hypothesis": None,
            "question": None, "expected_info_value": None,
            "distinctions": None,
            "rationale": _rec_next[:300],
            "executed": False, "outcome": "completed-turn",
            "incomplete_progression": False}
    else:
        _new_total = len(_hyps_now) - _hyps_before
        _decision = {
            "next_action": "no-diagnostic-no-reason",
            "tool": None, "target_hypothesis": None,
            "question": None, "expected_info_value": None,
            "distinctions": None,
            "rationale": (f"{_new_total} new hypothesis(es) this turn, "
                            "no experiment executed, no decline recorded"),
            "executed": False, "outcome": "completed-turn",
            "incomplete_progression": (bool(_new_total > 0) or _total_inaction)} 
    _decision.update({
        "total_inaction": _total_inaction,
        "progress": _progress,
        "investigation_status": inv.status,
        "candidates": _open,
        "new_hypotheses_this_turn": len(_hyps_now) - _hyps_before,
        "experiments_this_turn": len(_exp_names),
        "budget": {"experiments_used": budget.experiments_used,
                     "experiments_cap": budget.caps["experiments"],
                     "attempts_used": budget.attempts_used,
                     "attempts_cap": budget.caps["attempts"]},
        "summary_valid": bool(summary.get("valid"))})
    record_event(session, inv.id, "investigator_decision",
                 "Investigator decision: " + _decision["next_action"][:120],
                 payload=_decision)
    session.commit()
    return {"status": "ok", "message_text": text_out, "tool_calls": executed,
            "response_id": last_id, "usage": usage,
            "summary": summary, "usage_rollup": usage_roll,
            "continuation_state": repair_state, "repairs": repair_records,
            "fallback": fallback, "decision": _decision}
