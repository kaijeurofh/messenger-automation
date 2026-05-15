"""Synthetic Euro-FH study data.

Two surfaces:

* `FIXED_PROFILES` — five hand-curated students covering distinct
  scenarios (study start, exam phase, behind schedule, near completion,
  recently reactivated). Stable IDs so the frontend can deep-link.
* `generate_studi()` — Faker-backed generator producing additional random
  but internally consistent profiles. Used to stress-test the messaging
  agent against unfamiliar inputs.

Generation is deterministic when a `seed` is provided so demos and tests
stay reproducible.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from llm_uv_template.models import (
    CampusAktivitaet,
    Kursfortschritt,
    Pruefung,
    Pruefungsstatus,
    Studi,
)

_STUDIENGAENGE: tuple[str, ...] = (
    "Bachelor Wirtschaftspsychologie",
    "Bachelor Betriebswirtschaft",
    "Master Wirtschaftsrecht",
    "Bachelor Wirtschaftsinformatik",
    "Master Sales Management",
)

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
    fortschritt_kurse: list[tuple[str, int, bool]],
    abgeschlossene_pruefungen: list[tuple[str, int, Pruefungsstatus, float | None]],
    naechste_pruefung: tuple[str, int] | None,
    tage_seit_letztem_login: int,
    logins_letzte_30_tage: int,
) -> Studi:
    """Assemble a `Studi` from low-level scenario knobs.

    `monate_im_studium` and `tage_seit_letztem_login` are interpreted
    relative to `today()` so the profiles age naturally.
    """
    today = _today()
    studienbeginn = today - timedelta(days=monate_im_studium * 30)

    pruefungen = [
        Pruefung(
            modul=modul,
            datum=today - timedelta(days=tage_zurueck),
            status=status,
            note=note,
        )
        for (modul, tage_zurueck, status, note) in abgeschlossene_pruefungen
    ]
    naechste = (
        Pruefung(
            modul=naechste_pruefung[0],
            datum=today + timedelta(days=naechste_pruefung[1]),
            status=Pruefungsstatus.GEPLANT,
            note=None,
        )
        if naechste_pruefung
        else None
    )
    kurse = [
        Kursfortschritt(modul=modul, fortschritt_prozent=pct, abgeschlossen=done)
        for (modul, pct, done) in fortschritt_kurse
    ]
    aktivitaet = CampusAktivitaet(
        letzter_login=today - timedelta(days=tage_seit_letztem_login),
        logins_letzte_30_tage=logins_letzte_30_tage,
    )

    benotete = [p.note for p in pruefungen if p.note is not None]
    schnitt = round(sum(benotete) / len(benotete), 2) if benotete else None

    return Studi(
        id=student_id,
        vorname=vorname,
        nachname=nachname,
        studiengang=studiengang,
        studienbeginn=studienbeginn,
        regelstudienzeit_monate=regelstudienzeit,
        aktueller_monat_im_studium=monate_im_studium,
        abgeschlossene_pruefungen=pruefungen,
        naechste_pruefung=naechste,
        kurse=kurse,
        campus_aktivitaet=aktivitaet,
        notendurchschnitt=schnitt,
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
            fortschritt_kurse=[
                ("Allgemeine Psychologie", 35, False),
                ("Statistik I", 10, False),
            ],
            abgeschlossene_pruefungen=[],
            naechste_pruefung=("Allgemeine Psychologie", 21),
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
            fortschritt_kurse=[
                ("Externes Rechnungswesen", 100, True),
                ("Internes Rechnungswesen", 80, False),
                ("Marketing", 65, False),
            ],
            abgeschlossene_pruefungen=[
                ("Grundlagen der BWL", 240, Pruefungsstatus.BESTANDEN, 2.3),
                ("Externes Rechnungswesen", 120, Pruefungsstatus.BESTANDEN, 1.7),
            ],
            naechste_pruefung=("Internes Rechnungswesen", 7),
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
            fortschritt_kurse=[
                ("Vertragsrecht", 100, True),
                ("Gesellschaftsrecht", 40, False),
                ("Arbeitsrecht", 5, False),
            ],
            abgeschlossene_pruefungen=[
                ("Vertragsrecht", 200, Pruefungsstatus.BESTANDEN, 2.7),
                ("Gesellschaftsrecht", 60, Pruefungsstatus.NICHT_BESTANDEN, 5.0),
            ],
            naechste_pruefung=("Gesellschaftsrecht", 35),
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
            fortschritt_kurse=[
                ("Programmierung I", 100, True),
                ("Datenbanken", 100, True),
                ("IT-Projektmanagement", 100, True),
                ("Web-Technologien", 100, True),
                ("Geschäftsprozessmanagement", 85, False),
            ],
            abgeschlossene_pruefungen=[
                ("Programmierung I", 900, Pruefungsstatus.BESTANDEN, 1.7),
                ("Datenbanken", 700, Pruefungsstatus.BESTANDEN, 2.0),
                ("IT-Projektmanagement", 500, Pruefungsstatus.BESTANDEN, 1.3),
                ("Web-Technologien", 250, Pruefungsstatus.BESTANDEN, 2.3),
            ],
            naechste_pruefung=("Geschäftsprozessmanagement", 14),
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
            fortschritt_kurse=[
                ("Strategisches Vertriebsmanagement", 70, False),
                ("Key Account Management", 25, False),
            ],
            abgeschlossene_pruefungen=[
                ("Strategisches Vertriebsmanagement", 30, Pruefungsstatus.BESTANDEN, 1.7),
            ],
            naechste_pruefung=("Key Account Management", 28),
            tage_seit_letztem_login=4,
            logins_letzte_30_tage=6,
        ),
    ]


def generate_studi(seed: int | None = None) -> Studi:
    """Generate a single synthetic student.

    The output is internally consistent: graded exams precede today, the
    next exam (if any) lies in the future, and login counts respect the
    age of `letzter_login`.
    """
    rng = random.Random(seed)
    fake = Faker("de_DE")
    if seed is not None:
        Faker.seed(seed)

    studiengang = rng.choice(_STUDIENGAENGE)
    module = _module_for(studiengang)

    regelstudienzeit = rng.choice([24, 36, 48])
    monate = rng.randint(1, regelstudienzeit + 6)

    n_abgeschlossen = min(len(module) - 1, max(0, monate // 4))
    chosen_done = rng.sample(module, k=n_abgeschlossen) if n_abgeschlossen else []
    abgeschlossene: list[tuple[str, int, Pruefungsstatus, float | None]] = []
    for modul in chosen_done:
        tage_zurueck = rng.randint(15, max(16, monate * 30))
        if rng.random() < 0.85:
            note = round(rng.uniform(1.0, 3.7), 1)
            abgeschlossene.append((modul, tage_zurueck, Pruefungsstatus.BESTANDEN, note))
        else:
            abgeschlossene.append((modul, tage_zurueck, Pruefungsstatus.NICHT_BESTANDEN, 5.0))

    remaining = [m for m in module if m not in chosen_done]
    naechste: tuple[str, int] | None = None
    if remaining and rng.random() < 0.8:
        naechste = (rng.choice(remaining), rng.randint(5, 60))

    fortschritt: list[tuple[str, int, bool]] = []
    for modul in chosen_done:
        fortschritt.append((modul, 100, True))
    for modul in rng.sample(remaining, k=min(3, len(remaining))):
        pct = rng.randint(5, 90)
        fortschritt.append((modul, pct, False))

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
        fortschritt_kurse=fortschritt,
        abgeschlossene_pruefungen=abgeschlossene,
        naechste_pruefung=naechste,
        tage_seit_letztem_login=tage_seit_login,
        logins_letzte_30_tage=logins,
    )


def generate_studis(count: int, seed: int | None = None) -> list[Studi]:
    rng = random.Random(seed)
    return [generate_studi(seed=rng.randint(0, 2**31 - 1)) for _ in range(count)]
