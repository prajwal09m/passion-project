"""Hypothesis lifecycle management (Milestone 3, Part 3).

Every hypothesis is a structured card with mechanism, motivating
evidence, expected observables, diagnostics, support/refute criteria,
priority and explicit status. Status transitions are validated; a
hypothesis can only reach supported/rejected with linked evidence.
Cards live in investigation config['research']['hypotheses'] so no DB
migration is needed; DB hypotheses stay untouched for backward compat.
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field

STATUSES = ("proposed", "investigating", "supported", "rejected",
            "inconclusive", "blocked")

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "proposed": ("investigating", "blocked", "rejected", "inconclusive"),
    "investigating": ("supported", "rejected", "inconclusive", "blocked",
                      "proposed"),
    "blocked": ("proposed", "investigating", "inconclusive"),
    "supported": ("investigating",),
    "rejected": ("investigating",),
    "inconclusive": ("investigating", "proposed"),
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class HypothesisCard:
    id: str = ""
    title: str = ""
    mechanism: str = ""
    evidence_motivating: list = field(default_factory=list)
    expected_observables: list = field(default_factory=list)
    diagnostics: list = field(default_factory=list)
    support_criteria: str = ""
    refute_criteria: str = ""
    priority: str = "medium"
    status: str = "proposed"
    history: list = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []
        if not self.title.strip():
            errors.append("title is required")
        if not self.mechanism.strip():
            errors.append("mechanism is required")
        if not self.support_criteria.strip():
            errors.append("support_criteria is required")
        if not self.refute_criteria.strip():
            errors.append("refute_criteria is required")
        if self.priority not in PRIORITY_ORDER:
            errors.append(f"unknown priority {self.priority!r}")
        if self.status not in STATUSES:
            errors.append(f"unknown status {self.status!r}")
        return errors


def _space(inv) -> dict:
    import copy as _copy
    rs = _copy.deepcopy(dict((inv.config or {}).get("research") or {}))
    rs.setdefault("hypotheses", [])
    return rs


def _save(session, inv, rs: dict) -> None:
    inv.config = {**(inv.config or {}), "research": rs}
    session.commit()


def propose(session, inv, card: dict) -> dict:
    from ..db import record_event
    c = HypothesisCard(id=card.get("id") or uuid.uuid4().hex[:12],
                       title=card.get("title", ""),
                       mechanism=card.get("mechanism", ""),
                       evidence_motivating=list(
                           card.get("evidence_motivating") or []),
                       expected_observables=list(
                           card.get("expected_observables") or []),
                       diagnostics=list(card.get("diagnostics") or []),
                       support_criteria=card.get("support_criteria", ""),
                       refute_criteria=card.get("refute_criteria", ""),
                       priority=card.get("priority", "medium"))
    errors = c.validate()
    if errors:
        raise ValueError(f"invalid hypothesis card: {errors}")
    rs = _space(inv)
    if any(h.get("id") == c.id for h in rs["hypotheses"]):
        raise ValueError(f"duplicate hypothesis id {c.id!r}")
    entry = asdict(c)
    entry["history"] = [{"at": "now", "from": None, "to": "proposed",
                         "note": card.get("note", "proposed")}]
    rs["hypotheses"].append(entry)
    _save(session, inv, rs)
    record_event(session, inv.id, "hypothesis",
                 f"Research hypothesis proposed: {c.title[:120]}",
                 payload={"hypothesis_id": c.id, "priority": c.priority})
    session.commit()
    return entry


def transition(session, inv, hid: str, to: str, note: str = "",
               evidence: list | None = None) -> dict:
    from ..db import record_event
    if to not in STATUSES:
        raise ValueError(f"unknown status {to!r}")
    rs = _space(inv)
    for h in rs["hypotheses"]:
        if h["id"] == hid:
            frm = h["status"]
            if to not in TRANSITIONS.get(frm, ()):
                raise ValueError(
                    f"illegal research transition {frm} -> {to}")
            if to in ("supported", "rejected") and not (
                    evidence or h.get("evidence_motivating")):
                raise ValueError(
                    f"cannot mark {to} without evidence references")
            h["status"] = to
            h["history"].append({"from": frm, "to": to, "note": note,
                                 "evidence": evidence or []})
            if evidence:
                h["evidence_motivating"] = list(
                    h.get("evidence_motivating") or []) + list(evidence)
            _save(session, inv, rs)
            record_event(
                session, inv.id, "hypothesis",
                f"Research hypothesis {hid[:8]} {frm} -> {to}",
                payload={"hypothesis_id": hid, "from": frm, "to": to,
                         "note": note})
            session.commit()
            return h
    raise LookupError(f"hypothesis {hid!r} not found")


def list_cards(inv) -> list[dict]:
    rs = dict((inv.config or {}).get("research") or {})
    cards = list(rs.get("hypotheses") or [])
    return sorted(cards,
                  key=lambda h: (PRIORITY_ORDER.get(h.get("priority"),
                                                    9), h.get("id", "")))
