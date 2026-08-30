"""Le hasard : injecté, semé, et rejouable."""

import pytest

from webradio.core.rng import RealRandom, ScriptedRandom

PISTES = ["a", "b", "c", "d", "e"]


def test_une_meme_graine_rejoue_la_meme_emission() -> None:
    """C'est la raison d'être de ce module : une soirée dont l'enchaînement
    déplaît doit pouvoir être rejouée à l'identique pour comprendre pourquoi."""
    un = [RealRandom(graine=42).pick(PISTES) for _ in range(1)]
    premier = RealRandom(graine=42)
    second = RealRandom(graine=42)
    assert [premier.pick(PISTES) for _ in range(20)] == [second.pick(PISTES) for _ in range(20)]
    assert un  # la suite est bien produite


def test_deux_graines_differentes_donnent_des_suites_differentes() -> None:
    a = [RealRandom(graine=1).pick(PISTES) for _ in range(1)]
    suite_a = RealRandom(graine=1)
    suite_b = RealRandom(graine=2)
    tirages_a = [suite_a.pick(PISTES) for _ in range(30)]
    tirages_b = [suite_b.pick(PISTES) for _ in range(30)]
    assert tirages_a != tirages_b
    assert a


def test_le_tirage_reste_dans_la_suite_proposee() -> None:
    tireur = RealRandom(graine=7)
    for _ in range(50):
        assert tireur.pick(PISTES) in PISTES


def test_tirer_dans_une_suite_vide_est_refuse() -> None:
    """Le repli — plage thématique sans musique, fenêtre trop étroite — se
    décide au-dessus, avec le contexte. Ici, on refuse plutôt que d'inventer."""
    with pytest.raises(ValueError, match="suite vide"):
        RealRandom(graine=1).pick([])
    with pytest.raises(ValueError, match="suite vide"):
        ScriptedRandom([0]).pick([])


def test_le_hasard_scripte_sort_ce_que_le_test_a_ecrit() -> None:
    tireur = ScriptedRandom([0, 2, 4])
    assert [tireur.pick(PISTES) for _ in range(3)] == ["a", "c", "e"]


def test_le_hasard_scripte_ramene_un_indice_trop_grand_dans_la_suite() -> None:
    """Un test qui écrit `[7]` sur trois pistes veut la deuxième, pas une
    erreur : le script décrit une intention, pas une adresse mémoire."""
    assert ScriptedRandom([7]).pick(["a", "b", "c"]) == "b"


def test_un_script_epuise_echoue_bruyamment() -> None:
    """Un script trop court signale un test qui tire plus qu'il ne croyait —
    le laisser boucler masquerait l'écart."""
    tireur = ScriptedRandom([0])
    tireur.pick(PISTES)
    with pytest.raises(ValueError, match="épuisé"):
        tireur.pick(PISTES)


UNIFORMES = [1.0] * len(PISTES)


def test_le_tirage_pondere_reste_rejouable_a_graine_et_poids_fixes() -> None:
    """Sans cela, on perdrait ce que l'injection du hasard avait acheté : une
    émission pondérée qui déplaît doit se rejouer à l'identique."""
    weight = [1.0, 0.25, 4.0, 1.0, 2.0]
    premier = RealRandom(graine=42)
    second = RealRandom(graine=42)
    assert [premier.pick_weighted(PISTES, weight) for _ in range(30)] == [
        second.pick_weighted(PISTES, weight) for _ in range(30)
    ]


def test_le_tirage_pondere_reste_dans_la_suite_proposee() -> None:
    tireur = RealRandom(graine=7)
    for _ in range(50):
        assert tireur.pick_weighted(PISTES, UNIFORMES) in PISTES


def test_un_poids_lourd_sort_plus_souvent_qu_un_poids_leger() -> None:
    """C'est tout ce que la pondération promet : la chance change, elle ne
    s'annule pas (SPECS.md §4.12)."""
    tireur = RealRandom(graine=3)
    weight = [16.0, 1.0, 1.0, 1.0, 1.0]
    tirages = [tireur.pick_weighted(PISTES, weight) for _ in range(400)]
    assert tirages.count("a") > tirages.count("b") * 3
    assert set(tirages) == set(PISTES)


def test_un_poids_nul_n_est_jamais_tire_mais_n_empeche_pas_les_autres() -> None:
    """Le plancher de SPECS.md §4.12 vaut 0,25, jamais zéro : un poids nul ne
    vient donc pas de la pondération, mais il ne doit pas casser le tirage."""
    tireur = RealRandom(graine=5)
    weight = [0.0, 1.0, 0.0, 1.0, 0.0]
    tirages = {tireur.pick_weighted(PISTES, weight) for _ in range(100)}
    assert tirages == {"b", "d"}


def test_un_poids_manquant_est_refuse() -> None:
    with pytest.raises(ValueError, match="la correspondance est perdue"):
        RealRandom(graine=1).pick_weighted(PISTES, [1.0, 1.0])


def test_un_poids_negatif_est_refuse() -> None:
    with pytest.raises(ValueError, match="poids négatif"):
        RealRandom(graine=1).pick_weighted(["a", "b"], [1.0, -1.0])


def test_des_poids_tous_nuls_sont_refuses() -> None:
    """Ils supprimeraient tout le monde, ce que SPECS.md §4.12 interdit."""
    with pytest.raises(ValueError, match="tous nuls"):
        RealRandom(graine=1).pick_weighted(["a", "b"], [0.0, 0.0])


def test_le_tirage_pondere_dans_une_suite_vide_est_refuse() -> None:
    with pytest.raises(ValueError, match="suite vide"):
        RealRandom(graine=1).pick_weighted([], [])


def test_le_hasard_scripte_pondere_sort_ce_que_le_test_a_ecrit() -> None:
    tireur = ScriptedRandom([4, 0])
    assert tireur.pick_weighted(PISTES, UNIFORMES) == "e"
    assert tireur.pick_weighted(PISTES, UNIFORMES) == "a"


def test_le_hasard_scripte_verifie_les_poids_comme_le_hasard_reel() -> None:
    """Un double plus indulgent que la production transforme la suite de tests
    en décor (AGENTS.md §4.1)."""
    with pytest.raises(ValueError, match="la correspondance est perdue"):
        ScriptedRandom([0]).pick_weighted(PISTES, [1.0])
