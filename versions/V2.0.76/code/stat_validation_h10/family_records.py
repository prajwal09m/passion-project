"""Campaign-end consumption of persisted v1.1.0 family measurements.

Remediation of the Campaign 4 measurement-wiring finding (owner decision
2026-10-16, ``C4_MEASUREMENT_WIRING_FINDING_OWNER_DECISION_RECORD_2026_10_16.md``):
this module is the third wiring link — it reads the per-member records an
ordinary v1.1.0 experiment execution persisted under
``results.family_measurements`` (in ``outputs/evaluation.json`` and,
durably, in the candidate's ``result.json``), validates them against the
frozen family table and ladders, and builds the
``multiplicity.FamilyMember`` inputs the campaign-end record consumes.

Placement (2026-10-16): this module deliberately lives on the
stat-validation side, beside the multiplicity machinery it delegates to
(the same boundary ``build_multiplicity_record.py`` operates under).  The
execution side (``autonomous_agent/recipe_harness.py``) may not import
the multiplicity machinery at all (T12 / freeze import boundary —
enforced by ``test_freeze_integrity`` and ``test_proposal_layer``), so
the producer stamps records and the consumer, on this side, validates
and consumes them.  A thin re-export facade below keeps callers (owner-
side finalization scripts, wiring acceptance tests) from touching the
multiplicity modules directly.

Contract (fail-closed; every check raises :class:`MemberRecordError`):

* The block schema, family, and primitive must match the frozen
  ``multiplicity.FAMILIES`` table and the frozen ladders.
* The member set must be complete (every frozen-ladder rung present,
  ``member_set_complete`` true) — a partial set is refused, never
  reduced, never assumed.
* Every ``ok`` member's sign-flip payload must satisfy the frozen linear
  form identity (``sum(g) == 2 * n_pos * n_neg * delta_hat``) and the
  member's week alignment must match the campaign's recorded flip draw
  (``W``), so ``signflip.signflip_p_value`` computes the unadjusted
  p-value from the persisted record with the campaign's own draw.
* Every consumed block's experiment identity is cross-checked (F-6)
  against the authoritative ``spec.json`` the adapter executed and the
  append-only ledger's recorded ``spec_sha256``; a missing, malformed, or
  mismatched source of truth fails closed — no hash is ever invented.
* ``unavailable`` members map to the frozen C-2 Option A treatment:
  they count toward ``m`` at p = 1.0 and can never be formally refuted.
* The bare formal-refutation label may never appear in a consumed block
  (the provisional-to-formal firewall).

Nothing here computes new statistics beyond the approved
``week_level_signflip_holm`` unadjusted p-value; the Holm adjustment is
``multiplicity.campaign_end_record``'s job alone.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    # Same bootstrap every stat_validation_h10 script uses to reach the
    # reviewed autonomous_agent modules (see build_multiplicity_record.py).
    sys.path.insert(0, str(_ROOT))

from autonomous_agent import hardening                             # noqa: E402
from autonomous_agent import three_valued as tv                     # noqa: E402
from autonomous_agent.proposal_layer import multiplicity as mult    # noqa: E402
from autonomous_agent.proposal_layer import signflip                # noqa: E402

SCHEMA = "family_members_v1"

# -- consumption-side facade -----------------------------------------------
# Re-exports so callers (owner-side finalization scripts, wiring tests)
# never import the multiplicity machinery directly; every value is the
# frozen module's own, reached through this module only.
FAMILIES = mult.FAMILIES
FORMAL_REFUTED = mult.FORMAL_REFUTED
FORMAL_INCONCLUSIVE = mult.FORMAL_INCONCLUSIVE
FORMAL_UNAVAILABLE = mult.FORMAL_UNAVAILABLE
STATUS_AVAILABLE = mult.STATUS_AVAILABLE
STATUS_UNAVAILABLE = mult.STATUS_UNAVAILABLE
REFUTATION_SIGNAL_VALUE = mult.REFUTATION_SIGNAL_VALUE
LABEL_PROVISIONAL_REFUTATION = mult.LABEL_PROVISIONAL_REFUTATION
LABEL_NO_SIGNAL = mult.LABEL_NO_SIGNAL
FirewallViolation = mult.FirewallViolation
APPROVED_P_VALUE_METHOD = signflip.APPROVED_METHOD_NAME
campaign_end_record = mult.campaign_end_record
load_campaign_flip_draw = signflip.load_campaign_flip_draw
draw_flips = signflip.draw_flips

# -- F-1 (C4 post-remediation audit 2026-10-16, finding F-1) ---------------
# The reusable campaign-end finalization successor
# (``campaign_end_finalization.py``) reaches every frozen API it needs
# through this facade, so this module stays the single consumption-side
# entry point and the finalization path never imports the multiplicity
# machinery directly.  Pure re-exports of the frozen module's own
# objects: no statistics, no behavior change to anything above.
FamilyMember = mult.FamilyMember
append_record = mult.append_record
read_records = mult.read_records
require_feasible = mult.require_feasible
require_approved_method = mult.require_approved_method
PRIMITIVE_TO_FAMILY = mult.PRIMITIVE_TO_FAMILY
MIN_N_BOOT = mult.MIN_N_BOOT
MIN_N_FLIPS = mult.MIN_N_FLIPS
formal_refuted_members = mult.formal_refuted_members


class MemberRecordError(Exception):
    """Persisted member records are missing, malformed, mismatched, or incomplete."""


def load_member_block(source: Mapping[str, Any] | Path | str) -> dict[str, Any]:
    """Read the ``family_measurements`` block from an execution artifact.

    Accepts a path to ``outputs/evaluation.json`` or the durable
    ``result.json`` (the adapter copies ``results`` into ``metrics``), or
    an already-parsed mapping.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise MemberRecordError(
                f"cannot read member-record artifact {path}: {error}") from error
    else:
        data = source
    if not isinstance(data, Mapping):
        raise MemberRecordError("member-record source is not a JSON object")
    block = data.get("family_measurements")
    if block is None and isinstance(data.get("metrics"), Mapping):
        block = data["metrics"].get("family_measurements")
    if block is None and isinstance(data.get("results"), Mapping):
        # outputs/evaluation.json nests everything under "results"; the
        # adapter copies that subtree into the durable result.json's
        # "metrics", so both spellings reach the same persisted records.
        block = data["results"].get("family_measurements")
    if not isinstance(block, Mapping):
        raise MemberRecordError(
            "no family_measurements block: the experiment predates the "
            "measurement wiring or its run failed closed; its members are "
            "not computable and may never be assumed or reconstructed")
    if block.get("schema") != SCHEMA:
        raise MemberRecordError(
            f"unknown family-measurements schema {block.get('schema')!r}; "
            f"expected {SCHEMA!r}")
    mult.assert_firewall_intact(dict(block), context="family_measurements block")
    return dict(block)


