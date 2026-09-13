from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, Literal

import logfire


SendToLogfire = bool | Literal["if-token-present"]


def _environment_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be one of true/false, 1/0, yes/no, or on/off")


def _send_mode() -> SendToLogfire:
    value = os.getenv("LOGFIRE_SEND_TO_LOGFIRE", "false").strip().lower()
    if value == "if-token-present":
        return "if-token-present"
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError("LOGFIRE_SEND_TO_LOGFIRE must be true, false, or if-token-present")


@dataclass(frozen=True)
class ObservabilityConfig:
    enabled: bool = False
    send_to_logfire: SendToLogfire = False
    service_name: str = "eval-mutation"
    environment: str | None = None
    include_content: bool = False
    console: bool = False
    system_metrics: bool = False

    @classmethod
    def from_environment(cls) -> ObservabilityConfig:
        return cls(
            enabled=_environment_bool("LOGFIRE_ENABLED", False),
            send_to_logfire=_send_mode(),
            service_name=os.getenv("LOGFIRE_SERVICE_NAME", "eval-mutation"),
            environment=os.getenv("LOGFIRE_ENVIRONMENT") or None,
            include_content=_environment_bool("LOGFIRE_INCLUDE_CONTENT", False),
            console=_environment_bool("LOGFIRE_CONSOLE", False),
            system_metrics=_environment_bool("LOGFIRE_SYSTEM_METRICS", False),
        )


_configured = False


def configure_observability(config: ObservabilityConfig | None = None) -> bool:
    """Configure Logfire and Pydantic AI instrumentation once per process."""

    global _configured
    if _configured:
        return True

    resolved = config or ObservabilityConfig.from_environment()
    if not resolved.enabled:
        return False

    configure_arguments: dict[str, object] = {
        "send_to_logfire": resolved.send_to_logfire,
        "service_name": resolved.service_name,
        "console": None if resolved.console else False,
        "inspect_arguments": False,
    }
    if resolved.environment is not None:
        configure_arguments["environment"] = resolved.environment

    logfire.configure(**configure_arguments)
    logfire.instrument_pydantic_ai(include_content=resolved.include_content)
    if resolved.system_metrics:
        logfire.instrument_system_metrics()
    _configured = True
    return True


@contextmanager
def triage_span(
    *,
    request_id: str,
    run_id: str,
    model_name: str,
    channel: str,
    account_tier: str,
) -> Iterator[logfire.LogfireSpan | None]:
    """Create the project-level parent span only after explicit configuration."""

    if not _configured:
        yield None
        return

    with logfire.span(
        "triage request {request_id}",
        request_id=request_id,
        run_id=run_id,
        model_name=model_name,
        channel=channel,
        account_tier=account_tier,
        _tags=("ticket-triage",),
    ) as span:
        yield span
