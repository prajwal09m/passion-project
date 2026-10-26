#!/usr/bin/env python3
"""Freeze the Campaign 4 configuration (2026-10-14) and install it into state/.

Run AFTER every freeze prerequisite exists:
  * owner decisions recorded (H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md;
    launch_gates.json: review_received/d2_decided/c3_ratified decided),
  * production sign-flip port + A-1..A-13 acceptance tests green,
  * precision evidence (D=17, 153/153 hash-verified raw files),
  * frozen census manifest with zero validate_manifest errors.

Step 1 (default): build CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json from the
byte-verified 2026-10-13 candidate, apply the freeze-time finalizations,
recompute the protocol fingerprint, self-scan for placeholders, and write
the file + hash-only sidecar into this directory. Nothing in state/ changes.

Step 2 (--install): archive the final Campaign 3 state artifacts following
the campaign-2 precedent, copy the frozen config into
autonomous_agent/state/campaign_config.json with a fresh SHA-256 sidecar,
and remove state/loop_state.json so the loop self-initializes on the new
campaign (load_state records the new campaign_id and config hash; the
loop's own safety precheck pins the hash on every cycle).
"""
import argparse
import hashlib
import json
import pathlib
import re
import secrets
import shutil
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import schema, signflip  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE = (ROOT / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                    "CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json")
CANDIDATE_SIDECAR = CANDIDATE.with_suffix(".json.sha256")
PRECISION = HERE / "precision_evidence.json"
CENSUS = HERE / "C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json"
OUT = HERE / "CAMPAIGN_4_CONFIG_FROZEN_2026_10_14.json"
STATE = ROOT / "autonomous_agent/state"

# Mirrors launch_readiness_check.PLACEHOLDER_RX -- the frozen config must
# contain no unfinalized markers.
PLACEHOLDER_RX = re.compile(r"TO_BE_|_AT_FREEZE|-XX\b|DRAFT_ONLY|TBD|PLACEHOLDER",
                            re.I)

