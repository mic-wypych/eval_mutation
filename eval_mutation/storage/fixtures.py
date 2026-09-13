from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from eval_mutation.domain.models import FixtureTicket


_FIXTURE_ADAPTER = TypeAdapter(list[FixtureTicket])


def load_fixture(path: str | Path) -> list[FixtureTicket]:
    """Load and validate a versioned JSON ticket fixture."""

    fixture_path = Path(path)
    return _FIXTURE_ADAPTER.validate_python(json.loads(fixture_path.read_text(encoding="utf-8")))
