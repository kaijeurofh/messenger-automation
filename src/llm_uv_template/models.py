"""Domain models for the Euro-FH student messaging PoC.

These types describe the synthetic study data the agent reasons over and
the structured messages it returns. Everything that crosses the LLM
boundary is a Pydantic model so we keep `mypy --strict` happy and so the
agent's output is validated before it ever reaches a (mocked) Twilio
client.

EAP-Sichtbarkeit (Quelle für die Modelle):

* `abgeschlossene_module` — vollständige Historie bestandener und nicht
  bestandener Module (mit Note und Datum).
* `aktuelle_module` — die maximal fünf Module, die der/die Studierende
  aktuell als "in Bearbeitung" gesetzt hat. Das sind die einzigen
  legitimen Lernziele für den Coach.
* `studienheft_ereignisse` — Öffnungen und Downloads von Studienheften
  pro Modul, mit Zeitstempel. Engagement-Signal.
* `pruefungsanmeldungen` — verbindliche Anmeldungen zu Klausuren mit
  Anmelde- und Prüfungsdatum.

Lernfortschritte in Prozent liefert EAP weiterhin NICHT — die Modelle
bilden bewusst nur ab, was die Fachbetreuung wirklich sieht.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Modulstatus(StrEnum):
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht_bestanden"


class StudienheftAktion(StrEnum):
    GEOEFFNET = "geoeffnet"
    HERUNTERGELADEN = "heruntergeladen"


class AbgeschlossenesModul(BaseModel):
    """Ein Modul, dessen Klausur bereits geschrieben wurde.

    `status == BESTANDEN` heißt: das Modul ist endgültig durch und darf
    NIE wieder als Lernziel empfohlen werden.
    `status == NICHT_BESTANDEN` heißt: ggf. als Wiederholung erneut
    aktiv — taucht dann zusätzlich in `Studi.aktuelle_module` auf.
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


class AktuellesModul(BaseModel):
    """Ein vom Studi aktuell zur Bearbeitung gewähltes Modul.

    EAP erlaubt maximal fünf parallele Slots — siehe `Studi.aktuelle_module`.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    belegt_seit: date | None = Field(
        default=None,
        description="Wann der Studi das Modul in den Slots aktiviert hat.",
    )


class StudienheftEreignis(BaseModel):
    """EAP meldet, wenn ein Studienheft geöffnet oder heruntergeladen wird."""

    model_config = ConfigDict(frozen=True)

    modul: str
    aktion: StudienheftAktion
    zeitpunkt: datetime


class Pruefungsanmeldung(BaseModel):
    """Verbindliche Klausur-Anmeldung mit Anmelde- und Prüfungsdatum."""

    model_config = ConfigDict(frozen=True)

    modul: str
    pruefungstermin: date
    angemeldet_am: date


class CampusAktivitaet(BaseModel):
    model_config = ConfigDict(frozen=True)

    letzter_login: date
    logins_letzte_30_tage: int = Field(ge=0)


class Studi(BaseModel):
    """Snapshot of a single student's study situation.

    Bewusst auf die Felder beschränkt, die der EAP-Export tatsächlich
    liefert. Keine prozentualen Lernfortschritte.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    vorname: str
    nachname: str
    studiengang: str
    studienbeginn: date
    regelstudienzeit_monate: int = Field(ge=12, le=72)
    aktueller_monat_im_studium: int = Field(ge=1)
    abgeschlossene_module: list[AbgeschlossenesModul] = Field(default_factory=list)
    aktuelle_module: list[AktuellesModul] = Field(
        default_factory=list,
        max_length=5,
        description="Max. fünf parallel belegte Module (EAP-Constraint).",
    )
    studienheft_ereignisse: list[StudienheftEreignis] = Field(
        default_factory=list,
        description=(
            "Chronologisch letzte Studienheft-Aktionen. Engagement-Signal — "
            "keine vollständige Historie, sondern jüngste relevante Ereignisse."
        ),
    )
    pruefungsanmeldungen: list[Pruefungsanmeldung] = Field(default_factory=list)
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
