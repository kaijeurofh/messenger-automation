"""Tests for the synthetic data layer.

Locks down two invariants we care about for the frontend demo:

* Fixed profiles are stable, distinct, and internally consistent.
* The Faker-backed generator is reproducible under a seed and produces
  data the messaging agent can actually reason over: ein optionales
  ``letztes_modul`` in der Vergangenheit und kommende Module, deren
  Prüfungstermine in der Zukunft liegen.
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
        if studi.letztes_modul is not None:
            assert studi.letztes_modul.abgeschlossen_am <= today
            assert studi.letztes_modul.status in {
                Modulstatus.BESTANDEN,
                Modulstatus.NICHT_BESTANDEN,
            }
        for modul in studi.kommende_module:
            if modul.geplante_pruefung is not None:
                assert modul.geplante_pruefung >= today, (
                    f"Geplante Prüfung für {modul.name} darf nicht in der "
                    f"Vergangenheit liegen ({modul.geplante_pruefung})."
                )
        assert 0 <= studi.campus_aktivitaet.logins_letzte_30_tage <= 30


def test_fixed_profile_letztes_modul_not_in_kommende() -> None:
    """Kern-Invariante: das letzte (= bestandene/abgeschlossene) Modul
    darf nicht gleichzeitig in den kommenden Modulen auftauchen, sonst
    würde der Agent es als Lern-Empfehlung aufgreifen können."""
    for studi in fixed_profiles():
        if studi.letztes_modul is None:
            continue
        if studi.letztes_modul.status != Modulstatus.BESTANDEN:
            # Ein nicht bestandenes Modul *darf* als Wiederholung wieder
            # in `kommende_module` stehen — das ist der ganze Sinn der
            # Wiederholungsregel.
            continue
        kommende_namen = {m.name for m in studi.kommende_module}
        assert studi.letztes_modul.name not in kommende_namen, (
            f"{studi.id}: bestandenes Modul {studi.letztes_modul.name!r} "
            f"darf nicht erneut in kommende_module stehen."
        )


def test_generate_studi_is_seeded_reproducible() -> None:
    a = generate_studi(seed=1234)
    b = generate_studi(seed=1234)
    assert a.model_dump() == b.model_dump()


def test_generate_studi_internal_consistency() -> None:
    today = date.today()
    studi = generate_studi(seed=7)
    if studi.letztes_modul is not None:
        assert studi.letztes_modul.abgeschlossen_am < today
    for modul in studi.kommende_module:
        if modul.geplante_pruefung is not None:
            assert modul.geplante_pruefung > today


def test_generate_studi_does_not_recycle_letztes_modul() -> None:
    """Generierte Profile dürfen das letzte Modul nicht als kommendes
    Modul wiederverwenden — sonst empfiehlt der Agent Lernen für eine
    bereits bestandene Prüfung."""
    for seed in range(20):
        studi = generate_studi(seed=seed)
        if studi.letztes_modul is None:
            continue
        if studi.letztes_modul.status != Modulstatus.BESTANDEN:
            continue
        kommende_namen = {m.name for m in studi.kommende_module}
        assert studi.letztes_modul.name not in kommende_namen


def test_generate_studis_returns_requested_count() -> None:
    assert len(generate_studis(count=3, seed=99)) == 3
