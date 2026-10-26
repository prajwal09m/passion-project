"""Reusable campaign-end multiplicity finalization for future campaigns.

Finding F-1 of the independent audit (``stat_validation_h10/
C4_POST_REMEDIATION_INDEPENDENT_AUDIT_2026_10_16.md``): the third
measurement-wiring link — campaign-end consumption of persisted
per-member records — existed only inside tests, with no production
finalization caller.  The historical one-shot builder
(``campaign_end_2026_10_16/build_multiplicity_record.py``) predates the
measurement wiring: it constructed every predeclared member as
``unavailable`` from the ledger alone and never called
``family_records``.  That builder produced Campaign 4's append-only
record and is retained untouched as the record of how that artifact was
produced; it must never be rerun or overwritten against persistent
historical state.  This module is the reviewed successor entry point for
FUTURE campaigns.

Data flow this successor completes (audit task section 2, points 1-8):

  1. ordinary execution (``python -m autonomous_agent.experiments.
     run_experiment``) produces per-member measurements under
     ``outputs/evaluation.json`` -> ``results.family_measurements``;
  2. the adapter durably persists them in
     ``autonomous_agent/candidates/<experiment_id>/result.json`` under
     ``metrics.family_measurements`` (surviving workspace destruction);
  3. this finalization loads and validates those persisted records
     through ``stat_validation_h10/family_records.py``;
  4. family / member / experiment / comparison association is verified
     against the frozen family table and the frozen ladders;
  5. available members receive their unadjusted p-values from the
     approved ``week_level_signflip_holm`` implementation, computed
     from the persisted records with the campaign's own recorded flip
     draw (inside ``family_records.family_members_from_records``);
  6. unavailable members follow C-2 Option A (count toward m at
     p = 1.0, never formally REFUTED);
  7. the frozen Holm step-down consumes the complete family via
     ``family_records.campaign_end_record``;
  8. missing, incomplete, malformed, or mismatched required data
     prevents successful finalization (fail-closed contract below).

Fail-closed contract:

* A poolable experiment whose durable ``result.json`` exists but
  carries no usable ``family_measurements`` block raises
  ``family_records.MemberRecordError`` — finalization can never fall
  back to pooled-only results and still report a completed family
  evaluation (the defect class F-1 exists to prevent).
* An *adjudicated* experiment with no durable result at all raises
  :class:`FinalizationError` — required persisted measurements are
  absent and are never defaulted to unavailable.
* Only an experiment whose ledger record shows execution never produced
  a durable result (interrupted before adjudication, recorded as
  FAILED_EXECUTION) maps to the frozen C-2 Option A unavailable
  treatment, with the recorded reason — the same convention the
  historical builder applied to interrupted executions.
* Config pin (sidecar sha256), campaign-id match, the approved-method
  choke point, H-10b floors (n_boot / n_flips), the owner-frozen C-2
  policy flags, family bounds, feasibility, duplicate member ids, and
  block family/primitive association are all verified through the
  frozen modules before anything is written.
* Writes go through ``family_records.append_record`` (append-only,
  fsynced, refuses a second record for the same campaign) and are read
  back for verification.  If a record for the campaign already exists,
  a fresh recomputation must equal it exactly or finalization refuses;
  it never re-decides history.

The statistics remain exactly where the frozen architecture put them:
this module performs none of its own.  Import boundary: this file lives
on the stat-validation side (beside the multiplicity machinery and the
consumption module); the execution side never imports it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
for _path in (str(_ROOT), str(_HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import family_records as fr                                    # noqa: E402
from autonomous_agent import three_valued as tv                # noqa: E402


class FinalizationError(Exception):
    """Required campaign-end inputs are missing, mismatched, or inadmissible."""


def load_campaign_config(campaign_id: str, config_path: Path,
                         sidecar_path: Path | None = None
                         ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and verify the frozen campaign config (pin + policy, fail-closed).

    Returns ``(config, policy)`` where ``policy`` carries the verified
    ``n_boot``, ``n_flips``, recorded flip-draw ``W``, and config pin.
    """
    config_path = Path(config_path)
    try:
        config_bytes = config_path.read_bytes()
    except OSError as error:
        raise FinalizationError(
            f"cannot read campaign config {config_path}: {error}") from error
    try:
        config = json.loads(config_bytes)
    except ValueError as error:
        raise FinalizationError(
            f"campaign config {config_path} is not valid JSON: {error}"
        ) from error
    if not isinstance(config, dict):
        raise FinalizationError(
            f"campaign config {config_path} is not a JSON object")
    if config.get("campaign_id") != campaign_id:
        raise FinalizationError(
            f"campaign config {config_path} declares campaign_id "
            f"{config.get('campaign_id')!r}, expected {campaign_id!r}")
    pin = hashlib.sha256(config_bytes).hexdigest()
    sidecar = Path(sidecar_path) if sidecar_path is not None \
        else config_path.with_suffix(".sha256")
    if not sidecar.is_file():
        raise FinalizationError(
            f"campaign config pin sidecar is missing: {sidecar}; a frozen "
            "campaign config must ship its recorded sha256 pin")
    recorded = sidecar.read_text("utf-8").split()
    if not recorded or recorded[0] != pin:
        raise FinalizationError(
            f"config pin {pin} does not match the recorded sidecar pin "
            f"{recorded[0] if recorded else '<empty>'}: this is not the "
            "frozen campaign config")
    policy_block = config.get("multiplicity_policy")
    if not isinstance(policy_block, dict):
        raise FinalizationError(
            "campaign config has no multiplicity_policy mapping")
    try:
        n_boot = int(policy_block["n_boot"])
        flip_draw = policy_block["flip_draw"]
        n_flips = int(flip_draw["M"])
        flip_w = int(flip_draw["W"])
    except (KeyError, TypeError, ValueError) as error:
        raise FinalizationError(
            f"malformed multiplicity_policy (n_boot/flip_draw): {error}"
        ) from error
    if n_boot < fr.MIN_N_BOOT:
        raise FinalizationError(
            f"n_boot {n_boot} is below the H-10b floor {fr.MIN_N_BOOT}")
    if n_flips < fr.MIN_N_FLIPS:
        raise FinalizationError(
            f"n_flips {n_flips} is below the H-10b floor {fr.MIN_N_FLIPS}")
    if policy_block.get("missing_member_rule") != "C-2_option_A":
        raise FinalizationError(
            "multiplicity_policy.missing_member_rule must be the "
            "owner-frozen 'C-2_option_A'; got "
            f"{policy_block.get('missing_member_rule')!r}")
    if float(policy_block.get("missing_member_p", -1.0)) != 1.0:
        raise FinalizationError(
            "multiplicity_policy.missing_member_p must be 1.0 "
            f"(C-2 Option A); got {policy_block.get('missing_member_p')!r}")
    if policy_block.get("campaign_end_record_required") is not True:
        raise FinalizationError(
            "multiplicity_policy.campaign_end_record_required must be "
            "true: this workflow exists to build the mandatory "
            "finalization record")
    # Fail-closed choke point: exactly the owner-recorded method passes.
    fr.require_approved_method(fr.APPROVED_P_VALUE_METHOD)
    return config, {"n_boot": n_boot, "n_flips": n_flips,
                    "flip_w": flip_w, "pin": pin}


