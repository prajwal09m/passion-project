"""Offline checks for the pre-registered Phase D blind scoring package.

No network, no credentials, no benchmark execution. These tests verify the
frozen contract (six dimensions, 0/1/2, max 12), the four neutral sheets, the
separation of the sealed condition mapping, and that historical raw traces were
not modified. Dummy data only; no provider request is made.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from model_autopsy.benchmarks import blind_scoring as bs

BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUBRIC = BENCH / "phase_d_blind_scoring_rubric_v1.md"
PROTOCOL = BENCH / "phase_d_blind_evaluation_protocol_v1.md"
SHEETS_DIR = BENCH / "phase_d_blind_scoring_sheets"
KEY = BENCH / ".sealed" / "phase_d_blind_condition_key_v1.json"
MANIFEST = BENCH / "phase_d_blind_freeze_manifest_v1.json"
SHEET_NAMES = [f"run-{i:02d}.md" for i in range(1, 5)]
CONDITION_TERMS = re.compile(
    r"\b(full|delta|baseline|candidate|phase[ -]c)\b|p[12]-(?:full|delta)",
    re.IGNORECASE)


def _artifact_texts() -> dict[str, str]:
    texts = {RUBRIC.name: RUBRIC.read_text(encoding="utf-8"),
             PROTOCOL.name: PROTOCOL.read_text(encoding="utf-8")}
    for name in SHEET_NAMES:
        texts[name] = (SHEETS_DIR / name).read_text(encoding="utf-8")
    return texts


def test_machine_contract_is_six_dimensions_of_0_1_2_max_12() -> None:
    assert bs.RUBRIC_VERSION == "v1"
    assert len(bs.DIMENSIONS) == 6
    assert len({key for key, _ in bs.DIMENSIONS}) == 6
    assert bs.ALLOWED_SCORES == (0, 1, 2)
    assert bs.MAX_TOTAL == 12


def test_validate_scores_accepts_only_0_1_2() -> None:
    zeros = {key: 0 for key, _ in bs.DIMENSIONS}
    twos = {key: 2 for key, _ in bs.DIMENSIONS}
    assert bs.total_score(zeros) == 0
    assert bs.total_score(twos) == bs.MAX_TOTAL == 12

    bad_values = [-1, 3, 1.5, True, "2", None]
    for value in bad_values:
        scores = dict(zeros)
        scores[bs.DIMENSIONS[0][0]] = value
        with pytest.raises(bs.ScoringError):
            bs.validate_scores(scores)

    missing = dict(zeros)
    missing.pop(bs.DIMENSIONS[0][0])
    with pytest.raises(bs.ScoringError):
        bs.validate_scores(missing)
    extra = dict(zeros, bonus=1)
    with pytest.raises(bs.ScoringError):
        bs.validate_scores(extra)


def test_rubric_matches_machine_contract_and_freezes_rules() -> None:
    text = re.sub(r"\s+", " ", RUBRIC.read_text(encoding="utf-8"))
    for _key, label in bs.DIMENSIONS:
        assert label in text
    assert "Maximum score: 12" in text
    assert "Scores are integers in `{0, 1, 2}`" in text
    assert "**both** experimental conditions" in text
    assert "Do not force a diagnostic-test requirement" in text
    assert "Never award quality points because a summary passes formatting" in text
    assert "No re-scoring after unblinding" in text
    assert "FROZEN" in text and "2026-10-29" in text


def test_four_neutral_sheets_are_complete_and_condition_free() -> None:
    found = sorted(p.name for p in SHEETS_DIR.glob("*.md"))
    assert found == SHEET_NAMES

    texts = []
    for index, name in enumerate(SHEET_NAMES, start=1):
        text = (SHEETS_DIR / name).read_text(encoding="utf-8")
        texts.append(text)
        assert f"RUN-{index:02d}" in text
        assert f"Presentation position: {index} of 4" in text
        assert text.count("**Score (0/1/2):**") == 6
        assert "____ / 12" in text
        for i, (_key, label) in enumerate(bs.DIMENSIONS, start=1):
            assert f"### D{i} — {label}" in text
        assert "First-attempt valid" in text
        assert "Post-repair valid" in text
        assert CONDITION_TERMS.search(text) is None, f"{name} leaks a condition term"
        assert "p1-full" not in text and "p1-delta" not in text
        assert "p2-full" not in text and "p2-delta" not in text

    # Same template for every run: identical line count and headings once the
    # neutral label itself is masked.
    assert len({len(t.splitlines()) for t in texts}) == 1
    headings = []
    for index, text in enumerate(texts, start=1):
        headings.append({
            line.replace(f"RUN-{index:02d}", "RUN-XX")
            for line in text.splitlines() if line.startswith("#")})
    assert all(h == headings[0] for h in headings)


def test_condition_mapping_is_separate_balanced_and_sealed() -> None:
    assert KEY.exists(), "sealed condition key missing"
    assert SHEETS_DIR not in KEY.parents
    assert KEY.parent.name == ".sealed"

    key = json.loads(KEY.read_text(encoding="utf-8"))
    mapping = key["mapping"]
    assert key["sealed"] is True
    assert set(mapping) == {f"RUN-{i:02d}" for i in range(1, 5)}
    assert sorted(v["presentation_position"] for v in mapping.values()) == [1, 2, 3, 4]

    pairs: dict[int, set[str]] = {}
    run_ids = set()
    for entry in mapping.values():
        pairs.setdefault(entry["pair"], set()).add(entry["condition"])
        assert entry["run_id"] == f"p{entry['pair']}-{entry['condition']}"
        run_ids.add(entry["run_id"])
    assert set(pairs) == {1, 2}
    assert all(conditions == {"full", "delta"} for conditions in pairs.values())
    assert len(run_ids) == 4

    for name in SHEET_NAMES:
        text = (SHEETS_DIR / name).read_text(encoding="utf-8")
        for run_id in run_ids:
            assert run_id not in text


def test_condition_key_digest_and_raw_traces_match_freeze_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    key_info = manifest["condition_key"]
    assert key_info["entries"] == 4
    digest = hashlib.sha256(KEY.read_bytes()).hexdigest()
    assert digest == key_info["sha256"]

    raw = manifest["raw_traces_sha256"]
    assert raw, "manifest must cover the raw traces present at freeze time"
    for name, expected in raw.items():
        path = BENCH / name
        assert path.is_file(), f"frozen raw trace missing: {name}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, (
            f"raw trace changed after freeze: {name}")
    assert not any(name.startswith("phase_d_blind_") for name in raw)


def test_scoring_package_matches_freeze_manifest() -> None:
    """The rubric, protocol, sheets, and machine contract are frozen by digest;
    a post-freeze edit to any scoring criterion fails this check."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    package = manifest["scoring_package_sha256"]
    expected = {
        RUBRIC.name, PROTOCOL.name, "blind_scoring.py",
        *(f"phase_d_blind_scoring_sheets/{name}" for name in SHEET_NAMES),
    }
    assert set(package) == expected
    for rel, digest in package.items():
        path = BENCH / rel
        assert path.is_file(), f"frozen scoring artifact missing: {rel}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            f"scoring artifact changed after freeze: {rel}")


def test_no_credentials_in_blind_scoring_artifacts() -> None:
    texts = _artifact_texts()
    texts[MANIFEST.name] = MANIFEST.read_text(encoding="utf-8")
    texts["blind_scoring.py"] = (
        BENCH / "blind_scoring.py").read_text(encoding="utf-8")
    forbidden = re.compile(
        r"Authorization:\s*\S+|Bearer\s+\S+|MODEL_API_KEY\s*=\s*\S+|"
        r"GROQ_API_KEY\s*=\s*\S+|sk-[A-Za-z0-9]{10,}")
    for name, text in texts.items():
        assert forbidden.search(text) is None, f"credential-like value in {name}"


def test_sealed_key_is_git_ignored() -> None:
    ignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "model_autopsy/benchmarks/.sealed/" in ignore
