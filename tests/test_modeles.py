"""Les modèles refusent ce qui rendrait une règle inapplicable plus loin."""

from datetime import timedelta

import pytest

from tests.fakes import piste
from webradio.core.modeles import Piste


def test_une_piste_porte_ce_qu_il_faut_pour_decider() -> None:
    p = piste("id1", "Bowie", genre="rock", secondes=210)
    assert p.artiste == "Bowie"
    assert p.genre == "rock"
    assert p.duree == timedelta(seconds=210)


def test_une_piste_est_immuable() -> None:
    """Une piste qui change en cours de file rendrait la fenêtre de
    non-répétition incohérente avec ce qui a réellement été joué."""
    p = piste("id1", "Bowie")
    with pytest.raises(AttributeError):
        p.artiste = "autre"  # type: ignore[misc]


def test_le_genre_peut_manquer() -> None:
    """Une bibliothèque réelle a des morceaux sans étiquette : les refuser
    reviendrait à amputer la radio de ce que Navidrome ne sait pas classer."""
    assert piste("id1", "Bowie", genre=None).genre is None


def test_une_piste_sans_identifiant_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans identifiant"):
        Piste("", "t", "Bowie", None, timedelta(seconds=1))


def test_une_piste_sans_artiste_est_refusee() -> None:
    """Sans artiste, la règle de non-répétition n'a rien sur quoi s'appliquer."""
    with pytest.raises(ValueError, match="sans artiste"):
        Piste("id", "t", "", None, timedelta(seconds=1))


@pytest.mark.parametrize("secondes", [0, -1])
def test_une_duree_nulle_ou_negative_est_refusee(secondes: int) -> None:
    """La programmation des jingles se calcule sur les durées : une durée
    fausse ferait glisser toute la grille sans que rien ne le signale."""
    with pytest.raises(ValueError, match="durée non valable"):
        Piste("id", "t", "Bowie", None, timedelta(seconds=secondes))
