"""Tests de la file de tirage `Queue`."""

from typing import TypeVar

import pytest

from tests.fakes import FakeSource, track
from webradio.core.bands import Constraint
from webradio.core.queue import EmptyQueue, Queue
from webradio.core.rng import RealRandom, ScriptedRandom
from webradio.core.rotation import Window
from webradio.core.runs import Mode, Runs
from webradio.core.sources import SourceUnavailable

T = TypeVar("T")

CATALOGUE = [
    track("1", "Air", genre="électro"),
    track("2", "Bowie", genre="rock"),
    track("3", "Portishead", genre="trip-hop"),
    track("4", "Massive Attack", genre="trip-hop"),
]


def test_la_file_sert_une_piste_du_catalogue() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0]))
    assert f.next_pick().track in CATALOGUE


def test_la_file_respecte_la_non_repetition() -> None:
    """Avec quatre artistes et une fenêtre de trois, aucun artiste ne revient
    avant que trois autres soient passés."""
    f = Queue(FakeSource(CATALOGUE), RealRandom(graine=1), Window(width=3))
    joues = [f.next_pick().track.artist for _ in range(12)]
    for i in range(3, len(joues)):
        assert joues[i] not in joues[i - 3 : i], f"répétition en position {i} : {joues}"


def test_une_plage_sans_musique_replie_sur_le_tirage_libre() -> None:
    """Une plage sans musique replie sur le tirage libre, et le repli est
    signalé dans `fallbacks` (SPECS.md §4.4)."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0]))
    pick = f.next_pick(Constraint(genre="jazz"))
    assert pick.track in CATALOGUE
    assert any("jazz" in r for r in pick.fallbacks)


def test_une_plage_pourvue_ne_replie_pas() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0]))
    pick = f.next_pick(Constraint(genre="trip-hop"))
    assert pick.track.genre == "trip-hop"
    assert pick.fallbacks == ()


def test_une_bibliotheque_de_trois_artistes_ne_bloque_pas() -> None:
    """La fenêtre rétrécit quand le catalogue est trop petit (SPECS.md §4.2)."""
    trois = [track("1", "Air"), track("2", "Bowie"), track("3", "Portishead")]
    f = Queue(FakeSource(trois), RealRandom(graine=3), Window(width=5))
    joues = [f.next_pick() for _ in range(10)]
    assert len(joues) == 10
    assert any(c.fallbacks for c in joues), "la fenêtre aurait dû rétrécir au moins une fois"


def test_le_retrecissement_est_signale() -> None:
    un_seul = [track("1", "Air"), track("2", "Air")]
    f = Queue(FakeSource(un_seul), ScriptedRandom([0, 0, 0]), Window(width=2))
    f.next_pick()
    assert any("rétréci" in r for r in f.next_pick().fallbacks)


def test_une_source_vide_est_refusee_franchement() -> None:
    """Une source qui répond mais n'a rien est une erreur, distincte d'une
    panne (SPECS.md §4.1)."""
    f = Queue(FakeSource([]), ScriptedRandom([0]))
    with pytest.raises(EmptyQueue, match="aucune piste"):
        f.next_pick()


def test_une_source_injoignable_remonte_telle_quelle() -> None:
    """La file ne masque pas la panne : le repli se décide au-dessus, avec le
    contexte (SPECS.md §5.1)."""
    f = Queue(FakeSource(CATALOGUE, injoignable=True), ScriptedRandom([0]))
    with pytest.raises(SourceUnavailable):
        f.next_pick()


def test_preparer_resout_a_l_avance_sans_consommer() -> None:
    """La résolution se fait pendant le morceau en cours, pas à la jonction
    (docs/ffmpeg.md §2.2)."""
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0, 1]))
    f.prepare()
    appels_apres_preparation = source.appels
    assert appels_apres_preparation > 0
    f.next_pick()
    assert source.appels == appels_apres_preparation, "suivant() a réinterrogé la source"


def test_preparer_deux_fois_ne_resout_qu_une_fois() -> None:
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0]))
    f.prepare()
    appels = source.appels
    f.prepare()
    assert source.appels == appels


def test_l_avance_est_bien_celle_qui_est_servie() -> None:
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([2, 0]))
    f.prepare()
    assert f.next_pick().track.artist == "Portishead"


def test_sans_preparation_la_file_n_annonce_rien() -> None:
    assert Queue(FakeSource(CATALOGUE), ScriptedRandom([0])).advance == ()


def test_la_file_dit_ce_qu_elle_a_prepare_sans_le_consommer() -> None:
    """`advance` expose ce qui est préparé sans le consommer, pour que
    « À suivre » ne reste pas vide quand l'avance du diffuseur est un jingle
    (GOAL-054)."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([2, 0]))
    f.prepare()
    (annonce,), (redite,) = f.advance, f.advance
    assert annonce.artist == "Portishead"
    assert redite is annonce, "le dire ne le consomme pas"
    assert f.next_pick().track is annonce, "et c'est bien lui qui est servi"


