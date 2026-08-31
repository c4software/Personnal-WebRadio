"""La file : ce qui passe ensuite, ce qu'elle relâche, et ce qu'elle refuse."""

from datetime import timedelta
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
    """Sur un catalogue de quatre artistes et une fenêtre de trois, aucun
    artiste ne doit revenir avant que trois autres soient passés."""
    f = Queue(FakeSource(CATALOGUE), RealRandom(graine=1), Window(width=3))
    joues = [f.next_pick().track.artist for _ in range(12)]
    for i in range(3, len(joues)):
        assert joues[i] not in joues[i - 3 : i], f"répétition en position {i} : {joues}"


def test_une_plage_sans_musique_replie_sur_le_tirage_libre() -> None:
    """SPECS.md §4.4 : la radio ne se tait pas, et le repli est signalé."""
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
    """Le cas de SPECS.md §4.2 : la fenêtre rétrécit plutôt que de se taire."""
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
    """La source a répondu, elle n'a rien. C'est distinct d'une panne : SPECS.md
    §4.1 en fait une erreur, pas un silence."""
    f = Queue(FakeSource([]), ScriptedRandom([0]))
    with pytest.raises(EmptyQueue, match="aucune piste"):
        f.next_pick()


def test_une_source_injoignable_remonte_telle_quelle() -> None:
    """La file ne masque pas la panne : le repli en cours de diffusion se décide
    au-dessus, avec le contexte (SPECS.md §5.1)."""
    f = Queue(FakeSource(CATALOGUE, injoignable=True), ScriptedRandom([0]))
    with pytest.raises(SourceUnavailable):
        f.next_pick()


def test_preparer_resout_a_l_avance_sans_consommer() -> None:
    """La contrainte de docs/ffmpeg.md §2.2 : résoudre pendant que le courant
    joue, jamais à la jonction."""
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


def test_apres_avoir_servi_l_avance_la_file_recalcule() -> None:
    source = FakeSource(CATALOGUE)
    f = Queue(source, ScriptedRandom([0, 1]))
    f.prepare()
    f.next_pick()
    assert f.next_pick().track in CATALOGUE


def test_sans_poids_la_file_tire_uniformement() -> None:
    """La pondération est une capacité en plus, jamais un réglage de la
    première : sans `peser`, rien de ce qui existait ne change."""
    f = Queue(FakeSource(CATALOGUE), ScriptedRandom([0]))
    assert f.next_pick().track in CATALOGUE


def test_avec_des_poids_la_file_les_honore() -> None:
    """Un poids nul sur tout sauf un morceau : c'est celui-là qui doit sortir,
    quel que soit le tirage."""
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
    """Refuser ici plutôt qu'au premier tirage : sinon la file tirerait
    uniformément sans rien signaler, et la pondération semblerait « ne pas
    marcher » des semaines durant."""

    class PlainRandom:
        """Un hasard qui sait tirer, mais pas pondérer. C'est le cas à refuser."""

        def pick(self, parmi: list[T]) -> T:
            return parmi[0]

    with pytest.raises(TypeError, match="ne sait pas les honorer"):
        Queue(FakeSource(CATALOGUE), PlainRandom(), weigh=lambda _: 1.0)


def test_une_plage_d_artiste_tire_chez_cet_artiste() -> None:
    """GOAL-023 : une heure d'un seul artiste — la contrainte va à `tracks_by`."""
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
    """Le second titre outrepasse la fenêtre — le passe-droit de l'encore —
    puis la règle reprend : le troisième tirage écarte l'artiste."""
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
    """La clé est l'occurrence, et la suite passe par `tracks_by` : le genre
    retiré entre deux jonctions ne la rompt pas."""
    catalogue = [
        track("a1", "Air", genre="électro"),
        track("a2", "Air", genre="ambient"),
        track("a3", "Air", genre="électro"),
        track("b1", "Bowie", genre="rock"),
    ]
    hasard = ScriptedRandom([0, 0, 0, 0])  # le 2e indice : longueur 3 dans [3..6]
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


# ── Le plafond de durée (SPECS.md §7 n°32) ─────────────────────────────────


def test_une_piste_trop_longue_n_est_jamais_tiree() -> None:
    catalogue = [track("long", "Air", secondes=1300), track("ok", "Bowie", secondes=180)]
    f = Queue(
        FakeSource(catalogue),
        RealRandom(graine=1),
        Window(width=0),
        max_duration=timedelta(minutes=20),
    )
    assert all(f.next_pick().track.identifier == "ok" for _ in range(10))


def test_la_limite_exacte_de_duree_passe() -> None:
    """« Au-delà » est strict : vingt minutes pile se diffusent."""
    catalogue = [track("pile", "Air", secondes=1200)]
    f = Queue(FakeSource(catalogue), ScriptedRandom([0]), max_duration=timedelta(minutes=20))
    assert f.next_pick().track.identifier == "pile"


def test_une_plage_videe_par_le_plafond_replie_sur_le_tirage_libre() -> None:
    catalogue = [
        track("long", "Air", genre="ambient", secondes=2400),
        track("ok", "Bowie", genre="rock", secondes=200),
    ]
    f = Queue(FakeSource(catalogue), ScriptedRandom([0]), max_duration=timedelta(minutes=20))
    pick = f.next_pick(Constraint(genre="ambient"))
    assert pick.track.identifier == "ok"
    assert any("ambient" in raison for raison in pick.fallbacks)


def test_une_bibliotheque_entierement_trop_longue_se_refuse_en_le_disant() -> None:
    catalogue = [track("long", "Air", secondes=2400)]
    f = Queue(FakeSource(catalogue), ScriptedRandom([0]), max_duration=timedelta(minutes=20))
    with pytest.raises(EmptyQueue, match="durée maximale"):
        f.next_pick()
