"""Universal project adapter system (Phase 2).

A Project is described by a validated ProjectSpec (metadata + model +
dataset + task). The core engine consumes the spec — never project fields
directly. New projects need: a spec, optionally an adapter subclass, and
optionally custom tools. Demand Zone AI ships as the reference adapter.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    FORECASTING = "forecasting"
    RANKING = "ranking"
    CLUSTERING = "clustering"
    OTHER = "other"


class ModelAvailability(str, Enum):
    LOCAL = "local"            # weights loadable in-process
    API = "api"                # inference via remote endpoint
    BLACK_BOX = "black_box"    # predictions/observations only


@dataclass
class ModelMetadata:
    name: str = "unknown"
    architecture: str = "unknown"
    framework: str = "unknown"
    version: str = "unknown"
    task: str = "classification"
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    training_config: dict = field(default_factory=dict)
    inference_config: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    availability: str = ModelAvailability.BLACK_BOX.value

    def validate(self) -> list[str]:
        errors = []
        if not self.name.strip():
            errors.append("model.name is required")
        if self.availability not in {m.value for m in ModelAvailability}:
            errors.append(f"unknown availability {self.availability!r}")
        return errors


@dataclass
class DatasetMetadata:
    location: str = ""
    features: list = field(default_factory=list)
    target: dict = field(default_factory=dict)
    n_rows: int | None = None
    partitions: dict = field(default_factory=dict)
    temporal_structure: dict = field(default_factory=dict)
    provenance: str = ""
    missing_value_info: dict = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors = []
        if self.n_rows is not None and self.n_rows < 0:
            errors.append("dataset.n_rows cannot be negative")
        return errors


@dataclass
class ProjectSpec:
    project_id: str
    name: str
    description: str = ""
    domain: str = "general"
    objective: str = ""
    task_type: str = TaskType.CLASSIFICATION.value
    target_definition: str = ""
    evaluation_methodology: str = ""
    known_limitations: list = field(default_factory=list)
    model: ModelMetadata = field(default_factory=ModelMetadata)
    dataset: DatasetMetadata = field(default_factory=DatasetMetadata)
    custom_tools: list = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []
        if not self.project_id.strip():
            errors.append("project_id is required")
        if not self.name.strip():
            errors.append("name is required")
        if self.task_type not in {t.value for t in TaskType}:
            errors.append(f"unknown task_type {self.task_type!r}")
        errors += [f"model.{e}" for e in self.model.validate()]
        errors += [f"dataset.{e}" for e in self.dataset.validate()]
        return errors

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectSpec":
        data = dict(data)
        model = data.pop("model", {})
        dataset = data.pop("dataset", {})
        if isinstance(model, dict):
            data["model"] = ModelMetadata(**{k: v for k, v in model.items()
                                             if k in ModelMetadata.__dataclass_fields__})
        if isinstance(dataset, dict):
            data["dataset"] = DatasetMetadata(**{k: v for k, v in dataset.items()
                                                 if k in DatasetMetadata.__dataclass_fields__})
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})

    def investigator_brief(self) -> str:
        """Domain-independent brief injected into investigator context."""
        lines = [f"Project: {self.name} (domain: {self.domain}).",
                 f"Objective: {self.objective or self.description or 'not stated'}",
                 f"Task: {self.task_type}; target: "
                 f"{self.target_definition or 'see dataset metadata'}",
                 f"Model: {self.model.name} [{self.model.framework} / "
                 f"{self.model.architecture}], availability: {self.model.availability}.",
                 f"Evaluation: {self.evaluation_methodology or 'not stated'}."]
        if self.known_limitations:
            lines.append("Known limitations: " + "; ".join(self.known_limitations))
        return "\n".join(lines)


class ProjectAdapter:
    """Base adapter: spec + project-specific context/brief behavior.

    Subclass for project-specific context loading; the default
    implementation is fully generic (spec-driven, no filesystem access).
    """

    def __init__(self, spec: ProjectSpec):
        errors = spec.validate()
        if errors:
            raise ValueError(f"invalid project spec: {errors}")
        self.spec = spec

    @property
    def project_id(self) -> str:
        return self.spec.project_id

    def context_summary(self) -> dict:
        """Small JSON-serializable summary for investigator context."""
        return {"project_id": self.spec.project_id, "name": self.spec.name,
                "domain": self.spec.domain, "task_type": self.spec.task_type,
                "objective": self.spec.objective,
                "model": {"name": self.spec.model.name,
                          "framework": self.spec.model.framework,
                          "availability": self.spec.model.availability},
                "dataset": {"location": self.spec.dataset.location,
                            "n_rows": self.spec.dataset.n_rows,
                            "target": self.spec.dataset.target,
                            "partitions": self.spec.dataset.partitions}}

    def investigator_brief(self) -> str:
        return self.spec.investigator_brief()

    def available_capabilities(self) -> list[str]:
        """Capability tokens the project's model/data expose (Phase 3/6)."""
        return ["prediction_inspection", "error_analysis"]


_REGISTRY: dict[str, ProjectAdapter] = {}


def _register_builtin_reference() -> None:
    """Demand Zone AI is always present as the reference project."""
    from . import demand_zone as _dz  # noqa: F401
    assert _dz is not None


def register_project(adapter: ProjectAdapter) -> None:
    _REGISTRY[adapter.project_id] = adapter


def get_project(project_id: str) -> ProjectAdapter:
    try:
        return _REGISTRY[project_id]
    except KeyError:
        raise LookupError(f"unknown project {project_id!r}") from None


def list_projects() -> list[dict]:
    return [{"project_id": a.project_id, "name": a.spec.name,
             "domain": a.spec.domain, "task_type": a.spec.task_type}
            for a in _REGISTRY.values()]


_register_builtin_reference()
