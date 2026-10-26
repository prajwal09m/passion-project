# Campaign 5 Candidate Identity Validation — Synthetic Matrix Audit

**Status: SYNTHETIC ENGINEERING VALIDATION COMPLETE; no campaign authorization.** This validates identity bookkeeping only, not prediction quality, AUC, market performance, or profitability. The development candidate search remains disconnected from production.

## Scope and method

Ran against `.model_discovery_workspace/dev/autonomous_agent/proposal_layer/candidate_search_v2.py` and its synthetic-only tests. No event table, OOF predictions, real-market rows, metrics, or holdout content were loaded. Used a deterministic `numpy.random.default_rng(20261018)` matrix of 31 rows × 3 synthetic feature columns, all three feature operators, and all three transform settings for a fixed RandomForest config. The test reconstructs each generated matrix's monomial columns by inspecting and applying the *actual* sklearn pipeline transformations, then compares column multiset signatures with `_semantic_feature_map` and candidate identity. It checks identity stability across two fresh Python subprocesses.

## Checks

- Reordered feature IDs retain the same canonical identity; existing tests exercise this and identity-only changes for transformations/operators.
- Tree estimator standardization is intentionally canonicalized with identity scaling; logistic-regression standardization remains distinct.
- Feature operators (`original`, pairwise interactions, marginal squares) and transforms create identity-bearing changes where generated matrix columns differ.
- The synthetic 3×3 operator/transform set yields six identities after intended tree-scaling aliases collapse; each identity has a reproducible matrix signature.
- Pipeline-generated matrix columns were verified against the corresponding synthetic monomials at `rtol=1e-12, atol=1e-12`.
- Repeated process execution returns the same identity digest.
- Existing malformed feature-ID, identity, and temporal-synthetic tests remain active. Candidate selection now materializes a caller-supplied one-shot feature-universe iterator once, so every candidate is checked against the same vocabulary; unhashable universe entries fail closed. The selector also rejects negative, fractional, and boolean budgets instead of silently truncating or accepting booleans as integers.

## Exact verification

From `.model_discovery_workspace/dev/`:

```bash
py -3 -m py_compile autonomous_agent/proposal_layer/candidate_search_v2.py autonomous_agent/test_candidate_search_v2.py
timeout 120s py -3 -m pytest -q autonomous_agent/test_candidate_search_v2.py
```

Historical identity-only result: **16 passed in 4.18s**, exit 0; later focused suite before the selector regression was **16 passed in 2.71s**, exit 0. After the added selector input validation, final focused run: **18 passed in 2.18s**, exit 0; compilation of implementation and tests passed. No tests were skipped or removed. This is a bounded dev-only selection check, not campaign authorization or a predictive-performance result. The complete unchanged development-suite evidence remains in [coordinated full-suite log](CAMPAIGN5_COORDINATED_FULL_SUITE.log).

## Limitations

The identity check models the feature-map columns symbolically and numerically on synthetic values. It does not establish equal fitted model behavior, handle arbitrary data-dependent transformations, make mathematical claims about numerical ties/conditioning, authorize a candidate family, or validate any real-market workflow. Tree standardization equivalence is only the proposal's intended axis-scaling canonicalization and is not an evaluation conclusion. No production integration or frozen campaign settings were changed.
