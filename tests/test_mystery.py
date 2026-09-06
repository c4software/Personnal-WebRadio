"""Le thème tiré au sort : figé sur l'occurrence, jamais bloquant (GOAL-037)."""

import logging
from datetime import UTC, datetime, time, timedelta

import pytest

from tests.fakes import FakeSource, track
from webradio.core.bands import Band, Constraint
from webradio.core.mystery import MEMOIRE_MAX, RandomTheme
from webradio.core.rng import ScriptedRandom

CATALOGUE = [
    track("1", "Air", genre="electro"),
    track("2", "Moderat", genre="techno"),
    track("3", "Bill Evans", genre="jazz"),
]

SOIREE = Band(start=time(21), end=time(23), random_theme="genre")
SOIREE_ARTISTE = Band(start=time(21), end=time(23), random_theme="artist")


def test_un_genre_est_tire_dans_toute_la_bibliotheque() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]))
    contrainte = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.genre == "jazz"  # genres() rend electro, jazz, techno triés
    assert contrainte.artist is None


def test_un_artiste_se_tire_par_une_piste_de_la_bibliotheque() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0]))
    contrainte = tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.artist == "Air"
    assert contrainte.genre is None


def test_le_theme_tire_tient_jusqu_a_la_fin_de_l_occurrence() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]))
    debut = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    fin = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 22, 55, tzinfo=UTC))
    assert debut == fin
    # Un seul tirage : le script d'un seul indice n'a pas été épuisé deux fois.


def test_l_occurrence_suivante_retire() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1, 0]))
    veille = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    lendemain = tirage.constraint_for(SOIREE, datetime(2026, 9, 1, 21, 5, tzinfo=UTC))
    assert veille is not None
    assert lendemain is not None
    assert veille.genre == "jazz"
    assert lendemain.genre == "electro"


def test_une_plage_de_nuit_garde_son_theme_apres_minuit() -> None:
    nuit = Band(start=time(22), end=time(2), random_theme="genre")
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]))
    avant = tirage.constraint_for(nuit, datetime(2026, 8, 31, 23, 0, tzinfo=UTC))
    apres = tirage.constraint_for(nuit, datetime(2026, 9, 1, 1, 30, tzinfo=UTC))
    assert avant == apres


def test_une_source_injoignable_rend_le_tirage_libre_sans_le_memoriser() -> None:
    source = FakeSource(CATALOGUE, injoignable=True)
    tirage = RandomTheme(source, ScriptedRandom([1]))
    instant = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    assert tirage.constraint_for(SOIREE, instant) is None

    source.injoignable = False
    retente = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 10, tzinfo=UTC))
    assert retente is not None
    assert retente.genre == "jazz"


def test_une_bibliotheque_sans_genre_rend_le_tirage_libre() -> None:
    sans_genre = FakeSource([track("1", "Air")])
    tirage = RandomTheme(sans_genre, ScriptedRandom([0]))
    assert tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC)) is None


def test_une_bibliotheque_vide_rend_le_tirage_libre_pour_un_artiste() -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]))
    assert tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC)) is None


def test_un_echec_ne_se_journalise_qu_une_fois_par_occurrence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]))
    with caplog.at_level("WARNING"):
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 9, tzinfo=UTC))
    assert len(caplog.records) == 1
    assert "tire librement" in caplog.records[0].getMessage()


def test_l_occurrence_suivante_signale_a_nouveau_son_echec(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]))
    with caplog.at_level("WARNING"):
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 9, 1, 21, 5, tzinfo=UTC))
    assert len(caplog.records) == 2


def test_une_plage_qui_ne_demande_aucun_tirage_est_refusee() -> None:
    ordinaire = Band(start=time(21), end=time(23), genres=("jazz",))
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0]))
    with pytest.raises(ValueError, match="aucun thème à tirer"):
        tirage.constraint_for(ordinaire, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))


