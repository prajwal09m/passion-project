"""Owner-controlled pruning of test-generated investigation records.

Model Autopsy never deletes records automatically. This module exists so
the owner can, in ONE documented step, review which database records were
created by test runs and (only then, explicitly) remove them.

Identification
--------------
  1. Records created while MODEL_AUTOPSY_TESTING=1 was set (the test
     conftest sets it) carry a `"test"` tag in their config.
  2. Legacy records from pre-isolation test runs predate that marker and
     are matched against a conservative fingerprint list: the literal
     titles/questions the test suite uses. They are surfaced for human
     review with their id, title, timestamp and counts.

Usage
-----
  Dry run (default, changes nothing):
      py -3 -m model_autopsy.backend.prune

  Apply (deletes only the candidates printed above, requires explicit
  confirmation via env var — never a stray flag):
      py -3 -m model_autopsy.backend.prune --apply
      with  MODEL_AUTOPSY_CONFIRM_PRUNE = yes_test_prune
"""
from __future__ import annotations

import sys

from . import db

# Titles/questions used verbatim by model_autopsy/tests. A REAL
# investigation could coincidentally match one of these — which is exactly
# why the listing is human-reviewed before --apply deletes anything.
LEGACY_FINGERPRINTS = {
    "t", "title", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9",
    "fake case", "x", "y",
    "Where does the model fail?", "why?", "q",
}
TEST_TAG = "test"


def is_test_record(inv: db.Investigation) -> tuple[bool, str]:
    """(is_candidate, reason). Conservative: tag first, fingerprints second."""
    cfg = inv.config if isinstance(inv.config, dict) else {}
    tags = cfg.get("tags") or []
    if TEST_TAG in tags:
        return True, "tagged 'test' (created under MODEL_AUTOPSY_TESTING=1)"
    if (inv.title or "").strip() in LEGACY_FINGERPRINTS:
        return True, "legacy pre-isolation test fingerprint (exact title match)"
    return False, ""


def candidates(session) -> list[tuple[db.Investigation, str]]:
    out = []
    for inv in session.query(db.Investigation).order_by(
            db.Investigation.created_at).all():
        flag, reason = is_test_record(inv)
        if flag:
            out.append((inv, reason))
    return out


def print_candidates() -> int:
    db.init_db()
    s = db.SessionLocal()
    try:
        found = candidates(s)
        if not found:
            print("No test-generated records found. Nothing to prune.")
            return 0
        print(f"{len(found)} test-record candidate(s) in the "
              f"application database ({db._paths}):")
        for inv, reason in found:
            print(f"  {inv.id}  {str(inv.created_at)}  mode={inv.mode}  "
                  f"title={inv.title!r}  tools={inv.tool_call_count}  "
                  f"reason={reason}")
        print("\nNothing was deleted. To remove exactly the rows above:")
        print("  MODEL_AUTOPSY_CONFIRM_PRUNE=yes_test_prune "
              "py -3 -m model_autopsy.backend.prune --apply")
        return len(found)
    finally:
        s.close()


def apply_prune() -> int:
    if _confirm() != "yes_test_prune":
        print("Refusing: --apply requires MODEL_AUTOPSY_CONFIRM_PRUNE="
              "yes_test_prune in the environment (owner confirmation).")
        return 1
    db.init_db()
    s = db.SessionLocal()
    n = 0
    try:
        for inv, _reason in candidates(s):
            s.delete(inv)     # cascades to hypotheses/actions/events
            n += 1
        s.commit()
        print(f"Deleted {n} test-generated record(s).")
        return 0 if n >= 0 else 1
    except Exception as exc:
        s.rollback()
        print(f"Prune failed before commit; nothing deleted: "
              f"{type(exc).__name__}: {exc}")
        return 2
    finally:
        s.close()


def _confirm() -> str:
    import os
    return os.environ.get("MODEL_AUTOPSY_CONFIRM_PRUNE", "")


def main(argv: list[str]) -> int:
    if "--apply" in argv:
        return apply_prune()
    return print_candidates()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
