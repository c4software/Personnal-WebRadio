"""Le hasard : injecté, semé, et rejouable."""

import pytest

from webradio.core.rng import HasardReel, HasardScripte

PISTES = ["a", "b", "c", "d", "e"]


def test_une_meme_graine_rejoue_la_meme_emission() -> None:
    """C'est la raison d'être de ce module : une soirée dont l'enchaînement
    déplaît doit pouvoir être rejouée à l'identique pour comprendre pourquoi."""
    un = [HasardReel(graine=42).choisir(PISTES) for _ in range(1)]
    premier = HasardReel(graine=42)
    second = HasardReel(graine=42)
    assert [premier.choisir(PISTES) for _ in range(20)] == [
        second.choisir(PISTES) for _ in range(20)
    ]
    assert un  # la suite est bien produite


def test_deux_graines_differentes_donnent_des_suites_differentes() -> None:
    a = [HasardReel(graine=1).choisir(PISTES) for _ in range(1)]
    suite_a = HasardReel(graine=1)
    suite_b = HasardReel(graine=2)
    tirages_a = [suite_a.choisir(PISTES) for _ in range(30)]
    tirages_b = [suite_b.choisir(PISTES) for _ in range(30)]
    assert tirages_a != tirages_b
    assert a


def test_le_tirage_reste_dans_la_suite_proposee() -> None:
    tireur = HasardReel(graine=7)
    for _ in range(50):
        assert tireur.choisir(PISTES) in PISTES


def test_tirer_dans_une_suite_vide_est_refuse() -> None:
    """Le repli — plage thématique sans musique, fenêtre trop étroite — se
    décide au-dessus, avec le contexte. Ici, on refuse plutôt que d'inventer."""
    with pytest.raises(ValueError, match="suite vide"):
        HasardReel(graine=1).choisir([])
    with pytest.raises(ValueError, match="suite vide"):
        HasardScripte([0]).choisir([])


def test_le_hasard_scripte_sort_ce_que_le_test_a_ecrit() -> None:
    tireur = HasardScripte([0, 2, 4])
    assert [tireur.choisir(PISTES) for _ in range(3)] == ["a", "c", "e"]


def test_le_hasard_scripte_ramene_un_indice_trop_grand_dans_la_suite() -> None:
    """Un test qui écrit `[7]` sur trois pistes veut la deuxième, pas une
    erreur : le script décrit une intention, pas une adresse mémoire."""
    assert HasardScripte([7]).choisir(["a", "b", "c"]) == "b"


def test_un_script_epuise_echoue_bruyamment() -> None:
    """Un script trop court signale un test qui tire plus qu'il ne croyait —
    le laisser boucler masquerait l'écart."""
    tireur = HasardScripte([0])
    tireur.choisir(PISTES)
    with pytest.raises(ValueError, match="épuisé"):
        tireur.choisir(PISTES)