CID = "campaign-4-continuous-2026-10-14"
# The frozen OOF evaluation frame's week-group count (D2 review: 41,221 rows,
# 157 ISO weeks, pi = 0.165; supersession note; port spec section 9). The
# production loader validates the actual frame's W against the recorded
# rows hash and fails closed on mismatch, so this documented value is a
# recorded expectation, never a silently trusted constant.
FLIP_W = 157
FLIP_M = 1000


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build() -> int:
    sidecar_expected = CANDIDATE_SIDECAR.read_text("utf-8").split()[0]
    candidate_bytes = CANDIDATE.read_bytes()
    candidate_sha = sha256_bytes(candidate_bytes)
    normalized_sha = sha256_bytes(candidate_bytes.replace(b"\r\n", b"\n"))
    if candidate_sha == sidecar_expected:
        candidate_verification = "raw-bytes hash matches the sidecar"
    elif normalized_sha == sidecar_expected:
        # The 2026-10-13 builder wrote the file in text mode (CRLF on
        # Windows) but pinned the digest of the LF serialization. The
        # content is byte-identical modulo newline translation, which this
        # comparison proves; both hashes are recorded in the freeze status.
        candidate_verification = (
            "content verified against the sidecar under newline "
            "normalization: the 2026-10-13 builder's text-mode write "
            "produced CRLF file bytes while the pinned digest covers the "
            "LF serialization; LF-normalized sha256 equals the sidecar "
            "exactly (raw-bytes sha256 recorded separately)")
    else:
        print(f"FAIL: candidate drift (raw {candidate_sha[:16]} / "
              f"normalized {normalized_sha[:16]} != {sidecar_expected[:16]})",
              file=sys.stderr)
        return 1

    precision_sha = sha256_bytes(PRECISION.read_bytes())
    census_sha = sha256_bytes(CENSUS.read_bytes())
    evidence = json.loads(PRECISION.read_text("utf-8"))
    D = int(evidence["documented_decimals_D"])
    census = json.loads(CENSUS.read_text("utf-8"))
    if census["completeness_validation"]["errors"]:
        print("FAIL: census manifest carries validation errors", file=sys.stderr)
        return 1

    cfg = json.loads(candidate_bytes.decode("utf-8"))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    cfg.pop("_CANDIDATE_STATUS", None)
    cfg["campaign_id"] = CID
    cfg["created_at"] = now
    cfg["seed_base"] = 20261014                    # C2/C3 convention: freeze date
    cfg["approval"]["approver"] = f"policy:{CID}"
    cfg["approval"]["rationale"] = (
        "Frozen 2026-10-14 under the owner's recorded decisions "
        "(stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md, "
        "source: the owner's written FINAL DIRECTIVE of 2026-10-14): D2 "
        "adopted (substitute AI review with disclosed conflict of interest; "
        "Result 2' operative, Result 2 retracted), C-3 ratified, freeze "
        "authorized once every prerequisite passed. Budgets: 30 executions "
        "/ 45 proposals. Approval mode stays autonomous_revalidation: every "
        "proposal is revalidated against current ledger state at approval "
        "time; no hidden human selection.")
    cfg["policy_overrides"]["campaign_id"] = CID

    # -- H-10: the adopted method, its note, and the frozen flip draw -------
    mult = cfg["multiplicity_policy"]
    mult["_status"] = (
        "FROZEN_2026_10_14: method adopted by the owner's recorded D2 "
        "decision (H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md); "
        "n_boot=1000 and M=1000 pinned; production module "
        "autonomous_agent/proposal_layer/signflip.py; A-1..A-13 acceptance "
        "tests green (test_signflip_port.py, equivalence fixtures pinned).")
    mult["p_value_method"] = signflip.APPROVED_METHOD_NAME
    mult["p_value_note"] = (
        "Adopted method (b): week-level sign-flip Monte-Carlo p-values at "
        "M=1000 with Holm step-down (familywise alpha=0.05), computed by "
        "the production port with recorded, data-independent flip-draw "
        "provenance (see multiplicity_policy.flip_draw). Validity is "
        "procedure-level (Result 2'-B, marginal over the recorded flip "
        "draw), never conditional on the realized flip set; Result 2 is "
        "retracted. The campaign-end record discloses the Monte-Carlo "
        "resolution limitation (min representable p = 1/1001; borderline "
        "members at large m resolved 25-48%, biased toward non-rejection) "
        "and the C-2 Option A missing-member rule (strictens, never "
        "loosens).")
    flip_seed = secrets.randbits(64)               # external entropy, Case A
    S, draw = signflip.draw_flips(FLIP_W, FLIP_M, flip_seed)
    del S
    mult["flip_draw"] = {
        "stage": signflip.FLIP_DRAW_STAGE,
        "procedure": (
            "Case A: drawn once at configuration freeze by "
            "secrets.randbits(64) (OS CSPRNG, data-independent) before any "
            "Campaign 4 outcome exists; recorded here and never redrawn. "
            "Production callers obtain it via "
            "signflip.load_campaign_flip_draw and fail closed "
            "(FlipProvenanceMissing) on any stage/W/hash mismatch."),
        "seed": flip_seed,
        "M": FLIP_M,
        "W": FLIP_W,
        "rows_sha256": draw.rows_sha256,
        "rng_name": draw.rng_name,
        "bitgen": draw.bitgen,
        "numpy_version": draw.numpy_version,
        "drawn_at": now,
        "flip_W_source": (
            "documented frozen OOF evaluation frame: 41,221 rows / 157 ISO "
            "weeks / pi=0.165 (D2 review, D2_REVIEW_SUPERSESSION_NOTE_2026_10_13.md, "
            "H10_SIGNFLIP_PORT_SPEC_2026_10_13.md section 9); the recorded "
            "rows hash binds the actual frame W at use time"),
        "disclosures": signflip.disclosure_fields(),
    }

    # -- freeze provenance block ------------------------------------------
    cfg["_FREEZE_STATUS"] = {
        "state": "FROZEN_2026_10_14",
        "frozen_at": now,
        "frozen_by": (
            "coding agent executing the owner's written FINAL DIRECTIVE of "
            "2026-10-14 (decisions recorded in "
            "stat_validation_h10/H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md)"),
        "derived_from": (
            "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
            "CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json, left untouched; "
            f"verification: {candidate_verification}; raw-bytes sha256 "
            f"{candidate_sha}, LF-normalized sha256 {normalized_sha}, "
            f"sidecar {sidecar_expected}"),
        "freeze_time_finalizations": [
            "campaign_id/created_at/seed_base finalized (freeze-date "
            "convention: seed_base 20261014)",
            "multiplicity_policy.p_value_method set to the adopted "
            "week_level_signflip_holm with the recorded flip_draw block "
            "(Case A draw, seed + rows hash pinned)",
            "Tier-1 float tolerances declared for the census via the "
            "documented-precision rule (D="
            f"{D}, abs=0.5e-{D}, rel=1e-9, origin DOCUMENTED_PRECISION)",
            "census manifest frozen with zero validate_manifest errors "
            "(stat_validation_h10/freeze_2026_10_14/"
            "C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json)",
            "16 stop conditions carried (14 Campaign 3 verbatim + both "
            "v1.1.0 audit stops)",
            "protocol_fingerprint recomputed by the recorded method "
            "(sha256 of canonical_json(config minus the fingerprint key))",
        ],
        "expected_column_ruling": (
            "the frozen event table's own header defines the census "
            "expected-column set (100 feature columns, 47/11/8/34 by "
            "family); the lineage inventory's 101/48 count is off by one "
            "and superseded"),
        "census_manifest": {
            "path": "stat_validation_h10/freeze_2026_10_14/"
                    "C4_CENSUS_MANIFEST_FROZEN_2026_10_14.json",
            "sha256": census_sha,
            "validate_manifest_errors": 0,
        },
        "tolerances_declaration": {
            "rule": ("H-11 documented precision: Tier-1 float columns carry "
                     "abs = 0.5*10^-D with D = the maximum stored decimal "
                     "place across the price columns of the 153 hash-verified "
                     "raw OHLCV files, plus rel = 1e-9 for the float64 "
                     "derived-computation chain; exact-valued kinds compare "
                     "at exact equality"),
            "documented_decimals_D": D,
            "evidence": "stat_validation_h10/freeze_2026_10_14/"
                        "precision_evidence.json",
            "evidence_sha256": precision_sha,
        },
        "h10_artifacts": {
            "decision_record": "stat_validation_h10/"
                               "H10_D2_C3_OWNER_DECISION_RECORD_2026_10_14.md",
            "production_port": "autonomous_agent/proposal_layer/signflip.py",
            "acceptance_tests": "autonomous_agent/test_signflip_port.py",
            "equivalence_fixtures": "autonomous_agent/"
                                    "signflip_port_fixtures_2026_10_14.json",
            "equivalence_fixtures_sha256":
                "0bb6339a690de0615bf93ccf814719f541dfb008b452f7228cf454113edf1a98",
        },
    }

    cfg["versions"]["primitive_library_version"] = "1.1.0"
    cfg["versions"]["signflip_port_version"] = "signflip@1.0.0"
    cfg["versions"]["h10_method"] = (
        "week_level_signflip_holm (M=1000, Holm step-down, familywise "
        "alpha=0.05; recorded owner decision 2026-10-14)")
    cfg["versions"]["_note"] = (
        "All five v1.1.0 primitives executable; the H-10 p-value method is "
        "adopted and its production port versioned; no other component "
        "version changed (no gate/governor/compiler changes).")

    cfg["notes"] = (
        "FROZEN production epoch (Campaign 4), successor to "
        "campaign-3-continuous-2026-10-05 (38/40 executed, PORTFOLIO_COMPLETE; "
        "final state and config archived in autonomous_agent/state/). C4 is a "
        "measurement-axis campaign: it opens the three never-executed "
        "directions (error_analysis, data_quality, target_design) plus "
        "purge-sensitivity and complexity-reduction falsifiers via harness "
        "v1.1.0. Budgets are campaign-scoped; duplicate/already-asked memory "
        "stays global and permanent. Stage 1 bias_policy.json is NOT "
        "modified. Holdout stays SEALED. If the point-in-time audit reports "
        "confirmed contamination or UNVERIFIABLE lineage, the loop STOPs "
        "fail-closed for human data-lineage review. Formal refutation claims "
        "at campaign end run through the adopted sign-flip + Holm method "
        "with the recorded flip draw.")

    fp = schema.sha256_hex(schema.canonical_json(
        {k: v for k, v in cfg.items() if k != "protocol_fingerprint"}))
    cfg["protocol_fingerprint"] = fp

    text = json.dumps(cfg, indent=2, sort_keys=True) + "\n"
    holes = sorted(set(PLACEHOLDER_RX.findall(text)))
    if holes:
        print(f"FAIL: placeholder markers remain in the frozen config: {holes}",
              file=sys.stderr)
        return 1

    data = text.encode("utf-8")
    digest = sha256_bytes(data)
    OUT.write_bytes(data)
    OUT.with_suffix(".json.sha256").write_text(digest + "\n", "utf-8")
    print("frozen config:", OUT.relative_to(ROOT))
    print("sha256:", digest)
    print("protocol_fingerprint:", fp)
    print("flip_draw seed:", flip_seed, "| rows_sha256:", draw.rows_sha256[:16] + "...")
    print("placeholder scan: clean")
    return 0


