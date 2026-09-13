from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import Field, field_validator, model_validator

from eval_mutation.domain.models import (
    InboundRequest,
    StrictModel,
    Team,
    TicketRecord,
    TriageReceipt,
    Urgency,
)


class EvalSplit(StrEnum):
    DEVELOPMENT = "development"
    CONFIRMATION = "confirmation"


class TaskFamily(StrEnum):
    T1_ROUTINE_ROUTING = "T1_routine_routing"
    T2_ROUTING_BOUNDARY = "T2_routing_boundary"
    T3_URGENCY_THRESHOLD = "T3_urgency_threshold"
    T4_URGENCY_DECOY = "T4_urgency_decoy"
    T5_TRUE_RELATION = "T5_true_relation"
    T6_RELATION_DISTRACTOR = "T6_relation_distractor"
    T7_POLICY_AMBIGUITY = "T7_policy_ambiguity"
    T8_INTEGRATED = "T8_integrated"


class ConstructFacet(StrEnum):
    F1_ROUTING = "F1_routing"
    F2_URGENCY = "F2_urgency"
    F3_RELATIONS = "F3_relations"
    F4_POLICY = "F4_policy_uncertainty"
    F5_TRANSACTION = "F5_transaction"


class DifficultyBand(StrEnum):
    ROUTINE = "routine"
    BOUNDARY = "boundary"
    INTEGRATED = "integrated"


class RiskSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TriageCaseInput(StrictModel):
    request: InboundRequest
    fixture_path: str = "fixtures/demo_tickets.json"
    frozen_at: datetime
    injected_tool_condition: str | None = None

    @field_validator("fixture_path")
    @classmethod
    def fixture_must_be_workspace_relative(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("fixture_path must be a workspace-relative path without '..'")
        return value


class PersistenceEvidence(StrictModel):
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_state_unchanged: bool
    ticket_count_before: int = Field(ge=0)
    ticket_count_after: int = Field(ge=0)
    request_row_count: int = Field(ge=0)
    agent_ticket_count_delta: int
    orphan_link_count: int = Field(ge=0)
    self_link_count: int = Field(ge=0)
    linked_targets_exist: bool


class ProcessEvidence(StrictModel):
    loaded_capability_ids: list[str] = Field(default_factory=list)
    tool_call_counts: dict[str, int] = Field(default_factory=dict)
    total_tool_calls: int = Field(ge=0)
    failed_tool_calls: int = Field(ge=0)
    model_requests: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @field_validator("loaded_capability_ids")
    @classmethod
    def normalize_capability_ids(cls, value: list[str]) -> list[str]:
        return sorted(set(value))


class TriageEvalOutput(StrictModel):
    team: Team | None = None
    permitted_teams: list[Team] = Field(default_factory=list)
    urgency: Urgency | None = None
    related_ticket_ids: list[int] = Field(default_factory=list)
    manual_triage: bool = False
    persisted_ticket: TicketRecord | None = None
    receipt: TriageReceipt | None = None
    receipt_consistent: bool | None = None
    consistency_issues: list[str] = Field(default_factory=list)
    persistence: PersistenceEvidence | None = None
    process: ProcessEvidence | None = None

    @field_validator("related_ticket_ids")
    @classmethod
    def normalize_related_ids(cls, value: list[int]) -> list[int]:
        if any(ticket_id <= 0 for ticket_id in value):
            raise ValueError("related ticket IDs must be positive")
        return sorted(set(value))

    @field_validator("permitted_teams")
    @classmethod
    def normalize_permitted_teams(cls, value: list[Team]) -> list[Team]:
        return sorted(set(value), key=str)

    @model_validator(mode="after")
    def expected_team_shape_is_coherent(self) -> TriageEvalOutput:
        if self.team is not None and self.permitted_teams:
            raise ValueError("set either team or permitted_teams, not both")
        return self


class TriageCaseMetadata(StrictModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    dataset_version: str = Field(min_length=1)
    split: EvalSplit
    task_family: TaskFamily
    target_facets: list[ConstructFacet] = Field(min_length=1)
    policy_rule_ids: list[str] = Field(min_length=1)
    difficulty: DifficultyBand
    required_capability_ids: list[str] = Field(default_factory=list)
    evaluator_ids: list[str] = Field(min_length=1)
    predicted_sensitive_mutant_ids: list[str] = Field(default_factory=list)
    negative_control_mutant_ids: list[str] = Field(default_factory=list)
    metamorphic_group_id: str | None = None
    metamorphic_relation: str | None = None
    risk_severity: RiskSeverity
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sentinel: bool = False

    @field_validator(
        "target_facets",
        "policy_rule_ids",
        "required_capability_ids",
        "evaluator_ids",
        "predicted_sensitive_mutant_ids",
        "negative_control_mutant_ids",
    )
    @classmethod
    def reject_duplicate_metadata_values(cls, value: list[object]) -> list[object]:
        if len(value) != len(set(value)):
            raise ValueError("metadata lists may not contain duplicates")
        return value

    @model_validator(mode="after")
    def metamorphic_fields_are_paired(self) -> TriageCaseMetadata:
        if (self.metamorphic_group_id is None) != (self.metamorphic_relation is None):
            raise ValueError("metamorphic_group_id and metamorphic_relation must be set together")
        return self
