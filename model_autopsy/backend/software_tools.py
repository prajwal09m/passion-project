"""Software diagnostics tools — real diff inspection and bounded test runs.

Every path argument is resolved inside the configured workspace roots;
executed test commands are fixed, not model-authored. Code changes are
NEVER applied to the operational program here — approved only via
check_apply_approval, which always requires an explicit human flag.

Git-subprocess safety: model/operator-supplied revision strings are
validated against a deliberately restrictive grammar BEFORE any subprocess
runs. Anything that could be parsed as a git option (leading '-', option
syntax, whitespace, quoting tricks) is rejected outright, and revision
arguments are only ever passed as bare positional values after an explicit
`--` path terminator. Git inspection stays strictly read-only.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

from . import config

TEST_COMMANDS_DEFAULT = ('py -3 -m pytest', 'python -m pytest', 'pytest', 'npm test')

# Restrictive git-revision grammar: a bare abbreviated/full SHA, `HEAD`,
# or `HEAD~N` (N<=999), optionally as a two-dot range "rev..rev". No
# symbolic refs, no glob/brace expansion, no traversal, no option chars.
_GIT_REV = r"(?:[0-9a-fA-F]{6,64}|HEAD(?:~[0-9]{1,3})?)"
_GIT_RANGE_RE = re.compile(rf"^{_GIT_REV}(?:\.\.\.?{_GIT_REV})?$")


def _valid_git_revision(rev: str) -> bool:
    """True only for values matching the restrictive grammar above."""
    return bool(rev) and bool(_GIT_RANGE_RE.match(rev))


def _validate_git_revision(rev: str | None, *, arg: str = "commit_range") -> None:
    if rev is None:
        return
    if not isinstance(rev, str):
        raise TypeError(f"{arg} must be a string")
    rev = rev.strip()
    if rev == "":
        raise ValueError(f"{arg} must not be blank")
    if not _GIT_RANGE_RE.match(rev):
        raise ValueError(
            f"{arg} rejected: {rev[:60]!r} does not match the allowed git "
            "revision grammar (bcrypt-free: a 6-64 hex SHA, HEAD, HEAD~N, "
            "or a rev..rev / rev...rev pair of those). Options, symbolic "
            "refs and whitespace-bearing values are never allowed.")


def _resolve_root(root: str | None) -> Path:
    p = config.resolve_restricted(root or ".")
    if not p.is_dir():
        raise FileNotFoundError(f"workspace {p} is not a directory")
    return p


def _git(args: list[str], cwd: Path, timeout: float = 30.0):
    """Run a read-only git command with fixed subcommand + pre-validated args.

    The caller constructs `args`; this helper never interpolates strings and
    always passes arguments positionally (no shell, no string concatenation).
    """
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                         text=True, timeout=timeout)
    return out.returncode, out.stdout, out.stderr


def git_status_and_diff(root: str | None = None, max_diff_chars: int = 4000,
                        commit_range: str | None = None) -> dict:
    """Git status plus (staged+unstaged, or commit_range) diff, truncated."""
    _validate_git_revision(commit_range)
    cwd = _resolve_root(root)
    rc, status, err = _git(["status", "--porcelain", "-b"], cwd)
    if rc != 0:
        return {"ok": False, "error": err.strip() or "git status failed"}
    rc2, diff_full, err2 = _git(["diff", "HEAD", "--stat", "--"], cwd)
    diff_bytes = diff_full
    if commit_range:
        # Revision values are grammar-validated above, then passed as bare
        # positional args followed by `--` so they can never be reparsed as
        # options or paths.
        rc2, diff_full, err2 = _git(["diff", commit_range, "--stat", "--"], cwd)
    if rc2 != 0:
        return {"ok": False, "error": err2.strip() or "git diff failed"}
    rc3, diff_body, _ = _git(["diff", commit_range or "HEAD", "--"], cwd)
    truncated = len(diff_body) > int(max_diff_chars)
    body = diff_body[: int(max_diff_chars)]
    return {"ok": True, "workspace": str(cwd), "status": status.strip(),
            "diff_stat": diff_bytes.strip(),
            "diff_head_truncated": truncated,
            "diff_head": body}


def list_changed_files(root: str | None = None,
                       commit_range: str | None = None) -> dict:
    _validate_git_revision(commit_range)
    cwd = _resolve_root(root)
    rc, out, err = _git(["diff", "--name-only", commit_range or "HEAD", "--"], cwd)
    if rc != 0:
        return {"ok": False, "error": err.strip() or "git diff --name-only failed"}
    files = [l for l in out.splitlines() if l.strip()]
    return {"ok": True, "changed_files": files, "count": len(files)}


def read_changed_file_head(root: str | None = None, file_path: str = "",
                           lines: int = 120) -> dict:
    cwd = _resolve_root(root)
    rel = Path(file_path)
    resolved = config.resolve_restricted(str((cwd / rel) if not rel.is_absolute() else rel))
    if not resolved.exists():
        raise FileNotFoundError(f"{resolved} does not exist")
    lines = max(10, min(int(lines), 400))
    return {"ok": True, "file": file_path, "head": resolved.read_text(
        encoding="utf-8", errors="replace").splitlines()[:lines]}


def _pick_runner(cwd: Path, command: str | None) -> list[str]:
    if command:
        return command.split()      # only from the operator, never from Meta
    py = "py"
    for cmd in (["py", "-3", "-m", "pytest"], ["python", "-m", "pytest"], ["pytest"]):
        rc = subprocess.run([cmd[0], "--version"], capture_output=True).returncode
        if rc == 0:
            py = cmd[0]
            break
    return [py] + ([ "-3", "-m", "pytest"] if py == "py" else ["-m", "pytest"])


def run_tests(root: str | None = None, test_path: str | None = None,
              timeout_seconds: float | None = None) -> dict:
    """Run the pytest command against a real directory; parse the exit code
    and the pytest summary line.

    Meta may never supply the command itself, only choose scope from
    (root, test_path). Timeouts are bounded by the absolute cap.
    """
    cwd = _resolve_root(root)
    timeout = min(float(timeout_seconds or config.DEFAULT_TOOL_TIMEOUT_SECONDS),
                  config.ABSOLUTE_TOOL_TIMEOUT_SECONDS)
    argv = _pick_runner(cwd, None)
    if test_path:
        target = _resolve_root(test_path)
        argv += ["-q", str(target)]
    else:
        argv += ["-q"]
    started = time.time()
    try:
        out = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                             timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "test_timeout_exceeded",
                "timeout_seconds": timeout}
    text = out.stdout
    tail = "\n".join(text.splitlines()[-12:])
    summary_line = ""
    for line in text.splitlines():
        s = line.strip()
        if ("passed" in s or "failed" in s or "error" in s) and s.endswith("=") is False and ("=" in s or "," in s):
            summary_line = s
    return {"ok": True, "command": argv, "exit_code": out.returncode,
            "seconds": round(time.time() - started, 2),
            "summary_line": summary_line,
            "tail": tail, "passed": out.returncode == 0}


def compare_test_results(before: dict, after: dict) -> dict:
    if not (isinstance(before, dict) and isinstance(after, dict)):
        raise ValueError("compare_test_results expects two test-result payloads")
    return {"ok": True, "before_exit": before.get("exit_code"),
            "after_exit": after.get("exit_code"),
            "regression": bool(before.get("passed")) and not bool(after.get("passed"))}


def check_apply_approval(requested_by_meta: bool = False,
                         owner_approved: bool = False) -> dict:
    """Applying code changes to the operational stock program requires an
    explicit human approval flag; Meta alone can never grant it."""
    return {"ok": True,
            "apply_allowed": bool(owner_approved and not bool(requested_by_meta)),
            "reason": "owner_and_meta_agreement_required" if not owner_approved
                      else ("owner_approval_only" if requested_by_meta else "ready")}
