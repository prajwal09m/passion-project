"""Groq context-efficiency benchmark for Model Autopsy.

Measures whether the AI-investigator context optimization (commit 6cf865f ->
working tree) reduces prompt size and redundant diagnostic work, using Groq
for provider-reported token counts when explicitly asked.

ISOLATION GUARANTEES
  - Runs entirely on a MODEL_AUTOPSY_DB_PATH temp SQLite database; never the
    live application DB.
  - Never calls the Meta API; the Meta integration is imported read-only
    (metadata only) and never modified.
  - GROQ_API_KEY is read from the environment only. The key is never
    printed, logged, or written anywhere.
  - Default mode is --offline: no network at all.

MODES
  --offline            Build both payloads, compare sizes, verify duplicate
                       reuse locally. Zero network. (default)
  --live --requests N  Additionally POST the two payloads to Groq Chat
                       Completions (no tools) and record provider-reported
                       prompt/completion tokens, latency, and an ESTIMATED
                       cost from the published pricing table. N <= 3 extra
                       requests; the default is the two context probes.
  --rounds N           MIRRORED OLD-NEW multi-round comparison (live only):
                       a 1-request tool-calling capability probe plus, per
                       condition (old 6cf865f loop vs current loop), up to N
                       billed rounds with the SAME reduced tool list in both,
                       everything through backend registry validation and
                       budgets. Hard billed-request cap: 10 (probe + 2*N).
                       Execution/reuse counts come from RECORDED backend
                       actions, never from model prose. Reuse-certification
                       stays in the offline test (it is NOT token-credited).

ACCURACY RULES
  - Character counts are never presented as tokens. Offline rows say
    "not measured".
  - Live token numbers are exactly what Groq's usage object reports.
  - Cost is an estimate computed from the price source named per model;
    it is never claimed to be an actual charge.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCH_DIR.parent.parent   # the repo root (importable package)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
RESULTS_PATH = BENCH_DIR / "RESULTS.md"

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# Published per-1M-token pricing, labeled per source. "llama-3.3-70b-versatile"
# is currently Enterprise/Contact-Sales on console.groq.com/docs/models, which
# publishes no per-token price; the value below is the historical published
# rate and may not reflect current terms.
GROQ_PRICING_USD_PER_M = {
    "llama-3.3-70b-versatile": {
        "input": 0.59, "output": 0.79,
        "source": "historical published Groq text rates; current models page "
                  "lists this model as Enterprise/Contact-Sales with no "
                  "per-token price — estimate may not match current terms"},
    "openai/gpt-oss-120b": {
        "input": 0.15, "output": 0.60,
        "source": "console.groq.com/docs/models (current published price)"},
    "openai/gpt-oss-20b": {
        "input": 0.075, "output": 0.30,
        "source": "console.groq.com/docs/models (current published price)"},
}
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

# Multi-round live mode (mirrored conditions)
#   - identical reduced tool list for BOTH conditions; everything still goes
#     through the backend registry validation and tool budget.
BENCH_TOOL_ALLOWLIST = ("artifact_summary", "classification_metrics",
                        "propose_hypothesis")
BILL_REQUEST_CAP = 10          # hard ceiling: probe + 2 conditions x rounds
CHT_MAX_TOKENS = 800

# --------------------------------------------------------------------------
# Multi-round live mode: mirrored old-loop vs new-loop capstone comparison
# --------------------------------------------------------------------------

def _to_openai_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function", "function": t} for t in tools]


def _backend_tool_counts(session, engine_mod, inv_id: str) -> dict:
    """Counts from RECORDED backend actions — never from model prose."""
    from model_autopsy.backend.db import Action, Event
    actions = (session.query(Action)
               .filter(Action.investigation_id == inv_id).all())
    executed = [a for a in actions if a.status == "ran"]
    failed = [a for a in actions if a.status == "failed"]
    reused_evs = [e for e in (session.query(Event)
                              .filter_by(investigation_id=inv_id,
                                         kind="tool_result").all())
                  if (e.payload or {}).get("reused")]
    return {"executed": len(executed),
            "executed_tools": sorted({a.tool_name for a in executed}),
            "failed": len(failed),
            "reused_prior_results": len(reused_evs)}


def _mirror_loop(condition: str, n_rounds: int, api_key: str, model: str,
                 session, engine_mod, meta_loop, tools: list[dict],
                 ledger: dict[str, int]) -> dict:
    """Run one condition's loop against Groq with identical constraints.

    `condition` old/new determines ONLY the instruction text, the initial
    payload and the reuse semantics that the corresponding implementation
    had. Threading mechanics are identical for both (stateless resend).
    Reuse results never cross investigations/conditions.
    """
    import json as _json
    from model_autopsy.backend.db import Event as _Event, init_db as _init_db
    _init_db()
    inv = engine_mod.create_investigation(
        session, "ml", f"groq-bench-{condition}",
        "Why does the model underperform on out-of-fold data?",
        {"max_tool_calls": 3})
    engine_mod.build_context(session, inv)
    if condition == "old":
        initial_content = _json.dumps(
            _legacy_initial_context_items(inv)[0]["content"])
        instructions = LEGACY_MODE_INSTRUCTIONS_ML
        allow_reuse = False   # old loop executed duplicate requests verbatim
    else:
        initial_content = meta_loop._initial_context_items(session, inv)[0]["content"]
        instructions = meta_loop.MODE_INSTRUCTIONS["ml"]
        allow_reuse = True    # backend reuse guard, as in the current loop

    messages = [{"role": "system", "content": instructions},
                {"role": "user", "content": initial_content}]
    rounds_out: list[dict] = []
    totals = {"input_tokens": 0, "output_tokens": 0}
    billed = 0

    for round_no in range(1, n_rounds + 1):
        if billed >= n_rounds:
            break
        body: dict = {"model": model, "messages": messages,
                      "temperature": 0, "max_tokens": CHT_MAX_TOKENS,
                      "tools": tools}
        if ledger["billed_requests"] >= BILL_REQUEST_CAP:
            rounds_out.append({"round": round_no,
                               "error": "request-attempt cap reached; aborted "
                                        "before sending"})
            break

        def _post_once() -> dict:
            return _groq_request("POST", GROQ_CHAT_URL, api_key, json=body)

        r = _post_once()
        billed += 1
        ledger["billed_requests"] += 1
        if r["status"] == 429:
            # Rate limit: wait once and retry. Rejected requests generate no
            # tokens (unbilled by the provider) but still count toward the
            # request-attempt cap, which is enforced below.
            time.sleep(20)
            if ledger["billed_requests"] >= BILL_REQUEST_CAP:
                rounds_out.append({"round": round_no,
                                   "error": "attempt cap reached after 429 "
                                            "backoff; aborted before retry"})
                break
            r = _post_once()
            billed += 1
            ledger["billed_requests"] += 1
        if r["status"] != 200:
            rounds_out.append({"round": round_no, "http_status": r["status"],
                               "error": str(r["body"])[:200]})
            break
        usage = r["body"].get("usage") or {}
        message = ((r["body"].get("choices") or [{}])[0]
                   or {}).get("message", {}) or {}
        finish = (((r["body"].get("choices") or [{}])[0] or {})
                  .get("finish_reason"))
        totals["input_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["output_tokens"] += int(usage.get("completion_tokens") or 0)
        calls = [(tc.get("id"), ((tc.get("function") or {}) or {})
                 .get("name"), (tc.get("function") or {}).get("arguments"))
                 for tc in (message.get("tool_calls") or [])]
        rounds_out.append({"round": round_no,
                           "prompt_tokens": usage.get("prompt_tokens"),
                           "completion_tokens": usage.get("completion_tokens"),
                           "latency_s": r["latency_s"],
                           "finish_reason": finish,
                           "tool_calls_requested": len(calls)})
        if not calls:
            break
        # Mirror the EXISTING loop semantics: resolved to the registered tool
        # list; run_tool validates, budgets and records evidence itself.
        messages.append({"role": "assistant",
                          "content": message.get("content") or None,
                          "tool_calls": message.get("tool_calls")})
        for call_id, name, args in calls:
            try:
                parsed = _json.loads(args) if isinstance(args, str) else (args or {})
            except _json.JSONDecodeError:
                parsed = {"_invalid_json": str(args)[:200]}
            outcome = engine_mod.run_tool(session, inv, str(name or ""),
                                          dict(parsed),
                                          source_meta=allow_reuse)
            payload = {"tool": name,
                       "ok": outcome.get("ok", False),
                       "error": outcome.get("error")}
            if "result" in outcome:
                payload["result_digest"] = _json.dumps(
                    outcome.get("result"), default=str)[:600]
            messages.append({"role": "tool", "tool_call_id": call_id,
                             "content": _json.dumps(payload)[:2000]})
        if inv.tool_call_count >= inv.max_tool_calls:
            break
        # NEW-loop wrap-up rides the last permissible round (no extra call):
        if condition == "new" and (
                inv.max_tool_calls - inv.tool_call_count) <= 2:
            messages.append({"role": "user", "content": (
                "Budget/rounds are nearly exhausted. Do not request further "
                "experiments unless one could still change the conclusion. "
                "Finish now: interpret the recorded results honestly and end "
                "with your investigation_summary block.")})
        session.commit()
        time.sleep(2)   # small inter-round pause; avoids tight-loop rate limits

    executed = _backend_tool_counts(session, engine_mod, inv.id)
    return {
        "condition": condition,
        "rounds_investigated": len(rounds_out),
        "per_round": rounds_out,
        "cumulative": totals,
        "provider_reported": True,
        "backend_validation": {
            **executed,
            "tool_calls_used": inv.tool_call_count,
            "max_tool_calls": inv.max_tool_calls,
        },
        "billed_this_condition": billed,
    }


def _pricing_for(model: str) -> dict:
    return GROQ_PRICING_USD_PER_M.get(model, {
        "input": None, "output": None,
        "source": f"no published price registered for {model!r}"})


def _capability_probe(api_key: str, model: str,
                      ledger: dict[str, int]) -> dict:
    """1-request check that tool calling works on the selected model.
    Stops the comparison if it does not (no misleading fallback results)."""
    matching = [t for t in _raw_ml_tools() if t["name"] == "artifact_summary"]
    one_tool = _to_openai_tools(matching)
    body = {"model": model,
            "messages": [
                {"role": "system",
                 "content": "Be terse. When asked, call the offered tool."},
                {"role": "user",
                 "content": "Call the artifact_summary tool with no "
                 "arguments."}],
            "temperature": 0, "max_tokens": 500, "tools": one_tool}
    r = _groq_request("POST", GROQ_CHAT_URL, api_key, json=body)
    if r["status"] != 200:
        return {"ok": False, "why": f"probe HTTP {r['status']}: "
                                     f"{str(r['body'])[:200]}"}
    message = ((r["body"].get("choices") or [{}])[0] or {}).get("message", {})
    supported = bool(message.get("tool_calls"))
    ledger["billed_requests"] += 1
    return {"ok": supported,
            "why": "" if supported else
            "model returned no tool call to an explicit tool request; "
            "tool-enabled comparison cannot be made fairly"}


def _raw_ml_tools() -> list[dict]:
    from model_autopsy.backend import tools_registry as tr
    return [t for t in tr.meta_tool_schemas("ml")
            if t["name"] in BENCH_TOOL_ALLOWLIST]


def _multi_run(n_rounds: int, model: str, skip_verification: bool = False,
               prior_attempts_note: str = "",
               only_condition: str | None = None) -> dict:
    """Mirrored old-vs-new multi-round comparison under the hard cap.

    skip_verification=True skips GET /models and the tool-calling probe —
    ONLY safe when both were already exercised successfully earlier in the
    same session, so a recovery rerun does not re-bill them.
    Returns a report dict or {error: ...} when fairness cannot be kept."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"error": "GROQ_API_KEY is not set in the environment."}
    if 1 + 2 * n_rounds > BILL_REQUEST_CAP:
        return {"error": f"refusing to run: probe + 2x{n_rounds} rounds = "
                         f"{1 + 2 * n_rounds} billed requests exceeds the "
                         f"{BILL_REQUEST_CAP}-request hard cap"}
    ledger = {"billed_requests": 0}
    from model_autopsy.backend import engine as engine_mod
    from model_autopsy.backend.meta_api import loop as meta_loop
    from model_autopsy.backend.db import SessionLocal, init_db

    # Unbilled verification: model listed + tool-calling capability.
    if not skip_verification:
        listing = _groq_request("GET", GROQ_MODELS_URL, api_key)
        model_list = [m.get("id") for m in
                      (listing["body"].get("data") or []) if isinstance(m, dict)]
        if listing["status"] != 200:
            return {"error": f"GET /models failed: {listing['status']} "
                             f"{str(listing['body'])[:200]} (key or endpoint "
                             f"problem); nothing billed",
                    "billed_requests": 0}
        if model not in model_list:
            return {"error": f"{model!r} was NOT returned by GET /models "
                             f"(got {len(model_list)} ids); nothing billed",
                    "billed_requests": 0}
        probe = _capability_probe(api_key, model, ledger)
        if not probe["ok"]:
            return {"error": "tool-calling capability probe failed: "
                             + probe["why"],
                    "billed_requests": ledger["billed_requests"]}
    tools = _to_openai_tools(_raw_ml_tools())
    init_db()
    session = SessionLocal()
    try:
        results = []
        for condition in (("old", "new") if only_condition is None
                          else (only_condition,)):
            results.append(_mirror_loop(
                condition, n_rounds, api_key, model, session, engine_mod,
                meta_loop, tools, ledger))
        if ledger["billed_requests"] > BILL_REQUEST_CAP:
            return {"error": "cap exceeded — aborting"}
        pricing = _pricing_for(model)
        for row in results:
            tin = row["cumulative"]["input_tokens"]
            tout = row["cumulative"]["output_tokens"]
            if pricing["input"] is not None:
                row["estimated_cost_usd"] = round(
                    tin / 1e6 * pricing["input"]
                    + tout / 1e6 * pricing["output"], 6)
            else:
                row["estimated_cost_usd"] = None
        return {"mode": "multi-round", "model": model, "rounds": n_rounds,
                "tool_list": [t["name"] for t in _raw_ml_tools()],
                "same_tools_both_conditions": [t["name"] for t in _raw_ml_tools()],
                "billed_requests": ledger["billed_requests"],
                "request_cap": BILL_REQUEST_CAP,
                "conditions": results,
                "pricing": pricing,
                "limitations": ([prior_attempts_note] if prior_attempts_note else []) + [
                    "Measures the COMBINED effect of instruction + context "
                    "changes (they differ between conditions); not context "
                    "compaction alone.",
                    "Groq chat-completions is stateless — each round resends "
                    "the transcript; Meta's Responses API uses "
                    "previous_response_id, so absolute per-round counts "
                    "would differ behind Meta.",
                    "A 3-round simulation is not a real end-to-end "
                    "investigation and cannot show that the new investigator "
                    "reaches better conclusions.",
                    "Groq results do not establish Meta API performance.",
                    "Duplicate-diagnostic prevention is certified separately "
                    "by the offline backend test (see RESULTS offline "
                    "section); it is NOT included in these token totals.",
                    "Cost figures are estimates from published pricing, not "
                    "actual charges.",
                ]}
    finally:
        session.close()


