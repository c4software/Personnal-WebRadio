"""La grille : ce qu'elle restreint, et ce qu'elle ne décide pas."""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.bands import Band, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.rng import RealRandom, ScriptedRandom

MATIN = Band(start=time(8), end=time(10), genres=("jazz",))
SOIR = Band(start=time(20), end=time(23), genres=("electro",))


def a(hour: int, minute: int = 0) -> FrozenClock:
    return FrozenClock(datetime(2026, 8, 30, hour, minute, tzinfo=UTC))


def test_hors_de_toute_plage_le_tirage_est_libre() -> None:
    grille = Schedule([MATIN, SOIR], a(15))
    assert grille.current_band() is None
    assert grille.genre_to_draw(RealRandom(graine=1)) is None


def test_une_plage_impose_son_genre() -> None:
    assert Schedule([MATIN, SOIR], a(9)).genre_to_draw(RealRandom(graine=1)) == "jazz"
    assert Schedule([MATIN, SOIR], a(21)).genre_to_draw(RealRandom(graine=1)) == "electro"


def test_le_debut_de_plage_est_inclus_et_la_fin_exclue() -> None:
    """Sans cette convention, deux plages qui se touchent se recouvriraient
    d'une minute — et la seconde n'aurait jamais son heure pleine."""
    assert Schedule([MATIN], a(8)).current_band() is MATIN
    assert Schedule([MATIN], a(9, 59)).current_band() is MATIN
    assert Schedule([MATIN], a(10)).current_band() is None


def test_une_plage_qui_enjambe_minuit_couvre_les_deux_cotes() -> None:
    nuit = Band(start=time(22), end=time(2), genres=("ambient",))
    grille_avant = Schedule([nuit], a(23))
    grille_apres = Schedule([nuit], a(1))
    grille_dehors = Schedule([nuit], a(12))
    assert grille_avant.current_band() is nuit
    assert grille_apres.current_band() is nuit
    assert grille_dehors.current_band() is None


def test_une_plage_a_plusieurs_genres_tranche_par_le_hasard_injecte() -> None:
    """La source n'accepte qu'un genre à la fois : le choix doit rester
    rejouable, donc il passe par le hasard injecté."""
    band = Band(start=time(8), end=time(10), genres=("jazz", "soul", "funk"))
    grille = Schedule([band], a(9))
    assert grille.genre_to_draw(ScriptedRandom([1])) == "soul"
    premier = Schedule([band], a(9)).genre_to_draw(RealRandom(graine=3))
    second = Schedule([band], a(9)).genre_to_draw(RealRandom(graine=3))
    assert premier == second


def test_la_premiere_plage_declaree_l_emporte_sur_un_recouvrement() -> None:
    tot = Band(start=time(8), end=time(12), genres=("jazz",))
    tard = Band(start=time(10), end=time(14), genres=("rock",))
    assert Schedule([tot, tard], a(11)).genre_to_draw(RealRandom(graine=1)) == "jazz"
    assert Schedule([tard, tot], a(11)).genre_to_draw(RealRandom(graine=1)) == "rock"


def test_une_plage_sans_genre_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans genre"):
        Band(start=time(8), end=time(10), genres=())


def test_une_plage_de_duree_nulle_est_refusee() -> None:
    with pytest.raises(ValueError, match="plage vide"):
        Band(start=time(8), end=time(8), genres=("jazz",))


def test_une_grille_sans_plage_laisse_tout_le_tirage_libre() -> None:
    grille = Schedule([], a(9))
    assert grille.bands == ()
    assert grille.genre_to_draw(RealRandom(graine=1)) is None


def test_un_morceau_tire_dans_une_plage_n_est_pas_repris_par_la_suivante() -> None:
    """SPECS.md §7 n°5 : la grille n'est consultée qu'au tirage. Un morceau
    tiré à 09 h 58 finit dans « jazz », même s'il déborde sur 10 h — et rien,
    ici, n'a de quoi le lui reprendre."""
    clock = FrozenClock(datetime(2026, 8, 30, 9, 58, tzinfo=UTC))
    grille = Schedule([MATIN], clock)
    genre_au_tirage = grille.genre_to_draw(RealRandom(graine=1))
    clock.advance(timedelta(minutes=6))
    assert genre_au_tirage == "jazz"
    assert grille.current_band() is None


def test_une_journee_entiere_se_deroule_en_une_boucle_et_se_rejoue() -> None:
    """L'horloge est figée, la graine est fixée : vingt-quatre heures de
    programmation tiennent en quelques millisecondes, deux fois de suite."""

    def journee() -> list[str | None]:
        clock = FrozenClock(datetime(2026, 8, 30, tzinfo=UTC))
        grille = Schedule([MATIN, SOIR], clock)
        random = RealRandom(graine=99)
        genres: list[str | None] = []
        for _ in range(24):
            genres.append(grille.genre_to_draw(random))
            clock.advance(timedelta(hours=1))
        return genres

    premiere = journee()
    assert premiere == journee()
    assert premiere[9] == "jazz"
    assert premiere[21] == "electro"
    assert premiere[15] is None
