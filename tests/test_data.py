"""Tests for the synthetic data layer.

Locks down two invariants we care about for the frontend demo:

* Fixed profiles are stable, distinct, and internally consistent.
* The Faker-backed generator is reproducible under a seed and produces
  data the messaging agent can actually reason over (next exam in the
  future, graded exams in the past, login counts within bounds).
"""

from __future__ import annotations

from datetime import date

from llm_uv_template.data import fixed_profiles, generate_studi, generate_studis
from llm_uv_template.models import Pruefungsstatus


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
        if studi.naechste_pruefung is not None:
            assert studi.naechste_pruefung.datum >= today
            assert studi.naechste_pruefung.status == Pruefungsstatus.GEPLANT
        for p in studi.abgeschlossene_pruefungen:
            assert p.datum <= today
            assert p.status != Pruefungsstatus.GEPLANT
        assert 0 <= studi.campus_aktivitaet.logins_letzte_30_tage <= 30


def test_generate_studi_is_seeded_reproducible() -> None:
    a = generate_studi(seed=1234)
    b = generate_studi(seed=1234)
    assert a.model_dump() == b.model_dump()


def test_generate_studi_internal_consistency() -> None:
    today = date.today()
    studi = generate_studi(seed=7)
    if studi.naechste_pruefung is not None:
        assert studi.naechste_pruefung.datum > today
    for p in studi.abgeschlossene_pruefungen:
        assert p.datum < today


def test_generate_studis_returns_requested_count() -> None:
    assert len(generate_studis(count=3, seed=99)) == 3