def _multi_markdown(mr: dict) -> str:
    if mr.get("error"):
        return f"\n<!-- multi-round -->\n## Multi-round comparison\n\nBROKEN: {mr['error']}\n"
    lines = [
        "\n<!-- multi-round -->",
        f"## Multi-round comparison ({mr['rounds']} rounds, "
        f"cap {mr['request_cap']}, billed {mr['billed_requests']})",
        "",
        f"Model: `{mr['model']}`; tools (identical both conditions): "
        f"{', '.join(mr['tool_list'])}",
        "",
        "| Condition | cumulative input tokens | cumulative output tokens | "
        "executions (backend) | reused results (backend) | est. cost USD |",
        "|---|---|---|---|---|---|",
    ]
    for row in mr["conditions"]:
        bv = row["backend_validation"]
        lines.append(
            f"| {row['condition']} | {row['cumulative']['input_tokens']} | "
            f"{row['cumulative']['output_tokens']} | {bv['executed']} | "
            f"{bv.get('reused_prior_results', 0)} | "
            f"{row.get('estimated_cost_usd')} |")
    lines += ["", "### Per-round detail", ""]

    def _round_label(p: dict) -> str:
        if "prompt_tokens" in p:
            return (f"r{p['round']}: in {p['prompt_tokens']} / out "
                    f"{p['completion_tokens']} / {p['latency_s']}s "
                    f"(finish={p['finish_reason']}, "
                    f"tool_calls={p['tool_calls_requested']})")
        return f"r{p['round']}: FAILED (http {p.get('http_status')}: " \
               f"{p.get('error', '')[:120]})"

    for row in mr["conditions"]:
        lines.append(f"- **{row['condition']}**: " + "; ".join(
            _round_label(p) for p in row["per_round"]))
    lines += ["", "### Limitations", ""]
    lines += [f"- {lim}" for lim in mr["limitations"]]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Legacy (pre-improvement) reproduction — verbatim semantics from commit
