"""La charnière Liquidsoap : demandé n'est pas à l'antenne (GOAL-016-T07, T08)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.fakes import FakeSource, track
from webradio.app.liquidsoap_playout import LiquidsoapPlayout
from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.bands import Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.queue import Queue
from webradio.core.rng import ScriptedRandom
from webradio.core.rotation import Window

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
CATALOGUE = [track("1", "Air", genre="électro"), track("2", "Bowie", genre="rock")]


def _playout(
    folder: Path,
    *,
    resume_fresh_after: timedelta | None = None,
    order_requeue: Callable[[], None] | None = None,
    order_skip: Callable[[], None] | None = None,
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
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
        on_kind=lambda kind, piste, e: branche[0].on_kind(kind, piste, e),
    )
    playout = LiquidsoapPlayout(
        programme,
        radio,
        counter,
        clock=clock,
        resume_fresh_after=resume_fresh_after,
        order_requeue=order_requeue,
        order_skip=order_skip,
    )
    branche.append(playout)
    return playout, radio, clock


def _playout_avec_reprise(
    folder: Path, ordres: list[str]
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    return _playout(
        folder,
        resume_fresh_after=timedelta(minutes=15),
        order_requeue=lambda: ordres.append("requeue"),
        order_skip=lambda: ordres.append("skip"),
    )


def test_une_longue_pause_fait_repartir_a_neuf(tmp_path: Path) -> None:
    """SPECS.md §7 n°30 : l'avance rassise est jetée, le reliquat coupé."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    assert playout.next_entry() is not None  # l'avance du diffuseur
    assert playout.up_next() is not None

    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert ordres == ["requeue", "skip"]
    assert playout.up_next() is None  # le registre de l'avance est purgé


def test_une_pause_courte_reprend_l_avance_telle_quelle(tmp_path: Path) -> None:
    """En deçà du seuil, la pause reste le mode nominal (SPECS.md §4.7)."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()

    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=5))
    playout.declare_listeners(1)

    assert ordres == []
    assert playout.up_next() is not None


def test_le_battement_periodique_ne_redate_pas_la_pause(tmp_path: Path) -> None:
    """Le diffuseur redit « 0 » toutes les quinze secondes : la pause se
    mesure depuis le départ du dernier auditeur, pas depuis le dernier écho."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)

    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=10))
    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=10))
    playout.declare_listeners(1)

    assert ordres == ["requeue", "skip"]


def test_sans_morceau_en_cours_le_saut_n_est_pas_ordonne(tmp_path: Path) -> None:
    """À froid, un saut resterait enregistré et mangerait le premier morceau
    (docs/liquidsoap.md §5.bis) : seule la file est purgée."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)
    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert ordres == ["requeue"]


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
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"faux jingle")
    playout, radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    clock.advance(timedelta(hours=1))
    entry = playout.next_entry()
    assert entry is not None
    # Un jingle porte ses propres fondus, plus courts que ceux des morceaux
    # (GOAL-022) : l'entrée est annotée, et c'est elle qui fait clé.
    assert entry.startswith("annotate:liq_fade_in=")
    assert entry.endswith(str(tmp_path / "hours" / "13h.mp3"))
    playout.playing(entry)
    assert radio.on_air_now().kind.value == "jingle"  # type: ignore[union-attr]


def test_sans_auditeur_la_radio_ne_tourne_pas(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    assert not radio.on_air()
    playout.declare_listeners(2)
    assert radio.on_air()
    playout.declare_listeners(0)
    assert not radio.on_air()


def test_une_entree_inconnue_s_affiche_par_ses_etiquettes(tmp_path: Path) -> None:
    """Après un redémarrage, Liquidsoap joue encore un morceau demandé à
    l'ancien processus : plutôt que rien, les étiquettes du décodeur."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.playing("/nulle/part.mp3", "Air", "Sexy Boy")
    a_l_antenne = radio.on_air_now()
    assert a_l_antenne is not None
    assert a_l_antenne.title == "Sexy Boy"
    assert a_l_antenne.artist == "Air"


def test_une_entree_inconnue_sans_etiquettes_n_affiche_rien(tmp_path: Path) -> None:
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
        on_kind=lambda _kind, _piste, _e: None,
    )
    assert LiquidsoapPlayout(programme, radio, counter).next_entry() is None


def test_une_emission_s_affiche_par_son_nom_declare(tmp_path: Path) -> None:
    """GOAL-015-T06 : le flux d'un direct ne porte aucune métadonnée — ce qui
    s'affiche est le nom déclaré au TOML, rien d'autre."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.on_kind(Kind.SHOW, None, "Flash franceinfo")
    radio.declare(Kind.SHOW, None, "Flash franceinfo")
    a_l_antenne = radio.on_air_now()
    assert a_l_antenne is not None
    assert a_l_antenne.kind.value == "emission"
    assert a_l_antenne.title == "Flash franceinfo"
    assert a_l_antenne.artist is None


def test_une_video_lue_s_efface_quand_la_suite_commence(tmp_path: Path) -> None:
    """GOAL-028 : le cache ne garde rien après lecture — question de l'auteur."""
    cache = tmp_path / "cache"
    cache.mkdir()
    video = cache / "v1.m4a"
    video.write_bytes(b"audio")
    ailleurs = tmp_path / "13h.mp3"
    ailleurs.write_bytes(b"jingle")

    playout, _radio, _ = _playout(tmp_path)
    playout._ephemere = cache
    playout.playing(str(video), None, "Alcatraz")
    assert video.exists()  # elle joue encore : on ne touche à rien

    playout.playing(str(ailleurs), None, None)
    assert not video.exists()  # la suite a commencé : effacée
    assert ailleurs.exists()  # rien d'autre n'est touché


def test_la_file_annonce_ce_qui_suit_et_l_encore_le_replace(tmp_path: Path) -> None:
    """GOAL-034/035 : l'avance se voit, et un encore la replace sans la jeter."""
    playout, _radio, _clock = _playout(tmp_path)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    deuxieme = playout.next_entry()  # l'avance du diffuseur
    assert deuxieme is not None

    a_suivre = playout.up_next()
    assert a_suivre is not None
    assert a_suivre[1] is not None  # la piste demandée, connue de la charnière

    playout.stash_for_replay()
    assert playout.up_next() is None  # l'avance est partie se replacer
    # …et le programme la ressert telle quelle au prochain tirage.
    assert playout.next_entry() == deuxieme


def test_l_a_suivre_saute_les_jingles(tmp_path: Path) -> None:
    """Dix secondes d'habillage ne sont pas « à suivre »."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    playout, _radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    clock.advance(timedelta(hours=1))
    jingle = playout.next_entry()  # l'avance est le jingle de 13 h
    assert jingle is not None and "13h.mp3" in jingle

    assert playout.up_next() is None  # rien à annoncer : c'est de l'habillage

    musique = playout.next_entry()  # la vraie avance suivante
    assert musique is not None
    a_suivre = playout.up_next()
    assert a_suivre is not None and a_suivre[1] is not None
