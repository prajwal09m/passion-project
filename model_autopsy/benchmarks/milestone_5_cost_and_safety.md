# Milestone 5 — Cost & Safety

## Pricing basis (dev.meta.ai pricing page, read 2026-11-01)

`muse-spark-1.3` Standard: input $1.25/1M, cached input $0.15/1M,
output $4.25/1M; no long-context premium; 3,000 RPM / 4M TPM.
Contributor variant ($0.10/$0.20) is NOT in use — the backend default
model id is `muse-spark-1.3`.

## Pilot budget (hard caps, pre-request enforced)

3 rounds / 6 experiments / 12 attempts (incl. retries+repairs) /
50,000 provider tokens / $0.40 (authorized; raised from $0.25). Reference: preserved phase_d run
(6 requests, ~25.5k input mostly cached, ~7.1k output) cost ≈ $0.04.
Preflight projection for the turbine brief: worst case (no cache)
≈ $0.06–0.21 — within cap with margin; typical (cached) ≈ $0.04.

## Actuals (completed pilot, 2026-11-01)

Attempt 1 (infra failure, preserved): 7 attempts, 36,663 tokens,
$0.0613. Attempt 2 (completed, `live-140167117ef5`): 7/12 attempts,
28,192/50,000 tokens (17,446 cached), $0.0308 — combined $0.0921,
within the $0.40 authorization. No cap breached.

## Safety rules implemented

- Key from env only; never printed, logged, copied to fixtures,
  reports, or run dirs (run dirs contain DB + JSONs only).
- No verbose HTTP logging; request logs carry metadata, not secrets.
- 429 → honor `retry-after`, count the attempt, no infinite retry.
- Incomplete responses preserved + classified, not repaired away.
- No auto-repeat, no 7-project sweep, no comparisons, no second run —
  one CLI invocation, one investigation. Anything further needs
  explicit authorization.
- UI cannot spend: no POST /api/live/runs exists; dashboard is
  read-only over preserved runs.
- Preflight gates: audit green, key present (boolean only), model +
  endpoint verified, artifact readable, cost projection ≤ cap,
  preservation dir writable. Any failure refuses launch (exit 2)
  before any request.

## Credential handling in tests

All 15 live tests run keyless with mocked transport; the suite asserts
no provider keys in the test env. The pilot check reads only key
presence — value never leaves the process except as the auth header.
