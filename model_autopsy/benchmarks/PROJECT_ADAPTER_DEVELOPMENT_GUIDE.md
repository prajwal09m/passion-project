# Project Adapter Development Guide

## What a new project needs (no engine changes)
1. A `ProjectSpec` (metadata: project, model, dataset, task).
2. Optionally a `ProjectAdapter` subclass (custom context/brief/capabilities).
3. Optionally custom diagnostic tools (see Diagnostic guide).
4. One registration call: `register_project(MyAdapter(spec))`.

## Minimal example
```python
from model_autopsy.backend.projects import (
    ProjectSpec, ProjectAdapter, DatasetMetadata, ModelMetadata,
    TaskType, ModelAvailability, register_project)

spec = ProjectSpec(
    project_id="churn", name="Churn prediction", domain="telecom",
    objective="Why did churn-model precision drop in Q3?",
    task_type=TaskType.CLASSIFICATION.value,
    target_definition="Binary: churned within 30 days",
    evaluation_methodology="AUC + precision@k on rolling windows",
    model=ModelMetadata(name="churn-gbm", framework="lightgbm",
                        availability=ModelAvailability.BLACK_BOX.value),
    dataset=DatasetMetadata(location="data/churn_scores.csv", n_rows=80000))
register_project(ProjectAdapter(spec))  # subclass to override context_summary()
```

## Rules
- `spec.validate()` must return `[]`; the adapter constructor enforces this.
- Put project knowledge in the spec/adapter — never in `engine.py`.
- Capabilities claimed must be ones the project's data/model actually expose.
- `investigator_brief()` is injected verbatim into investigator context; keep it factual.

## Wiring it in
- Investigations: `POST /api/investigations` with `"project_id": "<id>"`.
- The project appears automatically in `GET /api/projects` and the dashboard Projects page.
- Reference implementation: `backend/projects/demand_zone.py`.