def poolable_executed_experiments(ledger_path: Path,
                                  campaign_id: str) -> list[dict[str, Any]]:
    """Every executed, poolable proposal of this campaign, with its experiment id.

    Mirrors the historical builder's ledger derivation (proposals plus
    EXECUTED/ADJUDICATED transitions pinned to ``campaign_id``), but
    the experiment id is resolved from the transitions themselves — the
    EXECUTION_STARTED detail always carries it, so interrupted
    executions no longer need the registry-substring fallback.
    """
    ledger_path = Path(ledger_path)
    try:
        raw = ledger_path.read_text("utf-8")
    except OSError as error:
        raise FinalizationError(
            f"cannot read proposal ledger {ledger_path}: {error}") from error
    proposals: dict[str, dict[str, Any]] = {}
    details: dict[str, list[dict[str, Any]]] = {}
    executed: set[str] = set()
    adjudicated: set[str] = set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("row_type") == "proposal":
            proposals[str(row.get("proposal_id"))] = row.get("proposal") or {}
        elif row.get("row_type") == "transition":
            detail = row.get("detail") or {}
            if detail.get("campaign_id") != campaign_id:
                continue
            pid = str(row.get("proposal_id"))
            details.setdefault(pid, []).append(detail)
            if row.get("to") == "EXECUTED":
                executed.add(pid)
            elif row.get("to") == "ADJUDICATED":
                adjudicated.add(pid)
    entries: list[dict[str, Any]] = []
    for pid in sorted(executed):
        design = (proposals.get(pid) or {}).get("design") or {}
        primitives = [entry.get("primitive_id")
                      for entry in (design.get("primitives") or [])]
        poolable = [p for p in primitives if p in fr.PRIMITIVE_TO_FAMILY]
        if not poolable:
            continue
        experiment_id = ""
        for detail in reversed(details.get(pid, [])):
            candidate = str(detail.get("experiment_id") or "")
            if candidate:
                experiment_id = candidate
                break
        if not experiment_id:
            raise FinalizationError(
                f"executed proposal {pid} of campaign {campaign_id!r} "
                "carries no experiment id in its ledger transitions; "
                "finalization cannot locate its persisted measurements "
                "and refuses to guess")
        # F-6: the ledger's recorded specification identity for this
        # experiment (the authoritative join source for the persisted
        # block's identity).  Conflicting recorded values are refused,
        # not guessed between; absence is carried as None and fails
        # closed only where a persisted block must actually be consumed.
        spec_shas = sorted({str(detail.get("spec_sha256")) for detail
                            in details.get(pid, [])
                            if detail.get("spec_sha256")})
        if len(spec_shas) > 1:
            raise FinalizationError(
                f"executed proposal {pid} of campaign {campaign_id!r} "
                f"records conflicting spec_sha256 values in the append-only "
                f"proposal ledger: {spec_shas}; finalization refuses to "
                "choose between them")
        entries.append({"proposal_id": pid, "experiment_id": experiment_id,
                        "primitives": poolable,
                        "spec_sha256": (spec_shas[0] if spec_shas else None),
                        "adjudicated": pid in adjudicated})
    return entries


