"""L'apprentissage : ce qu'il lit, ce qu'il écrit, et ce qu'il refuse d'écrire."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.fakes import FakeEtatQuiCompteSesLectures, FakeSource, track
from webradio.adapters.state.database import Scope as PorteeBase
from webradio.adapters.state.database import SqliteState
from webradio.app.learning import Learning
from webradio.core.clock import FrozenClock
from webradio.core.control import Command
from webradio.core.models import Track
from webradio.core.queue import Queue
from webradio.core.rng import RealRandom
from webradio.core.rotation import Window
from webradio.core.weighting import Scope, Scores, track_weight

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _apprentissage(tmp_path: Path, clock: FrozenClock | None = None) -> Learning:
    database = SqliteState(
        tmp_path / "etat.sqlite3",
        clock=clock or FrozenClock(MIDI),
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return Learning(database, floor=0.25, ceiling=4.0, slope=0.5)


def _poids(apprentissage: Learning, piste: Track) -> float:
    """Le poids d'une seule piste : `weigh` pèse tout un tirage d'un coup."""
    return apprentissage.weigh([piste])[0]


def test_les_deux_vocabulaires_de_portee_coincident() -> None:
    """Le noyau et la base ont chacun leur `Scope` ; s'ils divergent, ce test
    casse avant la base."""
    assert {p.value for p in Scope} == {p.value for p in PorteeBase}


def test_une_piste_inconnue_pese_neutre(tmp_path: Path) -> None:
    """Une base vide pèse comme si personne n'avait voté."""
    assert _poids(_apprentissage(tmp_path), track("1", "Bowie")) == pytest.approx(1.0)


def test_un_stop_fait_reculer_la_piste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    a.remember(Command.SKIP, p)
    assert _poids(a, p) < 1.0


def test_un_encore_fait_avancer_l_artiste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    a.remember(Command.MORE, track("1", "Bowie"))
    # Un autre titre du même artiste profite du vote : c'est la portée croisée.
    assert _poids(a, track("2", "Bowie")) > 1.0


def test_le_vote_porte_sur_l_artiste_seul_et_egalement(tmp_path: Path) -> None:
    """Un `stop` pèse pareil sur tous les titres de l'artiste : la piste visée
    n'écope pas double (révision n°16)."""
    a = _apprentissage(tmp_path)
    visee = track("1", "Bowie")
    voisine = track("2", "Bowie")
    autre_artiste = track("3", "Air")
    a.remember(Command.SKIP, visee)
    assert _poids(a, visee) == _poids(a, voisine) < 1.0
    assert _poids(a, autre_artiste) == 1.0


def test_le_poids_ne_descend_jamais_a_zero(tmp_path: Path) -> None:
    """Rien n'est jamais supprimé : le plancher est 0,25, pas 0 (SPECS.md §7 n°17)."""
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    for _ in range(50):
        a.remember(Command.SKIP, p)
    assert _poids(a, p) == pytest.approx(0.25)


