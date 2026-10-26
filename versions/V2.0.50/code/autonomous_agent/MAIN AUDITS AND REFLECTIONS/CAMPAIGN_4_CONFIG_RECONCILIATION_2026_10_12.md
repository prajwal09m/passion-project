# Campaign 4 draft configuration — reconciliation against the governing protocol

Prepared 2026-10-12 by the coding agent. **Read-only reconciliation. The
draft was NOT edited, NOT frozen, NOT loaded.** Reasons for not editing are
in §7.

- Draft under review:
  `autonomous_agent/MAIN AUDITS AND REFLECTIONS/CAMPAIGN_4_CONFIG_DRAFT_2026_10_09.json`
  — SHA-256 `307e98ab4b7207dac24bada4a438686fb859b28bec5e919e80219e249168cdcd`
  (unchanged; verified today).
- Governing sources: the pinned implementation plan
  (`HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md`, `094827b0…`),
  `CAMPAIGN_3_POST_CAMPAIGN_AUDIT_AND_CAMPAIGN_4_PROPOSAL_2026_10_09.md`,
  the H-10 decision sheet/record, and the frozen Campaign 3 config
  (`state/campaign_config.json`, `1e0e30b8…`, 14 stop conditions).

## 1. Verdict summary

| # | Requirement | Source | Draft state | Verdict |
|---|---|---|---|---|
| 1 | `n_boot ≥ 1000` for every experiment feeding a Holm family | plan H-10b; D4 (`M=1000`, `m ≤ 50`) | **no `n_boot` key exists anywhere in the draft** | **MISSING** |
| 2 | Fixed family membership (four named families, rules frozen before generation) | plan, multiplicity section | no multiplicity/families block at all | **MISSING** |
| 3 | Family-size caps + freeze-time `B + 1 ≥ 20·m` feasibility test | plan H-10b | absent | **MISSING** |
| 4 | All original stop conditions preserved | proposal "identical fail-closed set as C3" | draft = C3's 14 + `point_in_time_contamination_detected` = 15; **C3 frozen config contains 14** | PRESENT, but see the count conflict in §3 |
| 5 | Required UNVERIFIABLE-lineage stop added | plan code-touchpoints | **absent** | **MISSING** |
| 6 | Point-in-time contamination stop preserved | plan + draft `_stop_condition_notes` | present as stop #15, with an explicit "wire before freeze or do not launch" note | PRESENT (declaration only; no enforcement site in code — §4) |
| 7 | Fresh configuration pin | `_DRAFT_STATUS.activation_requires` | no fresh pin exists; `state/campaign_config.sha256` still pins **Campaign 3** | NOT YET — correct for a draft |
| 8 | `protocol_fingerprint` recomputed | draft + plan | `TO_BE_RECOMPUTED_AT_FREEZE` placeholder | NOT YET — correct for a draft |
| 9 | Provenance fields finalized (`campaign_id`, `created_at`, `seed_base`) | draft note | `…-2026-10-XX`, `TO_BE_SET_AT_FREEZE` | NOT YET — correct for a draft |
| 10 | Freeze approval record (gate 6) | decision sheet | does not exist | **ABSENT — human** |
| 11 | Launch authorization record (gate 8) | decision sheet | does not exist | **ABSENT — human** |
| 12 | Draft must not be loaded | `_DRAFT_STATUS` | `state/campaign_config.json` is still `campaign-3-continuous-2026-10-05`, pin matches | **CONFIRMED NOT LOADED** |

## 2. Requirements the draft already satisfies (verified field-by-field)

- **Budget 30 / 45**: `execution.max_total_executions = 30`,
  `policy_overrides.max_total_proposals = 45` — matches the approved C4
  budget exactly.
- **Class budgets**: confirmatory 12 / exploration 9 / falsification 18 /
  replication 6 = 45, falsification-heavy as proposed;
  `min_falsification_share = 0.35`, `max_replication_share = 0.5`.
- **`max_per_direction = 12`** consistent in both `direction_limits` and
  `policy_overrides`.
- **Holdout**: `status: SEALED`, `uses: 0`, `prospective_usage: 0`,
  rule text unchanged. Independently verified today: `prospective/`
  directory absent.
- **Duplicate policy**: all five layers, `already_asked` global and
  permanent, `budget_scope` never weakens duplicates — identical to C3
  plus an informational `_note` (no behavioral change).
