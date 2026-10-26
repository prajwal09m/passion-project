"""One-shot diagnostic for cycle 34's long execution: state + result + sleep history."""
import json
import pathlib
import subprocess
from datetime import datetime, timezone

now = datetime.now(timezone.utc).isoformat(timespec="seconds")
print("now:", now)

s = json.loads(pathlib.Path("autonomous_agent/state/loop_state.json").read_text("utf-8"))
print("loop:", s["status"], "| cycle", s["cycle"], "| done", s["executions_done"],
      "| heartbeat", s["heartbeat_at"], "| err", s.get("last_error"))

r = pathlib.Path("autonomous_agent/candidates/exp-proposal-dbcceddf3839/result.json")
print("result.json exists:", r.exists())
if r.exists():
    d = json.loads(r.read_text("utf-8"))
    rt = d.get("runtime") or {}
    print("status:", d.get("status"), "| rec:", d.get("acceptance_recommendation"),
          "| total_s:", rt.get("total_seconds"))

print("--- last adapter events ---")
p = pathlib.Path("autonomous_agent/state/adapter_events.jsonl")
for line in [l for l in p.read_text("utf-8").splitlines() if l.strip()][-4:]:
    print(line[:280])

print("--- power sleep/wake events (last 2 days) ---")
ps = (
    "Get-WinEvent -FilterHashtable @{LogName='System'; Id=42,107,1,41; "
    "StartTime=(Get-Date).AddDays(-2)} -ErrorAction SilentlyContinue | "
    "Select-Object TimeCreated,Id,ProviderName | Sort-Object TimeCreated | "
    "Format-Table -AutoSize"
)
out = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True)
print(out.stdout or out.stderr)