_UNAVAILABLE_NOTE = (
    "predeclared member; the executed experiment's ledger record shows "
    "it never produced a durable result (interrupted before a durable "
    "result existed), so no per-member delta/CI/week-level g exists in "
    "any artifact; C-2 Option A: counts toward m at p=1.0, never "
    "formally REFUTED")


def build_campaign_end_record(campaign_id: str, *,
                              config_path: Path, ledger_path: Path,
                              candidates_root: Path,
                              sidecar_path: Path | None = None
                              ) -> dict[str, Any]:
    """Compute the campaign-end record from persisted measurements (no write).

    Returns ``{"record", "inventory", "family_sizes"}``.  Raises a
    fail-closed exception on any missing / incomplete / malformed /
    mismatched input: ``family_records.MemberRecordError`` from the
    consumption module, ``signflip.FlipProvenanceMissing`` from the
    recorded-draw loader, ``MultiplicityError`` /
    ``GranularityInfeasible`` from the frozen multiplicity API, or
    :class:`FinalizationError` for ledger/config association problems.
    """
    config, policy = load_campaign_config(
        campaign_id, Path(config_path), sidecar_path)
    entries = poolable_executed_experiments(Path(ledger_path), campaign_id)
    if not entries:
        raise FinalizationError(
            f"campaign {campaign_id!r} has no executed poolable "
            "experiments in its ledger; a finalization record cannot be "
            "built from absent evidence")

    blocks_and_ids: list[tuple[dict[str, Any], str]] = []
    identity_authority: dict[str, dict[str, Any]] = {}
    pending_unavailable: list[tuple[str, str, str, str]] = []
    inventory: dict[str, list[dict[str, Any]]] = {"persisted": [],
                                                  "unavailable": []}
    seen_member_ids: set[str] = set()
    candidates_root = Path(candidates_root)
    for entry in entries:
        experiment_id = entry["experiment_id"]
        for primitive in entry["primitives"]:
            family = fr.PRIMITIVE_TO_FAMILY[primitive]
            ladder = tv.ladder_for(primitive)
            if ladder.get("family") != family:
                raise FinalizationError(
                    f"frozen ladder for {primitive!r} disagrees with the "
                    f"frozen family table ({ladder.get('family')!r} vs "
                    f"{family!r}); refusing to continue")
            rungs = [str(rung) for rung in ladder["rungs"]]
            for rung in rungs:
                member_id = f"{experiment_id}:{rung}"
                if member_id in seen_member_ids:
                    raise FinalizationError(
                        f"duplicate predeclared member {member_id!r} "
                        "across executed proposals; the complete-family "
                        "bookkeeping would double count, so finalization "
                        "refuses")
                seen_member_ids.add(member_id)
            result_path = candidates_root / experiment_id / "result.json"
            if result_path.is_file():
                # F-6: recompute the authoritative configuration /
                # specification identity BEFORE trusting the persisted
                # record (spec.json vs the ledger's recorded spec_sha256,
                # and the configuration hash the spec installs).  Missing
                # or malformed sources fail closed here.
                identity_authority[experiment_id] = (
                    fr.load_authoritative_identity(
                        experiment_id,
                        spec_path=(candidates_root / experiment_id
                                   / "spec.json"),
                        ledger_spec_sha256=entry.get("spec_sha256")))
                # Fail-closed validation (schema, firewall, ladder,
                # complete member set, linear form, week index, draw).
                block = fr.load_member_block(result_path)
                if block.get("family") != family \
                        or block.get("primitive_id") != primitive:
                    raise FinalizationError(
                        f"persisted block for experiment {experiment_id!r} "
                        "declares family/primitive "
                        f"{block.get('family')!r}/{block.get('primitive_id')!r} "
                        f"but the ledger predeclares {family!r}/"
                        f"{primitive!r}: measurement association mismatch "
                        "refused")
                blocks_and_ids.append((block, experiment_id))
                inventory["persisted"].append(
                    {"experiment_id": experiment_id, "family": family,
                     "primitive": primitive, "result_json": str(result_path)})
            elif entry["adjudicated"]:
                raise FinalizationError(
                    f"experiment {experiment_id!r} was adjudicated but "
                    f"its durable result.json is missing ({result_path}): "
                    "required persisted measurements are absent; "
                    "finalization refuses to record its members as "
                    "unavailable by default")
            else:
                for rung in rungs:
                    pending_unavailable.append(
                        (family, primitive, experiment_id, rung))
                    inventory["unavailable"].append(
                        {"experiment_id": experiment_id, "family": family,
                         "primitive": primitive, "member_key": rung,
                         "reason": "interrupted_without_durable_result"})

    families: dict[str, list[Any]] = {}
    if blocks_and_ids:
        # Approved-method unadjusted p-values, C-2 mapping, and
        # week-index / flip-draw verification all happen inside the
        # consumption module with the campaign's own recorded draw.
        families = fr.family_members_from_records(
            blocks_and_ids, campaign_config=config,
            identity_authority=identity_authority)
    for family, primitive, experiment_id, rung in pending_unavailable:
        families.setdefault(family, []).append(fr.FamilyMember(
            member_id=f"{experiment_id}:{rung}", family=family,
            primitive=primitive, experiment_id=experiment_id,
            status=fr.STATUS_UNAVAILABLE, note=_UNAVAILABLE_NOTE))
    if not families:
        raise FinalizationError(
            f"campaign {campaign_id!r} produced no family members to "
            "finalize (no persisted blocks, no recorded interruptions)")

    n_boot = policy["n_boot"]
    n_flips = policy["n_flips"]
    ledger_sha256 = hashlib.sha256(
        Path(ledger_path).read_bytes()).hexdigest()
    record = fr.campaign_end_record(
        campaign_id=campaign_id, families=families, n_boot=n_boot,
        n_flips=n_flips, p_value_method=fr.APPROVED_P_VALUE_METHOD,
        ledger_sha256=ledger_sha256)
    return {"record": record, "inventory": inventory,
            "family_sizes": {name: len(members)
                             for name, members in sorted(families.items())}}