def test_l_avance_servie_n_est_plus_annoncee() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([2, 0]))
    f.prepare()
    f.next_pick()
    assert f.advance == ()


def test_l_avance_s_oublie_pour_repartir_a_neuf() -> None:
    """Après une longue pause, le tirage doit être neuf (SPECS.md §7 n°30).
    `next_pick` sert l'avance sans regarder la contrainte : la garder aurait
    resservi un morceau tiré sous une plage fermée depuis."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([2, 0]))
    f.prepare()
    f.forget_prepared()
    assert f.advance == ()


def test_apres_avoir_servi_l_avance_la_file_recalcule() -> None:
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0, 1]))
    f.prepare()
    f.next_pick()
    assert f.next_pick().track in CATALOGUE


def test_sans_poids_la_file_tire_uniformement() -> None:
    """Sans `weigh`, le tirage reste uniforme : la pondération est optionnelle."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0]))
    assert f.next_pick().track in CATALOGUE


def test_avec_des_poids_la_file_les_honore() -> None:
    """Avec un poids quasi nul sur tout sauf un morceau, c'est celui-là qui
    sort presque toujours."""
    vise = CATALOGUE[2]
    f = Queue(
        FakeSource(CATALOGUE),
        RealRandom(graine=1),
        Window(width=0),
        weigh=lambda p: 1000.0 if p.identifier == vise.identifier else 0.001,
    )
    sorties = [f.next_pick().track.identifier for _ in range(30)]
    assert sorties.count(vise.identifier) > 25, sorties


def test_des_poids_sans_hasard_pondere_sont_refuses_a_la_construction() -> None:
    """Le refus se fait à la construction : au premier tirage, la file tirerait
    uniformément sans rien signaler."""

    class PlainRandom:
        """Hasard qui sait tirer mais pas pondérer."""

        def pick(self, parmi: list[T]) -> T:
            return parmi[0]

    with pytest.raises(TypeError, match="ne sait pas les honorer"):
        Queue(FakeSource(CATALOGUE), PlainRandom(), weigh=lambda _: 1.0)


def test_une_plage_d_artiste_tire_chez_cet_artiste() -> None:
    """Une contrainte d'artiste passe par `tracks_by` (GOAL-023)."""
    source = FakeSource([track("1", "Air", genre="électro"), track("2", "Bowie", genre="rock")])
    f = Queue(source, ScriptedRandom([0] * 10), Window(width=1))
    pick = f.next_pick(Constraint(artist="Bowie"))
    assert pick.track.artist == "Bowie"


def test_une_plage_d_artiste_sans_musique_replie_sur_le_tirage_libre() -> None:
    source = FakeSource([track("1", "Air", genre="électro")])
    f = Queue(source, ScriptedRandom([0] * 10), Window(width=1))
    pick = f.next_pick(Constraint(artist="Personne"))
    assert pick.track.artist == "Air"
    assert any("Personne" in raison for raison in pick.fallbacks)


# ── Les suites (SPECS.md §7 n°31) ──────────────────────────────────────────