def test_le_poids_ne_depasse_jamais_le_plafond(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    for _ in range(50):
        a.remember(Command.MORE, p)
    assert _poids(a, p) == pytest.approx(4.0)


def test_les_votes_s_oublient_avec_le_temps(tmp_path: Path) -> None:
    """Sans oubli, la radio se figerait sur les premiers votes (SPECS.md §7 n°18)."""
    clock = FrozenClock(MIDI)
    a = _apprentissage(tmp_path, clock)
    p = track("1", "Bowie")
    for _ in range(5):
        a.remember(Command.SKIP, p)
    juste_apres = _poids(a, p)
    clock.advance(timedelta(days=365 * 2))
    bien_plus_tard = _poids(a, p)
    assert juste_apres < bien_plus_tard < 1.0


def test_une_base_devenue_injoignable_rend_un_poids_neutre(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une base injoignable en cours de diffusion rend un poids neutre : la radio
    ne se tait pas (SPECS.md §5.1).

    La base est construite normalement puis rendue inaccessible. Une base
    injoignable au démarrage échoue bruyamment : les deux régimes d'erreur de
    SPECS.md §5 sont distincts.
    """
    folder = tmp_path / "etat"
    folder.mkdir()
    a = _apprentissage(folder)
    p = track("1", "Bowie")
    a.remember(Command.SKIP, p)
    assert _poids(a, p) < 1.0

    folder.chmod(0o500)
    (folder / "etat.sqlite3").chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            assert _poids(a, p) == pytest.approx(1.0)
        assert "tirage neutre" in caplog.text
    finally:
        (folder / "etat.sqlite3").chmod(0o600)
        folder.chmod(0o700)


def test_un_vote_non_retenu_ne_fait_pas_taire_la_radio(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Perdre un vote ne doit pas couper la radio."""
    folder = tmp_path / "etat"
    folder.mkdir()
    a = _apprentissage(folder)
    a.remember(Command.SKIP, track("1", "Bowie"))
    (folder / "etat.sqlite3").chmod(0o400)
    try:
        with caplog.at_level(logging.WARNING):
            a.remember(Command.MORE, track("2", "Air"))
        assert "non retenu" in caplog.text
    finally:
        (folder / "etat.sqlite3").chmod(0o600)


def test_le_vote_s_affiche_par_le_nom_de_l_artiste(tmp_path: Path) -> None:
    """Seule l'entrée artiste existe et elle se lit par son nom, sans identifiant
    opaque ni ligne à zéro (GOAL-020, révision n°16)."""
    learning = _apprentissage(tmp_path)
    learning.remember(Command.SKIP, track("1", "Air"))

    base = SqliteState(
        tmp_path / "etat.sqlite3",
        clock=FrozenClock(MIDI),
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    tout = base.all_scores()
    assert [(scope, libelle) for scope, _, libelle, _ in tout] == [(PorteeBase.ARTIST, "Air")]


# ── Les scores se lisent une fois par tirage (GOAL-075-T05) ──────────────────

CATALOGUE = [track(str(i), f"artiste {i}", genre="rock") for i in range(1, 8)]


def _base_qui_compte(tmp_path: Path) -> FakeEtatQuiCompteSesLectures:
    return FakeEtatQuiCompteSesLectures(
        tmp_path / "etat.sqlite3",
        clock=FrozenClock(MIDI),
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )


def test_un_tirage_ne_lit_les_scores_qu_une_fois(tmp_path: Path) -> None:
    """Deux requêtes par candidat coûtaient 1,3 s sur une bibliothèque de
    5 700 pistes, à chaque tirage libre, et le verrou de la charnière les
    attendait (GOAL-075-T05)."""
    base = _base_qui_compte(tmp_path)
    apprentissage = Learning(base, floor=0.25, ceiling=4.0, slope=0.5)
    file = Queue(
        FakeSource(CATALOGUE), RealRandom(graine=1), Window(width=0), weigh=apprentissage.weigh
    )

    file.next_pick()

    assert base.lectures == 1, "les scores sont lus plusieurs fois pour un seul tirage"


def test_un_vote_se_voit_des_le_tirage_suivant(tmp_path: Path) -> None:
    """Le relevé vaut pour un tirage, pas au-delà : rien ne garde un score
    périmé (GOAL-075-T05)."""
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    avant = _poids(a, p)

    a.remember(Command.SKIP, p)

    assert _poids(a, p) < avant


def test_les_poids_valent_ceux_lus_cible_par_cible(tmp_path: Path) -> None:
    """Le relevé d'un coup donne exactement ce que donnaient deux lectures par
    candidat (GOAL-075-T05)."""
    base = _base_qui_compte(tmp_path)
    a = Learning(base, floor=0.25, ceiling=4.0, slope=0.5)
    a.remember(Command.SKIP, CATALOGUE[0])
    a.remember(Command.MORE, CATALOGUE[1])
    a.remember(Command.MORE, CATALOGUE[1])

    poids = a.weigh(CATALOGUE)

    attendus = []
    for piste in CATALOGUE:
        de_la_piste = base.scores(PorteeBase.TRACK, piste.identifier)
        de_l_artiste = base.scores(PorteeBase.ARTIST, piste.artist)
        attendus.append(
            track_weight(
                Scores(stop=de_la_piste.stop, encore=de_la_piste.encore),
                Scores(stop=de_l_artiste.stop, encore=de_l_artiste.encore),
                floor=0.25,
                ceiling=4.0,
                slope=0.5,
            )
        )
    assert poids == attendus
    assert len(set(poids)) > 1, "sans vote qui compte, l'égalité ne prouverait rien"
