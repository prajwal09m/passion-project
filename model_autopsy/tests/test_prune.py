"""Prune utility tests — detection correctness + hard confirmation gate.

The utility must never delete anything without MODEL_AUTOPSY_CONFIRM_PRUNE
being exactly "yes_test_prune", and must identify both tagged and legacy
test records without touching real investigations.
"""
from __future__ import annotations

import pytest

from model_autopsy.backend import engine, prune
from model_autopsy.backend.db import SessionLocal, init_db


@pytest.fixture()
def session():
    init_db()
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def test_records_created_by_tests_are_tagged(session, monkeypatch):
    inv = engine.create_investigation(session, "ml", "t", "q")
    assert "test" in (inv.config.get("tags") or [])


def test_detection_covers_tagged_and_legacy_without_touching_real(session):
    from model_autopsy.backend.db import Investigation
    tagged = engine.create_investigation(session, "ml", "t", "q")
    # A separate legacy record: pre-isolation runs had no tags.
    legacy = engine.create_investigation(session, "ml", "t2", "q2")
    leg_row = session.get(Investigation, legacy.id)
    leg_row.config = {}
    leg_row.title = "T4"
    session.commit()
    # A real record as it exists outside test runs: no tag, real title.
    real = engine.create_investigation(session, "ml",
                                       "Demand Zone honest audit",
                                       "Why does calibration drift?")
    real_row = session.get(Investigation, real.id)
    real_row.config = {}
    session.commit()

    found = prune.candidates(session)
    ids = [inv.id for inv, _ in found]
    assert tagged.id in ids and real.id not in ids
    reasons = {inv.id: r for inv, r in found}
    assert "legacy" in reasons[legacy.id]
    assert "tagged" in reasons[tagged.id]


def test_apply_refuses_without_explicit_confirmation(session, monkeypatch,
                                                     capsys):
    session  # noqa: ensure fixture ran
    monkeypatch.setattr(prune, "candidates", lambda s: [])
    monkeypatch.setattr(prune, "_confirm", lambda: "")
    code = prune.apply_prune()
    assert code == 1
    out = capsys.readouterr().out
    assert "Refusing" in out and "MODEL_AUTOPSY_CONFIRM_PRUNE" in out


def test_apply_with_confirmation_deletes_only_candidates(session, monkeypatch):
    from model_autopsy.backend.db import Investigation
    tagged = engine.create_investigation(session, "ml", "t", "q")
    real = engine.create_investigation(session, "ml",
                                       "A real investigation title",
                                       "A real, non-fingerprint question")
    real_row = session.get(Investigation, real.id)
    real_row.config = {}          # simulate a record created outside tests
    session.commit()
    session.expunge_all()
    monkeypatch.setattr(prune, "_confirm", lambda: "yes_test_prune")
    code = prune.apply_prune()
    assert code == 0
    assert session.get(Investigation, tagged.id) is None
    assert session.get(Investigation, real.id) is not None
