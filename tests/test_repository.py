from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from eval_mutation.domain.models import AccountTier, Channel, InboundRequest, Team, Urgency
from eval_mutation.storage.fixtures import load_fixture
from eval_mutation.storage.repository import RepositoryError, TicketRepository


class TicketRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = TicketRepository(Path(self.temp_dir.name) / "tickets.db")
        self.repository.initialize()
        self.repository.seed_tickets(load_fixture("fixtures/demo_tickets.json"))
        self.now = datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        self.request = InboundRequest(
            request_id="request-test-1",
            title="INC-42 still returns 503 for our API calls",
            body="Our production traffic is affected by incident INC-42.",
            customer_id="cust-new",
            submitted_at=self.now,
            channel=Channel.CHAT,
            account_tier=AccountTier.ENTERPRISE,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_search_ranks_distinctive_incident(self) -> None:
        hits = self.repository.search_tickets("INC-42 API 503")
        self.assertTrue(hits)
        self.assertEqual(hits[0].ticket.id, 1001)

    def test_file_is_idempotent_and_preserves_links(self) -> None:
        first = self.repository.file_ticket(
            self.request,
            team=Team.PRODUCT_TECHNICAL,
            urgency=Urgency.P0_CRITICAL,
            summary="Customer affected by INC-42.",
            rationale="Same incident ID as ticket 1001.",
            related_ticket_ids=[1001],
            created_at=self.now,
        )
        second = self.repository.file_ticket(
            self.request,
            team=Team.MANUAL_TRIAGE,
            urgency=Urgency.P3_LOW,
            summary="A conflicting retry must not overwrite state.",
            rationale="Retry.",
            related_ticket_ids=[],
            created_at=self.now,
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.ticket.id, second.ticket.id)
        self.assertEqual(second.ticket.team, Team.PRODUCT_TECHNICAL)
        self.assertEqual(second.linked_ticket_ids, [1001])

    def test_link_rejects_another_requests_ticket(self) -> None:
        with self.assertRaises(RepositoryError):
            self.repository.link_tickets(
                1001,
                [1002],
                request_id=self.request.request_id,
                created_at=self.now,
            )

    def test_list_team_tickets_filters_resolved_by_default(self) -> None:
        tickets = self.repository.list_team_tickets(Team.BILLING_PAYMENTS)
        self.assertEqual([ticket.id for ticket in tickets], [1002])


if __name__ == "__main__":
    unittest.main()
