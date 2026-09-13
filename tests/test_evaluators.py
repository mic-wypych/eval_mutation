from __future__ import annotations

import unittest
from types import SimpleNamespace

from eval_mutation.domain.models import Team, Urgency
from eval_mutation.evals.evaluators import (
    IntegratedSuccess,
    LinkSet,
    PolicyUse,
    ReceiptConsistency,
    SafeEscalation,
    TeamAssignment,
    ToolProcessMetrics,
    TransactionIntegrity,
    UrgencyAssignment,
)
from eval_mutation.evals.models import (
    ConstructFacet,
    DifficultyBand,
    EvalSplit,
    PersistenceEvidence,
    ProcessEvidence,
    RiskSeverity,
    TaskFamily,
    TriageCaseMetadata,
    TriageEvalOutput,
)


FIXTURE_HASH = "a" * 64


def metadata(*, required_capabilities: list[str] | None = None) -> TriageCaseMetadata:
    return TriageCaseMetadata(
        case_id="test-case",
        dataset_version="test",
        split=EvalSplit.DEVELOPMENT,
        task_family=TaskFamily.T8_INTEGRATED,
        target_facets=[ConstructFacet.F1_ROUTING],
        policy_rule_ids=["R-ID-1"],
        difficulty=DifficultyBand.INTEGRATED,
        required_capability_ids=required_capabilities or [],
        evaluator_ids=["integrated_success"],
        risk_severity=RiskSeverity.MEDIUM,
        fixture_sha256=FIXTURE_HASH,
    )


def expected() -> TriageEvalOutput:
    return TriageEvalOutput(
        team=Team.IDENTITY_ACCESS,
        urgency=Urgency.P2_NORMAL,
        related_ticket_ids=[1006],
        manual_triage=False,
    )


def actual(*, loaded_capabilities: list[str] | None = None) -> TriageEvalOutput:
    return TriageEvalOutput(
        team=Team.IDENTITY_ACCESS,
        urgency=Urgency.P2_NORMAL,
        related_ticket_ids=[1006],
        manual_triage=False,
        receipt_consistent=True,
        persistence=PersistenceEvidence(
            fixture_sha256=FIXTURE_HASH,
            fixture_state_unchanged=True,
            ticket_count_before=6,
            ticket_count_after=7,
            request_row_count=1,
            agent_ticket_count_delta=1,
            orphan_link_count=0,
            self_link_count=0,
            linked_targets_exist=True,
        ),
        process=ProcessEvidence(
            loaded_capability_ids=loaded_capabilities or [],
            tool_call_counts={"search_tickets": 1, "get_ticket": 1, "file_ticket": 1},
            total_tool_calls=3,
            failed_tool_calls=0,
            model_requests=3,
            input_tokens=200,
            output_tokens=80,
        ),
    )


def context(
    output: TriageEvalOutput | None = None,
    *,
    expected_output: TriageEvalOutput | None = None,
    case_metadata: TriageCaseMetadata | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        output=output or actual(),
        expected_output=expected_output or expected(),
        metadata=case_metadata or metadata(),
    )


