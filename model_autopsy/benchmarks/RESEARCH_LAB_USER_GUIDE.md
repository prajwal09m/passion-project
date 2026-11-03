# Research Lab User Guide (Milestone 3, Part 11)

## When to use it

You have an unfamiliar ML project and want an evidence-backed answer
to "what is wrong and how do you know". Use the Research Lab for the
autonomous cycle; use the existing Case Study / Projects pages for
manual inspection.

## Workflow

1. Open an ML investigation (or create one with a `project_id`).
2. Scroll to the **Research lab** section in the Workspace.
3. Press **Run autonomous cycle (offline)** — no key needed, no spend.
4. Read the 8 sections in order:
   1. Research overview (stages completed, executive summary).
   2. Hypothesis workspace (cards with status, priority, mechanism).
   3. Experiment laboratory (per-experiment tool + result summary).
   4. Evidence explorer (references; full outputs by experiment id).
   5. Verification workspace (upheld/downgraded/rejected + disagreements).
   6. Model behavior (task-aware panels from the Projects view).
   7. Efficiency (offline: no billed tokens; Part-10 harness numbers).
   8. Final forensic report (confirmed / rejected / limits / next steps).

## API equivalents

`POST /research/run`, `GET /research` (state), `POST
/research/hypotheses` (propose with title/mechanism/support/refute),
`POST /research/hypotheses/{id}/transition` (validated transitions;
evidence required to confirm).

## Interpreting results

- `supported` + review `upheld` = act on it (re-run on fresh data first).
- `downgraded`/`rejected` with preserved disagreement = read the
  checks before deciding; the lab keeps both sides visible.
- `blocked` = supply the missing artifact listed in the card note.
- Empty confirmed list on a clean project is a SUCCESS (null held).

## Safety

The lab never modifies originals (copy-on-read workspaces under
`backend/data/research_runs/`), never calls external services, and
has no path to overwrite weights or configs. Destructive actions
require future owner-approval gates that are not yet implemented —
nothing in the lab pretends otherwise.
