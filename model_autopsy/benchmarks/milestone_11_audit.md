# Milestone 11 Audit — Multi-Agent Research Collaboration

## Verdict: IMPLEMENTED and honest about its limits.

## What the team is
Six deterministic roles (`backend/m11/roles.py`) with enforced
input contracts: lead (agenda + assignment), data_scientist
(schema/hygiene brief), model_analyst (error brief), designer
(discriminating specs via the M9 inventor), skeptic (blocking +
advisory challenges), judge (verdicts from hypotheses + evidence
only — its signature excludes lead/designer/skeptic outputs, so
agreement is evidence-driven, never copied).

## Genuine disagreement
The skeptic flags unsupported-support (blocks), confounder-ignored,
and missing-falsification with proposed falsifying tests. All
challenges are preserved with resolutions; nothing is voted away.
On the ward-gap case the team records challenges and the judge
renders independent verdicts; single-vs-multi comparison shows the
team never scores worse than the baseline on the same scenario.

## What it is not
Roles are heuristic functions over shared evidence, not
independent reasoners: the skeptic cannot invent objections beyond
its three screens, the judge audits recorded evidence without
re-measuring, and multi-agent does not beat single-agent discovery
on these scenarios — it adds challenge-and-review structure at
extra tool-call cost. Claimed: better scrutiny + provenance, not
higher discovery.
