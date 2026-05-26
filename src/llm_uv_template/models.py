"""Domain models for the Euro-FH student messaging PoC.

These types describe the synthetic study data the agent reasons over and
the structured messages it returns. Everything that crosses the LLM
boundary is a Pydantic model so we keep `mypy --strict` happy and so the
agent's output is validated before it ever reaches a (mocked) Twilio
client.

Note on data source: Das EAP-System der Euro-FH liefert für den Lern-
Coach nur das zuletzt abgeschlossene Modul und die laut Studienverlaufs-
plan kommenden Module. Prozentuale Lernfortschritte oder eine voll-
ständige Prüfungshistorie sind nicht verfügbar — die Modelle bilden
genau diesen Ausschnitt ab, damit der Agent nicht halluzinierte Daten
in seine Empfehlungen einbaut.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Modulstatus(StrEnum):
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht_bestanden"


class LetztesModul(BaseModel):
    """Zuletzt abgeschlossenes Modul gemäß EAP-System.

    Das EAP gibt jeweils nur das *jüngste* abgeschlossene Modul preis —
    keine vollständige Historie. Diese Information dient ausschließlich
    der Einordnung/Anerkennung; sie darf NICHT als Lern-Empfehlung
    aufgegriffen werden.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Modulname, z.B. 'Grundlagen der BWL'.")
    abgeschlossen_am: date
    status: Modulstatus
    note: float | None = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Deutsche Notenskala (1.0 = sehr gut bis 5.0 = nicht ausreichend).",
    )


class KommendesModul(BaseModel):
    """Anstehendes Modul laut Studienverlaufsplan im EAP-System.

    Die Reihenfolge in `Studi.kommende_module` entspricht der geplanten
    Reihenfolge im Studienverlauf — das erste Element ist also das
    nächste Modul, das die/der Studierende belegt.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    geplanter_start: date | None = None
    geplante_pruefung: date | None = None


class CampusAktivitaet(BaseModel):
    model_config = ConfigDict(frozen=True)

    letzter_login: date
    logins_letzte_30_tage: int = Field(ge=0)


class Studi(BaseModel):
    """Snapshot of a single student's study situation.

    Bewusst auf die Felder reduziert, die der EAP-Export tatsächlich
    liefert. Keine Prüfungshistorie, kein Kursfortschritt in Prozent.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    vorname: str
    nachname: str
    studiengang: str
    studienbeginn: date
    regelstudienzeit_monate: int = Field(ge=12, le=72)
    aktueller_monat_im_studium: int = Field(ge=1)
    letztes_modul: LetztesModul | None = None
    kommende_module: list[KommendesModul] = Field(default_factory=list)
    campus_aktivitaet: CampusAktivitaet


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
