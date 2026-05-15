"""HTTP-level tests for the FastAPI surface.

Uses FastAPI's ``TestClient`` (synchronous, no real server) and overrides
the pydantic-ai model with ``TestModel`` for the one endpoint that runs
the agent. The dependency override is wired via ``app.dependency_overrides``
on the store so the agent runs against a freshly built isolate.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from llm_uv_template.api import create_app
from llm_uv_template.models import GenerierteNachricht, Tonalitaet
from llm_uv_template.prompts import SYSTEM_PROMPT


def _fake_output() -> GenerierteNachricht:
    return GenerierteNachricht(
        betreff="Test-Betreff",
        nachricht="Test-Nachricht für Anna.",
        empfohlene_naechste_schritte=["A", "B", "C"],
        tonalitaet=Tonalitaet.MOTIVIEREND,
    )


def test_health_reports_configured_model(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OLLAMA_MODEL", "gemma4:31b")
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["modell"] == "gemma4:31b"


def test_triggers_lists_known_enum_values() -> None:
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/triggers")
    assert res.status_code == 200
    assert "lernplan_woche" in res.json()["trigger"]


def test_students_endpoint_returns_fixed_profiles() -> None:
    app = create_app()
    client = TestClient(app)
    res = client.get("/api/students")
    assert res.status_code == 200
    ids = [s["id"] for s in res.json()]
    assert "anna-studienanfang" in ids
    assert "boris-pruefungsphase" in ids


def test_generate_students_appends_to_store() -> None:
    app = create_app()
    client = TestClient(app)
    before = len(client.get("/api/students").json())
    res = client.post("/api/students/generate", json={"count": 2, "seed": 1})
    assert res.status_code == 200
    assert len(res.json()) == 2
    after = len(client.get("/api/students").json())
    assert after == before + 2


def test_messages_endpoint_invokes_agent(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def _patched_build() -> Agent[None, GenerierteNachricht]:
        # Construct a fresh agent already wired to TestModel — avoids the
        # `agent.override` context manager, which can't be cleanly torn down
        # inside a sync route handler and trips pytest's unraisable-warning
        # check at teardown.
        return Agent(
            TestModel(custom_output_args=_fake_output().model_dump()),
            output_type=GenerierteNachricht,
            system_prompt=SYSTEM_PROMPT,
        )

    monkeypatch.setattr("llm_uv_template.api.build_agent", _patched_build)

    app = create_app()
    client = TestClient(app)
    res = client.post(
        "/api/messages",
        json={"studi_id": "anna-studienanfang", "trigger": "lernplan_woche"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["studi_id"] == "anna-studienanfang"
    assert body["nachricht"]["betreff"] == "Test-Betreff"
    assert body["nachricht"]["tonalitaet"] == "motivierend"


def test_messages_endpoint_404_for_unknown_studi() -> None:
    app = create_app()
    client = TestClient(app)
    res = client.post(
        "/api/messages",
        json={"studi_id": "does-not-exist", "trigger": "lernplan_woche"},
    )
    assert res.status_code == 404