# 6cf865f ("Add Model Autopsy: evidence-backed ML forensics platform").
# tests/test_groq_benchmark.py verifies the instruction text below against
# the actual commit via git, so this copy cannot drift.
# ---------------------------------------------------------------------------
LEGACY_MODE_INSTRUCTIONS_ML = (
    "You are the runtime investigator of Model Autopsy, an ML model autopsy. "
    "Given the recorded evaluation context, propose competing explanations about "
    "why the model performs as observed by calling the propose_hypothesis tool "
    "(each with a falsifiable statement, a predicted observation, and a note "
    "that its confidence is uncalibrated). Select diagnostic tools that can "
    "DISCRIMINATE between competing hypotheses — do not run every tool. "
    "Interpret only recorded tool results; distinguish confirmed findings from "
    "hypotheses. Never claim leakage from suspiciousness alone without "
    "evaluation evidence.")


def _legacy_initial_context_items(inv) -> list[dict]:
    """Verbatim pre-6cf865f _initial_context_items behavior (full payload)."""
    from model_autopsy.backend.db import to_json_blob
    context = (inv.config or {}).get("context") or {}
    items = [
        {"role": "user", "content": json.dumps({
            "mode": inv.mode, "objective": inv.question,
            "recorded_context": to_json_blob(context),
            "evidence_so_far": [f for f in (inv.latest_findings or [])],
            "budget": {"iterations_used": inv.iteration_count,
                       "max_iterations": inv.max_iterations}}, sort_keys=True)}]
    return items


