from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from eval_mutation.domain.models import InboundRequest
from eval_mutation.storage.repository import TicketRepository


@dataclass(frozen=True)
class AgentDeps:
    repository: TicketRepository
    request: InboundRequest
    run_id: str
    now: datetime
