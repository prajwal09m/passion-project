"""Campaign 5 cutover watcher (recorded handoff, 2026-10-23).

Background: the launch-time bounded run started before the two C5-declared
signal stops were wired (``regime_predefinition_violation`` /
``data_snooping_detected``). Enforcement is now implemented
(``autonomous_agent/proposal_layer/stops_c5.py`` + loop wiring + tests), but a
Python process only sees new code when it starts. This watcher performs the
cutover WITHOUT wasting the in-flight execution slot:

1. wait until ``loop_state.executing`` is null (cycle boundary; the running
   experiment is never interrupted),
2. create the explicit STOP file so the old process stops cleanly (its next
   cycle top raises STOP_FILE; journaled as an explicit stop),
3. wait for the old process to exit (durable ``STOPPED``/STOP_FILE, no
   executing slot, loop lock released),
4. remove the STOP file,
5. relaunch ``launch_campaign5.py`` (new code, same config pin) detached,
   output to a fresh log,
6. verify the fresh startup: state RUNNING on the campaign-5 pin, preflight
   audit APPROVED for this campaign, journal ``loop_started`` with the NEW pid.

Every step is echoed to stdout; exit 0 only if step 6 verifies.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
STATE = WORKSPACE / "autonomous_agent" / "state"
STATE_FILE = STATE / "loop_state.json"
STOP_FILE = STATE / "STOP"
LOCK_FILE = STATE / "loop.lock"
LAUNCHER = WORKSPACE / "stat_validation_h10" / "freeze_2026_10_22" / "launch_campaign5.py"
NEW_LOG = STATE / "campaign5_wired_relaunch_2026_10_23.log"
PID = int(sys.argv[1]) if len(sys.argv) > 1 else None


STOP_REQUEST_TEXT = (b"requested by restart_into_wired_c5 cutover "
                     b"2026-10-23\n")


def state() -> dict:
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def alive(pid: int | None) -> bool:
    if pid is None:
        return False
    probe = subprocess.run(["python", "-c", "import os,sys;"
                           f"os.kill({pid},0)"],
                           capture_output=True)
    if probe.returncode == 0:
        return True
    # Windows: emulate tasklist-based existence check
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                         capture_output=True, text=True)
    return f" {pid} " in out.stdout.replace("\n", " ") or out.stdout.strip().endswith(str(pid))


def log(message: str) -> None:
    print(message, flush=True)


def main() -> int:
    log(f"watcher start; old pid={PID}")
    base_cycle = state()["cycle"]

    # 1. cycle boundary
    waited = 0
    while True:
        st = state()
        if not st.get("executing"):
            log(f"boundary reached (cycle {st['cycle']}, exec_done "
                f"{st['executions_done']})")
            break
        if waited and waited % 600 == 0:
            log(f"still executing {st['executing']['experiment_id']} "
                f"({waited}s waited)")
        time.sleep(10)
        waited += 10

    # 2. explicit STOP file
    STOP_FILE.write_bytes(STOP_REQUEST_TEXT)
    log("STOP file written")
    while state().get("executing"):     # retry until the boundary tripwire sticks
        old_cycle = state()["cycle"]
        time.sleep(5)
        if old_cycle != base_cycle and state().get("executing"):
            STOP_FILE.write_bytes(STOP_REQUEST_TEXT)

    # 3. wait for the old process's clean stop (bounded: 15 min)
    deadline = time.monotonic() + 15 * 60
    while time.monotonic() < deadline:
        st = state()
        old_exited = PID is None or not alive(PID)
        if (not st.get("executing")
                and st.get("status") == "STOPPED"
                and st.get("last_stop_reason") == "STOP_FILE"
                and old_exited):
            log("old process stopped cleanly on STOP_FILE (pid gone, lock "
                "released)")
            break
        if st.get("status") == "RUNNING" and st.get("executing"):
            # raced into the next cycle: keep the STOP file present; it stops
            # it at the next boundary and we re-wait
            STOP_FILE.write_bytes(STOP_REQUEST_TEXT)
        time.sleep(5)
    else:
        log("ABORT: old process did not stop within 15 minutes; STOP file "
            "left in place")
        return 3

    # 4. clear the STOP file
    STOP_FILE.unlink(missing_ok=True)
    log("STOP file removed")

    # 5. relaunch under the wired code (detached; the launcher never echoes
    #    trust values)
    log("relaunching with the wired code (max-cycles 120)")
    subprocess.Popen(
        ["py", "-3", str(LAUNCHER), "--max-cycles", "120"],
        cwd=str(WORKSPACE),
        stdout=open(NEW_LOG, "ab"), stderr=subprocess.STDOUT,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True)

    # 6. verify startup
    deadline = time.monotonic() + 10 * 60
    while time.monotonic() < deadline:
        try:
            st = state()
        except (OSError, json.JSONDecodeError):
            time.sleep(5)
            continue
        if st.get("status") == "RUNNING" and st.get("campaign_id", "").startswith("campaign-5"):
            journal_last = (STATE / "loop_events.jsonl").read_text(
                encoding="utf-8").strip().splitlines()[-1]
            event = json.loads(journal_last)
            audit_last = (STATE / "campaign5_preflight_audit.jsonl").read_text(
                encoding="utf-8").strip().splitlines()[-1]
            audit = json.loads(audit_last)
            ok = (event.get("event") == "loop_started"
                  and st.get("campaign_config_sha256")
                  == "29c905aaf25012cdd20bf21270821f81f5a8e24b46b4a51163d2c65e2e9124a5"
                  and int(event.get("pid", -1)) != PID
                  and audit.get("allowed") is True
                  and audit.get("campaign_id", "").startswith("campaign-5"))
            log(f"new state: pin={st.get('campaign_config_sha256')[:12]} "
                f"cycle={st['cycle']} exec_done={st['executions_done']} "
                f"preflight={audit.get('status')} "
                f"newpid={event.get('pid')}")
            log(f"cutover {'OK' if ok else 'VERIFICATION_FAILED'}")
            return 0 if ok else 4
        time.sleep(5)
    log("ABORT: relaunched loop did not reach RUNNING within 10 minutes")
    return 5


if __name__ == "__main__":
    raise SystemExit(main())
