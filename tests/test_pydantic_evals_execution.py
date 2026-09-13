from __future__ import annotations

import asyncio
import unittest

from pydantic_ai.models.test import TestModel

from eval_mutation.agent.triage_agent import AgentConfig, build_agent
from eval_mutation.evals import TriageEvalTask, load_dataset


class PydanticEvalsExecutionTests(unittest.TestCase):
    def test_one_case_runs_through_dataset_task_and_all_evaluators(self) -> None:
        dataset = load_dataset("datasets/development.yaml")
        dataset.cases = [dataset.cases[0]]
        config = AgentConfig()
        model = TestModel(
            call_tools=[],
            custom_output_args={
                "team": "product_feedback",
                "urgency": "P3_low",
                "summary": "Feature request for scheduled PDF exports.",
                "rationale": "A new non-blocking capability is product feedback.",
                "related_ticket_ids": [],
                "uncertainty_note": None,
            },
        )
        task = TriageEvalTask(config=config, agent=build_agent(config, model=model))

        report = asyncio.run(dataset.evaluate(task, progress=False))

        self.assertFalse(report.failures)
        self.assertEqual(len(report.cases), 1)
        result = report.cases[0]
        for assertion in (
            "team_correct",
            "urgency_correct",
            "link_set_exact",
            "safe_escalation",
            "transaction_valid",
            "receipt_consistent",
            "integrated_success",
        ):
            self.assertIn(assertion, result.assertions)
            self.assertTrue(result.assertions[assertion].value, assertion)
        self.assertEqual(result.labels["policy_use_applicability"].value, "not_required")
        self.assertEqual(result.scores["filing_calls"].value, 1)


if __name__ == "__main__":
    unittest.main()