- **Outcome blindness**: same closed-input list, `llm: none`.
- **Approval policy**: `revalidate_at_approval@1.0.0` — unchanged.
- **Dual-comparison rule** (`champion_integrity_policy`, flagged
  `NEW_IN_C4_DRAFT`): present, records both deltas plus
  `champion_regression`, explicitly does not weaken the parent rule.
- **Stop list superset of C3**: all 14 Campaign 3 stop identifiers appear
  verbatim; `point_in_time_contamination_detected` added, none removed.
- **`versions.primitive_library_version = 1.1.0`** with a note that all
  other component versions are unchanged — matches the plan's scope.
- **`immutable: true`, `schema_version: 1`, `stage_id`, `baseline_id`,
  `parent_champion: V2.0.35`** — consistent with the handoff from C3.

## 3. Blocking finding A — the stop-condition count conflicts across documents

- Frozen Campaign 3 config: **14** stop conditions (counted today).
- C4 draft: **15** (those same 14 + `point_in_time_contamination_detected`).
- Plan, safety-suite bullet: *"all **15 original** stop conditions (the two
  new stops are additions, never replacements)"* — implying **17** at C4.
- Plan code touchpoints: the two new stops are
  `point_in_time_contamination_detected` **plus** the UNVERIFIABLE-lineage
  stop.

Read one way: original = C3's 14 → C4 must carry **16** (14 + 2).
Read the plan literally: original = 15 → C4 must carry **17**.
No document in the repository enumerates a 15th *original* stop, and no
source file or test reads `stop_conditions` at all (§4), so nothing
resolves the conflict mechanically.

**Disposition: fail-closed.** The exact required set must be enumerated by
the owner at freeze approval; freeze must not proceed on an ambiguous
count. Proposed reading, offered for confirmation rather than adopted:
**14 (C3, verbatim) + `point_in_time_contamination_detected` +
`unverifiable_lineage_detected` = 16**, with the plan's "15 original"
treated as a wording error to be corrected in the plan by its author — not
silently reconciled by the agent.

## 4. Blocking finding B — `stop_conditions` is declarative only

A repository-wide scan of every `.py` file (excluding the `candidates/`
tree) found **exactly zero** occurrences of `stop_conditions` outside this
reconciliation's own scratch script. The config's stop list is therefore
**documentation**: enforcement lives in the 18 `LoopStop(...)` reasons in
`continuous_loop.py` (e.g. `HOLDOUT_TOUCHED`, `CAMPAIGN_CONFIG_HASH_MISMATCH`,
`LOCKED`, `STOP_FILE`) and there is **no test asserting correspondence
between the config's declared stop list and the code that can fire it**.

Consequences for the freeze:

1. `point_in_time_contamination_detected` currently has **no enforcement
   site** — the draft's own note admits this ("Implementation must wire
   this stop before freeze; if the wiring is not ready, C4 must not
   launch").
2. The UNVERIFIABLE-lineage stop has neither a declaration nor a site.
3. Until both are wired **and** a correspondence test exists, adding names
   to the JSON would create a false appearance of enforcement.

This is the concrete content of "complete stop-condition enforcement" in
the v1.1.0 remainder and is why it sits behind implementation
authorization (§7).

## 5. Blocking finding C — multiplicity block absent, and what it must contain

Under `max_per_direction: 12`, the plan's H-10b bounds give, with
`n_boot = 1000` (`B + 1 = 1001`):

| Family | Primitive | Members/exp | Bound `m` | `20·m` | Feasible? |
|---|---|---|---|---|---|
| Regime | `regime_split_analysis` | 2 (above/below SMA200) | 24 | 480 | yes |
| Horizon | `target_horizon_robustness` | 3 (1/2/3 sessions) | 36 | 720 | yes |
| Purge | `purge_sensitivity_probe` | 3 (+0/+5/+10 sessions) | 36 | 720 | yes |
| Complexity | `complexity_reduction_check` | 1 (primary rung) | 12 (plan quotes `m = 1` per experiment) | 240 | yes |
| Global cap | — | — | 50 (D4) | 1000 | yes (margin 1) |

So a draft carrying `n_boot = 1000` plus explicit caps is feasible; an
**uncapped** family would need `n_boot ≥ 1799` (grid ceiling 2000) or the
freeze is blocked. Neither the number nor the caps is present today.

## 6. Proposed amendment — PREPARED, NOT APPLIED

To be applied **only** when (a) implementation authorization exists, (b)
D2/C-3 are decided, and (c) the owner approves the freeze. Until then this
block lives here, not in the draft.