def test_la_double_dose_sert_le_meme_artiste_deux_fois_sans_le_meme_titre() -> None:
    """Le second titre passe outre la fenêtre, comme un encore ; au troisième
    tirage, la règle reprend et écarte l'artiste."""
    catalogue = [
        track("a1", "Air", genre="électro"),
        track("a2", "Air", genre="électro"),
        track("b1", "Bowie", genre="électro"),
        track("b2", "Bowie", genre="électro"),
    ]
    hasard = ScriptedRandom([0, 0, 0, 0])
    f = Queue(FakeSource(catalogue), hasard, Window(width=2), runs=Runs(hasard))
    c = Constraint(genre="électro", mode=Mode.DOUBLE_DOSE, run_key="occurrence")
    joues = [f.next_pick(c).track.identifier for _ in range(4)]
    assert joues == ["a1", "a2", "b1", "b2"]


def test_le_passionne_d_artiste_suit_l_artiste_meme_si_la_plage_change_de_genre() -> None:
    """La suite est indexée par occurrence et passe par `tracks_by` : un
    changement de genre entre deux jonctions ne la rompt pas."""
    catalogue = [
        track("a1", "Air", genre="électro"),
        track("a2", "Air", genre="ambient"),
        track("a3", "Air", genre="électro"),
        track("b1", "Bowie", genre="rock"),
    ]
    hasard = ScriptedRandom([0, 0, 0, 0])  # 2e indice : longueur 3 dans [3..6]
    f = Queue(FakeSource(catalogue), hasard, Window(width=1), runs=Runs(hasard))
    premier = f.next_pick(Constraint(genre="électro", mode=Mode.ARTIST_FAN, run_key="occ"))
    deuxieme = f.next_pick(Constraint(genre="ambient", mode=Mode.ARTIST_FAN, run_key="occ"))
    assert premier.track.identifier == "a1"
    assert deuxieme.track.artist == "Air"  # le genre a changé, la suite tient


def test_le_passionne_d_epoque_reste_dans_la_decennie() -> None:
    catalogue = [
        track("x1", "Air", year=1991),
        track("x2", "Bowie", year=1995),
        track("x3", "Portishead", year=1992),
        track("y1", "Daft Punk", year=2003),
    ]
    hasard = ScriptedRandom([0, 0, 0])  # piste x1, longueur 2 dans [2..6], piste suivante
    f = Queue(FakeSource(catalogue), hasard, Window(width=1), runs=Runs(hasard))
    c = Constraint(mode=Mode.ERA_FAN, run_key="occ")
    premier = f.next_pick(c)
    deuxieme = f.next_pick(c)
    assert premier.track.year == 1991
    assert deuxieme.track.year is not None and 1990 <= deuxieme.track.year < 2000
    assert deuxieme.track.identifier != premier.track.identifier


def test_une_suite_d_epoque_epuisee_se_rompt_en_le_disant() -> None:
    catalogue = [
        track("s1", "Elvis", year=1956),
        track("y1", "Daft Punk", year=2003),
        track("y2", "Justice", year=2007),
    ]
    hasard = ScriptedRandom([0, 2, 0, 0])  # s1, longueur 4, la rupture, la nouvelle ancre
    f = Queue(FakeSource(catalogue), hasard, Window(width=1), runs=Runs(hasard))
    c = Constraint(mode=Mode.ERA_FAN, run_key="occ")
    assert f.next_pick(c).track.identifier == "s1"
    suivant = f.next_pick(c)
    assert "suite rompue : plus rien des années 1950" in suivant.fallbacks
    assert suivant.track.identifier in ("y1", "y2")


def test_une_suite_d_artiste_epuisee_se_rompt_en_le_disant() -> None:
    catalogue = [
        track("a1", "Air", genre="électro"),
        track("b1", "Bowie", genre="électro"),
        track("b2", "Bowie", genre="électro"),
    ]
    hasard = ScriptedRandom([0, 0, 0, 0])  # a1, longueur 3, la rupture, la nouvelle ancre
    f = Queue(FakeSource(catalogue), hasard, Window(width=1), runs=Runs(hasard))
    c = Constraint(genre="électro", mode=Mode.ARTIST_FAN, run_key="occ")
    assert f.next_pick(c).track.identifier == "a1"
    suivant = f.next_pick(c)
    assert "suite rompue : plus rien de « Air »" in suivant.fallbacks
    assert suivant.track.artist == "Bowie"


