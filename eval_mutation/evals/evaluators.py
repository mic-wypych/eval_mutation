from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from eval_mutation.evals.models import TriageCaseInput, TriageCaseMetadata, TriageEvalOutput


EvalContext = EvaluatorContext[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]


def _expected(ctx: EvalContext) -> TriageEvalOutput:
    if ctx.expected_output is None:
        raise ValueError("triage cases require a typed expected_output")
    return ctx.expected_output


def _team_correct(actual: TriageEvalOutput, expected: TriageEvalOutput) -> bool:
    allowed = set(expected.permitted_teams)
    if expected.team is not None:
        allowed.add(expected.team)
    return actual.team is not None and actual.team in allowed


def _urgency_correct(actual: TriageEvalOutput, expected: TriageEvalOutput) -> bool:
    return expected.urgency is not None and actual.urgency == expected.urgency


def _link_set_exact(actual: TriageEvalOutput, expected: TriageEvalOutput) -> bool:
    return set(actual.related_ticket_ids) == set(expected.related_ticket_ids)


def _safe_escalation(actual: TriageEvalOutput, expected: TriageEvalOutput) -> bool:
    return actual.manual_triage == expected.manual_triage


def _transaction_checks(actual: TriageEvalOutput, metadata: TriageCaseMetadata | None) -> dict[str, bool]:
    state = actual.persistence
    if state is None:
        return {
            "transaction_exactly_once": False,
            "transaction_referential_integrity": False,
            "fixture_unchanged": False,
            "fixture_hash_matches": False,
        }
    return {
        "transaction_exactly_once": (
            state.request_row_count == 1
            and state.agent_ticket_count_delta == 1
            and state.ticket_count_after == state.ticket_count_before + 1
        ),
        "transaction_referential_integrity": (
            state.orphan_link_count == 0
            and state.self_link_count == 0
            and state.linked_targets_exist
        ),
        "fixture_unchanged": state.fixture_state_unchanged,
        "fixture_hash_matches": (
            metadata is not None and state.fixture_sha256 == metadata.fixture_sha256
        ),
    }


class VersionedEvaluator:
    def get_evaluator_version(self) -> str:
        return "v1"


@dataclass(repr=False)
class TeamAssignment(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, EvaluationReason]:
        expected = _expected(ctx)
        correct = _team_correct(ctx.output, expected)
        allowed = expected.permitted_teams or ([expected.team] if expected.team is not None else [])
        return {
            "team_correct": EvaluationReason(
                correct,
                f"expected one of {[str(team) for team in allowed]}; actual={ctx.output.team}",
            )
        }


@dataclass(repr=False)
class UrgencyAssignment(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, EvaluationReason]:
        expected = _expected(ctx)
        return {
            "urgency_correct": EvaluationReason(
                _urgency_correct(ctx.output, expected),
                f"expected={expected.urgency}; actual={ctx.output.urgency}",
            )
        }


@dataclass(repr=False)
class LinkSet(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, bool | float | EvaluationReason]:
        expected_ids = set(_expected(ctx).related_ticket_ids)
        actual_ids = set(ctx.output.related_ticket_ids)
        output: dict[str, bool | float | EvaluationReason] = {
            "link_set_exact": EvaluationReason(
                actual_ids == expected_ids,
                f"expected={sorted(expected_ids)}; actual={sorted(actual_ids)}",
            )
        }
        if expected_ids or actual_ids:
            output["link_precision"] = len(expected_ids & actual_ids) / len(actual_ids) if actual_ids else 0.0
            output["link_recall"] = len(expected_ids & actual_ids) / len(expected_ids) if expected_ids else 1.0
        return output


@dataclass(repr=False)
class SafeEscalation(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, EvaluationReason]:
        expected = _expected(ctx)
        return {
            "safe_escalation": EvaluationReason(
                _safe_escalation(ctx.output, expected),
                f"expected manual_triage={expected.manual_triage}; actual={ctx.output.manual_triage}",
            )
        }


@dataclass(repr=False)
class TransactionIntegrity(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, bool | EvaluationReason]:
        checks = _transaction_checks(ctx.output, ctx.metadata)
        return {
            **checks,
            "transaction_valid": EvaluationReason(
                all(checks.values()),
                "failed=" + ",".join(name for name, value in checks.items() if not value)
                if not all(checks.values())
                else "exactly one valid filing; fixture state preserved",
            ),
        }


@dataclass(repr=False)
class ReceiptConsistency(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, EvaluationReason]:
        return {
            "receipt_consistent": EvaluationReason(
                ctx.output.receipt_consistent is True,
                "; ".join(ctx.output.consistency_issues) or "receipt matches persistent state",
            )
        }


@dataclass(repr=False)
class PolicyUse(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, bool | str | EvaluationReason]:
        required = set(ctx.metadata.required_capability_ids if ctx.metadata is not None else [])
        process = ctx.output.process
        loaded = set(process.loaded_capability_ids if process is not None else [])
        if not required:
            return {"policy_use_applicability": "not_required"}
        missing = sorted(required - loaded)
        return {
            "policy_use": EvaluationReason(
                not missing,
                f"required={sorted(required)}; loaded={sorted(loaded)}; missing={missing}",
            )
        }


@dataclass(repr=False)
class ToolProcessMetrics(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, int | str]:
        process = ctx.output.process
        if process is None:
            return {"process_evidence": "missing"}
        return {
            "model_requests": process.model_requests,
            "tool_calls_total": process.total_tool_calls,
            "tool_calls_failed": process.failed_tool_calls,
            "ticket_searches": process.tool_call_counts.get("search_tickets", 0),
            "ticket_reads": process.tool_call_counts.get("get_ticket", 0),
            "team_list_reads": process.tool_call_counts.get("list_team_tickets", 0),
            "capability_loads": process.tool_call_counts.get("load_capability", 0),
            "filing_calls": process.tool_call_counts.get("file_ticket", 0),
        }


@dataclass(repr=False)
class IntegratedSuccess(VersionedEvaluator, Evaluator[TriageCaseInput, TriageEvalOutput, TriageCaseMetadata]):
    def evaluate(self, ctx: EvalContext) -> dict[str, EvaluationReason]:
        expected = _expected(ctx)
        checks = {
            "team": _team_correct(ctx.output, expected),
            "urgency": _urgency_correct(ctx.output, expected),
            "links": _link_set_exact(ctx.output, expected),
            "safe_escalation": _safe_escalation(ctx.output, expected),
            "receipt": ctx.output.receipt_consistent is True,
            "transaction": all(_transaction_checks(ctx.output, ctx.metadata).values()),
        }
        required = set(ctx.metadata.required_capability_ids if ctx.metadata is not None else [])
        if required:
            loaded = set(ctx.output.process.loaded_capability_ids if ctx.output.process else [])
            checks["policy_use"] = required <= loaded
        failures = [name for name, passed in checks.items() if not passed]
        return {
            "integrated_success": EvaluationReason(
                not failures,
                f"failed={failures}" if failures else "all applicable checks passed",
            )
        }


DEFAULT_EVALUATORS = (
    TeamAssignment(),
    UrgencyAssignment(),
    LinkSet(),
    SafeEscalation(),
    TransactionIntegrity(),
    ReceiptConsistency(),
    PolicyUse(),
    ToolProcessMetrics(),
    IntegratedSuccess(),
)

CUSTOM_EVALUATOR_TYPES = tuple(type(evaluator) for evaluator in DEFAULT_EVALUATORS)
