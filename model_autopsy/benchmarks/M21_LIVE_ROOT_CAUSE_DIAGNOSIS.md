# M21 Live Root-Cause Diagnosis — Why `m21-music-01` Did Not Investigate

Diagnosis only. No code, tests, prompts, docs (other than this file),
config, or artifacts were modified; no live calls were made; nothing
was reset, cleaned, or overwritten. Git baseline recorded before and
verified after (§10).

## 1. Executive summary

The investigator did nothing — zero hypotheses, zero tool calls in its
single round — and the orchestration layer accepted that nothing as a
completed investigation. Two facts combine: (a) the model returned a
one-line deviation note with no action (**strongly supported**,
intent unprovable from preserved evidence); (b) the system's
done-conditions equate "valid summary" with "finished investigation"
and record total inaction as `completed-turn` with
`incomplete_progression:false` (**confirmed** by code and events).
The repair pipeline then converted the empty prose into a valid,
consistent, honest summary, which *shortened* the investigation: had
the repair failed, the driver would have run further rounds. The most
important lifecycle failure is the done-condition, because it is the
part the system controls.

## 2. M21 execution reconstruction (observed facts)

Source: `live_runs/m21-music-01/` (`events_dump.json` 19 events,
`assistant_messages.jsonl`, `usage.jsonl`, `manifest.json`,
`eval_report.json`, `scorecard.json`, `m21-music-01.launch.log`).

1. Asked: `eval_music` — "Are top results relevant for every catalog
   slice?" (ranking, black-box `rank-lgb`, P@K per slice). Neutral
   recon brief + 5 sample rows + full tool contract in the request.
   Selection brief top pick: `artifact_summary` (`events_dump.json`
   seq 3; `planning.py:61-68` first-turn starters).
2. Received: hypotheses roster (empty), findings (none), ledger
   (empty), budget (3/6/12/$0.65), tool schemas incl.
   `propose_hypothesis` (`tools_registry.py:102`) and diagnostics.
3. Returned (round 1, `resp_6ae899ba53`, 0 tool calls, 5598 in / 2000
   out + 1300 reasoning tokens): "Deviating from the brief's low-value
   generic checks because they don't measure P@K per slice needed to
   test slice parity." No hypotheses, no calls, no decline reason.
4. Orchestration: `loop.py:751` (`if not calls: break`) ended the
   round loop. No wrapup was sent (gate `loop.py:206-210` requires
   near-empty budget or last round; neither held). No decision nudge
   (gate `loop.py:859` requires newly proposed hypotheses; zero
   existed). Summary invalid (`prose_without_block`, eligible) → one
   repair → valid + all 10 consistency gates passed → provenance
   `model_repaired` (the repaired text honestly reports nothing
   recorded; 251 chars, fully preserved in the event head).
5. Terminated: `driver.py:235`
   (`if not turn.get("tool_calls") and summary.get("valid"): break`)
   broke the investigation loop after turn 1 of 3. No stall break, no
   cap break (spend $0.020448, 3.1% of cap). Reservation declined,
   skeptic 0 challenges, verification skipped, contract `unresolved`.
6. Decision record: `no-diagnostic-no-reason`, 0 new hypotheses,
   `incomplete_progression:false`, outcome `completed-turn`.

Stopping condition that actually fired: the valid-summary break
(`driver.py:235`; same shape in `resume.py:256`).

## 3. Investigator execution path (supposed vs actual)

| Stage (code) | Supposed | Actual in M21 | Blocking condition met? |
|---|---|---|---|
| Recon `driver.build_live_context` | neutral brief + schema | done (seq 2) | — |
| Brief `planning.plan_next` | top diagnostic | `artifact_summary` (generic starter, no hyps yet) | model dismissed it — arguably correctly |
| Round `loop.run_meta_turn` | propose 2–3 hyps, run 1 diagnostic | text only, 0 calls → `loop.py:751` break | no enforcement exists for this shape |
| Wrapup `loop._wrapup_item` | steer empty rounds | not sent (gate unmet) | gate never considers "empty round" |
| Nudge `loop.py:847-880` | force decide-or-act | not sent (needs new hyps) | zero-action round invisible to it |
| Decision `loop.py:1140-1195` | flag incomplete work | `completed-turn`, incomplete **false** (`:1195` keys on `_new_total > 0`) | total inaction explicitly marked complete |
| Driver loop `driver.py:200-236` | continue until evidence/caps | broke on valid summary + no calls (`:235`) | repair-made-valid triggered it |
| Skeptic/verify/resolve | adversarial + contract | ran correctly on empty state; `unresolved` | — (these stages are exonerated) |
| Report/adapter | provenance + consistency | correct (`model_repaired`, gates pass) | — (exonerated) |

## 4. Root-cause hypothesis assessment

- **A. Prompt/instruction failure — plausible but unproven.**
  The ml instructions (`loop.py:73-100`) do order propose-then-diagnose
  and the brief demands explicit deviation reasons, but nothing
  *requires* any action: every steering mechanism is conditional on
  partial progress (new hyps, last round, low budget). The M20 contract
  (`loop.py:31-60`) adds summary-format emphasis to the system prompt;
  whether that anchored a summarize-instead-of-act response cannot be
  tested from one run (M19 ran under the older, shorter prompt and
  acted: 3 calls in round 1). No A/B exists.
- **B. Context failure — ruled out as blocker.** Recon context,
  sample rows, methodology, and tool contract were delivered (seq 2,
  `preflight.artifact_readable`). The model's own sentence
  demonstrates project understanding (P@K per slice, slice parity).
