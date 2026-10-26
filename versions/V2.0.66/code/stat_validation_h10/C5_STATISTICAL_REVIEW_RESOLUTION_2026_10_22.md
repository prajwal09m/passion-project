# Campaign 5 Statistical Review Resolution

Date: 2026-10-22
Author: Project Owner
Status: FINAL DECISION

## Background

Campaign 4 adopted the `week_level_signflip_holm` method based on a substitute AI statistical review with disclosed conflict of interest (recorded in `H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`). The external human statistical reviewer was unavailable.

## Decision for Campaign 5

### Resolution: Accept Substitute Review for C4, Require Independent Review for C5

**Decision**: The substitute AI review for Campaign 4 is **accepted as sufficient for Campaign 4's decision-making**, with the following understandings:

1. **Campaign 4 Status**: The `week_level_signflip_holm` method, as implemented and frozen in Campaign 4, is considered validated for Campaign 4's purposes based on the owner's adoption decision with disclosed conflict of interest.

2. **Campaign 5 Requirement**: **Campaign 5 requires independent human statistical review** before launch. The substitute AI review route used for Campaign 4 is **not acceptable** for Campaign 5 or any future campaign.

3. **Justification**: 
   - Campaign 4 was a measurement-axis campaign with limited scope (30 executions, focused on regime/purge/complexity families)
   - Campaign 5 may involve different objectives, possibly including model-discovery or real-market evaluation
   - The risk profile and scientific stakes are higher for Campaign 5
   - Independent review is a foundational requirement that should not be weakened for the next major campaign

### Required Actions for Campaign 5

Before Campaign 5 can launch, the following must be completed:

1. **Engage an independent human statistical reviewer** with:
   - No prior involvement in implementing the system under review
   - No conflict of interest with the project owner or implementation team
   - Qualifications in statistical methodology, particularly multiple testing and permutation-based inference

2. **Provide the reviewer with**:
   - Frozen Campaign 5 protocol and configuration
   - Implementation code for any new multiplicity or measurement methods
   - Development dataset (without holdout)
   - Clear scope: what is being validated and what conclusions may be drawn

3. **Obtain written assessment** covering:
   - Validity of the method for its intended use
   - Assumptions and their justification
   - Limitations and required disclosures
   - Overall approval or rejection with reasons

4. **Record the review** in:
   - `stat_validation_h10/H10_C5_INDEPENDENT_STATISTICAL_REVIEW.md`
   - Corresponding entry in `launch_gates.json` for Campaign 5

### Outstanding Questions from H-10 Packet

The following questions from the H-10 statistical review packet remain **unresolved** and should be addressed by the independent reviewer for Campaign 5:

- Q1: Exchangeability / sign symmetry on real data
- Q2: Temporal dependence and shared-training dependence
- Q3: Super-uniformity of marginal p-values (size 0.055/0.060 at nominal 0.05)
- Q4: Adequacy of null calibration
- Q5: Monte-Carlo resolution at M=1000 near Holm thresholds
- Q6: Holm validity with discrete p-values
- Q7: One-sided conventions and degenerate samples
- Q8: CI-versus-test disagreement
- Q9: Conflict of interest assessment (to be resolved by the independent reviewer's independence statement)

### Campaign 4 Method Status

The `week_level_signflip_holm` method as frozen in Campaign 4 remains:
- **Valid for Campaign 4**: The owner's adoption decision stands
- **Not independently validated**: The substitute review is not equivalent to independent review
- **Not automatically valid for C5**: Campaign 5 must undergo its own independent review

If Campaign 5 uses the same or similar methods, the independent reviewer must:
- Review the method independently (not rely on the Campaign 4 substitute review)
- Consider whether the Campaign 4 findings inform their assessment
- Provide their own conclusions specific to Campaign 5's scope

## Authorization

This resolution is signed by the project owner and constitutes the final decision on statistical review requirements for Campaign 5.

**Decision**: ACCEPT substitute review for C4, REQUIRE independent review for C5
**Signed by**: Project Owner
**Date**: 2026-10-22
**Evidence path**: `stat_validation_h10/C5_STATISTICAL_REVIEW_RESOLUTION_2026_10_22.md`
