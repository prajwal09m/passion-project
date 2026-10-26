"""Deterministic compositional ProposalGenerator (Phase 1 component 3).

Pure function of (EvidenceView, policy, seed, pinned versions). No I/O, no
subprocesses, no filesystem handle — the generator receives a serialized view
and returns inert proposal payloads.

Selection blindness is structural: ranking reads ONLY the closed input set
from ``BiasGovernor.selection_inputs``. ``preregistered_expectation`` is
computed and recorded but never scored — expected outcomes are not an input
to proposal selection (Phase 1 D/F, user SCIENTIFIC REQUIREMENTS).

No LLM exists in this system; every payload carries
``generator_type = deterministic_compositional``.
"""
from __future__ import annotations

import itertools
import random
from typing import Any, Mapping

from autonomous_agent.proposal_layer import schema
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor
from autonomous_agent.proposal_layer.primitives import LIBRARY, Primitive

# Reviewed candidate values for bounded int params (inside the harness ranges).
# 2026-10-15 (generator v1.1.0, owner repair directive): n_boot gains the
# 2000 grid point, completing the reviewed s/m/l bucket vocabulary that
# schema.bucket_n_boot already defines as design-identity-significant
# (500=s, 1000=m, 2000=l). Every value stays inside each primitive's
# declared ParamSpec bounds (low..high unchanged), renders into the
# existing closed harness config schema (no new config keys, no new code
# paths), and satisfies the H-10b n_boot >= 1000 floor for family-feeding
# primitives. This is the smallest candidate-space change that restores
# legitimate, never-asked signatures after the s/m/l space was exhausted
# by Campaigns 1-4 (61/64 non-validation grid cells already asked or
# recipe-excluded at the time of the repair).
GRID_INT_CANDIDATES: dict[str, tuple[int, ...]] = {
    "n_boot": (500, 1000, 2000),
    "calibration_bins": (5, 10),
}

_OPPOSITE_CLASS = {
    "confirmatory": "falsification",
    "falsification": "confirmatory",
    "replication": "replication",
    "exploration": "exploration",
}


def _param_grid(primitive: Primitive) -> list[dict[str, Any]]:
    keys = sorted(primitive.params)
    columns: list[tuple[Any, ...]] = []
    for key in keys:
        spec = primitive.params[key]
        if spec.kind == "enum":
            columns.append(tuple(spec.values))
        else:
            # The grid may never emit a value outside the primitive's own
            # declared bounds (e.g. n_boot=500 for an H-10b family-feeding
            # primitive whose floor is 1000): intersect, fail-closed.
            candidates = tuple(value for value in
                               GRID_INT_CANDIDATES.get(key, (spec.low,))
                               if spec.low <= value <= spec.high)
            columns.append(candidates or (spec.low,))
    return [dict(zip(keys, combo)) for combo in itertools.product(*columns)]


def _framed_classes(primitive: Primitive) -> tuple[str, ...]:
    classes = [primitive.default_class]
    if primitive.falsification_capable:
        opposite = _OPPOSITE_CLASS[primitive.default_class]
        if opposite not in classes:
            classes.append(opposite)
    return tuple(classes)


def _params_summary(params: Mapping[str, Any]) -> str:
    return ", ".join(f"{key}={params[key]}" for key in sorted(params))


def _prior_counts(view: Mapping[str, Any], direction: str) -> tuple[int, int]:
    stats = (view.get("direction_stats") or {}).get(direction) or {}
    return int(stats.get("accepted", 0)), int(stats.get("rejected", 0))


def quota_state_from_view(view: Mapping[str, Any],
                          governor: BiasGovernor,
                          campaign_id: str | None = None) -> dict[str, Any]:
    """Mirror the validator's accounting EXACTLY (same quota_state, same
    fingerprint dedupe, same campaign scope) so scheduler capacity can never
    diverge from gate behavior — budgets stay conservative by construction."""
    items = [{"proposal": {"proposal_class": item.get("proposal_class"),
                            "direction": item.get("direction"),
                            "design_signature": item.get("design_signature"),
                            "proposal_fingerprint": item.get("fingerprint"),
                            "campaign_id": item.get("campaign_id")}}
             for item in view.get("already_asked", [])]
    return governor.quota_state(items, campaign_id=campaign_id)


