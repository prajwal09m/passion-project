"""Regression tests for the git option-injection fix.

Malicious values must be rejected BEFORE any git subprocess can run; valid
grammar values are passed positionally with `--` terminators only.
"""
from __future__ import annotations

import subprocess

import pytest

from model_autopsy.backend import software_tools as sw
from model_autopsy.backend.tools_registry import validate_arguments


MALICIOUS = [
    "--upload-pack=touch evil",
    "--exec=run_me",
    "-o", "-O ~/.bashrc", "-q",
    "--", "--ext-diff",
    "HEAD; rm -rf /", "HEAD && evil", "HEAD | evil",
    "master..HEAD --output=x",            # symbolic ref (not in grammar)
    "origin/main",                        # symbolic remote ref
    "HEAD~/../HEAD",                      # traversal-ish
    "HEAD extra",                         # whitespace injection
    "0" * 200,                            # oversized
    "\x1b[32mHEAD",
]


@pytest.mark.parametrize("value", MALICIOUS)
def test_malicious_revision_never_reaches_subprocess(value, monkeypatch):
    def _explode(*a, **k):  # any subprocess attempt fails the test loudly
        raise AssertionError(f"subprocess called with {a} {k}")

    monkeypatch.setattr(subprocess, "run", _explode)
    with pytest.raises((ValueError, TypeError)):
        sw.git_status_and_diff(root=".", commit_range=value)
    with pytest.raises((ValueError, TypeError)):
        sw.list_changed_files(root=".", commit_range=value)


VALID = ["HEAD", "HEAD~5", "a1b2c3d", "0123456789abcdef",
         "HEAD~10..HEAD", "a1b2c3d..e4f5a6b", "HEAD...HEAD~3"]


@pytest.mark.parametrize("value", VALID)
def test_valid_grammar_constructs_safe_git_invocation(value):
    """Grammar-valid values are passed as bare positional args with a `--`
    path terminator and can never mutate the command (stubbed git)."""
    seen = []

    def fake_git(args, cwd, timeout=30.0):
        seen.append(list(args))
        return 0, " mock diff ", ""

    import model_autopsy.backend.software_tools as _sw
    real_git = _sw._git
    _sw._git = fake_git
    try:
        out = sw.git_status_and_diff(root=".", commit_range=value,
                                     max_diff_chars=300)
        assert out["ok"] is True and out["diff_stat"].strip()
        sw.list_changed_files(root=".", commit_range=value)
    finally:
        _sw._git = real_git
    # every git invocation: defined subcommand first, revision positional,
    # explicit `--` terminator; the revision never rides inside a flag.
    diff_calls = [c for c in seen if c[0] == "diff"]
    assert diff_calls, "git diff must have been invoked"
    for args in diff_calls:
        assert args[-1] == "--"
        for arg in args[1:-1]:          # no flag-position revision values
            if arg == value:
                assert not value.startswith("-")


def test_real_repo_accepts_head_range_smoke():
    """Cheap real-repo check against HEAD (deep history is left unstrobed)."""
    out = sw.list_changed_files(root=".", commit_range="HEAD")
    assert out["ok"] is True


def test_schema_contract_matches_git_grammar():
    # validation layer agrees with the tool layer
    for value in ["--exec=x", "HEAD&&evil", "origin/master"]:
        with pytest.raises(ValueError):
            validate_arguments("git_status_and_diff", {"commit_range": value})
    for value in VALID:
        assert validate_arguments("git_status_and_diff",
                                  {"commit_range": value})["commit_range"] == value


def test_paths_cannot_escape_workspace():
    with pytest.raises(PermissionError):
        sw.read_changed_file_head(root=".", file_path="..\\..\\project.env")
    with pytest.raises(PermissionError):
        sw.read_changed_file_head(root=".", file_path="C:\\Windows\\win.ini")


def test_run_tests_timeout_bounded():
    from model_autopsy.backend import config
    with pytest.raises(ValueError):
        validate_arguments("run_tests", {"timeout_seconds": 100000})
    assert config.ABSOLUTE_TOOL_TIMEOUT_SECONDS == 300.0
