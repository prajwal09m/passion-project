"""Persistent research loop — Stage 5 infrastructure (BUILT, NOT STARTED).

Implements repeated execution under FIXED, predeclared constraints:

    GENERATE -> VALIDATE -> BIAS-GOVERN -> APPROVE -> COMPILE -> EXECUTE
    -> EVALUATE -> PROMOTE/REJECT -> UPDATE RESEARCH MEMORY -> UPDATE LEDGER
    -> SELECT NEXT PROPOSAL -> REPEAT

"Continuous" means repeated execution under fixed constraints. It NEVER
means permission to modify itself:

* every lifecycle change goes through the append-only proposal ledger
  (invalid transitions raise, provenance is mandatory);
* budgets are derived from the ledger every cycle (never incremented in
  memory, never auto-expanded; negative capacity is a safety stop);
* the campaign configuration is hash-verified every cycle against its
  sidecar AND pinned to the digest first recorded in loop state
  (mismatch => STOP: a self-consistent config+sidecar rewrite is refused);
* duplicate/already-asked memory is global and permanent across restarts;
* the only execution path is ``ExperimentAdapter.run_experiment`` behind
  the compiled ExperimentSpec boundary (executor injection exists for
  disposable test fixtures only);
* the holdout directory is never opened; its mere existence in the
  workspace is a safety stop;
* a STOP file, stale-lock recovery, heartbeat, and repeated-crash guard
  are built in.

This module is a LIBRARY + CLI. Importing it does nothing and starts no
process. The CLI refuses to run without an explicit ``--max-cycles``:
there is no implicit infinite mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from autonomous_agent.proposal_layer import compiler, generator, schema
from autonomous_agent.proposal_layer.multiplicity import campaign_end_gap_status
from autonomous_agent.proposal_layer import cycle as proposal_cycle
from autonomous_agent.proposal_layer import evidence_view
from autonomous_agent.proposal_layer.bias_governor import BiasGovernor
from autonomous_agent.proposal_layer.ledger import (LedgerCorrupt, LedgerError,
                                                    ProposalLedger)

LOOP_STATE_NAME = "loop_state.json"
LOOP_LOCK_NAME = "loop.lock"
LOOP_JOURNAL_NAME = "loop_events.jsonl"
STOP_FILE_NAME = "STOP"
CAMPAIGN_CONFIG_REL = "autonomous_agent/state/campaign_config.json"
CAMPAIGN_SHA_REL = "autonomous_agent/state/campaign_config.sha256"
LAUNCH_GATES_REL = "autonomous_agent/launch_gates.json"
# Human launch gates that must be decided (and evidenced) before ANY campaign
# loop may start. Fail-closed: a missing gate file, an undecided gate, or a
# gate whose evidence file is absent blocks launch.
REQUIRED_LAUNCH_GATES = (
    "review_received",
    "d2_decided",
    "c3_ratified",
    "implementation_authorized",
    "implementation_complete",
    "freeze_approved",
    "launch_authorized",
)
MAX_CONSECUTIVE_FAILURES = 3
PORTFOLIO_MINIMUM_CLASSES = ("falsification", "confirmatory")

# --- frozen diagnostic-promotion rule (owner predeclaration) -----------------
# The 2026-10-25 defect: an ACCEPTED run was unconditionally promoted through
# _promote() even when its frozen owner predeclaration declares the family
# diagnostics-only (champion_rule: "V2.0.74 stays the standing champion;
# these are diagnostics, not promotions", which created versions V2.0.75/
# V2.0.76 wrongly). The map below is the only code-side coupling to a frozen
# owner record; adding a second diagnostic primitive requires adding its own
# frozen predeclaration here at owner-authorization time, never silently.
_FROZEN_DIAGNOSTIC_PREDECLARATIONS: dict[str, tuple[str, str]] = {
    "error_clustering_analysis": (
        "autonomous_agent/MAIN AUDITS AND REFLECTIONS"
        "/C5_ERROR_CLUSTER_PREDECLARATION_2026_10_25.json",
        "FROZEN_2026_10_25",
    ),
}
DIAGNOSTIC_RETAINED_OUTCOME = "DIAGNOSTIC_RETAINED"


def diagnostic_promotion_outcome(payload: Mapping[str, Any]
                                 ) -> tuple[str | None, str] | None:
    """Classify an accepted-run payload against frozen diagnostic rules.

    Returns ``None`` when the run promotes like any other accepted
    experiment.  Returns ``(rule_text, record_status)`` when the design uses a
    primitive whose frozen predeclaration forbids champion promotion:
    ``rule_text`` is the exact frozen champion_rule (may be ``None`` when the
    record cannot be read or thawed) and ``record_status`` records HOW the
    rule was sourced ("frozen" | "record_missing" | "record_unreadable" |
    "record_not_frozen").  Fail-closed: an unreadable, missing, or unfrozen
    record still refuses promotion — it can never silently allow it.
    """
    design = dict(payload.get("design") or {})
    used_ids = {str(pr.get("primitive_id") or "")
                for pr in (design.get("primitives") or [])
                if isinstance(pr, Mapping)}
    for primitive_id, (relpath, expected_status) in (
            _FROZEN_DIAGNOSTIC_PREDECLARATIONS.items()):
        if primitive_id not in used_ids:
            continue
        record_path = Path(__file__).resolve().parent.parent / relpath
        if not record_path.is_file():
            return (None, "record_missing")
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return (None, "record_unreadable")
        if not isinstance(record, dict) \
                or record.get("_status") != expected_status:
            return (None, "record_not_frozen")
        rule = (record.get("evaluation_rules") or {}).get("champion_rule")
        return (str(rule) if rule else None, "frozen")
    return None


class LoopStop(Exception):
    """Hard stop with a machine-readable reason (never swallowed)."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"[{reason}] {detail}")
        self.reason = reason
        self.detail = detail


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now() -> str:
    from autonomous_agent.core import utc_now
    return utc_now()


def default_executor(root: Path | str) -> Callable[[Any], dict[str, Any]]:
    """The reviewed real executor: the existing isolated adapter only.

    Nothing else in this module may execute experiments; tests inject
    disposable mock executors instead.
    """
    from autonomous_agent.experiment_adapter import ExperimentAdapter
    from autonomous_agent.core import Supervisor

    adapter = ExperimentAdapter(root=Path(root))

    def execute(spec) -> dict[str, Any]:
        result = adapter.run_experiment(spec)
        outcome = result.to_supervisor_outcome()
        try:
            # Same acceptance-evidence contract the Campaign 1 supervisor
            # enforced; also forces REJECTED whenever a mandatory gate did
            # not PASS or the holdout was touched.
            Supervisor._validate_outcome({}, outcome)
        except Exception as error:  # noqa: BLE001 - fail closed on bad evidence
            outcome["status"] = "REJECTED"
            outcome["rejection_reason"] = (
                f"outcome evidence contract refused the result: {error}")
        return outcome

    return execute