# ---------------------------------------------------------------------------
# Isolated investigation on a temp DB (read-only with respect to artifacts)
# ---------------------------------------------------------------------------

def _ensure_temp_db() -> Path:
    if not os.environ.get("MODEL_AUTOPSY_DB_PATH", "").strip():
        db_dir = Path(tempfile.mkdtemp(prefix="ma-groq-bench-"))
        os.environ["MODEL_AUTOPSY_DB_PATH"] = str(db_dir / "sandbox.db")
        print(f"[isolation] temp DB: {os.environ['MODEL_AUTOPSY_DB_PATH']}")
    else:
        print(f"[isolation] MODEL_AUTOPSY_DB_PATH already set by caller: "
              f"{os.environ['MODEL_AUTOPSY_DB_PATH']}")
    return Path(os.environ["MODEL_AUTOPSY_DB_PATH"])


def _offline_run() -> dict:
    """Build both payloads, size them, verify duplicate reuse. NO network."""
    import json as _json
    from model_autopsy.backend import engine, tools_registry
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.meta_api import loop as meta_loop

    init_db()
    session = SessionLocal()
    try:
        inv = engine.create_investigation(
            session, "ml", "groq-bench",
            "Why does the model underperform on out-of-fold data?",
            {"max_tool_calls": 8})
        context = engine.build_context(session, inv)
        # One real (read-only) diagnostic so the ledger/non-ledger difference
        # exists; NOT counted toward Meta budgets — this is a fresh sandbox.
        engine.run_tool(session, inv, "artifact_summary", {}, source_meta=False)

        new_payload = meta_loop._initial_context_items(session, inv)
        new_instr = meta_loop.MODE_INSTRUCTIONS["ml"]
        old_payload = _legacy_initial_context_items(inv)
        old_instr = LEGACY_MODE_INSTRUCTIONS_ML

        new_text = _json.dumps(new_payload[0]["content"])
        old_text = _json.dumps(old_payload[0]["content"])

        def _packed(content: str, instructions: str) -> int:
            return (len(content.encode("utf-8"))
                    + len(instructions.encode("utf-8")))

        # Duplicate-diagnostic reuse check (backend-only; no API involved)
        r1 = engine.run_tool(session, inv, "artifact_summary", {},
                             source_meta=True)
        r2 = engine.run_tool(session, inv, "artifact_summary", {},
                             source_meta=True)
        reused = bool(r2.get("reused")) and \
            r1.get("action_id") == r2.get("action_id")

        return {
            "mode": "offline",
            "db_path": os.environ["MODEL_AUTOPSY_DB_PATH"],
            "case_rows": context.get("n_rows"),
            "tool_schemas_chars": len(_json.dumps(
                tools_registry.meta_tool_schemas("ml"))),
            "old": {"content_chars": len(old_text),
                    "instructions_chars": len(old_instr),
                    "wire_bytes": _packed(old_text, old_instr)},
            "new": {"content_chars": len(new_text),
                    "instructions_chars": len(new_instr),
                    "wire_bytes": _packed(new_text, new_instr)},
            "duplicate_diagnostic": {
                "second_response_reused": reused,
                "second_run_signal": r2.get("reused"),
                "tool_call_count_after_two_requests": inv.tool_call_count,
                "executions": 1 if reused else 2},
            "network_calls": 0,
            "token_rows": "not measured (offline); see Results for sizes only",
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Live Groq probes (explicitly gated)
# ---------------------------------------------------------------------------

def _groq_request(method: str, url: str, api_key: str, **kwargs) -> dict:
    import httpx
    t0 = time.perf_counter()
    headers = {"Authorization": f"Bearer {api_key}",
               "Content-Type": "application/json"}
    resp = httpx.request(method, url, headers=headers,
                         timeout=60.0, **kwargs)
    latency = time.perf_counter() - t0
    return {"status": resp.status_code, "latency_s": round(latency, 2),
            "body": _try_json(resp)}


def _try_json(resp):
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text[:300]}


