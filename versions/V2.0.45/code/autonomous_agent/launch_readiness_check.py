#!/usr/bin/env python3
"""Read-only Campaign 4 launch-readiness checker.

Runs every launch prerequisite that can be checked mechanically (pins,
holdout seal, frozen-config content, stop-condition wiring, v1.1.0
implementation markers, review-bundle integrity) and reports the human
gates from an owner-maintained gates file.

HONESTY CONTRACT
  * This tool never approves, freezes, signs, or launches anything. It
    reads files and prints what it found.
  * A human gate recorded in the gates file is *evidence the owner
    recorded*, not machine proof that a review was independent or that an
    approval was genuine. Independence and approval remain human
    judgments.
  * Implementation checks are source-marker heuristics; a marker can be
    satisfied by a comment. They are a pre-flight aid, never a proof.
  * It never writes to, opens, or derives anything from holdout data.

EXIT CODES
  0  every machine check PASS and every human gate recorded
  2  at least one machine check FAIL/BLOCKED (not ready)
  3  machine checks pass, human gates still outstanding
  1  usage / IO error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

PASS, FAIL, BLOCKED, INFO, HUMAN, RECORDED = (
    "PASS", "FAIL", "BLOCKED", "INFO", "HUMAN", "RECORDED")

# Prefixes pinned in H10_OWNER_AUTHORIZATION_RECORD_2026_10_11.md,
# the review packet provenance table, and the flake evidence file.
DEFAULT_PINS = {
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "HARNESS_V1_1_0_IMPLEMENTATION_PLAN_2026_10_09.md": "094827b0",
    "stat_validation_h10/H10_DECISION_RECORD_AWAITING_SIGNATURE.md": "b9db3233",
    "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
    "GOVERNANCE_SUITE_FLAKE_EVIDENCE_2026_10_11.md": "72504661",
    "autonomous_agent/test_continuous_loop.py": "e1de8523",
    "stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip": "ee345dab",
}

# Frozen Campaign 3 stop conditions -- must all be carried into C4 verbatim.
C3_STOPS = [
    "max_total_executions_reached",
    "portfolio_minimums_met_and_no_admissible_proposal",
    "holdout_or_prospective_access_detected",
    "arbitrary_code_or_executor_bypass_detected",
    "validation_or_approval_bypass_detected",
    "provenance_loss_or_ledger_corruption",
    "budget_inconsistency_or_negative_capacity",
    "duplicate_execution_detected",
    "invalid_lifecycle_transition",
    "repeated_crash_threshold_exceeded",
    "stale_loop_lock",
    "research_proposal_direction_or_class_exhaustion",
    "explicit_STOP_file_present",
    "campaign_config_hash_mismatch",
]
NEW_STOPS = [
    "point_in_time_contamination_detected",
    "unverifiable_lineage_detected",  # proposed identifier, owner to confirm
]
FIVE_DORMANT = [
    "purge_sensitivity_probe",
    "regime_split_analysis",
    "complexity_reduction_check",
    "target_horizon_robustness",
    "point_in_time_data_audit",
]
PLACEHOLDER_RX = re.compile(r"TO_BE_|_AT_FREEZE|-XX\b|DRAFT_ONLY|TBD|PLACEHOLDER", re.I)
HARNESS_CODE = ("recipe_harness.py", "spec_recipes.py", "experiment_adapter.py",
                "continuous_loop.py", "core.py")
HARNESS_PROPOSAL_LAYER = tuple(
    "proposal_layer/" + name for name in
    ("multiplicity.py", "census.py", "ledger.py", "validator.py",
     "primitives.py", "compiler.py", "generator.py", "schema.py", "cycle.py"))
# Wiring markers: each entry is (needles that must ALL appear in the harness
# source, human-readable description). Kept in step with the implementation;
# a marker that no longer matches is a wiring regression, not a pass.
WIRING_MARKERS = {
    "impl.stop.pit": (["audit_stop_signal", "CONFIRMED_CONTAMINATION"],
                      "point-in-time contamination stop wired"),
    "impl.stop.lineage": (["recorded_audit_stop", "UNVERIFIABLE_LINEAGE"],
                          "UNVERIFIABLE-lineage stop wired"),
    "impl.holm": (["holm_step_down"], "Holm step-down implemented"),
    "impl.firewall": (["formal_refutation", "refutation_signal"],
                      "provisional-to-formal firewall markers"),
    "impl.pvalue_gate": (["p_value_method", "PValueMethodUnresolved"],
                         "H-10 fail-closed p-value gate"),
    "impl.census": (["validate_manifest", "OBSERVED_MISMATCH"],
                    "census manifest validator with the frozen-tolerance rule"),
}
HUMAN_GATES = [
    ("review_received", "independent written assessment exists in the repository"),
    ("d2_decided", "D2 recorded as decided (adopt / reject / deferred-with-rationale)"),
    ("c3_ratified", "C-3 ratified (required only if D2 adopted)"),
    ("implementation_authorized", "gate 3 separate implementation authorization recorded"),
    ("implementation_complete", "v1.1.0 implemented and full test suite green"),
    ("freeze_approved", "gate 6 freeze approval recorded"),
    ("launch_authorized", "gate 8 explicit Campaign 4 launch authorization recorded"),
]
GATES_TEMPLATE = {
    "_NOTE": ("TEMPLATE -- every value is false. The HUMAN OWNER fills this in "
              "and saves it as launch_gates.json after each decision. An entry "
              "here is the owner's recorded evidence, not machine proof."),
    "_required_fields_per_gate": ["decided", "decided_by", "date", "evidence_path"],
    "review_received": {"decided": False, "decided_by": "", "date": "",
                        "evidence_path": ""},
    "d2_decided": {"decided": False, "decided_by": "", "date": "", "evidence_path": "",
                   "decision": ""},
    "c3_ratified": {"decided": False, "decided_by": "", "date": "", "evidence_path": ""},
    "implementation_authorized": {"decided": False, "decided_by": "", "date": "",
                                  "evidence_path": ""},
    "implementation_complete": {"decided": False, "decided_by": "", "date": "",
                                "evidence_path": ""},
    "freeze_approved": {"decided": False, "decided_by": "", "date": "",
                        "evidence_path": ""},
    "launch_authorized": {"decided": False, "decided_by": "", "date": "",
                          "evidence_path": ""},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, status: str, code: str, msg: str) -> None:
        self.rows.append((status, code, msg))

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for status, _, _ in self.rows:
            out[status] = out.get(status, 0) + 1
        return out

    def render(self) -> str:
        lines = []
        for status, code, msg in self.rows:
            lines.append(f"[{status:7}] {code}: {msg}")
        return "\n".join(lines)


def read_json(path: Path):
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed silently
        return exc


# ---------------------------------------------------------------- machine checks
def check_integrity(root: Path, pins: dict, rep: Report) -> None:
    for rel, prefix in pins.items():
        path = root / rel
        if not path.exists():
            rep.add(FAIL, "integrity.pin.missing", f"{rel} is absent")
            continue
        got = sha256(path)
        if got.startswith(prefix):
            rep.add(PASS, "integrity.pin", f"{rel} = {got[:16]}…")
        else:
            rep.add(FAIL, "integrity.pin.mismatch",
                    f"{rel}: expected {prefix}… got {got[:16]}…")

    cfg_path = root / "autonomous_agent/state/campaign_config.json"
    pin_path = root / "autonomous_agent/state/campaign_config.sha256"
    if not cfg_path.exists():
        rep.add(FAIL, "integrity.config.missing", "state/campaign_config.json absent")
    elif not pin_path.exists():
        rep.add(FAIL, "integrity.pinfile.missing", "campaign_config.sha256 absent")
    else:
        pinned = pin_path.read_text("utf-8").split()[0]
        actual = sha256(cfg_path)
        if pinned == actual:
            rep.add(PASS, "integrity.config.pin", f"pin == file ({actual[:16]}…)")
        else:
            rep.add(FAIL, "integrity.config.pin",
                    f"pin {pinned[:16]}… != file {actual[:16]}…")

    bundle = root / "stat_validation_h10/H10_D2_REVIEW_SUBMISSION.zip"
    if not bundle.exists():
        rep.add(BLOCKED, "bundle.absent", "review bundle missing")
        return
    try:
        with zipfile.ZipFile(bundle) as zf:
            bad = zf.testzip()
            names = zf.namelist()
            manifest_name = next((n for n in names if n.endswith("BUNDLE_MANIFEST.txt")), None)
            mism = []
            if manifest_name:
                lines = zf.read(manifest_name).decode("utf-8", "replace").splitlines()
                want = {}
                for i, line in enumerate(lines):
                    if i and re.fullmatch(r"[0-9a-f]{64}", line.strip()):
                        want[lines[i - 1].strip()] = line.strip()
                for name, digest in want.items():
                    cand = next((n for n in names if n == name or n.endswith("/" + name)), None)
                    if cand is None:
                        mism.append(f"missing:{name}")
                    elif hashlib.sha256(zf.read(cand)).hexdigest() != digest:
                        mism.append(f"hash:{name}")
            if bad or mism:
                rep.add(FAIL, "bundle.integrity",
                        f"corrupt={bad} manifest_problems={mism[:3]}")
            else:
                rep.add(PASS, "bundle.integrity",
                        f"{len(names)} entries, manifest hashes verified")
    except Exception as exc:  # noqa: BLE001
        rep.add(FAIL, "bundle.unreadable", str(exc))


def check_holdout(root: Path, cfg: dict, rep: Report) -> None:
    leaked = [p for p in ("prospective", "autonomous_agent/prospective",
                          "study_files/prospective") if (root / p).exists()]
    if leaked:
        rep.add(FAIL, "holdout.directory_present", f"sealed path exists: {leaked}")
    else:
        rep.add(PASS, "holdout.directory_absent", "prospective/ absent at all candidate roots")
    policy = cfg.get("holdout_policy") or {}
    if (policy.get("status") == "SEALED" and policy.get("uses") == 0
            and policy.get("prospective_usage") == 0):
        rep.add(PASS, "holdout.policy", "SEALED, uses 0, prospective_usage 0")
    else:
        rep.add(FAIL, "holdout.policy", f"unexpected policy: {policy}")


def check_live_state(root: Path, rep: Report) -> None:
    state = root / "autonomous_agent/state"
    present = [n for n in ("loop.lock", "supervisor.lock", "STOP")
               if (state / n).exists()]
    if present:
        rep.add(INFO, "live_state.lock_or_stop", f"present (must be absent at launch): {present}")
    else:
        rep.add(PASS, "live_state.clean", "no loop.lock, supervisor.lock, or STOP")


def check_c4_config(root: Path, cfg: dict, rep: Report) -> None:
    cid = str(cfg.get("campaign_id", ""))
    if not cid.startswith("campaign-4"):
        rep.add(BLOCKED, "c4.not_frozen",
                f"state config is {cid!r}; a frozen C4 config must be in state/ before launch")
        return
    rep.add(PASS, "c4.campaign_id", cid)

    blob = json.dumps(cfg)
    holes = sorted(set(PLACEHOLDER_RX.findall(blob)))
    if holes:
        rep.add(FAIL, "c4.placeholders", f"unfinalized values remain: {holes[:5]}")
    else:
        rep.add(PASS, "c4.placeholders", "no TO_BE_/-XX/DRAFT placeholders")

    exec_budget = (cfg.get("execution") or {}).get("max_total_executions")
    prop_budget = (cfg.get("policy_overrides") or {}).get("max_total_proposals")
    # 2026-10-15 capacity re-freeze (owner directive "Continue Campaign 4
    # Through Completion"): proposal total 45 -> 64, ceilings only, with
    # every statistical constraint unchanged. Evidence:
    # C4_GENERATOR_REPAIR_AND_REFREEZE_RECORD_2026_10_15.md section 6 and
    # cfg._FREEZE_STATUS.capacity_amendment.
    if exec_budget == 31 and prop_budget == 64:
        rep.add(PASS, "c4.budget", "31 executions / 64 proposals (capacity re-freeze #2, interruption slack)")
    else:
        rep.add(FAIL, "c4.budget", f"executions={exec_budget} proposals={prop_budget} (expected 31/64)")

    stops = cfg.get("stop_conditions") or []
    missing_c3 = [s for s in C3_STOPS if s not in stops]
    missing_new = [s for s in NEW_STOPS if s not in stops]
    if missing_c3:
        rep.add(FAIL, "c4.stops.c3", f"C3 stops missing: {missing_c3}")
    else:
        rep.add(PASS, "c4.stops.c3", f"all {len(C3_STOPS)} C3 stops carried forward")
    if missing_new:
        rep.add(FAIL, "c4.stops.new", f"required new stops missing: {missing_new}")
    else:
        rep.add(PASS, "c4.stops.new", f"both new stops declared ({len(stops)} total)")

    fp = str(cfg.get("protocol_fingerprint", ""))
    if re.fullmatch(r"[0-9a-f]{64}", fp):
        rep.add(PASS, "c4.fingerprint", f"{fp[:16]}…")
    else:
        rep.add(FAIL, "c4.fingerprint", f"not a 64-hex fingerprint: {fp!r}")

    if cfg.get("immutable") is True:
        rep.add(PASS, "c4.immutable", "immutable: true")
    else:
        rep.add(FAIL, "c4.immutable", "immutable flag missing/false")

    # multiplicity / H-10b feasibility
    mult = cfg.get("multiplicity_policy")
    if not isinstance(mult, dict):
        rep.add(FAIL, "c4.multiplicity.absent",
                "no multiplicity_policy block (n_boot, family caps, C-2 rule)")
        return
    n_boot = mult.get("n_boot")
    if not isinstance(n_boot, int) or n_boot < 1000:
        rep.add(FAIL, "c4.multiplicity.n_boot", f"n_boot={n_boot!r}, requires >= 1000")
    else:
        rep.add(PASS, "c4.multiplicity.n_boot", f"n_boot = {n_boot}")
    # M (the sign-flip count) governs the p-value's resolution 1/(M+1); a
    # recorded feasibility without it can disagree with what the p-value can
    # actually resolve (D2 review 2026-10-13, freeze-test gap / Condition 3).
    n_flips = mult.get("n_flips")
    if not isinstance(n_flips, int) or n_flips < 1000:
        rep.add(FAIL, "c4.multiplicity.n_flips",
                f"n_flips={n_flips!r}, requires >= 1000 (M pins the p-value "
                "resolution; the recorded feasibility must include it)")
    else:
        rep.add(PASS, "c4.multiplicity.n_flips", f"n_flips (M) = {n_flips}")
    fams = mult.get("families") or {}
    if not fams:
        rep.add(FAIL, "c4.multiplicity.families", "no fixed family membership declared")
        return
    bad = []
    for name, spec in fams.items():
        m = spec.get("member_bound")
        if not isinstance(m, int) or m <= 0:
            bad.append(f"{name}: no member_bound")
        elif n_boot is None or n_boot + 1 < 20 * m:
            bad.append(f"{name}: m={m} needs n_boot >= {20 * m - 1}")
        if isinstance(m, int) and m > 0 and \
                (not isinstance(n_flips, int) or n_flips + 1 < 20 * m):
            bad.append(f"{name}: m={m} needs n_flips (M) >= {20 * m - 1}")
        if isinstance(m, int) and m > 50:
            bad.append(f"{name}: m={m} exceeds D4 cap 50")
    if bad:
        rep.add(FAIL, "c4.multiplicity.feasibility", "; ".join(bad))
    else:
        rep.add(PASS, "c4.multiplicity.feasibility",
                f"n_boot+1 >= 20*m, n_flips+1 >= 20*m, and m <= 50 for "
                f"{len(fams)} families")
    if mult.get("missing_member_p") == 1.0 and mult.get("missing_member_never_refuted") is True:
        rep.add(PASS, "c4.multiplicity.c2", "C-2 missing-member rule present (p=1.0, never REFUTED)")
    else:
        rep.add(FAIL, "c4.multiplicity.c2", "C-2 missing-member rule not declared")


def check_implementation(root: Path, rep: Report) -> None:
    src = {}
    for rel in HARNESS_CODE + HARNESS_PROPOSAL_LAYER:
        path = root / "autonomous_agent" / rel
        src[rel] = path.read_text("utf-8", "replace") if path.exists() else ""
    code_all = "\n".join(src.values())

    for code, (needles, description) in WIRING_MARKERS.items():
        missing = [needle for needle in needles if needle not in code_all]
        if missing:
            rep.add(BLOCKED, code,
                    f"{description}: missing {missing} in harness source")
        else:
            rep.add(PASS, code, description)

    prim_path = root / "autonomous_agent/proposal_layer/primitives.py"

    if not prim_path.exists():
        rep.add(FAIL, "impl.primitives.missing", "proposal_layer/primitives.py absent")
    else:
        text = prim_path.read_text("utf-8", "replace")
        still_dormant = []
        for pid in FIVE_DORMANT:
            m = re.search(r'primitive_id="%s"[\s\S]{0,400}?executable=(True|False)' % re.escape(pid), text)
            if not m:
                still_dormant.append(f"{pid}:not-found")
            elif m.group(1) == "False":
                still_dormant.append(pid)
        if still_dormant:
            rep.add(BLOCKED, "impl.primitives.dormant",
                    f"{len(still_dormant)}/5 primitives still executable=False: "
                    f"{still_dormant} (primitive activation was NOT part of the "
                    f"2026-10-12 gate-3 authorization; it needs its own grant)")
        else:
            rep.add(PASS, "impl.primitives.dormant",
                    "all five v1.1.0 primitives executable")
    tests_dir = root / "autonomous_agent"
    test_text = "\n".join(p.read_text("utf-8", "replace")
                          for p in sorted(tests_dir.glob("test_*.py")))
    if "stop_conditions" in test_text:
        rep.add(PASS, "impl.test.stop_correspondence", "a test reads stop_conditions")
    else:
        rep.add(BLOCKED, "impl.test.stop_correspondence",
                "no test asserts config stop list ↔ enforcement code")
    if re.search(r"holm", test_text, re.I):
        rep.add(PASS, "impl.test.holm", "Holm tests present")
    else:
        rep.add(BLOCKED, "impl.test.holm", "no Holm tests")
    if re.search(r"multiplicity|firewall", test_text, re.I):
        rep.add(PASS, "impl.test.multiplicity", "multiplicity/firewall tests present")
    else:
        rep.add(BLOCKED, "impl.test.multiplicity", "no multiplicity/firewall tests")


# ------------------------------------------------------------------ human gates
def check_human_gates(root: Path, gates_path: Path, rep: Report) -> None:
    if not gates_path.exists():
        rep.add(HUMAN, "gates.file_absent",
                f"{gates_path.relative_to(root) if gates_path.is_relative_to(root) else gates_path} "
                "not written yet -- owner fills it per decision (use --write-template)")
        for name, why in HUMAN_GATES:
            rep.add(HUMAN, f"gates.{name}", "outstanding: " + why)
        return
    data = read_json(gates_path)
    if isinstance(data, Exception):
        rep.add(FAIL, "gates.unreadable", str(data))
        return
    for name, why in HUMAN_GATES:
        entry = data.get(name)
        if not isinstance(entry, dict):
            rep.add(HUMAN, f"gates.{name}", "not recorded: " + why)
            continue
        missing = [k for k in ("decided", "decided_by", "date", "evidence_path")
                   if k not in entry]
        if missing:
            rep.add(FAIL, f"gates.{name}.incomplete", f"missing fields {missing}")
            continue
        if entry.get("decided") is not True:
            rep.add(HUMAN, f"gates.{name}", "recorded as not decided: " + why)
            continue
        ev = entry.get("evidence_path") or ""
        ev_path = root / ev
        if not ev or not ev_path.exists() or ev_path.stat().st_size == 0:
            rep.add(FAIL, f"gates.{name}.evidence",
                    f"decided=true but evidence_path {ev!r} is missing or empty")
            continue
        if not str(entry.get("decided_by", "")).strip() or not str(entry.get("date", "")).strip():
            rep.add(FAIL, f"gates.{name}.provenance", "decided_by/date empty")
            continue
        rep.add(RECORDED, f"gates.{name}",
                f"recorded by {entry['decided_by']} on {entry['date']} -> {ev} "
                f"({why}; recorded evidence, not machine proof)")


# ------------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    ap.add_argument("--pins", help="JSON file overriding the built-in pin table")
    ap.add_argument("--gates", default="stat_validation_h10/launch_gates.json",
                    help="owner-maintained human-gate record")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--write-template", metavar="PATH",
                    help="write the blank human-gate template and exit")
    args = ap.parse_args(argv)

    if args.write_template:
        Path(args.write_template).write_text(
            json.dumps(GATES_TEMPLATE, indent=2) + "\n", "utf-8")
        print(f"wrote blank template: {args.write_template}")
        return 0

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    pins = dict(DEFAULT_PINS)
    if args.pins:
        try:
            pins.update(json.loads(Path(args.pins).read_text("utf-8")))
        except Exception as exc:  # noqa: BLE001
            print(f"error: cannot read pins file: {exc}", file=sys.stderr)
            return 1

    rep = Report()
    cfg_path = root / "autonomous_agent/state/campaign_config.json"
    cfg = read_json(cfg_path)
    if isinstance(cfg, Exception):
        rep.add(FAIL, "config.unreadable", str(cfg))
        cfg = {}

    check_integrity(root, pins, rep)
    if cfg:
        check_holdout(root, cfg, rep)
    check_live_state(root, rep)
    if cfg:
        check_c4_config(root, cfg, rep)
    check_implementation(root, rep)
    check_human_gates(root, (root / args.gates) if not Path(args.gates).is_absolute()
                      else Path(args.gates), rep)

    counts = rep.counts()
    machine_bad = counts.get(FAIL, 0) + counts.get(BLOCKED, 0)
    human_outstanding = counts.get(HUMAN, 0)
    verdict = ("NOT READY" if machine_bad else
               ("MACHINE-CHECKS PASS; HUMAN GATES OUTSTANDING" if human_outstanding else
                "READY (machine checks pass and all human gates recorded)"))
    exit_code = 2 if machine_bad else (3 if human_outstanding else 0)

    if args.json:
        print(json.dumps({"root": str(root), "verdict": verdict, "exit_code": exit_code,
                          "counts": counts,
                          "results": [{"status": s, "code": c, "message": m}
                                      for s, c, m in rep.rows]}, indent=2))
    else:
        print(f"CAMPAIGN 4 LAUNCH READINESS -- root={root}")
        print(rep.render())
        print(f"\nsummary: {counts}  ->  {verdict}")
        print("note: this tool approves nothing; human gates are recorded evidence, "
              "not machine proof.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
