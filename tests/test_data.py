"""Tests for the synthetic data layer.

Locks down die Invarianten, die für den Coach kritisch sind:

* Fixed profiles sind stabil, eindeutig und konsistent.
* Generator ist seed-reproduzierbar.
* EAP-Constraint: max. 5 aktuelle Module.
* Empfehlungs-Sicherheit: ein *bestandenes* Modul taucht nie in den
  aktuellen Modulen auf (sonst würde der Agent es als Lernziel sehen).
* Wiederholungen dürfen das, weil sie aktiv wieder belegt sind.
* Prüfungsanmeldungen referenzieren nur aktive Module.
* Studienheft-Ereignisse liegen in der Vergangenheit und referenzieren
  ein aktuelles Modul.
"""

from __future__ import annotations

from datetime import date

from llm_uv_template.data import fixed_profiles, generate_studi, generate_studis
from llm_uv_template.models import Modulstatus


def test_fixed_profiles_are_stable_and_unique() -> None:
    a = fixed_profiles()
    b = fixed_profiles()
    ids_a = [s.id for s in a]
    ids_b = [s.id for s in b]
    assert ids_a == ids_b
    assert len(set(ids_a)) == len(ids_a), "duplicate fixed-profile ids"
    assert len(ids_a) == 5


def test_fixed_profile_internal_consistency() -> None:
    today = date.today()
    for studi in fixed_profiles():
        assert studi.studienbeginn <= today
        assert len(studi.aktuelle_module) <= 5
        for am in studi.abgeschlossene_module:
            assert am.abgeschlossen_am <= today
            assert am.status in {Modulstatus.BESTANDEN, Modulstatus.NICHT_BESTANDEN}
        for ereignis in studi.studienheft_ereignisse:
            assert ereignis.zeitpunkt.date() <= today, (
                f"Studienheft-Ereignis {ereignis} liegt in der Zukunft"
            )
        for anmeldung in studi.pruefungsanmeldungen:
            assert anmeldung.angemeldet_am <= today
        assert 0 <= studi.campus_aktivitaet.logins_letzte_30_tage <= 30


def test_fixed_profile_bestandene_module_not_active() -> None:
    """Kern-Invariante: ein bestandenes Modul darf nicht zugleich aktiv
    belegt sein — sonst empfiehlt der Agent Lernen für eine bereits
    abgehakte Prüfung."""
    for studi in fixed_profiles():
        bestandene = {
            am.name for am in studi.abgeschlossene_module if am.status == Modulstatus.BESTANDEN
        }
        aktive = {m.name for m in studi.aktuelle_module}
        assert bestandene.isdisjoint(aktive), (
            f"{studi.id}: bestandene Module {bestandene & aktive} dürfen "
            f"nicht in aktuelle_module stehen."
        )


def test_fixed_profile_pruefungsanmeldungen_reference_active_modules() -> None:
    """Anmeldungen können nur für Module bestehen, die der Studi auch
    belegt hat — sonst wäre die Datenlage inkonsistent."""
    for studi in fixed_profiles():
        aktive = {m.name for m in studi.aktuelle_module}
        for anmeldung in studi.pruefungsanmeldungen:
            assert anmeldung.modul in aktive, (
                f"{studi.id}: Anmeldung für {anmeldung.modul!r} ohne entsprechendes aktives Modul."
            )


def test_fixed_profile_studienheft_events_reference_active_modules() -> None:
    """Studienheft-Aktivität gibt es nur für aktiv belegte Module."""
    for studi in fixed_profiles():
        aktive = {m.name for m in studi.aktuelle_module}
        for ereignis in studi.studienheft_ereignisse:
            assert ereignis.modul in aktive, (
                f"{studi.id}: Studienheft-Ereignis für {ereignis.modul!r} "
                f"ohne entsprechendes aktives Modul."
            )


def test_generate_studi_is_seeded_reproducible() -> None:
    a = generate_studi(seed=1234)
    b = generate_studi(seed=1234)
    assert a.model_dump() == b.model_dump()


def test_generate_studi_internal_consistency() -> None:
    today = date.today()
    studi = generate_studi(seed=7)
    assert len(studi.aktuelle_module) <= 5
    for am in studi.abgeschlossene_module:
        assert am.abgeschlossen_am < today
    for ereignis in studi.studienheft_ereignisse:
        assert ereignis.zeitpunkt.date() <= today
    for anmeldung in studi.pruefungsanmeldungen:
        assert anmeldung.angemeldet_am <= today


def test_generate_studi_bestandene_module_not_active() -> None:
    """Generierte Profile dürfen ein bestandenes Modul nicht als aktiv
    belegt führen — sonst empfiehlt der Agent Lernen für bereits
    bestandene Prüfungen."""
    for seed in range(20):
        studi = generate_studi(seed=seed)
        bestandene = {
            am.name for am in studi.abgeschlossene_module if am.status == Modulstatus.BESTANDEN
        }
        aktive = {m.name for m in studi.aktuelle_module}
        assert bestandene.isdisjoint(aktive), (
            f"seed={seed}: bestandene Module {bestandene & aktive} "
            f"dürfen nicht in aktuelle_module stehen."
        )


def test_generate_studi_anmeldungen_only_for_active_modules() -> None:
    for seed in range(20):
        studi = generate_studi(seed=seed)
        aktive = {m.name for m in studi.aktuelle_module}
        for anmeldung in studi.pruefungsanmeldungen:
            assert anmeldung.modul in aktive


def test_generate_studis_returns_requested_count() -> None:
    assert len(generate_studis(count=3, seed=99)) == 3