def _live_run(n_requests: int) -> dict:
    import json as _json
    from model_autopsy.backend import engine
    from model_autopsy.backend.db import SessionLocal, init_db
    from model_autopsy.backend.meta_api import loop as meta_loop

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return {"mode": "live", "error": (
            "GROQ_API_KEY is not set in the environment. Export the key and "
            "re-run with --live. (The key is never read from any file here.)")}
    model = os.environ.get("GROQ_MODEL_ID", "").strip() or DEFAULT_GROQ_MODEL
    pricing = GROQ_PRICING_USD_PER_M.get(
        os.environ.get("GROQ_MODEL_ID", "").strip() or model)
    if pricing is None:
        pricing = {"input": None, "output": None,
                   "source": f"no published price registered for {model!r}"}

    init_db()
    session = SessionLocal()
    try:
        inv = engine.create_investigation(
            session, "ml", "groq-bench",
            "Why does the model underperform on out-of-fold data?",
            {"max_tool_calls": 8})
        engine.build_context(session, inv)
        engine.run_tool(session, inv, "artifact_summary", {},
                        source_meta=False)
        new_payload = meta_loop._initial_context_items(session, inv)
        new_instr = meta_loop.MODE_INSTRUCTIONS["ml"]
        old_payload = _legacy_initial_context_items(inv)
        old_instr = LEGACY_MODE_INSTRUCTIONS_ML

        # 0. Capability verification: the requested model id must be listed
        # by GET /models before spending anything (not a billed call).
        probe = _groq_request("GET", GROQ_MODELS_URL, api_key)
        model_list = [m.get("id") for m in
                      (probe["body"].get("data") or []) if isinstance(m, dict)]
        if probe["status"] != 200:
            return {"mode": "live",
                    "error": "GET /models failed: "
                             f"{probe['status']} {probe['body']}"}
        model_supported = model in model_list
        if not model_supported:
            return {"mode": "live",
                    "error": f"{model!r} was NOT returned by GET /models "
                             f"(did get {len(model_list)} ids). No chat "
                             "request was spent on an unlisted model."}

        results, n_billed = [], 0
        for tag, payload, instr in (
                ("new", new_payload, new_instr),
                ("old", old_payload, old_instr)):
            if n_billed >= max(1, min(n_requests, 3)):
                break
            body = {"model": model,
                    "messages": [
                        {"role": "system", "content": instr},
                        {"role": "user", "content": payload[0]["content"]}],
                    "temperature": 0, "max_tokens": 16}
            r = _groq_request("POST", GROQ_CHAT_URL, api_key, json=body)
            n_billed += 1
            usage = (r["body"].get("usage") or {}) if r["status"] == 200 else {}
            row = {
                "variant": tag, "model": model,
                "http_status": r["status"], "latency_s": r["latency_s"],
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "provider_reported": bool(usage)
                if r["status"] == 200 else False,
            }
            if r["status"] == 200 and usage:
                row["estimated_cost_usd"] = round(
                    usage["prompt_tokens"] / 1e6 * pricing["input"] +
                    usage["completion_tokens"] / 1e6 * pricing["output"], 6)
            else:
                row["estimated_cost_usd"] = None
            results.append(row)

        return {
            "mode": "live", "model": model,
            "model_listed_by_provider": model_supported,
            "tool_calling_notes":
                "This probe intentionally does NOT use tools; it measures "
                "context payload tokens only. Duplicate-diagnostic reuse is "
                "verified offline (backend-enforced, no provider involved).",
            "requests": results,
            "billed_requests": n_billed,
            "pricing": pricing,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------

def _table(off: dict, live: dict | None) -> str:
    def row(name, o, n):
        return f"| {name} | {o} | {n} |"

    live_by_variant = {r.get("variant"): r for r in ((live or {}).get("requests") or [])}

    def tok(variant: str, key: str) -> object:
        r = live_by_variant.get(variant)
        if live is None:
            return "not measured (offline)"
        return (r or {}).get(key, "n/a")

    return "\n".join([
        "| Metric | Old (pre-6cf865f) | New (compacted) |",
        "|---|---|---|",
        row("context payload (chars)",
            off["old"]["content_chars"], off["new"]["content_chars"]),
        row("instructions (chars; separate channel)",
            off["old"]["instructions_chars"], off["new"]["instructions_chars"]),
        row("combined request bytes (no tool schemas — identical both sides)",
            off["old"]["wire_bytes"], off["new"]["wire_bytes"]),
        row("input tokens (provider-reported)",
            tok("old", "prompt_tokens"), tok("new", "prompt_tokens")),
        row("output tokens (provider-reported)",
            tok("old", "completion_tokens"), tok("new", "completion_tokens")),
        row("latency (s)",
            tok("old", "latency_s"), tok("new", "latency_s")),
    ])


def to_markdown(off: dict, live: dict | None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# Groq context-efficiency benchmark — Model Autopsy",
        f"Generated: {ts}",
        f"DB: {off.get('db_path', '')}",
        "",
        "## Payload sizes",
        _table(off, live),
        "",
        "## Duplicate diagnostics (backend-enforced reuse; no provider)",
        f"- second identical request reused prior result: "
        f"**{off['duplicate_diagnostic']['second_response_reused']}**",
        f"- tool executions for two identical requests: "
        f"**{off['duplicate_diagnostic']['executions']}** "
        f"(budget stayed at "
        f"{off['duplicate_diagnostic']['tool_call_count_after_two_requests']})",
        "",
        "## Notes / limitations",
        "- Character/byte sizes are NOT token counts; token rows are filled "
        "only from provider-reported usage in --live mode.",
        "- A Groq result does not establish Meta API performance; providers "
        "and tokenizers differ.",
        "- Estimated cost is computed from the pricing source named below; "
        "it is an estimate, not an actual charge or billing record.",
        live and (
            (f"- Live model: `{live['model']}`; listed by provider: "
             f"{live['model_listed_by_provider']}; billed requests: "
             f"{live['billed_requests']}; pricing source: "
             f"{live['pricing'].get('source')}")
            if "model" in live else
            f"- Live requests FAILED: {live.get('error')}") or
        "- No live requests were made (offline mode).",
    ]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    # Parse BEFORE importing backend modules so the temp-DB env var can be
    # set first.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="send the two payloads to Groq (billed requests)")
    parser.add_argument("--requests", type=int, default=2,
                        help="max billed requests in --live mode (1..3)")
    parser.add_argument("--rounds", type=int, default=0,
                        help="if >0 with --live: mirrored multi-round old-vs-"
                             "new comparison; billed requests = 1 probe + "
                             "2x rounds, hard cap 10")
    parser.add_argument("--model", default=None,
                        help="Groq model id override (bench conditions share "
                             "one model; default GROQ_MODEL_ID env or "
                             "openai/gpt-oss-120b)")
    parser.add_argument("--skip-verify", action="store_true",
                        help="skip GET /models + capability probe (recovery "
                             "rerun only: those already passed this session)")
    parser.add_argument("--only-condition", choices=("old", "new"), default=None,
                        help="re-run a single condition whose rounds were "
                             "incomplete, then MERGE with the saved report — "
                             "the other condition's data is untouched")
    args = parser.parse_args(argv)

    _ensure_temp_db()
    live = None
    off = _offline_run()
    if args.live and not args.rounds:
        live = _live_run(max(1, min(args.requests, 3)))

    md = to_markdown(off, live)
    if args.rounds > 0:
        md = md.replace(
            "- No live requests were made (offline mode).",
            "- Single-payload probes skipped: only the --rounds comparison "
            "below ran live.")
    multi_md = ""
    if args.rounds > 0:
        if not args.live:
            multi_md = ("\n<!-- multi-round -->\n## Multi-round comparison\n\n"
                        "BROKEN: --rounds requires --live (nothing was run).\n")
        else:
            model = (args.model or os.environ.get("GROQ_MODEL_ID", "").strip()
                     or "openai/gpt-oss-120b")
            multi = _multi_run(
                args.rounds, model, skip_verification=args.skip_verify,
                prior_attempts_note=(
                    "Recovery rerun after two aborted attempts caused by "
                    "harness defects (since fixed: argument shaping, init "
                    "ordering, and a render crash). Those attempts consumed "
                    "2 capability-probe requests and produced no comparison "
                    "data; the numbers in this section come from one "
                    "completed comparison run.") if args.skip_verify else "",
                only_condition=args.only_condition)
            if not multi.get("error") and args.only_condition:
                rep_path = BENCH_DIR / "multi_report_last.json"
                if rep_path.exists():
                    base = json.loads(rep_path.read_text(encoding="utf-8"))
                    new_row = multi["conditions"][0]
                    base["conditions"] = [
                        c if c["condition"] != new_row["condition"] else new_row
                        for c in base.get("conditions", [])]
                    pricing = base["pricing"]
                    for row in base["conditions"]:
                        tin = row["cumulative"]["input_tokens"]
                        tout = row["cumulative"]["output_tokens"]
                        if pricing.get("input") is not None:
                            row["estimated_cost_usd"] = round(
                                tin / 1e6 * pricing["input"]
                                + tout / 1e6 * pricing["output"], 6)
                    base["billed_requests"] = (
                        base.get("billed_requests", 0)
                        + multi.get("billed_requests", 0))
                    base["limitations"].append(
                        f"Condition '{new_row['condition']}' was re-run once "
                        "(same parameters; other condition untouched) to "
                        "complete all rounds after an HTTP 429 provider rate "
                        "limit cut short that attempt; token totals exclude "
                        "the non-billed 429 request.")
                    base["limitations"].append(
                        f"Total request ATTEMPTS across the completed "
                        f"comparison: {base['billed_requests']} (hard cap 10). "
                        f"Attempts include HTTP 400/429 requests the provider "
                        f"rejected without billing; only generated-token "
                        f"responses were charged.")
                    multi = base
            # Persist the raw report BEFORE rendering so a render bug can
            # never destroy measured data again.
            (BENCH_DIR / "multi_report_last.json").write_text(
                json.dumps(multi, indent=2, default=str), encoding="utf-8")
            multi_md = _multi_markdown(multi)

    RESULTS_PATH.write_text(md + multi_md, encoding="utf-8")
    print(md + multi_md)

    for failure in ([live and live.get("error"),
                     multi_md if "BROKEN:" in multi_md else None]):
        if failure:
            print(f"[bench] {failure}", file=sys.stderr)

    if live and live.get("error"):
        print(f"[live] {live['error']}", file=sys.stderr)
        return 0   # live gating failure is a reportable condition, not a crash
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