def test_retirer_donne_un_autre_theme_et_le_garde() -> None:
    """Le retirage écarte l'ancien thème ; le nouveau tient jusqu'à la fin de
    l'occurrence (GOAL-057)."""
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1, 0]))
    debut = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    premier = tirage.constraint_for(SOIREE, debut)
    assert premier is not None and premier.genre == "jazz"
    retire = tirage.redraw(SOIREE, datetime(2026, 8, 31, 21, 20, tzinfo=UTC))
    assert retire is not None
    assert retire.genre == "electro"  # l'indice 0 de [electro, techno] : jazz est écarté
    assert tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 22, 0, tzinfo=UTC)) == retire


def test_retirer_un_artiste_ecarte_l_ancien() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0, 0]))
    debut = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    assert tirage.constraint_for(SOIREE_ARTISTE, debut) == Constraint(artist="Air")
    assert tirage.redraw(SOIREE_ARTISTE, debut) == Constraint(artist="Moderat")


def test_retirer_sans_theme_encore_tire_est_un_tirage_ordinaire() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]))
    retire = tirage.redraw(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert retire is not None and retire.genre == "jazz"


def test_retirer_avec_un_seul_genre_rend_le_meme_en_le_disant(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource([track("1", "Air", genre="dub")]), ScriptedRandom([0, 0]))
    debut = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    assert tirage.constraint_for(SOIREE, debut) == Constraint(genre="dub")
    with caplog.at_level(logging.INFO):
        assert tirage.redraw(SOIREE, debut) == Constraint(genre="dub")
    assert "pas d'autre" in caplog.text


def test_retirer_hors_d_une_plage_au_hasard_est_refuse() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0]))
    declaree = Band(start=time(21), end=time(23), genres=("jazz",))
    with pytest.raises(ValueError, match="aucun thème"):
        tirage.redraw(declaree, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))


SOIREE_SUIVANTE = Band(start=time(23), end=time(1), random_theme="genre")


def test_une_occurrence_a_venir_ne_change_pas_le_theme_en_cours() -> None:
    """La préparation tire chaque titre d'avance sous le moment de son heure
    estimée (décision n°34) : elle demande donc le thème d'occurrences que
    l'antenne n'a pas encore atteintes. Ce thème-là ne doit rien effacer.

    Sans cela, la consultation d'une occurrence à venir remplace la mémoire, et
    la jonction suivante — qui redemande le moment courant — n'y retrouve plus
    rien et retire : la soirée change de thème en cours de route (GOAL-076).
    """
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1, 0, 2]))
    ce_soir = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)

    en_cours = tirage.constraint_for(SOIREE, ce_soir)
    tirage.constraint_for(SOIREE_SUIVANTE, datetime(2026, 8, 31, 23, 30, tzinfo=UTC))

    assert tirage.constraint_for(SOIREE, ce_soir) == en_cours


def test_chaque_plage_garde_son_propre_theme() -> None:
    """La mémoire tenait une seule entrée pour toutes les plages : deux plages
    `random` se la disputaient (GOAL-076)."""
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1, 0, 2, 1]))
    ce_soir = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    plus_tard = datetime(2026, 8, 31, 23, 30, tzinfo=UTC)

    premier = tirage.constraint_for(SOIREE, ce_soir)
    second = tirage.constraint_for(SOIREE_SUIVANTE, plus_tard)

    assert tirage.constraint_for(SOIREE, ce_soir) == premier
    assert tirage.constraint_for(SOIREE_SUIVANTE, plus_tard) == second


def test_une_soiree_trop_ancienne_finit_par_s_oublier() -> None:
    """La mémoire est bornée : sans cela, une radio qui tourne des mois
    retiendrait chaque soirée passée. Ce qui sort de la borne se retire, sans
    conséquence — personne ne rejoue une soirée d'il y a un mois (GOAL-076)."""
    indices = [1] + [0] * (MEMOIRE_MAX + 1) + [2]
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom(indices))
    premier_soir = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)

    ancien = tirage.constraint_for(SOIREE, premier_soir)
    for jour in range(1, MEMOIRE_MAX + 2):
        tirage.constraint_for(SOIREE, premier_soir + timedelta(days=jour))

    assert tirage.constraint_for(SOIREE, premier_soir) != ancien