```json
"multiplicity_policy": {
  "_status": "PROPOSED_2026_10_12_NOT_APPLIED",
  "correction": "holm_step_down",
  "familywise_alpha": 0.05,
  "pooling": "campaign_end_over_complete_family",
  "n_boot": 1000,
  "n_boot_floor": 1000,
  "feasibility_rule": "n_boot + 1 >= 20 * m for every declared family; otherwise freeze blocked (fail-closed)",
  "max_family_size_m": 50,
  "families": {
    "regime":     {"primitive": "regime_split_analysis",     "members_per_experiment": 2, "member_bound": 24},
    "horizon":    {"primitive": "target_horizon_robustness", "members_per_experiment": 3, "member_bound": 36},
    "purge":      {"primitive": "purge_sensitivity_probe",   "members_per_experiment": 3, "member_bound": 36},
    "complexity": {"primitive": "complexity_reduction_check","members_per_experiment": 1, "member_bound": 12}
  },
  "pooling_exclusions": ["campaign_1_2_3_tests", "primitives_not_named_above"],
  "missing_member_rule": "C-2_option_A",
  "missing_member_p": 1.0,
  "missing_member_label": "unavailable",
  "missing_member_never_refuted": true,
  "p_value_method": "UNRESOLVED_H10_FAIL_CLOSED",
  "campaign_end_record_required": true,
  "no_multiplicity_record_outcome": "INCONCLUSIVE"
}
```

plus stop additions `"point_in_time_contamination_detected"` (already in the
draft) and `"unverifiable_lineage_detected"` (**proposed identifier** — the
exact stop name is part of the frozen contract and needs owner approval),
plus resolution of the §3 count conflict, plus the four freeze-time
placeholders (`campaign_id`, `created_at`, `seed_base`,
`protocol_fingerprint`).

`"p_value_method": "UNRESOLVED_H10_FAIL_CLOSED"` is deliberate: writing
Holm machinery into a config does not adopt method (b), and the plan's
p-value gate test must refuse to compute adjusted p-values until H-10 is
resolved.

## 7. Why the draft was not edited

1. The review packet — inside the pinned bundle `ee345dab…bb03` — quotes
   this draft's exact SHA-256 in its provenance table (§10). Editing the
   draft would make the submitted packet's provenance false, and fixing
   that means rebuilding the bundle and re-pinning every recorded hash,
   which is a worse trade than the delay it saves.
2. Amendments 1–3 and 5 depend on decisions that do not exist yet (D2,
   C-3, implementation authorization, freeze approval). Writing decided-
   by-nobody values into the config is precisely what "never freeze a
   draft or represent an unsigned record as approved" forbids.
3. The work that *can* be done now — this reconciliation, the amendment
   text, and the automated pre-freeze checker
   (`autonomous_agent/launch_readiness_check.py`) — is done, so applying
   the amendment at freeze time is a mechanical step.

## 8. Freeze prerequisites remaining (for the execution checklist)

1. Review received → D2 decided → C-3 ratified (if adopting).
2. Implementation authorization → v1.1.0 built and tested (§3/§4 findings
   closed: stops wired, correspondence test, multiplicity machinery with
   the H-10 fail-closed gate).
3. §3 count conflict resolved in writing by the owner.
4. Amendment applied; freeze-time checks run: H-10b feasibility
   (`B + 1 ≥ 20·m`), census-manifest completeness, count-once rule,
   Tier-2 residual ruling recorded.
5. `campaign_id`/`created_at`/`seed_base` finalized, fingerprint
   recomputed, fresh SHA-256 pin written and verified.6. Gate 6 freeze approval recorded, then gate 7 re-verification, then gate
   8 launch authorization.

## 9. Status update — 2026-10-12 (after the gate-3 subset was implemented)

- **Finding B is closed.** Both new stops are now wired in
  `continuous_loop.py` (durable `AUDIT_STOP` ledger transition + journaled
  `audit_stop` event + restart guard), and the firewall plus a
  config↔code stop-correspondence test exist
  (`test_freeze_integrity.py`, `STOP_ENFORCEMENT`). Adding a declared stop
  without enforcement now fails the suite.
- The amendment block in §6 is unchanged and still **not applied**; its
  stop names now have real enforcement markers behind them.
- The H-10b numbers in §5 remain valid: with `n_boot = 1000` all four
  families pass `B + 1 >= 20·m` under `max_per_direction: 12`.
- Findings A (stop-count conflict), the missing `n_boot`/multiplicity
  block, and the missing UNVERIFIABLE stop **declaration** are unchanged:
  they are freeze-time decisions, and the draft itself remains untouched
  at `307e98ab…`.
