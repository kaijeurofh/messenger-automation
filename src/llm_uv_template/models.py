"""Domain models for the Euro-FH student messaging PoC.

These types describe the synthetic study data the agent reasons over and
the structured messages it returns. Everything that crosses the LLM
boundary is a Pydantic model so we keep `mypy --strict` happy and so the
agent's output is validated before it ever reaches a (mocked) Twilio
client.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Pruefungsstatus(StrEnum):
    GEPLANT = "geplant"
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht_bestanden"


class Pruefung(BaseModel):
    model_config = ConfigDict(frozen=True)

    modul: str = Field(description="Modulname, z.B. 'Grundlagen der BWL'.")
    datum: date
    status: Pruefungsstatus
    note: float | None = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Deutsche Notenskala (1.0 = sehr gut bis 5.0 = nicht ausreichend).",
    )


class Kursfortschritt(BaseModel):
    model_config = ConfigDict(frozen=True)

    modul: str
    fortschritt_prozent: int = Field(ge=0, le=100)
    abgeschlossen: bool


class CampusAktivitaet(BaseModel):
    model_config = ConfigDict(frozen=True)

    letzter_login: date
    logins_letzte_30_tage: int = Field(ge=0)


class Studi(BaseModel):
    """Snapshot of a single student's study situation."""

    model_config = ConfigDict(frozen=True)

    id: str
    vorname: str
    nachname: str
    studiengang: str
    studienbeginn: date
    regelstudienzeit_monate: int = Field(ge=12, le=72)
    aktueller_monat_im_studium: int = Field(ge=1)
    abgeschlossene_pruefungen: list[Pruefung] = Field(default_factory=list)
    naechste_pruefung: Pruefung | None = None
    kurse: list[Kursfortschritt] = Field(default_factory=list)
    campus_aktivitaet: CampusAktivitaet
    notendurchschnitt: float | None = Field(default=None, ge=1.0, le=5.0)


class NachrichtTrigger(StrEnum):
    """Why the proactive message is being generated."""

    LERNPLAN_WOCHE = "lernplan_woche"
    INAKTIVITAET = "inaktivitaet"
    PRUEFUNG_VORBEREITUNG = "pruefung_vorbereitung"
    MEILENSTEIN = "meilenstein"
    MOTIVATION_ALLGEMEIN = "motivation_allgemein"


class Tonalitaet(StrEnum):
    MOTIVIEREND = "motivierend"
    UNTERSTUETZEND = "unterstuetzend"
    FEIERND = "feiernd"
    FREUNDLICH_ERINNERND = "freundlich_erinnernd"


class GenerierteNachricht(BaseModel):
    """Structured output of the messaging agent — Twilio-ready."""

    model_config = ConfigDict(frozen=True)

    betreff: str = Field(
        max_length=80,
        description="Kurze Zusammenfassung, z.B. für Push-Benachrichtigung.",
    )
    nachricht: str = Field(
        max_length=1500,
        description="WhatsApp-fertiger Fließtext auf Deutsch, max. ~1500 Zeichen.",
    )
    empfohlene_naechste_schritte: list[str] = Field(
        default_factory=list,
        description="Konkrete Handlungsempfehlungen (3–5 Bullet-Points).",
    )
    tonalitaet: Tonalitaet


class NachrichtAnfrage(BaseModel):
    """Input payload for the /api/messages endpoint."""

    studi_id: str
    trigger: NachrichtTrigger


class NachrichtAntwort(BaseModel):
    """API envelope returned to the frontend."""

    studi_id: str
    trigger: NachrichtTrigger
    erzeugt_am: datetime
    modell: str
    nachricht: GenerierteNachricht