class ResearchLoop:
    def __init__(self, root: Path | str, *, max_cycles: int,
                 executor: Callable[[Any], dict[str, Any]] | None = None,
                 clock: Callable[[], str] | None = None,
                 idle_seconds: float = 0.0,
                 max_cycle_seconds: float | None = None) -> None:
        if int(max_cycles) <= 0:
            raise ValueError("max_cycles must be a positive, explicit bound")
        self.root = Path(root).resolve()
        self.state_root = self.root / "autonomous_agent" / "state"
        self.state_path = self.state_root / LOOP_STATE_NAME
        self.lock_path = self.state_root / LOOP_LOCK_NAME
        self.journal_path = self.state_root / LOOP_JOURNAL_NAME
        self.stop_file = self.state_root / STOP_FILE_NAME
        self.max_cycles = int(max_cycles)
        self.idle_seconds = max(0.0, float(idle_seconds))
        self.max_cycle_seconds = (None if max_cycle_seconds is None
                                  else max(0.0, float(max_cycle_seconds)))
        self.clock = clock or _now
        self.executor = executor            # None => real, built on demand
        self.stop_requested = False
        self._lock_fd: int | None = None
        self._lock_identity: tuple[int, int] | None = None
        self._state: dict[str, Any] = {}

    # -- durable state -------------------------------------------------------
    def load_state(self) -> dict[str, Any]:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("schema_version") == 1:
                return data
        except (OSError, json.JSONDecodeError, FileNotFoundError):
            pass
        config = self.load_campaign()
        return {
            "schema_version": 1,
            "campaign_id": config.get("campaign_id"),
            "campaign_config_sha256": self.campaign_sha(),
            "status": "INITIALIZED",
            "cycle": 0,
            "seed_base": int(config.get("seed_base", 0)),
            "max_cycles": self.max_cycles,
            "executions_done": 0,
            "executing": None,
            "consecutive_failures": 0,
            "last_stop_reason": None,
            "last_error": None,
            "started_at": self.clock(),
            "heartbeat_at": self.clock(),
        }

    def save_state(self) -> None:
        self._state["heartbeat_at"] = self.clock()
        self._state["updated_at"] = self.clock()
        from autonomous_agent.core import write_json_atomic
        write_json_atomic(self.state_path, self._state)

    def journal(self, event: str, **fields: Any) -> None:
        from autonomous_agent.core import append_jsonl
        append_jsonl(self.journal_path,
                     {"event": event, "at": self.clock(), **fields})

    # -- campaign configuration (immutable) ----------------------------------
    def load_campaign(self) -> dict[str, Any]:
        path = self.root / CAMPAIGN_CONFIG_REL
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LoopStop("CAMPAIGN_CONFIG_UNREADABLE", str(error)) from error
        if not isinstance(data, dict) or not isinstance(data.get("campaign_id"), str):
            raise LoopStop("CAMPAIGN_CONFIG_INVALID",
                           "campaign_id missing or malformed")
        return data

    def campaign_sha(self) -> str:
        path = self.root / CAMPAIGN_CONFIG_REL
        sidecar = self.root / CAMPAIGN_SHA_REL
        if not path.is_file() or not sidecar.is_file():
            raise LoopStop("CAMPAIGN_CONFIG_MISSING",
                           "campaign config or its sha256 sidecar is missing")
        expected = sidecar.read_text(encoding="utf-8").strip()
        actual = _sha256_file(path)
        if actual != expected:
            raise LoopStop("CAMPAIGN_CONFIG_HASH_MISMATCH",
                           f"expected {expected[:16]}.. got {actual[:16]}..")
        return actual

    def _check_launch_gates(self, campaign: dict[str, Any]) -> None:
        """Verify human launch gates are satisfied before campaign execution.

        This addresses the F-5 finding that the loop did not check
        launch_gates.json. The check is fail-closed: missing or incomplete
        gates block the loop BEFORE any startup state is written or any
        cycle can run. The stop is raised inside run()'s guarded startup
        section so it lands in durable state as a normal stop reason,
        exactly like a tampered campaign config or a missing sidecar.
        """
        gates_path = self.root / LAUNCH_GATES_REL
        if not gates_path.is_file():
            raise LoopStop("LAUNCH_GATES_FILE_MISSING",
                           f"launch_gates.json not found at {gates_path}")
        try:
            gates_data = json.loads(gates_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LoopStop("LAUNCH_GATES_UNREADABLE", str(error)) from error

        if not isinstance(gates_data, dict):
            raise LoopStop("LAUNCH_GATES_INVALID", "gates file is not a JSON object")

        missing = []
        for gate_name in REQUIRED_LAUNCH_GATES:
            entry = gates_data.get(gate_name)
            if not isinstance(entry, dict):
                missing.append(f"{gate_name}: malformed entry")
            elif entry.get("decided") is not True:
                missing.append(f"{gate_name}: not decided")
            else:
                # Verify evidence exists
                evidence_path = entry.get("evidence_path")
                if not evidence_path or not (self.root / evidence_path).is_file():
                    missing.append(f"{gate_name}: evidence missing or inaccessible")

        if missing:
            raise LoopStop("LAUNCH_GATES_NOT_SATISFIED",
                           f"Required gates not satisfied: {', '.join(missing)}")

    # -- lock / stop ---------------------------------------------------------
    def acquire_lock(self) -> bool:
        self.state_root.mkdir(parents=True, exist_ok=True)
        try:
            self._lock_fd = os.open(str(self.lock_path),
                                    os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # Recover only a lock whose recorded owner is provably gone.
            try:
                raw = self.lock_path.read_text(encoding="utf-8").strip()
                owner_pid = int(raw.split("pid=", 1)[1].split()[0])
                os.kill(owner_pid, 0)
            except ProcessLookupError:
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
                return self.acquire_lock()
            except OSError as error:
                # Windows: nonexistent PID surfaces as generic OSError.
                if getattr(error, "errno", None) == getattr(os, "ESRCH", 3) \
                        or getattr(error, "winerror", None) in (87, 1168):
                    try:
                        self.lock_path.unlink()
                    except FileNotFoundError:
                        pass
                    return self.acquire_lock()
                return False
            except (ValueError, IndexError):
                return False
            return False
        os.write(self._lock_fd,
                 f"pid={os.getpid()} started={self.clock()}\n".encode("utf-8"))
        os.fsync(self._lock_fd)
        stat = os.fstat(self._lock_fd)
        self._lock_identity = (stat.st_dev, stat.st_ino)
        return True

    def release_lock(self) -> None:
        if self._lock_fd is None:
            return
        try:
            os.close(self._lock_fd)
        finally:
            self._lock_fd = None
            try:
                current = self.lock_path.stat()
                if self._lock_identity == (current.st_dev, current.st_ino):
                    self.lock_path.unlink()
            except FileNotFoundError:
                pass
            self._lock_identity = None

    def request_stop(self, *_: Any) -> None:
        self.stop_requested = True

    # -- safety prechecks ----------------------------------------------------
    def _policy(self) -> dict[str, Any]:
        return proposal_cycle._load_policy(self.root)

    def _ledger(self) -> ProposalLedger:
        return ProposalLedger(self.root / proposal_cycle.LEDGER_RELATIVE_PATH,
                              clock=self.clock)

    def safety_precheck(self, policy: Mapping[str, Any]) -> None:
        """Hard-stop conditions checked at the top of every cycle."""
        from autonomous_agent.proposal_layer import proposals_enabled
        if not proposals_enabled(self.root):
            raise LoopStop("FLAG_OFF", "allow_generated_proposals is false")
        actual_sha = self.campaign_sha()
        # Stage 3 (2026-10-05): pin the campaign config to the digest first
        # recorded in loop state. The sidecar alone is not a trust anchor
        # (an attacker—or an accidental regeneration—can rewrite config AND
        # sidecar together); a self-consistent swap of the frozen campaign
        # configuration must still stop the loop before any budget is read.
        pinned_sha = self._state.get("campaign_config_sha256")
        if isinstance(pinned_sha, str) and pinned_sha \
                and pinned_sha != actual_sha:
            raise LoopStop(
                "CAMPAIGN_CONFIG_CHANGED",
                f"campaign config digest {actual_sha[:16]}.. does not match "
                f"the digest pinned in loop state {pinned_sha[:16]}..; the "
                "frozen campaign configuration may not change while loop "
                "state exists")
        # Holdout hard stop: the champion must still declare the holdout
        # SEALED with zero uses (actual access is stopped below from the
        # execution outcome, and the adapter rejects touched holdouts).
        try:
            raw = json.loads((self.root / "CHAMPION.json").read_text(
                encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LoopStop("CHAMPION_UNREADABLE", str(error)) from error
        holdout = raw.get("holdout_policy") or {}
        if holdout.get("status") != "SEALED" \
                or int(holdout.get("uses", 0) or 0) != 0:
            raise LoopStop("HOLDOUT_STATE",
                           f"holdout policy {holdout!r} is not SEALED/uses=0")
        # Champion-identity divergence: agent_state's champion projection must
        # never be ahead of (or corrupt next to) the live canonical champion.
        from autonomous_agent.champion_identity import check_divergence
        detail = check_divergence(self.root, self.state_root)
        if detail is not None:
            raise LoopStop("CHAMPION_STATE_DIVERGENCE", detail)
        ledger = self._ledger()
        ledger.read_rows(strict=True)          # raises LedgerCorrupt => caller stops
        view = self._view(ledger, policy)
        cap = generator.capacity(view, policy)
        if int(cap["remaining_total"]) < 0:
            raise LoopStop("BUDGET_INCONSISTENCY",
                           f"negative remaining_total {cap['remaining_total']}")
        # capacity/quota fields must never contradict the validator's accounting
        state = cap["state"]
        if int(state["total"]) < 0 or any(int(v) < 0 for v in
                                          state["by_direction"].values()):
            raise LoopStop("BUDGET_INCONSISTENCY", "negative quota counter")
        if any(int(v) < 0 for v in cap["remaining_by_direction"].values()):
            # over-cap directions from other scopes are fine; only a
            # NEGATIVE remaining for the ACTIVE scope indicates corruption
            # (scoped counts can never exceed their caps by construction)
            raise LoopStop("BUDGET_INCONSISTENCY",
                           f"negative remaining capacity {cap['remaining_by_direction']}")

    def _view(self, ledger: ProposalLedger, policy: Mapping[str, Any]):
        return evidence_view.build(self.root, clock=self.clock,
                                   ledger_rows=ledger.read_rows(strict=True))

    def _enforce_audit_stops(self, campaign: Mapping[str, Any]) -> None:
        """Fail-closed restart guard for the two v1.1.0 audit stops.

        Inert unless the frozen campaign config declares one of them: the
        Campaign 3 config does not, so a v1.0.0 campaign behaves exactly as
        before. When a campaign DOES declare them, a point-in-time audit stop
        already recorded in the ledger halts the campaign again after a
        restart instead of resuming past it.
        """
        from autonomous_agent.proposal_layer import multiplicity as mult
        declared = set(campaign.get("stop_conditions") or ())
        if not (declared & mult.AUDIT_STOP_CONDITIONS):
            return
        stop = mult.recorded_audit_stop(
            self._ledger().read_rows(strict=True))
        if stop is not None:
            raise LoopStop(stop[0],
                           f"{stop[1]} (recorded in the ledger; campaign "
                           f"cannot resume without human data-lineage review)")

    def _enforce_c5_signal_stops(self, campaign: Mapping[str, Any]) -> None:
        """Fail-closed restart guard for Campaign 5's two declared stops.

        Inert unless the frozen campaign config declares one of them: every
        pre-Campaign-5 config (and any future config that leaves them
        undeclared) behaves exactly as before. When a campaign DOES declare
        them, a regime-predefinition or data-snooping stop already recorded in
        the ledger halts the campaign again after a restart instead of
        resuming past it.
        """
        from autonomous_agent.proposal_layer import stops_c5
        declared = set(campaign.get("stop_conditions") or ())
        if not (declared & stops_c5.C5_SIGNAL_STOPS):
            return
        stop = stops_c5.recorded_c5_signal_stop(
            self._ledger().read_rows(strict=True))
        if stop is not None:
            raise LoopStop(stop[0],
                           f"{stop[1]} (recorded in the ledger; campaign "
                           "cannot resume without human review)")

    # -- exhaustion detection ------------------------------------------------
    def exhaustion_report(self) -> dict[str, Any]:
        policy = self._policy()
        ledger = self._ledger()
        view = self._view(ledger, policy)
        sched = generator.scheduler_report(view, policy)
        campaign_id = policy.get("campaign_id")
        mine = [m for m in ledger.all_proposals()
                if campaign_id is None
                or (m.get("proposal") or {}).get("campaign_id") == campaign_id]
        executed_states = {schema.STATUS_EXECUTED, schema.STATUS_ADJUDICATED,
                           schema.STATUS_PROMOTED,
                           schema.STATUS_FAILED_EXECUTION}
        executions_done = sum(1 for m in mine if m.get("status") in executed_states)
        approved = [m for m in mine
                    if m.get("status") == schema.STATUS_ACCEPTED_FOR_EXECUTION]
        compiled = [m for m in mine
                    if m.get("status") == schema.STATUS_COMPILED]
        done = {"falsification": 0, "confirmatory": 0,
                "replication": 0, "exploration": 0}
        # Count executed portfolio classes from adjudication transitions.
        for row in ledger.read_rows(strict=True):
            if row.get("row_type") != "transition" \
                    or row.get("to") != schema.STATUS_ADJUDICATED:
                continue
            detail = row.get("detail") or {}
            if detail.get("result") == "ACCEPTED" or detail.get("result") == "REJECTED":
                payload = next((m.get("proposal") or {} for m in mine
                                if m.get("proposal_id") == row.get("proposal_id")),
                               {})
                cls = str(payload.get("proposal_class"))
                if cls in done:
                    done[cls] += 1
        campaign = self.load_campaign()
        maximum = int((campaign.get("execution") or {})
                      .get("max_total_executions", 4))
        minimums = campaign.get("portfolio") or {}
        return {
            "campaign_id": campaign_id,
            "scheduler_exhausted": bool(sched.get("exhausted")),
            "candidates_remaining": int(sched.get("candidates_remaining", 0)),
            "excluded_exhausted_directions": sched.get(
                "excluded_exhausted_directions", []),
            "excluded_exhausted_classes": sched.get("excluded_exhausted_classes", []),
            "remaining_total": int(cap_remaining(view, policy)),
            "executions_done": executions_done,
            "execution_budget": maximum,
            "approved_waiting": [m["proposal_id"] for m in mine
                                 if m.get("status")
                                 == schema.STATUS_ACCEPTED_FOR_EXECUTION],
            "compiled_waiting": [m["proposal_id"] for m in mine
                                 if m.get("status") == schema.STATUS_COMPILED],
            "executed_by_class": {k: v for k, v in done.items() if v},
            "portfolio_minimums": {
                cls: int((minimums.get(cls + "_minimum") or {}).get("count", 1))
                for cls in PORTFOLIO_MINIMUM_CLASSES},
            "portfolio_complete": all(
                done[cls] >= int((minimums.get(cls + "_minimum") or {})
                                 .get("count", 1))
                for cls in PORTFOLIO_MINIMUM_CLASSES),
        }

    # -- phase: generate / validate / approve --------------------------------
    def phase_generate_and_approve(self) -> dict[str, Any]:
        from autonomous_agent.proposal_layer import proposals_enabled
        if not proposals_enabled(self.root):
            raise LoopStop("FLAG_OFF", "allow_generated_proposals is false")
        policy = self._policy()
        ledger = self._ledger()
        view = self._view(ledger, policy)
        governor = BiasGovernor(policy)
        campaign = self.load_campaign()
        approver = str((campaign.get("approval") or {})
                       .get("approver", "policy:auto"))
        seed = int(self._state.get("seed_base", 0)) + int(self._state["cycle"])
        payloads = generator.generate_proposals(view, policy, seed=seed)
        summary = {"seed": seed, "created": [], "approved": [],
                   "refused": [], "failed_validation": [],
                   "refused_at_approval": [], "failed_at_approval": []}
        for payload in payloads:
            proposal_id = ledger.create_proposal(payload)
            summary["created"].append(proposal_id)
            ledger.transition(proposal_id, schema.STATUS_VALIDATING)
            merged = ledger.all_proposals()
            report = proposal_cycle.generator_validate(
                payload, root=self.root, view=view, history=merged,
                policy=policy, governor=governor, proposal_id=proposal_id)
            if not report.passed:
                target = report.status_target or schema.STATUS_FAILED_VALIDATION
                ledger.transition(proposal_id, target,
                                  reason_code=report.reason_code,
                                  detail=report.to_dict())
                bucket = ("refused" if target == schema.STATUS_REFUSED
                          else "failed_validation")
                summary[bucket].append({"proposal_id": proposal_id,
                                        "reason_code": report.reason_code})
                continue
            # Autonomous approval under the frozen campaign policy; always
            # revalidated against current ledger state with full provenance.
            target, approval_report = proposal_cycle._revalidate_and_approve(
                ledger, payload=payload, proposal_id=proposal_id,
                root=self.root, view=view, policy=policy, governor=governor,
                approver=approver, auto_approve=True)
            if target == schema.STATUS_ACCEPTED_FOR_EXECUTION:
                summary["approved"].append(proposal_id)
            else:
                bucket = ("refused_at_approval"
                          if target == schema.STATUS_REFUSED
                          else "failed_at_approval")
                summary[bucket].append({"proposal_id": proposal_id,
                                        "reason_code":
                                            approval_report.reason_code})
        self.journal("phase_generate", **{k: (len(v) if isinstance(v, list)
                                              else v)
                                          for k, v in summary.items()})
        return summary

    # -- phase: select / compile / execute / adjudicate ----------------------
    def _select_next(self, approved: list[dict[str, Any]],
                     executed_by_class: Mapping[str, int],
                     maximums: Mapping[str, int]) -> dict[str, Any] | None:
        """Predeclared rule: portfolio minimums first, then approval order."""
        if not approved:
            return None
        for cls in PORTFOLIO_MINIMUM_CLASSES:
            if int(executed_by_class.get(cls, 0)) < int(maximums.get(cls, 1)):
                for item in approved:
                    payload = item.get("proposal") or {}
                    if str(payload.get("proposal_class")) == cls:
                        return item
        return approved[0]

    def phase_execute_one(self) -> dict[str, Any]:
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        campaign = self.load_campaign()
        preflight = check_campaign5_authorization(
            self.root, campaign, campaign.get("authorization_scope"))
        if campaign.get("campaign_id", "").startswith("campaign-5") and not preflight["allowed"]:
            raise LoopStop("CAMPAIGN5_AUTHORIZATION_BLOCKED",
                           ",".join(preflight["reason_codes"]))
        policy = self._policy()
        ledger = self._ledger()
        view = self._view(ledger, policy)
        maximum = int((campaign.get("execution") or {})
                      .get("max_total_executions", 4))
        report = self.exhaustion_report()
        self._state["executions_done"] = int(report["executions_done"])
        if int(report["executions_done"]) >= maximum:
            raise LoopStop("EXECUTION_BUDGET",
                           f"{report['executions_done']}/{maximum} executed")
        campaign_id = policy.get("campaign_id")
        merged = [m for m in ledger.all_proposals()
                  if campaign_id is None
                  or (m.get("proposal") or {}).get("campaign_id") == campaign_id]
        approved = [m for m in merged
                    if m.get("status") == schema.STATUS_ACCEPTED_FOR_EXECUTION]
        compiled = [m for m in merged
                    if m.get("status") == schema.STATUS_COMPILED]
        minimums = campaign.get("portfolio") or {}
        maximums = {cls: int((minimums.get(cls + "_minimum") or {}).get("count", 1))
                    for cls in PORTFOLIO_MINIMUM_CLASSES}
        if not compiled:
            target = self._select_next(approved, report["executed_by_class"],
                                       maximums)
            if target is None:
                # Nothing admissible: complete portfolio => clean stop;
                # unmet minimums + exhausted scheduler => honest exhaustion.
                if report["portfolio_complete"]:
                    raise LoopStop("PORTFOLIO_COMPLETE",
                                   "minimums met and no admissible proposal")
                if report["scheduler_exhausted"] and not approved:
                    raise LoopStop("PROPOSAL_EXHAUSTED",
                                   f"no admissible proposal; minimums "
                                   f"unmet: {report['executed_by_class']}")
                return {"action": "nothing_admissible"}
            payload = target["proposal"]
            proposal_id = target["proposal_id"]
            try:
                spec, spec_sha = compiler.compile_proposal(
                    payload, root=self.root,
                    status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
            except (compiler.CompileError, compiler.BoundaryViolation) as error:
                code = getattr(error, "code", schema.RC_SPEC_CONTRACT)
                ledger.transition(proposal_id, schema.STATUS_FAILED_COMPILATION,
                                  reason_code=code,
                                  detail={"error": str(error),
                                          "campaign_id": campaign_id})
                return {"action": "failed_compilation",
                        "proposal_id": proposal_id, "reason_code": code}
            ledger.transition(proposal_id, schema.STATUS_COMPILED,
                              reason_code="COMPILED",
                              detail={"spec_sha256": spec_sha,
                                      "experiment_id": spec.experiment_id,
                                      "campaign_id": campaign_id,
                                      "proposal_fingerprint":
                                          payload.get("proposal_fingerprint")})
            compiled = [m for m in merged
                        if m.get("proposal_id") == proposal_id]
            compiled[0]["status"] = schema.STATUS_COMPILED
            target = compiled[0]
        payload = target["proposal"]
        proposal_id = target["proposal_id"]
        spec, spec_sha = compiler.compile_proposal(
            payload, root=self.root, status=schema.STATUS_ACCEPTED_FOR_EXECUTION)
        # Execution marker BEFORE invoking the executor: a crash here is
        # recovered, never re-run blindly.
        ledger.transition(proposal_id, schema.STATUS_EXECUTED,
                          reason_code="EXECUTION_STARTED",
                          detail={"phase": "started",
                                  "experiment_id": spec.experiment_id,
                                  "spec_sha256": spec_sha,
                                  "campaign_id": campaign_id,
                                  "proposal_fingerprint":
                                      payload.get("proposal_fingerprint")})
        self._state["executing"] = {"proposal_id": proposal_id,
                                    "experiment_id": spec.experiment_id,
                                    "spec_sha256": spec_sha,
                                    "started_at": self.clock()}
        self.save_state()
        outcome = self._invoke_executor(spec, spec.experiment_id)
        self._state["executing"] = None
        self.save_state()
        return self._adjudicate(ledger, proposal_id, spec, spec_sha, payload,
                                outcome)

    def _invoke_executor(self, spec, experiment_id: str) -> dict[str, Any]:
        executor = self.executor
        if executor is None:
            executor = default_executor(self.root)
            self.executor = executor
        try:
            outcome = executor(spec)
        except Exception as error:  # noqa: BLE001 - failures are evidence
            self.journal("execution_error", experiment_id=experiment_id,
                         error=f"{type(error).__name__}: {error}")
            return {"status": "FAILED",
                    "checks": {}, "results": {}, "candidate_path": None,
                    "error": {"message": f"{type(error).__name__}: {error}"}}
        if not isinstance(outcome, dict):
            return {"status": "FAILED", "checks": {}, "results": {},
                    "candidate_path": None,
                    "error": {"message": "executor returned a non-mapping"}}
        return outcome

    def _adjudicate(self, ledger: ProposalLedger, proposal_id: str, spec,
                    spec_sha: str, payload: Mapping[str, Any],
                    outcome: Mapping[str, Any]) -> dict[str, Any]:
        campaign_id = payload.get("campaign_id")
        status = str(outcome.get("status") or "FAILED")
        base_detail = {
            "experiment_id": spec.experiment_id,
            "spec_sha256": spec_sha,
            "campaign_id": campaign_id,
            "proposal_fingerprint": payload.get("proposal_fingerprint"),
            "parent_version": payload.get("parent_version"),
            "baseline_id": payload.get("baseline_id"),
            "checks": dict(outcome.get("checks") or {}),
            "holdout_touched": bool(outcome.get("holdout_touched")),
            "result_json": (f"autonomous_agent/candidates/"
                            f"{spec.experiment_id}/result.json"),
        }
        if status == "FAILED":
            detail = {**base_detail,
                      "error": dict(outcome.get("error") or {})}
            ledger.transition(proposal_id, schema.STATUS_FAILED_EXECUTION,
                              reason_code="EXECUTION_FAILED", detail=detail)
            self._record_memory(payload, "FAILED", outcome)
            return {"action": "failed_execution", "proposal_id": proposal_id}
        results = dict(outcome.get("results") or {})
        # v1.1.0 (authorized 2026-10-12, gate 3, D2-independent subset):
        #  * provisional-to-formal firewall — a bare formal-refutation label
        #    may never reach a ledger row, loop event, or report before the
        #    campaign-end multiplicity record exists;
        #  * point-in-time audit stops — confirmed contamination or
        #    unverifiable lineage halts the campaign fail-closed.
        # Both are inert for v1.0.0 outcomes, which never carry these fields.
        from autonomous_agent.proposal_layer import multiplicity as mult
        try:
            mult.assert_firewall_intact(
                {"results": results,
                 "rejection_reason": outcome.get("rejection_reason"),
                 "blockers": list(outcome.get("blockers") or [])},
                context="adjudication detail")
        except mult.FirewallViolation as violation:
            # A formal-refutation label can never reach a ledger row, loop
            # event, or report before the campaign-end multiplicity record;
            # halt rather than persist an unlabeled-free artifact.
            self.journal("firewall_violation", detail=str(violation),
                         experiment_id=spec.experiment_id,
                         campaign_id=campaign_id)
            raise LoopStop("FIREWALL_VIOLATION", str(violation)) from violation
        audit_stop = mult.audit_stop_signal(outcome)
        if audit_stop is not None:
            # Durable first (append-only ledger), then halt: the signal must
            # survive a restart so the campaign can never resume past it.
            ledger.transition(
                proposal_id, schema.STATUS_FAILED_EXECUTION,
                reason_code="AUDIT_STOP",
                detail={**base_detail,
                        "audit_stop": audit_stop[0],
                        "audit_stop_detail": audit_stop[1],
                        "results": results})
            self.journal("audit_stop", reason=audit_stop[0],
                         detail=audit_stop[1],
                         experiment_id=spec.experiment_id,
                         campaign_id=campaign_id)
            raise LoopStop(
                audit_stop[0],
                f"{audit_stop[1]} (experiment {spec.experiment_id}); "
                f"campaign halted for human data-lineage review")
        from autonomous_agent.proposal_layer import stops_c5
        c5_stop = stops_c5.c5_signal_stop(outcome)
        if c5_stop is not None:
            # Campaign 5's two declared signal stops (regime predefinition /
            # data snooping): the audit-stops contract again — durable first
            # (append-only ledger), then halt; inert for any outcome payload
            # that never carries the violation verdicts.
            ledger.transition(
                proposal_id, schema.STATUS_FAILED_EXECUTION,
                reason_code="C5_SIGNAL_STOP",
                detail={**base_detail,
                        "c5_signal_stop": c5_stop[0],
                        "c5_signal_stop_detail": c5_stop[1],
                        "results": results})
            self.journal("c5_signal_stop", reason=c5_stop[0],
                         detail=c5_stop[1],
                         experiment_id=spec.experiment_id,
                         campaign_id=campaign_id)
            raise LoopStop(
                c5_stop[0],
                f"{c5_stop[1]} (experiment {spec.experiment_id}); "
                "campaign halted for human review")
        primary = results.get("primary_metric") or {}
        scientific = {**base_detail,
                      "result": "ACCEPTED" if status == "ACCEPTED" else "REJECTED",
                      "primary_delta": primary.get("delta"),
                      "decision_criteria_passed":
                          results.get("decision_criteria_passed"),
                      "rejection_reason": outcome.get("rejection_reason"),
                      "blockers": list(outcome.get("blockers") or []),
                      "leakage_status": outcome.get("leakage_status"),
                      "robustness_status": outcome.get("robustness_status"),
                      "artifact_sha256": outcome.get("artifact_sha256"),
                      "reproduction_command": outcome.get("reproduction_command")}
        experiment = {"id": spec.experiment_id,
                      "direction": str(payload.get("direction")),
                      "hypothesis": str(payload.get("hypothesis")),
                      "status": status,
                      "baseline_id": payload.get("baseline_id"),
                      "rationale": str((payload.get("rationale") or {})
                                       .get("open_question", ""))}
        if status == "ACCEPTED":
            # Stage 3 (2026-10-05): the release-gate contract is enforced
            # BEFORE the ledger records an acceptance, using the exact
            # VersionManager._validate_outcome the promotion path runs. A
            # refusal (holdout touched, evidence contract failed) is then
            # recorded truthfully as REJECTED — the ledger can never claim
            # ACCEPTED for an outcome the release gates refused — and the
            # campaign stops (HOLDOUT_TOUCHED / PROMOTION_FAILED).
            try:
                from autonomous_agent.core import VersionManager
                VersionManager._validate_outcome(dict(experiment), outcome)
            except Exception as error:  # noqa: BLE001 - refusal is evidence
                outcome["status"] = "REJECTED"
                outcome.setdefault(
                    "rejection_reason",
                    f"outcome evidence contract refused the result: {error}")
                scientific["rejection_reason"] = outcome["rejection_reason"]
                ledger.transition(proposal_id, schema.STATUS_ADJUDICATED,
                                  reason_code="GATES_FAILED",
                                  detail={**scientific, "result": "REJECTED"})
                self._record_memory(payload, "REJECTED", outcome)
                if outcome.get("holdout_touched"):
                    raise LoopStop(
                        "HOLDOUT_TOUCHED",
                        f"experiment {spec.experiment_id} touched the "
                        "holdout; rejection recorded, campaign halted")
                raise LoopStop("PROMOTION_FAILED",
                               f"{type(error).__name__}: {error}") from error
            diagnostic = diagnostic_promotion_outcome(payload)
            if diagnostic is not None:
                # Frozen champion rule (owner predeclaration): this is a
                # diagnostic run, never a promotion. Acceptance evidence is
                # recorded; the champion is never advanced. The retained
                # adjudication is made permanently non-promotable at the
                # ledger level (promotion_outcome=DIAGNOSTIC_RETAINED), so no
                # later transition can repair it into a standing version.
                rule_text, record_status = diagnostic
                ledger.transition(
                    proposal_id, schema.STATUS_ADJUDICATED,
                    reason_code="DIAGNOSTIC_RETAINED",
                    detail={"result": "ACCEPTED",
                            "promotion_outcome": "DIAGNOSTIC_RETAINED",
                            "diagnostic_rule": rule_text,
                            "rule_record_status": record_status,
                            "champion_unchanged": True,
                            "experiment_id": spec.experiment_id,
                            "campaign_id": campaign_id,
                            "parent_version": payload.get("parent_version"),
                            "artifact_sha256": outcome.get("artifact_sha256"),
                            **scientific})
                self._record_memory(
                    payload, "ACCEPTED", outcome, promoted_version=None,
                    lesson_note=("Diagnostic retained (frozen champion_rule, "
                                 "record status " + record_status + "): "
                                 "champion unchanged; "
                                 "not promotable per the frozen predeclaration"))
                self.journal("diagnostic_retained",
                             proposal_id=proposal_id,
                             experiment_id=spec.experiment_id,
                             campaign_id=campaign_id,
                             rule_record_status=record_status)
                return {"action": "diagnostic_retained",
                        "proposal_id": proposal_id}
            ledger.transition(proposal_id, schema.STATUS_ADJUDICATED,
                              reason_code="GATES_PASSED",
                              detail={**scientific, "result": "ACCEPTED"})
            promoted_version = self._promote(experiment, outcome)
            ledger.transition(proposal_id, schema.STATUS_PROMOTED,
                              reason_code="PROMOTED",
                              detail={"version": promoted_version,
                                      "experiment_id": spec.experiment_id,
                                      "artifact_sha256":
                                          outcome.get("artifact_sha256"),
                                      "campaign_id": campaign_id,
                                      "parent_version":
                                          payload.get("parent_version")})
            self._record_memory(payload, "ACCEPTED", outcome,
                                promoted_version=promoted_version)
            return {"action": "promoted", "proposal_id": proposal_id,
                    "version": promoted_version}
        ledger.transition(proposal_id, schema.STATUS_ADJUDICATED,
                          reason_code="GATES_FAILED",
                          detail={**scientific, "result": "REJECTED"})
        self._record_memory(payload, "REJECTED", outcome)
        if outcome.get("holdout_touched"):
            raise LoopStop("HOLDOUT_TOUCHED",
                           f"experiment {spec.experiment_id} touched the "
                           "holdout; rejection recorded, campaign halted")
        return {"action": "rejected", "proposal_id": proposal_id}

    def _promote(self, experiment: Mapping[str, Any],
                 outcome: Mapping[str, Any]) -> str:
        from autonomous_agent.core import VersionManager, parse_champion
        champion, errors = parse_champion(self.root / "CHAMPION.json")
        if champion is None:
            raise LoopStop("PROMOTION_BLOCKED",
                           "no valid CHAMPION.json: " + "; ".join(errors))
        if champion.get("experiment_id") == experiment.get("id"):
            # Crash-recovery: this experiment already advanced the champion.
            return str(champion.get("version"))
        try:
            destination = VersionManager(self.root).promote(
                dict(champion), dict(experiment), dict(outcome))
        except Exception as error:  # noqa: BLE001 - promotion is evidence too
            raise LoopStop("PROMOTION_FAILED",
                           f"{type(error).__name__}: {error}") from error
        # Keep agent_state's champion projection from drifting behind the new
        # champion: best-effort refresh from the verified canonical chain.
        # Refusal must NOT block the promotion ledger row: leaving the
        # projection *behind* is safe (the divergence guard only stops on a
        # state ahead of / corrupt relative to the canonical champion), so a
        # failed verification is recorded as evidence and the promotion
        # continues.
        from autonomous_agent.champion_identity import reconcile
        report = reconcile(self.root, self.state_root, apply=True)
        if report.get("status") == "refused":
            self.journal("champion_state_reconcile_refused",
                         detail=str(report.get("detail")))
        return destination.name

    def _record_memory(self, payload: Mapping[str, Any], status: str,
                       outcome: Mapping[str, Any],
                       promoted_version: str | None = None,
                       lesson_note: str | None = None) -> None:
        """Append-only research memory + agent-state bookkeeping."""
        from autonomous_agent.core import (append_discovery,
                                           append_human_memory,
                                           build_research_record, utc_now)
        experiment_id = f"prop-{str(payload.get('proposal_fingerprint', ''))[:12]}"
        results = dict(outcome.get("results") or {})
        experiment = {
            "id": experiment_id,
            "direction": str(payload.get("direction")),
            "hypothesis": str(payload.get("hypothesis")),
            "status": status,
            "baseline_id": payload.get("baseline_id"),
            "rationale": str((payload.get("rationale") or {})
                             .get("open_question", "")),
            "failure": (outcome.get("rejection_reason")
                        if status != "ACCEPTED" else None),
            "rejection_reason": outcome.get("rejection_reason"),
            "results": results,
        }
        record = {
            "experiment_id": experiment_id,
            "created_at": utc_now(),
            "direction": experiment["direction"],
            "question": experiment["hypothesis"],
            "status": status,
            "blockers": list(outcome.get("blockers") or []),
            "lesson": (outcome.get("rejection_reason")
                       or lesson_note
                       or ("Promoted as " + promoted_version
                           if promoted_version else
                           "Candidate result recorded; review evaluation artifacts.")),
            "scientific_claim": False,
            "campaign_id": payload.get("campaign_id"),
            "proposal_fingerprint": payload.get("proposal_fingerprint"),
            "accepted_version": promoted_version,
        }
        record.update(build_research_record(experiment, None, outcome,
                                            self.state_root / "research_memory.json"))
        append_discovery(self.state_root / "research_memory.json", record)
        append_human_memory(self.root / "RESEARCH_MEMORY.md", record)
        self._update_agent_state(experiment, promoted_version)

    def _update_agent_state(self, experiment: Mapping[str, Any],
                            promoted_version: str | None) -> None:
        path = self.state_root / "agent_state.json"
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(state, dict):
            return
        experiments = state.setdefault("experiments", [])
        if any(item.get("id") == experiment.get("id") for item in experiments):
            return
        experiments.append({
            "id": experiment.get("id"),
            "direction": experiment.get("direction"),
            "status": experiment.get("status"),
            "created_at": self.clock(),
            "finished_at": self.clock(),
            "accepted_version": promoted_version,
            "campaign_id": None,
        })
        stats = state.setdefault("direction_stats", {})
        direction = str(experiment.get("direction"))
        entry = stats.setdefault(direction, {"attempts": 0, "accepted": 0,
                                              "rejected": 0})
        entry["attempts"] = int(entry.get("attempts", 0)) + 1
        key = "accepted" if experiment.get("status") == "ACCEPTED" else "rejected"
        entry[key] = int(entry.get(key, 0)) + 1
        from autonomous_agent.core import write_json_atomic
        write_json_atomic(path, state)

    def _recover_interrupted(self, ledger: ProposalLedger) -> None:
        """Crash between start-marker and adjudication: never re-run blind."""
        for merged in ledger.all_proposals():
            if merged.get("status") != schema.STATUS_EXECUTED:
                continue
            transitions = merged.get("transitions") or []
            last = transitions[-1] if transitions else {}
            detail = last.get("detail") or {}
            if detail.get("phase") != "started":
                continue
            experiment_id = str(detail.get("experiment_id") or "")
            result_path = (self.root / "autonomous_agent" / "candidates"
                           / experiment_id / "result.json")
            if result_path.is_file():
                # The adapter finished but the ledger did not get the tail:
                # adjudicate from the durable result, without re-running.
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    result = None
                if isinstance(result, dict):
                    from autonomous_agent.experiment_adapter import ExperimentResult
                    outcome = ExperimentResult.from_dict(result).to_supervisor_outcome()
                    payload = merged.get("proposal") or {}
                    spec = compiler.preview_spec(payload, root=self.root)
                    self._adjudicate(ledger, merged["proposal_id"], spec,
                                     str(detail.get("spec_sha256") or ""),
                                     payload, outcome)
                    continue
            ledger.transition(merged["proposal_id"],
                              schema.STATUS_FAILED_EXECUTION,
                              reason_code="EXECUTION_INTERRUPTED",
                              detail={"experiment_id": experiment_id,
                                      "error": "process interrupted before a "
                                               "durable result existed; the "
                                               "attempt is recorded, never "
                                               "silently retried"})

    # -- one cycle -----------------------------------------------------------
    def cycle_once(self) -> dict[str, Any]:
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        campaign = self.load_campaign()
        preflight = check_campaign5_authorization(
            self.root, campaign, campaign.get("authorization_scope"))
        if campaign.get("campaign_id") and str(campaign.get("campaign_id")).startswith("campaign-5") and not preflight["allowed"]:
            raise LoopStop("CAMPAIGN5_AUTHORIZATION_BLOCKED",
                           ",".join(preflight["reason_codes"]))
        if self.stop_file.exists():
            raise LoopStop("STOP_FILE", "explicit STOP file present")
        if self.stop_requested:
            raise LoopStop("STOP_REQUESTED", "in-process stop requested")
        policy = self._policy()
        self.safety_precheck(policy)
        # Crash recovery runs BEFORE anything else: an interrupted execution
        # is adjudicated from its durable result and never re-run.
        self._recover_interrupted(self._ledger())
        # Execution budget is checked BEFORE generating anything: never
        # create proposals that no execution budget could ever consume.
        budget = self.exhaustion_report()
        campaign = self.load_campaign()
        self._enforce_audit_stops(campaign)
        self._enforce_c5_signal_stops(campaign)
        maximum = int((campaign.get("execution") or {})
                      .get("max_total_executions", 4))
        if int(budget["executions_done"]) >= maximum:
            raise LoopStop("EXECUTION_BUDGET",
                           f"{budget['executions_done']}/{maximum} executed")
        if budget["portfolio_complete"] and not budget["approved_waiting"] \
                and not budget["compiled_waiting"] \
                and int(budget["remaining_total"]) <= 0:
            raise LoopStop("PORTFOLIO_COMPLETE",
                           "minimums met and proposal budget exhausted")
        self._state["cycle"] = int(self._state["cycle"]) + 1
        generation = self.phase_generate_and_approve()
        execution = self.phase_execute_one()
        # Refresh the durable execution counter from the ledger AFTER the
        # execution so budget accounting survives restarts exactly.
        self._state["executions_done"] = int(
            self.exhaustion_report()["executions_done"])
        result = {"cycle": int(self._state["cycle"]),
                  "generation": generation, "execution": execution}
        self.journal("cycle", **{k: (len(v) if isinstance(v, list) else v)
                                 for k, v in generation.items()},
                     action=execution.get("action"))
        return result

    # -- driver --------------------------------------------------------------
    def run(self) -> dict[str, Any]:
        from autonomous_agent.campaign5_authorization import check_campaign5_authorization
        try:
            campaign = self.load_campaign()
        except LoopStop:
            # Preserve the normal durable startup-stop path for malformed or
            # missing campaign configs; no execution can be reached from it.
            campaign = None
        if campaign is not None:
            preflight = check_campaign5_authorization(
                self.root, campaign, campaign.get("authorization_scope"))
            if campaign["campaign_id"].startswith("campaign-5") and not preflight["allowed"]:
                raise LoopStop("CAMPAIGN5_AUTHORIZATION_BLOCKED",
                               ",".join(preflight["reason_codes"]))
        if not self.acquire_lock():
            raise LoopStop("LOCKED", "another loop holds the lock")
        summary: dict[str, Any] = {"campaign_id": None, "cycles": 0,
                                   "stop_reason": None, "status": None}
        startup_stop: LoopStop | None = None
        try:
            try:
                # Human launch gates are checked at the very start of the
                # guarded startup section: the stop is recorded durably
                # (durable state + summary stop_reason) like every other
                # startup stop, and it can never preempt the LOCKED stop or
                # run outside the lock.
                if campaign is not None:
                    self._check_launch_gates(campaign)
                self._state = self.load_state()
                summary["campaign_id"] = self._state.get("campaign_id")
                self._state["status"] = "RUNNING"
                self.save_state()
                self.journal("loop_started", pid=os.getpid(),
                             max_cycles=self.max_cycles,
                             campaign_config_sha256=self._state.get(
                                 "campaign_config_sha256"))
            except LoopStop as stop:
                # A hard stop raised during startup (e.g. campaign config
                # tamper, missing sidecar, flag off) must stop the loop
                # cleanly instead of escaping run().
                startup_stop = stop
                if not self._state:
                    self._state = {"schema_version": 1, "cycle": 0,
                                   "executions_done": 0,
                                   "consecutive_failures": 0}
                summary["campaign_id"] = self._state.get("campaign_id")
                self._state["status"] = "STOPPED"
                self._state["last_stop_reason"] = stop.reason
                self._state["last_error"] = stop.detail or None
                summary["stop_reason"] = stop.reason
                summary["stop_detail"] = stop.detail
                self.journal("loop_stop_at_startup", reason=stop.reason,
                             detail=stop.detail)
            while startup_stop is None \
                    and int(self._state["cycle"]) < self.max_cycles:
                cycle_started = time.monotonic()
                try:
                    self.cycle_once()
                    self._state["consecutive_failures"] = 0
                    self.save_state()
                    # Phase watchdog (separate bounded change): runs only at a
                    # CLEAN cycle boundary — cycle_once has fully finished and
                    # its adjudication/recovery/transitions are already durable
                    # — so the overflow stop cannot preempt or bypass any
                    # recovery or authorization check. It is pure failure
                    # logging: an explicit journal event plus the standard
                    # durable stop path, identical to every other stop reason.
                    if self.max_cycle_seconds is not None:
                        elapsed = time.monotonic() - cycle_started
                        if elapsed > float(self.max_cycle_seconds):
                            detail = (f"cycle took {elapsed:.3f}s which exceeds "
                                      f"the declared bound "
                                      f"{self.max_cycle_seconds:.3f}s")
                            self._state["status"] = "STOPPED"
                            self._state["last_stop_reason"] = "WATCHDOG_CYCLE_OVERFLOW"
                            self._state["last_error"] = detail
                            self.save_state()
                            summary["stop_reason"] = "WATCHDOG_CYCLE_OVERFLOW"
                            summary["stop_detail"] = detail
                            self.journal("phase_watchdog_overflow",
                                         elapsed_seconds=round(elapsed, 3),
                                         bound_seconds=self.max_cycle_seconds)
                            summary["cycles"] = int(self._state["cycle"])
                            summary["cycles_run"] = summary["cycles"]
                            break
                except LoopStop as stop:
                    self._state["status"] = "STOPPED"
                    self._state["last_stop_reason"] = stop.reason
                    self._state["last_error"] = stop.detail or None
                    summary["stop_reason"] = stop.reason
                    summary["stop_detail"] = stop.detail
                    break
                except (LedgerError, LedgerCorrupt) as fatal:
                    # Invalid lifecycle / corrupted state: hard stop.
                    self._state["status"] = "FAILED"
                    self._state["last_stop_reason"] = "INVALID_LEDGER_STATE"
                    self._state["last_error"] = str(fatal)
                    summary["stop_reason"] = "INVALID_LEDGER_STATE"
                    summary["stop_detail"] = str(fatal)
                    break
                except Exception as error:  # noqa: BLE001 - crash guard
                    failures = int(self._state.get("consecutive_failures", 0)) + 1
                    self._state["consecutive_failures"] = failures
                    self._state["last_error"] = (
                        f"cycle {type(error).__name__}: {error}")
                    self.save_state()
                    self.journal("cycle_error", error=self._state["last_error"])
                    if failures >= MAX_CONSECUTIVE_FAILURES:
                        self._state["status"] = "FAILED"
                        self._state["last_stop_reason"] = "REPEATED_CRASHES"
                        summary["stop_reason"] = "REPEATED_CRASHES"
                        summary["stop_detail"] = self._state["last_error"]
                        break
                summary["cycles"] = int(self._state["cycle"])
                if self.idle_seconds and \
                        int(self._state["cycle"]) < self.max_cycles:
                    deadline = time.monotonic() + self.idle_seconds
                    while time.monotonic() < deadline \
                            and not self.stop_file.exists():
                        time.sleep(min(0.2, deadline - time.monotonic()))
            else:
                self._state["last_stop_reason"] = (
                    self._state.get("last_stop_reason") or "MAX_CYCLES")
                summary["stop_reason"] = summary.get("stop_reason") or "MAX_CYCLES"
            if self._state.get("status") == "RUNNING":
                self._state["status"] = "STOPPED"
                summary.setdefault("stop_reason",
                                   self._state.get("last_stop_reason")
                                   or "MAX_CYCLES")
            # H-6 stop-time completeness guard: a campaign whose frozen
            # policy requires a campaign-end multiplicity record must not
            # finish silently without one. The gap is journaled and pinned
            # into the durable summary with the DECLARED outcome (e.g.
            # C5's pre-declared no_multiplicity_record_outcome); this never
            # fabricates a record and never upgrades provisional signals.
            if campaign is not None:
                gap = campaign_end_gap_status(
                    campaign, self.root / "autonomous_agent" / "state" / "campaign_end_multiplicity.jsonl")
                if gap is not None:
                    summary["multiplicity_outcome"] = gap["outcome"]
                    self._state["multiplicity_outcome"] = gap["outcome"]
                    self.journal("campaign_end_multiplicity_missing", **gap)
            self.save_state()
            self.journal("loop_stopped", cycles=int(self._state["cycle"]),
                         reason=summary.get("stop_reason"),
                         status=self._state.get("status"))
        finally:
            self.release_lock()
        summary["status"] = self._state.get("status")
        summary["executions_done"] = self._state.get("executions_done")
        return summary


def cap_remaining(view, policy) -> int:
    return int(generator.capacity(view, policy)["remaining_total"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autonomous_agent.continuous_loop",
        description="Persistent research loop (bounded; never implicit-"
                    "infinite). Execution requires explicit authorization "
                    "and an explicit --max-cycles.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--max-cycles", type=int, required=True,
                        help="explicit positive cycle bound (required: there "
                             "is no implicit infinite mode)")
    parser.add_argument("--idle-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    if int(args.max_cycles) <= 0:
        parser.error("--max-cycles must be a positive integer")
    loop = ResearchLoop(args.root, max_cycles=args.max_cycles,
                        idle_seconds=args.idle_seconds)
    try:
        summary = loop.run()
    except LoopStop as stop:
        print(stop, file=sys.stderr)
        return 3
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
