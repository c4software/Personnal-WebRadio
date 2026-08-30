"""La file : ce qui passe ensuite, ce qu'elle relâche, et ce qu'elle refuse."""

from typing import TypeVar

import pytest

from tests.fakes import FakeSource, piste
from webradio.core.queue import File, FileVide
from webradio.core.rotation import Fenetre
from webradio.core.rng import HasardReel, HasardScripte
from webradio.core.sources import SourceIndisponible

T = TypeVar("T")

CATALOGUE = [
    piste("1", "Air", genre="électro"),
    piste("2", "Bowie", genre="rock"),
    piste("3", "Portishead", genre="trip-hop"),
    piste("4", "Massive Attack", genre="trip-hop"),
]


def test_la_file_sert_une_piste_du_catalogue() -> None:
    f = File(FakeSource(CATALOGUE), HasardScripte([0]))
    assert f.suivant().piste in CATALOGUE


def test_la_file_respecte_la_non_repetition() -> None:
    """Sur un catalogue de quatre artistes et une fenêtre de trois, aucun
    artiste ne doit revenir avant que trois autres soient passés."""
    f = File(FakeSource(CATALOGUE), HasardReel(graine=1), Fenetre(largeur=3))
    joues = [f.suivant().piste.artiste for _ in range(12)]
    for i in range(3, len(joues)):
        assert joues[i] not in joues[i - 3 : i], f"répétition en position {i} : {joues}"


def test_une_plage_sans_musique_replie_sur_le_tirage_libre() -> None:
    """SPECS.md §4.4 : la radio ne se tait pas, et le repli est signalé."""
    f = File(FakeSource(CATALOGUE), HasardScripte([0]))
    choix = f.suivant(genre="jazz")
    assert choix.piste in CATALOGUE
    assert any("jazz" in r for r in choix.replis)


def test_une_plage_pourvue_ne_replie_pas() -> None:
    f = File(FakeSource(CATALOGUE), HasardScripte([0]))
    choix = f.suivant(genre="trip-hop")
    assert choix.piste.genre == "trip-hop"
    assert choix.replis == ()


def test_une_bibliotheque_de_trois_artistes_ne_bloque_pas() -> None:
    """Le cas de SPECS.md §4.2 : la fenêtre rétrécit plutôt que de se taire."""
    trois = [piste("1", "Air"), piste("2", "Bowie"), piste("3", "Portishead")]
    f = File(FakeSource(trois), HasardReel(graine=3), Fenetre(largeur=5))
    joues = [f.suivant() for _ in range(10)]
    assert len(joues) == 10
    assert any(c.replis for c in joues), "la fenêtre aurait dû rétrécir au moins une fois"


def test_le_retrecissement_est_signale() -> None:
    un_seul = [piste("1", "Air"), piste("2", "Air")]
    f = File(FakeSource(un_seul), HasardScripte([0, 0, 0]), Fenetre(largeur=2))
    f.suivant()
    assert any("rétréci" in r for r in f.suivant().replis)


def test_une_source_vide_est_refusee_franchement() -> None:
    """La source a répondu, elle n'a rien. C'est distinct d'une panne : SPECS.md
    §4.1 en fait une erreur, pas un silence."""
    f = File(FakeSource([]), HasardScripte([0]))
    with pytest.raises(FileVide, match="aucune piste"):
        f.suivant()


def test_une_source_injoignable_remonte_telle_quelle() -> None:
    """La file ne masque pas la panne : le repli en cours de diffusion se décide
    au-dessus, avec le contexte (SPECS.md §5.1)."""
    f = File(FakeSource(CATALOGUE, injoignable=True), HasardScripte([0]))
    with pytest.raises(SourceIndisponible):
        f.suivant()


def test_preparer_resout_a_l_avance_sans_consommer() -> None:
    """La contrainte de docs/ffmpeg.md §2.2 : résoudre pendant que le courant
    joue, jamais à la jonction."""
    source = FakeSource(CATALOGUE)
    f = File(source, HasardScripte([0, 1]))
    f.preparer()
    appels_apres_preparation = source.appels
    assert appels_apres_preparation > 0
    f.suivant()
    assert source.appels == appels_apres_preparation, "suivant() a réinterrogé la source"


def test_preparer_deux_fois_ne_resout_qu_une_fois() -> None:
    source = FakeSource(CATALOGUE)
    f = File(source, HasardScripte([0]))
    f.preparer()
    appels = source.appels
    f.preparer()
    assert source.appels == appels


def test_l_avance_est_bien_celle_qui_est_servie() -> None:
    source = FakeSource(CATALOGUE)
    f = File(source, HasardScripte([2, 0]))
    f.preparer()
    assert f.suivant().piste.artiste == "Portishead"


def test_apres_avoir_servi_l_avance_la_file_recalcule() -> None:
    source = FakeSource(CATALOGUE)
    f = File(source, HasardScripte([0, 1]))
    f.preparer()
    f.suivant()
    assert f.suivant().piste in CATALOGUE


def test_sans_poids_la_file_tire_uniformement() -> None:
    """La pondération est une capacité en plus, jamais un réglage de la
    première : sans `peser`, rien de ce qui existait ne change."""
    f = File(FakeSource(CATALOGUE), HasardScripte([0]))
    assert f.suivant().piste in CATALOGUE


def test_avec_des_poids_la_file_les_honore() -> None:
    """Un poids nul sur tout sauf un morceau : c'est celui-là qui doit sortir,
    quel que soit le tirage."""
    vise = CATALOGUE[2]
    f = File(
        FakeSource(CATALOGUE),
        HasardReel(graine=1),
        Fenetre(largeur=0),
        peser=lambda p: 1000.0 if p.identifiant == vise.identifiant else 0.001,
    )
    sorties = [f.suivant().piste.identifiant for _ in range(30)]
    assert sorties.count(vise.identifiant) > 25, sorties


def test_des_poids_sans_hasard_pondere_sont_refuses_a_la_construction() -> None:
    """Refuser ici plutôt qu'au premier tirage : sinon la file tirerait
    uniformément sans rien signaler, et la pondération semblerait « ne pas
    marcher » des semaines durant."""

    class HasardSimple:
        """Un hasard qui sait tirer, mais pas pondérer. C'est le cas à refuser."""

        def choisir(self, parmi: list[T]) -> T:
            return parmi[0]

    with pytest.raises(TypeError, match="ne sait pas les honorer"):
        File(FakeSource(CATALOGUE), HasardSimple(), peser=lambda _: 1.0)
