from __future__ import annotations

from typing import Any

from pydantic_ai import ModelRetry, RunContext

from eval_mutation.agent.deps import AgentDeps
from eval_mutation.domain.models import (
    FilingResult,
    LinkResult,
    SearchHit,
    Team,
    TicketRecord,
    TicketSummary,
    Urgency,
)
from eval_mutation.storage.repository import RepositoryError


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _audit(
    ctx: RunContext[AgentDeps],
    action: str,
    arguments: dict[str, Any],
    *,
    result: Any | None = None,
    error: Exception | None = None,
) -> None:
    ctx.deps.repository.record_audit_event(
        run_id=ctx.deps.run_id,
        action=action,
        arguments=arguments,
        result=_jsonable(result),
        success=error is None,
        error_code=type(error).__name__ if error is not None else None,
        created_at=ctx.deps.now,
    )


def search_tickets(
    ctx: RunContext[AgentDeps],
    query: str,
    team: Team | None = None,
    limit: int = 5,
) -> list[SearchHit]:
    """Search open existing tickets for plausible relation candidates.

    Args:
        query: Focused incident ID, error code, component, symptom, or earlier-contact cue.
        team: Optional team filter. Omit it when a relation may cross teams.
        limit: Maximum candidates to return, from 1 to 20.
    """

    arguments = {"query": query, "team": team.value if team else None, "limit": limit}
    result = ctx.deps.repository.search_tickets(query, team=team, limit=limit)
    _audit(ctx, "search_tickets", arguments, result=result)
    return result


def get_ticket(ctx: RunContext[AgentDeps], ticket_id: int) -> TicketRecord:
    """Read one existing ticket in full before deciding whether it is related.

    Args:
        ticket_id: Positive ticket ID returned by a search or team listing.
    """

    arguments = {"ticket_id": ticket_id}
    ticket = ctx.deps.repository.get_ticket(ticket_id)
    if ticket is None:
        error = RepositoryError(f"ticket {ticket_id} does not exist")
        _audit(ctx, "get_ticket", arguments, error=error)
        raise ModelRetry(str(error))
    _audit(ctx, "get_ticket", arguments, result=ticket)
    return ticket


def list_team_tickets(
    ctx: RunContext[AgentDeps],
    team: Team,
    limit: int = 10,
) -> list[TicketSummary]:
    """List recent open tickets already assigned to one team.

    Args:
        team: Team whose open queue should be inspected.
        limit: Maximum tickets to return, from 1 to 25.
    """

    arguments = {"team": team.value, "limit": limit}
    result = ctx.deps.repository.list_team_tickets(team, limit=limit)
    _audit(ctx, "list_team_tickets", arguments, result=result)
    return result


def file_ticket(
    ctx: RunContext[AgentDeps],
    team: Team,
    urgency: Urgency,
    summary: str,
    rationale: str,
    related_ticket_ids: list[int] | None = None,
) -> FilingResult:
    """Persist the inbound request as exactly one routed support ticket.

    The inbound request data and idempotency key come from trusted run context. Calling
    this tool again cannot create a duplicate.

    Args:
        team: Single owning team selected under the routing policy.
        urgency: Supported P0-P3 urgency under the urgency policy.
        summary: Concise neutral summary of the actionable request.
        rationale: Facts and relevant policy rule IDs supporting the decision.
        related_ticket_ids: Existing ticket IDs supported by the relation policy.
    """

    relation_ids = related_ticket_ids or []
    arguments = {
        "team": team.value,
        "urgency": urgency.value,
        "summary": summary,
        "rationale": rationale,
        "related_ticket_ids": relation_ids,
    }
    try:
        result = ctx.deps.repository.file_ticket(
            ctx.deps.request,
            team=team,
            urgency=urgency,
            summary=summary,
            rationale=rationale,
            related_ticket_ids=relation_ids,
            created_at=ctx.deps.now,
        )
    except RepositoryError as error:
        _audit(ctx, "file_ticket", arguments, error=error)
        raise ModelRetry(str(error)) from error
    _audit(ctx, "file_ticket", arguments, result=result)
    return result


def link_tickets(
    ctx: RunContext[AgentDeps],
    ticket_id: int,
    related_ticket_ids: list[int],
) -> LinkResult:
    """Add supported relations to the ticket created for the current request.

    Args:
        ticket_id: ID returned by file_ticket for this inbound request.
        related_ticket_ids: Existing tickets that meet the loaded relation policy.
    """

    arguments = {"ticket_id": ticket_id, "related_ticket_ids": related_ticket_ids}
    try:
        result = ctx.deps.repository.link_tickets(
            ticket_id,
            related_ticket_ids,
            request_id=ctx.deps.request.request_id,
            created_at=ctx.deps.now,
        )
    except RepositoryError as error:
        _audit(ctx, "link_tickets", arguments, error=error)
        raise ModelRetry(str(error)) from error
    _audit(ctx, "link_tickets", arguments, result=result)
    return result


TOOL_FUNCTIONS = (search_tickets, get_ticket, list_team_tickets, file_ticket, link_tickets)
