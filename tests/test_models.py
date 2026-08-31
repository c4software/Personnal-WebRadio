"""Les modèles refusent ce qui rendrait une règle inapplicable plus loin."""

from datetime import timedelta

import pytest

from tests.fakes import track
from webradio.core.models import Track


def test_une_piste_porte_ce_qu_il_faut_pour_decider() -> None:
    p = track("id1", "Bowie", genre="rock", secondes=210)
    assert p.artist == "Bowie"
    assert p.genre == "rock"
    assert p.duration == timedelta(seconds=210)


def test_une_piste_est_immuable() -> None:
    """Une piste qui change en cours de file rendrait la fenêtre de
    non-répétition incohérente avec ce qui a réellement été joué."""
    p = track("id1", "Bowie")
    with pytest.raises(AttributeError):
        p.artist = "autre"  # type: ignore[misc]


def test_le_genre_peut_manquer() -> None:
    """Une bibliothèque réelle a des morceaux sans étiquette : les refuser
    reviendrait à amputer la radio de ce que Navidrome ne sait pas classer."""
    assert track("id1", "Bowie", genre=None).genre is None


def test_une_piste_sans_identifiant_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans identifiant"):
        Track("", "t", "Bowie", None, timedelta(seconds=1))


def test_une_piste_sans_artiste_est_refusee() -> None:
    """Sans artiste, la règle de non-répétition n'a rien sur quoi s'appliquer."""
    with pytest.raises(ValueError, match="sans artiste"):
        Track("id", "t", "", None, timedelta(seconds=1))


@pytest.mark.parametrize("secondes", [0, -1])
def test_une_duree_nulle_ou_negative_est_refusee(secondes: int) -> None:
    """La programmation des jingles se calcule sur les durées : une durée
    fausse ferait glisser toute la grille sans que rien ne le signale."""
    with pytest.raises(ValueError, match="durée non valable"):
        Track("id", "t", "Bowie", None, timedelta(seconds=secondes))


def test_une_piste_sans_annee_reste_valable() -> None:
    """6,7 % de la bibliothèque réelle n'a pas d'année (docs/subsonic.md §4.1) :
    la refuser amputerait la radio, elle ne participe juste pas aux époques."""
    assert track("id1", "Bowie").year is None


def test_l_annee_est_portee_quand_la_bibliotheque_la_connait() -> None:
    assert track("id1", "Bowie", year=1977).year == 1977
