"""La grille : ce qu'elle restreint, et ce qu'elle ne décide pas."""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.clock import HorlogeFigee
from webradio.core.grille import Grille, Plage
from webradio.core.rng import HasardReel, HasardScripte

MATIN = Plage(debut=time(8), fin=time(10), genres=("jazz",))
SOIR = Plage(debut=time(20), fin=time(23), genres=("electro",))


def a(heure: int, minute: int = 0) -> HorlogeFigee:
    return HorlogeFigee(datetime(2026, 8, 30, heure, minute, tzinfo=UTC))


def test_hors_de_toute_plage_le_tirage_est_libre() -> None:
    grille = Grille([MATIN, SOIR], a(15))
    assert grille.plage_courante() is None
    assert grille.genre_a_tirer(HasardReel(graine=1)) is None


def test_une_plage_impose_son_genre() -> None:
    assert Grille([MATIN, SOIR], a(9)).genre_a_tirer(HasardReel(graine=1)) == "jazz"
    assert Grille([MATIN, SOIR], a(21)).genre_a_tirer(HasardReel(graine=1)) == "electro"


def test_le_debut_de_plage_est_inclus_et_la_fin_exclue() -> None:
    """Sans cette convention, deux plages qui se touchent se recouvriraient
    d'une minute — et la seconde n'aurait jamais son heure pleine."""
    assert Grille([MATIN], a(8)).plage_courante() is MATIN
    assert Grille([MATIN], a(9, 59)).plage_courante() is MATIN
    assert Grille([MATIN], a(10)).plage_courante() is None


def test_une_plage_qui_enjambe_minuit_couvre_les_deux_cotes() -> None:
    nuit = Plage(debut=time(22), fin=time(2), genres=("ambient",))
    grille_avant = Grille([nuit], a(23))
    grille_apres = Grille([nuit], a(1))
    grille_dehors = Grille([nuit], a(12))
    assert grille_avant.plage_courante() is nuit
    assert grille_apres.plage_courante() is nuit
    assert grille_dehors.plage_courante() is None


def test_une_plage_a_plusieurs_genres_tranche_par_le_hasard_injecte() -> None:
    """La source n'accepte qu'un genre à la fois : le choix doit rester
    rejouable, donc il passe par le hasard injecté."""
    plage = Plage(debut=time(8), fin=time(10), genres=("jazz", "soul", "funk"))
    grille = Grille([plage], a(9))
    assert grille.genre_a_tirer(HasardScripte([1])) == "soul"
    premier = Grille([plage], a(9)).genre_a_tirer(HasardReel(graine=3))
    second = Grille([plage], a(9)).genre_a_tirer(HasardReel(graine=3))
    assert premier == second


def test_la_premiere_plage_declaree_l_emporte_sur_un_recouvrement() -> None:
    tot = Plage(debut=time(8), fin=time(12), genres=("jazz",))
    tard = Plage(debut=time(10), fin=time(14), genres=("rock",))
    assert Grille([tot, tard], a(11)).genre_a_tirer(HasardReel(graine=1)) == "jazz"
    assert Grille([tard, tot], a(11)).genre_a_tirer(HasardReel(graine=1)) == "rock"


def test_une_plage_sans_genre_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans genre"):
        Plage(debut=time(8), fin=time(10), genres=())


def test_une_plage_de_duree_nulle_est_refusee() -> None:
    with pytest.raises(ValueError, match="plage vide"):
        Plage(debut=time(8), fin=time(8), genres=("jazz",))


def test_une_grille_sans_plage_laisse_tout_le_tirage_libre() -> None:
    grille = Grille([], a(9))
    assert grille.plages == ()
    assert grille.genre_a_tirer(HasardReel(graine=1)) is None


def test_un_morceau_tire_dans_une_plage_n_est_pas_repris_par_la_suivante() -> None:
    """SPECS.md §7 n°5 : la grille n'est consultée qu'au tirage. Un morceau
    tiré à 09 h 58 finit dans « jazz », même s'il déborde sur 10 h — et rien,
    ici, n'a de quoi le lui reprendre."""
    horloge = HorlogeFigee(datetime(2026, 8, 30, 9, 58, tzinfo=UTC))
    grille = Grille([MATIN], horloge)
    genre_au_tirage = grille.genre_a_tirer(HasardReel(graine=1))
    horloge.avancer(timedelta(minutes=6))
    assert genre_au_tirage == "jazz"
    assert grille.plage_courante() is None


def test_une_journee_entiere_se_deroule_en_une_boucle_et_se_rejoue() -> None:
    """L'horloge est figée, la graine est fixée : vingt-quatre heures de
    programmation tiennent en quelques millisecondes, deux fois de suite."""

    def journee() -> list[str | None]:
        horloge = HorlogeFigee(datetime(2026, 8, 30, tzinfo=UTC))
        grille = Grille([MATIN, SOIR], horloge)
        hasard = HasardReel(graine=99)
        genres: list[str | None] = []
        for _ in range(24):
            genres.append(grille.genre_a_tirer(hasard))
            horloge.avancer(timedelta(hours=1))
        return genres

    premiere = journee()
    assert premiere == journee()
    assert premiere[9] == "jazz"
    assert premiere[21] == "electro"
    assert premiere[15] is None
