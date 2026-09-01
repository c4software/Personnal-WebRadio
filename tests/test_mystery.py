"""Le thème tiré au sort : figé sur l'occurrence, jamais bloquant (GOAL-037)."""

from datetime import UTC, datetime, time

import pytest

from tests.fakes import FakeSource, track
from webradio.core.bands import Band
from webradio.core.mystery import RandomTheme
from webradio.core.rng import ScriptedRandom

CATALOGUE = [
    track("1", "Air", genre="electro"),
    track("2", "Moderat", genre="techno"),
    track("3", "Bill Evans", genre="jazz"),
]

SOIREE = Band(start=time(21), end=time(23), random_theme="genre")
SOIREE_ARTISTE = Band(start=time(21), end=time(23), random_theme="artist")


def test_un_genre_est_tire_dans_toute_la_bibliotheque() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]), min_tracks=1)
    contrainte = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.genre == "jazz"  # genres() rend electro, jazz, techno triés
    assert contrainte.artist is None


def test_un_artiste_se_tire_par_une_piste_de_la_bibliotheque() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0]), min_tracks=1)
    contrainte = tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.artist == "Air"
    assert contrainte.genre is None


def test_le_theme_tire_tient_jusqu_a_la_fin_de_l_occurrence() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]), min_tracks=1)
    debut = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    fin = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 22, 55, tzinfo=UTC))
    assert debut == fin
    # Un seul tirage : le script d'un seul indice n'a pas été épuisé deux fois.


def test_l_occurrence_suivante_retire() -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1, 0]), min_tracks=1)
    veille = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    lendemain = tirage.constraint_for(SOIREE, datetime(2026, 9, 1, 21, 5, tzinfo=UTC))
    assert veille is not None
    assert lendemain is not None
    assert veille.genre == "jazz"
    assert lendemain.genre == "electro"


def test_une_plage_de_nuit_garde_son_theme_apres_minuit() -> None:
    nuit = Band(start=time(22), end=time(2), random_theme="genre")
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([1]), min_tracks=1)
    avant = tirage.constraint_for(nuit, datetime(2026, 8, 31, 23, 0, tzinfo=UTC))
    apres = tirage.constraint_for(nuit, datetime(2026, 9, 1, 1, 30, tzinfo=UTC))
    assert avant == apres


def test_une_source_injoignable_rend_le_tirage_libre_sans_le_memoriser() -> None:
    source = FakeSource(CATALOGUE, injoignable=True)
    tirage = RandomTheme(source, ScriptedRandom([1]), min_tracks=1)
    instant = datetime(2026, 8, 31, 21, 5, tzinfo=UTC)
    assert tirage.constraint_for(SOIREE, instant) is None

    source.injoignable = False
    retente = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 10, tzinfo=UTC))
    assert retente is not None
    assert retente.genre == "jazz"


def test_une_bibliotheque_sans_genre_rend_le_tirage_libre() -> None:
    sans_genre = FakeSource([track("1", "Air")])
    tirage = RandomTheme(sans_genre, ScriptedRandom([0]), min_tracks=1)
    assert tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC)) is None


def test_une_bibliotheque_vide_rend_le_tirage_libre_pour_un_artiste() -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]), min_tracks=1)
    assert tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC)) is None


def test_un_echec_ne_se_journalise_qu_une_fois_par_occurrence(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]), min_tracks=1)
    with caplog.at_level("WARNING"):
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 9, tzinfo=UTC))
    assert len(caplog.records) == 1
    assert "tire librement" in caplog.records[0].getMessage()


def test_l_occurrence_suivante_signale_a_nouveau_son_echec(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource([]), ScriptedRandom([0]), min_tracks=1)
    with caplog.at_level("WARNING"):
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
        tirage.constraint_for(SOIREE_ARTISTE, datetime(2026, 9, 1, 21, 5, tzinfo=UTC))
    assert len(caplog.records) == 2


def test_un_genre_fantome_est_ecarte_et_un_genre_reel_sort_a_la_place(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # « Hip-Hop » est annoncé par la source mais ne rend aucune piste
    # (docs/subsonic.md §2.7.3) : le tirage l'écarte en le disant, et retire.
    source = FakeSource(CATALOGUE, genres_fantomes=("Hip-Hop",))
    tirage = RandomTheme(source, ScriptedRandom([0, 0]), min_tracks=1)
    with caplog.at_level("INFO"):
        contrainte = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.genre == "electro"  # genres() rend Hip-Hop, electro, jazz, techno triés
    assert "« Hip-Hop » écarté" in caplog.text


def test_un_genre_sous_le_plancher_est_ecarte() -> None:
    clairseme = [
        track("1", "Air", genre="electro"),
        track("2", "Daft Punk", genre="electro"),
        track("3", "Bill Evans", genre="jazz"),
    ]
    tirage = RandomTheme(FakeSource(clairseme), ScriptedRandom([1]), min_tracks=2)
    contrainte = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    # « jazz » (indice 1) n'a qu'une piste : écarté, « electro » reste seul.
    assert contrainte.genre == "electro"


def test_aucun_genre_au_plancher_rend_le_tirage_libre(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0, 0, 0]), min_tracks=5)
    with caplog.at_level("WARNING"):
        assert tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC)) is None
    assert "aucun genre n'atteint le plancher" in caplog.text


def test_un_plancher_nul_exige_quand_meme_une_piste() -> None:
    source = FakeSource(CATALOGUE, genres_fantomes=("Hip-Hop",))
    tirage = RandomTheme(source, ScriptedRandom([0, 0]), min_tracks=0)
    contrainte = tirage.constraint_for(SOIREE, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
    assert contrainte is not None
    assert contrainte.genre == "electro"


def test_une_plage_qui_ne_demande_aucun_tirage_est_refusee() -> None:
    ordinaire = Band(start=time(21), end=time(23), genres=("jazz",))
    tirage = RandomTheme(FakeSource(CATALOGUE), ScriptedRandom([0]), min_tracks=1)
    with pytest.raises(ValueError, match="aucun thème à tirer"):
        tirage.constraint_for(ordinaire, datetime(2026, 8, 31, 21, 5, tzinfo=UTC))
