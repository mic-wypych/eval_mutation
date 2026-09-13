from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent, ToolOutput
from pydantic_ai.models import Model
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.profiles import merge_profile
from pydantic_ai.profiles.openai import OpenAIModelProfile
from pydantic_ai.settings import ModelSettings

from eval_mutation.agent.capabilities import load_runbook_capabilities
from eval_mutation.agent.deps import AgentDeps
from eval_mutation.agent.instructions import BASE_INSTRUCTIONS
from eval_mutation.domain.models import TriageReceipt
from eval_mutation.tools.terminal import file_ticket_output
from eval_mutation.tools.ticketing import get_ticket, list_team_tickets, search_tickets


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = Field(default="gemma4:e4b", min_length=1)
    base_url: str = "http://localhost:11434/v1"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    thinking: bool = False
    seed: int = 0
    max_tokens: int = Field(default=2_048, gt=0)
    request_limit: int = Field(default=8, gt=0)
    tool_calls_limit: int = Field(default=12, gt=0)
    timeout_seconds: float = Field(default=120.0, gt=0)

    @classmethod
    def from_environment(cls) -> AgentConfig:
        return cls(
            model_name=os.getenv("OLLAMA_MODEL", cls.model_fields["model_name"].default),
            base_url=os.getenv("OLLAMA_BASE_URL", cls.model_fields["base_url"].default),
        )


def build_ollama_model(config: AgentConfig) -> OllamaModel:
    provider = OllamaProvider(base_url=config.base_url)
    profile = merge_profile(
        provider.model_profile(config.model_name),
        OpenAIModelProfile(openai_chat_supports_max_completion_tokens=False),
    )
    return OllamaModel(config.model_name, provider=provider, profile=profile)


def build_agent(
    config: AgentConfig | None = None,
    *,
    model: Model | None = None,
) -> Agent[AgentDeps, TriageReceipt]:
    resolved = config or AgentConfig.from_environment()
    resolved_model = model or build_ollama_model(resolved)
    settings = ModelSettings(
        temperature=resolved.temperature,
        thinking=resolved.thinking,
        seed=resolved.seed,
        max_tokens=resolved.max_tokens,
        timeout=resolved.timeout_seconds,
        parallel_tool_calls=False,
    )
    return Agent(
        resolved_model,
        deps_type=AgentDeps,
        output_type=ToolOutput(
            file_ticket_output,
            name="file_ticket",
            description=(
                "Terminal action: persist the triaged inbound request and return its typed receipt."
            ),
            sequential=True,
        ),
        instructions=BASE_INSTRUCTIONS,
        tools=(search_tickets, get_ticket, list_team_tickets),
        capabilities=load_runbook_capabilities(),
        model_settings=settings,
        retries=2,
        tool_timeout=resolved.timeout_seconds,
        name="ticket_triage_agent",
    )