def install() -> int:
    frozen_bytes = OUT.read_bytes()
    digest = sha256_bytes(frozen_bytes)
    sidecar = OUT.with_suffix(".json.sha256").read_text("utf-8").split()[0]
    if digest != sidecar:
        print("FAIL: frozen config does not match its sidecar", file=sys.stderr)
        return 1
    cfg = json.loads(frozen_bytes.decode("utf-8"))
    if cfg.get("campaign_id") != CID:
        print(f"FAIL: unexpected campaign_id {cfg.get('campaign_id')!r}",
              file=sys.stderr)
        return 1

    live_cfg = STATE / "campaign_config.json"
    live_side = STATE / "campaign_config.sha256"
    if not live_cfg.exists() or not live_side.exists():
        print("FAIL: live state config/sidecar missing", file=sys.stderr)
        return 1
    live_sha = sha256_bytes(live_cfg.read_bytes())
    if live_sha != live_side.read_text("utf-8").strip():
        print("FAIL: live Campaign 3 config pin mismatch; refusing to touch",
              file=sys.stderr)
        return 1
    live = json.loads(live_cfg.read_text("utf-8"))
    if not str(live.get("campaign_id", "")).startswith("campaign-3"):
        print(f"FAIL: live config is {live.get('campaign_id')!r}, expected "
              "campaign-3; refusing to touch", file=sys.stderr)
        return 1

    # Archive the final Campaign 3 artifacts (campaign-2 precedent).
    arch_state = STATE / f"loop_state.{live['campaign_id']}.final.json"
    arch_cfg = STATE / f"campaign_config.{live['campaign_id']}.json"
    arch_side = STATE / f"campaign_config.{live['campaign_id']}.sha256"
    loop_state = STATE / "loop_state.json"
    for src, dst in ((loop_state, arch_state), (live_cfg, arch_cfg),
                     (live_side, arch_side)):
        if not src.exists():
            print(f"FAIL: cannot archive, missing {src.name}", file=sys.stderr)
            return 1
        if dst.exists():
            print(f"FAIL: archive target exists, refusing to overwrite: "
                  f"{dst.name}", file=sys.stderr)
            return 1
    shutil.copy2(loop_state, arch_state)
    shutil.copy2(live_cfg, arch_cfg)
    shutil.copy2(live_side, arch_side)

    # Install the frozen Campaign 4 config with a fresh hash-only pin.
    live_cfg.write_bytes(frozen_bytes)
    live_side.write_text(digest + "\n", "utf-8")
    # Fresh campaign: the loop self-initializes loop_state.json from the
    # config (campaign id, hash pin, seed_base) on its next run.
    loop_state.unlink()

    # Verify the way continuous_loop.campaign_sha() will.
    verified = sha256_bytes(live_cfg.read_bytes()) == \
        live_side.read_text("utf-8").strip()
    print("installed:", live_cfg.relative_to(ROOT))
    print("fresh pin:", digest)
    print("archived:", arch_state.name, "|", arch_cfg.name, "|", arch_side.name)
    print("loop_state.json removed (fresh campaign start):", not loop_state.exists())
    print("pin verified:", verified)
    return 0 if verified else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install", action="store_true",
                        help="install the frozen config into state/ "
                             "(archives Campaign 3 first)")
    args = parser.parse_args()
    if args.install:
        return install()
    return build()


if __name__ == "__main__":
    sys.exit(main())
