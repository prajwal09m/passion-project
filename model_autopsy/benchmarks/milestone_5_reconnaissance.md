# Milestone 5 — Reconnaissance (read-only, zero live requests)

Date: 2026-11-01. No API calls sent (pricing sourced from public docs
via web research; usage figures below are from preserved historical
run artifacts). No historical artifact modified.

## 1. Existing Meta API integration (verified current)

- `backend/meta_api/client.py` (198 lines): Responses API adapter.
  `POST {base}/responses` (`https://api.meta.ai/v1` + `/responses`),
  bearer `MODEL_API_KEY`, flat `function` tools, `function_call` items
  with JSON-string args, `function_call_output` matched by `call_id`.
  Bounded retries (408/429/5xx, max 3, backoff, Retry-After honored);
  failures → `MetaUnavailable(status_code)` — never inferred from text.
  `usage()` flattens `input_tokens`, `output_tokens`,
  `input_tokens_details.cached_tokens`, reasoning tokens; numbers only.
- `backend/meta_api/loop.py` (533 lines): `run_meta_turn(session, inv,
  max_rounds=3)` — full-context first turn, `previous_response_id`
  chaining after, one full-context fallback on chain-state errors
  (400/404/409/410/413 only), per-call tool validation via allowlist,
  real execution + evidence recording, `function_call_output`
  round-trips, verbatim message persistence, one bounded summary-repair
  attempt, `meta_usage` rollup event (rounds, api_calls, api_attempts,
  latency, tokens, tool counts, context mode). `MODE_INSTRUCTIONS["ml"]`
  is a domain-independent forensic method (competing hypotheses,
  discriminate, demote-on-contradiction, cite action ids, fenced
  `investigation_summary` JSON). No key ever leaves the backend.
- Credential loading: `config.meta_api_key()` from `MODEL_API_KEY` env
  (`.env.example` template, never committed); `GET /models` no-spend
  connection test; Settings page shows key-configured only.
- Live-campaign precedent: `phase_d_meta_live_*` dirs preserve
  `responses.jsonl`, `assistant_messages.jsonl`, `usage.jsonl`,
  `repairs.jsonl`, `events_dump.json`, `sandbox_final.db`,
  `run_manifest.json` with sha256 artifact map + required-evidence
  checklist + atomic finalization. This is the preservation pattern
  to reuse.

## 2. Existing research-agent capabilities

Deterministic lab (`research/lab.py`, 11 stages), hypothesis cards with
evidence-gated transitions (`research/hypotheses.py`), heuristic
experiment design + copy-on-read workspaces (`research/experiments.py`),
independent checklist review (`research/verification.py`), M4 eval
package (8 unfamiliar projects, sealed truth, leakage audit, rubric-v2
scorer, repeatable runner, blind review). M4 deterministic baseline:
mean overall 0.945 (official run `eval-6247993ca658`).

## 3. Investigator access to projects and tools

`POST /api/investigations` (mode `ml`, optional `project_id`) →
`POST .../context` (`engine.build_context`: project-adapter branch or
legacy artifact branch) → `POST .../meta-turn` (bounded Meta loop;
tool schemas from `tools_registry.meta_tool_schemas(mode)`; budgets
3 iterations / 12 tool calls enforced). TO VERIFY in implementation:
that the Meta tool allowlist exposes the forecasting/ranking diagnostics
the pilot needs, and how an eval project (spec-direct, not registered
in the `projects` registry) gets its context/Meta brief without
leaking mechanism text.

## 4. Ground-truth protection (current state)

M4: investigator dir (`tests/fixture_eval/investigator/`, CSVs +
briefs) vs sealed `ground_truth_eval.json` outside it; lexical audit
(9 files / 17 tokens, green) at `GET /api/eval/separation-audit`;
runner never references ground truth (source-tested). Gaps for live
use: brief text itself will be sent to Meta (by design — it is the
task, not the answer); must audit that briefs + spec fields contain no
mechanism words, and that tool results / error messages / DB context
dumps never echo truth (truth never enters the investigation session,
so the risk is confined to static strings — verify by audit + review).

## 5. Experiment results → investigator

`engine.run_tool` validates → executes → records Action → returns
result packet; loop serializes truncated-valid-JSON packets as
`function_call_output`. Dedup: repeats return prior results.

## 6. History persistence

SQLite (`db.py`): investigations/hypotheses/actions/events; full Meta
request/response/usage/repair events; `validate_structured_summary`
recorded valid-or-invalid (never discarded); phase_d pattern adds
JSONL response/usage/assistant-message logs + manifest + sandbox DB.

## 7. Final-report scoring

M4 `scorer.py`: dimensions A–F with weights (0.30/0.25/0.15/0.15/
0.05/0.10), verdict taxonomy
(correct/partial/incorrect/unsupported/inconclusive/correct-null),
mechanism bands on attached numbers, false-positive penalties. Works
on any `{confirmed_findings, experiments[].numbers, executive_summary}`
report — Meta's `engine.build_report` output is compatible pending an
adapter check (finding titles come from Meta prose, not triage cards).

## 8. Missing functionality (to implement, offline-testable)

1. Live-investigation driver: create investigation from eval project,
   run recon → N Meta turns → freeze report → score (new module,
   reuse `run_meta_turn`, M4 `runner`/`scorer`).
2. Meta-brief builder for eval projects (neutral identifier, no
   mechanism words; verify tool allowlist coverage).
3. Budget governor: hard caps (12 attempts / 50k provider tokens /
   $0.40 authorized, raised from $0.25 / 3 rounds / 6 experiments) enforced pre-request, not
   post-hoc; 429 respected; attempts counted incl. retries+repairs.
4. Live-run recorder (phase_d pattern): requests, responses, ids,
   usage, repairs, events dump, manifest, atomic finalize, unique dir.
5. Meta-report → M4-scorer adapter + blind-review package wiring.
6. Dashboard live view (status/usage/evaluation/integrity) behind a
   clear live-vs-simulation label.
7. ≥20 offline tests with mocked provider responses.

## 9. Expected API usage and cost (pricing: dev.meta.ai pricing page)

Standard `muse-spark-1.3`: input $1.25 / 1M, cached input $0.15 / 1M,
output $4.25 / 1M; no long-context premium; rate limits 3000 RPM /
4M TPM. Historical reference (preserved `usage.jsonl`, 6 requests):
~25.5k input tokens (≈80% cached), ~7.1k output → ≈ $0.04–0.06.
Pilot projection (3 rounds, ≤6 experiments, ≤12 attempts): worst case
50k total tokens ≈ $0.06–0.21 even if nothing cached — within the
$0.40 cap with margin. Preflight must compute this from the actual
brief size before the first request; stop + request authorization if
projection exceeds $0.40.

## 10. Proposed pilot execution sequence

1. Offline: implement driver + governor + recorder + adapter + view +
   mocked tests; full suite + tsc/build green; docs.
2. Preflight: separation audit green; caps verified; model/endpoint/key
   verified; preservation dir ready; cost projection ≤ $0.40.
3. Pilot project: **eval_turbine** (forecasting; missed clean level
   shift; tempting-but-wrong leakage explanation tests attribution;
   single-diagnostic evidence; neutral name; mechanism never discussed
   with Meta). Presented under neutral run/investigation identifiers.
4. One investigation, ≤3 rounds / ≤6 experiments / ≤12 attempts.
   Freeze report → independent M4 scoring → blind-review package
   (review pending, never fabricated).
5. Document results with the four-way separation (deterministic
   baseline / live result / automated score / human review).
