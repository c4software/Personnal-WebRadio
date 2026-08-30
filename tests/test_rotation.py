"""La non-répétition : ce qu'elle interdit, et ce qu'elle cède plutôt que bloquer."""

import pytest

from tests.fakes import piste
from webradio.core.rotation import DEFAUT_NON_REPETITION, Fenetre


def test_la_largeur_par_defaut_est_celle_de_la_specification() -> None:
    assert DEFAUT_NON_REPETITION == 5
    assert Fenetre().largeur == 5


def test_un_artiste_qui_vient_de_passer_est_refuse() -> None:
    f = Fenetre(largeur=3)
    f.retenir(piste("1", "Bowie"))
    assert not f.autorise(piste("2", "Bowie"))


def test_un_artiste_ressort_de_la_fenetre_apres_n_autres() -> None:
    f = Fenetre(largeur=3)
    f.retenir(piste("1", "Bowie"))
    for i, a in enumerate(["Air", "Portishead"], start=2):
        f.retenir(piste(str(i), a))
        assert not f.autorise(piste("x", "Bowie")), (
            f"Bowie ne devrait pas encore ressortir après {a}"
        )
    f.retenir(piste("4", "Massive Attack"))
    assert f.autorise(piste("x", "Bowie"))


def test_la_regle_compte_des_artistes_pas_des_morceaux() -> None:
    """Trois titres d'affilée du même artiste ne comptent que pour un.

    Sans cela, un enchaînement `encore` ferait sortir un artiste de plus à
    chaque titre et viderait la fenêtre — l'inverse de ce qu'elle protège."""
    f = Fenetre(largeur=3)
    f.retenir(piste("1", "Air"))
    f.retenir(piste("2", "Bowie"))
    f.retenir(piste("3", "Bowie"))
    f.retenir(piste("4", "Bowie"))
    assert list(f.artistes) == ["Bowie", "Air"]


def test_filtrer_ecarte_les_artistes_recents() -> None:
    f = Fenetre(largeur=2)
    f.retenir(piste("1", "Bowie"))
    restant = f.filtrer([piste("2", "Bowie"), piste("3", "Air"), piste("4", "Bowie")])
    assert [p.artiste for p in restant] == ["Air"]


def test_une_largeur_nulle_desactive_la_regle() -> None:
    f = Fenetre(largeur=0)
    f.retenir(piste("1", "Bowie"))
    assert f.autorise(piste("2", "Bowie"))
    assert list(f.artistes) == []


def test_une_largeur_negative_est_refusee() -> None:
    with pytest.raises(ValueError, match="largeur négative"):
        Fenetre(largeur=-1)


def test_retrecir_relache_le_plus_ancien_d_abord() -> None:
    """C'est le sens du rétrécissement : on rend d'abord ce qu'on a le moins
    récemment entendu."""
    f = Fenetre(largeur=3)
    for i, a in enumerate(["Air", "Bowie", "Portishead"], start=1):
        f.retenir(piste(str(i), a))
    assert list(f.artistes) == ["Portishead", "Bowie", "Air"]
    assert f.retrecir()
    assert list(f.artistes) == ["Portishead", "Bowie"]
    assert f.autorise(piste("x", "Air"))


def test_retrecir_une_fenetre_vide_rend_faux() -> None:
    """L'appelant doit pouvoir distinguer « j'ai relâché » de « je n'ai plus
    rien à relâcher » : sans cela, une bibliothèque vide ferait boucler la
    file indéfiniment."""
    f = Fenetre(largeur=3)
    assert not f.retrecir()


def test_une_bibliotheque_de_trois_artistes_ne_bloque_pas() -> None:
    """Le cas que SPECS.md §4.2 nomme : elle joue en alternant trois artistes,
    elle ne s'arrête pas."""
    catalogue = [piste("1", "Air"), piste("2", "Bowie"), piste("3", "Portishead")]
    f = Fenetre(largeur=5)
    for p in catalogue:
        f.retenir(p)
    assert f.filtrer(catalogue) == []
    while not f.filtrer(catalogue) and f.retrecir():
        pass
    assert [p.artiste for p in f.filtrer(catalogue)] == ["Air"]
