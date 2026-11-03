# Milestone 5 — Limitations (honest, binding)

1. **One run proves nothing general.** A single successful pilot is
   preliminary evidence only; it does not show Meta investigates
   unfamiliar systems in general, across tasks, or better than
   alternatives. No generalization claim is made here.
2. **An API call is not an investigation.** Spending budget and
   returning text proves traffic, not reasoning. Only the frozen
   evidence trail + independent score + blind review speak to quality.
3. **Deterministic ≠ live.** The 0.945 baseline and any live score
   measure different things and are never ranked or averaged.
4. **Recovery is partial.** An interrupted run (crash/kill) leaves a
   run dir WITHOUT a manifest — detectable (no manifest = not
   finalized) but not resumable; reruns mint new IDs rather than
   continuing. Repair budget counts against attempts by design.
5. **No raw HTTP bodies retained.** Recorder persists DB events
   (texts, usage, ids) but not wire payloads — a deliberate
   credential-safety trade-off that limits byte-level replay.
6. **Manifest-last atomicity is crash-scoped.** Tmp-file + rename
   protects against partial writes, not against process kill between
   artifact writes; the checklist exposes exactly what is missing.
7. **Synchronous API reads.** The read-only live endpoints serve the
   backend process; no streaming, timeout, or cancellation yet.
8. **Single-model, single-project, single-budget.** Multi-model,
   multi-project, Full/Delta, and consistency studies are explicitly
   out of scope without fresh authorization.
9. **Human review pending.** Until a reviewer acts, the review status
   is pending — reported as such, never filled in.
10. **Attempt 1 failed on infrastructure, not on science.** The first
    pilot invocation crashed in the driver's report-finalization path
    (`hypotheses_proposed -> complete`); its spend ($0.061) and
    artifacts are preserved alongside the completed run, and the fix
    (legal FSM walk + regression test) is documented in the results
    doc. Combined spend stayed within $0.40; no further runs are
    authorized.
