from __future__ import annotations

from importlib.resources import files

from pydantic_ai.capabilities import Capability


_RUNBOOKS = (
    (
        "routing-policy",
        "Load for team ownership, routing boundaries, precedence, or manual-triage decisions.",
        "routing-policy.md",
    ),
    (
        "urgency-policy",
        "Load for P0-P3 thresholds, impact cues, urgency decoys, and tie-breaking.",
        "urgency-policy.md",
    ),
    (
        "relation-policy",
        "Load before deciding whether existing tickets are genuinely related.",
        "relation-policy.md",
    ),
)


def load_runbook_capabilities() -> tuple[Capability[object], ...]:
    resource_root = files("eval_mutation.agent.runbooks")
    capabilities: list[Capability[object]] = []
    for capability_id, description, filename in _RUNBOOKS:
        instructions = resource_root.joinpath(filename).read_text(encoding="utf-8").strip()
        capabilities.append(
            Capability(
                id=capability_id,
                description=description,
                instructions=instructions,
                defer_loading=True,
            )
        )
    return tuple(capabilities)
