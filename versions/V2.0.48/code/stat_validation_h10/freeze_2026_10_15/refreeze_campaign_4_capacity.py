#!/usr/bin/env python3
"""Capacity-only re-freeze for Campaign 4 (2026-10-15, owner directive section 7).

Owner directive "Continue Campaign 4 Through Completion": complete the
30-execution target. Diagnosis of the binding constraint after the
generator repair: admissible candidates exist (37+ falsification-framed),
but the frozen *capacity* ceilings cap the campaign well below 30:

  * class budgets (falsification 18 / confirmatory 12 / exploration 9 /
    replication 6) are nearly or fully consumed, and
  * the proposal total (45) has only 19 slots left,

so the campaign would exhaust at roughly 19-21 of 30 executions.

This script raises ONLY execution-capacity ceilings:
  * policy_overrides.max_total_proposals
  * policy_overrides.class_budgets (per class, as passed)

Explicitly NOT touched (verified by diff before install):
the 0.35 falsification-share floor, max_replication_share, the six
promotion gates, recipe/duplicate layers, every stop condition, the
statistical method and its Case-A flip draw, budgets already consumed
(all 29+ created records keep counting - refusals are never erased), the
holdout policy, outcome-blindness inputs, census/precision references.

Consumption is preserved: raising a ceiling does not reset the used
counts; quota_state still counts every prior record against the new
ceiling, exactly as before.

Usage:
  py -3 refreeze_campaign_4_capacity.py --proposals 64 \
      --falsification 34 --confirmatory 14
  py -3 refreeze_campaign_4_capacity.py ... --install
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent.proposal_layer import schema  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
STATE = ROOT / "autonomous_agent/state"
SOURCE = STATE / "campaign_config.json"
OUT = HERE / "CAMPAIGN_4_CONFIG_CAPACITY_FROZEN_2026_10_15.json"

PLACEHOLDER_RX = re.compile(r"TO_BE_|_AT_FREEZE|-XX\b|DRAFT_ONLY|TBD|PLACEHOLDER",
                            re.I)
# The directives this amendment must leave byte-identical.
PROTECTED_TOP = ("multiplicity_policy", "holdout_policy", "duplicate_policy",
                 "outcome_blindness_policy", "portfolio", "stop_conditions",
                 "execution", "protocol_fingerprint", "campaign_id",
                 "seed_base", "immutable", "versions", "notes")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(args) -> int:
    live_bytes = SOURCE.read_bytes()
    digest = sha256_bytes(live_bytes)
    cfg = json.loads(live_bytes.decode("utf-8"))
    if cfg.get("campaign_id") != "campaign-4-continuous-2026-10-14":
        print("FAIL: unexpected campaign_id", file=sys.stderr)
        return 1

    before = {key: json.dumps(cfg.get(key), sort_keys=True)
              for key in PROTECTED_TOP}
    before_policy = json.dumps(cfg["policy_overrides"], sort_keys=True)

    overrides = cfg["policy_overrides"]
    old_proposals = overrides["max_total_proposals"]
    old_classes = dict(overrides["class_budgets"])
    overrides["max_total_proposals"] = int(args.proposals)
    classes = overrides["class_budgets"]
    for name in ("falsification", "confirmatory", "replication", "exploration"):
        value = getattr(args, name)
        if value is not None:
            if value < int(classes[name]):
                print(f"FAIL: refusing to LOWER {name} budget "
                      f"{classes[name]} -> {value}", file=sys.stderr)
                return 1
            classes[name] = int(value)

    old_executions = None
    if args.executions is not None:
        execution = cfg["execution"]
        old_executions = int(execution["max_total_executions"])
        if int(args.executions) < old_executions:
            print("FAIL: refusing to lower the execution budget",
                  file=sys.stderr)
            return 1
        execution["max_total_executions"] = int(args.executions)
        # `execution` is otherwise protected: prove nothing else moved.
        restored_exec = json.loads(before["execution"])
        restored_exec["max_total_executions"] = execution[
            "max_total_executions"]
        if execution != restored_exec:
            print("FAIL: non-capacity key changed inside execution",
                  file=sys.stderr)
            return 1
    elif json.dumps(cfg.get("execution"), sort_keys=True) != before["execution"]:
        print("FAIL: execution changed without --executions", file=sys.stderr)
        return 1

    cfg["refrozen_at_capacity"] = datetime.now(timezone.utc).isoformat(
        timespec="seconds")
    freeze = cfg.setdefault("_FREEZE_STATUS", {})
    amend = freeze.get("capacity_amendment")
    if amend is None:
        amend = {
            "date": "2026-10-15",
            "authority": (
                "Owner directive 'Continue Campaign 4 Through Completion' "
                "(2026-10-15): complete the 30-execution target; repair "
                "and resume under the required versioning and freeze "
                "rules; never weaken constraints merely to reach the "
                "target."),
            "diagnosis": (
                "After the generator repair the binding constraint is "
                "capacity, not admissibility: 37+ admissible "
                "falsification candidates exist, but the frozen class "
                "budgets and proposal total cap the campaign below 30 "
                "executions."),
            "consumption_preserved": (
                "Ceilings only: every already-created record (including "
                "all refusals) keeps counting against the raised "
                "ceilings; nothing is reset, erased, or recycled."),
            "untouched": (
                "min_falsification_share 0.35, max_replication_share, "
                "the six promotion gates, duplicate/recipe layers, 16 "
                "stop conditions, statistical method + Case-A flip "
                "draw, holdout SEALED, outcome-blind selection inputs, "
                "census/precision references, all prior adjudications."),
            "changes": [],
        }
        freeze["capacity_amendment"] = amend
    amend.setdefault("changes", []).append(
        f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}: "
        f"proposals {old_proposals} -> "
        f"{overrides['max_total_proposals']}; classes {old_classes} -> "
        f"{json.dumps(classes, sort_keys=True)}")

    for key in PROTECTED_TOP:
        if key == "execution":
            continue          # handled above with its own exact diff
        if json.dumps(cfg.get(key), sort_keys=True) != before[key]:
            print(f"FAIL: protected block changed: {key}", file=sys.stderr)
            return 1
    policy_changed = json.dumps(overrides, sort_keys=True) != before_policy
    exec_changed = old_executions is not None and \
        cfg["execution"]["max_total_executions"] != old_executions
    if not policy_changed and not exec_changed:
        print("FAIL: no capacity change produced", file=sys.stderr)
        return 1
    # Policy diff must touch ONLY the two capacity keys.
    restored = json.loads(before_policy)
    for key in list(overrides):
        if key not in ("max_total_proposals", "class_budgets"):
            if overrides[key] != restored.get(key):
                print(f"FAIL: non-capacity policy key changed: {key}",
                      file=sys.stderr)
                return 1
    if overrides["min_falsification_share"] != 0.35:
        print("FAIL: share floor changed", file=sys.stderr)
        return 1

    if args.executions is not None:
        amend.setdefault("changes", []).append(
            f"{datetime.now(timezone.utc).isoformat(timespec='seconds')}: "
            f"max_total_executions {old_executions} -> "
            f"{cfg['execution']['max_total_executions']} (target stays 30 "
            f"COMPLETED executions; H-8 counts an interrupted attempt "
            f"against the budget, and EXECUTION_INTERRUPTED records "
            f"already exist, so the budget must cover 30 completed plus "
            f"the recorded interruptions)")

    fp = schema.sha256_hex(schema.canonical_json(
        {k: v for k, v in cfg.items() if k != "protocol_fingerprint"}))
    cfg["protocol_fingerprint"] = fp
    text = json.dumps(cfg, indent=2, sort_keys=True) + "\n"
    holes = sorted(set(PLACEHOLDER_RX.findall(text)))
    if holes:
        print(f"FAIL: placeholders remain: {holes}", file=sys.stderr)
        return 1
    data = text.encode("utf-8")
    new_digest = sha256_bytes(data)
    OUT.write_bytes(data)
    OUT.with_suffix(".json.sha256").write_text(new_digest + "\n", "utf-8")
    print("capacity config:", OUT.relative_to(ROOT))
    print("source pin:", digest)
    print("new pin:", new_digest)
    print("protocol_fingerprint:", fp)
    print(f"budgets: proposals {old_proposals} -> "
          f"{overrides['max_total_proposals']} | classes {old_classes} -> "
          f"{json.dumps(classes, sort_keys=True)} | executions "
          f"{old_executions} -> "
          f"{cfg['execution']['max_total_executions']}")
    print("protected blocks: unchanged | placeholder scan: clean")
    return 0


def install() -> int:
    frozen_bytes = OUT.read_bytes()
    new_digest = sha256_bytes(frozen_bytes)
    if new_digest != OUT.with_suffix(".json.sha256").read_text(
            "utf-8").split()[0]:
        print("FAIL: frozen config/sidecar mismatch", file=sys.stderr)
        return 1
    live_bytes = SOURCE.read_bytes()
    live_digest = sha256_bytes(live_bytes)
    sidecar = (STATE / "campaign_config.sha256").read_text("utf-8").strip()
    if live_digest != sidecar:
        print("FAIL: live config/sidecar mismatch; refusing", file=sys.stderr)
        return 1
    if live_digest == new_digest:
        print("already installed")
        return 0

    loop_state_path = STATE / "loop_state.json"
    state = json.loads(loop_state_path.read_text("utf-8"))
    if state.get("campaign_config_sha256") != live_digest:
        print("FAIL: loop-state pin is not the current live digest; "
              "refusing", file=sys.stderr)
        return 1

    # Atomic replace: the loop may be mid-run; a torn read must be
    # impossible.
    tmp_cfg = SOURCE.with_suffix(".json.tmp")
    tmp_cfg.write_bytes(frozen_bytes)
    os.replace(tmp_cfg, SOURCE)
    tmp_side = (STATE / "campaign_config.sha256").with_suffix(".sha256.tmp")
    tmp_side.write_text(new_digest + "\n", "utf-8")
    os.replace(tmp_side, STATE / "campaign_config.sha256")

    from autonomous_agent.core import write_json_atomic
    state["campaign_config_sha256"] = new_digest
    write_json_atomic(loop_state_path, state)

    ok = sha256_bytes(SOURCE.read_bytes()) == \
        (STATE / "campaign_config.sha256").read_text("utf-8").strip()
    repinned = json.loads(loop_state_path.read_text("utf-8"))[
        "campaign_config_sha256"] == new_digest
    kept = json.loads(loop_state_path.read_text("utf-8"))
    print("installed, sidecar verified:", ok, "| loop-state re-pinned:",
          repinned)
    print("carried: cycle", kept.get("cycle"), "executions_done",
          kept.get("executions_done"), "status", kept.get("status"))
    return 0 if (ok and repinned) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=int, required=True)
    parser.add_argument("--executions", type=int)
    parser.add_argument("--falsification", type=int)
    parser.add_argument("--confirmatory", type=int)
    parser.add_argument("--replication", type=int)
    parser.add_argument("--exploration", type=int)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.install:
        return install()
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
