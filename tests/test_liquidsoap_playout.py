"""La charnière Liquidsoap : demandé n'est pas à l'antenne (GOAL-016-T07, T08)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.fakes import FakeSource, track
from webradio.app.liquidsoap_playout import LiquidsoapPlayout
from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.bands import Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Control
from webradio.core.jingles import Jingles
from webradio.core.queue import Queue
from webradio.core.rng import ScriptedRandom
from webradio.core.rotation import Window

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
CATALOGUE = [track("1", "Air", genre="électro"), track("2", "Bowie", genre="rock")]


def _playout(folder: Path) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    clock = FrozenClock(MIDI)
    random = ScriptedRandom([0] * 100)
    source = FakeSource(CATALOGUE)
    jingles = Jingles(clock)
    counter = ListenerCount()
    radio = LiveRadio(Control(source=source, random=random, jingles=jingles), counter)
    branche: list[LiquidsoapPlayout] = []
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([], clock),
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=folder,
        on_kind=lambda kind, piste: branche[0].on_kind(kind, piste),
    )
    playout = LiquidsoapPlayout(programme, radio, counter)
    branche.append(playout)
    return playout, radio, clock


def test_un_morceau_demande_n_est_pas_encore_a_l_antenne(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry == "fake://1"
    assert radio.on_air_now() is not None
    assert radio.on_air_now().title is None  # type: ignore[union-attr]

    assert entry is not None
    playout.playing(entry)
    assert radio.on_air_now().title == "titre 1"  # type: ignore[union-attr]


def test_un_jingle_est_une_entree_comme_une_autre(tmp_path: Path) -> None:
    """GOAL-016-T07 — le chemin unique reste `next_entry()`."""
    (tmp_path / "13h.mp3").write_bytes(b"faux jingle")
    playout, radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    clock.advance(timedelta(hours=1))
    entry = playout.next_entry()
    assert entry == str(tmp_path / "13h.mp3")
    assert entry is not None
    playout.playing(entry)
    assert radio.on_air_now().kind.value == "jingle"  # type: ignore[union-attr]


def test_sans_auditeur_la_radio_ne_tourne_pas(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    assert not radio.on_air()
    playout.declare_listeners(2)
    assert radio.on_air()
    playout.declare_listeners(0)
    assert not radio.on_air()


def test_une_entree_inconnue_est_journalisee_sans_rien_declarer(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.playing("/nulle/part.mp3")
    assert radio.on_air_now().title is None  # type: ignore[union-attr]


def test_plus_rien_a_jouer_rend_none(tmp_path: Path) -> None:
    clock = FrozenClock(MIDI)
    random = ScriptedRandom([0] * 10)
    source = FakeSource([])
    counter = ListenerCount()
    jingles = Jingles(clock)
    radio = LiveRadio(Control(source=source, random=random, jingles=jingles), counter)
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([], clock),
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda _kind, _piste: None,
    )
    assert LiquidsoapPlayout(programme, radio, counter).next_entry() is None
