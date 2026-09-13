from __future__ import annotations

import asyncio
import hashlib
import unittest
from pathlib import Path

from pydantic_ai.models.test import TestModel

from eval_mutation.agent.triage_agent import AgentConfig, build_agent
from eval_mutation.evals import TaskFamily, TriageEvalTask, load_dataset


class EvalHarnessTests(unittest.TestCase):
    def test_development_dataset_is_typed_and_covers_every_family(self) -> None:
        dataset = load_dataset("datasets/development.yaml")
        self.assertEqual(len(dataset.cases), 8)
        self.assertEqual(
            {case.metadata.task_family for case in dataset.cases if case.metadata is not None},
            set(TaskFamily),
        )
        fixture_hash = hashlib.sha256(Path("fixtures/demo_tickets.json").read_bytes()).hexdigest()
        for case in dataset.cases:
            self.assertEqual(case.name, case.metadata.case_id)
            self.assertEqual(case.metadata.fixture_sha256, fixture_hash)
            self.assertIsNotNone(case.expected_output)
            self.assertIsNone(case.expected_output.persistence)
            self.assertIsNone(case.expected_output.process)

    def test_task_adapter_resets_fixture_for_every_execution(self) -> None:
        case = load_dataset("datasets/development.yaml").cases[0]
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
        config = AgentConfig()
        task = TriageEvalTask(config=config, agent=build_agent(config, model=model))

        first = asyncio.run(task(case.inputs))
        second = asyncio.run(task(case.inputs))

        for output in (first, second):
            self.assertEqual(output.team.value, "product_feedback")
            self.assertIsNotNone(output.persistence)
            assert output.persistence is not None
            self.assertEqual(output.persistence.ticket_count_before, 6)
            self.assertEqual(output.persistence.ticket_count_after, 7)
            self.assertEqual(output.persistence.request_row_count, 1)
            self.assertEqual(output.persistence.agent_ticket_count_delta, 1)
            self.assertTrue(output.persistence.fixture_state_unchanged)
            self.assertTrue(output.receipt_consistent)
        self.assertEqual(first.receipt.ticket_id, second.receipt.ticket_id)


if __name__ == "__main__":
    unittest.main()
