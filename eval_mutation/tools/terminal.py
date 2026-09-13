from __future__ import annotations

from pydantic_ai import ModelRetry, RunContext

from eval_mutation.agent.deps import AgentDeps
from eval_mutation.domain.models import Team, TriageReceipt, Urgency
from eval_mutation.storage.repository import RepositoryError
from eval_mutation.tools.ticketing import _audit


def file_ticket_output(
    ctx: RunContext[AgentDeps],
    team: Team,
    urgency: Urgency,
    summary: str,
    rationale: str,
    related_ticket_ids: list[int] | None = None,
    uncertainty_note: str | None = None,
) -> TriageReceipt:
    """File the inbound request and finish with a receipt matching persistent state.

    This is the terminal action. Call it once after any needed policy loading, searching,
    and ticket inspection. The trusted inbound request and idempotency key come from run
    context, so retries cannot create duplicate tickets.

    Args:
        team: Single owning team selected under the routing policy.
        urgency: Supported P0-P3 urgency under the urgency policy.
        summary: Concise neutral summary of the actionable request.
        rationale: Request facts and relevant policy rule IDs supporting the decision.
        related_ticket_ids: Existing ticket IDs supported by the relation policy.
        uncertainty_note: Required explanation when team is manual_triage; otherwise omit.
    """

    relation_ids = related_ticket_ids or []
    arguments = {
        "team": team.value,
        "urgency": urgency.value,
        "summary": summary,
        "rationale": rationale,
        "related_ticket_ids": relation_ids,
        "uncertainty_note": uncertainty_note,
    }
    if team is Team.MANUAL_TRIAGE and not uncertainty_note:
        error = RepositoryError("manual_triage requires an uncertainty_note")
        _audit(ctx, "file_ticket", arguments, error=error)
        raise ModelRetry(str(error))
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

    receipt = TriageReceipt(
        ticket_id=result.ticket.id,
        team=result.ticket.team,
        urgency=result.ticket.urgency,
        related_ticket_ids=result.linked_ticket_ids,
        summary=result.ticket.summary,
        rationale=result.ticket.rationale,
        uncertainty_note=uncertainty_note,
    )
    _audit(ctx, "file_ticket", arguments, result=receipt)
    return receipt
