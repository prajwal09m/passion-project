#!/usr/bin/env python3
"""Durable watcher: poll loop_state until the campaign stops or 31st slot resolves.

Appends one line per state change to watch_campaign_4.log and exits when
status != RUNNING or executions_done reaches the frozen ceiling.
"""
import json, pathlib, time, sys

root = pathlib.Path(".")
state_p = root / "autonomous_agent/state/loop_state.json"
log_p = root / "stat_validation_h10/freeze_2026_10_15/watch_campaign_4.log"
last = None
for i in range(2880):  # up to ~24h at 30s
    try:
        s = json.loads(state_p.read_text(encoding="utf-8"))
        key = (s.get("status"), s.get("cycle"), s.get("executions_done"),
               s.get("last_error"))
        if key != last:
            last = key
            with log_p.open("a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} status={s.get('status')} "
                        f"cycle={s.get('cycle')} done={s.get('executions_done')} "
                        f"executing={bool(s.get('executing'))} err={s.get('last_error')}\n")
        if s.get("status") not in ("RUNNING", "EXECUTING", None) and s.get("status") != "RUNNING":
            if s.get("status") not in ("RUNNING",):
                break
        if (s.get("executions_done") or 0) >= 32:
            break
    except Exception as e:
        with log_p.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} poll-error {e}\n")
    time.sleep(30)
print("watcher done")
