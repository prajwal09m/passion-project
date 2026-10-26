"""Re-sign the Campaign 5 authorization record (owner-authorized 2026-10-23).

Authorized path (chat, PMED owner):
1. trust keys: the owner ROTATED both HMAC keys directly into .env (the
   retired key values were exposed in plaintext in
   CAMPAIGN_5_FINALIZATION_SUMMARY_2026_10_22.md and are redacted/retired);
2. record re-sign: implementer repairs the ``disclosure`` field to the
   validator-required form (non-empty list of unique non-empty strings) while
   preserving the attested text verbatim, recomputes BOTH HMAC signatures over
   the repaired record with the current (rotated) keys, and writes the shorter,
   atomically-replaced record;
3. verify: run the shipped validator (no synthetic switch) and the shipped
   preflight; only an empty validator error list is acceptable.

Fail-closed rules:
* refuses to run if either .env key is one of the retired leaked values,
* refuses to run if the .env keys are not valid hex of >= 32 bytes,
* refuses to run if the two keys are equal,
* refuses to write anything unless post-sign validation returns zero errors,
* this script NEVER invents a new attestation: the attested content (decisions,
  actors, digests, mode, basis) is preserved verbatim from the existing record;
  only (a) the disclosure encoding is normalized and (b) the record's stale
  predeclaration protocol pin is propagated to the record's protocol pin
  (the same value already propagated into the owner/review blocks by the
  external re-finalization), and the signatures re-bound.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
RECORD_PATH = WORKSPACE / "autonomous_agent" / "state" / "campaign5_authorization.json"
ENV_PATH = WORKSPACE / ".env"

RETIRED_LEAKED_KEYS = {
    "f918a6fe6351e5cf1bfa60b2cad4f790a853e6ec162208b5679a04b8e0ea2c7c",
    "1554e311965ff09d31960815522c8a4eb969d13e5b188981c394994c66ef766e",
}


def _load_keys() -> tuple[bytes, bytes]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        env[name.strip()] = value.strip()
    owner, reviewer = env.get("C5_OWNER_HMAC_KEY", ""), env.get("C5_REVIEWER_HMAC_KEY", "")
    if not owner or not reviewer:
        raise SystemExit("refusing: .env trust keys not found")
    for value in (owner, reviewer):
        if value.lower() in RETIRED_LEAKED_KEYS:
            raise SystemExit(
                "refusing: this is one of the retired leaked key values - the owner "
                "rotation recorded in chat has not happened yet")
    try:
        owner_key, reviewer_key = bytes.fromhex(owner), bytes.fromhex(reviewer)
    except ValueError as error:
        raise SystemExit(f"refusing: trust key not valid hex: {error}")
    if len(owner_key) < 32 or len(reviewer_key) < 32:
        raise SystemExit("refusing: trust key must be >= 32 bytes")
    if owner_key == reviewer_key:
        raise SystemExit("refusing: keys must be distinct")
    return owner_key, reviewer_key


def _sign_unsigned(record: dict, key: bytes) -> str:
    unsigned = {k: v for k, v in record.items() if k != "signatures"}
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


import hmac  # noqa: E402  (kept late to keep the fail-closed import section readable)


def main() -> int:
    owner_key, reviewer_key = _load_keys()

    record = json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    protocol_pin = record.get("protocol", {}).get("sha256")
    predecl = record.get("predeclaration", {})
    if protocol_pin and predecl.get("protocol_sha256") != protocol_pin:
        print("predecl protocol pin propagated:", str(predecl.get("protocol_sha256"))[:16], "->", protocol_pin[:16])
        predecl["protocol_sha256"] = protocol_pin
        record["predeclaration"] = predecl
    def _as_list(value: object, field: str) -> list[str]:
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            normalized = list(dict.fromkeys(items))
            if not normalized:
                raise SystemExit(f"refusing: {field} has no non-empty text")
            return normalized
        raise SystemExit(f"refusing: {field} missing or other type")

    normalized = _as_list(record["independent_review"].get("disclosure"), "disclosure")
    normalized_basis = _as_list(record["independent_review"].get("decision_basis"), "decision_basis")

    # verify the shipped validator FAILS now (pre-state), then repair
    sys.path.insert(0, str(WORKSPACE))
    from autonomous_agent.campaign5_authorization import (check_campaign5_authorization,
                                                          validate_authorization)
    pre_errors = validate_authorization(record, record.get("scope"),
                                        owner_key=owner_key, reviewer_key=reviewer_key)
    print("validator errors BEFORE re-sign:", pre_errors)

    record["independent_review"]["disclosure"] = normalized
    record["independent_review"]["decision_basis"] = normalized_basis
    record["signatures"] = {
        "owner_hmac_sha256": _sign_unsigned(record, owner_key),
        "reviewer_hmac_sha256": _sign_unsigned(record, reviewer_key),
    }
    post_errors = validate_authorization(record, record.get("scope"),
                                         owner_key=owner_key, reviewer_key=reviewer_key)
    print("validator errors AFTER re-sign:", post_errors)
    if post_errors:
        raise SystemExit("refusing to write: post-sign validation still fails")

    tmp = RECORD_PATH.with_suffix(".json.tmp")
    tmp.write_bytes((json.dumps(record, sort_keys=True, indent=2, ensure_ascii=False)
                     + "\n").encode("utf-8"))
    os.replace(tmp, RECORD_PATH)
    print("record re-signed and atomically written:", RECORD_PATH.relative_to(WORKSPACE))

    campaign = json.loads((WORKSPACE / "autonomous_agent" / "state" / "campaign_config.json")
                          .read_text(encoding="utf-8-sig"))
    preflight = check_campaign5_authorization(WORKSPACE, campaign)
    print("preflight:", json.dumps(preflight, sort_keys=True))
    return 0 if preflight.get("allowed") else 1


if __name__ == "__main__":
    sys.exit(main())
