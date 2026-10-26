# Baseline Establishment Report (Reconstructed Track)

Baseline: `BASELINE_RECONSTRUCTED_2026_10` — status `ESTABLISHED`

> **This baseline is a reconstruction and is NOT a reproduction of V1.0.1.**

The historical V1.0.1 reproduction record remains 
`autonomous_agent/state/baseline_reproduction.json` (FAILED/BLOCKED) and was not modified.

- **Historical record unchanged:** `True`
- **Lineage:** `{"historical_v1_0_1_sha256": "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b", "note": "The reconstructed implementation differs from historical V1.0.1: 49 known feature-column differences (rsi14, atr_pct, zone_width_pct, 14 zone-base and 32 order-block features).", "parent": "V1.0.1", "relation": "reconstruction", "v1_0_1_evidence": "autonomous_agent/state/baseline_reproduction.json (unchanged)", "v1_0_1_record_status": "FAILED", "v1_0_1_status": "FAILED"}`
- **Source:** `{"bytes": 90614, "path": "study_files/backend/demand_zone_study_v1.py", "sha256": "cea2440425e1f2f56a95b576481ae2ef603fe1f6a9816078e0a998781e0cef2a"}`
- **Test suite:** `{"path": "study_files/backend/tests/test_demand_zone_study_v1.py", "sha256": "c20e0889ec488b7bacc17c753bafb6c98acf1f804df38735df8c166259343107"}`
- **Protocol:** `{"path": "study_files/MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json", "sha256": "6b4e4557d6ca9dc5dec118d39c22f2e1483011b9fcc7fc1940ecd544f2e3ed05", "version": "1.0.2"}`
- **Dual run:** `{"artifact_byte_equality": "strict", "artifact_files_compared": 12, "byte_identical": true, "full_file_map_differences": ["development/run_manifest.json"], "manifest_compared_by": "stable fields; volatile keys excluded", "manifest_differing_keys": ["artifact_directory", "data_directory"], "manifest_stable_fields_equal": true, "manifest_volatile_keys_excluded": ["artifact_directory", "data_directory", "runtime"], "runs": 2}`
- **Leakage:** `{"hits": [], "status": "PASS", "tokens_checked": ["mfe_pct", "mae_pct", "forward_return"]}`
- **Holdout:** `{"detail": "final holdout artifacts absent; holdout remains sealed", "status": "SEALED", "uses": 0}`
- **Pipeline fingerprint:** `d103e4c94a5f8fb7287c1617b956b45a939c86f8372a77f02f81555ee4aeccf1`
- **Self-reproduction:** `{"artifact_files_compared": 12, "byte_identical": true, "runs": 2, "verified_at": "2026-10-03T22:22:55+00:00"}`

## Known limitations

- This baseline is a reconstruction and is NOT a reproduction of V1.0.1.
- The implementation differs from historical V1.0.1 with 49 known feature-column differences (rsi14, atr_pct, zone_width_pct, 14 zone-base and 32 order-block features); see autonomous_agent/state/baseline_reproduction.json drift record.
- Outputs are retrospective development artifacts; the final holdout remains sealed and no prospective claim exists.