# -- F-6 (C4 post-remediation audit 2026-10-16, finding F-6) -------------
# What the persisted ``identity.config_sha256`` identifies, precisely:
# the producer (``recipe_harness._collect_family_measurements``) hashes
# the parsed ``experiment_config.json`` the frozen spec installed into
# the execution workspace, as ``sha256(json.dumps(config,
# sort_keys=True).encode("utf-8"))``.  What it did NOT do before this
# finding was closed: tie that value to anything outside the persisted
# block, so a self-consistent record could carry any 64-hex string and
# still pass every intra-block check (members == block == hash-of-
# nothing-independently-known).  The source of truth for a campaign
# execution is the candidate's ``spec.json`` — the adapter writes the
# exact ``ExperimentSpec.to_dict()`` it executed — joined to the
# append-only proposal ledger's recorded ``spec_sha256`` (which is
# ``hardening.spec_fingerprint`` of that same spec, written by
# ``SpecRegistry.record`` at attempt time).  The cross-check therefore
# walks: block identity  <- recompute hash from the spec's own
# experiment_config content ->  spec.json  <- recompute
# ``hardening.spec_fingerprint``  vs  the ledger's recorded value.
# Nothing is compared to another copy of itself, and no hash is ever
# invented: a missing, malformed, or mismatched source fails closed.