def _project_quota_state(state: Mapping[str, Any], *, direction: str,
                         proposal_class: str, signature: str) -> dict[str, Any]:
    """Post-creation quota state for one prospective, distinct record.

    ``BiasGovernor.check_accept`` is defined on POST-creation state (it
    includes the proposal under review), so any pre-creation admissibility
    check must project that state exactly. The candidate is guaranteed
    distinct here (never asked, never seen this cycle), so the projection
    is one increment per key -- same arithmetic ``quota_state`` would do
    after ``ledger.create_proposal``. Used by the generator's fail-closed
    pre-creation guard (2026-10-15 repair, owner directive): a candidate
    the governor would certainly refuse must never become a record,
    because refusals consume permanent budget.
    """
    by_direction = dict(state.get("by_direction") or {})
    by_class = dict(state.get("by_class") or {})
    by_signature = dict(state.get("by_signature") or {})
    by_direction[direction] = int(by_direction.get(direction, 0)) + 1
    by_class[proposal_class] = int(by_class.get(proposal_class, 0)) + 1
    by_signature[signature] = int(by_signature.get(signature, 0)) + 1
    return {
        "total": int(state.get("total", 0)) + 1,
        "by_direction": by_direction,
        "by_class": by_class,
        "by_signature": by_signature,
    }


