"""Hardening for long-running autonomous execution (MAIN TASK 5).

Windows-aware utilities used by the experiment adapter and the supervisor:

* process-tree launch/termination (whole tree killed on timeout or kill switch),
* configurable resource limits (runtime, output, workspace, GPU, concurrency),
* network denial for experiment subprocesses by default (sitecustomize shim),
* credential-variable scrubbing for experiment subprocesses,
* duplicate-experiment prevention via a spec-hash registry,
* a global kill switch helper that terminates the active subprocess tree.

Nothing here changes the scientific methodology; these are safety rails only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

IS_WINDOWS = os.name == "nt"

DEFAULT_LIMITS: dict[str, Any] = {
    "timeout_seconds": 3600.0,
    "max_output_bytes": 2_000_000,
    "max_workspace_files": 250_000,
    "max_workspace_bytes": 3_000_000_000,
    "max_memory_bytes": 8_000_000_000,
    "cpu_affinity": None,          # None = all cores; list[int] pins the tree
    "gpu_enabled": False,
    "max_concurrent_experiments": 1,
    "allow_network": False,
}

CREDENTIAL_ENV_TOKENS = ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "API_KEY",
                         "APIKEY", "ACCESS_KEY", "PRIVATE_KEY", "CREDENTIAL",
                         "BROKER", "SESSION_KEY", "AUTH")

DENY_NETWORK_SITECUSTOMIZE = '''\
"""Auto-loaded sandbox shim: experiments have no network access by default.

