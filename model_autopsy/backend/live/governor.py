"""Hard budget governor (Milestone 5, §8.1).

Every cap is enforced BEFORE a request is sent. Attempts include
retries and summary-repair calls. Cost is computed ONLY from
provider-reported usage (never local estimates); unknown usage is
treated as unavailable, not zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import threading
import uuid

# dev.meta.ai pricing page: muse-spark-1.3 Standard, $ per token.
PRICE_INPUT = 1.25 / 1_000_000
PRICE_CACHED_INPUT = 0.15 / 1_000_000
PRICE_OUTPUT = 4.25 / 1_000_000

# M18 Phase 6: the single authorized live investigation runs under a $0.65
# absolute ceiling (M18 §Phase 6/10). All other caps are unchanged; the
# 6-experiment cap still counts actual experiment dispatches only.
CAPS = {"rounds": 3, "experiments": 6, "attempts": 12,
        "tokens": 50_000, "cost_usd": 0.65}

# M17 Phase 5: conservative per-dispatch headroom. A refused request
# costs nothing, but a dispatched one always spends its output tokens —
# so dispatch is refused while the projection (used + estimated input
# + one full output allowance) would breach the nominal cap. The
# nominal 50,000-token maximum is unchanged; the policy only stops
# earlier, never later.
EST_OUTPUT_TOKENS = 6_000


class BudgetExceeded(RuntimeError):
    """Raised pre-request when any hard cap would be exceeded."""


@dataclass
class Budget:
    caps: dict = field(default_factory=lambda: dict(CAPS))
    rounds_used: int = 0
    experiments_used: int = 0
    attempts_used: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock,
                                  repr=False, compare=False)
    _open: dict = field(default_factory=dict, repr=False, compare=False)
    _settled_tokens: set = field(default_factory=set, repr=False,
                                 compare=False)

    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost_usd(self) -> float:
        uncached = max(0, self.input_tokens - self.cached_tokens)
        return round(uncached * PRICE_INPUT
                     + self.cached_tokens * PRICE_CACHED_INPUT
                     + self.output_tokens * PRICE_OUTPUT, 6)

    def check(self, *, rounds: int = 0, experiments: int = 0,
              attempts: int = 1) -> None:
        """Pre-request gate: raise before sending if caps break."""
        if self.rounds_used + rounds > self.caps["rounds"]:
            raise BudgetExceeded(
                f"round cap {self.caps['rounds']} reached")
        if self.experiments_used + experiments > self.caps["experiments"]:
            raise BudgetExceeded(
                f"experiment cap {self.caps['experiments']} reached")
        if self.attempts_used + attempts > self.caps["attempts"]:
            raise BudgetExceeded(
                f"attempt cap {self.caps['attempts']} reached "
                f"({self.attempts_used} used)")
        if self.total_tokens() >= self.caps["tokens"]:
            raise BudgetExceeded("provider-token cap reached")
        if self.cost_usd() >= self.caps["cost_usd"]:
            raise BudgetExceeded("cost cap reached")

    def check_dispatch(self, est_input_tokens: int = 0) -> None:
        """M17 headroom gate: refuse BEFORE dispatch when the honest
        projection (used + estimated input + one output allowance) would
        breach the nominal token cap. Hard caps checked first."""
        self.check()
        projected = (self.total_tokens() + max(0, int(est_input_tokens))
                     + EST_OUTPUT_TOKENS)
        if projected > self.caps["tokens"]:
            raise BudgetExceeded(
                f"token headroom: projected {projected} > cap "
                f"{self.caps['tokens']} (used={self.total_tokens()}, "
                f"est_input={int(est_input_tokens)}, "
                f"output_allowance={EST_OUTPUT_TOKENS})")

    def record_turn(self, usage_rollup: dict,
                    fold_work: bool = True) -> None:
        """Fold a turn's provider-reported usage into the ledger.

        When the turn ran with this budget attached (reserve/settle per
        request and per execution), pass fold_work=False: attempts and
        experiments are already settled exactly, and refolding the rollup
        would double-count them. Tokens and rounds always fold here."""
        self.rounds_used += 1
        if fold_work:
            self.attempts_used += int(usage_rollup.get("api_attempts") or 0)
            self.experiments_used += int(
                usage_rollup.get("tool_calls_executed") or 0)
        tokens = usage_rollup.get("tokens") or {}
        self.input_tokens += int(tokens.get("input_tokens") or 0)
        self.cached_tokens += int(
            tokens.get("input_tokens_details.cached_tokens") or 0)
        self.output_tokens += int(tokens.get("output_tokens") or 0)

    # ---- M8 atomic reservation lifecycle (Workstream A) ----------------
    # Reserve-then-settle with a lock; durable via caller-recorded events
    # (see reserve_payload/settle_payload); ambiguous (crashed) work is
    # never assumed free — reconcile() counts it against the caps.
    def _held(self, kind: str) -> int:
        return sum(r["amount"] for r in self._open.values()
                   if r["kind"] == kind and r["status"] == "open")

    def _used(self, kind: str) -> int:
        return {"experiments": self.experiments_used,
                "attempts": self.attempts_used,
                "rounds": self.rounds_used}.get(kind, 0)

    def reserve(self, kind: str, amount: int = 1, note: str = "") -> str:
        """Atomically hold capacity; raises BudgetExceeded when unsafe."""
        if kind not in ("experiments", "attempts", "rounds"):
            raise ValueError(f"unknown reservation kind {kind!r}")
        if amount < 1:
            raise ValueError("reservation amount must be >= 1")
        with self._lock:
            cap = self.caps[kind]
            if self._used(kind) + self._held(kind) + amount > cap:
                raise BudgetExceeded(
                    f"{kind} cap {cap} would break "
                    f"(used={self._used(kind)}, held={self._held(kind)}, "
                    f"asked={amount})")
            token = uuid.uuid4().hex[:16]
            self._open[token] = {"kind": kind, "amount": amount,
                                 "status": "open", "note": note[:120]}
            return token

    def settle(self, token: str, actual: int | None = None) -> bool:
        """Idempotent: first settle applies, repeats return False."""
        with self._lock:
            rec = self._open.get(token)
            if rec is None or rec["status"] != "open":
                return False
            apply = rec["amount"] if actual is None else max(0, actual)
            if rec["kind"] == "experiments":
                self.experiments_used += apply
            elif rec["kind"] == "attempts":
                self.attempts_used += apply
            elif rec["kind"] == "rounds":
                self.rounds_used += apply
            rec["status"] = "settled"
            rec["actual"] = apply
            return True

    def release(self, token: str, reason: str = "") -> bool:
        """Explicitly free an open hold (recorded proof required by caller)."""
        with self._lock:
            rec = self._open.get(token)
            if rec is None or rec["status"] != "open":
                return False
            rec["status"] = "released"
            rec["release_reason"] = reason[:160]
            return True

    def settle_usage(self, input_tokens: int = 0, cached_tokens: int = 0,
                     output_tokens: int = 0) -> None:
        with self._lock:
            self.input_tokens += max(0, int(input_tokens or 0))
            self.cached_tokens += max(0, int(cached_tokens or 0))
            self.output_tokens += max(0, int(output_tokens or 0))

    def to_state(self) -> dict:
        with self._lock:
            return {"caps": dict(self.caps),
                    "rounds_used": self.rounds_used,
                    "experiments_used": self.experiments_used,
                    "attempts_used": self.attempts_used,
                    "input_tokens": self.input_tokens,
                    "cached_tokens": self.cached_tokens,
                    "output_tokens": self.output_tokens,
                    "open": [dict(v, token=k)
                             for k, v in self._open.items()
                             if v["status"] == "open"]}

    @classmethod
    def reconcile(cls, state: dict, ledger_events: list[dict],
                  conservative_extra_attempts: int = 0) -> "Budget":
        """Rebuild from durable records; refuse on malformed input.

        Ambiguous (reserved-but-unsettled) work counts against the caps —
        never assumed free. Raises ValueError when reconstruction is not
        confident."""
        try:
            b = cls(caps=dict(state.get("caps") or CAPS))
            for key in ("rounds_used", "experiments_used",
                        "attempts_used", "input_tokens", "cached_tokens",
                        "output_tokens"):
                val = state.get(key)
                if not isinstance(val, int) or val < 0:
                    raise ValueError(f"bad counter {key}={val!r}")
                setattr(b, key, val)
            for ev in list(state.get("open") or []) + list(
                    ledger_events or []):
                if not isinstance(ev, dict):
                    raise ValueError("malformed ledger event")
                kind, amount = ev.get("kind"), ev.get("amount")
                if ev.get("status") == "open":
                    if kind not in ("experiments", "attempts", "rounds") \
                            or not isinstance(amount, int) or amount < 1:
                        raise ValueError(f"bad open hold {ev!r}")
                    # Conservative: unsettled work counts as spent.
                    if kind == "experiments":
                        b.experiments_used += amount
                    elif kind == "attempts":
                        b.attempts_used += amount
                    else:
                        b.rounds_used += amount
            b.attempts_used += max(0, conservative_extra_attempts)
            return b
        except (AttributeError, TypeError) as exc:
            raise ValueError(f"cannot reconstruct budget: {exc}")

    def ledger(self) -> dict:
        return {"rounds": [self.rounds_used, self.caps["rounds"]],
                "experiments": [self.experiments_used,
                                self.caps["experiments"]],
                "attempts": [self.attempts_used, self.caps["attempts"]],
                "tokens": {"input": self.input_tokens,
                           "cached": self.cached_tokens,
                           "output": self.output_tokens,
                           "total": self.total_tokens(),
                           "cap": self.caps["tokens"]},
                "cost_usd": {"spent": self.cost_usd(),
                             "cap": self.caps["cost_usd"]},
                "pricing": "muse-spark-1.3 Standard: "
                           "$1.25/$0.15 cached input, $4.25 output per 1M"}


def project_cost_brief(input_chars: int) -> dict:
    """Preflight projection: worst case assumes zero cache hits and a
    generous output allowance per request within the attempt cap."""
    per_req_in = max(1, round(input_chars / 4))
    worst_in = per_req_in * CAPS["attempts"]
    worst_out = 2000 * CAPS["attempts"]
    worst_cost = round(worst_in * PRICE_INPUT
                       + worst_out * PRICE_OUTPUT, 4)
    typical_cost = round(
        (worst_in * 0.2 * PRICE_INPUT
         + worst_in * 0.8 * PRICE_CACHED_INPUT
         + 7000 * PRICE_OUTPUT), 4)
    return {"worst_case_usd": worst_cost,
            "typical_cached_usd": typical_cost,
            "within_cap": worst_cost <= CAPS["cost_usd"],
            "note": "worst case assumes no cache hits; typical uses the "
                    "cached-input rate for 80% of input (matches preserved "
                    "phase_d usage patterns)"}
