"""Synthetic Euro-FH study data.

Two surfaces:

* `fixed_profiles()` — five hand-curated students covering distinct
  scenarios (study start, exam phase, behind schedule, near completion,
  recently reactivated). Stable IDs so the frontend can deep-link.
* `generate_studi()` — Faker-backed generator producing additional random
  but internally consistent profiles. Used to stress-test the messaging
  agent against unfamiliar inputs.

Die Datenform spiegelt den EAP-Export wider: vollständige Historie
abgeschlossener Module, maximal fünf aktuell belegte Module, jüngste
Studienheft-Ereignisse (geöffnet/heruntergeladen) und verbindliche
Prüfungsanmeldungen mit Datum. Keine prozentualen Lernfortschritte.

Generation is deterministic when a `seed` is provided so demos and tests
stay reproducible.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from faker import Faker

from llm_uv_template.models import (
    AbgeschlossenesModul,
    AktuellesModul,
    CampusAktivitaet,
    Modulstatus,
    Pruefungsanmeldung,
    Studi,
    StudienheftAktion,
    StudienheftEreignis,
)

_STUDIENGAENGE: tuple[str, ...] = (
    "Bachelor Wirtschaftspsychologie",
    "Bachelor Betriebswirtschaft",
    "Master Wirtschaftsrecht",
    "Bachelor Wirtschaftsinformatik",
    "Master Sales Management",
)

# Modul-Pools entsprechen einer plausiblen Reihenfolge im
# Studienverlaufsplan: vorne stehen die Basismodule, hinten die
# Vertiefungs-/Spezialisierungsmodule. Generator und Fixed-Profile
# greifen darauf zurück.
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


def _ereignis(
    *,
    modul: str,
    aktion: StudienheftAktion,
    tage_zurueck: int,
    stunde: int = 9,
) -> StudienheftEreignis:
    today = _today()
    moment = datetime.combine(today - timedelta(days=tage_zurueck), time(hour=stunde))
    return StudienheftEreignis(modul=modul, aktion=aktion, zeitpunkt=moment)


def _build_fixed_profile(
    *,
    student_id: str,
    vorname: str,
    nachname: str,
    studiengang: str,
    monate_im_studium: int,
    regelstudienzeit: int,
    abgeschlossene_module: list[tuple[str, int, Modulstatus, float | None]],
    aktuelle_module: list[tuple[str, int | None]],
    studienheft_ereignisse: list[StudienheftEreignis],
    pruefungsanmeldungen: list[tuple[str, int, int]],
    tage_seit_letztem_login: int,
    logins_letzte_30_tage: int,
) -> Studi:
    """Assemble a `Studi` from low-level scenario knobs.

    Tupelschemata (alle Zeitangaben relativ zu `_today()`):

    * `abgeschlossene_module`: ``(name, tage_seit_abschluss, status, note)``
    * `aktuelle_module`: ``(name, tage_seit_belegung_oder_None)``
    * `pruefungsanmeldungen`: ``(modul, tage_bis_pruefung, tage_seit_anmeldung)``
      — `tage_bis_pruefung` darf negativ sein (Klausur kürzlich vorbei).
    """
    today = _today()
    studienbeginn = today - timedelta(days=monate_im_studium * 30)

    abgeschlossen = [
        AbgeschlossenesModul(
            name=name,
            abgeschlossen_am=today - timedelta(days=tage),
            status=status,
            note=note,
        )
        for (name, tage, status, note) in abgeschlossene_module
    ]
    aktuell = [
        AktuellesModul(
            name=name,
            belegt_seit=today - timedelta(days=tage) if tage is not None else None,
        )
        for (name, tage) in aktuelle_module
    ]
    anmeldungen = [
        Pruefungsanmeldung(
            modul=modul,
            pruefungstermin=today + timedelta(days=tage_bis_pruefung),
            angemeldet_am=today - timedelta(days=tage_seit_anmeldung),
        )
        for (modul, tage_bis_pruefung, tage_seit_anmeldung) in pruefungsanmeldungen
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
        abgeschlossene_module=abgeschlossen,
        aktuelle_module=aktuell,
        studienheft_ereignisse=list(studienheft_ereignisse),
        pruefungsanmeldungen=anmeldungen,
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
            abgeschlossene_module=[],
            aktuelle_module=[
                ("Allgemeine Psychologie", 55),
                ("Statistik I", 30),
            ],
            studienheft_ereignisse=[
                _ereignis(
                    modul="Allgemeine Psychologie",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=55,
                ),
                _ereignis(
                    modul="Allgemeine Psychologie",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=2,
                    stunde=20,
                ),
                _ereignis(
                    modul="Statistik I",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=20,
                ),
            ],
            pruefungsanmeldungen=[("Allgemeine Psychologie", 21, 7)],
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
            abgeschlossene_module=[
                ("Grundlagen der BWL", 240, Modulstatus.BESTANDEN, 2.3),
                ("Externes Rechnungswesen", 120, Modulstatus.BESTANDEN, 1.7),
            ],
            aktuelle_module=[
                ("Internes Rechnungswesen", 90),
                ("Marketing", 60),
                ("Investition und Finanzierung", 30),
            ],
            studienheft_ereignisse=[
                _ereignis(
                    modul="Internes Rechnungswesen",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=88,
                ),
                _ereignis(
                    modul="Internes Rechnungswesen",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=3,
                    stunde=21,
                ),
                _ereignis(
                    modul="Internes Rechnungswesen",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=1,
                    stunde=19,
                ),
                _ereignis(
                    modul="Marketing",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=58,
                ),
                _ereignis(
                    modul="Investition und Finanzierung",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=29,
                ),
            ],
            pruefungsanmeldungen=[
                ("Internes Rechnungswesen", 7, 35),
                ("Marketing", 60, 5),
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
            abgeschlossene_module=[
                ("Vertragsrecht", 200, Modulstatus.BESTANDEN, 2.7),
                ("Gesellschaftsrecht", 60, Modulstatus.NICHT_BESTANDEN, 5.0),
            ],
            aktuelle_module=[
                ("Gesellschaftsrecht (Wiederholung)", 30),
                ("Arbeitsrecht", 90),
                ("Steuerrecht", 90),
            ],
            studienheft_ereignisse=[
                _ereignis(
                    modul="Gesellschaftsrecht (Wiederholung)",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=30,
                ),
                _ereignis(
                    modul="Arbeitsrecht",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=80,
                ),
            ],
            pruefungsanmeldungen=[("Gesellschaftsrecht (Wiederholung)", 35, 20)],
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
            abgeschlossene_module=[
                ("Programmierung I", 900, Modulstatus.BESTANDEN, 1.7),
                ("Datenbanken", 700, Modulstatus.BESTANDEN, 2.0),
                ("IT-Projektmanagement", 500, Modulstatus.BESTANDEN, 1.3),
                ("Web-Technologien", 250, Modulstatus.BESTANDEN, 2.3),
            ],
            aktuelle_module=[("Geschäftsprozessmanagement", 90)],
            studienheft_ereignisse=[
                _ereignis(
                    modul="Geschäftsprozessmanagement",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=88,
                ),
                _ereignis(
                    modul="Geschäftsprozessmanagement",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=5,
                    stunde=22,
                ),
                _ereignis(
                    modul="Geschäftsprozessmanagement",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=1,
                    stunde=20,
                ),
            ],
            pruefungsanmeldungen=[("Geschäftsprozessmanagement", 14, 45)],
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
            abgeschlossene_module=[
                ("Strategisches Vertriebsmanagement", 30, Modulstatus.BESTANDEN, 1.7),
            ],
            aktuelle_module=[
                ("Key Account Management", 60),
                ("Vertriebscontrolling", 60),
                ("Digital Sales", 60),
            ],
            studienheft_ereignisse=[
                _ereignis(
                    modul="Key Account Management",
                    aktion=StudienheftAktion.HERUNTERGELADEN,
                    tage_zurueck=58,
                ),
                _ereignis(
                    modul="Key Account Management",
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=0,
                    stunde=8,
                ),
            ],
            pruefungsanmeldungen=[("Key Account Management", 28, 10)],
            tage_seit_letztem_login=0,
            logins_letzte_30_tage=6,
        ),
    ]


def _generate_studienheft_ereignisse(
    rng: random.Random,
    aktuelle: list[tuple[str, int | None]],
    pruefungsanmeldungen: list[tuple[str, int, int]],
) -> list[StudienheftEreignis]:
    """Erzeuge plausible Studienheft-Aktivität für die aktuellen Module.

    Heuristik: pro aktiv belegtem Modul ein Download in der Vergangenheit
    (oft kurz nach Belegung) plus 1–3 Öffnungen in den letzten 30 Tagen.
    Module mit naher Prüfungsanmeldung bekommen tendenziell mehr Events.
    """
    ereignisse: list[StudienheftEreignis] = []
    naechste_pruefung_pro_modul = {
        modul: tage_bis_pruefung for (modul, tage_bis_pruefung, _) in pruefungsanmeldungen
    }

    for name, tage_belegt in aktuelle:
        if tage_belegt is not None:
            download_tage = max(tage_belegt - rng.randint(0, 2), 1)
        else:
            download_tage = rng.randint(20, 120)
        ereignisse.append(
            _ereignis(
                modul=name,
                aktion=StudienheftAktion.HERUNTERGELADEN,
                tage_zurueck=download_tage,
                stunde=rng.randint(8, 21),
            )
        )

        # Mehr Engagement, wenn eine Prüfung naht.
        tage_bis_pruefung = naechste_pruefung_pro_modul.get(name)
        if tage_bis_pruefung is not None and 0 <= tage_bis_pruefung <= 30:
            anzahl_openings = rng.randint(2, 4)
        elif tage_bis_pruefung is not None:
            anzahl_openings = rng.randint(1, 2)
        else:
            anzahl_openings = rng.randint(0, 2)

        for _ in range(anzahl_openings):
            tage = rng.randint(0, 25)
            ereignisse.append(
                _ereignis(
                    modul=name,
                    aktion=StudienheftAktion.GEOEFFNET,
                    tage_zurueck=tage,
                    stunde=rng.randint(7, 22),
                )
            )

    # Chronologisch jüngste zuerst; das macht den JSON-Snapshot lesbarer.
    return sorted(ereignisse, key=lambda e: e.zeitpunkt, reverse=True)


def generate_studi(seed: int | None = None) -> Studi:
    """Generate a single synthetic student.

    The output is internally consistent: abgeschlossene Module liegen in
    der Vergangenheit, aktuelle Module sind höchstens fünf,
    Studienheft-Ereignisse zeitlich plausibel zur Modulbelegung,
    Prüfungsanmeldungen verweisen ausschließlich auf aktuelle Module.
    """
    rng = random.Random(seed)
    fake = Faker("de_DE")
    if seed is not None:
        Faker.seed(seed)

    studiengang = rng.choice(_STUDIENGAENGE)
    module = _module_for(studiengang)

    regelstudienzeit = rng.choice([24, 36, 48])
    monate = rng.randint(1, regelstudienzeit + 6)

    # Wieviele Module sind laut Verlauf schon "durch"?
    n_durch = min(len(module) - 1, max(0, monate // 4))
    abgeschlossen_raw: list[tuple[str, int, Modulstatus, float | None]] = []
    wiederholungen: list[str] = []
    for i in range(n_durch):
        name = module[i]
        tage_zurueck = rng.randint(30, max(31, monate * 30))
        if rng.random() < 0.85:
            note = round(rng.uniform(1.0, 3.7), 1)
            abgeschlossen_raw.append((name, tage_zurueck, Modulstatus.BESTANDEN, note))
        else:
            abgeschlossen_raw.append((name, tage_zurueck, Modulstatus.NICHT_BESTANDEN, 5.0))
            wiederholungen.append(name)

    # Aktuelle Module: bis zu 5 Slots. Wiederholungen (nicht bestanden)
    # kommen verbindlich rein, dazu die nächsten Module aus dem Verlauf.
    verbleibend = list(module[n_durch:])
    aktuelle_namen: list[str] = []
    for w in wiederholungen[:2]:
        aktuelle_namen.append(f"{w} (Wiederholung)")
    for name in verbleibend:
        if len(aktuelle_namen) >= 5:
            break
        aktuelle_namen.append(name)
    # Mindestens ein aktuelles Modul für nicht ganz frische Studis.
    if not aktuelle_namen and verbleibend:
        aktuelle_namen.append(verbleibend[0])

    aktuelle_raw: list[tuple[str, int | None]] = []
    for name in aktuelle_namen:
        belegt = rng.randint(5, 120)
        aktuelle_raw.append((name, belegt))

    # Prüfungsanmeldungen: 0–2 Stück, immer für aktive Module.
    n_anmeldungen = rng.randint(0, min(2, len(aktuelle_raw)))
    pruefungsanmeldungen: list[tuple[str, int, int]] = []
    for name in rng.sample([n for (n, _) in aktuelle_raw], k=n_anmeldungen):
        tage_bis_pruefung = rng.randint(5, 60)
        tage_seit_anmeldung = rng.randint(1, 40)
        pruefungsanmeldungen.append((name, tage_bis_pruefung, tage_seit_anmeldung))

    studienheft = _generate_studienheft_ereignisse(rng, aktuelle_raw, pruefungsanmeldungen)

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
        abgeschlossene_module=abgeschlossen_raw,
        aktuelle_module=aktuelle_raw,
        studienheft_ereignisse=studienheft,
        pruefungsanmeldungen=pruefungsanmeldungen,
        tage_seit_letztem_login=tage_seit_login,
        logins_letzte_30_tage=logins,
    )


def generate_studis(count: int, seed: int | None = None) -> list[Studi]:
    rng = random.Random(seed)
    return [generate_studi(seed=rng.randint(0, 2**31 - 1)) for _ in range(count)]