def capacity(view: Mapping[str, Any],
             policy: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed remaining capacity (OBS-2 resolution, 2026-10-04).

    remaining = cap - current_records (conservative: refusals count, never
    removed). A new proposal in a direction is admissible iff remaining >= 1
    — the same post-creation rule the BUDGET gate enforces.
    """
    governor = BiasGovernor(policy)
    state = quota_state_from_view(view, governor,
                                  campaign_id=policy.get("campaign_id"))
    max_total = int(policy.get("max_total_proposals", 20))
    max_dir = int(policy.get("max_per_direction", 4))
    max_sig = int(policy.get("max_signature_count", 2))
    remaining_by_direction = {
        str(direction): max_dir - int(count)
        for direction, count in state["by_direction"].items()
    }
    for direction in policy.get("directions") or []:
        remaining_by_direction.setdefault(str(direction), max_dir)
    # Class budgets are just as binding as direction caps: a class already
    # at its cap cannot admit a new proposal (post-creation `>` rule), so
    # ranking it would only manufacture guaranteed BUDGET refusals (OBS-2).
    class_budgets = policy.get("class_budgets") or {}
    remaining_by_class = {
        str(cls): int(budget) - int(state["by_class"].get(cls, 0))
        for cls, budget in class_budgets.items()
    }
    return {
        "state": state,
        "remaining_total": max_total - int(state["total"]),
        "remaining_by_direction": remaining_by_direction,
        "remaining_by_class": remaining_by_class,
        "max_signature_count": max_sig,
    }


def _build_candidates(view: Mapping[str, Any], policy: Mapping[str, Any],
                      governor: BiasGovernor,
                      stats: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    stats = stats if stats is not None else {}
    cap = capacity(view, policy)
    state = cap["state"]
    stats.setdefault("remaining_total", cap["remaining_total"])
    stats.setdefault("remaining_by_direction", dict(cap["remaining_by_direction"]))
    stats.setdefault("excluded_exhausted_directions", [])
    stats.setdefault("excluded_exhausted_classes", [])
    stats.setdefault("remaining_by_class", dict(cap["remaining_by_class"]))
    stats.setdefault("excluded_recipe_signatures", 0)
    stats.setdefault("excluded_asked_signatures", 0)
    stats.setdefault("excluded_signature_cap", 0)
    stats.setdefault("excluded_governor_inadmissible", 0)
    stats.setdefault("excluded_governor_reasons", [])
    if cap["remaining_total"] <= 0:
        stats["excluded_total_budget"] = True
        return []                      # total budget exhausted: report, don't churn
    stats["excluded_total_budget"] = False
    min_fals = float(policy["min_falsification_share"])
    directions = set(policy.get("directions") or [])
    priorities = policy.get("direction_priorities") or {}
    allow_future = bool(policy.get("allow_future_primitives"))

    recipe_signatures: set[str] = set()
    for row in view.get("recipe_attempts", []):
        signature = schema.signature_from_recipe_attempt(
            row.get("recipe_id"), row.get("selected_parameters") or {})
        if signature:
            recipe_signatures.add(signature)
    asked_signatures = {item.get("design_signature")
                        for item in view.get("already_asked", [])}

    candidates: list[dict[str, Any]] = []
    for primitive in LIBRARY:
        if directions and primitive.direction not in directions:
            continue
        if not primitive.executable and not allow_future:
            continue
        # OBS-2: a direction whose remaining capacity is zero can no longer
        # produce an executable proposal — never rank it again.
        remaining_dir = int(cap["remaining_by_direction"].get(
            primitive.direction, int(policy.get("max_per_direction", 4))))
        if remaining_dir <= 0:
            if primitive.direction not in stats["excluded_exhausted_directions"]:
                stats["excluded_exhausted_directions"].append(primitive.direction)
            continue
        for params in _param_grid(primitive):
            signature = schema.design_signature(
                primitive_ids=(primitive.primitive_id,), params=params)
            # Already-asked / prior-campaign signatures are permanent and
            # can never be regenerated (the generator cannot declare
            # delta_from_prior, so re-emitting them would be guaranteed
            # refusal churn — OBS-2).
            if signature in recipe_signatures:
                stats["excluded_recipe_signatures"] += 1
                continue
            if signature in asked_signatures:
                stats["excluded_asked_signatures"] += 1
                continue
            if state["by_signature"].get(signature, 0) \
                    >= cap["max_signature_count"]:
                stats["excluded_signature_cap"] += 1
                continue
            # Remaining candidates are all previously unseen signatures.
            novelty = 1.0
            accepted, rejected = _prior_counts(view, primitive.direction)
            evidence_gap = 1.0 / (accepted + 1.0)
            attempts = int((view.get("direction_stats") or {})
                           .get(primitive.direction, {}).get("attempts", 0))
            for proposal_class in _framed_classes(primitive):
                # Fail-closed: a class with zero remaining budget can never
                # admit this proposal — never rank it (OBS-2).
                if int(cap["remaining_by_class"].get(proposal_class, 1)) <= 0:
                    if proposal_class not in stats["excluded_exhausted_classes"]:
                        stats["excluded_exhausted_classes"].append(proposal_class)
                    continue
                if proposal_class == "falsification":
                    quota_pressure = 1.0 if state["falsification_share"] < min_fals \
                        else 0.5
                else:
                    quota_pressure = 0.0 if state["falsification_share"] < min_fals \
                        else 0.5
                # Pre-creation governor guard (2026-10-15 repair): the
                # validator runs check_accept on the POST-creation state,
                # so creation must project it first. A candidate the
                # governor would certainly refuse (most importantly any
                # non-falsification class while the falsification share is
                # below the floor) is never ranked and never becomes a
                # record - refused records consume permanent direction/
                # class budget by design, so creating doomed proposals
                # silently destroys campaign capacity (observed in
                # Campaign 4: 24 of 26 creations were doomed BIAS_QUOTA
                # refusals and burned the validation/exploration budgets).
                projected = _project_quota_state(
                    state, direction=str(primitive.direction),
                    proposal_class=str(proposal_class),
                    signature=str(signature))
                admitted, reason_code, _ = governor.check_accept(
                    {"proposal_class": proposal_class,
                     "direction": primitive.direction,
                     "design_signature": signature}, projected)
                if not admitted:
                    stats["excluded_governor_inadmissible"] = \
                        int(stats.get("excluded_governor_inadmissible", 0)) + 1
                    reasons = stats.setdefault("excluded_governor_reasons", [])
                    if str(reason_code) not in reasons:
                        reasons.append(str(reason_code))
                    continue
                candidates.append({
                    "direction": primitive.direction,
                    "proposal_class": proposal_class,
                    "primitive": primitive,
                    "primitive_id": primitive.primitive_id,
                    "params": dict(params),
                    "design_signature": signature,
                    "novelty_score": novelty,
                    "evidence_gap_score": evidence_gap,
                    "quota_pressure": quota_pressure,
                    "priority": float(priorities.get(primitive.direction, 0.5)),
                    "attempts_in_direction": attempts,
                    "prior_counts": (accepted, rejected),
                })
    stats["candidates_remaining"] = len(candidates)
    return candidates


def scheduler_report(view: Mapping[str, Any],
                     policy: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic scheduler state for cycle summaries, tests, audits:
    exclusions applied, remaining capacity, research-exhaustion flag."""
    governor = BiasGovernor(policy)
    stats: dict[str, Any] = {}
    _build_candidates(view, policy, governor, stats=stats)
    stats["exhausted"] = int(stats.get("candidates_remaining", 0)) == 0
    return stats


def _ranking_key(candidate: Mapping[str, Any], governor: BiasGovernor):
    # Outcome-blind: uses only the closed selection-input set. Ties broken by
    # signature for full determinism (no wall-clock, no dict order).
    return (-governor.score(candidate), str(candidate["design_signature"]),
            str(candidate["proposal_class"]), str(candidate["primitive_id"]))


def _preregistered_expectation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Recorded AFTER ranking, from evidence only. Never a selection input."""
    accepted, rejected = candidate["prior_counts"]
    if accepted > rejected and accepted > 0:
        basis = "prior_evidence_favors"
    elif rejected > accepted and rejected > 0:
        basis = "prior_evidence_against"
    else:
        basis = "insufficient_prior_evidence"
    return {
        "basis": basis,
        "accepted_prior": accepted,
        "rejected_prior": rejected,
        "expected_direction": ("support" if basis == "prior_evidence_favors"
                               else "uncertain"),
    }


def _falsification_rule(candidate: Mapping[str, Any]) -> dict[str, Any]:
    primitive: Primitive = candidate["primitive"]
    metric = primitive.default_metric
    return {
        "metric": metric,
        "comparator": "<",
        "threshold": 0.0,
        "scope": ("predeclared chronological folds 2023/2024/2025, pooled OOF"
                  if metric != "min_year_delta"
                  else "per-year OOF deltas for 2023, 2024 and 2025"),
        "refutes": ("the candidate comparison satisfies the predeclared gates"
                    if candidate["proposal_class"] != "falsification"
                    else "the challenger claim that the effect is absent"),
    }


def _hypothesis(candidate: Mapping[str, Any]) -> str:
    primitive: Primitive = candidate["primitive"]
    summary = _params_summary(candidate["params"])
    if candidate["proposal_class"] == "falsification":
        return (f"[{primitive.direction}] Falsifier: {primitive.purpose} "
                f"({summary}) — predeclared refutation: metric below zero "
                f"under the frozen purged protocol.")
    if candidate["proposal_class"] == "replication":
        return (f"[{primitive.direction}] Replication: does {primitive.purpose} "
                f"({summary}) reproduce deterministically under an "
                f"independently parameterized re-run?")
    return (f"[{primitive.direction}] {primitive.purpose} "
            f"({summary}) — does it satisfy the predeclared non-degradation "
            f"criteria on the frozen development folds?")


def _citations(view: Mapping[str, Any],
               candidate: Mapping[str, Any]) -> list[dict[str, str]]:
    sources = {row["path"]: row["sha256"] for row in view.get("sources", [])}
    citations: list[dict[str, str]] = []

    def cite(path: str, shows: str, sha: str | None) -> None:
        if sha:
            citations.append({"artifact_path": path, "sha256": sha,
                              "what_it_shows": shows})

    champion = view.get("champion") or {}
    cite("CHAMPION.json",
         f"champion {champion.get('version')} (parent "
         f"{champion.get('parent_champion')}) with pinned metrics",
         sources.get("CHAMPION.json"))
    accepted, rejected = _prior_counts(view, candidate["direction"])
    cite("autonomous_agent/state/agent_state.json",
         f"prior {candidate['direction']} experiments: {accepted} accepted, "
         f"{rejected} rejected",
         sources.get("autonomous_agent/state/agent_state.json"))
    cite("autonomous_agent/state/baseline_registry.json",
         "established reconstructed baseline grounding",
         sources.get("autonomous_agent/state/baseline_registry.json"))
    dataset = view.get("dataset") or {}
    cite(dataset.get("path", ""),
         "frozen development event table with pinned dataset sha256",
         dataset.get("sha256"))
    cite("autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
         "AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md",
         "frozen Campaign 1 audit: prior campaign outcomes and limitations",
         sources.get("autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                     "AUTONOMOUS_CAMPAIGN_AUDIT_2026_10_04.md"))
    return citations


def _make_payload(candidate: Mapping[str, Any],
                  view: Mapping[str, Any]) -> dict[str, Any]:
    primitive: Primitive = candidate["primitive"]
    payload: dict[str, Any] = {
        "schema_version": schema.SCHEMA_VERSION,
        "generator_type": schema.GENERATOR_TYPE_DETERMINISTIC,
        "generator_version": schema.GENERATOR_VERSION,
        "primitive_library_version": schema.PRIMITIVE_LIBRARY_VERSION,
        "direction": candidate["direction"],
        "proposal_class": candidate["proposal_class"],
        "research_question_id": f"rq-{candidate['direction']}",
        "hypothesis": _hypothesis(candidate),
        "rationale": {
            "open_question": candidate["direction"],
            "evidence_gap": (
                f"direction {candidate['direction']}: "
                f"{candidate['prior_counts'][0]} accepted / "
                f"{candidate['prior_counts'][1]} rejected prior experiments"),
            "trigger": ("quota_class" if candidate.get("quota_pressure", 0.0) >= 1.0
                        else "novelty_score" if candidate.get("novelty_score", 0.0) >= 1.0
                        else "budget_slot"),
        },
        "preregistered_expectation": _preregistered_expectation(candidate),
        "falsification_rule": _falsification_rule(candidate),
        "evidence_citations": _citations(view, candidate),
        "parent_version": str((view.get("champion") or {}).get("version", "")),
        "baseline_id": str((view.get("baseline") or {}).get("baseline_id") or ""),
        "design": {
            "primitives": [{"primitive_id": candidate["primitive_id"],
                            "params": dict(candidate["params"])}],
            "protocol": {"folds": [2023, 2024, 2025],
                         "seeds": [42, 43, 44],
                         "ci_method": "moving_block_bootstrap",
                         "block_weeks": 4},
        },
        "parameters": dict(candidate["params"]),
        "design_signature": candidate["design_signature"],
    }
    payload["proposal_fingerprint"] = schema.proposal_fingerprint(payload)
    return payload


def payload_for(view: Mapping[str, Any], primitive_id: str,
                params: Mapping[str, Any], proposal_class: str) -> dict[str, Any]:
    """Public helper: build one payload for a specific design (used by tests
    and by targeted regeneration). Same construction path as generation."""
    from autonomous_agent.proposal_layer.primitives import get as get_primitive
    primitive = get_primitive(primitive_id)
    if primitive is None:
        raise KeyError(f"unknown primitive {primitive_id!r}")
    candidate = {
        "primitive": primitive,
        "primitive_id": primitive_id,
        "params": dict(params),
        "proposal_class": proposal_class,
        "direction": primitive.direction,
        "prior_counts": _prior_counts(view, primitive.direction),
        "design_signature": schema.design_signature(
            primitive_ids=(primitive_id,), params=dict(params)),
    }
    return _make_payload(candidate, view)


def generate_proposals(view: Mapping[str, Any], policy: Mapping[str, Any], *,
                       seed: int, limit: int | None = None) -> list[dict[str, Any]]:
    """Deterministically compose up to ``limit`` proposal payloads.

    Same (view, policy, seed, versions) => byte-identical payloads (T1).
    The seed only rotates the deterministic candidate list; scoring itself is
    a pure closed-input function (T8).
    """
    governor = BiasGovernor(policy)
    cap = capacity(view, policy)
    remaining_total = int(cap["remaining_total"])
    remaining_by_direction = cap["remaining_by_direction"]
    effective_limit = int(limit if limit is not None
                          else policy.get("max_proposals_per_cycle", 3))
    # Fail-closed scheduling: never emit more proposals than the remaining
    # budget can accept, and never exceed a direction's remaining capacity
    # (OBS-2 — creates no records that are doomed to BUDGET refusal).
    if remaining_total <= 0 or effective_limit <= 0:
        return []
    effective_limit = min(effective_limit, remaining_total)
    candidates = _build_candidates(view, policy, governor)
    candidates.sort(key=lambda candidate: _ranking_key(candidate, governor))
    if candidates:
        rotation = int(seed) % len(candidates)
        candidates = candidates[rotation:] + candidates[:rotation]

    threshold = float(policy.get("near_duplicate_text_threshold",
                                 schema.NEAR_DUPLICATE_TEXT_THRESHOLD))
    selected: list[dict[str, Any]] = []
    selected_sigs: set[str] = set()
    selected_by_direction: dict[str, int] = {}
    selected_by_class: dict[str, int] = {}
    remaining_by_class = cap["remaining_by_class"]
    # Running post-creation quota state for this cycle (never mutated in
    # place; _project_quota_state returns copies).
    running_state = cap["state"]
    for candidate in candidates:
        if len(selected) >= effective_limit:
            break
        # Capacity-bounded selection per direction/class (post-creation rule:
        # records + selected_so_far must stay within the cap).
        direction = str(candidate["direction"])
        remaining_dir = int(remaining_by_direction.get(
            direction, int(policy.get("max_per_direction", 4))))
        if selected_by_direction.get(direction, 0) >= remaining_dir:
            continue   # direction out of capacity this cycle
        cls = str(candidate["proposal_class"])
        if selected_by_class.get(cls, 0) \
                >= int(remaining_by_class.get(cls, 1)):
            continue   # class budget out of capacity this cycle
        if candidate["design_signature"] in selected_sigs:
            continue   # no same-signature doubles within one cycle
        # Exact governor mirror (2026-10-15 repair): validation runs
        # check_accept on the post-creation state -- base records + every
        # proposal already selected this cycle + this candidate. Skip any
        # candidate that would be refused there, so creation and
        # validation can never disagree (a cycle can no longer consist
        # entirely of doomed creations that burn permanent budget).
        projected = _project_quota_state(
            running_state, direction=direction, proposal_class=cls,
            signature=str(candidate["design_signature"]))
        admitted, _, _ = governor.check_accept(
            {"proposal_class": cls, "direction": direction,
             "design_signature": str(candidate["design_signature"])},
            projected)
        if not admitted:
            continue
        payload = _make_payload(candidate, view)
        if policy.get("campaign_id"):
            # Budget scope stamp: which campaign's budget this proposal
            # consumes. Deliberately excluded from proposal_fingerprint
            # (scientific identity is campaign-independent).
            payload["campaign_id"] = str(policy["campaign_id"])
        if any(schema.text_similarity(payload["hypothesis"], prior["hypothesis"])
               >= threshold for prior in selected):
            continue   # generation-side wording diversity (not a gate)
        selected.append(payload)
        selected_sigs.add(candidate["design_signature"])
        selected_by_direction[direction] = \
            selected_by_direction.get(direction, 0) + 1
        selected_by_class[cls] = selected_by_class.get(cls, 0) + 1
        # Commit the projected state so the next candidate in this cycle is
        # judged against exactly what validation will see.
        running_state = projected
    return selected
