"""Independent evaluation framework (Milestone 4).

Tests whether Model Autopsy can investigate UNFAMILIAR projects with
concealed failure mechanisms. Separate from the Milestone 3 flagship
challenge (which stays frozen): new projects, sealed ground truth,
trust-boundary enforcement, mechanism-level scoring, repeatable runs,
and blind human review. Fully offline; initiates zero provider calls.
"""
from __future__ import annotations

EVAL_VERSION = "m4-v1"
INVESTIGATOR_VERSION = "lab-deterministic-v1"
