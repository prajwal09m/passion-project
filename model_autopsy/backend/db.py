"""SQLite persistence for Model Autopsy.

Tables:
  investigations — one row per investigation (mode, status, config, report).
  hypotheses     — proposed/validated hypotheses owned by an investigation.
  actions        — every executed tool call or orchestration step (bounded).
  events         — append-only timeline: meta requests/responses, tool runs,
                   test results, revisions, reports.
  settings       — non-secret operational configuration and Meta test state.
"""
from __future__ import annotations

import datetime as _dt
import json
import uuid
from pathlib import Path

from sqlalchemy import (JSON, DateTime, ForeignKey, Integer, String, Text,
                        create_engine)
from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, mapped_column,
                            relationship, sessionmaker)

from . import config

_paths = Path(config.DB_PATH)
_paths.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{_paths}",
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _uuid() -> str:
    return uuid.uuid4().hex


def utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None, microsecond=0)


class Base(DeclarativeBase):
    pass


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    mode: Mapped[str] = mapped_column(String(16), index=True)  # software | ml
    title: Mapped[str] = mapped_column(String(200))
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="created", index=True)
    # created -> context_ready -> hypotheses_proposed -> investigating ->
    # revising -> finalizing -> complete | blocked | failed | stopped
    iteration_count: Mapped[int] = mapped_column(Integer, default=0)
    max_iterations: Mapped[int] = mapped_column(Integer, default=3)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    max_tool_calls: Mapped[int] = mapped_column(Integer, default=12)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    final_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latest_findings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow,
                                                    onupdate=utcnow)

    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan")
    actions: Mapped[list["Action"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan")


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(24), default="meta")
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    # proposed | investigating | supported | rejected | inconclusive
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    predicted_observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured extensions (SQLite ALTER TABLE migrations in init_db):
    evidence_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    revisions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow)

    investigation: Mapped[Investigation] = relationship(back_populates="hypotheses")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(24))  # tool_call | meta_turn | revision | report
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="recorded")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow)

    investigation: Mapped[Investigation] = relationship(back_populates="actions")


class Event(Base):
    """Append-only timeline entry (drives Timeline / History views)."""
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigations.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(32))
    # meta_request | meta_response | tool_request | tool_result |
    # test_result | revision | finding | hypothesis | report | status_change
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow)

    investigation: Mapped[Investigation] = relationship(back_populates="events")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[_dt.datetime] = mapped_column(DateTime, default=utcnow,
                                                     onupdate=utcnow)


def init_db() -> None:
    Base.metadata.create_all(engine)
    _migrate_sqlite_columns(engine)


def _migrate_sqlite_columns(bind) -> None:
    """Additive, backward-compatible column migrations for existing DBs.
    create_all() never alters live tables, so list columns via PRAGMA and
    ALTER TABLE the missing ones. Existing rows keep their records."""
    from sqlalchemy import text
    wanted = {
        "hypotheses": {
            "predicted_observation": "TEXT",
            "confidence_note": "TEXT",
            "evidence_refs": "JSON",
            "revisions": "JSON",
        },
    }
    with bind.connect() as conn:
        for table, cols in wanted.items():
            existing = {row[1] for row in conn.execute(
                text(f"PRAGMA table_info({table})")).fetchall()}
            if not existing:
                continue
            for col, coltype in cols.items():
                if col not in existing:
                    conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
        conn.commit()


def next_seq(session: Session, investigation_id: str) -> int:
    row = (session.query(Event)
           .filter(Event.investigation_id == investigation_id)
           .order_by(Event.seq.desc()).first())
    return (row.seq + 1) if row else 1


def record_event(session: Session, investigation_id: str, kind: str,
                 title: str, detail: str | None = None,
                 payload: dict | None = None) -> Event:
    ev = Event(investigation_id=investigation_id, seq=next_seq(session, investigation_id),
               kind=kind, title=title, detail=detail, payload=payload or {})
    session.add(ev)
    return ev


def get_setting(session: Session, key: str, default: str | None = None) -> str | None:
    row = session.get(Setting, key)
    return row.value if row else default


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value


def to_json_blob(obj) -> dict | list | None:
    """JSON-safe conversion for tool results (numpy/pandas friendly)."""
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return str(obj)
        return round(obj, 6)
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return to_json_blob(float(obj))
    if isinstance(obj, np.ndarray):
        return [to_json_blob(v) for v in obj.tolist()]
    if isinstance(obj, dict):
        return {str(k): to_json_blob(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_json_blob(v) for v in obj]
    import pandas as pd
    if isinstance(obj, pd.Series):
        return to_json_blob({obj.index.name or "index": None}) if False else [to_json_blob(v) for v in obj.tolist()]
    if isinstance(obj, pd.DataFrame):
        return {"rows": obj.shape[0], "columns": list(obj.columns)}
    return str(obj)


def dump_payload(payload) -> str:
    return json.dumps(to_json_blob(payload), default=str, sort_keys=True)