class DeterministicEvaluatorTests(unittest.TestCase):
    def test_assignment_and_escalation_evaluators_detect_wrong_values(self) -> None:
        correct_ctx = context()
        self.assertTrue(TeamAssignment().evaluate(correct_ctx)["team_correct"].value)
        self.assertTrue(UrgencyAssignment().evaluate(correct_ctx)["urgency_correct"].value)
        self.assertTrue(SafeEscalation().evaluate(correct_ctx)["safe_escalation"].value)

        wrong = actual()
        wrong.team = Team.BILLING_PAYMENTS
        wrong.urgency = Urgency.P0_CRITICAL
        wrong.manual_triage = True
        wrong_ctx = context(wrong)
        self.assertFalse(TeamAssignment().evaluate(wrong_ctx)["team_correct"].value)
        self.assertFalse(UrgencyAssignment().evaluate(wrong_ctx)["urgency_correct"].value)
        self.assertFalse(SafeEscalation().evaluate(wrong_ctx)["safe_escalation"].value)

    def test_team_assignment_accepts_explicit_permitted_set(self) -> None:
        permitted = TriageEvalOutput(
            permitted_teams=[Team.IDENTITY_ACCESS, Team.MANUAL_TRIAGE],
            urgency=Urgency.P2_NORMAL,
        )
        result = TeamAssignment().evaluate(context(expected_output=permitted))
        self.assertTrue(result["team_correct"].value)

    def test_link_evaluator_reports_exact_precision_and_recall(self) -> None:
        partly_wrong = actual()
        partly_wrong.related_ticket_ids = [1005, 1006]
        result = LinkSet().evaluate(context(partly_wrong))
        self.assertFalse(result["link_set_exact"].value)
        self.assertEqual(result["link_precision"], 0.5)
        self.assertEqual(result["link_recall"], 1.0)

        empty = TriageEvalOutput(team=Team.IDENTITY_ACCESS, urgency=Urgency.P2_NORMAL)
        empty_expected = TriageEvalOutput(team=Team.IDENTITY_ACCESS, urgency=Urgency.P2_NORMAL)
        empty_result = LinkSet().evaluate(context(empty, expected_output=empty_expected))
        self.assertEqual(set(empty_result), {"link_set_exact"})

    def test_transaction_and_receipt_evaluators_detect_corruption(self) -> None:
        correct_ctx = context()
        transaction = TransactionIntegrity().evaluate(correct_ctx)
        self.assertTrue(transaction["transaction_valid"].value)
        self.assertTrue(ReceiptConsistency().evaluate(correct_ctx)["receipt_consistent"].value)

        corrupt = actual()
        assert corrupt.persistence is not None
        corrupt.persistence.request_row_count = 0
        corrupt.receipt_consistent = False
        corrupt.consistency_issues = ["receipt team does not match persistent state"]
        corrupt_ctx = context(corrupt)
        self.assertFalse(TransactionIntegrity().evaluate(corrupt_ctx)["transaction_valid"].value)
        self.assertFalse(ReceiptConsistency().evaluate(corrupt_ctx)["receipt_consistent"].value)

    def test_policy_use_is_assertion_only_when_required(self) -> None:
        not_required = PolicyUse().evaluate(context())
        self.assertEqual(not_required, {"policy_use_applicability": "not_required"})

        required_metadata = metadata(required_capabilities=["routing-policy", "urgency-policy"])
        missing = PolicyUse().evaluate(context(case_metadata=required_metadata))
        self.assertFalse(missing["policy_use"].value)
        loaded = actual(loaded_capabilities=["routing-policy", "urgency-policy"])
        present = PolicyUse().evaluate(context(loaded, case_metadata=required_metadata))
        self.assertTrue(present["policy_use"].value)

    def test_tool_metrics_and_integrated_success(self) -> None:
        metrics = ToolProcessMetrics().evaluate(context())
        self.assertEqual(metrics["ticket_searches"], 1)
        self.assertEqual(metrics["filing_calls"], 1)
        self.assertTrue(IntegratedSuccess().evaluate(context())["integrated_success"].value)

        wrong = actual()
        wrong.related_ticket_ids = []
        result = IntegratedSuccess().evaluate(context(wrong))["integrated_success"]
        self.assertFalse(result.value)
        self.assertIn("links", result.reason or "")

    def test_missing_runtime_evidence_fails_integrated_checks(self) -> None:
        malformed = TriageEvalOutput(
            team=Team.IDENTITY_ACCESS,
            urgency=Urgency.P2_NORMAL,
            related_ticket_ids=[1006],
        )
        result = IntegratedSuccess().evaluate(context(malformed))["integrated_success"]
        self.assertFalse(result.value)


if __name__ == "__main__":
    unittest.main()
