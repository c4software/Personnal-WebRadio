"""L'horloge : la seule source de temps, et celle que les tests déplacent."""

from datetime import UTC, datetime, timedelta

import pytest

from webradio.core.clock import FrozenClock, SystemClock

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_l_horloge_systeme_rend_un_instant_avec_fuseau() -> None:
    """Un instant sans fuseau donne des comparaisons fausses au changement
    d'heure, invisibles en test."""
    assert SystemClock().now().tzinfo is not None


def test_l_horloge_figee_ne_bouge_pas_toute_seule() -> None:
    h = FrozenClock(MIDI)
    assert h.now() == MIDI
    assert h.now() == MIDI


def test_avancer_deplace_l_instant() -> None:
    h = FrozenClock(MIDI)
    h.advance(timedelta(hours=2, minutes=30))
    assert h.now() == datetime(2026, 8, 30, 14, 30, tzinfo=UTC)


def test_une_journee_entiere_se_deroule_sans_attendre() -> None:
    """Vingt-quatre heures en une boucle, grâce à l'horloge injectée."""
    h = FrozenClock(MIDI)
    hours = []
    for _ in range(24):
        hours.append(h.now().hour)
        h.advance(timedelta(hours=1))
    assert hours == [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, *range(12)]


def test_aller_a_deplace_directement() -> None:
    h = FrozenClock(MIDI)
    h.jump_to(datetime(2026, 8, 31, 3, 0, tzinfo=UTC))
    assert h.now() == datetime(2026, 8, 31, 3, 0, tzinfo=UTC)


def test_le_temps_ne_recule_pas() -> None:
    """Un test qui recule teste autre chose ; mieux vaut échouer que produire
    une chronologie impossible."""
    h = FrozenClock(MIDI)
    with pytest.raises(ValueError, match="ne recule pas"):
        h.advance(timedelta(hours=-1))
    with pytest.raises(ValueError, match="ne recule pas"):
        h.jump_to(MIDI - timedelta(seconds=1))


def test_une_horloge_sans_fuseau_est_refusee_a_la_construction() -> None:
    with pytest.raises(ValueError, match="sans fuseau"):
        FrozenClock(datetime(2026, 8, 30, 12, 0))  # noqa: DTZ001
