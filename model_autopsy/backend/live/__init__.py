"""Live Meta investigation framework (Milestone 5).

Meta AI (Muse Spark) is the investigator; Model Autopsy is the research
environment; the M4 scorer is the judge. All live traffic goes through
the existing `meta_api` client/loop (bearer key from env, bounded
retries, usage rollups). A hard budget governor caps every paid
dimension BEFORE requests are sent. Offline development and all tests
use mocked provider responses — the single live pilot is CLI-launched
only, never UI-triggered, never retried automatically.
"""
from __future__ import annotations

LIVE_VERSION = "m5-v1"
