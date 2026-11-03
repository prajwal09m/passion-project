"""Human-review workflow (Milestone 4).

Blind-then-reveal: the reviewer first records a verdict on the
investigator report WITHOUT ground truth; only then may the truth be
revealed and a post-reveal assessment recorded. The store enforces
ordering (reveal requires a prior blind verdict). Reviews live
separately from automated scorecards; absence of review is reported as
absent, never fabricated.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

BLIND_VERDICTS = ("defensible", "questionable", "not_defensible",
                   "cannot_tell")


def review_path(rundir: Path, pid: str) -> Path:
    return Path(rundir) / f"{pid}.review.json"


def blind_verdict(rundir: Path, pid: str, reviewer: str,
                  verdict: str, notes: str = "") -> dict:
    """Record the pre-reveal assessment. Ground truth must NOT have been
    shown: the record stores reviewer attestation + timestamp."""
    if verdict not in BLIND_VERDICTS:
        raise ValueError(f"unknown blind verdict {verdict!r}")
    rp = review_path(rundir, pid)
    if rp.exists():
        raise RuntimeError(f"review for {pid} already exists; reviews are "
                           "append-only, refusing to overwrite")
    rec = {"project": pid, "reviewer": reviewer,
           "blind_verdict": verdict, "blind_notes": notes,
           "blind_at": _dt.datetime.now(
               _dt.timezone.utc).replace(tzinfo=None,
                                         microsecond=0).isoformat() + "Z",
           "revealed": False, "attests_no_prior_truth": True}
    rp.write_text(json.dumps(rec, indent=2))
    return rec


def reveal_and_assess(rundir: Path, pid: str, assessment: str) -> dict:
    """Reveal step: requires an existing blind verdict, then records the
    post-reveal assessment alongside (never replacing) the blind one."""
    from . import projects as P
    rp = review_path(rundir, pid)
    if not rp.exists():
        raise RuntimeError(f"no blind verdict for {pid}; reveal refused "
                           "until the reviewer assesses the report blind")
    rec = json.loads(rp.read_text(encoding="utf-8"))
    if rec.get("revealed"):
        raise RuntimeError(f"{pid} already revealed; refusing to overwrite")
    truth = P.load_truth()[pid]
    rec["revealed"] = True
    rec["post_reveal_assessment"] = assessment
    rec["ground_truth_summary"] = truth["mechanism"][:300]
    rp.write_text(json.dumps(rec, indent=2))
    return rec


def status(rundir: Path, pid: str) -> dict:
    rp = review_path(rundir, pid)
    if not rp.exists():
        return {"project": pid, "review": None,
                "note": "no human review recorded"}
    return {"project": pid,
            "review": json.loads(rp.read_text(encoding="utf-8"))}
