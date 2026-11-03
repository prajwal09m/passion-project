"""Offline tests for the Meta benchmark's .env loading.

The real MODEL_API_KEY is never read, printed, or written here. Every test
uses a clearly fake placeholder and no network path is exercised.
"""
from __future__ import annotations

import os

import pytest

from model_autopsy.benchmarks import meta_paired_continuation_benchmark as bench

DUMMY = "offline-placeholder-not-a-real-key"
PROCESS_DUMMY = "process-placeholder-not-real"


def _write_env(monkeypatch: pytest.MonkeyPatch, tmp_path, text: str) -> None:
    bench_dir = tmp_path / "benchmarks"
    bench_dir.mkdir()
    (tmp_path / ".env").write_text(text, encoding="utf-8")
    monkeypatch.setattr(bench, "BENCH_DIR", bench_dir)
    monkeypatch.setenv("MODEL_AUTOPSY_DB_PATH", str(tmp_path / "sandbox.db"))


def test_env_file_supplies_dummy_key_when_process_is_missing(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    _write_env(monkeypatch, tmp_path, f"MODEL_API_KEY={DUMMY}\n")

    bench.bootstrap_env(key_required=False)

    assert os.environ["MODEL_API_KEY"] == DUMMY


def test_empty_process_key_does_not_shadow_env_file(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "")
    _write_env(monkeypatch, tmp_path, f"MODEL_API_KEY={DUMMY}\n")

    bench.bootstrap_env(key_required=False)

    assert os.environ["MODEL_API_KEY"] == DUMMY


def test_nonempty_process_key_wins_over_env_file(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_API_KEY", PROCESS_DUMMY)
    _write_env(monkeypatch, tmp_path, f"MODEL_API_KEY={DUMMY}\n")

    bench.bootstrap_env(key_required=False)

    assert os.environ["MODEL_API_KEY"] == PROCESS_DUMMY


@pytest.mark.parametrize("text", [
    f"\ufeffMODEL_API_KEY={DUMMY}\n",
    f"export MODEL_API_KEY={DUMMY}\n",
    f'MODEL_API_KEY="{DUMMY}"\n',
    f"MODEL_API_KEY='{DUMMY}'\n",
])
def test_loader_handles_bom_export_and_quotes(
        monkeypatch: pytest.MonkeyPatch, tmp_path, text: str) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    _write_env(monkeypatch, tmp_path, text)

    bench.bootstrap_env(key_required=False)

    assert os.environ["MODEL_API_KEY"] == DUMMY


def test_missing_assignment_stays_blocked(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    _write_env(monkeypatch, tmp_path, f"GROQ_API_KEY={DUMMY}\n")

    with pytest.raises(SystemExit) as excinfo:
        bench.bootstrap_env(key_required=True)

    assert "MODEL_API_KEY" in str(excinfo.value)
    assert not os.environ.get("MODEL_API_KEY", "").strip()


def test_empty_assignment_stays_blocked(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    _write_env(monkeypatch, tmp_path, "MODEL_API_KEY=\n")

    with pytest.raises(SystemExit) as excinfo:
        bench.bootstrap_env(key_required=True)

    assert "MODEL_API_KEY" in str(excinfo.value)
    assert not os.environ.get("MODEL_API_KEY", "").strip()


def test_offline_report_never_contains_the_dummy_key(
        monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MODEL_API_KEY", DUMMY)
    _write_env(monkeypatch, tmp_path, "")

    report = bench.run_offline()

    assert "offline" in report
    assert '"key_available": true' in report
    assert DUMMY not in report
