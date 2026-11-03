# Phase 6 — Final Meta readiness gate (2026-10-31)

Offline. No provider request, no credential access beyond presence checks.
No Meta inference has been run under the repaired harness.

## Gate checklist

| # | Gate | Evidence | Status |
|---|------|----------|--------|
| 1 | Full offline test suite passes | `model_autopsy/tests`: **189 passed, 0 failed** (includes 15 continuation-ID regressions, 17 meta-persistence, 7 groq-persistence, 6-dimension blind-artifact tests) | PASS |
| 2 | Groq infrastructure validation passes | validation3 `phase_d_groq_live_20261031T202441Z`: 15/15 billed, 0 failed, no stop; both runs summary-valid after 1 repair each; manifests finalized; all required evidence present; SHA-256 verified 16/16 artifacts; private per-run sandboxes; $0.00896 / 45,107 tokens (caps 25 / 120,000 / $0.50) | PASS |
| 3 | Final messages survive cleanup | validation3: turn2-final-repaired records 954/1,045 chars, finalized manifests, hashes verify | PASS |
| 4 | Complete summaries survive cleanup | post-repair valid summaries in repairs.jsonl + assistant record + report | PASS |
| 5 | Repair responses survive cleanup | repairs.jsonl per run, hashed in manifest | PASS |
| 6 | Usage records survive cleanup | usage.jsonl per attempt, ledger totals reconcile | PASS |
| 7 | Continuation IDs verified | 15 offline regression tests (original/repaired/missing/invalid/unavailable branches, both conditions) + per-turn continuation-state audit in report | PASS |
| 8 | All raw artifacts and manifests verify | validation3: every manifest digest recomputed OK; missing-evidence-never-invented unit tests | PASS |
| 9 | Blinded scoring packets can be generated | Demonstrated: PACKET-A/B built from recorder artifacts (no condition/billing leakage, leak-scan clean), scored 7/7 under frozen rubric v1, machine contract passes, sheets frozen with digests, condition key sealed and unopened | PASS |
| 10 | Credential security checks | `.env` git-ignored and untouched; nothing staged; no credential files tracked; pattern scans over validation2+validation3 trees, logs, reports: 0 hits; tests use dummy keys only; no values ever printed | PASS |
| 11 | Final benchmark protocol frozen | `phase_d_meta_protocol_revision_v2_2026-10-29.md` + RESULTS.md entry intact; harness changes are preservation-only (no condition/payload/budget changes) | PASS |

## Repair cycles used (max 3 authorized)

- Cycle 1 (offline, pre-Groq): shared-session `sandbox_final.db` pollution failed the secret-hygiene gate in full-suite order. Fix: per-run private sandbox sessions ported to the Groq harness (Meta-harness pattern), plus `turn2-final` staleness fix after validation2 exposed it live. Regression tests added (7 new: incomplete-1st/2nd, malformed summary, missing usage, commit failure, dump failure, post-repair final message). Full suite re-greened (189).
- Cycles 2–3: unused. validation3 passed on first attempt after the cycle-1 fixes.

## Residual risks (accepted, documented)

1. The Meta catch-all failure handler (`except Exception` → interrupted finalize) is validated in simulation only; the success path is byte-identical to the previously live-exercised flow.
2. Live Meta provider behavior (incomplete statuses at 2,000/1,200 tokens, real repair ids) is handled by the preserved v2 continuation logic, regression-tested offline against all branches.
3. Groq quality scores (7/7) describe honest abstentions, not billing evidence; they are not unblinded to conditions and no condition comparison is made.

## GO / NO-GO DECISION

**GO.** All eleven gates pass. The experiment is safe (frozen caps: 40 attempts / 150,000 tokens / $1.00 / stop after 3 consecutive 429s, Meta only, model muse-spark-1.3), correctly configured (existing secure credential mechanism, no credential exposure in any artifact), within budget (prior campaign peaked at $0.18; Groq analogues at <$0.01), and capable of preserving every result (demonstrated end-to-end on live provider traffic twice, with hash verification).

Authorized: exactly one final Meta campaign (2 pairs, Full-then-Delta each), then STOP for blinded scoring under the frozen protocol. No additional experiments without a new explicit approval.
