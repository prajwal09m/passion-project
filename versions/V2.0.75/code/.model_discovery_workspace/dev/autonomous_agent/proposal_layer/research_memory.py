"""Development-only outcome taxonomy and append-only research memory.

NOT wired into production. Every experiment record is classified into exactly
one category, and every category has a precise meaning:

  VERIFIED_IMPROVEMENT  Measurement completed, decision criteria passed, and the
                        evidence is substantive (not a replication of an
                        existing key). Supports only a claim about this exact
                        measurement key on the recorded data.
  REJECTED              Measurement completed and decision criteria failed.
                        Says this configuration did not clear the criteria. It
                        says nothing about related configurations.
  INCONCLUSIVE          Measurement completed but the decision is three-valued
                        INCONCLUSIVE (for example, under-sized cell).
  UNAVAILABLE           The measurement could not be obtained (missing input,
                        missing artifact). No inference about the model.
  INTERRUPTED           Execution stopped before completion. Not a model failure.
  INVALID_CONFIG        The configuration failed compilation or validation. It
                        was never executed.
  REDUNDANT             A proposal whose measurement key already has evidence.
                        Not executed; carries no new evidence.
  REPLICATION           Re-measures an existing key under other seeds. Adds
                        stability evidence for a known key, not a new model.
  NOVEL_HYPOTHESIS      Measurement completed on a key never measured before.

Precedence (first match wins): INVALID_CONFIG, REDUNDANT (proposal only),
INTERRUPTED, UNAVAILABLE, INCONCLUSIVE, REPLICATION, then VERIFIED_IMPROVEMENT,
REJECTED, or NOVEL_HYPOTHESIS, depending on the decision.

Temporal discipline: ``ResearchMemory.as_of(cutoff)`` is the only way to read
history for ranking. It returns only records whose ``at`` is strictly before
the cutoff, so a later outcome cannot change an earlier ranking. Failures are
retained as evidence; nothing is dropped from memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

from autonomous_agent.proposal_layer import outcome_ranking as ork


class Outcome(str, Enum):
    VERIFIED_IMPROVEMENT = "verified_improvement"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"
    UNAVAILABLE = "unavailable"
    INTERRUPTED = "interrupted"
    INVALID_CONFIG = "invalid_config"
    REDUNDANT = "redundant"
    REPLICATION = "replication"
    NOVEL_HYPOTHESIS = "novel_hypothesis"


# Categories that carry a pass/fail signal usable as a ranking outcome.
DECIDED = frozenset({Outcome.VERIFIED_IMPROVEMENT, Outcome.REJECTED,
                     Outcome.REPLICATION, Outcome.NOVEL_HYPOTHESIS})


@dataclass(frozen=True)
class Record:
    """One proposal's experiment record. Fields are facts known at ``at``."""
    at: str                          # ISO-8601 time the fact became known
    proposal_id: str
    key: str                         # measurement key (compiled config identity)
    direction: str
    is_proposal_only: bool = False   # True if never executed
    valid_config: bool = True
    interrupted: bool = False
    measurement_available: bool = True
    inconclusive: bool = False
    passed: Optional[bool] = None    # decision criteria result if decided
    key_seen_before: bool = False    # key had evidence when proposed
    is_replication: bool = False     # same key, different seeds


def classify(r: Record) -> Outcome:
    if not r.valid_config:
        return Outcome.INVALID_CONFIG
    if r.is_proposal_only and r.key_seen_before:
        return Outcome.REDUNDANT
    if r.interrupted:
        return Outcome.INTERRUPTED
    if not r.measurement_available:
        return Outcome.UNAVAILABLE
    if r.inconclusive or r.passed is None:
        return Outcome.INCONCLUSIVE
    if r.is_replication:
        return Outcome.REPLICATION
    if r.passed:
        return Outcome.VERIFIED_IMPROVEMENT if r.key_seen_before else Outcome.NOVEL_HYPOTHESIS
    return Outcome.REJECTED


@dataclass
class ResearchMemory:
    records: list[Record] = field(default_factory=list)

    def append(self, record: Record) -> None:
        self.records.append(record)

    def extend(self, records: Iterable[Record]) -> None:
        self.records.extend(records)

    def as_of(self, cutoff: str) -> list[Record]:
        """Only records known strictly before ``cutoff``."""
        return [r for r in self.records if r.at < cutoff]

    def counts(self) -> dict[str, int]:
        out = {o.value: 0 for o in Outcome}
        for r in self.records:
            out[classify(r).value] += 1
        return out

    def rank(self, keys: Iterable[tuple[str, str]], cutoff: str) -> list[tuple[str, float]]:
        """Rank (key, direction) candidates using only evidence before ``cutoff``.

        Only DECIDED records are used as pass/fail observations. Records that
        are REDUNDANT, INTERRUPTED, UNAVAILABLE, INVALID_CONFIG, or INCONCLUSIVE
        do not count as evidence about the model.
        """
        history = self.as_of(cutoff)
        # Evidence belongs to the canonical measurement key, not proposal
        # phrasing or parameter labels. This prevents repeated campaigns or
        # multiple primitives that compile to one measurement from appearing
        # to be independent ranking trials.
        obs = [ork.Observation(at=r.at, direction=r.direction, proposal_class="experiment",
                               primitive_id=r.key, passed=bool(r.passed))
               for r in history if classify(r) in DECIDED]
        scored = []
        for key, direction in keys:
            if key not in ork._effective_adjudicated_groups(obs):
                # A genuinely unseen measurement key receives the cold-start
                # prior, not a pseudo-observation equal to the historical mean.
                global_groups = ork._effective_adjudicated_groups(obs)
                global_prior = ork._mean(global_groups.values(), 0.5)
                direction_groups = ork._direction_group_outcomes(obs, direction)
                direction_prior = ork._mean(direction_groups.values(), global_prior)
                prior = min(0.95, max(0.05,
                                      global_prior + 0.25 * (direction_prior - global_prior)))
                scored.append((key, prior))
            else:
                est = ork.estimate(obs, cutoff=cutoff, direction=direction,
                                   primitive_id=key)
                scored.append((key, est.mean))

        return sorted(scored, key=lambda kv: (-kv[1], kv[0]))
