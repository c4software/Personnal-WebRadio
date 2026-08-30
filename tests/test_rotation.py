"""La non-répétition : ce qu'elle interdit, et ce qu'elle cède plutôt que bloquer."""

import pytest

from tests.fakes import track
from webradio.core.rotation import DEFAULT_ARTIST_GAP, Window


def test_la_largeur_par_defaut_est_celle_de_la_specification() -> None:
    assert DEFAULT_ARTIST_GAP == 5
    assert Window().width == 5


def test_un_artiste_qui_vient_de_passer_est_refuse() -> None:
    f = Window(width=3)
    f.remember(track("1", "Bowie"))
    assert not f.allows(track("2", "Bowie"))


def test_un_artiste_ressort_de_la_fenetre_apres_n_autres() -> None:
    f = Window(width=3)
    f.remember(track("1", "Bowie"))
    for i, a in enumerate(["Air", "Portishead"], start=2):
        f.remember(track(str(i), a))
        assert not f.allows(track("x", "Bowie")), f"Bowie ne devrait pas encore ressortir après {a}"
    f.remember(track("4", "Massive Attack"))
    assert f.allows(track("x", "Bowie"))


def test_la_regle_compte_des_artistes_pas_des_morceaux() -> None:
    """Trois titres d'affilée du même artiste ne comptent que pour un.

    Sans cela, un enchaînement `encore` ferait sortir un artiste de plus à
    chaque titre et viderait la fenêtre — l'inverse de ce qu'elle protège."""
    f = Window(width=3)
    f.remember(track("1", "Air"))
    f.remember(track("2", "Bowie"))
    f.remember(track("3", "Bowie"))
    f.remember(track("4", "Bowie"))
    assert list(f.artists) == ["Bowie", "Air"]


def test_filtrer_ecarte_les_artistes_recents() -> None:
    f = Window(width=2)
    f.remember(track("1", "Bowie"))
    restant = f.filter_out([track("2", "Bowie"), track("3", "Air"), track("4", "Bowie")])
    assert [p.artist for p in restant] == ["Air"]


def test_une_largeur_nulle_desactive_la_regle() -> None:
    f = Window(width=0)
    f.remember(track("1", "Bowie"))
    assert f.allows(track("2", "Bowie"))
    assert list(f.artists) == []


def test_une_largeur_negative_est_refusee() -> None:
    with pytest.raises(ValueError, match="largeur négative"):
        Window(width=-1)


def test_retrecir_relache_le_plus_ancien_d_abord() -> None:
    """C'est le sens du rétrécissement : on rend d'abord ce qu'on a le moins
    récemment entendu."""
    f = Window(width=3)
    for i, a in enumerate(["Air", "Bowie", "Portishead"], start=1):
        f.remember(track(str(i), a))
    assert list(f.artists) == ["Portishead", "Bowie", "Air"]
    assert f.shrink()
    assert list(f.artists) == ["Portishead", "Bowie"]
    assert f.allows(track("x", "Air"))


def test_retrecir_une_fenetre_vide_rend_faux() -> None:
    """L'appelant doit pouvoir distinguer « j'ai relâché » de « je n'ai plus
    rien à relâcher » : sans cela, une bibliothèque vide ferait boucler la
    file indéfiniment."""
    f = Window(width=3)
    assert not f.shrink()


def test_une_bibliotheque_de_trois_artistes_ne_bloque_pas() -> None:
    """Le cas que SPECS.md §4.2 nomme : elle joue en alternant trois artistes,
    elle ne s'arrête pas."""
    catalogue = [track("1", "Air"), track("2", "Bowie"), track("3", "Portishead")]
    f = Window(width=5)
    for p in catalogue:
        f.remember(p)
    assert f.filter_out(catalogue) == []
    while not f.filter_out(catalogue) and f.shrink():
        pass
    assert [p.artist for p in f.filter_out(catalogue)] == ["Air"]
