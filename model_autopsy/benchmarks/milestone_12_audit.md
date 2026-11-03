# Milestone 12 Audit — Continuous Research Laboratory

## Verdict: IMPLEMENTED, all gates pass.

## Persistence
File-backed projects (`backend/m12/projects.py`, atomic tmp+rename
writes): objectives, agenda, hypotheses, experiments, evidence,
decisions, unresolved, resource usage, checkpoints, idempotency
keys, history. States: active/paused/awaiting-approval/completed/
aborted. Application restart loses nothing (plain JSON on disk).

## Long-running investigations
Checkpoints capture resumable state; `record_experiment` is
idempotent on caller-supplied keys — a retried resume after a
crash reuses the original record and never double-counts
budget (tested).

## Follow-up research
Unresolved disagreements (M11) and unanswered agenda items flow
into project agendas as queued proposals with importance ×
info-gain / cost ranking. Proposals are data, not actions: the
scheduler only executes offline work; paid work parks in
awaiting-approval.

## Memory
`memory.py`: kind-tagged entries pinned to project+run. Transfer
guard tested: promotion to universal scope requires replications
in ≥2 distinct projects; single-project evidence is refused with
the gap named.

## Scheduling
`priority = importance × info_gain / cost`, budget-capped,
states queued/paused/completed/aborted/awaiting-approval. Paid
proposals without a human token are deferred, never run (tested
via API: paidX stays parked).

## Authorization
`authorization.py`: single-use human-minted tokens per scope;
`require()` enforced on the paid path. The UI never mints tokens.
No scheduler, retry, or resume path can self-authorize (no code
path calls `issue` except the human surface).

## Reproducibility
`snapshots` pin artifact SHA + package versions + result
summaries; grades exact/approximate/unreproducible with
instructions. Artifact mutation → unreproducible; version drift
→ approximate; replay match → exact (all tested).
