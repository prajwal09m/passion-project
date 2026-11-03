# Milestone 4 — Security Model & Isolation

## Threat posture

Benchmark projects are treated as untrusted content. The v1 design
eliminates the largest risks by construction: fixtures are DATA
(CSV + declarative spec + prose brief). No benchmark-supplied code
exists, is imported, or is executed — the only code that runs is the
registered deterministic diagnostic suite (read-only, in-process).

## Controls

1. **No arbitrary execution**: the runner never imports or execs
   project code; `run_fn`s are internal diagnostics.
2. **Credential isolation**: `runner.run_all` refuses to start when
   `MODEL_API_KEY` or `GROQ_API_KEY` is set (tested); provider clients
   are never imported by the eval path; `.env` is never copied into
   run dirs (run dirs contain only DB, JSONs, manifest).
3. **Ground-truth confinement**: truth file outside the investigator
   tree + lexical audit + source-level test (runner never references
   ground truth).
4. **Result integrity**: run dirs are never overwritten (existing ID =
   hard error, tested); reviews are append-only (existing review =
   hard error, tested); frozen `phase_d_*` dirs gain no files (tested:
   live-dir count pinned at 7).
5. **Credential redaction inherited**: key-from-env-only, never
   stored/logged/returned (M2/M3 protections unchanged).

## Honest limitations

- In-process diagnostics are NOT a sandbox boundary: a malicious CSV
  is inert, but this must not be described as sandboxing. If future
  benchmarks include executable project code, a real container
  boundary is required first.
- The lexical audit cannot catch semantic hints (documented).
- API-triggered runs execute synchronously in the server process
  (bounded: ≤8 projects, seconds each); no timeout/cancellation yet —
  do not expose to untrusted callers beyond loopback dev origins.
