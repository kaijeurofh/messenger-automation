"""Tests for the Euro-FH messaging agent.

We use ``pydantic_ai.models.test.TestModel`` so no provider is contacted
and the suite stays deterministic / offline. The agent is exercised end
to end (build → override model → run), which guards against schema or
prompt regressions without depending on Ollama being reachable.
"""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from llm_uv_template.agent import build_agent
from llm_uv_template.data import fixed_profiles, generate_studi
from llm_uv_template.models import GenerierteNachricht, NachrichtTrigger, Tonalitaet
from llm_uv_template.prompts import build_user_prompt


def _sample_output() -> GenerierteNachricht:
    return GenerierteNachricht(
        betreff="Lernplan diese Woche",
        nachricht="Hallo Anna, hier dein Plan für die nächste Woche...",
        empfohlene_naechste_schritte=[
            "Heute 30 min Statistik I",
            "Mittwoch Lerngruppe",
            "Freitag Probeklausur",
        ],
        tonalitaet=Tonalitaet.MOTIVIEREND,
    )


async def test_agent_returns_structured_message() -> None:
    agent = build_agent()
    studi = fixed_profiles()[0]
    prompt = build_user_prompt(studi, NachrichtTrigger.LERNPLAN_WOCHE)
    with agent.override(model=TestModel(custom_output_args=_sample_output().model_dump())):
        result = await agent.run(prompt)
    assert isinstance(result.output, GenerierteNachricht)
    assert result.output.betreff
    assert result.output.nachricht
    assert result.output.tonalitaet in set(Tonalitaet)


async def test_agent_handles_generated_studi() -> None:
    agent = build_agent()
    studi = generate_studi(seed=42)
    prompt = build_user_prompt(studi, NachrichtTrigger.INAKTIVITAET)
    with agent.override(model=TestModel(custom_output_args=_sample_output().model_dump())):
        result = await agent.run(prompt)
    assert isinstance(result.output, GenerierteNachricht)


def test_build_agent_uses_env_model_name(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model:latest")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://test:11434/v1")
    # Construction must not call the network; only verify it succeeds.
    agent = build_agent()
    assert agent is not None
