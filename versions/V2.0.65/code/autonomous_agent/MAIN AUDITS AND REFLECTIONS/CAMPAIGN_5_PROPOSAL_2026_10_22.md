# Campaign 5 Proposal — Research Objectives and Options

Date: 2026-10-22
Status: PROPOSAL FOR OWNER REVIEW
Type: Multiple research objective options presented for owner selection

## Background

Campaign 4 completed successfully (30/30 executions, V2.0.61 champion) with the following achievements:
- Opened three previously unexplored directions (error_analysis, data_quality, target_design)
- Implemented harness v1.1.0 with new primitives
- Fixed champion line integrity with dual comparison rule
- Adopted multiplicity method `week_level_signflip_holm`

The champion plateau (~0.68 pooled OOF AUC) has been characterized but not exhausted. Campaign 5 can pursue several distinct research directions.

## Prerequisites for Campaign 5 (All Required)

Before any Campaign 5 option can proceed, the following must be completed:

1. **Independent Statistical Review** (resolved in `C5_STATISTICAL_REVIEW_RESOLUTION_2026_10_22.md`)
   - Engage independent human statistical reviewer
   - Review C5 protocol and any new methods
   - Obtain written approval

2. **Real-Data Integration Test** (documented in `C5_REAL_DATA_INTEGRATION_STATUS_2026_10_22.md`)
   - Complete C4 predeclaration or create new C5-specific test
   - Execute in disposable workspace
   - Verify all checks pass

3. **Authorization Predeclaration**
   - Create `campaign5_authorization.json` with signed attestations
   - Define scope and data boundary
   - Obtain owner and reviewer signatures

## Campaign 5 Research Objective Options

### Option A: Model-Discovery Campaign

**Objective**: Enable autonomous search for novel model architectures and feature combinations beyond the current recipe library.

**Hypotheses**:
- H1: The proposal layer's deterministic composition can discover configurations that improve on the plateau
- H2: New primitive combinations (beyond the current 12) yield statistically significant gains
- H3: The search space can be constrained to safe, falsifiable experiments

**Proposed Changes**:
- Enable `allow_generated_proposals` (currently default false)
- Expand `DesignPrimitiveLibrary` with new primitives (e.g., feature interaction terms, ensemble methods, target transformations)
- Add LLM-assisted hypothesis drafting (optional, requires separate review)
- Maintain all existing gates and duplicate layers

**Budget Suggestion**:
- Executions: 50-75 (higher than C4 due to search space)
- Proposals: 100-150
- Class budgets: falsification 40%, confirmatory 30%, exploration 20%, replication 10%

**Risks**:
- Larger search space may exhaust budget without finding gains
- New primitives require harness support and testing
- LLM assistance introduces new safety surface (if enabled)

**Gate Requirements**:
- All existing C4 gates (6 promotion gates, 16 stop conditions)
- Additional gate: `novelty_gate` to ensure new primitives are genuinely novel, not parameter re-sweeps
- Budget ceiling on any single primitive family

**Success Criteria**:
- At least one accepted configuration with delta ≥ +0.02 vs champion AND passes all gates
- Or clear evidence that the search space is exhausted with no improvements (honest negative result)

---

### Option B: Profitability and Utility Simulation

**Objective**: Evaluate whether the predictive improvements translate to realistic trading performance after costs and market impact.

**Hypotheses**:
- H1: AUC improvements correlate with positive risk-adjusted returns after realistic costs
- H2: Position sizing and risk management can convert predictive edge to profitable strategy
- H3: The model's edge persists across market regimes and transaction cost regimes

**Proposed Changes**:
- Add simulation primitives to harness (already exists in historical code but not integrated)
- Define cost model (slippage, commission, market impact)
- Define position sizing rules (fixed fraction, Kelly criterion, risk parity)
- Add utility metrics (Sharpe ratio, profit factor, maximum drawdown, Calmar ratio)

**Budget Suggestion**:
- Executions: 40-60 (simulation is cheaper than training)
- Proposals: 60-80
- Class budgets: exploration 50%, falsification 30%, confirmatory 15%, replication 5%

**Risks**:
- Simulation may not reflect real-world execution
- Historical data may not represent future market conditions
- Risk of overfitting to simulation metrics

**Gate Requirements**:
- All existing C4 gates
- Additional gate: `simulation_integrity_gate` (no leakage from future returns into position decisions)
- Additional gate: `cost_realism_gate` (cost parameters must be defensible)
- Disclosure: "NOT INVESTMENT ADVICE" in all results

**Success Criteria**:
- At least one configuration with Sharpe ≥ 1.0 OR profit factor ≥ 1.5 on development folds
- Or clear evidence that predictive edge does not translate to profitability (honest negative result)

**Important Note**: This option requires **additional governance review** because it touches trading simulation. The project's educational/research scope must be respected.

---

### Option C: Holdout Evaluation (Prospective Test)

**Objective**: Perform a prospective evaluation on the sealed holdout to test whether development-set performance generalizes.

**Hypotheses**:
- H1: Development-set AUC predicts holdout AUC within a predeclared margin
- H2: The champion's performance is stable across the time split between development and holdout
- H3: Calibration degrades predictably (or not) in the prospective period

**Proposed Changes**:
- Define holdout access protocol (single-use, irreversible)
- Add holdout evaluation primitive to harness
- Pre-register holdout evaluation criteria (e.g., AUC degradation ≤ 0.02)
- Seal holdout after evaluation (no re-tuning)

**Budget Suggestion**:
- Executions: 10-20 (holdout evaluation is single-shot per configuration)
- Proposals: 20-30
- Class budgets: confirmatory 60%, falsification 30%, replication 10%

**Risks**:
- Holdout is a finite resource; once evaluated, it cannot be reused
- Poor holdout performance would invalidate much of the development work
- Temptation to re-tune on holdout (must be prevented by gate)

**Gate Requirements**:
- All existing C4 gates
- Additional gate: `holdout_single_use_gate` (holdout can only be accessed once per campaign)
- Additional gate: `no_retuning_gate` (no modifications after holdout evaluation)
- Predeclaration: holdout criteria must be declared before evaluation

**Success Criteria**:
- Holdout AUC within predeclared margin of development AUC (e.g., degradation ≤ 0.02)
- Or clear evidence of generalization failure (honest negative result)

**Important Note**: This option requires **explicit owner authorization** because it consumes the sealed holdout, a finite resource.

---

### Option D: Deep Regime and Error Analysis

**Objective**: Deepen the regime and error analysis work from Campaign 4 to understand when and why the model fails.

**Hypotheses**:
- H1: Model performance varies systematically by market regime (bull/bear/high-vol/trend)
- H2: Errors are concentrated in specific feature spaces or time periods
- H3: Sub-models specialized to regimes outperform a single global model

**Proposed Changes**:
- Expand regime primitive definitions (add more granular regime splits)
- Add error analysis primitives (error clustering, feature importance by regime, failure case studies)
- Add ensemble-of-specialists primitive (train separate models per regime)
- Add regime-detection primitive (identify regime from market features)

**Budget Suggestion**:
- Executions: 40-50
- Proposals: 60-80
- Class budgets: exploration 40%, falsification 30%, confirmatory 20%, replication 10%

**Risks**:
- Regime definitions may be post-hoc or data-dependent
- Specialized models may overfit to regime-specific noise
- Complexity increases without guaranteed performance gain

**Gate Requirements**:
- All existing C4 gates
- Additional gate: `regime_predefinition_gate` (regime definitions must be predeclared, not discovered from labels)
- Additional gate: `no_data_snooping_gate` (regime detection must not use outcome labels)

**Success Criteria**:
- At least one regime-specialized configuration with delta ≥ +0.01 vs global model
- Or regime analysis that characterizes failure modes (honest explanatory result)

---

### Option E: Conservative Validation and Replication

**Objective**: Strengthen the validation of existing findings through independent replication and stricter validation protocols.

**Hypotheses**:
- H1: Current findings replicate on independent data splits or seed sets
- H2: Findings are robust to stricter purging and validation protocols
- H3: Bootstrap intervals are well-calibrated

**Proposed Changes**:
- Expand replication primitive (more seed sets, time-block splits)
- Add stricter purging primitive (wider embargo windows)
- Add calibration diagnostic primitives (reliability diagrams, expected calibration error by subgroup)
- Add bootstrap validation primitive (verify CI coverage)

**Budget Suggestion**:
- Executions: 30-40
- Proposals: 40-50
- Class budgets: replication 40%, falsification 30%, confirmatory 20%, exploration 10%

**Risks**:
- May be perceived as "going backward" rather than advancing
- Stricter protocols may reject currently accepted findings
- Lower risk, but also lower novelty

**Gate Requirements**:
- All existing C4 gates
- No new gates required (conservative approach)

**Success Criteria**:
- Key findings replicate with p ≤ 0.05 on independent validation
- Or clear evidence of where findings do not replicate (honest negative result)

---

## Comparison of Options

| Option | Novelty | Risk | Budget | Gate Complexity | Holdout Use |
|--------|---------|------|--------|----------------|-------------|
| A: Model-Discovery | High | High | High | Medium-High | No |
| B: Profitability | High | Very High | Medium | High | No |
| C: Holdout Evaluation | Medium | Medium | Low | Medium | Yes (single-use) |
| D: Regime/Error Analysis | Medium | Medium | Medium | Medium | No |
| E: Conservative Validation | Low | Low | Low | Low | No |

## Recommendation

**Immediate Next Step**: Owner should select one primary option for Campaign 5, or specify a hybrid approach.

**Suggested Path**:
1. **Start with Option D (Regime/Error Analysis)**: Medium risk, builds on C4 work, does not consume holdout, provides explanatory value
2. **Consider Option C (Holdout Evaluation)** as a follow-up if D succeeds: validates generalization prospectively
3. **Defer Options A and B**: Higher risk, require additional governance review
4. **Option E** is always available as a baseline if other options are blocked

However, the owner's research priorities and risk tolerance should guide the final decision.

## What I Need from the Owner

1. **Select a primary option** (A, B, C, D, E, or hybrid)
2. **Authorize the scope** (budget ranges, specific primitives to add, any special constraints)
3. **Confirm the prerequisites** are acceptable (independent review, integration test, authorization)
4. **Specify any additional requirements** not covered in the options above

Once the owner selects an option, I will:
- Draft the frozen Campaign 5 configuration
- Create the authorization predeclaration
- Begin the independent statistical review engagement
- Prepare the real-data integration test plan

**Status**: PROPOSAL FOR OWNER DECISION
**Date**: 2026-10-22
**Evidence path**: `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_5_PROPOSAL_2026_10_22.md`