Installed into the isolated experiment workspace by the autonomous agent.
Set AUTONOMOUS_ALLOW_NETWORK=1 only for explicitly reviewed commands.
"""
import os
import socket

if os.environ.get("AUTONOMOUS_ALLOW_NETWORK", "0") != "1":
    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex
    _real_create = socket.create_connection

    def _deny(*args, **kwargs):
        raise PermissionError(
            "Network access is disabled for autonomous experiments "
            "(autonomous_agent.hardening). This command must not reach "
            "brokerage, credential, or external services.")

    socket.socket.connect = _deny
    socket.socket.connect_ex = _deny
    socket.create_connection = _deny
    socket.getaddrinfo = _deny
'''


def spec_fingerprint(spec: Mapping[str, Any]) -> str:
    """Hash the scientific identity of a spec (duplicate prevention).

    Volatile identity fields (experiment_id, and generation provenance such as
    timestamps) are excluded so that re-running the exact same
    hypothesis/change/criteria under a new id or a new generation timestamp is
    still detected as a duplicate. Provenance is metadata only; it never
    changes what a spec does, so it must not change its scientific identity.
    """
    payload = {key: value for key, value in spec.items()
               if key not in ("experiment_id", "provenance")}
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class SpecRegistry:
    """Append-only registry of attempted experiment spec fingerprints."""

    def __init__(self, state_root: Path):
        self.state_root = Path(state_root)
        self.path = self.state_root / "experiment_registry.json"

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"schema_version": 1, "attempts": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "attempts": []}

    def check(self, spec: Mapping[str, Any]) -> tuple[bool, str]:
        """Return (allowed, reason). Duplicates are refused unless explicitly intended."""
        fingerprint = spec_fingerprint(spec)
        attempts = self._load().get("attempts", [])
        previous = [item for item in attempts if item.get("spec_sha256") == fingerprint]
        if previous and not bool(spec.get("allow_repeat")):
            last = previous[-1]
            return False, (f"Duplicate experiment specification (spec_sha256={fingerprint[:16]}, "
                           f"first attempted {last.get('at')} as {last.get('experiment_id')}). "
                           "Set allow_repeat only when a deliberate re-run is intended.")
        return True, f"spec_sha256={fingerprint}"

    def record(self, spec: Mapping[str, Any], experiment_id: str, at: str) -> str:
        fingerprint = spec_fingerprint(spec)
        data = self._load()
        data.setdefault("attempts", []).append({
            "spec_sha256": fingerprint, "experiment_id": experiment_id, "at": at,
        })
        self.state_root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        return fingerprint


def scrubbed_environment(base: Mapping[str, str], *, seed: int, experiment_id: str,
                         allow_network: bool = False, gpu_enabled: bool = False) -> dict[str, str]:
    """Environment for experiment subprocesses: no credentials, no GPU, no network."""
    env = {key: value for key, value in base.items()
           if not any(token in key.upper() for token in CREDENTIAL_ENV_TOKENS)}
    env["PYTHONHASHSEED"] = str(seed)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["AUTONOMOUS_EXPERIMENT_ID"] = experiment_id
    env["AUTONOMOUS_ALLOW_NETWORK"] = "1" if allow_network else "0"
    if not gpu_enabled:
        env["CUDA_VISIBLE_DEVICES"] = ""
        env["NVIDIA_VISIBLE_DEVICES"] = "none"
    return env


def install_network_guard(workspace: Path) -> Path:
    """Install the sitecustomize network-denial shim into the isolated workspace."""
    sandbox = Path(workspace) / "_agent_sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    (sandbox / "sitecustomize.py").write_text(DENY_NETWORK_SITECUSTOMIZE, encoding="utf-8")
    return sandbox


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if IS_WINDOWS:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def terminate_process_tree(pid: int) -> bool:
    """Terminate a process and all of its descendants. Returns success."""
    if pid <= 0:
        return False
    if IS_WINDOWS:
        completed = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, text=True, timeout=30,
        )
        if completed.returncode == 0:
            return True
        # Fall back to a direct kill if taskkill cannot resolve the tree.
        subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                       capture_output=True, text=True, timeout=30)
        return not process_alive(pid)
    subprocess.run(["pkill", "-TERM", "-P", str(pid)], capture_output=True, timeout=30)
    try:
        os.kill(pid, 15)
    except OSError:
        pass
    time.sleep(0.2)
    return not process_alive(pid)


def active_child_path(state_root: Path) -> Path:
    return Path(state_root) / "active_child.json"


def record_active_child(state_root: Path, pid: int, experiment_id: str, role: str) -> None:
    path = active_child_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"pid": pid, "experiment_id": experiment_id,
                               "role": role, "at": time.time()}), encoding="utf-8")
    os.replace(tmp, path)


def clear_active_child(state_root: Path) -> None:
    try:
        active_child_path(state_root).unlink()
    except OSError:
        pass


def kill_active_subprocess_tree(state_root: Path) -> dict[str, Any]:
    """Global kill switch helper: terminate the currently running experiment tree."""
    path = active_child_path(state_root)
    if not path.is_file():
        return {"killed": False, "reason": "no active experiment subprocess"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"killed": False, "reason": "active-child record unreadable"}
    pid = int(data.get("pid") or 0)
    ok = terminate_process_tree(pid)
    clear_active_child(state_root)
    return {"killed": ok, "pid": pid, "experiment_id": data.get("experiment_id"),
            "role": data.get("role")}


def run_with_limits(argv: list[str], *, cwd: Path, env: Mapping[str, str],
                    timeout: float, limits: Mapping[str, Any],
                    state_root: Path | None = None,
                    experiment_id: str = "", role: str = "") -> dict[str, Any]:
    """Run a command with tree-managed process control and resource limits.

    Returns {"returncode", "stdout", "stderr", "timed_out", "duration_seconds"}.
    On timeout (or kill switch) the entire process tree is terminated.
    """
    timeout = min(float(timeout), float(limits.get("timeout_seconds", 3600.0)))
    creationflags = 0
    if IS_WINDOWS:
        creationflags |= 0x00000200  # CREATE_NEW_PROCESS_GROUP
        creationflags |= 0x08000000  # CREATE_NO_WINDOW
    started = time.monotonic()
    process = subprocess.Popen(
        [str(part) for part in argv], cwd=str(cwd), env=dict(env),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=creationflags if IS_WINDOWS else 0,
        start_new_session=not IS_WINDOWS,
    )
    if state_root is not None:
        record_active_child(state_root, process.pid, experiment_id, role)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        terminate_process_tree(process.pid)
        try:
            stdout, stderr = process.communicate(timeout=10)
        except Exception:  # noqa: BLE001 - fail safe
            stdout, stderr = "", ""
    finally:
        if state_root is not None:
            clear_active_child(state_root)
    return {
        "returncode": process.returncode,
        "stdout": stdout or "",
        "stderr": stderr or "",
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
    }