# ── Le plafond de durée ne filtre plus (SPECS.md §7 n°32 révisée) ──────────


def test_une_piste_longue_se_tire_comme_les_autres() -> None:
    """La coupe au plafond se fait à la diffusion, pas au tirage."""
    catalogue = [track("long", "Air", secondes=2400)]
    f = Queue(FakeSource(catalogue), ScriptedRandom([0]))
    assert f.next_pick().track.identifier == "long"


def test_l_avance_tiree_sous_une_plage_ne_passe_pas_sous_la_suivante() -> None:
    """Une avance dont le moment a fini est rassise : elle ne passe pas sous
    la plage suivante (décision n°33)."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0, 0]))
    f.prepare(Constraint(genre="trip-hop", run_key="15 h"))
    pick = f.next_pick(Constraint(genre="rock", run_key="16 h"))
    assert pick.track.genre == "rock"
    assert pick.fallbacks == ()


def test_l_avance_survit_au_changement_de_genre_dans_la_meme_plage() -> None:
    """Une plage multi-genres change de genre à chaque jonction sans changer
    de moment : l'avance, déjà résolue, est servie."""
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0, 0]))
    f.prepare(Constraint(genre="trip-hop", run_key="soirée"))
    appels = source.appels
    pick = f.next_pick(Constraint(genre="rock", run_key="soirée"))
    assert pick.track.genre == "trip-hop"
    assert source.appels == appels


def test_preparer_sous_un_autre_moment_remplace_l_avance() -> None:
    """Quand la plage change, le programme reprépare : l'avance rassise est
    remplacée par un tirage sous la nouvelle plage."""
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0, 0]))
    f.prepare(Constraint(genre="trip-hop", run_key="15 h"))
    f.revalidate(["16 h"])
    assert f.advance == ()
    f.prepare(Constraint(genre="rock", run_key="16 h"))
    assert f.dated_advance[0][0].genre == "rock"
    assert f.dated_advance[0][1] == "16 h"


def test_l_avance_du_tirage_libre_ne_passe_pas_sous_une_plage() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0, 0]))
    f.prepare()
    assert f.next_pick(Constraint(genre="rock", run_key="16 h")).track.genre == "rock"


def test_l_avance_dit_sous_quel_moment_chaque_titre_a_ete_tire() -> None:
    """`dated_advance` porte la clé du moment de chaque tirage, pour que le
    lecteur la compare à celle du créneau avant d'annoncer un titre."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0, 0]))
    f.prepare(Constraint(genre="trip-hop", run_key="15 h"))
    ((track, moment),) = f.dated_advance
    assert track.genre == "trip-hop"
    assert moment == "15 h"


def test_la_file_tire_plusieurs_titres_d_avance_sans_repeter_un_artiste() -> None:
    """La fenêtre tient compte des titres en attente, sinon un hasard à indice
    0 tirerait trois fois le même artiste (GOAL-058)."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0] * 10), Window(width=3), lookahead=3)
    assert f.wants_more()
    for _ in range(3):
        f.prepare()
    assert not f.wants_more()
    f.prepare()  # file pleine : sans effet
    artistes = [t.artist for t in f.advance]
    assert len(artistes) == 3
    assert len(set(artistes)) == 3


def test_l_avance_se_sert_dans_l_ordre_ou_elle_a_ete_tiree() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0] * 10), Window(width=3), lookahead=3)
    for _ in range(3):
        f.prepare()
    attendus = list(f.advance)
    servis = [f.next_pick().track for _ in range(3)]
    assert servis == attendus
    assert f.advance == ()


