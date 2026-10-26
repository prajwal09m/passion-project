#!/usr/bin/env python3
"""Re-freeze the Campaign 4 configuration after the 2026-10-15 repair.

Owner directive: "Campaign 4 - Repair Proposal Exhaustion and Resume
Execution", which re-authorizes the previously recorded freeze/launch
authorization wherever it validly covers the action and instructs an
automatic re-freeze + relaunch once the prerequisites are satisfied.

Scope of this re-freeze (everything else is carried over byte-for-byte):

  * versions.generator_version         1.0.0 -> 1.1.0  (pre-creation
    governor guard + the reviewed n_boot bucket-l grid point)
  * versions.primitive_library_version 1.1.0 -> 1.2.0  (default_class
    corrected for regime_split_analysis / target_horizon_robustness to
    the reviewed plan table)
  * approval.rationale / notes / _FREEZE_STATUS record the repair act
  * protocol_fingerprint recomputed by the recorded method

Explicitly PRESERVED (never redrawn, never edited):
  * multiplicity_policy in full, including the Case-A flip draw
    (seed, M, W, rows_sha256, drawn_at) - drawn once at freeze, never
    redrawn
  * budgets (30 executions / 45 proposals), the 0.35 falsification-share
    floor, all six gates, every stop condition, census + precision
    evidence references, holdout policy

Step 1 (default): build CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json from the
byte-verified 2026-10-14 frozen config. Nothing in state/ changes.

Step 2 (--install): verify the live config still matches the 2026-10-14
frozen digest, replace config + sidecar, and re-pin
loop_state.campaign_config_sha256 to the new digest (the pin's purpose is
tamper detection; this deliberate re-pin is part of the recorded re-freeze
act, exactly once per freeze, and no other loop-state field is touched).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import schema  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
PRIOR = ROOT / "stat_validation_h10/freeze_2026_10_14"
PRIOR_FROZEN = PRIOR / "CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json"
OUT = HERE / "CAMPAIGN_4_CONFIG_FROZEN_2026_10_15.json"
STATE = ROOT / "autonomous_agent/state"

CID = "campaign-4-continuous-2026-10-14"
PRIOR_DIGEST = ("33334d14a2140ab149669f12d4ddedf15f9bc427fa1fcce91f971f8a97471e9d")

PLACEHOLDER_RX = re.compile(r"TO_BE_|_AT_FREEZE|-XX\b|DRAFT_ONLY|TBD|PLACEHOLDER",
                            re.I)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> int:
    prior_bytes = PRIOR_FROZEN.read_bytes()
    prior_sha = sha256_bytes(prior_bytes)
    if prior_sha != PRIOR_DIGEST:
        print(f"FAIL: prior frozen config drifted ({prior_sha[:16]} != "
              f"{PRIOR_DIGEST[:16]})", file=sys.stderr)
        return 1
    cfg = json.loads(prior_bytes.decode("utf-8"))
    if cfg.get("campaign_id") != CID:
        print(f"FAIL: unexpected campaign_id {cfg.get('campaign_id')!r}",
              file=sys.stderr)
        return 1

    # --- recorded repair provenance ---------------------------------------
    cfg["refrozen_at"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds")

    versions = cfg["versions"]
    versions["generator_version"] = "1.1.0"
    versions["primitive_library_version"] = "1.2.0"
    versions["_note"] = (
        "Re-frozen 2026-10-15 under the owner's written directive "
        "'Campaign 4 - Repair Proposal Exhaustion and Resume Execution'. "
        "generator 1.1.0: exact pre-creation BiasGovernor projection "
        "(class, projected falsification share, direction/class budgets, "
        "signature history) so provably refusable proposals are never "
        "created, plus the reviewed n_boot bucket-l (2000) grid point "
        "inside the already-declared ParamSpec bounds. primitive library "
        "1.2.0: default_class corrected to the reviewed plan table for "
        "regime_split_analysis and target_horizon_robustness "
        "(falsification). All five v1.1.0 primitives remain executable; "
        "the H-10 method and its production port are unchanged; no gate, "
        "threshold, budget, stop rule, or approval policy changed.")

    cfg["approval"]["rationale"] = (
        str(cfg["approval"]["rationale"])
        + " RE-FREEZE 2026-10-15: re-authorized by the owner's written "
          "directive 'Campaign 4 - Repair Proposal Exhaustion and Resume "
          "Execution' (repair record: "
          "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
          "C4_GENERATOR_REPAIR_AND_REFREEZE_RECORD_2026_10_15.md). The "
          "repair corrects two implementation defects - doomed proposal "
          "creations that burned permanent budget on refusals the "
          "governor would certainly issue, and an unreachable "
          "falsification framing contradicting the reviewed v1.1.0 plan "
          "table - and adds one reviewed candidate-space grid point. "
          "Budgets remain 30 executions / 45 proposals; the 0.35 "
          "falsification-share floor, all six gates, every stop "
          "condition, and the adopted statistical method are unchanged.")

    status = cfg["_FREEZE_STATUS"]
    status["state"] = "FROZEN_2026_10_15"
    status["refreeze"] = {
        "reason": (
            "Owner directive 'Campaign 4 - Repair Proposal Exhaustion and "
            "Resume Execution' (2026-10-15): the pre-repair generator "
            "created 24 candidates that were provably BIAS_QUOTA-doomed, "
            "burning 12/12 validation-direction and 9/9 exploration-class "
            "budget and leaving 0 admissible candidates at 2/30 "
            "executions (stop PROPOSAL_EXHAUSTED)."),
        "changes": [
            "generator 1.0.0 -> 1.1.0: pre-creation governor projection "
            "in _build_candidates and cumulative exact mirror in "
            "generate_proposals (creation can never disagree with "
            "validation)",
            "generator 1.1.0 candidate space: n_boot grid gains the "
            "reviewed bucket-l point 2000 (schema.bucket_n_boot already "
            "defines 500=s/1000=m/2000=l as design-identity-significant; "
            "in-bounds for every primitive; H-10b floor >= 1000 still "
            "enforced at the ParamSpec)",
            "primitive library 1.1.0 -> 1.2.0: default_class corrected "
            "to the reviewed plan table (falsification) for "
            "regime_split_analysis and target_horizon_robustness; "
            "_OPPOSITE_CLASS untouched; point_in_time_data_audit "
            "(not falsification_capable) untouched",
        ],
        "preserved": [
            "multiplicity_policy byte-identical, including the Case-A "
            "flip draw (drawn once at the 2026-10-14 freeze, never "
            "redrawn)",
            "budgets 30/45, min_falsification_share 0.35, six "
            "promotion gates, 16 stop conditions, duplicate layers, "
            "outcome-blind selection inputs",
            "all ledger history: 421+ rows including the 24 refusals, "
            "92 asked signatures, 2 promoted Campaign-4 executions, "
            "prior-campaign archives",
            "holdout SEALED; census manifest and precision evidence "
            "references unchanged",
        ],
        "verification": {
            "regression_suite": "390 tests OK (exit 0) on the repaired "
                                "tree before this re-freeze",
            "targeted_suite": "test_generator_repair.py 20 tests OK",
            "candidate_pool": "37 admissible candidates on the real "
                              "state (all falsification-framed), 37 "
                              "share-doomed framings blocked pre-creation "
                              "with reason BIAS_QUOTA, asked(53)/"
                              "recipe(8) exclusions intact",
        },
        "derived_from": (
            "stat_validation_h10/freeze_2026_10_14/"
            "CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json, byte-verified "
            f"against its recorded digest {PRIOR_DIGEST}"),
    }
    cfg["notes"] = str(cfg["notes"]) + (
        " RE-FROZEN 2026_10_15 after the owner-directed generator repair "
        "(see _FREEZE_STATUS.refreeze): the campaign continues the same "
        "campaign_id, ledger, budgets, and global already-asked memory; "
        "2/30 executions and all prior records carry forward unchanged.")

    fp = schema.sha256_hex(schema.canonical_json(
        {k: v for k, v in cfg.items() if k != "protocol_fingerprint"}))
    cfg["protocol_fingerprint"] = fp

    text = json.dumps(cfg, indent=2, sort_keys=True) + "\n"
    holes = sorted(set(PLACEHOLDER_RX.findall(text)))
    if holes:
        print(f"FAIL: placeholder markers remain: {holes}", file=sys.stderr)
        return 1

    data = text.encode("utf-8")
    digest = sha256_bytes(data)
    OUT.write_bytes(data)
    OUT.with_suffix(".json.sha256").write_text(digest + "\n", "utf-8")
    print("re-frozen config:", OUT.relative_to(ROOT))
    print("sha256:", digest)
    print("protocol_fingerprint:", fp)
    print("flip_draw preserved:",
          cfg["multiplicity_policy"]["flip_draw"]["seed"],
          cfg["multiplicity_policy"]["flip_draw"]["rows_sha256"][:16] + "...")
    print("placeholder scan: clean")
    return 0


def install() -> int:
    frozen_bytes = OUT.read_bytes()
    digest = sha256_bytes(frozen_bytes)
    sidecar = OUT.with_suffix(".json.sha256").read_text("utf-8").split()[0]
    if digest != sidecar:
        print("FAIL: re-frozen config does not match its sidecar",
              file=sys.stderr)
        return 1
    cfg = json.loads(frozen_bytes.decode("utf-8"))
    if cfg.get("campaign_id") != CID:
        print(f"FAIL: unexpected campaign_id {cfg.get('campaign_id')!r}",
              file=sys.stderr)
        return 1

    live_cfg = STATE / "campaign_config.json"
    live_side = STATE / "campaign_config.sha256"
    if sha256_bytes(live_cfg.read_bytes()) != \
            live_side.read_text("utf-8").strip():
        print("FAIL: live config/sidecar mismatch; refusing to touch",
              file=sys.stderr)
        return 1
    if sha256_bytes(live_cfg.read_bytes()) != PRIOR_DIGEST:
        print("FAIL: live config is not the 2026-10-14 frozen build "
              "(another freeze intervened?); refusing to touch",
              file=sys.stderr)
        return 1
    live = json.loads(live_cfg.read_text("utf-8"))
    if not str(live.get("campaign_id", "")).startswith("campaign-4"):
        print(f"FAIL: live config is {live.get('campaign_id')!r}",
              file=sys.stderr)
        return 1

    # Preserve in-flight campaign state: only the config pin changes.
    loop_state_path = STATE / "loop_state.json"
    state = json.loads(loop_state_path.read_text("utf-8"))
    if state.get("campaign_config_sha256") != PRIOR_DIGEST:
        print("FAIL: loop state pin is not the prior frozen digest; "
              "refusing to touch", file=sys.stderr)
        return 1

    live_cfg.write_bytes(frozen_bytes)
    live_side.write_text(digest + "\n", "utf-8")

    from autonomous_agent.core import write_json_atomic
    state["campaign_config_sha256"] = digest
    write_json_atomic(loop_state_path, state)

    verified = sha256_bytes(live_cfg.read_bytes()) == \
        live_side.read_text("utf-8").strip()
    repinned = json.loads(loop_state_path.read_text("utf-8"))[
        "campaign_config_sha256"] == digest
    carried = json.loads(loop_state_path.read_text("utf-8"))[
        "executions_done"]
    print("installed:", live_cfg.relative_to(ROOT))
    print("fresh pin:", digest)
    print("sidecar verified:", verified, "| loop-state re-pinned:",
          repinned, "| executions_done carried:", carried)
    return 0 if (verified and repinned) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true",
                        help="install the re-frozen config into state/ "
                             "(re-pins the loop-state config digest)")
    args = parser.parse_args()
    if args.install:
        return install()
    return build()


if __name__ == "__main__":
    sys.exit(main())
