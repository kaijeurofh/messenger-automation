"""Prompt templates for the Euro-FH messaging agent.

The system prompt fixes the persona, language, and channel constraints
(WhatsApp-suitable length, no markdown). The per-request user prompt
plugs the student snapshot in as compact JSON, which keeps the agent
honest and removes any wording bias from a custom serializer.
"""

from __future__ import annotations

from llm_uv_template.models import GenerierteNachricht, NachrichtTrigger, Studi, Tonalitaet

SYSTEM_PROMPT = """Du bist ein Lern-Coach der Euro-FH (Europäische Fernhochschule Hamburg).
Du unterstützt Studierende per WhatsApp bei der Organisation ihres Fernstudiums.

Regeln:
- Sprache: Deutsch, Du-Form, persönlich aber professionell.
- Kanal: WhatsApp. Keine Markdown-Auszeichnungen, keine Überschriften, keine
  Aufzählungszeichen mit `*` oder `#`. Emojis sparsam (max. 2 pro Nachricht).
- Länge: 400 bis 900 Zeichen für den `nachricht`-Text.
- Inhalt: Beziehe Dich konkret auf die Studiendaten der/des Studierenden
  (Studiengang, aktueller Monat, nächste Prüfung, letzte Note, Login-Verhalten).
  Erfinde keine Daten. Wenn etwas fehlt, ignoriere es.
- Ton: Motivierend und unterstützend, niemals belehrend. Erfolge anerkennen,
  Rückschläge normalisieren.
- `empfohlene_naechste_schritte`: 3 bis 5 sehr konkrete, kurze Handlungs-
  empfehlungen (max. 80 Zeichen je Punkt), die innerhalb der nächsten 7 Tage
  umsetzbar sind.
- Gib ausschließlich ein valides `GenerierteNachricht`-Objekt zurück.
"""


_TRIGGER_HINWEISE: dict[NachrichtTrigger, str] = {
    NachrichtTrigger.LERNPLAN_WOCHE: (
        "Erstelle einen realistischen Lernplan für die kommende Woche. "
        "Berücksichtige die nächste Prüfung und den Fortschritt offener Module."
    ),
    NachrichtTrigger.INAKTIVITAET: (
        "Die/Der Studierende war zuletzt auffallend wenig im Online-Campus aktiv. "
        "Frage freundlich nach, biete konkrete Hilfe an. Kein Vorwurf."
    ),
    NachrichtTrigger.PRUEFUNG_VORBEREITUNG: (
        "Die nächste Prüfung steht bald an. Gib eine kompakte Lern-Empfehlung "
        "für die verbleibenden Tage."
    ),
    NachrichtTrigger.MEILENSTEIN: (
        "Würdige einen erreichten Meilenstein (bestandene Prüfung, hoher "
        "Fortschritt, halbe/letzte Etappe des Studiums)."
    ),
    NachrichtTrigger.MOTIVATION_ALLGEMEIN: (
        "Verfasse eine kurze, motivierende Botschaft passend zur aktuellen Studienphase."
    ),
}


def trigger_hinweis(trigger: NachrichtTrigger) -> str:
    return _TRIGGER_HINWEISE[trigger]


def build_user_prompt(studi: Studi, trigger: NachrichtTrigger) -> str:
    """Render the per-request prompt.

    Sends the student snapshot as JSON to avoid any narration the LLM
    might over-index on, plus a short directive derived from the trigger.
    """
    return (
        f"Trigger: {trigger.value}\n"
        f"Anweisung: {trigger_hinweis(trigger)}\n\n"
        f"Studiendaten (JSON):\n{studi.model_dump_json(indent=2)}\n\n"
        "Erzeuge jetzt die Nachricht."
    )


def empty_output_for_tests() -> GenerierteNachricht:
    """Sentinel used by tests that mock the model. Kept here so the test
    suite does not need to know the schema details."""
    return GenerierteNachricht(
        betreff="Test",
        nachricht="Test-Nachricht.",
        empfohlene_naechste_schritte=["Schritt 1"],
        tonalitaet=Tonalitaet.UNTERSTUETZEND,
    )
