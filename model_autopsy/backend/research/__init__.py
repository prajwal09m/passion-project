"""Autonomous research orchestration layer (Milestone 3, Part 1).

Sits ABOVE the universal investigation engine; never rewrites it.
Coordinates explicit stages with typed state, inputs, outputs and
provenance events. Provider-independent: the driver accepts an optional
reasoner callback but defaults to fully offline deterministic mode.
"""
from __future__ import annotations