# The identity-bearing configuration keys the producer copies into
# ``identity``; every one must exist in the authoritative configuration
# or the cross-check refuses to vouch for it.
_IDENTITY_CONFIG_KEYS = (
    "hypothesis_id", "recipe_id", "arm_a", "arm_b",
    "estimator_a", "estimator_b", "seeds", "n_boot", "folds",
)
_SPEC_CONFIG_FILE = "experiment_config.json"


def _require_sha256_hex(value: Any, what: str) -> str:
    """Return ``value`` only if it is a well-formed 64-char lowercase sha256."""
    if not isinstance(value, str) or len(value) != 64 \
            or any(ch not in "0123456789abcdef" for ch in value):
        raise MemberRecordError(
            f"{what} is missing or malformed: expected a 64-character "
            f"lowercase hex sha256, got {value!r}")
    return value


def config_identity_sha256(config: Mapping[str, Any]) -> str:
    """Recompute the producer's configuration fingerprint byte for byte.

    Exact reproduction of the recipe-harness convention (default
    ``json.dumps`` separators, ``sort_keys``, UTF-8) so the consumer can
    recompute the fingerprint from an independent copy of the
    configuration rather than trusting the persisted one.
    """
    if not isinstance(config, Mapping):
        raise MemberRecordError(
            "authoritative experiment configuration is not a JSON object")
    return hashlib.sha256(
        json.dumps(dict(config), sort_keys=True).encode("utf-8")).hexdigest()


def _spec_experiment_config(spec: Mapping[str, Any], *,
                            experiment_id: str) -> dict[str, Any]:
    """The authoritative ``experiment_config.json`` the spec installs."""
    proposed = spec.get("proposed_change")
    files = proposed.get("files") if isinstance(proposed, Mapping) else None
    content = None
    for item in files if isinstance(files, list) else []:
        if isinstance(item, Mapping) \
                and str(item.get("path", "")).endswith(_SPEC_CONFIG_FILE):
            content = item.get("content")
            break
    if not isinstance(content, str):
        raise MemberRecordError(
            f"the authoritative specification for experiment "
            f"{experiment_id!r} carries no {_SPEC_CONFIG_FILE} content; "
            "the source of truth for the configuration fingerprint is "
            "absent and no hash may be invented in its place")
    try:
        config = json.loads(content)
    except ValueError as error:
        raise MemberRecordError(
            f"the authoritative {_SPEC_CONFIG_FILE} for experiment "
            f"{experiment_id!r} is not valid JSON: {error}") from error
    if not isinstance(config, dict):
        raise MemberRecordError(
            f"the authoritative {_SPEC_CONFIG_FILE} for experiment "
            f"{experiment_id!r} is not a JSON object")
    return config


def authoritative_identity(spec: Mapping[str, Any], *, experiment_id: str,
                           ledger_spec_sha256: str) -> dict[str, Any]:
    """Recompute the authoritative identity for one experiment (fail-closed).

    ``spec`` is the persisted ``spec.json`` the adapter executed;
    ``ledger_spec_sha256`` is the fingerprint the append-only proposal
    ledger recorded for this experiment.  Both must agree — recomputed
    from the spec, never trusted as a stored copy — and the configuration
    fingerprint is recomputed from the spec's own installed config.
    Raises :class:`MemberRecordError` on any missing, malformed, or
    mismatched value.
    """
    if not isinstance(spec, Mapping):
        raise MemberRecordError(
            f"the authoritative specification for experiment "
            f"{experiment_id!r} is not a JSON object")
    fingerprint = hardening.spec_fingerprint(dict(spec))
    recorded = _require_sha256_hex(
        ledger_spec_sha256,
        f"recorded spec_sha256 for experiment {experiment_id!r} in the "
        "proposal ledger")
    if recorded != fingerprint:
        raise MemberRecordError(
            f"experiment {experiment_id!r}: the persisted spec.json "
            f"recomputes to spec_sha256 {fingerprint} but the append-only "
            f"proposal ledger records {recorded}: the specification "
            "identity disagrees with its authoritative ledger record")
    config = _spec_experiment_config(spec, experiment_id=experiment_id)
    return {
        "experiment_id": str(experiment_id),
        "config_sha256": config_identity_sha256(config),
        "spec_sha256": fingerprint,
        "ledger_spec_sha256": recorded,
        "config_fields": {key: config[key] for key in (
            *_IDENTITY_CONFIG_KEYS, "primitive_id") if key in config},
    }


