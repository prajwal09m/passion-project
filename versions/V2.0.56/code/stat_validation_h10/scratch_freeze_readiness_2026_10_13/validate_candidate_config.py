#!/usr/bin/env python3
"""SCRATCH — validate the C4 candidate config against the readiness checker.

Runs the authoritative machine checks (check_c4_config + stop-correspondence
map from test_freeze_integrity) against the CANDIDATE file, without touching
state/. Expectation: every c4.* check that will run at freeze passes now;
c4.not_frozen stays BLOCKED because the candidate is not in state/ (correct).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from autonomous_agent import launch_readiness_check as lrc  # noqa: E402
from autonomous_agent.test_freeze_integrity import (  # noqa: E402
    REPO, STOP_ENFORCEMENT, C3_STOPS)

candidate = json.loads((REPO / "autonomous_agent/MAIN AUDITS AND REFLECTIONS/"
                        "CAMPAIGN_4_CONFIG_CANDIDATE_2026_10_13.json")
                       .read_text("utf-8"))

rep = lrc.Report()
lrc.check_c4_config(REPO, candidate, rep)
for status, code, msg in rep.rows:
    print(f"[{status:7}] {code}: {msg}")

# Stop-correspondence: every declared stop must map to enforcement markers.
declared = list(candidate["stop_conditions"])
missing_map = [s for s in declared if s not in STOP_ENFORCEMENT]
print("stop_count:", len(declared))
print("missing_from_enforcement_map:", missing_map)
assert not missing_map, missing_map
assert len(declared) == 16, len(declared)
assert set(C3_STOPS) <= set(declared), "C3 stops not carried verbatim"

counts = rep.counts()
print("counts:", counts)
assert counts.get("FAIL") in (None, 0), "candidate failed a c4.* machine check"
print("OK: candidate passes every c4.* machine check; not_frozen remains "
      "correctly BLOCKED until gate 6 + copy-to-state")
