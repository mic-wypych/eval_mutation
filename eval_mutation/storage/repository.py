from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from eval_mutation.domain.models import (
    AuditEvent,
    FilingResult,
    FixtureTicket,
    InboundRequest,
    LinkResult,
    SearchHit,
    Team,
    TicketRecord,
    TicketStatus,
    TicketSummary,
    Urgency,
)


class RepositoryError(RuntimeError):
    """A safe, user-correctable ticket repository error."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    channel TEXT NOT NULL,
    account_tier TEXT NOT NULL,
    team TEXT NOT NULL,
    urgency TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    rationale TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_links (
    source_ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    target_ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL DEFAULT 'related',
    created_at TEXT NOT NULL,
    PRIMARY KEY (source_ticket_id, target_ticket_id),
    CHECK (source_ticket_id <> target_ticket_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    action TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    result_json TEXT,
    success INTEGER NOT NULL,
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tickets_team_status ON tickets(team, status);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_events(run_id, sequence);
"""

_STOPWORDS = {
    "about",
    "after",
    "again",
    "been",
    "from",
    "have",
    "into",
    "issue",
    "that",
    "their",
    "there",
    "this",
    "ticket",
    "with",
}


class TicketRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(_SCHEMA)

    def seed_tickets(self, tickets: Sequence[FixtureTicket]) -> None:
        with self._connection() as connection:
            for ticket in tickets:
                connection.execute(
                    """
                    INSERT INTO tickets (
                        id, request_id, title, body, customer_id, submitted_at,
                        channel, account_tier, team, urgency, status, summary,
                        rationale, source, created_at
                    ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'fixture', ?)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    (
                        ticket.id,
                        ticket.title,
                        ticket.body,
                        ticket.customer_id,
                        ticket.submitted_at.isoformat(),
                        ticket.channel.value,
                        ticket.account_tier.value,
                        ticket.team.value,
                        ticket.urgency.value,
                        ticket.status.value,
                        ticket.summary,
                        ticket.rationale,
                        ticket.submitted_at.isoformat(),
                    ),
                )

    def get_ticket(self, ticket_id: int) -> TicketRecord | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        return self._ticket_from_row(row) if row is not None else None

    def get_ticket_by_request_id(self, request_id: str) -> TicketRecord | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM tickets WHERE request_id = ?", (request_id,)).fetchone()
        return self._ticket_from_row(row) if row is not None else None

    def list_team_tickets(
        self,
        team: Team,
        *,
        status: TicketStatus = TicketStatus.OPEN,
        limit: int = 10,
    ) -> list[TicketSummary]:
        safe_limit = min(max(limit, 1), 25)
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM tickets
                WHERE team = ? AND status = ?
                ORDER BY submitted_at DESC, id DESC
                LIMIT ?
                """,
                (team.value, status.value, safe_limit),
            ).fetchall()
        return [self._summary_from_row(row) for row in rows]

    def search_tickets(
        self,
        query: str,
        *,
        team: Team | None = None,
        status: TicketStatus = TicketStatus.OPEN,
        limit: int = 5,
    ) -> list[SearchHit]:
        terms = self._search_terms(query)
        if not terms:
            return []

        parameters: list[Any] = [status.value]
        sql = "SELECT * FROM tickets WHERE status = ?"
        if team is not None:
            sql += " AND team = ?"
            parameters.append(team.value)

        with self._connection() as connection:
            rows = connection.execute(sql, parameters).fetchall()

        hits: list[SearchHit] = []
        for row in rows:
            title = row["title"].lower()
            body = row["body"].lower()
            summary = row["summary"].lower()
            matched = [term for term in terms if term in title or term in body or term in summary]
            if not matched:
                continue
            score = sum(3 if term in title else 0 for term in matched)
            score += sum(2 if term in summary else 0 for term in matched)
            score += sum(1 if term in body else 0 for term in matched)
            hits.append(
                SearchHit(
                    ticket=self._summary_from_row(row),
                    matched_terms=matched,
                    relevance_score=score,
                )
            )

        hits.sort(key=lambda hit: (-hit.relevance_score, -hit.ticket.id))
        return hits[: min(max(limit, 1), 20)]

    def file_ticket(
        self,
        request: InboundRequest,
        *,
        team: Team,
        urgency: Urgency,
        summary: str,
        rationale: str,
        related_ticket_ids: Sequence[int],
        created_at: datetime,
    ) -> FilingResult:
        related_ids = sorted(set(related_ticket_ids))
        with self._connection() as connection:
            existing_row = connection.execute(
                "SELECT * FROM tickets WHERE request_id = ?", (request.request_id,)
            ).fetchone()
            if existing_row is not None:
                existing = self._ticket_from_row(existing_row)
                return FilingResult(
                    ticket=existing,
                    created=False,
                    linked_ticket_ids=self._list_links(connection, existing.id),
                )

            self._validate_targets(connection, related_ids)
            cursor = connection.execute(
                """
                INSERT INTO tickets (
                    request_id, title, body, customer_id, submitted_at, channel,
                    account_tier, team, urgency, status, summary, rationale,
                    source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, 'agent', ?)
                """,
                (
                    request.request_id,
                    request.title,
                    request.body,
                    request.customer_id,
                    request.submitted_at.isoformat(),
                    request.channel.value,
                    request.account_tier.value,
                    team.value,
                    urgency.value,
                    summary,
                    rationale,
                    created_at.isoformat(),
                ),
            )
            ticket_id = int(cursor.lastrowid)
            for target_id in related_ids:
                connection.execute(
                    """
                    INSERT INTO ticket_links (
                        source_ticket_id, target_ticket_id, relation_type, created_at
                    ) VALUES (?, ?, 'related', ?)
                    """,
                    (ticket_id, target_id, created_at.isoformat()),
                )
            row = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            assert row is not None
            return FilingResult(
                ticket=self._ticket_from_row(row),
                created=True,
                linked_ticket_ids=related_ids,
            )

    def link_tickets(
        self,
        ticket_id: int,
        related_ticket_ids: Sequence[int],
        *,
        request_id: str,
        created_at: datetime,
    ) -> LinkResult:
        related_ids = sorted(set(related_ticket_ids))
        with self._connection() as connection:
            source = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
            if source is None:
                raise RepositoryError(f"ticket {ticket_id} does not exist")
            if source["request_id"] != request_id:
                raise RepositoryError("links may only be added to the ticket created for this request")
            if ticket_id in related_ids:
                raise RepositoryError("a ticket cannot link to itself")
            self._validate_targets(connection, related_ids)
            for target_id in related_ids:
                connection.execute(
                    """
                    INSERT INTO ticket_links (
                        source_ticket_id, target_ticket_id, relation_type, created_at
                    ) VALUES (?, ?, 'related', ?)
                    ON CONFLICT(source_ticket_id, target_ticket_id) DO NOTHING
                    """,
                    (ticket_id, target_id, created_at.isoformat()),
                )
            return LinkResult(ticket_id=ticket_id, linked_ticket_ids=self._list_links(connection, ticket_id))

    def list_links(self, source_ticket_id: int) -> list[int]:
        with self._connection() as connection:
            return self._list_links(connection, source_ticket_id)

    def record_audit_event(
        self,
        *,
        run_id: str,
        action: str,
        arguments: dict[str, Any],
        result: Any | None,
        success: bool,
        created_at: datetime,
        error_code: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    run_id, action, arguments_json, result_json,
                    success, error_code, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    action,
                    json.dumps(arguments, default=str, sort_keys=True),
                    json.dumps(result, default=str, sort_keys=True) if result is not None else None,
                    int(success),
                    error_code,
                    created_at.isoformat(),
                ),
            )

    def list_audit_events(self, run_id: str) -> list[AuditEvent]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
        return [
            AuditEvent(
                sequence=row["sequence"],
                run_id=row["run_id"],
                action=row["action"],
                arguments=json.loads(row["arguments_json"]),
                result=json.loads(row["result_json"]) if row["result_json"] is not None else None,
                success=bool(row["success"]),
                error_code=row["error_code"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    @staticmethod
    def _search_terms(query: str) -> list[str]:
        terms = re.findall(r"[a-z0-9][a-z0-9_.:-]{2,}", query.lower())
        return list(dict.fromkeys(term for term in terms if term not in _STOPWORDS))[:12]

    @staticmethod
    def _validate_targets(connection: sqlite3.Connection, target_ids: Sequence[int]) -> None:
        if not target_ids:
            return
        placeholders = ",".join("?" for _ in target_ids)
        rows = connection.execute(
            f"SELECT id FROM tickets WHERE id IN ({placeholders})",  # noqa: S608 - placeholders are generated
            list(target_ids),
        ).fetchall()
        found = {int(row["id"]) for row in rows}
        missing = sorted(set(target_ids) - found)
        if missing:
            raise RepositoryError(f"related ticket IDs do not exist: {missing}")

    @staticmethod
    def _list_links(connection: sqlite3.Connection, source_ticket_id: int) -> list[int]:
        rows = connection.execute(
            "SELECT target_ticket_id FROM ticket_links WHERE source_ticket_id = ? ORDER BY target_ticket_id",
            (source_ticket_id,),
        ).fetchall()
        return [int(row["target_ticket_id"]) for row in rows]

    @staticmethod
    def _ticket_from_row(row: sqlite3.Row) -> TicketRecord:
        return TicketRecord(
            id=row["id"],
            request_id=row["request_id"],
            title=row["title"],
            body=row["body"],
            customer_id=row["customer_id"],
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
            channel=row["channel"],
            account_tier=row["account_tier"],
            team=row["team"],
            urgency=row["urgency"],
            status=row["status"],
            summary=row["summary"],
            rationale=row["rationale"],
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _summary_from_row(row: sqlite3.Row) -> TicketSummary:
        return TicketSummary(
            id=row["id"],
            title=row["title"],
            customer_id=row["customer_id"],
            team=row["team"],
            urgency=row["urgency"],
            status=row["status"],
            summary=row["summary"],
            submitted_at=datetime.fromisoformat(row["submitted_at"]),
        )