def load_authoritative_identity(experiment_id: str, *, spec_path: Path | str,
                                ledger_spec_sha256: str) -> dict[str, Any]:
    """Read an experiment's ``spec.json`` and recompute its authoritative
    identity.  A missing or unreadable spec fails closed (source of truth
    absent), never a fabricated or skipped hash."""
    path = Path(spec_path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise MemberRecordError(
            f"cannot read the authoritative specification for experiment "
            f"{experiment_id!r} at {path}: {error}; the source of truth for "
            "its configuration/specification identity is absent, so the "
            "persisted identity cannot be cross-checked and consumption "
            "fails closed") from error
    try:
        spec = json.loads(raw)
    except ValueError as error:
        raise MemberRecordError(
            f"the authoritative specification for experiment "
            f"{experiment_id!r} at {path} is not valid JSON: {error}"
        ) from error
    return authoritative_identity(spec, experiment_id=experiment_id,
                                  ledger_spec_sha256=ledger_spec_sha256)


def verify_identity_provenance(block: Mapping[str, Any],
                               experiment_id: str,
                               authority: Any) -> None:
    """Cross-check the persisted identity against its source of truth (F-6).

    Fails closed on: no authority supplied for the experiment, a
    malformed hash anywhere, a spec fingerprint that disagrees with the
    recorded ledger value, a ``config_sha256`` that disagrees with the
    authoritative configuration, or identity fields that disagree with
    the authoritative configuration.  ``authority`` is the mapping
    returned by :func:`authoritative_identity` /
    :func:`load_authoritative_identity`.
    """
    identity = block.get("identity")
    if not isinstance(identity, Mapping):
        raise MemberRecordError("block is missing its experiment identity")
    if not isinstance(authority, Mapping):
        raise MemberRecordError(
            f"no authoritative configuration/specification identity is "
            f"available for experiment {experiment_id!r}; the persisted "
            "config_sha256 cannot be cross-checked against any source of "
            "truth, so consumption fails closed (no hash is assumed)")
    config_sha = _require_sha256_hex(
        authority.get("config_sha256"),
        f"authoritative config_sha256 for experiment {experiment_id!r}")
    spec_sha = _require_sha256_hex(
        authority.get("spec_sha256"),
        f"authoritative spec_sha256 for experiment {experiment_id!r}")
    ledger_sha = _require_sha256_hex(
        authority.get("ledger_spec_sha256"),
        f"ledger-recorded spec_sha256 for experiment {experiment_id!r}")
    if spec_sha != ledger_sha:
        raise MemberRecordError(
            f"experiment {experiment_id!r}: the authoritative specification "
            f"fingerprint {spec_sha} disagrees with the authoritative ledger "
            f"record {ledger_sha}")
    persisted = _require_sha256_hex(
        identity.get("config_sha256"),
        f"persisted identity config_sha256 for experiment {experiment_id!r}")
    if persisted != config_sha:
        raise MemberRecordError(
            f"experiment {experiment_id!r}: the persisted record declares "
            f"config_sha256 {persisted}, but the authoritative experiment "
            f"specification installs a configuration hashing to {config_sha}: "
            "an internally self-consistent record disagrees with its "
            "authoritative specification")
    fields = authority.get("config_fields")
    if not isinstance(fields, Mapping):
        raise MemberRecordError(
            f"the authoritative identity for experiment {experiment_id!r} "
            "carries no configuration fields: malformed authority")
    for key in _IDENTITY_CONFIG_KEYS:
        if key not in fields:
            raise MemberRecordError(
                f"experiment {experiment_id!r}: the authoritative "
                f"configuration carries no {key!r}; the persisted identity "
                "cannot be verified against the source of truth and "
                f"{key} may not be assumed")
        if key not in identity:
            raise MemberRecordError(
                f"experiment {experiment_id!r}: the persisted identity is "
                f"missing {key!r}, which the authoritative configuration "
                "declares")
        if identity.get(key) != fields.get(key):
            raise MemberRecordError(
                f"experiment {experiment_id!r}: persisted identity "
                f"{key}={identity.get(key)!r} disagrees with the "
                f"authoritative configuration ({fields.get(key)!r})")
    if "primitive_id" in fields:
        if block.get("primitive_id") != fields["primitive_id"]:
            raise MemberRecordError(
                f"experiment {experiment_id!r}: the persisted block tests "
                f"primitive {block.get('primitive_id')!r} but the "
                f"authoritative configuration declares "
                f"{fields['primitive_id']!r}")


def _member_identity_check(block: Mapping[str, Any],
                           members: Sequence[Mapping[str, Any]]) -> None:
    identity = block.get("identity")
    if not isinstance(identity, Mapping):
        raise MemberRecordError("block is missing its experiment identity")
    for member in members:
        if dict(member.get("identity") or {}) != dict(identity):
            raise MemberRecordError(
                f"member {member.get('member_key')!r} carries a different "
                "experiment identity than its block")


def _linear_form_check(member: Mapping[str, Any], W: int) -> None:
    payload = member.get("signflip")
    if not isinstance(payload, Mapping):
        raise MemberRecordError(
            f"member {member.get('member_key')!r} has no sign-flip payload; "
            "the approved p-value method cannot be applied to it")
    g = np.asarray(payload.get("g"), dtype=np.float64)
    n_pos = int(payload.get("n_pos"))
    n_neg = int(payload.get("n_neg"))
    delta_hat = float(payload.get("delta_hat"))
    if g.shape != (int(W),):
        raise MemberRecordError(
            f"member {member.get('member_key')!r}: g length {g.shape} does "
            f"not match the campaign week index W={W}")
    if n_pos <= 0 or n_neg <= 0 or n_pos + n_neg != int(member.get("n_rows", -1)) \
            or n_events_mismatch(member, n_pos):
        raise MemberRecordError(
            f"member {member.get('member_key')!r}: sign-flip pair counts are "
            "inconsistent with the member frame")
    pair_total = n_pos * n_neg
    if abs(float(g.sum()) - 2.0 * pair_total * delta_hat) > \
            1e-6 * max(1.0, abs(delta_hat)):
        raise MemberRecordError(
            f"member {member.get('member_key')!r}: the persisted linear form "
            "fails its all-+1 identity; the record is malformed")
    if int(payload.get("W", -1)) != int(W):
        raise MemberRecordError(
            f"member {member.get('member_key')!r}: payload W does not match "
            f"the campaign week index W={W}")


def n_events_mismatch(member: Mapping[str, Any], n_pos: int) -> bool:
    return int(member.get("n_events", -1)) != n_pos


def family_members_from_records(
        blocks_and_ids: Sequence[tuple[Mapping[str, Any], str]],
        *, campaign_config: Mapping[str, Any],
        identity_authority: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[mult.FamilyMember]]:
    """Build per-family ``FamilyMember`` lists from persisted records.

    ``blocks_and_ids`` pairs each consumed block (already loaded) with the
    experiment id that produced it.  ``identity_authority`` maps each of
    those experiment ids to its authoritative configuration/specification
    identity (see :func:`load_authoritative_identity`); it is REQUIRED
    (F-6) — a block with no authoritative identity, or whose identity
    disagrees with it, is refused rather than consumed.  The campaign's
    recorded flip draw is loaded once and every member's unadjusted
    p-value is computed from its persisted ``g`` — the approved
    ``week_level_signflip_holm`` method, nothing else.
    """
    if not isinstance(identity_authority, Mapping):
        raise MemberRecordError(
            "identity_authority must map every consumed experiment id to "
            "its authoritative configuration/specification identity (F-6); "
            "consumption without a source of truth fails closed")
    if not blocks_and_ids:
        raise MemberRecordError(
            "no family-measurement blocks supplied; the campaign-end record "
            "may not be built from absent evidence")
    flip_seed = flip_S = flip_draw = None
    loaded_W: int | None = None
    families: dict[str, list[mult.FamilyMember]] = {}
    seen_ids: set[str] = set()
    for block, experiment_id in blocks_and_ids:
        if block.get("schema") != SCHEMA:
            raise MemberRecordError(
                f"block for {experiment_id!r} has schema "
                f"{block.get('schema')!r}")
        if block.get("applicable") is not True:
            raise MemberRecordError(
                f"block for {experiment_id!r} declares no applicable family "
                "measurements; it cannot feed a Holm family")
        family = str(block.get("family"))
        primitive = str(block.get("primitive_id"))
        declared = mult.FAMILIES.get(family)
        if declared is None:
            raise MemberRecordError(f"undeclared family {family!r}")
        if declared["primitive"] != primitive:
            raise MemberRecordError(
                f"block family {family!r} does not match frozen primitive "
                f"{declared['primitive']!r} (block declares {primitive!r})")
        ladder = tv.ladder_for(primitive)
        if ladder.get("family") != family:
            raise MemberRecordError(
                f"frozen ladder for {primitive!r} disagrees with family "
                f"{family!r}")
        if block.get("member_set_complete") is not True:
            raise MemberRecordError(
                f"block for {experiment_id!r} is not a complete member set; "
                "an incomplete set is refused, never reduced")
        members = block.get("members")
        if not isinstance(members, list) or not members:
            raise MemberRecordError(
                f"block for {experiment_id!r} carries no member records")
        expected = sorted(str(rung) for rung in ladder["rungs"])
        seen = sorted(str(m.get("member_key")) for m in members)
        if seen != expected or len(members) != len(expected):
            raise MemberRecordError(
                f"block for {experiment_id!r} member set {seen} does not "
                f"match the frozen ladder {expected}")
        _member_identity_check(block, members)
        # F-6: cross-check the persisted identity against the
        # authoritative spec + ledger (inside the block it is only
        # self-referential; see the F-6 note above).
        verify_identity_provenance(
            block, experiment_id, identity_authority.get(experiment_id))
        week_index = block.get("week_index") or {}
        W = int(week_index.get("W", 0))
        if W <= 0:
            raise MemberRecordError(
                f"block for {experiment_id!r} has no usable week index")
        if loaded_W is None:
            loaded_W = W
            flip_seed, flip_S, flip_draw = signflip.load_campaign_flip_draw(
                campaign_config, W=W)
        elif W != loaded_W:
            raise MemberRecordError(
                f"block for {experiment_id!r} week index W={W} disagrees "
                f"with the campaign flip draw W={loaded_W}")
        for member in members:
            key = str(member.get("member_key"))
            member_id = f"{experiment_id}:{key}"
            if member_id in seen_ids:
                raise MemberRecordError(f"duplicate member id {member_id!r}")
            seen_ids.add(member_id)
            status = member.get("measurement_status")
            if status == "unavailable":
                families.setdefault(family, []).append(mult.FamilyMember(
                    member_id=member_id, family=family, primitive=primitive,
                    experiment_id=experiment_id,
                    status=mult.STATUS_UNAVAILABLE,
                    note=str(member.get("unavailable_reason")
                             or "recorded unavailable by execution")))
                continue
            if status != "ok":
                raise MemberRecordError(
                    f"member {member_id!r} has unknown measurement_status "
                    f"{status!r}")
            _linear_form_check(member, W)
            payload = member["signflip"]
            unadjusted_p = signflip.signflip_p_value(
                float(payload["delta_hat"]),
                np.asarray(payload["g"], dtype=np.float64),
                flip_draw, flip_S, n_pos=int(payload["n_pos"]),
                n_neg=int(payload["n_neg"]))
            if not 0.0 <= unadjusted_p <= 1.0:
                raise MemberRecordError(
                    f"member {member_id!r}: computed p-value out of range")
            families.setdefault(family, []).append(mult.FamilyMember(
                member_id=member_id, family=family, primitive=primitive,
                experiment_id=experiment_id, status=mult.STATUS_AVAILABLE,
                unadjusted_p=float(unadjusted_p),
                ci_upper=(float(member["ci_upper"])
                          if member.get("ci_upper") is not None else None),
                delta=float(payload["delta_hat"]),
                note=(f"persisted by ordinary v1.1.0 execution; "
                      f"{signflip.APPROVED_METHOD_NAME} unadjusted p from "
                      f"the campaign's recorded flip draw (seed {flip_seed})")))
    return families
