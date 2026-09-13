from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.models.test import TestModel

from eval_mutation.agent.deps import AgentDeps
from eval_mutation.agent.triage_agent import AgentConfig, build_agent
from eval_mutation.agent.capabilities import load_runbook_capabilities
from eval_mutation.domain.models import InboundRequest, Team, Urgency
from eval_mutation.storage.repository import TicketRepository


class TerminalAgentTests(unittest.TestCase):
    def test_runbooks_are_deferred_and_nonempty(self) -> None:
        capabilities = load_runbook_capabilities()
        self.assertEqual(
            {capability.id for capability in capabilities},
            {"routing-policy", "urgency-policy", "relation-policy"},
        )
        for capability in capabilities:
            self.assertTrue(capability.defer_loading)
            self.assertTrue(capability.get_instructions())

    def test_terminal_output_files_once_and_returns_persisted_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = TicketRepository(Path(temp_dir) / "tickets.db")
            repository.initialize()
            now = datetime(2026, 9, 13, 9, 0, tzinfo=timezone.utc)
            request = InboundRequest(
                request_id="request-terminal-agent",
                title="Please add dark mode",
                body="This is a non-blocking feature request.",
                customer_id="cust-test",
                submitted_at=now,
            )
            model = TestModel(
                call_tools=[],
                custom_output_args={
                    "team": "product_feedback",
                    "urgency": "P3_low",
                    "summary": "Feature request for dark mode.",
                    "rationale": "New non-blocking behavior belongs to product feedback.",
                    "related_ticket_ids": [],
                    "uncertainty_note": None,
                },
            )
            agent = build_agent(AgentConfig(), model=model)
            result = asyncio.run(
                agent.run(
                    "Triage the supplied request.",
                    deps=AgentDeps(
                        repository=repository,
                        request=request,
                        run_id="run-terminal-agent",
                        now=now,
                    ),
                )
            )
            persisted = repository.get_ticket_by_request_id(request.request_id)

        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(result.output.ticket_id, persisted.id)
        self.assertEqual(result.output.team, Team.PRODUCT_FEEDBACK)
        self.assertEqual(result.output.urgency, Urgency.P3_LOW)
        parameters = model.last_model_request_parameters
        self.assertIsNotNone(parameters)
        assert parameters is not None
        self.assertEqual(parameters.output_tools[0].name, "file_ticket")
        function_tool_names = {tool.name for tool in parameters.function_tools}
        self.assertTrue(
            {"search_tickets", "get_ticket", "list_team_tickets", "load_capability"}.issubset(
                function_tool_names
            )
        )
        self.assertNotIn("file_ticket", function_tool_names)


if __name__ == "__main__":
    unittest.main()
