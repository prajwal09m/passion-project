# Milestone 8 — Reliable Structured Reporting (Workstream B)

## M7 failure, diagnosed

Three invalid structured summaries. Causes found in the audit: (1) every
repair **chained `previous_response_id`** from a response whose tool calls
were never answered, so the provider returned HTTP 400 ("No tool output
found") — the repair could never succeed; (2) no contract beyond the M6
validator (no version, no truncation or certainty gates); (3) repair
failure had no fallback — the turn ended with `valid: False` and prose.

## The fix (extends, not replaces, the M6 validator)

- **Versioned contract `m8-v1`** (`causal/report_schema.py`, a strict
  superset of the M6 checks): unknown `schema_version` rejected; conclusion
  truncation/oversize rejected; confidence 100 rejected as certainty;
  `supported` without cited basis actions rejected; unknown/duplicate
  hypothesis and experiment refs rejected; contradictory recommendations
  rejected; missing uncertainties warn without failing.
- **Fresh-context repair**: exactly one repair request, `previous_response_id`
  unset (the old chain is what died with 400s in production), carrying the
  validation errors plus recorded state, tools-free, budget-reserved.
- **Deterministic fallback** (`causal/fallback.py`): on repair failure the
  loop composes a conclusion STRICTLY from hypotheses, ran actions and the
  drafted report — labeled `deterministic-fallback` with version,
  provenance, the preserved errors, and evidence ids. No model text is
  reused (tested with a planted distinctive phrase). The original invalid
  response is preserved, never repaired away.
- **Validity ≠ quality**: the validator separates structural validity from
  evidence integrity (unknown refs), consistency (contradictions), and
  completeness (uncertainties warning) — a JSON-valid report with
  unsupported confidence still fails.

## Proof (tests: `test_m8_reporting.py`, 12 tests)

Version rejection, 100-confidence rejection, supported-without-basis
rejection, malformed/empty/wrong-type inputs, 6000-char truncation,
unknown + duplicate + contradictory refs, uncertainties warning, valid
inconclusive outcomes, fallback determinism across sessions,
records-only fallback, and end-to-end loop fallback after exactly one
bounded repair (2 provider calls, no fabrication).
