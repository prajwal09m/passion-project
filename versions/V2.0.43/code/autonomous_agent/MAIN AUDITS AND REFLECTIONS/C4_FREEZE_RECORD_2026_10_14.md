# Campaign 4 Configuration Freeze Record (2026-10-14)

**Status: FROZEN AND INSTALLED.** Executed by the coding agent under the
owner's recorded freeze authorization
(`stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`,
section 0/3: the owner's written FINAL DIRECTIVE of 2026-10-14 authorized
the freeze conditional on every prerequisite being satisfied). Machine
timestamps below are the real UTC clock at execution (the freeze ran at
2026-10-15T00:01+00:00, the night of the 2026-10-14 session; nothing is
backdated). No handwritten signature is claimed; the gates mechanism
carries the recorded decision.

## 1. Frozen identities

| Artifact | Identity |
|---|---|
| Frozen config | `stat_validation_h10/freeze_2026_10_14/CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json`, installed byte-identical to `autonomous_agent/state/campaign_config.json` |
| Config sha256 (fresh pin, also in `state/campaign_config.sha256`) | `33334d14a2140ab149669f12d4ddedf15f9bc427fa1fcce91f971f8a97471e9d` |
| protocol_fingerprint | `58daa72b51ba80323cd0e7a2e9f66d40c27f4c9a4bc301082162ac9e3ff239e2` (sha256 of canonical_json(config minus the fingerprint key)) |
| campaign_id / created_at / seed_base | `campaign-4-continuous-2026-10-14` / `2026-10-15T00:01:27+00:00` / `20261014` (freeze-date convention, same as C2 `20261004` and C3 `20261005`) |
| Flip draw (Case A, C-2) | seed `2613983839999682065` (`secrets.randbits(64)`, OS CSPRNG, drawn at freeze before any C4 outcome exists), W=157, M=1000, rows sha256 `c9b6afb03d19aee4bb3a1075683f00c5a6874f7c2fa23b122e820401b3bc4b17`, PCG64 / numpy 2.3.3, stage `before_outcome_evaluation` |
| Census manifest | `stat_validation_h10/freeze_2026_10_14/C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json`, sha256 `e315103e6da37205…` |
| Precision evidence | `stat_validation_h10/freeze_2026_10_14/precision_evidence.json`, sha256 `1d0ac5fb2fd19ffc…` |
| H-10 decision record | `stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md`, sha256 `6dd405554e7afd76…` |
| Port acceptance fixtures | `autonomous_agent/signflip_port_fixtures_2026_10_14.json`, sha256 `0bb6339a690de061…` |

## 2. Freeze-time rulings and declarations

1. **Statistical method:** `week_level_signflip_holm` (M = 1000, Holm
   step-down, familywise α = 0.05), adopted by the owner's recorded D2
   decision; production module `proposal_layer/signflip.py` with
   recorded flip-draw provenance; A-1..A-13 acceptance tests green (see
   `H10_SIGNFLIP_PORT_IMPLEMENTATION_REPORT_2026_10_14.md`).
2. **Expected-column set (census):** the frozen event table's own header
   defines the expected set — 100 feature columns, 47/11/8/34 by family.
   The lineage inventory's 101/48 count is off by one column of
   label/meta; superseded by this ruling (documented, not silent).
3. **Tier-1 float tolerances (H-11):** one uniform documented rule —
   `abs = 0.5 × 10^-D`, `rel = 1e-9` (the documented float64-chain
   constant), origin `DOCUMENTED_PRECISION` — with **D = 17**, the
   maximum stored decimal place across the Open/High/Low/Close columns
   of all **153/153 raw OHLCV files hash-verified against the v1.0.1
   manifest pins** before measurement. Exact-valued kinds (29 columns)
   compare at exact equality; 3 documented Tier-2 columns stay
   parity-UNVERIFIABLE. Never derived from any observed mismatch.
4. **Stops:** 16 declared — the 14 Campaign 3 stops verbatim plus both
   v1.1.0 audit stops (`point_in_time_contamination_detected`,
   `unverifiable_lineage_detected`), each with recorded enforcement
   markers (config-to-code correspondence test green).
5. **Budgets:** 30 executions / 45 proposals (unchanged, owner-recorded);
   budgets campaign-scoped; duplicate/already-asked memory global.
6. **Holdout:** `holdout_policy` SEALED, uses 0, `prospective/` absent —
   re-verified by the authoritative readiness check; never accessed.

## 3. Validator outputs (direct, this execution)

| Check | Result |
|---|---|
| Raw-input integrity (`measure_documented_precision.py`) | 153/153 hash-verified, exit 0 |
| Real census validator (`census.validate_manifest` via `build_census_manifest_frozen.py`) | **0 errors**, can_audit_pass=True, exit 0 (value-level verdicts UNTESTED by design — the census executes inside the `point_in_time_data_audit` primitive at campaign time) |
| Candidate integrity | content verified against its sidecar under newline normalization (the 2026-10-13 builder's text-mode write produced CRLF bytes; the LF-normalized sha256 equals the pinned sidecar exactly; both hashes recorded in `_FREEZE_STATUS`) |
| Frozen-config placeholder scan (readiness regex) | clean |
| Pre-install readiness predicates (campaign_id, budget, 16 stops, fingerprint, immutable, n_boot/M floors, C-2 rule, holdout) | all hold |
| Full suite `unittest discover -s autonomous_agent -t .` | **367 tests, OK, exit 0** (also re-verified post-install) |
| Install verification (`continuous_loop.campaign_sha()` semantics) | fresh pin == file, exit 0 |

## 4. State transition (Campaign 3 → Campaign 4)

Following the campaign-2 precedent, the final Campaign 3 artifacts were
archived in `autonomous_agent/state/` (never modified):
`loop_state.campaign-3-continuous-2026-10-05.final.json`,
`campaign_config.campaign-3-continuous-2026-10-05.json`,
`campaign_config.campaign-3-continuous-2026-10-05.sha256`. The frozen
Campaign 4 config was installed with a fresh hash-only sidecar, and
`loop_state.json` was removed so the loop self-initializes on the new
campaign (its `load_state` records the C4 campaign id and config hash;
the loop pins the hash every cycle and stops on mismatch). Append-only
history (`proposal_ledger.jsonl`, `events.jsonl`, `loop_events.jsonl`,
research memory) is untouched and continues.

## 5. Gate

`launch_gates.json → freeze_approved` is recorded with this record as
evidence. This record documents a completed freeze; it approves nothing
beyond it, and launch remains the separate gate-7-readiness + gate-8 act
exercised by the owner's directive.