def test_une_suite_d_artiste_peut_attendre_deux_fois() -> None:
    """Le passe-droit de fenêtre des suites d'artiste (SPECS.md §4.4) vaut
    aussi pour les titres en attente."""
    deux_air = [track("a1", "Air"), track("a2", "Air"), track("b", "Bowie")]
    hasard = ScriptedRandom([0] * 20)
    f = Queue(FakeSource(deux_air), hasard, Window(width=2), runs=Runs(hasard), lookahead=2)
    suite = Constraint(mode=Mode.ARTIST_FAN, run_key="soirée")
    f.prepare(suite)
    f.prepare(suite)
    assert [t.artist for t in f.advance] == ["Air", "Air"]


def test_une_petite_bibliotheque_laisse_repasser_un_artiste_en_attente() -> None:
    """Quand tout le catalogue attend déjà, un artiste en attente repasse
    plutôt que de laisser un trou."""
    deux = [track("1", "Air"), track("2", "Bowie")]
    f = Queue(FakeSource(deux), ScriptedRandom([0] * 10), Window(width=1), lookahead=3)
    for _ in range(3):
        f.prepare()
    assert len(f.advance) == 3


def test_retirer_un_titre_de_l_avance() -> None:
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0] * 10), Window(width=3), lookahead=3)
    for _ in range(3):
        f.prepare()
    retire = f.advance[1]
    assert f.withdraw(retire.identifier)
    assert retire not in f.advance
    assert len(f.advance) == 2
    assert not f.withdraw(retire.identifier), "il n'y attend plus"


def test_revalider_coupe_a_la_premiere_avance_rassise() -> None:
    """Tout ce qui suit une entrée rassise est jeté aussi : ses créneaux ont
    glissé."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0] * 10), Window(width=3), lookahead=3)
    f.prepare(Constraint(genre="rock", run_key="15 h"))
    f.prepare(Constraint(genre="trip-hop", run_key="16 h"))
    f.prepare(Constraint(genre="trip-hop", run_key="16 h"))
    f.revalidate(["15 h", "15 h", "16 h"])
    assert len(f.advance) == 1
    f.revalidate(["15 h"])
    assert len(f.advance) == 1


def test_une_tete_tiree_pour_plus_tard_reste_en_place() -> None:
    """Une tête tirée pour un moment à venir n'est pas servie avant son heure :
    on tire un titre frais devant elle."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0] * 10), Window(width=3), lookahead=2)
    f.prepare(Constraint(genre="trip-hop", run_key="16 h"))
    f.prepare(Constraint(genre="rock", run_key="16 h"))
    pick = f.next_pick(Constraint(genre="électro", run_key="15 h"))
    assert pick.track.genre == "électro"
    assert len(f.advance) == 2


def test_une_avance_nulle_est_refusee() -> None:
    with pytest.raises(ValueError, match="trou"):
        Queue(FakeSource(CATALOGUE), ScriptedRandom([0]), lookahead=0)


def test_rompre_la_suite_fait_tirer_une_autre_decennie() -> None:
    """Après `break_run`, la suite suivante s'ouvre sur une autre décennie
    (GOAL-059)."""
    dates = [
        track("1", "Air", year=1998),
        track("2", "Bowie", year=1977),
        track("3", "Massive", year=1991),
    ]
    hasard = ScriptedRandom([0] * 20)
    f = Queue(FakeSource(dates), hasard, Window(width=0), runs=Runs(hasard))
    suite = Constraint(mode=Mode.ERA_FAN, run_key="soir")
    assert f.next_pick(suite).track.year == 1998
    assert f.break_run()
    pick = f.next_pick(suite)
    assert pick.track.year == 1977
    assert pick.fallbacks == ()


def test_rompre_sans_autre_decennie_le_dit() -> None:
    dates = [track("1", "Air", year=1998), track("2", "Bowie", year=1991)]
    hasard = ScriptedRandom([0] * 20)
    f = Queue(FakeSource(dates), hasard, Window(width=0), runs=Runs(hasard))
    suite = Constraint(mode=Mode.ERA_FAN, run_key="soir")
    f.next_pick(suite)
    f.break_run()
    pick = f.next_pick(suite)
    assert any("rien d'autre" in r for r in pick.fallbacks)


def test_sans_suites_rien_ne_se_rompt() -> None:
    assert not Queue(FakeSource(CATALOGUE), ScriptedRandom([0])).break_run()
