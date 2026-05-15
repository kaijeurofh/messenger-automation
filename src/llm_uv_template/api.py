"""FastAPI surface for the PoC frontend.

Endpoints:

* ``GET  /api/health`` — liveness + which Ollama model is configured.
* ``GET  /api/triggers`` — enum values for the trigger dropdown.
* ``GET  /api/students`` — fixed + generated profiles.
* ``POST /api/students/generate`` — synthesize ``count`` fresh profiles.
* ``POST /api/messages`` — run the agent against a chosen student/trigger.

In-memory state only. Generated students live until the container
restarts; the fixed profiles are recomputed on each request so the
"current month" stays accurate as time passes.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from llm_uv_template.agent import build_agent, resolve_model_name
from llm_uv_template.data import fixed_profiles, generate_studi, generate_studis
from llm_uv_template.models import (
    NachrichtAnfrage,
    NachrichtAntwort,
    NachrichtTrigger,
    Studi,
)


class GenerateStudentsRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=20)
    seed: int | None = None


class HealthResponse(BaseModel):
    status: str
    modell: str
    ollama_base_url: str


class TriggersResponse(BaseModel):
    trigger: list[str]


class _StudentStore:
    """In-process store for synthesized students.

    Fixed profiles are not cached because they encode "today" relative
    to the request, so we rebuild them per call.
    """

    def __init__(self) -> None:
        self._generated: list[Studi] = []

    def all_students(self) -> list[Studi]:
        return [*fixed_profiles(), *self._generated]

    def find(self, studi_id: str) -> Studi | None:
        return next((s for s in self.all_students() if s.id == studi_id), None)

    def add_generated(self, count: int, seed: int | None) -> list[Studi]:
        fresh = (
            generate_studis(count=count, seed=seed) if count > 1 else [generate_studi(seed=seed)]
        )
        self._generated.extend(fresh)
        return fresh

    def reset(self) -> None:
        self._generated.clear()


_store = _StudentStore()


def get_store() -> _StudentStore:
    return _store


def create_app() -> FastAPI:
    app = FastAPI(
        title="Euro-FH Messenger PoC",
        version="0.1.0",
        description=(
            "Generates WhatsApp-ready support messages for Euro-FH students "
            "using a local Ollama model. Twilio integration is stubbed for "
            "the PoC — messages render in the frontend instead of being sent."
        ),
    )

    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in cors_origins],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            modell=resolve_model_name(),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11435/v1"),
        )

    @app.get("/api/triggers", response_model=TriggersResponse)
    def triggers() -> TriggersResponse:
        return TriggersResponse(trigger=[t.value for t in NachrichtTrigger])

    @app.get("/api/students", response_model=list[Studi])
    def list_students(store: Annotated[_StudentStore, Depends(get_store)]) -> list[Studi]:
        return store.all_students()

    @app.post("/api/students/generate", response_model=list[Studi])
    def generate_students(
        payload: GenerateStudentsRequest,
        store: Annotated[_StudentStore, Depends(get_store)],
    ) -> list[Studi]:
        return store.add_generated(count=payload.count, seed=payload.seed)

    @app.post("/api/messages", response_model=NachrichtAntwort)
    async def create_message(
        payload: NachrichtAnfrage,
        store: Annotated[_StudentStore, Depends(get_store)],
    ) -> NachrichtAntwort:
        studi = store.find(payload.studi_id)
        if studi is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Studi '{payload.studi_id}' nicht gefunden.",
            )

        from llm_uv_template.prompts import build_user_prompt

        agent = build_agent()
        result = await agent.run(build_user_prompt(studi, payload.trigger))

        return NachrichtAntwort(
            studi_id=studi.id,
            trigger=payload.trigger,
            erzeugt_am=datetime.now(UTC),
            modell=resolve_model_name(),
            nachricht=result.output,
        )

    return app


app = create_app()
