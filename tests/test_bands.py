"""La grille : ce qu'elle restreint, et ce qu'elle ne décide pas."""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.bands import Band, Constraint, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.rng import Random, RealRandom, ScriptedRandom
from webradio.core.runs import Mode

MATIN = Band(start=time(8), end=time(10), genres=("jazz",))
SOIR = Band(start=time(20), end=time(23), genres=("electro",))


def a(hour: int, minute: int = 0) -> FrozenClock:
    return FrozenClock(datetime(2026, 8, 30, hour, minute, tzinfo=UTC))


def _genre(grille: Schedule, random: Random) -> str | None:
    """Le genre tiré, à travers la contrainte (GOAL-023)."""
    contrainte = grille.constraint_to_draw(random)
    return None if contrainte is None else contrainte.genre


def test_hors_de_toute_plage_le_tirage_est_libre() -> None:
    grille = Schedule([MATIN, SOIR], a(15))
    assert grille.current_band() is None
    assert _genre(grille, RealRandom(graine=1)) is None


def test_une_plage_impose_son_genre() -> None:
    assert _genre(Schedule([MATIN, SOIR], a(9)), RealRandom(graine=1)) == "jazz"
    assert _genre(Schedule([MATIN, SOIR], a(21)), RealRandom(graine=1)) == "electro"


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
    assert _genre(grille, ScriptedRandom([1])) == "soul"
    premier = _genre(Schedule([band], a(9)), RealRandom(graine=3))
    second = _genre(Schedule([band], a(9)), RealRandom(graine=3))
    assert premier == second


def test_la_premiere_plage_declaree_l_emporte_sur_un_recouvrement() -> None:
    tot = Band(start=time(8), end=time(12), genres=("jazz",))
    tard = Band(start=time(10), end=time(14), genres=("rock",))
    assert _genre(Schedule([tot, tard], a(11)), RealRandom(graine=1)) == "jazz"
    assert _genre(Schedule([tard, tot], a(11)), RealRandom(graine=1)) == "rock"


def test_une_plage_sans_genre_ni_artiste_est_refusee() -> None:
    with pytest.raises(ValueError, match="exactement un des trois"):
        Band(start=time(8), end=time(10), genres=())


def test_une_plage_de_duree_nulle_est_refusee() -> None:
    with pytest.raises(ValueError, match="plage vide"):
        Band(start=time(8), end=time(8), genres=("jazz",))


def test_une_grille_sans_plage_laisse_tout_le_tirage_libre() -> None:
    grille = Schedule([], a(9))
    assert grille.bands == ()
    assert _genre(grille, RealRandom(graine=1)) is None


def test_un_morceau_tire_dans_une_plage_n_est_pas_repris_par_la_suivante() -> None:
    """SPECS.md §7 n°5 : la grille n'est consultée qu'au tirage. Un morceau
    tiré à 09 h 58 finit dans « jazz », même s'il déborde sur 10 h — et rien,
    ici, n'a de quoi le lui reprendre."""
    clock = FrozenClock(datetime(2026, 8, 30, 9, 58, tzinfo=UTC))
    grille = Schedule([MATIN], clock)
    genre_au_tirage = _genre(grille, RealRandom(graine=1))
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
            genres.append(_genre(grille, random))
            clock.advance(timedelta(hours=1))
        return genres

    premiere = journee()
    assert premiere == journee()
    assert premiere[9] == "jazz"
    assert premiere[21] == "electro"
    assert premiere[15] is None


# ── Les plages par jour (GOAL-019) ──────────────────────────────────────────


def test_sans_jour_declare_une_plage_vaut_tous_les_jours() -> None:
    # Le 2026-08-30 est un dimanche.
    assert Schedule([MATIN], a(9)).current_band() is MATIN


def test_une_plage_restreinte_a_un_jour_ne_vaut_que_ce_jour() -> None:
    dimanche = Band(start=time(8), end=time(10), genres=("gospel",), days=("sunday",))
    lundi = Band(start=time(8), end=time(10), genres=("jazz",), days=("monday",))
    assert Schedule([lundi, dimanche], a(9)).current_band() is dimanche


def test_une_plage_de_nuit_appartient_au_jour_ou_elle_commence() -> None:
    """« samedi 22 h → 02 h » couvre dimanche 01 h, pas dimanche 23 h."""
    nuit = Band(start=time(22), end=time(2), genres=("électro",), days=("saturday",))
    grille = Schedule([nuit], a(1))  # dimanche 01 h — la soirée de samedi
    assert grille.current_band() is nuit
    assert Schedule([nuit], a(23)).current_band() is None  # dimanche 23 h


def test_un_jour_inconnu_est_refuse_en_le_nommant() -> None:
    with pytest.raises(ValueError, match="caturday"):
        Band(start=time(8), end=time(10), genres=("jazz",), days=("caturday",))


# ── Les plages d'artiste (GOAL-023) ─────────────────────────────────────────


def test_une_plage_peut_imposer_un_artiste() -> None:
    heure_air = Band(start=time(21), end=time(22), artists=("Air",))
    contrainte = Schedule([heure_air], a(21, 30)).constraint_to_draw(RealRandom(graine=1))
    assert contrainte == Constraint(artist="Air")


def test_plusieurs_artistes_tranchent_par_le_hasard_injecte() -> None:
    band = Band(start=time(21), end=time(22), artists=("Air", "Bowie", "M83"))
    contrainte = Schedule([band], a(21, 30)).constraint_to_draw(ScriptedRandom([1]))
    assert contrainte == Constraint(artist="Bowie")


