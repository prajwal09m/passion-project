"""Session-wide test isolation for Model Autopsy.

Every pytest run uses a throwaway SQLite database under the system temp
directory; the application/demo database (backend/data/model_autopsy.db)
is never touched by tests. The safeguard below refuses to run if the
isolation fails to produce a distinct path.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# The env overrides MUST be set before config/db are first imported: config
# computes DB_PATH once at import time. MODEL_AUTOPSY_TESTING marks every
# record the tests create so it is always distinguishable from real data.
_TMP_DB = Path(tempfile.mkdtemp(prefix="model_autopsy_test_db_")) / "test.sqlite3"
os.environ["MODEL_AUTOPSY_DB_PATH"] = str(_TMP_DB)
os.environ["MODEL_AUTOPSY_TESTING"] = "1"

from model_autopsy.backend import config as _config  # noqa: E402
import model_autopsy.backend.db as _db  # noqa: E402  (binds fresh engine)

_DEFAULT_APP_DB = (_config.BACKEND_DIR / "data" / "model_autopsy.db").resolve()


def pytest_configure(config) -> None:  # noqa: ANN001
    actual = Path(str(_config.DB_PATH)).resolve()
    if actual == _DEFAULT_APP_DB:
        raise RuntimeError(
            f"test isolation failed: DB path {actual} is the application "
            "database; the MODEL_AUTOPSY_DB_PATH override was ignored")
    engine_path = Path(_db.engine.url.database or "").resolve()
    if engine_path != _TMP_DB.resolve():
        raise RuntimeError(
            "test isolation failed: SQLAlchemy engine bound to "
            f"{engine_path}, not the temp DB {_TMP_DB}")
