"""L'apprentissage : ce qu'il lit, ce qu'il écrit, et ce qu'il refuse d'écrire."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.fakes import track
from webradio.adapters.state.database import Scope as PorteeBase
from webradio.adapters.state.database import SqliteState
from webradio.app.learning import Learning
from webradio.core.clock import FrozenClock
from webradio.core.control import Command
from webradio.core.weighting import Scope

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _apprentissage(tmp_path: Path, clock: FrozenClock | None = None) -> Learning:
    database = SqliteState(
        tmp_path / "etat.sqlite3",
        clock=clock or FrozenClock(MIDI),
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return Learning(database, floor=0.25, ceiling=4.0, slope=0.5)


def test_les_deux_vocabulaires_de_portee_coincident() -> None:
    """Le noyau et la base ont chacun leur `Scope`. Le jour où elles
    divergeront, ce test cassera ici plutôt qu'en base."""
    assert {p.value for p in Scope} == {p.value for p in PorteeBase}


def test_une_piste_inconnue_pese_neutre(tmp_path: Path) -> None:
    """Une base vide se comporte comme « personne n'a jamais voté »."""
    assert _apprentissage(tmp_path).weigh(track("1", "Bowie")) == pytest.approx(1.0)


def test_un_stop_fait_reculer_la_piste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    a.remember(Command.SKIP, p)
    assert a.weigh(p) < 1.0


def test_un_encore_fait_avancer_l_artiste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    a.remember(Command.MORE, track("1", "Bowie"))
    # Un autre titre du même artiste profite du vote : c'est la portée croisée.
    assert a.weigh(track("2", "Bowie")) > 1.0


def test_le_vote_porte_sur_l_artiste_seul_et_egalement(tmp_path: Path) -> None:
    """Révision n°16 : la double portée surpondérait. Un `stop` pèse pareil
    sur tous les titres de l'artiste — la piste visée n'écope pas double."""
    a = _apprentissage(tmp_path)
    visee = track("1", "Bowie")
    voisine = track("2", "Bowie")
    autre_artiste = track("3", "Air")
    a.remember(Command.SKIP, visee)
    assert a.weigh(visee) == a.weigh(voisine) < 1.0
    assert a.weigh(autre_artiste) == 1.0


def test_le_poids_ne_descend_jamais_a_zero(tmp_path: Path) -> None:
    """Rien n'est jamais supprimé : le plancher est 0,25 fois, pas 0
    (SPECS.md §7 n°17)."""
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    for _ in range(50):
        a.remember(Command.SKIP, p)
    assert a.weigh(p) == pytest.approx(0.25)


def test_le_poids_ne_depasse_jamais_le_plafond(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = track("1", "Bowie")
    for _ in range(50):
        a.remember(Command.MORE, p)
    assert a.weigh(p) == pytest.approx(4.0)


def test_les_votes_s_oublient_avec_le_temps(tmp_path: Path) -> None:
    """Sans oubli, la radio se figerait sur ce qu'on a cliqué le premier mois
    (SPECS.md §7 n°18)."""
    clock = FrozenClock(MIDI)
    a = _apprentissage(tmp_path, clock)
    p = track("1", "Bowie")
    for _ in range(5):
        a.remember(Command.SKIP, p)
    juste_apres = a.weigh(p)
    clock.advance(timedelta(days=365 * 2))
    bien_plus_tard = a.weigh(p)
    assert juste_apres < bien_plus_tard < 1.0


def test_une_base_devenue_injoignable_rend_un_poids_neutre(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Un tirage sans mémoire vaut infiniment mieux qu'un tirage qui n'a pas
    lieu : la radio ne se tait pas (SPECS.md §5.1).

    La base est construite normalement, **puis** rendue inaccessible — c'est le
    régime « en cours de diffusion ». Une base injoignable **au démarrage**,
    elle, échoue bruyamment, et c'est voulu : les deux régimes d'erreur de
    SPECS.md §5 sont bien distincts.
    """
    folder = tmp_path / "etat"
    folder.mkdir()
    a = _apprentissage(folder)
    p = track("1", "Bowie")
    a.remember(Command.SKIP, p)
    assert a.weigh(p) < 1.0

    folder.chmod(0o500)
    (folder / "etat.sqlite3").chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            assert a.weigh(p) == pytest.approx(1.0)
        assert "tirage neutre" in caplog.text
    finally:
        (folder / "etat.sqlite3").chmod(0o600)
        folder.chmod(0o700)


def test_un_vote_non_retenu_ne_fait_pas_taire_la_radio(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Perdre un vote est regrettable ; couper la radio pour cela serait pire."""
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
    """GOAL-020, révisé avec n°16 : seule l'entrée artiste existe, et elle se
    lit par son nom — jamais d'identifiant opaque, jamais de ligne à zéro."""
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