def test_genres_et_artistes_ensemble_sont_refuses() -> None:
    with pytest.raises(ValueError, match="exactement un des trois"):
        Band(start=time(8), end=time(10), genres=("jazz",), artists=("Air",))


# ── Les plages au thème tiré au sort (GOAL-037) ─────────────────────────────


def test_une_plage_peut_demander_un_theme_tire_au_sort() -> None:
    band = Band(start=time(21), end=time(22), random_theme="genre")
    assert band.random_theme == "genre"


def test_un_theme_a_tirer_inconnu_est_refuse_en_le_nommant() -> None:
    with pytest.raises(ValueError, match="album"):
        Band(start=time(21), end=time(22), random_theme="album")


def test_un_theme_a_tirer_et_des_genres_ensemble_sont_refuses() -> None:
    with pytest.raises(ValueError, match="exactement un des trois"):
        Band(start=time(8), end=time(10), genres=("jazz",), random_theme="artist")


def test_l_occurrence_commence_a_l_heure_de_la_plage_ce_jour_la() -> None:
    band = Band(start=time(20), end=time(23), genres=("electro",))
    instant = datetime(2026, 8, 30, 21, 15, tzinfo=UTC)
    assert band.occurrence_start(instant) == datetime(2026, 8, 30, 20, 0, tzinfo=UTC)


def test_l_occurrence_d_une_plage_de_nuit_appartient_au_jour_ou_elle_commence() -> None:
    nuit = Band(start=time(22), end=time(2), genres=("electro",))
    apres_minuit = datetime(2026, 8, 31, 1, 30, tzinfo=UTC)
    assert nuit.occurrence_start(apres_minuit) == datetime(2026, 8, 30, 22, 0, tzinfo=UTC)
    avant_minuit = datetime(2026, 8, 30, 23, 0, tzinfo=UTC)
    assert nuit.occurrence_start(avant_minuit) == datetime(2026, 8, 30, 22, 0, tzinfo=UTC)


def test_une_plage_au_hasard_delegue_au_resolveur_injecte() -> None:
    au_hasard = Band(start=time(21), end=time(23), random_theme="genre")
    vus: list[tuple[Band, datetime]] = []

    def resolveur(band: Band, instant: datetime) -> Constraint | None:
        vus.append((band, instant))
        return Constraint(genre="dub")

    grille = Schedule([au_hasard], a(21, 30), resolve_random_theme=resolveur)
    assert grille.constraint_to_draw(RealRandom(graine=1)) == Constraint(genre="dub")
    assert vus == [(au_hasard, datetime(2026, 8, 30, 21, 30, tzinfo=UTC))]


def test_un_resolveur_sans_theme_a_proposer_rend_le_tirage_libre() -> None:
    au_hasard = Band(start=time(21), end=time(23), random_theme="artist")

    def rien(_band: Band, _instant: datetime) -> Constraint | None:
        return None

    grille = Schedule([au_hasard], a(21, 30), resolve_random_theme=rien)
    assert grille.constraint_to_draw(RealRandom(graine=1)) is None


def test_une_plage_au_hasard_sans_resolveur_est_refusee_bruyamment() -> None:
    au_hasard = Band(start=time(21), end=time(23), random_theme="genre")
    grille = Schedule([au_hasard], a(21, 30))
    with pytest.raises(ValueError, match="aucun résolveur"):
        grille.constraint_to_draw(RealRandom(graine=1))


# ── Les modes d'enchaînement (SPECS.md §7 n°31) ────────────────────────────


def test_le_mode_et_la_cle_d_occurrence_voyagent_avec_la_contrainte() -> None:
    grille = Schedule([Band(time(9), time(11), genres=("jazz",), mode=Mode.DOUBLE_DOSE)], a(10))
    contrainte = grille.constraint_to_draw(RealRandom(graine=1))
    assert contrainte is not None
    assert contrainte.mode is Mode.DOUBLE_DOSE
    assert contrainte.run_key is not None


def test_la_cle_d_occurrence_survit_au_changement_de_genre_de_la_plage() -> None:
    """Une plage multi-genres retire un genre à chaque jonction : la clé, elle,
    reste celle de l'occurrence — c'est ce qui garde la suite vivante."""
    grille = Schedule(
        [Band(time(9), time(11), genres=("jazz", "soul"), mode=Mode.ARTIST_FAN)], a(10)
    )
    c1 = grille.constraint_to_draw(ScriptedRandom([0]))
    c2 = grille.constraint_to_draw(ScriptedRandom([1]))
    assert c1 is not None and c2 is not None
    assert (c1.genre, c2.genre) == ("jazz", "soul")
    assert c1.run_key == c2.run_key


def test_l_occurrence_du_lendemain_change_la_cle() -> None:
    clock = a(10)
    grille = Schedule([Band(time(9), time(11), genres=("jazz",), mode=Mode.ERA_FAN)], clock)
    c1 = grille.constraint_to_draw(RealRandom(graine=1))
    clock.advance(timedelta(days=1))
    c2 = grille.constraint_to_draw(RealRandom(graine=1))
    assert c1 is not None and c2 is not None
    assert c1.run_key != c2.run_key


def test_une_plage_a_mode_seul_est_un_tirage_libre_enchaine() -> None:
    grille = Schedule([Band(time(9), time(11), mode=Mode.DOUBLE_DOSE)], a(10))
    contrainte = grille.constraint_to_draw(RealRandom(graine=1))
    assert contrainte is not None
    assert contrainte.genre is None and contrainte.artist is None
    assert contrainte.mode is Mode.DOUBLE_DOSE


def test_une_plage_sans_theme_ni_mode_reste_refusee() -> None:
    with pytest.raises(ValueError, match="exactement un des trois"):
        Band(time(9), time(11))
