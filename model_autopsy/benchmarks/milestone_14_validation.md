# M14 Validation (Phase 14 gates)

Backend: py -m pytest model_autopsy/tests -q → 439 passed, 0
failed (~108s), exit 0. Includes 14 new M14 tests, all M13 suites
(discovery, eval2, m12, m11, m10), separation audits (52 passed),
framework suites (33 passed). Scientific: sealed truths for
corpora A/B/C intact, import-boundary audits pass, no label
leakage, evidence-required grading, no report-only shortcuts, no
false reproduction claims, no silent threshold changes (only
additive vocabulary plus fallback). Frontend: npx tsc --noEmit
exit 0, npm run build exit 0. Security: .env ignored, no
secrets in docs/logs/artifacts, no unapproved paid calls, no
untrusted code execution, original artifacts hash-guarded.
Historical: prior live runs intact; M9-M12 scores unchanged.
