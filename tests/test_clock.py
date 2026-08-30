"""L'horloge : la seule source de temps, et celle que les tests déplacent."""

from datetime import UTC, datetime, timedelta

import pytest

from webradio.core.clock import HorlogeFigee, HorlogeSysteme

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def test_l_horloge_systeme_rend_un_instant_avec_fuseau() -> None:
    """Un instant sans fuseau produit des comparaisons fausses à la première
    frontière d'heure d'été, et elles ne se voient pas en test."""
    assert HorlogeSysteme().maintenant().tzinfo is not None


def test_l_horloge_figee_ne_bouge_pas_toute_seule() -> None:
    h = HorlogeFigee(MIDI)
    assert h.maintenant() == MIDI
    assert h.maintenant() == MIDI


def test_avancer_deplace_l_instant() -> None:
    h = HorlogeFigee(MIDI)
    h.avancer(timedelta(hours=2, minutes=30))
    assert h.maintenant() == datetime(2026, 8, 30, 14, 30, tzinfo=UTC)


def test_une_journee_entiere_se_deroule_sans_attendre() -> None:
    """C'est ce que l'injection achète : vingt-quatre heures en une boucle."""
    h = HorlogeFigee(MIDI)
    heures = []
    for _ in range(24):
        heures.append(h.maintenant().hour)
        h.avancer(timedelta(hours=1))
    assert heures == [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, *range(12)]


def test_aller_a_deplace_directement() -> None:
    h = HorlogeFigee(MIDI)
    h.aller_a(datetime(2026, 8, 31, 3, 0, tzinfo=UTC))
    assert h.maintenant() == datetime(2026, 8, 31, 3, 0, tzinfo=UTC)


def test_le_temps_ne_recule_pas() -> None:
    """Un test qui a besoin de reculer teste autre chose : mieux vaut qu'il
    échoue bruyamment que d'obtenir une chronologie impossible."""
    h = HorlogeFigee(MIDI)
    with pytest.raises(ValueError, match="ne recule pas"):
        h.avancer(timedelta(hours=-1))
    with pytest.raises(ValueError, match="ne recule pas"):
        h.aller_a(MIDI - timedelta(seconds=1))


def test_une_horloge_sans_fuseau_est_refusee_a_la_construction() -> None:
    with pytest.raises(ValueError, match="sans fuseau"):
        HorlogeFigee(datetime(2026, 8, 30, 12, 0))  # noqa: DTZ001
