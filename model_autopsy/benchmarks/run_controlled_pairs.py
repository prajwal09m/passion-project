"""Run the pre-registered controlled Groq continuation experiment.

Benchmark-only driver. It never touches production code, never reads
MODEL_API_KEY, and never overwrites an existing artifact. Each pair runs in a
fresh sandbox SQLite database inside a fresh temp directory; the harness itself
enforces per-pair HTTP-attempt, token and estimated-cost caps, and this driver
enforces the frozen global caps from
`phase_d_groq_controlled_preregistration_2026-10-29.md`.

Usage:
    py benchmarks/run_controlled_pairs.py            # run up to 5 pairs
    py benchmarks/run_controlled_pairs.py --pairs 1  # one pair (smoke)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent.parent
HARNESS = BENCH_DIR / "groq_paired_continuation_benchmark.py"
MODEL = "openai/gpt-oss-120b"

GLOBAL_CAPS = {
    "max_pairs": 5,
    "max_attempts": 100,
    "max_total_tokens": 300_000,
    "max_est_cost_usd": 0.50,
    "max_aborted_pairs": 2,
}
PER_PAIR = {
    "max_attempts": 30,
    "max_total_tokens": 80_000,
    "max_est_cost_usd": 0.10,
    "repeated_429_limit": 4,
}
PAIR_TIMEOUT_S = 2400


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _key_available() -> bool:
    if os.environ.get("GROQ_API_KEY", "").strip():
        return True
    env_file = BENCH_DIR.parent / ".env"
    if not env_file.exists():
        return False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("GROQ_API_KEY=") and s.split("=", 1)[1].strip():
            return True
    return False


def _load_existing(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_atomic(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str),
                   encoding="utf-8")
    os.replace(tmp, path)


def _design_check(out: dict) -> tuple[bool, str]:
    if out.get("controlled_mode") is not True:
        return False, "controlled_mode is not true"
    if out.get("model") != MODEL:
        return False, f"model changed: {out.get('model')!r}"
    runs = out.get("runs") or []
    if len(runs) != 2:
        return False, f"expected 2 runs, got {len(runs)}"
    designs = [r.get("controlled_design") or {} for r in runs]
    if not all(d.get("enabled") is True for d in designs):
        return False, "a run has controlled_design.enabled != true"
    instr = {d.get("continuation_instruction") for d in designs}
    if len(instr) != 1:
        return False, "continuation instructions differ"
    budgets = {(d.get("turn_rounds"), d.get("max_tool_calls"))
               for d in designs}
    if len(budgets) != 1:
        return False, f"budgets differ: {budgets}"
    if sorted(d.get("recorded_context_included") for d in designs) != \
            [False, True]:
        return False, "recorded_context_included is not one True/one False"
    if any(d.get("forced_diagnostic") is not False for d in designs):
        return False, "forced_diagnostic is not false"
    conditions = {r.get("condition") for r in runs}
    if conditions != {"full", "delta"}:
        return False, f"unexpected conditions: {conditions}"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs", type=int, default=GLOBAL_CAPS["max_pairs"],
                    help="how many pairs to attempt (hard ceiling 5)")
    ap.add_argument("--ledger", default=str(
        BENCH_DIR / "phase_d_groq_controlled_ledger.json"))
    args = ap.parse_args()
    pairs_to_run = min(max(1, args.pairs), GLOBAL_CAPS["max_pairs"])
    ledger_path = Path(args.ledger)

    existing = _load_existing(ledger_path)
    if existing is not None:
        print(f"REFUSING TO OVERWRITE: {ledger_path} already exists "
              f"({len(existing.get('pairs', []))} pairs recorded).",
              flush=True)
        return 2

    if not _key_available():
        print("BLOCKED: GROQ_API_KEY is not configured "
              "(process env or model_autopsy/.env). Zero requests made.",
              flush=True)
        return 2
    if not HARNESS.exists():
        print(f"BLOCKED: harness not found at {HARNESS}", flush=True)
        return 2

    ledger: dict = {
        "campaign": "phase_d_groq_controlled_2026-10-29",
        "preregistration":
            "phase_d_groq_controlled_preregistration_2026-10-29.md",
        "started_utc": _now(),
        "model": MODEL,
        "global_caps": GLOBAL_CAPS,
        "per_pair_caps": PER_PAIR,
        "pairs": [],
        "status": "running",
        "stop_reason": None,
    }
    _write_atomic(ledger_path, ledger)

    total_attempts = 0
    total_tokens = 0
    total_cost = 0.0
    aborted_pairs = 0
    stop_reason: str | None = None

    for n in range(1, pairs_to_run + 1):
        if stop_reason:
            break
        first = "full" if n % 2 == 1 else "delta"
        pair_file = BENCH_DIR / f"phase_d_groq_controlled_pair{n}.json"
        if pair_file.exists():
            stop_reason = f"refusing to overwrite existing {pair_file.name}"
            break
        sandbox_dir = Path(tempfile.mkdtemp(prefix=f"ma-controlled-p{n}-"))
        db_path = sandbox_dir / "sandbox.db"
        env = dict(os.environ)
        env["MODEL_AUTOPSY_DB_PATH"] = str(db_path)
        env["PYTHONPATH"] = str(REPO_ROOT)
        cmd = [
            sys.executable, str(HARNESS),
            "--controlled", "--pairs", "1", "--model", MODEL,
            "--first", first,
            "--max-attempts", str(PER_PAIR["max_attempts"]),
            "--max-total-tokens", str(PER_PAIR["max_total_tokens"]),
            "--max-est-cost", str(PER_PAIR["max_est_cost_usd"]),
            "--repeated-429-limit", str(PER_PAIR["repeated_429_limit"]),
            "--out", str(pair_file),
        ]
        started = _now()
        print(f"[pair {n}] start {started} order={first} first "
              f"db={db_path}", flush=True)
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd, cwd=str(BENCH_DIR), env=env, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                timeout=PAIR_TIMEOUT_S)
            rc = proc.returncode
            stderr_tail = (proc.stderr or "")[-2000:]
        except subprocess.TimeoutExpired as exc:
            rc = -9
            stderr_tail = f"pair timeout after {PAIR_TIMEOUT_S}s: {exc}"
        elapsed = round(time.perf_counter() - t0, 1)

        record: dict = {
            "pair": n,
            "order": [first, "delta" if first == "full" else "full"],
            "started_utc": started,
            "elapsed_s": elapsed,
            "exit_code": rc,
            "pair_file": pair_file.name,
            "sandbox_db": str(db_path),
        }
        out = _load_existing(pair_file)
        if rc != 0 or not isinstance(out, dict):
            record["status"] = "aborted: harness did not produce a ledger"
            record["stderr_tail"] = stderr_tail
            ledger["pairs"].append(record)
            ledger["status"] = "stopped"
            stop_reason = f"pair {n} failed (exit {rc})"
            break

        totals = out.get("totals") or {}
        attempts = int(totals.get("provider_http_attempts") or 0)
        tokens = int(totals.get("input_tokens") or 0) + \
            int(totals.get("output_tokens") or 0)
        cost = float(totals.get("estimated_cost_usd") or 0.0)
        runs = out.get("runs") or []
        aborted = [r for r in runs
                   if r.get("aborted") or str(r.get("status", ""))
                   .startswith(("aborted", "failed", "skipped"))]
        design_ok, design_msg = _design_check(out)
        record.update({
            "status": "completed" if not totals.get("stop_reason")
            else f"stopped: {totals.get('stop_reason')}",
            "condition_order_ledger": out.get("condition_order"),
            "provider_http_attempts": attempts,
            "input_tokens": totals.get("input_tokens"),
            "output_tokens": totals.get("output_tokens"),
            "estimated_cost_usd": cost,
            "stop_reason": totals.get("stop_reason"),
            "aborted_runs": len(aborted),
            "design_check": {"ok": design_ok, "detail": design_msg},
            "summary_valid": {r.get("condition"):
                              (r.get("summary") or {}).get("valid")
                              for r in runs},
            "tool_calls": {r.get("condition"):
                           (r.get("backend") or {}).get("tool_calls_used")
                           for r in runs},
        })
        ledger["pairs"].append(record)
        total_attempts += attempts
        total_tokens += tokens
        total_cost = round(total_cost + cost, 6)
        aborted_pairs += 1 if aborted else 0
        _write_atomic(ledger_path, ledger)
        print(f"[pair {n}] {record['status']} elapsed={elapsed}s "
              f"attempts={attempts} tokens={tokens} cost=${cost:.6f} "
              f"design={design_ok} ({design_msg})", flush=True)
        if not design_ok:
            stop_reason = f"design check failed on pair {n}: {design_msg}"
        elif totals.get("stop_reason"):
            stop_reason = f"pair {n}: {totals.get('stop_reason')}"
        elif total_attempts > GLOBAL_CAPS["max_attempts"]:
            stop_reason = (f"global attempt ceiling: {total_attempts} > "
                           f"{GLOBAL_CAPS['max_attempts']}")
        elif total_tokens > GLOBAL_CAPS["max_total_tokens"]:
            stop_reason = (f"global token ceiling: {total_tokens} > "
                           f"{GLOBAL_CAPS['max_total_tokens']}")
        elif total_cost > GLOBAL_CAPS["max_est_cost_usd"]:
            stop_reason = (f"global estimated-cost ceiling: ${total_cost} > "
                           f"${GLOBAL_CAPS['max_est_cost_usd']}")
        elif aborted_pairs >= GLOBAL_CAPS["max_aborted_pairs"]:
            stop_reason = f"{aborted_pairs} aborted pairs"

    ledger["finished_utc"] = _now()
    ledger["status"] = "completed" if stop_reason is None else "stopped"
    ledger["stop_reason"] = stop_reason
    ledger["totals"] = {
        "pairs_completed": len([p for p in ledger["pairs"]
                                if p.get("status") == "completed"]),
        "provider_http_attempts": total_attempts,
        "input_plus_output_tokens": total_tokens,
        "estimated_cost_usd": total_cost,
        "aborted_pairs": aborted_pairs,
    }
    _write_atomic(ledger_path, ledger)
    print(json.dumps({"ledger": str(ledger_path),
                      "status": ledger["status"],
                      "stop_reason": stop_reason,
                      "totals": ledger["totals"]}, indent=2), flush=True)
    return 0 if ledger["status"] == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
