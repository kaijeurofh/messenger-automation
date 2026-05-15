"""Messaging agent backed by a local Ollama model.

The agent reads `OLLAMA_BASE_URL` and `OLLAMA_MODEL` from the environment
so the same code drives the docker-compose stack (where Ollama runs on
the host) and local development (`http://localhost:11434/v1`). Tests
override the model via `agent.override(model=TestModel(...))` so they
never reach Ollama.
"""

from __future__ import annotations

import os

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from llm_uv_template.models import GenerierteNachricht
from llm_uv_template.prompts import SYSTEM_PROMPT

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "gemma4:31b"


def _resolve_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)


def resolve_model_name() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def build_agent(model_name: str | None = None) -> Agent[None, GenerierteNachricht]:
    """Construct the messaging agent.

    `model_name` overrides the env var. Construction does not call the
    network; the first call to `agent.run` does.
    """
    selected = model_name or resolve_model_name()
    provider = OpenAIProvider(base_url=_resolve_base_url(), api_key="ollama")
    model = OpenAIChatModel(model_name=selected, provider=provider)

    agent: Agent[None, GenerierteNachricht] = Agent(
        model,
        output_type=GenerierteNachricht,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent
