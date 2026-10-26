"""Campaign 5 configuration freeze (Option D: Regime/Error Analysis).

Mirrors the C4 refreeze precedent (stat_validation_h10/freeze_2026_10_15/
refreeze_campaign_4_config.py). Runs fail-closed:

* refuses to run unless every freeze-time input is final (the draft's
  campaign_id/created_at/seed_base are already final; its
  protocol_fingerprint placeholder is replaced here),
* enforces the recorded digest conventions (see
  autonomous_agent/MAIN AUDITS AND REFLECTIONS/
  CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md,
  "Digest Finalization Convention"):
  - protocol_fingerprint = SHA-256(canonical_json(config minus
    protocol_fingerprint key)), computed while protocol_sha256 is not yet
    present; then protocol_sha256 = protocol_fingerprint,
  - signflip feasibility rule checked per declared family (fail-closed),
* scans the serialized frozen config for placeholders before writing,
* writes LF-only bytes (the C4 CRLF trap) and pins both the artifact and
  its sidecar,

By default this script performs a DRY FREEZE: it writes the frozen artifact
and sidecar into stat_validation_h10/freeze_2026_10_22/ and prints digests.
It does NOT install into autonomous_agent/state/ and does NOT create any
authorization record. Installing the frozen config into the live state
(``--install``) requires an explicit owner authorization documentation record
and must happen only after the owner approves the frozen content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DRAFT_PATH = (WORKSPACE /
              "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
              "CAMPAIGN_5_CONFIG_DRAFT_OPTION_D_2026_10_22.json")
OUT_DIR = Path(__file__).resolve().parent
FROZEN_ARTIFACT = OUT_DIR / "CAMPAIGN_5_CONFIG_FROZEN_2026_10_22.json"
STATE_CONFIG = WORKSPACE / "autonomous_agent/state/campaign_config.json"
STATE_SIDECAR = WORKSPACE / "autonomous_agent/state/campaign_config.sha256"

# Byte-identical to the record scope object in
# CAMPAIGN_5_AUTHORIZATION_PREDECLARATION_2026_10_22.md. The shipped
# validator requires scope.operations to be a subset of EVERY permitted
# dataset's operations; the two datasets intersect only at "read".
AUTHORIZATION_SCOPE = {
    "model_families": ["LightGBM", "LogisticRegression"],
    "candidate_generation_method": "deterministic_recipe",
    "comparisons": ["nested_feature_arms", "regime_conditional",
                    "error_cluster", "calibration"],
    "measurements": ["pooled_oof_auc", "regime_auc", "brier_score", "ece",
                     "error_cluster_stats"],
    "operations": ["read"],
    "permitted_changes": ["add_primitives", "modify_regime_parameters"],
}

PROTOCOL_ID = "protocol-demand-zone-ai-c5-regime-error"
PROTOCOL_VERSION = "1.0"

STALE_PLACEHOLDER_RE = re.compile(
    r"TO_BE_COMPUTED|TO_BE_SET|DRAFT_NOT_COMPUTED|NOT_APPROVED,", re.I)


def canonical_json(obj) -> str:
    # Identical encoding to proposal_layer.schema.canonical_json and to the
    # authorization validator's canonical_bytes (ensure_ascii is Python's
    # default True, allow_nan never triggered by this config).
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_draft(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    required_final = ("campaign_id", "created_at", "seed_base")
    missing = [k for k in required_final
               if not isinstance(cfg.get(k), (str, int)) or not str(cfg.get(k)).strip()]
    if missing:
        raise SystemExit(f"freeze blocked: pre-freeze fields not final: {missing}")
    if cfg.get("protocol_fingerprint") != "DRAFT_NOT_COMPUTED":
        raise SystemExit("freeze blocked: draft protocol_fingerprint is not the expected placeholder")
    if cfg.get("immutable") is not False:
        raise SystemExit("freeze blocked: draft config is already immutable / already frozen")
    if "protocol_sha256" in cfg or "authorization_scope" in cfg:
        raise SystemExit("freeze blocked: draft already carries freeze-only keys")
    return cfg


def check_signflip_feasibility(cfg: dict) -> None:
    mp = cfg.get("multiplicity_policy") or {}
    try:
        n_boot = int(mp["n_boot"])
        n_flips = int(mp["n_flips"])
        max_m = int(mp.get("max_family_size_m", 0))
    except (KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"freeze blocked: multiplicity_policy incomplete: {error}")
    bounds = [max_m] + [int(f.get("member_bound", 0))
                        for f in (mp.get("families") or {}).values()]
    for m in bounds:
        if m <= 0:
            continue
        if not (n_boot + 1 >= 20 * m and n_flips + 1 >= 20 * m):
            raise SystemExit(
                f"freeze blocked: signflip feasibility fails for m={m} "
                f"(need n+1 >= 20*m with n_boot={n_boot}, n_flips={n_flips})")


def finalize(cfg: dict) -> dict:
    frozen = json.loads(json.dumps(cfg, sort_keys=False))
    frozen.pop("_NOTE", None)  # draft-only status note; _FREEZE_STATUS replaces it
    frozen["protocol_id"] = PROTOCOL_ID
    frozen["protocol_version"] = PROTOCOL_VERSION
    frozen["authorization_scope"] = AUTHORIZATION_SCOPE
    frozen["immutable"] = True
    frozen["parent_champion"] = frozen.get("parent_champion", "V2.0.61")
    frozen["_FREEZE_STATUS"] = {
        "state": "FROZEN_2026_10_22",
        "campaign_id": frozen["campaign_id"],
        "base_protocol": "campaign-4-continuous-2026-10-14",
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "derived_from": (
            "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
            "CAMPAIGN_5_CONFIG_DRAFT_OPTION_D_2026_10_22.json (draft digest sanity "
            "de486a48d276f73fc118c1224e572cff884bf96971a8bb80e7149ce3b5d0e3e4)"),
        "digest_conventions": (
            "protocol_fingerprint = sha256(canonical_json(config minus the "
            "protocol_fingerprint key), computed before protocol_sha256 exists; "
            "then protocol_sha256 = protocol_fingerprint; scope_sha256 uses the "
            "authorization validator's sha256_json encoding; see the "
            "predeclaration's Digest Finalization Convention"),
        "review_mode_basis": (
            "reviewer attestation mode ai_substitute_owner_authorized per the "
            "owner's signed C5_OWNER_DECISION_AI_REVIEW_ACCEPTANCE_2026_10_22.md "
            "and the 2026-10-22 owner-authorized validator amendment "
            "(CAMPAIGN5_REVIEW_MODE_AMENDMENT_2026_10_22.md)"),
        "install_status": (
            "recorded by the sidecar/digest it accompanies; _FREEZE_STATUS text "
            "is stage-independent and never claims an install it did not do"),
        "frozen_by": "coding agent staging the owner-authorized C5 finalization; "
                     "install and record creation require explicit owner action",
    }
    return frozen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate everything and print computed digests "
                             "without writing any file (default behavior)")
    parser.add_argument("--write-artifact", action="store_true",
                        help="stage the frozen config artifact plus sidecar in "
                             "stat_validation_h10/freeze_2026_10_22/ (requires "
                             "recorded owner approval of the draft content)")
    parser.add_argument("--install", action="store_true",
                        help="also install the frozen config into "
                             "autonomous_agent/state/ (requires prior owner "
                             "authorization documentation)")
    args = parser.parse_args()
    if args.install and not args.write_artifact:
        raise SystemExit("--install requires --write-artifact")

    draft = load_draft(DRAFT_PATH)
    check_signflip_feasibility(draft)
    frozen = finalize(draft)

    no_fp = {k: v for k, v in frozen.items() if k != "protocol_fingerprint"}
    fp = sha256_bytes(canonical_json(no_fp).encode("utf-8"))
    frozen["protocol_fingerprint"] = fp
    frozen["protocol_sha256"] = fp

    payload = (json.dumps(frozen, sort_keys=True, indent=2,
                          ensure_ascii=False) + "\n").encode("utf-8")
    text = payload.decode("utf-8")
    hits = sorted(set(STALE_PLACEHOLDER_RE.findall(text)))
    if hits:
        raise SystemExit(f"freeze blocked: placeholder scan hits: {hits}")

    artifact_sha = sha256_bytes(payload)

    print("fingerprint_would_be (= would-be protocol_sha256):", fp)
    print("frozen artifact sha256 (would be):", artifact_sha)
    if not args.write_artifact:
        print("mode: check-only; nothing written")
        return 0

    artifact = OUT_DIR / FROZEN_ARTIFACT.name
    artifact.write_bytes(payload)
    artifact_sha_written = sha256_bytes(artifact.read_bytes())
    (OUT_DIR / (FROZEN_ARTIFACT.name + ".sha256")).write_bytes(
        (artifact_sha_written + "\n").encode("ascii"))

    print("frozen artifact:", artifact.relative_to(WORKSPACE))
    print("frozen artifact sha256:", artifact_sha_written)
    if args.install:
        STATE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        STATE_CONFIG.write_bytes(payload)
        STATE_SIDECAR.write_bytes((artifact_sha_written + "\n").encode("ascii"))
        print("installed:", STATE_CONFIG.relative_to(WORKSPACE), "with sidecar pin")
    else:
        print("install_status: NOT_INSTALLED (use --install only with recorded owner authorization)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
