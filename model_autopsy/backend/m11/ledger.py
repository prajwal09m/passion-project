"""M11 shared budget ledger (all agents, one cap).

Every tool execution by any agent reserves here first. Reservations
are atomic (thread-safe): concurrent agents cannot overspend even
when they act in parallel. Paid work additionally requires an
explicit human authorization token (see m12.authorization) — the
ledger alone never authorizes spend.
"""
from __future__ import annotations

import threading


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, tool_calls: int):
        self.cap = int(tool_calls)
        self.used = 0
        self._lock = threading.Lock()
        self.log: list[dict] = []

    def reserve(self, agent: str, tool: str, n: int = 1) -> dict:
        """Atomically reserve n tool calls. Raises BudgetExceeded."""
        with self._lock:
            if self.used + n > self.cap:
                raise BudgetExceeded(
                    f"{agent}/{tool}: cap {self.cap}, used "
                    f"{self.used}, need {n}")
            self.used += n
            entry = {"agent": agent, "tool": tool, "n": n,
                     "used": self.used, "cap": self.cap}
            self.log.append(entry)
            return entry

    def remaining(self) -> int:
        with self._lock:
            return self.cap - self.used
