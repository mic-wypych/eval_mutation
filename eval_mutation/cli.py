from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from eval_mutation.agent.triage_agent import AgentConfig
from eval_mutation.domain.models import AccountTier, Channel, InboundRequest
from eval_mutation.observability import configure_observability
from eval_mutation.service import run_triage
from eval_mutation.storage.fixtures import load_fixture
from eval_mutation.storage.repository import TicketRepository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the eval-mutation ticket-triage agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-db", help="Initialize a SQLite ticket store.")
    init_parser.add_argument("--db", type=Path, default=Path("tickets.db"))
    init_parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("fixtures/demo_tickets.json"),
        help="JSON fixture to seed; pass --empty to skip it.",
    )
    init_parser.add_argument("--empty", action="store_true")

    triage_parser = subparsers.add_parser("triage", help="Triage and persist one request.")
    triage_parser.add_argument("--db", type=Path, default=Path("tickets.db"))
    triage_parser.add_argument("--request-id", default=None)
    triage_parser.add_argument("--title", required=True)
    triage_parser.add_argument("--body", required=True)
    triage_parser.add_argument("--customer-id", required=True)
    triage_parser.add_argument("--channel", choices=[item.value for item in Channel], default="email")
    triage_parser.add_argument(
        "--account-tier", choices=[item.value for item in AccountTier], default="standard"
    )
    triage_parser.add_argument("--submitted-at", default=None, help="ISO-8601 timestamp; defaults to now.")
    triage_parser.add_argument("--model", default=None)
    triage_parser.add_argument("--base-url", default=None)
    triage_parser.add_argument("--max-tokens", type=int, default=None)
    triage_parser.add_argument("--request-limit", type=int, default=None)
    triage_parser.add_argument("--tool-calls-limit", type=int, default=None)
    triage_parser.add_argument("--timeout-seconds", type=float, default=None)
    triage_parser.add_argument("--trace-out", type=Path, default=None)
    return parser


def _initialize(args: argparse.Namespace) -> int:
    repository = TicketRepository(args.db)
    repository.initialize()
    seeded = 0
    if not args.empty:
        tickets = load_fixture(args.fixture)
        repository.seed_tickets(tickets)
        seeded = len(tickets)
    print(json.dumps({"database": str(args.db), "fixture_tickets_seen": seeded}, indent=2))
    return 0


async def _triage(args: argparse.Namespace, *, observability_enabled: bool = False) -> int:
    repository = TicketRepository(args.db)
    repository.initialize()
    submitted_at = (
        datetime.fromisoformat(args.submitted_at) if args.submitted_at else datetime.now(timezone.utc)
    )
    request = InboundRequest(
        request_id=args.request_id or f"request-{uuid4().hex}",
        title=args.title,
        body=args.body,
        customer_id=args.customer_id,
        submitted_at=submitted_at,
        channel=args.channel,
        account_tier=args.account_tier,
    )
    config = AgentConfig.from_environment()
    if args.model is not None:
        config.model_name = args.model
    if args.base_url is not None:
        config.base_url = args.base_url
    if args.max_tokens is not None:
        config.max_tokens = args.max_tokens
    if args.request_limit is not None:
        config.request_limit = args.request_limit
    if args.tool_calls_limit is not None:
        config.tool_calls_limit = args.tool_calls_limit
    if args.timeout_seconds is not None:
        config.timeout_seconds = args.timeout_seconds

    print(
        "[eval-mutation] triage started "
        f"request_id={request.request_id} model={config.model_name} db={args.db} "
        f"request_timeout={config.timeout_seconds:g}s "
        f"observability={'enabled' if observability_enabled else 'disabled'}",
        file=sys.stderr,
        flush=True,
    )
    result = await run_triage(request, repository, config=config)
    print(result.model_dump_json(indent=2, exclude={"messages"}))
    if args.trace_out is not None:
        args.trace_out.parent.mkdir(parents=True, exist_ok=True)
        args.trace_out.write_text(
            json.dumps(
                {
                    "run_id": result.run_id,
                    "messages": result.messages,
                    "audit_events": [event.model_dump(mode="json") for event in result.audit_events],
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
    return 0 if result.consistent else 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "init-db":
        return _initialize(args)
    observability_enabled = configure_observability()
    return asyncio.run(_triage(args, observability_enabled=observability_enabled))
