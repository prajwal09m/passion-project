# B1: Protocol Version & Scope Resolution

Date: 2026-10-22
Status: PROTOCOL SELECTION FOR OWNER REVIEW
Blocker: B1 - Protocol version & scope

## The Conflict

There are three protocol references in the project:

1. **V1.0.1 Archive**: Historical study with saved artifacts (event table, OOF predictions, 8 fitted models)
   - Status: Preserved, not a validated champion
   - Source: Never recovered; feature parity failed
   - Evidence: Archive audit showed internal consistency but not source reproduction

2. **V1.0.2 Frozen Protocol**: Frozen but never executed
   - Status: Protocol label, not an executed model version
   - Status: Frozen protocol, not a model release
   - Missing: Required roster/OHLCV inputs absent from checkout

3. **BASELINE_RECONSTRUCTED_2026_10**: Reconstructed baseline used in Campaigns 2-4
   - Status: Reconstruction-track experiment, NOT a reproduction of V1.0.1
   - Evidence: Self-reproduced (two byte-identical clean runs)
   - Limitation: 49 feature columns differ from V1.0.1 archive

## Resolution for Campaign 5

### Decision: Use Campaign 4 Protocol as Foundation

**Selected Protocol**: `campaign-4-continuous-2026-10-14`

**Protocol SHA-256**: `b4ced0e00493f7636efc74baee2424146cb1840233d2b48fda1061b8d50d86b4`

**Rationale**:
1. Campaign 4 completed successfully with this protocol
2. The protocol has been frozen, executed, and audited
3. It inherits all C3 stop conditions and safety architecture
4. It has proven reproducibility (30/30 executions completed)
5. The baseline (BASELINE_RECONSTRUCTED_2026_10) is consistent with this protocol

### V1.0.1 and V1.0.2 Disposition

**V1.0.1 Archive**:
- **Disposition**: Historical evidence only, not the operational protocol
- **Use in C5**: Reference only for historical context
- **Not used as**: The basis for new experiments or baseline
- **Reason**: Source never recovered; hash identity alone is not provenance; 49 feature columns differ from reconstruction

**V1.0.2 Frozen Protocol**:
- **Disposition**: Historical protocol draft, superseded by C4
- **Use in C5**: Reference only for protocol evolution history
- **Not used as**: The operational protocol
- **Reason**: Never executed; required inputs missing; C4 protocol is the executed and frozen successor

### Campaign 5 Protocol Definition

**Base Protocol**: Campaign 4 (`campaign-4-continuous-2026-10-14`)

**Protocol ID for C5**: `protocol-demand-zone-ai-c5-regime-error` (if Option D is selected)

**Protocol Version**: `1.0`

**Protocol SHA-256**: To be computed from frozen C5 configuration

### C4 → C5 Deltas

If Option D (Regime/Error Analysis) is selected, the following deltas from C4 to C5 are documented:

#### Structural Deltas

| Aspect | C4 | C5 (Option D) | Rationale |
|--------|----|---------------|-----------|
| Campaign ID | campaign-4-continuous-2026-10-14 | campaign-5-regime-error-analysis-2026-10-22 | New campaign ID required |
| Parent Champion | V2.0.35 | V2.0.61 | Continue from C4 champion |
| Execution Budget | 32 (30 target + 2 crash slack) | 45 | Increased budget for more regime/error analysis |
| Proposal Budget | 64 | 60 | Slightly reduced, focused on regime/error |
| Class Budgets | confirmatory 14, exploration 9, falsification 34, replication 6 | confirmatory 12, exploration 16, falsification 24, replication 8 | Rebalanced for exploration/error analysis |

#### New Additions

| Addition | Description | Justification |
|-----------|-------------|---------------|
| error_analysis family | New family with 20 members, error_clustering_analysis primitive | Deepen error analysis beyond C4's regime work |
| regime_predefinition_gate | New stop condition | Ensure regime definitions are predeclared, not discovered from labels |
| data_snooping_gate | New stop condition | Prevent regime detection from using outcome labels |

#### Preserved Elements

The following C4 elements are preserved unchanged in C5:

- **Baseline**: BASELINE_RECONSTRUCTED_2026_10
- **Dataset**: study_v1_development_event_table (SHA: 232de7db…)
- **Holdout Policy**: SEALED, uses=0
- **Multiplicity Policy**: week_level_signflip_holm, M=1000, familywise alpha=0.05
- **Flip Draw**: Case A, seed 2613983839999682065, rows SHA c9b6afb0… (reused from C4)
- **Promotion Gates**: All 6 gates unchanged
- **Stop Conditions**: 16 C4 stops carried forward + 2 new C5 stops
- **Duplicate Policy**: Global permanent already-asked memory unchanged
- **Champion Integrity Policy**: Dual comparison rule unchanged
- **Outcome Blindness**: Closed selection inputs unchanged

#### No Changes To

The following are explicitly NOT changed from C4 to C5:

- **Core harness implementation** (recipe_harness.py unchanged)
- **Feature arm definitions** (A→B→C→D nested arms unchanged)
- **Folds** (chronological [2023, 2024, 2025] unchanged)
- **Target definition** (binary label: 1-session hold >= +2% unchanged)
- **Preprocessing** (fold-local, purged unchanged)
- **Evaluation metric** (pooled OOF ROC-AUC unchanged)

### Evidence Boundary

The selected protocol (C4) has the following evidence boundary:

- **Development-only**: No prospective predictions or outcomes
- **Fixed-universe survivorship risk**: Inherited from frozen study roster
- **Point-in-time data**: Yahoo-derived snapshots, not vendor vintages
- **Reconstruction limitations**: 49 feature columns differ from V1.0.1 archive

This boundary is acknowledged and preserved in C5. C5 does not claim to resolve these limitations.

### Protocol Digest

The final protocol digest for C5 will be computed as:

```
SHA-256(canonical_json(C5_campaign_config_without_fingerprint_key))
```

This digest will be:
- Recorded in the frozen C5 configuration
- Included in the authorization predeclaration
- Verified by the authorization preflight before C5 launch

## Alternative: If Owner Chooses Different Option

If the owner selects a different option (A, B, C, or E), the C4→C5 deltas will need to be revised accordingly. The base protocol (C4) remains the same, but the option-specific deltas will differ.

## Status

**Protocol Selection**: Campaign 4 as foundation
**V1.0.1 Disposition**: Historical reference only
**V1.0.2 Disposition**: Historical protocol draft only
**C4→C5 Deltas**: Documented for Option D
**Owner Review Required**: YES

**Next Steps**:
1. Owner confirms protocol selection
2. Owner confirms Option D or selects different option
3. If different option, revise C4→C5 deltas
4. Finalize C5 configuration with protocol_fingerprint computed

**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/B1_PROTOCOL_VERSION_SCOPE_RESOLUTION_2026_10_22.md`
