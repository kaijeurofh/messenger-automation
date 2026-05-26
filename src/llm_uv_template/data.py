"""Synthetic Euro-FH study data.

Two surfaces:

* `fixed_profiles()` — five hand-curated students covering distinct
  scenarios (study start, exam phase, behind schedule, near completion,
  recently reactivated). Stable IDs so the frontend can deep-link.
* `generate_studi()` — Faker-backed generator producing additional random
  but internally consistent profiles. Used to stress-test the messaging
  agent against unfamiliar inputs.

Data shape mirrors the EAP export: pro Studi maximal *ein* zuletzt
abgeschlossenes Modul plus die laut Studienverlaufsplan kommenden Module.
Keine prozentualen Lernfortschritte und keine vollständige Prüfungs-
historie — wir bilden bewusst nur ab, was die Fachbetreuung im EAP auch
wirklich sieht, damit der LLM-Agent keine bereits bestandenen Module
als Lernziel empfiehlt.

Generation is deterministic when a `seed` is provided so demos and tests
stay reproducible.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from llm_uv_template.models import (
    CampusAktivitaet,
    KommendesModul,
    LetztesModul,
    Modulstatus,
    Studi,
)

_STUDIENGAENGE: tuple[str, ...] = (
    "Bachelor Wirtschaftspsychologie",
    "Bachelor Betriebswirtschaft",
    "Master Wirtschaftsrecht",
    "Bachelor Wirtschaftsinformatik",
    "Master Sales Management",
)

# Modul-Pools sind als geordnete Studienverlaufspläne zu lesen: vorne
# steht das, was zuerst belegt wird. Die fixen und generierten Profile
# greifen darauf zurück, damit "letztes Modul" und "kommende Module"
# einer plausiblen Reihenfolge folgen.
_MODULE_POOL: dict[str, tuple[str, ...]] = {
    "Bachelor Wirtschaftspsychologie": (
        "Allgemeine Psychologie",
        "Statistik I",
        "Statistik II",
        "Wirtschaftspsychologie I",
        "Markt- und Werbepsychologie",
        "Personalpsychologie",
        "Organisationspsychologie",
        "Empirische Forschungsmethoden",
    ),
    "Bachelor Betriebswirtschaft": (
        "Grundlagen der BWL",
        "Externes Rechnungswesen",
        "Internes Rechnungswesen",
        "Marketing",
        "Investition und Finanzierung",
        "Organisation und Personal",
        "Steuerlehre",
    ),
    "Master Wirtschaftsrecht": (
        "Vertragsrecht",
        "Gesellschaftsrecht",
        "Arbeitsrecht",
        "Steuerrecht",
        "Europarecht",
    ),
    "Bachelor Wirtschaftsinformatik": (
        "Programmierung I",
        "Datenbanken",
        "IT-Projektmanagement",
        "Web-Technologien",
        "Geschäftsprozessmanagement",
    ),
    "Master Sales Management": (
        "Strategisches Vertriebsmanagement",
        "Key Account Management",
        "Vertriebscontrolling",
        "Digital Sales",
    ),
}


def _module_for(studiengang: str) -> tuple[str, ...]:
    return _MODULE_POOL.get(studiengang, _MODULE_POOL["Bachelor Betriebswirtschaft"])


def _today() -> date:
    # Centralized so tests can monkeypatch a stable "today" if needed.
    return date.today()


def _build_fixed_profile(
    *,
    student_id: str,
    vorname: str,
    nachname: str,
    studiengang: str,
    monate_im_studium: int,
    regelstudienzeit: int,
    letztes_modul: tuple[str, int, Modulstatus, float | None] | None,
    kommende_module: list[tuple[str, int | None, int | None]],
    tage_seit_letztem_login: int,
    logins_letzte_30_tage: int,
) -> Studi:
    """Assemble a `Studi` from low-level scenario knobs.

    `monate_im_studium` and `tage_seit_letztem_login` are interpreted
    relative to `today()` so the profiles age naturally. Each
    `kommende_module`-Tupel ist `(name, tage_bis_start, tage_bis_pruefung)` —
    `None` für Start oder Prüfung, wenn das EAP keinen Termin liefert.
    """
    today = _today()
    studienbeginn = today - timedelta(days=monate_im_studium * 30)

    letztes = (
        LetztesModul(
            name=letztes_modul[0],
            abgeschlossen_am=today - timedelta(days=letztes_modul[1]),
            status=letztes_modul[2],
            note=letztes_modul[3],
        )
        if letztes_modul
        else None
    )
    kommende = [
        KommendesModul(
            name=name,
            geplanter_start=today + timedelta(days=tage_start) if tage_start is not None else None,
            geplante_pruefung=(
                today + timedelta(days=tage_pruefung) if tage_pruefung is not None else None
            ),
        )
        for (name, tage_start, tage_pruefung) in kommende_module
    ]
    aktivitaet = CampusAktivitaet(
        letzter_login=today - timedelta(days=tage_seit_letztem_login),
        logins_letzte_30_tage=logins_letzte_30_tage,
    )

    return Studi(
        id=student_id,
        vorname=vorname,
        nachname=nachname,
        studiengang=studiengang,
        studienbeginn=studienbeginn,
        regelstudienzeit_monate=regelstudienzeit,
        aktueller_monat_im_studium=monate_im_studium,
        letztes_modul=letztes,
        kommende_module=kommende,
        campus_aktivitaet=aktivitaet,
    )


def fixed_profiles() -> list[Studi]:
    """Return the five hand-curated demo profiles."""
    return [
        _build_fixed_profile(
            student_id="anna-studienanfang",
            vorname="Anna",
            nachname="Berger",
            studiengang="Bachelor Wirtschaftspsychologie",
            monate_im_studium=2,
            regelstudienzeit=48,
            letztes_modul=None,
            kommende_module=[
                ("Allgemeine Psychologie", 0, 21),
                ("Statistik I", 30, 60),
                ("Statistik II", 90, 120),
            ],
            tage_seit_letztem_login=1,
            logins_letzte_30_tage=18,
        ),
        _build_fixed_profile(
            student_id="boris-pruefungsphase",
            vorname="Boris",
            nachname="Hoffmann",
            studiengang="Bachelor Betriebswirtschaft",
            monate_im_studium=18,
            regelstudienzeit=48,
            letztes_modul=("Externes Rechnungswesen", 120, Modulstatus.BESTANDEN, 1.7),
            kommende_module=[
                ("Internes Rechnungswesen", -30, 7),
                ("Marketing", 14, 60),
                ("Investition und Finanzierung", 60, 120),
            ],
            tage_seit_letztem_login=0,
            logins_letzte_30_tage=24,
        ),
        _build_fixed_profile(
            student_id="clara-in-verzug",
            vorname="Clara",
            nachname="Wagner",
            studiengang="Master Wirtschaftsrecht",
            monate_im_studium=20,
            regelstudienzeit=24,
            letztes_modul=("Gesellschaftsrecht", 60, Modulstatus.NICHT_BESTANDEN, 5.0),
            kommende_module=[
                ("Gesellschaftsrecht (Wiederholung)", -15, 35),
                ("Arbeitsrecht", 14, 90),
                ("Steuerrecht", 60, 150),
            ],
            tage_seit_letztem_login=11,
            logins_letzte_30_tage=3,
        ),
        _build_fixed_profile(
            student_id="david-kurz-vor-abschluss",
            vorname="David",
            nachname="Krüger",
            studiengang="Bachelor Wirtschaftsinformatik",
            monate_im_studium=42,
            regelstudienzeit=48,
            letztes_modul=("Web-Technologien", 60, Modulstatus.BESTANDEN, 2.3),
            kommende_module=[
                ("Geschäftsprozessmanagement", -45, 14),
            ],
            tage_seit_letztem_login=2,
            logins_letzte_30_tage=22,
        ),
        _build_fixed_profile(
            student_id="elif-reaktiviert",
            vorname="Elif",
            nachname="Yıldız",
            studiengang="Master Sales Management",
            monate_im_studium=8,
            regelstudienzeit=24,
            letztes_modul=("Strategisches Vertriebsmanagement", 30, Modulstatus.BESTANDEN, 1.7),
            kommende_module=[
                ("Key Account Management", -10, 28),
                ("Vertriebscontrolling", 30, 90),
                ("Digital Sales", 90, 150),
            ],
            tage_seit_letztem_login=4,
            logins_letzte_30_tage=6,
        ),
    ]


def generate_studi(seed: int | None = None) -> Studi:
    """Generate a single synthetic student.

    The output is internally consistent: das `letztes_modul` (sofern
    vorhanden) liegt in der Vergangenheit, kommende Module liegen ab
    heute oder leicht in der Vergangenheit (Modulstart kann vor
    "heute" liegen, Prüfungstermin liegt aber stets in der Zukunft).
    """
    rng = random.Random(seed)
    fake = Faker("de_DE")
    if seed is not None:
        Faker.seed(seed)

    studiengang = rng.choice(_STUDIENGAENGE)
    module = _module_for(studiengang)

    regelstudienzeit = rng.choice([24, 36, 48])
    monate = rng.randint(1, regelstudienzeit + 6)

    # Wieviele Module sind laut Studienverlaufsplan schon "durch"?
    # Studis ganz am Anfang haben evtl. noch gar kein letztes Modul.
    n_durch = min(len(module) - 1, max(0, monate // 4))
    letztes: tuple[str, int, Modulstatus, float | None] | None = None
    if n_durch > 0:
        letztes_name = module[n_durch - 1]
        tage_zurueck = rng.randint(15, 180)
        if rng.random() < 0.85:
            note = round(rng.uniform(1.0, 3.7), 1)
            letztes = (letztes_name, tage_zurueck, Modulstatus.BESTANDEN, note)
        else:
            letztes = (letztes_name, tage_zurueck, Modulstatus.NICHT_BESTANDEN, 5.0)

    # Kommende Module: nimm bis zu drei aus dem verbleibenden Pool.
    # Beim ersten kommenden Modul ist die Prüfung nahe (5–45 Tage), die
    # übrigen liegen weiter in der Zukunft.
    verbleibend = list(module[n_durch:])
    kommende: list[tuple[str, int | None, int | None]] = []
    for i, modul_name in enumerate(verbleibend[:3]):
        if i == 0:
            tage_start = rng.randint(-30, 0)
            tage_pruefung = rng.randint(5, 45)
        else:
            tage_start = rng.randint(30 * i, 30 * i + 30)
            tage_pruefung = tage_start + rng.randint(30, 60)
        kommende.append((modul_name, tage_start, tage_pruefung))

    tage_seit_login = rng.choices(
        [0, 1, 2, 5, 9, 14, 30],
        weights=[20, 25, 20, 15, 10, 7, 3],
        k=1,
    )[0]
    max_logins = max(0, 30 - tage_seit_login)
    logins = rng.randint(0, min(28, max_logins + 2))

    return _build_fixed_profile(
        student_id=f"gen-{fake.uuid4()[:8]}",
        vorname=fake.first_name(),
        nachname=fake.last_name(),
        studiengang=studiengang,
        monate_im_studium=monate,
        regelstudienzeit=regelstudienzeit,
        letztes_modul=letztes,
        kommende_module=kommende,
        tage_seit_letztem_login=tage_seit_login,
        logins_letzte_30_tage=logins,
    )


def generate_studis(count: int, seed: int | None = None) -> list[Studi]:
    rng = random.Random(seed)
    return [generate_studi(seed=rng.randint(0, 2**31 - 1)) for _ in range(count)]