- **C. Tool-interface failure — not supported as blocker; brief
  quality plausible contributing.** Schemas are explicit
  (`tools_registry.py:102-135`); the identical interface produced
  M19's 3-call round. Contributing nuance: the first-turn brief can
  only recommend generic starters (`planning.py:61-68`), and
  `artifact_summary` genuinely does not measure P@K per slice — the
  model's stated objection has merit. But merit does not explain
  calling *nothing* (not even `propose_hypothesis`, which costs no
  experiment budget per `accounting.py` M18 rules).
- **D. Model behavior — strongly supported (intent unprovable).**
  Evidence for understanding + deliberate rejection: correct
  methodological vocabulary, explicit deviation rationale. Evidence
  for abandonment over confusion: it named the right measurement yet
  invoked no tool and proposed no hypothesis. Confirmed intent is
  impossible: 2024 reasoning tokens were spent but reasoning content
  is not preserved by the recorder (only text + usage), so "decided to
  stop" vs "failed to emit calls" cannot be distinguished. Hence
  strongly supported, not confirmed.
- **E. Orchestration/state failure — confirmed (mechanism).**
  Three compounding permissive stops, all cited above: `loop.py:751`
  ends the round on silence; `loop.py:1195` marks total inaction
  complete; `driver.py:235` ends the investigation on a valid summary
  with zero evidence. Perverse interaction (confirmed by code path):
  repair success *caused* earlier termination — a failed repair would
  have left the summary invalid and the driver would have run rounds
  2–3. No tool-call opportunity was *lost* (parsing was correct:
  `n_tool_calls:0` matches the response); opportunities were
  *declined by the model and accepted by the loop*.
- **F. Scenario-design failure — not supported.** Identical scenario
  produced a real M19 investigation (2 hypotheses + diagnostics,
  same brief shape); the scorer measurably punished emptiness
  (discovery 0.0, `inconclusive`). The scenario discriminates; the
  investigator did not participate.

**Primary root cause:** combined D + E — model silent non-action met
with orchestration that certifies inaction as completion. **Most
important single failure:** E's done-condition, because it is
system-controlled and it converts any future silent model into the
same empty-but-clean outcome. **Unknowns:** model intent (reasoning
unpreserved); whether the M20 contract text contributed (needs live
A/B, cannot be resolved offline).

## 5. Offline-test coverage audit

Established by the suite (635 green): classification, repair
mechanics, consistency gates, fallback composition, provenance
marking, budget accounting, dedup — all through mocked providers.
**Not established:** every mock emits round-1 tool calls, so the
"model does literally nothing" path is untested end to end — no test
asserts the decision record or driver continuation for a zero-call,
zero-hypothesis turn; `incomplete_progression` is only ever true when
hypotheses exist (M19 decline tests). The suite verifies *output
handling*, never *investigative progress*: a turn can score "completed"
with nothing done, and no test forbids it. The evaluation rewards
reporting validity (adapter/scorer shape) while the loop rewards
summary validity over evidence — both incentives point at paperwork,
neither at work.

## 6. Confirmed vs unresolved

Confirmed: event sequence; zero-action response content; three
permissive stops with line refs; repair-success-shortens-run
interaction; M19 contrast (same scenario acted); scorer punishment.
Unresolved: why the model stopped (intent); M20-contract influence;
how often silence recurs (n=1); whether rounds 2–3 would have
recovered the run (driver never tried).

## 7. Prioritized recommendations (no implementation)

**Necessary:**
1. *Evidence-floor done-condition* (`driver.py:235`,
   `resume.py:256`): do not break on valid summary when the turn (and
   investigation) produced zero tool calls and zero hypotheses —
   continue rounds. Tests offline with a zero-action mock asserting
   rounds continue; live re-test needs authorization. Trade-off: a
   truly stuck model burns attempts — bounded by existing caps.
2. *Flag total inaction* (`loop.py:1188-1195`): `incomplete_progression`
   must be true when a turn executes nothing and proposes nothing,
   regardless of hypothesis delta. Offline-testable today.
3. *Zero-action nudge* (`loop.py:847-880`): extend the decision prompt
   to rounds ending with no calls at all, not just post-hypothesis
   rounds. Offline-testable; slight token cost per occurrence.

**Useful:** first-turn brief ranking that surfaces the scenario's
discriminating diagnostic (`ranking_slice_diagnostics`) instead of
only generic starters (`planning.py:61-68`); wrapup trigger on empty
rounds; preserve reasoning-item content in `recorder.py` (closes the
intent unknown; watch payload size).

**Optional:** scorer weight review (discovery already 0.0 — no change
needed now); live A/B of contract-length influence (requires
authorization, low priority).

## 8. Proposed offline validation plan

Add zero-action mocks across `run_meta_turn` + driver loop: assert
(1) rounds continue past an empty round-1, (2) decision marks
incomplete, (3) nudge fires, (4) eventual honest stop still occurs at
caps, (5) M19/M20/M21 suites stay green unmodified. All deterministic,
no provider.

## 9. Live-testing requirements and risks

Requires explicit authorization (same envelope: 1 run, eval_music,
3/6/12/$0.65). Risks: another silent model burns the run with nothing
new learned — mitigate by asserting the offline plan first and
pre-registering silence itself as themeasurable outcome. Reasoning
preservation should land before the next run so intent is observable.

## 10. M22 readiness assessment

M22 must not start until: the evidence-floor done-condition and
inaction flag are implemented + offline-proven (recommendations 1–2),
because otherwise any silent model reproduces m21-music-01 exactly.
The reporting pipeline (M20/M21) is exonerated and needs no rework;
the investigation loop is not. Git status after this task matches the
recorded baseline: no source, test, config, doc (save this file), or
artifact modified; no live calls made.
