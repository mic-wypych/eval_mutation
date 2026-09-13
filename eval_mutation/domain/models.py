from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Team(StrEnum):
    IDENTITY_ACCESS = "identity_access"
    BILLING_PAYMENTS = "billing_payments"
    PRODUCT_TECHNICAL = "product_technical"
    SECURITY_PRIVACY = "security_privacy"
    PRODUCT_FEEDBACK = "product_feedback"
    MANUAL_TRIAGE = "manual_triage"


class Urgency(StrEnum):
    P0_CRITICAL = "P0_critical"
    P1_HIGH = "P1_high"
    P2_NORMAL = "P2_normal"
    P3_LOW = "P3_low"


class Channel(StrEnum):
    EMAIL = "email"
    CHAT = "chat"
    MONITORING = "monitoring"
    INTERNAL = "internal"


class AccountTier(StrEnum):
    STANDARD = "standard"
    ENTERPRISE = "enterprise"


class TicketStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class InboundRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10_000)
    customer_id: str = Field(min_length=1, max_length=100)
    submitted_at: datetime
    channel: Channel = Channel.EMAIL
    account_tier: AccountTier = AccountTier.STANDARD


class FixtureTicket(StrictModel):
    id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10_000)
    customer_id: str = Field(min_length=1, max_length=100)
    submitted_at: datetime
    channel: Channel
    account_tier: AccountTier
    team: Team
    urgency: Urgency
    status: TicketStatus = TicketStatus.OPEN
    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=2_000)


class TicketRecord(StrictModel):
    id: int
    request_id: str | None
    title: str
    body: str
    customer_id: str
    submitted_at: datetime
    channel: Channel
    account_tier: AccountTier
    team: Team
    urgency: Urgency
    status: TicketStatus
    summary: str
    rationale: str
    source: str
    created_at: datetime


class TicketSummary(StrictModel):
    id: int
    title: str
    customer_id: str
    team: Team
    urgency: Urgency
    status: TicketStatus
    summary: str
    submitted_at: datetime


class SearchHit(StrictModel):
    ticket: TicketSummary
    matched_terms: list[str]
    relevance_score: int


class FilingResult(StrictModel):
    ticket: TicketRecord
    created: bool
    linked_ticket_ids: list[int]


class LinkResult(StrictModel):
    ticket_id: int
    linked_ticket_ids: list[int]


class TriageReceipt(StrictModel):
    ticket_id: int = Field(gt=0)
    team: Team
    urgency: Urgency
    related_ticket_ids: list[int] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=500)
    rationale: str = Field(min_length=1, max_length=2_000)
    uncertainty_note: str | None = Field(default=None, max_length=1_000)

    @field_validator("related_ticket_ids")
    @classmethod
    def normalize_related_ids(cls, value: list[int]) -> list[int]:
        if any(ticket_id <= 0 for ticket_id in value):
            raise ValueError("related ticket IDs must be positive")
        return sorted(set(value))


class AuditEvent(StrictModel):
    sequence: int
    run_id: str
    action: str
    arguments: dict[str, Any]
    result: Any | None
    success: bool
    error_code: str | None
    created_at: datetime


class TriageRunResult(StrictModel):
    run_id: str
    receipt: TriageReceipt
    persisted_ticket: TicketRecord | None
    persisted_link_ids: list[int]
    consistent: bool
    consistency_issues: list[str]
    usage: dict[str, Any]
    messages: list[dict[str, Any]]
    audit_events: list[AuditEvent]
