"""Launch the Campaign 5 bounded research loop (authorized 2026-10-22/23).

Wires the four C5 preflight environment variables from ``.env`` into
``os.environ`` (the shipped preflight reads them from ``os.environ`` and the
codebase has no dotenv loader), then runs
``autonomous_agent.continuous_loop.main`` with an explicit positive
``--max-cycles`` (the loop has no implicit-infinite mode).

Fail-closed rules:
* refuses to launch if any of the four variables is missing or (for the HMAC
  keys) not valid hex of >= 32 bytes,
* refuses to launch if the two actor IDs are equal,
* refuses to launch if one of the retired leaked key values is present,
* never prints any variable value.

Usage:  py -3 stat_validation_h10/freeze_2026_10_22/launch_campaign5.py \
            [--max-cycles N] [--idle-seconds S]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ENV_PATH = WORKSPACE / ".env"

REQUIRED = ("C5_OWNER_HMAC_KEY", "C5_REVIEWER_HMAC_KEY",
            "C5_OWNER_ACTOR_ID", "C5_REVIEWER_ACTOR_ID")

LEAKED_RETIRED_KEYS = {
    "f918a6fe6351e5cf1bfa60b2cad4f790a853e6ec162208b5679a04b8e0ea2c7c",
    "1554e311965ff09d31960815522c8a4eb969d13e5b188981c394994c66ef766e",
}


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        env[name.strip()] = value.strip()
    missing = [name for name in REQUIRED if not env.get(name)]
    if missing:
        raise SystemExit(f"refusing to launch: missing .env variables: {missing}")
    for name in ("C5_OWNER_HMAC_KEY", "C5_REVIEWER_HMAC_KEY"):
        value = env[name]
        if value.lower() in LEAKED_RETIRED_KEYS:
            raise SystemExit(f"refusing to launch: {name} is a retired leaked key value")
        try:
            decoded = bytes.fromhex(value)
        except ValueError as error:
            raise SystemExit(f"refusing to launch: {name} not valid hex: {error}")
        if len(decoded) < 32:
            raise SystemExit(f"refusing to launch: {name} must be >= 32 bytes")
    if env["C5_OWNER_ACTOR_ID"] == env["C5_REVIEWER_ACTOR_ID"]:
        raise SystemExit("refusing to launch: owner and reviewer actor IDs must be distinct")
    return env


def main() -> int:
    parser = argparse.ArgumentParser(prog="launch_campaign5")
    parser.add_argument("--max-cycles", type=int, required=True,
                        help="explicit positive cycle bound (no implicit-infinite mode)")
    parser.add_argument("--idle-seconds", type=float, default=0.0)
    args = parser.parse_args()
    if args.max_cycles <= 0:
        parser.error("--max-cycles must be a positive integer")

    env = _load_env()
    for name in REQUIRED:
        os.environ[name] = env[name]     # values stay out of stdout/stderr

    sys.path.insert(0, str(WORKSPACE))
    from autonomous_agent.continuous_loop import main as loop_main
    argv = ["--root", str(WORKSPACE), "--max-cycles", str(args.max_cycles)]
    if args.idle_seconds:
        argv += ["--idle-seconds", str(args.idle_seconds)]
    return loop_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