def finalize_campaign_end(campaign_id: str, *, out_path: Path,
                          config_path: Path, ledger_path: Path,
                          candidates_root: Path,
                          sidecar_path: Path | None = None,
                          dry_run: bool = False) -> dict[str, Any]:
    """Compute, (idempotently) write, and verify the campaign-end record.

    Returns the ``build_campaign_end_record`` outcome plus
    ``written`` (bool).  Append-only: an existing record for this
    campaign must equal a fresh recomputation exactly, otherwise
    finalization refuses; a duplicate is never written.
    """
    outcome = build_campaign_end_record(
        campaign_id, config_path=Path(config_path),
        ledger_path=Path(ledger_path), candidates_root=Path(candidates_root),
        sidecar_path=sidecar_path)
    record = outcome["record"]
    out_path = Path(out_path)
    existing = fr.read_records(out_path)
    mine = [row for row in existing
            if str(row.get("campaign_id")) == campaign_id]
    if mine:
        if dict(mine[0]) != record:
            raise FinalizationError(
                f"the append-only record for {campaign_id!r} already in "
                f"{out_path} differs from a recomputation computed from "
                "the persisted inputs; refusing to write (append-only "
                "history is never re-decided)")
        outcome["written"] = False
        return outcome
    if dry_run:
        outcome["written"] = False
        return outcome
    fr.append_record(out_path, record)     # MultiplicityError on foreign rows
    written = fr.read_records(out_path)
    if not any(dict(row) == record for row in written
               if str(row.get("campaign_id")) == campaign_id):
        raise FinalizationError(
            f"readback verification failed for {out_path}: the appended "
            "record does not match the computation")
    outcome["written"] = True
    return outcome


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the owner-run campaign-end finalization step."""
    parser = argparse.ArgumentParser(
        description="Campaign-end multiplicity finalization for a future "
                    "campaign: consumes persisted v1.1.0 family "
                    "measurements through family_records (append-only, "
                    "fail-closed).  Never reruns the Campaign 4 one-shot "
                    "builder and never writes when anything required is "
                    "missing.")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--root", type=Path, default=_ROOT)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--candidates", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true",
                        help="compute and verify everything; write nothing")
    args = parser.parse_args(argv)
    state = args.root / "autonomous_agent" / "state"
    config_path = args.config or state / "campaign_config.json"
    ledger_path = args.ledger or state / "proposal_ledger.jsonl"
    candidates_root = args.candidates or \
        args.root / "autonomous_agent" / "candidates"
    out_path = args.out or state / "campaign_end_multiplicity.jsonl"
    try:
        outcome = finalize_campaign_end(
            args.campaign_id, out_path=out_path, config_path=config_path,
            ledger_path=ledger_path, candidates_root=candidates_root,
            dry_run=args.dry_run)
    except Exception as error:  # noqa: BLE001 - the CLI fails closed
        print(f"FINALIZATION REFUSED ({type(error).__name__}): {error}",
              file=sys.stderr)
        return 1
    record = outcome["record"]
    record_exists = any(
        str(row.get("campaign_id")) == args.campaign_id
        for row in fr.read_records(out_path))
    summary: dict[str, Any] = {
        "campaign_id": args.campaign_id,
        "out": str(out_path),
        "dry_run": args.dry_run,
        "written": outcome["written"],
        "record_exists": record_exists,
        "family_sizes": outcome["family_sizes"],
        "persisted_experiments": len(outcome["inventory"]["persisted"]),
        "interrupted_members_recorded_unavailable":
            len(outcome["inventory"]["unavailable"]),
    }
    if record_exists:
        # The formal vocabulary is printed only once the campaign-end
        # record actually exists (provisional-to-formal firewall).
        statuses: dict[str, int] = {}
        for family in record["families"].values():
            for member in family["members"]:
                key = str(member.get("formal_status"))
                statuses[key] = statuses.get(key, 0) + 1
        summary["formal_statuses"] = statuses
        summary["formal_refuted"] = fr.formal_refuted_members(record)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
