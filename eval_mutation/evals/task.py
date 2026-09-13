from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic_ai import Agent
from pydantic_evals.dataset import increment_eval_metric, set_eval_attribute

from eval_mutation.agent.deps import AgentDeps
from eval_mutation.agent.triage_agent import AgentConfig
from eval_mutation.domain.models import Team, TriageReceipt
from eval_mutation.evals.models import (
    PersistenceEvidence,
    ProcessEvidence,
    TriageCaseInput,
    TriageEvalOutput,
)
from eval_mutation.service import run_triage
from eval_mutation.storage.fixtures import load_fixture
from eval_mutation.storage.repository import TicketRepository


@dataclass(frozen=True)
class _DatabaseSnapshot:
    ticket_count: int
    agent_ticket_count: int
    request_row_count: int
    orphan_link_count: int
    self_link_count: int
    fixture_state_sha256: str


def _database_snapshot(path: Path, request_id: str) -> _DatabaseSnapshot:
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        ticket_count = int(connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])
        agent_ticket_count = int(
            connection.execute("SELECT COUNT(*) FROM tickets WHERE source = 'agent'").fetchone()[0]
        )
        request_row_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM tickets WHERE request_id = ?", (request_id,)
            ).fetchone()[0]
        )
        orphan_link_count = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM ticket_links AS links
                LEFT JOIN tickets AS source ON source.id = links.source_ticket_id
                LEFT JOIN tickets AS target ON target.id = links.target_ticket_id
                WHERE source.id IS NULL OR target.id IS NULL
                """
            ).fetchone()[0]
        )
        self_link_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM ticket_links WHERE source_ticket_id = target_ticket_id"
            ).fetchone()[0]
        )
        fixture_rows = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM tickets WHERE source = 'fixture' ORDER BY id"
            ).fetchall()
        ]
    fixture_bytes = json.dumps(
        fixture_rows, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return _DatabaseSnapshot(
        ticket_count=ticket_count,
        agent_ticket_count=agent_ticket_count,
        request_row_count=request_row_count,
        orphan_link_count=orphan_link_count,
        self_link_count=self_link_count,
        fixture_state_sha256=hashlib.sha256(fixture_bytes).hexdigest(),
    )


def _loaded_capability_ids(messages: list[dict[str, Any]]) -> list[str]:
    loaded: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("tool_name") == "load_capability":
                arguments = value.get("args", value.get("arguments"))
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = None
                if isinstance(arguments, dict) and isinstance(arguments.get("id"), str):
                    loaded.add(arguments["id"])
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(messages)
    return sorted(loaded)


@dataclass
class TriageEvalTask:
    """Run one eval case against an isolated, freshly seeded SQLite database."""

    config: AgentConfig
    project_root: Path = Path(".")
    agent: Agent[AgentDeps, TriageReceipt] | None = None

    async def __call__(self, case_input: TriageCaseInput) -> TriageEvalOutput:
        if case_input.injected_tool_condition is not None:
            raise NotImplementedError("injected tool conditions are reserved for robustness cases")

        root = self.project_root.resolve()
        fixture_path = (root / case_input.fixture_path).resolve()
        if not fixture_path.is_relative_to(root):
            raise ValueError("fixture path resolves outside project root")
        fixture_sha256 = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        fixture_tickets = load_fixture(fixture_path)

        with tempfile.TemporaryDirectory(prefix="eval-mutation-") as temp_dir:
            repository = TicketRepository(Path(temp_dir) / "tickets.db")
            repository.initialize()
            repository.seed_tickets(fixture_tickets)
            before = _database_snapshot(repository.path, case_input.request.request_id)

            result = await run_triage(
                case_input.request,
                repository,
                agent=self.agent,
                config=self.config,
                run_id=f"eval-{case_input.request.request_id}",
                now=case_input.frozen_at,
            )
            after = _database_snapshot(repository.path, case_input.request.request_id)

        action_counts = Counter(event.action for event in result.audit_events)
        loaded_capabilities = _loaded_capability_ids(result.messages)
        for _ in loaded_capabilities:
            action_counts["load_capability"] += 1

        usage = result.usage
        audited_tool_calls = sum(action_counts.values())
        process = ProcessEvidence(
            loaded_capability_ids=loaded_capabilities,
            tool_call_counts=dict(sorted(action_counts.items())),
            # Pydantic AI usage can omit terminal ToolOutput calls. The independent
            # audit/message evidence is authoritative when it observes more calls.
            total_tool_calls=max(int(usage.get("tool_calls", 0)), audited_tool_calls),
            failed_tool_calls=sum(not event.success for event in result.audit_events),
            model_requests=int(usage.get("requests", 0)),
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )
        persistence = PersistenceEvidence(
            fixture_sha256=fixture_sha256,
            fixture_state_unchanged=(before.fixture_state_sha256 == after.fixture_state_sha256),
            ticket_count_before=before.ticket_count,
            ticket_count_after=after.ticket_count,
            request_row_count=after.request_row_count,
            agent_ticket_count_delta=after.agent_ticket_count - before.agent_ticket_count,
            orphan_link_count=after.orphan_link_count,
            self_link_count=after.self_link_count,
            linked_targets_exist=(after.orphan_link_count == 0),
        )

        set_eval_attribute("fixture_sha256", fixture_sha256)
        set_eval_attribute("model_name", self.config.model_name)
        increment_eval_metric("model_requests", process.model_requests)
        increment_eval_metric("tool_calls", process.total_tool_calls)
        increment_eval_metric("input_tokens", process.input_tokens)
        increment_eval_metric("output_tokens", process.output_tokens)

        persisted = result.persisted_ticket
        return TriageEvalOutput(
            team=persisted.team if persisted is not None else None,
            urgency=persisted.urgency if persisted is not None else None,
            related_ticket_ids=result.persisted_link_ids,
            manual_triage=(persisted is not None and persisted.team is Team.MANUAL_TRIAGE),
            persisted_ticket=persisted,
            receipt=result.receipt,
            receipt_consistent=result.consistent,
            consistency_issues=result.consistency_issues,
            persistence=persistence,
            process=process,
        )
