"""Tests de `LiquidsoapPlayout` : une entrée demandée n'est pas encore à l'antenne (GOAL-016)."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta, timezone
from pathlib import Path

import pytest

from tests.fakes import (
    FakeDiffuseur,
    FakeProgrammeEpieLeVerrou,
    FakeProgrammeQuiNoteLesPrisesDAntenne,
    FakeSource,
    FakeSourceEpieLeVerrou,
    track,
)
from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.state.database import SqliteState
from webradio.adapters.web.api import Kind as NatureWeb
from webradio.adapters.web.api import Vote
from webradio.app.liquidsoap_playout import (
    LiquidsoapPlayout,
    _adresse,
    _lire_les_annotations,
)
from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.app.show_scheduler import Shows
from webradio.core.bands import Band, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.queue import Queue
from webradio.core.rng import ScriptedRandom
from webradio.core.rotation import Window
from webradio.core.shows import Show, ShowSchedule

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)
HORIZON = timedelta(hours=3)
CATALOGUE = [track("1", "Air", genre="électro"), track("2", "Bowie", genre="rock")]


def _sans_annotation(entry: str | None) -> str | None:
    """L'adresse d'une entrée, sans le préfixe d'annotation que `next_entry` y
    pose pour qu'elle se décrive (GOAL-086-T03)."""
    return None if entry is None else _adresse(entry)


def _playout(
    folder: Path,
    *,
    resume_fresh_after: timedelta | None = None,
    order_requeue: Callable[[], None] | None = None,
    order_skip: Callable[[], None] | None = None,
    order_announce: Callable[[], None] | None = None,
    max_duration: timedelta | None = None,
    catalogue: list[Track] | None = None,
    source: FakeSource | None = None,
    bands: list[Band] | None = None,
    lookahead: int = 1,
    in_background: Callable[[Callable[[], None]], None] | None = None,
    shows: Shows | None = None,
    clock: FrozenClock | None = None,
    programme_class: type[RadioProgramme] = RadioProgramme,
    draws: list[int] | None = None,
    order_skip_fresh: Callable[[], None] | None = None,
    journal: Callable[[str, str, str], None] | None = None,
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    clock = clock if clock is not None else FrozenClock(MIDI)
    random = ScriptedRandom(draws if draws is not None else [0] * 100)
    source = source if source is not None else FakeSource(catalogue or CATALOGUE)
    jingles = Jingles(clock)
    counter = ListenerCount()
    control = Control(
        source=source,
        random=random,
        jingles=jingles,
        another_episode=lambda: shows is not None and shows.has_another_episode(),
    )
    branche: list[LiquidsoapPlayout] = []

    def _piocher_un_autre_episode() -> None:
        # Même câblage que main.py : la route vide la file du diffuseur, donc
        # le registre local jette son avance sans ordonner de `/requeue`.
        branche[0].drop_advance(requeue=False)
        if order_skip_fresh is not None:
            order_skip_fresh()

    # Même câblage que main.py : un encore replace l'avance du diffuseur.
    radio = LiveRadio(
        control,
        counter,
        requeue=lambda: branche[0].stash_for_replay(),
        skip_fresh=_piocher_un_autre_episode,
        clock=clock,
        journal=journal,
    )
    programme = programme_class(
        queue=Queue(source, random, Window(width=1), lookahead=lookahead),
        source=source,
        grille=Schedule(bands or [], clock),
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=folder,
        horizon=HORIZON,
        on_kind=lambda kind, piste, e, longueur, passable: branche[0].on_kind(
            kind, piste, e, longueur, passable
        ),
        control=control,
        shows=shows,
    )
    playout = LiquidsoapPlayout(
        programme,
        radio,
        counter,
        clock=clock,
        resume_fresh_after=resume_fresh_after,
        order_requeue=order_requeue,
        order_skip=order_skip,
        order_announce=order_announce,
        max_duration=max_duration,
        in_background=in_background,
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
    """Après une longue pause, l'avance est jetée et le reliquat coupé (SPECS.md §7 n°30)."""
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
    # L'avance de la file est jetée aussi : `next_pick` la sert sans regarder
    # la contrainte, donc la garder aurait resservi un tirage d'avant la pause.
    assert playout.up_next() is None


def test_une_pause_courte_reprend_l_avance_telle_quelle(tmp_path: Path) -> None:
    """Sous le seuil, la pause est le fonctionnement normal : rien n'est jeté (SPECS.md §4.7)."""
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
    """Le diffuseur répète le compteur à zéro toutes les quinze secondes. La
    pause se mesure depuis le départ du dernier auditeur, pas depuis le dernier
    battement."""
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


def test_le_saut_part_meme_sans_entree_connue_de_ce_processus(tmp_path: Path) -> None:
    """Après un redémarrage de `radio` seul, Liquidsoap peut jouer un morceau
    que ce processus ignore. Le saut part quand même ; c'est `radio.liq` qui
    sait s'il tient une piste (docs/liquidsoap.md §9)."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)
    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert ordres == ["requeue", "skip"]


def test_un_redemarrage_pendant_une_longue_pause_repart_a_neuf(tmp_path: Path) -> None:
    """Le processus qui démarre pendant une pause la date de son démarrage : sans
    cela, le premier auditeur du matin retrouvait l'avance de la veille, que le
    diffuseur tient toujours (SPECS.md §7 n°29 et n°30)."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)

    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert ordres == ["requeue", "skip"]


def test_un_deploiement_a_chaud_ne_jette_rien(tmp_path: Path) -> None:
    """Redémarré pendant qu'on écoute, le processus reçoit un battement > 0 dans
    les quinze secondes : la pause datée au démarrage est courte, et le morceau
    en cours n'est pas coupé (SPECS.md §7 n°30)."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_reprise(tmp_path, ordres)

    clock.advance(timedelta(seconds=15))
    playout.declare_listeners(1)

    assert ordres == []


def test_un_morceau_demande_n_est_pas_encore_a_l_antenne(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None
    assert _adresse(entry) == "fake://1"
    assert radio.on_air_now() is not None
    assert radio.on_air_now().title is None  # type: ignore[union-attr]

    playout.playing(entry)
    assert radio.on_air_now().title == "titre 1"  # type: ignore[union-attr]


def test_un_jingle_est_une_entree_comme_une_autre(tmp_path: Path) -> None:
    """Un jingle passe par `next_entry()` comme un morceau (GOAL-016-T07)."""
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"faux jingle")
    playout, radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    clock.advance(timedelta(hours=1))
    entry = playout.next_entry()
    assert entry is not None
    # Un jingle a des fondus plus courts que les morceaux (GOAL-022) : l'entrée
    # est annotée, et c'est l'entrée annotée qui sert de clé.
    assert entry.startswith("annotate:liq_fade_in=")
    assert entry.endswith(str(tmp_path / "hours" / "13h.mp3"))
    playout.playing(entry)
    assert radio.on_air_now().kind.value == "jingle"  # type: ignore[union-attr]


def test_une_piste_au_dessus_du_plafond_s_annote_pour_se_couper(tmp_path: Path) -> None:
    """Une piste longue se joue, coupée au plafond par `liq_cue_out` ; le
    crossfade adoucit la coupe (SPECS.md §7 n°32 révisée, docs/liquidsoap.md §7)."""
    longue = [track("long", "Air", genre="électro", secondes=2400)]
    playout, _, _ = _playout(tmp_path, max_duration=timedelta(minutes=20), catalogue=longue)
    entry = playout.next_entry()
    assert entry is not None
    annotations, adresse = _lire_les_annotations(entry)
    assert annotations["liq_cue_out"] == "1200"
    assert adresse == "fake://long"


def test_une_piste_sous_le_plafond_ne_s_annote_pas_pour_se_couper(tmp_path: Path) -> None:
    playout, _, _ = _playout(tmp_path, max_duration=timedelta(minutes=20))
    entry = playout.next_entry()
    assert entry is not None
    annotations, adresse = _lire_les_annotations(entry)
    assert "liq_cue_out" not in annotations
    assert adresse == "fake://1"


def test_sans_plafond_une_piste_longue_passe_entiere(tmp_path: Path) -> None:
    longue = [track("long", "Air", genre="électro", secondes=2400)]
    playout, _, _ = _playout(tmp_path, catalogue=longue)
    entry = playout.next_entry()
    assert entry is not None
    annotations, adresse = _lire_les_annotations(entry)
    assert "liq_cue_out" not in annotations
    assert adresse == "fake://long"


def test_une_entree_replacee_apres_un_encore_ne_s_annote_pas_deux_fois(tmp_path: Path) -> None:
    """L'avance replacée après un encore est déjà annotée (GOAL-034) : la
    resservir ne doit pas ajouter un second `annotate:`."""
    longues = [
        track("long1", "Air", genre="électro", secondes=2400),
        track("long2", "Bowie", genre="rock", secondes=2400),
    ]
    playout, _, _ = _playout(tmp_path, max_duration=timedelta(minutes=20), catalogue=longues)
    annotee = playout.next_entry()
    assert annotee is not None and annotee.startswith("annotate:liq_cue_out=1200,")
    playout.stash_for_replay()
    resservie = playout.next_entry()
    assert resservie == annotee
    assert resservie.count("annotate:") == 1


def test_sans_auditeur_la_radio_ne_tourne_pas(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    assert not radio.on_air()
    playout.declare_listeners(2)
    assert radio.on_air()
    playout.declare_listeners(0)
    assert not radio.on_air()


def test_une_entree_inconnue_s_affiche_par_ses_etiquettes(tmp_path: Path) -> None:
    """Après un redémarrage, Liquidsoap joue encore un morceau demandé à
    l'ancien processus : on affiche les étiquettes du décodeur plutôt que rien."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.playing("/nulle/part.mp3", "Air", "Sexy Boy")
    a_l_antenne = radio.on_air_now()
    assert a_l_antenne is not None
    assert a_l_antenne.title == "Sexy Boy"
    assert a_l_antenne.artist == "Air"


def test_une_entree_d_avant_le_redemarrage_refuse_les_votes(tmp_path: Path) -> None:
    """Ses étiquettes ne disent pas ce qu'elle est : ce peut être une musique
    comme un épisode de plage. On affiche, on ne vote pas (SPECS.md §7 n°42)."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.playing("/nulle/part.mp3", "Air", "Sexy Boy")
    a_l_antenne = radio.on_air_now()
    assert a_l_antenne is not None
    assert a_l_antenne.kind is NatureWeb.UNKNOWN
    assert (a_l_antenne.title, a_l_antenne.artist) == ("Sexy Boy", "Air")

    verdict = radio.vote(Vote.SKIP)

    assert not verdict.accepted
    assert verdict.reason is not None and "vient de redémarrer" in verdict.reason


def test_une_entree_inconnue_sans_etiquettes_n_affiche_rien(tmp_path: Path) -> None:
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    playout.playing("/nulle/part.mp3")
    assert radio.on_air_now().title is None  # type: ignore[union-attr]


def test_une_entree_inconnue_sans_etiquettes_n_efface_pas_l_antenne(tmp_path: Path) -> None:
    """`input.http` annonce un direct deux fois (docs/liquidsoap.md §9). La
    seconde annonce arrive sans étiquettes, après que la première a consommé
    l'entrée : elle ne doit pas effacer l'antenne (GOAL-051)."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None
    playout.playing(entry)
    annonce = radio.on_air_now()
    assert annonce is not None and annonce.title is not None

    playout.playing(entry)  # seconde annonce, entrée déjà consommée

    assert radio.on_air_now() == annonce


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
        horizon=HORIZON,
        on_kind=lambda _kind, _piste, _e, _longueur, _passable: None,
    )
    assert LiquidsoapPlayout(programme, radio, counter).next_entry() is None


def test_une_emission_s_affiche_par_son_nom_declare(tmp_path: Path) -> None:
    """Le flux d'un direct ne porte aucune métadonnée : l'antenne affiche le
    nom déclaré dans le TOML (GOAL-015-T06)."""
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
    """Le cache des vidéos ne garde rien après lecture (GOAL-028)."""
    cache = tmp_path / "cache"
    cache.mkdir()
    video = cache / "v1.m4a"
    video.write_bytes(b"audio")
    ailleurs = tmp_path / "13h.mp3"
    ailleurs.write_bytes(b"jingle")

    playout, _radio, _ = _playout(tmp_path)
    playout._ephemere = cache
    playout.playing(str(video), None, "Alcatraz")
    assert video.exists()  # encore en lecture

    playout.playing(str(ailleurs), None, None)
    assert not video.exists()  # effacée dès que la suite commence
    assert ailleurs.exists()  # hors du cache, intouché


def test_la_file_annonce_ce_qui_suit_et_l_encore_le_replace(tmp_path: Path) -> None:
    """L'avance est exposée, et un encore la replace sans la jeter (GOAL-034, GOAL-035)."""
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
    assert playout.up_next() == a_suivre, "replacée, elle reste à suivre"
    # Le programme la ressert telle quelle au prochain tirage.
    assert playout.next_entry() == deuxieme


def test_la_liste_montre_le_morceau_force_des_le_vote(tmp_path: Path) -> None:
    """Dès le vote, sans attendre que le diffuseur redemande, la liste montre
    le titre forcé par l'encore (même artiste), puis l'avance replacée
    (GOAL-067)."""
    catalogue = [*CATALOGUE, track("3", "Air", genre="électro")]
    playout, radio, _clock = _playout(tmp_path, catalogue=catalogue)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert _sans_annotation(premier) == "fake://1"  # Air, à l'antenne
    assert premier is not None
    playout.playing(premier)
    assert _sans_annotation(playout.next_entry()) == "fake://2"  # Bowie, avance du diffuseur

    assert radio.vote(Vote.MORE).accepted

    a_venir = [u.track.identifier for u in playout.upcoming() if u.track is not None]
    assert a_venir[:2] == ["3", "2"]
    assert _sans_annotation(playout.next_entry()) == "fake://3"


BOWIE = [
    track("1", "Bowie", genre="rock"),
    track("2", "Bowie", genre="rock"),
    track("3", "Bowie", genre="rock"),
]


def test_l_encore_ne_rend_pas_un_morceau_que_l_antenne_vient_de_passer(tmp_path: Path) -> None:
    """La file passe 1 puis 2 ; un encore sur 2 rendait 1, qui venait de passer
    (SPECS.md §4.6, GOAL-083-T11)."""
    playout, radio, _clock = _playout(tmp_path, catalogue=BOWIE, draws=[0, 1, *[0] * 100])
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert _sans_annotation(premier) == "fake://1"
    assert premier is not None
    playout.playing(premier)
    deuxieme = playout.next_entry()
    assert _sans_annotation(deuxieme) == "fake://2"
    assert deuxieme is not None
    playout.playing(deuxieme)

    assert radio.vote(Vote.MORE).accepted
    assert _sans_annotation(playout.next_entry()) == "fake://3"


def test_une_entree_seulement_demandee_ne_compte_pas_comme_passee(tmp_path: Path) -> None:
    """C'est `playing()` qui alimente la mémoire, pas la demande : l'avance du
    diffuseur peut être jetée sans passer (GOAL-083-T11)."""
    playout, radio, _clock = _playout(tmp_path, catalogue=BOWIE, draws=[0, 1, *[0] * 100])
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert _sans_annotation(premier) == "fake://1"
    assert premier is not None
    playout.playing(premier)
    assert _sans_annotation(playout.next_entry()) == "fake://2"  # demandée, jamais annoncée

    assert radio.vote(Vote.MORE).accepted
    assert _sans_annotation(playout.next_entry()) == "fake://2"


def test_l_a_suivre_saute_les_jingles(tmp_path: Path) -> None:
    """Un jingle n'est pas annoncé comme « à suivre » : on annonce la musique
    que la file a déjà tirée derrière (GOAL-054)."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    playout, _radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    clock.advance(timedelta(hours=1))
    jingle = playout.next_entry()  # l'avance du diffuseur : le jingle de 13 h
    assert jingle is not None and "13h.mp3" in jingle

    a_suivre = playout.up_next()
    assert a_suivre is not None
    assert a_suivre[0] is Kind.MUSIC, "jamais le jingle"
    assert a_suivre[1] is not None

    musique = playout.next_entry()  # l'avance suivante
    assert musique is not None
    assert playout.up_next() == a_suivre, "c'est bien elle qui suit"


# Deux plages consécutives : électro à MIDI, rock une heure plus tard.
DEUX_PLAGES = [
    Band(start=time(12, 0), end=time(13, 0), genres=("électro",)),
    Band(start=time(13, 0), end=time(14, 0), genres=("rock",)),
]
# Deux titres d'électro, pour que l'avance ait une adresse distincte du
# morceau en cours : le playout indexe ses entrées par adresse.
DEUX_ELECTRO = [*CATALOGUE, track("3", "Portishead", genre="électro")]


def test_l_avance_replacee_ne_rejoue_pas_ce_qu_un_moment_fini_a_tire(tmp_path: Path) -> None:
    """Une entrée demandée sous la plage de 12 h ne se replace pas sous celle
    de 13 h : elle est jetée et la suite est tirée à neuf (décision n°33)."""
    playout, _radio, clock = _playout(tmp_path, bands=DEUX_PLAGES, catalogue=DEUX_ELECTRO)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert _sans_annotation(premier) == "fake://1"
    assert premier is not None
    playout.playing(premier)
    assert _sans_annotation(playout.next_entry()) == "fake://3"  # l'avance, tirée sous 12 h

    clock.advance(timedelta(hours=1, minutes=1))
    playout.stash_for_replay()

    # La suite est tirée à neuf sans attendre que le diffuseur redemande
    # (GOAL-067) : elle est déjà sous la plage de 13 h.
    a_suivre = playout.up_next()
    assert a_suivre is not None and a_suivre[1] is not None
    assert a_suivre[1].identifier == "2"
    assert _sans_annotation(playout.next_entry()) == "fake://2", (
        "tiré sous la plage de 13 h, pas replacé"
    )


def test_l_avance_replacee_dans_le_meme_moment_se_ressert_telle_quelle(tmp_path: Path) -> None:
    playout, _radio, clock = _playout(tmp_path, bands=DEUX_PLAGES)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    deuxieme = playout.next_entry()

    clock.advance(timedelta(minutes=10))
    playout.stash_for_replay()

    assert playout.next_entry() == deuxieme


def _playout_avec_requeue(
    folder: Path, ordres: list[str], bands: list[Band] | None = None
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    return _playout(
        folder,
        order_requeue=lambda: ordres.append("requeue"),
        bands=bands,
        catalogue=DEUX_ELECTRO if bands else None,
    )


def _avance_demandee(playout: LiquidsoapPlayout) -> str:
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    deuxieme = playout.next_entry()
    assert deuxieme is not None
    return deuxieme


def test_l_heure_pleine_remet_l_avance_en_question(tmp_path: Path) -> None:
    """L'avance a été décidée avant l'heure pleine, donc sans le jingle. Au
    premier battement après l'heure, le playout replace l'avance et fait
    redemander : le jingle sort à la jonction suivante, l'avance passe derrière."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_requeue(tmp_path, ordres)
    deuxieme = _avance_demandee(playout)

    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)

    assert ordres == ["requeue"]
    jingle = playout.next_entry()
    assert jingle is not None and "13h.mp3" in jingle
    assert playout.next_entry() == deuxieme, "replacée derrière le jingle, pas jetée"


def test_l_heure_pleine_ne_remet_en_question_qu_une_fois(tmp_path: Path) -> None:
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_requeue(tmp_path, ordres)
    _avance_demandee(playout)
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    playout.next_entry()  # le diffuseur a redemandé
    clock.advance(timedelta(seconds=15))
    playout.declare_listeners(1)
    assert ordres == ["requeue"]


def test_avant_l_heure_pleine_l_avance_reste(tmp_path: Path) -> None:
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_requeue(tmp_path, ordres)
    _avance_demandee(playout)
    clock.advance(timedelta(minutes=40))
    playout.declare_listeners(1)
    assert ordres == []


def test_sans_auditeur_l_heure_ne_remet_rien_en_question(tmp_path: Path) -> None:
    """Sans auditeur, rien n'est décodé ni demandé ; la purge de reprise
    (SPECS.md §7 n°30) jugera l'avance au retour."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_requeue(tmp_path, ordres)
    _avance_demandee(playout)
    playout.declare_listeners(0)
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(0)
    assert ordres == []


def test_pendant_une_emission_l_heure_pleine_ne_compte_pas(tmp_path: Path) -> None:
    """Les jingles dus pendant une émission sont abandonnés (SPECS.md §4.11) :
    rien à faire passer devant l'avance."""
    ordres: list[str] = []
    playout, radio, clock = _playout_avec_requeue(tmp_path, ordres)
    _avance_demandee(playout)
    radio.declare(Kind.SHOW, None, "Matinale franceinfo")
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    assert ordres == []


def test_au_battement_un_moment_fini_jette_l_avance(tmp_path: Path) -> None:
    """Quand la plage de 13 h commence, l'avance tirée sous celle de 12 h est
    jetée et la suite est tirée à neuf sous la plage ouverte."""
    ordres: list[str] = []
    playout, _radio, clock = _playout_avec_requeue(tmp_path, ordres, bands=DEUX_PLAGES)
    assert _sans_annotation(_avance_demandee(playout)) == "fake://3"
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    assert ordres == ["requeue"]
    assert _sans_annotation(playout.next_entry()) == "fake://2"


def test_un_moment_fini_compte_meme_pendant_une_emission(tmp_path: Path) -> None:
    ordres: list[str] = []
    playout, radio, clock = _playout_avec_requeue(tmp_path, ordres, bands=DEUX_PLAGES)
    _avance_demandee(playout)
    radio.declare(Kind.SHOW, None, "LEGEND")
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    assert ordres == ["requeue"]


TROIS = [*CATALOGUE, track("3", "Portishead", genre="trip-hop")]


def test_la_liste_des_prochains_titres_porte_l_heure_estimee(tmp_path: Path) -> None:
    """L'heure estimée part de la fin du morceau en cours, puis s'additionne
    durée après durée (GOAL-058)."""
    playout, _radio, clock = _playout(tmp_path, catalogue=TROIS, lookahead=2)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()  # l'avance du diffuseur ; la file se remplit derrière

    liste = playout.upcoming()
    assert [i.kind for i in liste] == [Kind.MUSIC, Kind.MUSIC, Kind.MUSIC]
    assert [i.at for i in liste] == [
        clock.now() + timedelta(minutes=3),
        clock.now() + timedelta(minutes=6),
        clock.now() + timedelta(minutes=9),
    ]
    assert playout.up_next() == (liste[0].kind, liste[0].track, liste[0].label)


def test_un_debut_date_en_utc_est_ramene_au_fuseau_de_l_horloge(tmp_path: Path) -> None:
    """Le diffuseur date le début en secondes Unix, lues en UTC. La grille et
    les jingles horaires vivent dans le fuseau de l'horloge : sans conversion,
    l'heure estimée porte un autre fuseau et la couture lit la grille deux
    heures à côté."""
    paris = timezone(timedelta(hours=2))
    clock = FrozenClock(MIDI.astimezone(paris))
    playout, _radio, _clock = _playout(tmp_path, catalogue=TROIS, lookahead=2, clock=clock)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier, started_at=MIDI)
    playout.next_entry()

    liste = playout.upcoming()
    assert liste[0].at == clock.now() + timedelta(minutes=3)
    assert all(i.at is None or i.at.tzinfo is paris for i in liste)


def test_sans_morceau_en_cours_connu_la_liste_n_a_pas_d_heure(tmp_path: Path) -> None:
    playout, _radio, _clock = _playout(tmp_path, catalogue=TROIS, lookahead=2)
    playout.declare_listeners(1)
    playout.next_entry()
    assert all(i.at is None for i in playout.upcoming())


def test_l_estimation_ne_tombe_jamais_dans_le_passe(tmp_path: Path) -> None:
    """Après une pause, un morceau commencé il y a longtemps finit au plus tôt
    maintenant."""
    playout, _radio, clock = _playout(tmp_path, catalogue=TROIS, lookahead=1)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()
    clock.advance(timedelta(minutes=30))
    assert playout.upcoming()[0].at == clock.now()


def test_un_jingle_qui_attend_chez_le_diffuseur_se_nomme_dans_la_liste(tmp_path: Path) -> None:
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    playout, _radio, clock = _playout(tmp_path, catalogue=TROIS, lookahead=1)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    clock.advance(timedelta(hours=1))
    playout.next_entry()  # le jingle de 13 h
    liste = playout.upcoming()
    assert (liste[0].kind, liste[0].label) == (Kind.JINGLE, "13h")
    assert liste[1].kind is Kind.MUSIC


def test_retirer_le_titre_qui_attend_chez_le_diffuseur_fait_redemander(tmp_path: Path) -> None:
    ordres: list[str] = []
    playout, _radio, _clock = _playout(
        tmp_path, catalogue=TROIS, lookahead=2, order_requeue=lambda: ordres.append("requeue")
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()
    attendu = playout.upcoming()[0].track
    assert attendu is not None

    assert playout.withdraw(attendu.identifier)

    assert ordres == ["requeue"]
    assert attendu not in [i.track for i in playout.upcoming()]
    assert playout.next_entry() != f"fake://{attendu.identifier}"


def test_retirer_un_titre_de_l_avance_de_la_file_le_remplace(tmp_path: Path) -> None:
    ordres: list[str] = []
    playout, _radio, _clock = _playout(
        tmp_path, catalogue=TROIS, lookahead=2, order_requeue=lambda: ordres.append("requeue")
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()
    avant = playout.upcoming()
    dans_la_file = avant[1].track
    assert dans_la_file is not None

    assert playout.withdraw(dans_la_file.identifier)

    assert ordres == [], "la file suffit : le diffuseur n'a rien à redemander"
    apres = playout.upcoming()
    assert len(apres) == len(avant), "remplacé, pas seulement retiré"
    assert dans_la_file not in [i.track for i in apres]


def test_retirer_un_titre_qui_n_attend_plus_rend_faux(tmp_path: Path) -> None:
    playout, _radio, _clock = _playout(tmp_path, catalogue=TROIS, lookahead=2)
    playout.declare_listeners(1)
    assert not playout.withdraw("nulle-part")


def test_jeter_l_avance_ne_replace_rien_et_fait_redemander(tmp_path: Path) -> None:
    """Une suite rompue ne doit pas revenir par l'avance (GOAL-059)."""
    ordres: list[str] = []
    playout, _radio, _clock = _playout(
        tmp_path, catalogue=TROIS, lookahead=2, order_requeue=lambda: ordres.append("requeue")
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()
    assert playout.upcoming()

    playout.drop_advance()

    assert ordres == ["requeue"]
    assert playout.upcoming() == []
    assert playout.next_entry() is not None, "le diffuseur redemande, la file retire"


def test_le_morceau_suivant_se_rend_sans_attendre_la_preparation_de_l_avance(
    tmp_path: Path,
) -> None:
    """Le diffuseur attend cette réponse pour jouer, et remplir l'avance coûte
    `draw.lookahead` tirages. À la reprise, où l'avance est vide et le cache
    de bibliothèque expiré, ils ont dépassé le délai d'attente du diffuseur,
    qui abandonne et coupe (GOAL-075)."""
    reportees: list[Callable[[], None]] = []
    playout, _, _ = _playout(tmp_path, lookahead=4, in_background=reportees.append)

    entree = playout.next_entry()

    assert entree is not None, "la réponse ne dépend pas de la préparation"
    # Seul le morceau rendu, que le diffuseur tient déjà : aucune avance
    # derrière lui, puisque rien n'a été préparé pendant la requête.
    assert len(playout.upcoming()) == 1
    assert len(reportees) == 1, "la préparation est reportée, pas abandonnée"


def test_l_avance_se_remplit_quand_la_preparation_reportee_s_execute(
    tmp_path: Path,
) -> None:
    """Reportée n'est pas perdue : le lanceur la joue hors de la requête, et
    l'avance retrouve sa profondeur (GOAL-075)."""
    reportees: list[Callable[[], None]] = []
    playout, _, _ = _playout(tmp_path, lookahead=4, in_background=reportees.append)
    playout.next_entry()

    for preparer in reportees:
        preparer()

    assert len(playout.upcoming()) == 5, "le morceau rendu, puis les quatre d'avance"


def test_sans_lanceur_la_preparation_se_fait_sur_place(tmp_path: Path) -> None:
    """Le défaut garde le comportement d'avant : c'est ce qui rend tous les
    autres tests déterministes, sans fil ni attente (GOAL-075)."""
    playout, _, _ = _playout(tmp_path, lookahead=4)

    playout.next_entry()

    assert len(playout.upcoming()) == 5, "le morceau rendu, puis les quatre d'avance"


def test_le_branchement_n_attend_pas_le_remplissage_de_l_avance(tmp_path: Path) -> None:
    """Le diffuseur annonce l'auditeur AVANT de rendre l'antenne, et attend la
    réponse : une avance rassise à replacer y coûtait `draw.lookahead` tirages
    pendant que l'auditeur attendait le son (GOAL-075)."""
    reportees: list[Callable[[], None]] = []
    playout, _, _ = _playout(tmp_path, lookahead=4, in_background=reportees.append)
    playout.next_entry()
    for preparer in reportees:
        preparer()
    reportees.clear()

    playout.stash_for_replay()

    assert reportees, "le replacement prépare hors de la requête, comme la jonction"


# ── Une émission ne s'inscrit qu'à la prise d'antenne (GOAL-083-T04) ─────────

EMISSION = Show(name="A la French", days=("all",), hour=time(12, 0))
EPISODE = "https://exemple.test/ep1.mp3"


class FluxDUnEpisode:
    """Un flux de podcast d'essai : un épisode d'une heure, toujours le même."""

    def episodes(self, url: str) -> list[EpisodeDuFlux]:  # noqa: ARG002
        return [
            EpisodeDuFlux(
                identifier="ep1",
                title="épisode ep1",
                published_at=MIDI,
                audio=EPISODE,
                duration=timedelta(hours=1),
            )
        ]


def _playout_avec_emission(
    folder: Path, clock: FrozenClock, **kwargs: object
) -> tuple[LiquidsoapPlayout, LiveRadio, SqliteState]:
    state = SqliteState(
        folder / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    emissions = Shows(
        ShowSchedule([EMISSION]),
        FluxDUnEpisode(),  # type: ignore[arg-type]
        state,
        clock,
        {"A la French": ("https://exemple.test/flux.xml",)},
        ScriptedRandom([0] * 50),
    )
    playout, radio, _clock = _playout(folder, clock=clock, shows=emissions, **kwargs)  # type: ignore[arg-type]
    return playout, radio, state


def test_une_emission_jetee_par_la_reprise_a_neuf_repasse_dans_sa_fenetre(
    tmp_path: Path,
) -> None:
    """La purge jette l'entrée sans la jouer (SPECS.md §7 n°30). Inscrite à la
    demande, l'émission ne repassait jamais, même dans sa fenêtre de rattrapage
    (SPECS.md §4.11)."""
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    ordres: list[str] = []
    playout, _radio, state = _playout_avec_emission(
        tmp_path,
        clock,
        resume_fresh_after=timedelta(minutes=15),
        order_requeue=lambda: ordres.append("requeue"),
        order_skip=lambda: ordres.append("skip"),
    )
    playout.declare_listeners(1)
    assert _sans_annotation(playout.next_entry()) == EPISODE

    playout.declare_listeners(0)
    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert ordres == ["requeue", "skip"]
    assert _sans_annotation(playout.next_entry()) == EPISODE, "elle n'a pas passé, elle reste due"
    assert state.last_airing("A la French") is None


def test_une_emission_jetee_par_le_changement_de_theme_repasse(tmp_path: Path) -> None:
    """« Autre thème » jette l'avance sans la rejouer (GOAL-059) : l'émission
    qui s'y trouvait n'a pas passé."""
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    playout, _radio, state = _playout_avec_emission(tmp_path, clock)
    playout.declare_listeners(1)
    assert _sans_annotation(playout.next_entry()) == EPISODE

    playout.drop_advance()

    assert _sans_annotation(playout.next_entry()) == EPISODE
    assert state.last_airing("A la French") is None


def test_une_emission_qui_ne_prend_jamais_l_antenne_reste_a_diffuser(tmp_path: Path) -> None:
    """Une adresse que le diffuseur n'arrive pas à ouvrir n'est jamais annoncée
    (docs/liquidsoap.md §3) : c'est l'entrée suivante qui commence à sa place."""
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    playout, _radio, state = _playout_avec_emission(tmp_path, clock)
    playout.declare_listeners(1)
    assert _sans_annotation(playout.next_entry()) == EPISODE
    remplacante = playout.next_entry()
    assert remplacante is not None and remplacante != EPISODE

    playout.playing(remplacante)

    assert state.last_airing("A la French") is None
    assert _sans_annotation(playout.next_entry()) == EPISODE


def test_une_emission_a_l_antenne_est_retenue_et_ne_repasse_pas(tmp_path: Path) -> None:
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    playout, _radio, state = _playout_avec_emission(tmp_path, clock)
    playout.declare_listeners(1)
    episode = playout.next_entry()
    assert _sans_annotation(episode) == EPISODE

    assert episode is not None
    playout.playing(episode)

    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "ep1"
    assert _sans_annotation(playout.next_entry()) != EPISODE, "elle est passée, la case est sautée"


def test_le_morceau_d_avance_qui_commence_ne_jette_pas_l_emission(tmp_path: Path) -> None:
    """Le diffuseur demande un morceau d'avance (docs/liquidsoap.md §3) : celui
    décidé avant l'émission commence après elle sans rien dire de son sort."""
    clock = FrozenClock(MIDI - timedelta(minutes=1))
    playout, _radio, state = _playout_avec_emission(tmp_path, clock)
    playout.declare_listeners(1)
    avance = playout.next_entry()
    assert avance is not None and avance != EPISODE
    clock.advance(timedelta(minutes=2))
    episode = playout.next_entry()
    assert _sans_annotation(episode) == EPISODE

    playout.playing(avance)
    assert episode is not None
    playout.playing(episode)

    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "ep1"


def test_un_encore_pendant_qu_une_emission_attend_ne_la_fait_pas_passer_deux_fois(
    tmp_path: Path,
) -> None:
    """Un encore replace l'avance sans la jeter (GOAL-034) : l'émission qui s'y
    trouvait passera, plus tard. Prendre le jingle qui la précède pour la preuve
    qu'elle a été jetée la rendait une seconde fois, et elle passait deux fois."""
    (tmp_path / "encore.mp3").write_bytes(b"faux jingle")
    clock = FrozenClock(MIDI - timedelta(minutes=1))
    catalogue = [*CATALOGUE, track("3", "Air", genre="électro")]
    playout, radio, state = _playout_avec_emission(tmp_path, clock, catalogue=catalogue)
    playout.declare_listeners(1)
    musique = playout.next_entry()
    assert _sans_annotation(musique) == "fake://1"
    assert musique is not None
    playout.playing(musique)
    clock.advance(timedelta(minutes=2))
    assert _sans_annotation(playout.next_entry()) == EPISODE, "l'émission attend chez le diffuseur"

    assert radio.vote(Vote.MORE).accepted

    servies: list[str] = []
    for _ in range(4):
        entree = playout.next_entry()
        assert entree is not None
        servies.append(_sans_annotation(entree) or entree)
        playout.playing(entree)

    assert servies.count(EPISODE) == 1, "l'émission ne passe qu'une fois"
    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "ep1"


# ── Ce que le diffuseur jette sans le dire (GOAL-083-T05) ───────────────────

DIRECT = Show(name="Le flash", days=("all",), hour=time(12, 0), duration=timedelta(minutes=5))
FLUX_DU_DIRECT = "https://exemple.test/direct.mp3"
# La plage change à la fin du direct : ce qui a gelé dessous est de l'électro,
# tout ce qui se tire après est du rock. C'est ce qui distingue l'avance gelée
# d'un tirage frais, sans dépendre d'un identifiant.
PLAGES_AUTOUR_DU_DIRECT = [
    Band(start=time(12, 0), end=time(12, 5), genres=("électro",)),
    Band(start=time(12, 5), end=time(13, 0), genres=("rock",)),
]
AUTOUR_DU_DIRECT = [*CATALOGUE, track("4", "Blur", genre="rock")]


def _playout_avec_direct(
    folder: Path, clock: FrozenClock, **kwargs: object
) -> tuple[LiquidsoapPlayout, LiveRadio]:
    state = SqliteState(
        folder / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    emissions = Shows(
        ShowSchedule([DIRECT]),
        FluxDUnEpisode(),  # type: ignore[arg-type]
        state,
        clock,
        {},
        ScriptedRandom([0] * 50),
        streams={DIRECT.name: FLUX_DU_DIRECT},
    )
    playout, radio, _clock = _playout(
        folder,
        clock=clock,
        shows=emissions,
        **kwargs,  # type: ignore[arg-type]
    )
    return playout, radio


def _un_direct_et_sa_fin(
    playout: LiquidsoapPlayout, clock: FrozenClock, *, annoncer_le_gele: bool = False
) -> tuple[str, str]:
    """Rejoue la séquence du script : un direct, le morceau qu'il redemande
    aussitôt et qui gèle sous la case, puis la purge de la fin du direct et le
    morceau frais (radio.liq, `vider_l_avance`).

    `annoncer_le_gele` ajoute ce que fait vraiment le diffuseur : la source
    musicale défile en sourdine sous le direct et chaque morceau s'annonce
    (GOAL-090).

    Rend le morceau gelé et le morceau frais.
    """
    playout.declare_listeners(1)
    direct = playout.next_entry()
    assert direct is not None and direct.startswith("live:")
    gele = playout.next_entry()
    assert gele is not None
    playout.playing(direct)
    if annoncer_le_gele:
        playout.playing(gele)
    clock.advance(timedelta(minutes=6))
    frais = playout.next_entry()
    assert frais is not None and frais != gele
    playout.playing(frais)
    return gele, frais


def test_l_avance_gelee_sous_un_direct_n_est_plus_annoncee_a_suivre(tmp_path: Path) -> None:
    """La fin d'un direct est une purge (SPECS.md §7 n°22) : le diffuseur jette
    l'avance et redemande, sans route pour le dire. L'ordre des demandes suffit
    à l'apprendre — ce qui commence est plus récent que ce qui a été jeté."""
    clock = FrozenClock(MIDI)
    playout, _radio = _playout_avec_direct(
        tmp_path, clock, bands=PLAGES_AUTOUR_DU_DIRECT, catalogue=AUTOUR_DU_DIRECT
    )

    _gele, _frais = _un_direct_et_sa_fin(playout, clock)

    a_suivre = playout.up_next()
    assert a_suivre is not None and a_suivre[1] is not None
    assert a_suivre[1].genre == "rock", "l'électro gelée sous le direct a été jetée"


def test_un_morceau_annonce_sous_un_direct_ne_prend_pas_l_antenne(tmp_path: Path) -> None:
    """Le diffuseur consomme la source musicale en sourdine sous un direct
    (docs/liquidsoap.md §16.1) : les morceaux gelés s'annoncent sans que
    personne les entende. Ni antenne, ni journal, ni encore (GOAL-090)."""
    clock = FrozenClock(MIDI)
    journal: list[tuple[str, str, str]] = []
    playout, radio = _playout_avec_direct(
        tmp_path,
        clock,
        catalogue=TROIS,
        journal=lambda nature, titre, artiste: journal.append((nature, titre, artiste)),
        programme_class=FakeProgrammeQuiNoteLesPrisesDAntenne,
    )
    espion = playout._programme
    assert isinstance(espion, FakeProgrammeQuiNoteLesPrisesDAntenne)
    espion.noter()
    playout.declare_listeners(1)
    direct = playout.next_entry()
    assert direct is not None and direct.startswith("live:")
    gele = playout.next_entry()
    assert gele is not None
    playout.playing(direct)
    journal.clear()

    playout.playing(gele)

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.SHOW, "le direct tient toujours l'antenne"
    assert antenne.title == DIRECT.name
    assert journal == [], "le morceau gelé n'entre pas au journal des titres"
    assert espion.prises == [], "l'encore doit encore pouvoir rendre le morceau gelé"


def test_un_morceau_annonce_apres_la_fin_du_direct_est_pris_et_le_gele_jete(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Le direct se prolonge du temps de résolution du morceau frais
    (SPECS.md §7 n°22) : l'annonce du frais arrive après la fin portée par son
    instruction, elle est acceptée, et l'ordre des demandes apprend que le
    morceau gelé a été jeté (n°22, GOAL-090)."""
    clock = FrozenClock(MIDI)
    playout, radio = _playout_avec_direct(
        tmp_path, clock, bands=PLAGES_AUTOUR_DU_DIRECT, catalogue=AUTOUR_DU_DIRECT
    )

    with caplog.at_level(logging.INFO):
        gele, _frais = _un_direct_et_sa_fin(playout, clock, annoncer_le_gele=True)

    antenne = radio.on_air_now()
    assert antenne is not None and antenne.kind is NatureWeb.MUSIC
    assert f"demandée puis jetée par le diffuseur : {gele.split('?', 1)[0]}" in caplog.text
    a_suivre = playout.up_next()
    assert a_suivre is not None and a_suivre[1] is not None
    assert a_suivre[1].genre == "rock", "l'électro gelée sous le direct a été jetée"


def test_l_avance_gelee_sous_un_direct_n_est_pas_replacee_au_battement(tmp_path: Path) -> None:
    """Restée en attente, elle était replacée et diffusée au premier battement
    après l'heure pleine (décision n°33), une heure après sa plage."""
    clock = FrozenClock(MIDI)
    ordres: list[str] = []
    playout, _radio = _playout_avec_direct(
        tmp_path, clock, catalogue=TROIS, order_requeue=lambda: ordres.append("requeue")
    )
    _un_direct_et_sa_fin(playout, clock)
    ordres.clear()

    clock.advance(timedelta(hours=1))
    playout.declare_listeners(1)

    assert ordres == [], "il ne reste rien en attente à remettre en question"


def test_le_battement_ne_fait_pas_rejouer_le_morceau_qui_vient_de_commencer(
    tmp_path: Path,
) -> None:
    """L'annonce du diffuseur attend le verrou pendant une préparation de fond :
    le battement peut replacer une entrée déjà commencée. Elle est à l'antenne,
    pas à rejouer."""
    ordres: list[str] = []
    playout, radio, clock = _playout_avec_requeue(tmp_path, ordres)
    entree = _avance_demandee(playout)

    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    assert ordres == ["requeue"], "l'heure pleine est passée, l'avance est replacée"

    playout.playing(entree, "Air", "Sexy Boy")

    a_l_antenne = radio.on_air_now()
    assert a_l_antenne is not None
    assert a_l_antenne.title != "Sexy Boy", "déclarée avec sa nature, pas avec ses étiquettes"
    assert playout.next_entry() != entree, "elle vient de commencer, elle ne se rejoue pas"


def test_une_emission_replacee_qui_prend_l_antenne_s_inscrit(tmp_path: Path) -> None:
    """Même course, avec une émission : reprise à l'antenne, sa diffusion
    s'inscrit (SPECS.md §4.11.1). Sans cela elle restait demandée pour toujours,
    et aucune autre ne pouvait plus être rendue."""
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    playout, radio, state = _playout_avec_emission(tmp_path, clock)
    playout.declare_listeners(1)
    episode = playout.next_entry()
    assert _sans_annotation(episode) == EPISODE
    playout.stash_for_replay()

    assert episode is not None
    playout.playing(episode)

    assert radio.playing_kind() is Kind.SHOW
    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "ep1"


# ── Tout ce qui touche la file passe sous le verrou (GOAL-083-T06) ───────────

CATALOGUE_LARGE = [track(str(i), f"artiste {i}", genre="rock") for i in range(1, 6)]


def _playout_epie(
    folder: Path,
    *,
    lookahead: int = 2,
    resume_fresh_after: timedelta | None = None,
    order_requeue: Callable[[], None] | None = None,
) -> tuple[LiquidsoapPlayout, FakeProgrammeEpieLeVerrou, FrozenClock]:
    playout, _, clock = _playout(
        folder,
        catalogue=CATALOGUE_LARGE,
        lookahead=lookahead,
        resume_fresh_after=resume_fresh_after,
        order_requeue=order_requeue,
        programme_class=FakeProgrammeEpieLeVerrou,
    )
    espion = playout._programme
    assert isinstance(espion, FakeProgrammeEpieLeVerrou)
    espion.epier(playout._verrou)
    return playout, espion, clock


def test_le_retrait_d_un_titre_de_la_file_se_fait_sous_le_verrou(tmp_path: Path) -> None:
    """La préparation de fond boucle sur l'avance de la file ; la retirer sous
    ses pieds lui faisait lever une `IndexError` non attrapée, et la
    préparation s'arrêtait (GOAL-083-T06)."""
    playout, espion, _ = _playout_epie(tmp_path)
    playout.next_entry()
    a_venir = playout.upcoming()
    # Le premier est chez le diffuseur ; le second vient de l'avance de la file.
    dans_la_file = a_venir[1].track
    assert dans_la_file is not None

    assert playout.withdraw(dans_la_file.identifier)

    assert espion.verrous["withdraw"], "la file est touchée hors du verrou"


def test_l_avance_jetee_se_jette_sous_le_verrou(tmp_path: Path) -> None:
    """Le bouton « Autre thème » sur une suite jette l'avance de la file
    (GOAL-059) pendant que la préparation de fond la lit (GOAL-083-T06)."""
    playout, espion, _ = _playout_epie(tmp_path)
    playout.next_entry()

    playout.drop_advance()

    assert espion.verrous["forget_advance"], "la file est touchée hors du verrou"


def test_la_rupture_de_suite_se_fait_sous_le_verrou(tmp_path: Path) -> None:
    """`main.py` appelait `RadioProgramme.break_run()` directement : la
    charnière expose le geste verrouillé (GOAL-083-T06)."""
    playout, espion, _ = _playout_epie(tmp_path)

    playout.break_run()

    assert espion.verrous["break_run"], "la suite est rompue hors du verrou"


def test_l_avance_replacee_se_replace_sous_le_verrou(tmp_path: Path) -> None:
    """Le vote « encore » et le battement replacent l'avance du diffuseur dans
    le programme : la lecture du moment et le replacement touchent la file
    (GOAL-083-T06)."""
    playout, espion, _ = _playout_epie(tmp_path)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    playout.next_entry()
    espion.verrous.clear()

    playout.stash_for_replay()

    assert espion.verrous["current_moment"], "le moment est lu hors du verrou"
    assert espion.verrous["replay_later"], "l'avance est replacée hors du verrou"


def test_la_reprise_a_neuf_oublie_l_attente_sous_le_verrou(tmp_path: Path) -> None:
    """Après une longue pause sans auditeur, tout repart d'un tirage neuf
    (SPECS.md §7 n°30) : l'oubli vide la file (GOAL-083-T06)."""
    ordres: list[str] = []
    playout, espion, clock = _playout_epie(
        tmp_path,
        resume_fresh_after=timedelta(minutes=15),
        order_requeue=lambda: ordres.append("requeue"),
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)

    playout.declare_listeners(0)
    playout.next_entry()
    espion.verrous.clear()
    clock.advance(timedelta(minutes=20))
    playout.declare_listeners(1)

    assert espion.verrous["forget_pending"], "la file est vidée hors du verrou"


# ── Le parcours de bibliothèque sort du verrou (GOAL-075-T04) ────────────────


def test_la_bibliotheque_se_parcourt_hors_du_verrou_avant_de_tirer(tmp_path: Path) -> None:
    """Un parcours de genre absent du cache coûte une dizaine d'appels à la
    source. Sous le verrou, `/playout/next` et `/playing` l'attendent autant de
    fois qu'il y a de créneaux à remplir (GOAL-075-T04)."""
    source = FakeSourceEpieLeVerrou(CATALOGUE_LARGE)
    playout, _, _ = _playout(
        tmp_path,
        source=source,
        lookahead=4,
        bands=[Band(start=time(0, 0), end=time(23, 59), genres=("rock",))],
        in_background=lambda travail: travail(),
    )
    source.epier(playout._verrou)

    playout.next_entry()

    assert ("rock", False) in source.parcours, "la bibliothèque n'est parcourue que sous le verrou"


def test_la_duree_du_morceau_demande_voyage_jusqu_a_l_antenne(tmp_path: Path) -> None:
    """L'antenne ne sait où en est la lecture que si la longueur a suivi la
    déclaration (GOAL-085)."""
    playout, radio, clock = _playout(tmp_path)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None

    playout.playing(entry)
    clock.advance(timedelta(seconds=20))

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.duration_seconds == 180
    assert antenne.elapsed_seconds == 20


def test_une_piste_plus_longue_que_le_plafond_annonce_le_plafond(tmp_path: Path) -> None:
    """Elle sera coupée par `liq_cue_out` : annoncer sa durée entière ferait
    une barre qui n'atteint jamais sa fin (SPECS.md §7 n°32)."""
    longue = [track("long", "Air", genre="électro", secondes=2400)]
    playout, radio, _ = _playout(tmp_path, max_duration=timedelta(minutes=20), catalogue=longue)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None

    playout.playing(entry)

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.duration_seconds == 1200


def test_une_entree_inconnue_n_annonce_aucune_duree(tmp_path: Path) -> None:
    """Après un redémarrage, le diffuseur joue une entrée demandée à l'ancien
    processus : ses étiquettes s'affichent, sa durée reste inconnue."""
    playout, radio, _ = _playout(tmp_path)
    playout.declare_listeners(1)

    playout.playing("fake://inconnue", artist="Air", title="titre inconnu")

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.title == "titre inconnu"
    assert antenne.duration_seconds is None


# ── L'avance datée connaît les cases de podcasts (GOAL-086-T04) ──────────────

DIMANCHE_20H = datetime(2026, 9, 6, 20, 0, tzinfo=UTC)  # 2026-09-06 est un dimanche
ACTUS = Show(name="Podcasts - actus", days=("sunday",), hour=time(20, 0), end=time(21, 0))
LONGS = Show(name="Podcasts - longs formats", days=("sunday",), hour=time(21, 0), end=time(23, 0))
FLUX_ACTUS = "https://exemple.test/actus.xml"
FLUX_ACTUS_BIS = "https://exemple.test/actus-bis.xml"
FLUX_ACTUS_TER = "https://exemple.test/actus-ter.xml"
FLUX_LONGS = "https://exemple.test/longs.xml"
ADRESSES_DU_DIMANCHE: dict[str, tuple[str, ...]] = {
    ACTUS.name: (FLUX_ACTUS,),
    LONGS.name: (FLUX_LONGS,),
}
ADRESSES_A_DEUX_FLUX: dict[str, tuple[str, ...]] = {
    ACTUS.name: (FLUX_ACTUS, FLUX_ACTUS_BIS),
    LONGS.name: (FLUX_LONGS,),
}
# Trois flux : un épisode à l'antenne, un demandé d'avance, et encore un à
# piocher — ce qu'un « Passer » demande pour être accepté (SPECS.md §7 n°45).
ADRESSES_A_TROIS_FLUX: dict[str, tuple[str, ...]] = {
    ACTUS.name: (FLUX_ACTUS, FLUX_ACTUS_BIS, FLUX_ACTUS_TER),
    LONGS.name: (FLUX_LONGS,),
}
# La plage musicale du soir : la même occurrence à 20 h 01 et à 21 h 10, donc
# la même clé tant que les cases de podcasts n'y entrent pas.
ROCK_DU_SOIR = [Band(start=time(20, 0), end=time(22, 0), genres=("rock",))]
CATALOGUE_DU_SOIR = [
    track("1", "Air", genre="électro"),
    track("2", "Bowie", genre="rock"),
    track("3", "Blur", genre="rock"),
    track("4", "Oasis", genre="rock"),
]


def _episode_de_soiree(guid: str) -> EpisodeDuFlux:
    return EpisodeDuFlux(
        identifier=guid,
        title=f"épisode {guid}",
        published_at=DIMANCHE_20H,
        audio=f"https://exemple.test/{guid}.mp3",
        duration=timedelta(minutes=71),
    )


class FluxParAdresse:
    """Un flux d'essai qui rend un catalogue différent selon l'adresse."""

    def __init__(self, par_url: dict[str, list[EpisodeDuFlux]]) -> None:
        self._par_url = par_url

    def episodes(self, url: str) -> list[EpisodeDuFlux]:
        return list(self._par_url.get(url, []))

    def cached(self, url: str, *, stale_ok: bool = False) -> list[EpisodeDuFlux] | None:
        """Le cache est chaud : une plage vient de lire ses flux à la jonction
        précédente, et `podcast.cache_seconds` vaut 900 s par défaut."""
        del stale_ok
        return list(self._par_url.get(url, []))


def _playout_du_dimanche(
    folder: Path,
    clock: FrozenClock,
    ordres: list[str],
    *,
    addresses: dict[str, tuple[str, ...]] | None = None,
) -> tuple[LiquidsoapPlayout, SqliteState]:
    state = SqliteState(
        folder / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    emissions = Shows(
        ShowSchedule([ACTUS, LONGS]),
        FluxParAdresse(
            {
                FLUX_ACTUS: [_episode_de_soiree("a1")],
                FLUX_ACTUS_BIS: [_episode_de_soiree("a2")],
                FLUX_ACTUS_TER: [_episode_de_soiree("a3")],
                FLUX_LONGS: [_episode_de_soiree("l1")],
            }
        ),  # type: ignore[arg-type]
        state,
        clock,
        addresses if addresses is not None else ADRESSES_DU_DIMANCHE,
        ScriptedRandom([0] * 50),
    )
    playout, _radio, _clock = _playout(
        folder,
        clock=clock,
        shows=emissions,
        bands=ROCK_DU_SOIR,
        catalogue=CATALOGUE_DU_SOIR,
        order_requeue=lambda: ordres.append("requeue"),
        order_skip_fresh=lambda: ordres.append("skip-fresh"),
    )
    return playout, state


def _radio_du_dimanche(
    folder: Path,
    clock: FrozenClock,
    ordres: list[str],
    *,
    addresses: dict[str, tuple[str, ...]] | None = None,
) -> tuple[LiquidsoapPlayout, LiveRadio, SqliteState]:
    """La même soirée, avec la façade que l'API interroge."""
    state = SqliteState(
        folder / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    emissions = Shows(
        ShowSchedule([ACTUS, LONGS]),
        FluxParAdresse(
            {
                FLUX_ACTUS: [_episode_de_soiree("a1")],
                FLUX_ACTUS_BIS: [_episode_de_soiree("a2")],
                FLUX_ACTUS_TER: [_episode_de_soiree("a3")],
                FLUX_LONGS: [_episode_de_soiree("l1")],
            }
        ),  # type: ignore[arg-type]
        state,
        clock,
        addresses if addresses is not None else ADRESSES_DU_DIMANCHE,
        ScriptedRandom([0] * 50),
    )
    playout, radio, _clock = _playout(
        folder,
        clock=clock,
        shows=emissions,
        bands=ROCK_DU_SOIR,
        catalogue=CATALOGUE_DU_SOIR,
        order_requeue=lambda: ordres.append("requeue"),
        order_skip_fresh=lambda: ordres.append("skip-fresh"),
    )
    return playout, radio, state


def test_l_ouverture_d_une_plage_de_podcasts_jette_la_musique_d_avance(tmp_path: Path) -> None:
    """La soirée du 2026-09-06 : « actus » n'a plus rien de neuf à 20 h 01, la
    musique d'avance est tirée, et elle passait à 21 h 12 alors que
    « longs formats » était ouverte depuis 21 h. La plage musicale ne change
    pas entre les deux : c'est la case qui doit rassir l'avance (décision n°43).
    """
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H - timedelta(minutes=3))
    playout, _state = _playout_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    musique = playout.next_entry()
    assert musique is not None
    playout.playing(musique)
    assert playout.next_entry() is not None, "l'avance de 19 h 57"

    clock.advance(timedelta(minutes=3))
    episode = playout.next_entry()
    assert _sans_annotation(episode) == "https://exemple.test/a1.mp3"
    clock.advance(timedelta(minutes=1))
    assert episode is not None
    playout.playing(episode)
    avance = playout.next_entry()
    assert avance is not None and (_sans_annotation(avance) or "").startswith("fake://"), (
        "« actus » n'a plus rien de neuf"
    )

    clock.advance(timedelta(minutes=59, seconds=5))
    playout.declare_listeners(1)

    assert ordres == ["requeue"], "« longs formats » s'ouvre : l'avance est rassise"
    assert _sans_annotation(playout.next_entry()) == "https://exemple.test/l1.mp3"


def test_l_avance_tiree_pendant_qu_un_episode_attend_est_rejugee_quand_il_commence(
    tmp_path: Path,
) -> None:
    """Une plage dont le seul flux n'a plus rien de neuf tire une musique
    pendant qu'un épisode attend. Elle doit être rejugée à la prise d'antenne
    de l'épisode, sinon elle s'intercale entre deux épisodes de la plage."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, _state = _playout_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    episode = playout.next_entry()
    assert episode is not None and (_sans_annotation(episode) or "").endswith(".mp3")
    avance = playout.next_entry()
    assert avance is not None and (_sans_annotation(avance) or "").startswith("fake://"), (
        "le seul flux de la case n'a plus rien de neuf"
    )

    clock.advance(timedelta(minutes=1))
    playout.playing(episode)
    playout.declare_listeners(1)

    assert ordres == ["requeue"]
    assert playout.next_entry() != avance, "l'avance rassie a été jetée"


def test_un_episode_demande_avant_end_mais_pas_commence_est_jete_a_end(tmp_path: Path) -> None:
    """L'épisode entamé avant `end` finit (SPECS.md §7 n°35), mais celui qui
    n'a fait qu'être demandé n'a rien entamé : la case fermée, il est jeté et
    rien ne s'inscrit (SPECS.md §4.11.1)."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H + timedelta(hours=2, minutes=59, seconds=50))
    playout, state = _playout_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    assert _sans_annotation(playout.next_entry()) == "https://exemple.test/l1.mp3", (
        "l'épisode attend, seul"
    )

    clock.advance(timedelta(seconds=15))
    playout.declare_listeners(1)

    assert ordres == ["requeue"]
    assert state.last_airing(LONGS.name) is None, "il n'a pas passé, rien n'est inscrit"
    suivante = playout.next_entry()
    assert suivante is not None and (_sans_annotation(suivante) or "").startswith("fake://"), (
        "la case est fermée"
    )


def test_la_musique_tiree_faute_d_episode_neuf_n_est_pas_rejugee_a_chaque_battement(
    tmp_path: Path,
) -> None:
    """Une case qui n'a rien de neuf reste ouverte : la musique tirée dessous
    porte la même clé qu'elle, et le battement de quinze secondes ne doit pas
    ordonner un `/requeue` de plus à chaque passage."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, _state = _playout_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    episode = playout.next_entry()
    assert episode is not None
    clock.advance(timedelta(minutes=1))
    playout.playing(episode)
    playout.declare_listeners(1)
    ordres.clear()
    avance = playout.next_entry()
    assert avance is not None and (_sans_annotation(avance) or "").startswith("fake://")

    for _ in range(4):
        clock.advance(timedelta(seconds=15))
        playout.declare_listeners(1)

    assert ordres == [], "la case n'a pas changé, l'avance tient"


def test_un_podcast_seul_et_un_direct_ne_sont_pas_rejuges(tmp_path: Path) -> None:
    """Leur case est à eux : elle n'entre pas dans la clé de l'avance, et un
    changement de plage musicale ne doit pas les jeter avant qu'ils commencent
    (SPECS.md §7 n°5)."""
    ordres: list[str] = []
    podcast = tmp_path / "podcast"
    podcast.mkdir()
    clock = FrozenClock(MIDI + timedelta(minutes=1))
    playout, _radio, state = _playout_avec_emission(
        podcast,
        clock,
        bands=PLAGES_AUTOUR_DU_DIRECT,
        order_requeue=lambda: ordres.append("requeue"),
    )
    playout.declare_listeners(1)
    episode = playout.next_entry()
    assert _sans_annotation(episode) == EPISODE

    clock.advance(timedelta(minutes=5))
    playout.declare_listeners(1)

    assert ordres == [], "la plage musicale a changé, l'épisode demandé reste dû"
    assert episode is not None
    playout.playing(episode)
    assert state.last_airing("A la French") is not None

    direct = tmp_path / "direct"
    direct.mkdir()
    horloge = FrozenClock(MIDI + timedelta(minutes=1))
    en_direct, _radio = _playout_avec_direct(
        direct,
        horloge,
        bands=PLAGES_AUTOUR_DU_DIRECT,
        order_requeue=lambda: ordres.append("requeue"),
    )
    en_direct.declare_listeners(1)
    entree = en_direct.next_entry()
    assert entree is not None and entree.startswith("live:")

    horloge.advance(timedelta(minutes=5))
    en_direct.declare_listeners(1)

    assert ordres == [], "le direct demandé n'est pas remis en question"


# ── Le diffuseur redit ce qu'il joue après un redémarrage (GOAL-086-T03) ─────

# Ce qu'une entrée porte depuis `next_entry` : la forme exacte que le diffuseur
# rend à l'annonce (docs/liquidsoap.md §7 et §12).
EMISSION_DECRITE = (
    'annotate:radio_kind="emission",radio_label="A la French, n° 12",'
    'radio_duration="1800":https://exemple.test/ep1.mp3'
)
MUSIQUE_DECRITE = (
    'annotate:radio_kind="musique",radio_label="Sexy Boy",radio_duration="200":fake://9'
)


def _playout_neuf(
    folder: Path, diffuseur: FakeDiffuseur
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    """Un processus qui vient de démarrer : il n'a rien annoncé, et le
    diffuseur note les ordres qu'il reçoit."""
    return _playout(
        folder,
        order_requeue=diffuseur.requeue,
        order_skip=diffuseur.skip,
        order_announce=diffuseur.announce,
    )


def test_au_premier_battement_un_processus_neuf_fait_redire_l_antenne_et_redecide_l_avance(
    tmp_path: Path,
) -> None:
    """Le diffuseur n'annonce qu'au début d'une entrée : sans cela l'antenne
    resterait inconnue jusqu'à la jonction suivante, et l'avance décidée par le
    processus précédent passerait (SPECS.md §7 n°42)."""
    diffuseur = FakeDiffuseur()
    playout, _radio, _clock = _playout_neuf(tmp_path, diffuseur)

    playout.declare_listeners(1)

    assert diffuseur.ordres == ["announce", "requeue"]

    playout.declare_listeners(1)

    assert diffuseur.ordres == ["announce", "requeue"], "une seule fois par processus"


def test_sans_auditeur_un_processus_neuf_ne_fait_rien_redire(tmp_path: Path) -> None:
    """Rien n'est décodé ni demandé sans auditeur (SPECS.md §1) : il n'y a rien
    à redire tant que personne n'écoute."""
    diffuseur = FakeDiffuseur()
    playout, _radio, _clock = _playout_neuf(tmp_path, diffuseur)

    playout.declare_listeners(0)

    assert diffuseur.ordres == []


def test_une_entree_inconnue_qui_se_decrit_restaure_sa_nature_et_son_libelle(
    tmp_path: Path,
) -> None:
    """L'entrée porte sa nature depuis `next_entry` : le processus neuf la relit
    et rouvre les refus au lieu de rester en nature inconnue."""
    diffuseur = FakeDiffuseur()
    playout, radio, _clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)

    playout.playing(EMISSION_DECRITE)

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.SHOW
    assert antenne.title == "A la French, n° 12"
    assert antenne.duration_seconds == 1800
    verdict = radio.vote(Vote.SKIP)
    assert not verdict.accepted
    assert verdict.reason is not None and "émission" in verdict.reason


def test_une_musique_d_avant_le_redemarrage_restaure_son_titre_et_accepte_le_stop(
    tmp_path: Path,
) -> None:
    """Aucune source ne retrouve une piste par son identifiant : la musique se
    déclare sans `Track`. Le `stop` est accepté et coupe, l'encore n'a rien à
    peser (SPECS.md §7 n°42)."""
    diffuseur = FakeDiffuseur()
    playout, radio, clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)
    diffuseur.ordres.clear()

    playout.playing(MUSIQUE_DECRITE, "Air", None, started_at=clock.now() - timedelta(seconds=30))

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.MUSIC
    assert (antenne.title, antenne.artist) == ("Sexy Boy", "Air")
    assert antenne.duration_seconds == 200
    assert antenne.elapsed_seconds == 30, "l'écoulé part du vrai début, pas de la ré-annonce"
    assert radio.vote(Vote.SKIP).accepted
    assert radio.playing_track() is None, "sans piste, l'encore ne retient rien"


def test_une_reannonce_de_l_entree_en_cours_ne_redeclare_rien(tmp_path: Path) -> None:
    """La ré-annonce arrive après le début : redéclarer relancerait l'écoulé à
    zéro et inscrirait le titre une seconde fois au journal."""
    diffuseur = FakeDiffuseur()
    playout, radio, clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None
    playout.playing(entry)
    clock.advance(timedelta(seconds=40))
    avant = radio.on_air_now()

    playout.playing(entry, started_at=clock.now())

    assert radio.on_air_now() == avant
    assert avant is not None and avant.elapsed_seconds == 40


def test_une_entree_sans_description_reste_inconnue(tmp_path: Path) -> None:
    """Une entrée demandée par un script d'avant ce déploiement ne porte aucune
    nature : elle s'affiche par ses étiquettes et les votes restent refusés."""
    diffuseur = FakeDiffuseur()
    playout, radio, _clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)

    playout.playing("https://exemple.test/ep1.mp3", "Air", "Sexy Boy")

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.UNKNOWN
    assert not radio.vote(Vote.SKIP).accepted


def test_une_entree_dont_la_nature_ne_se_lit_pas_reste_inconnue(tmp_path: Path) -> None:
    """Une nature annotée que le noyau ne connaît pas ne se devine pas."""
    diffuseur = FakeDiffuseur()
    playout, radio, _clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)

    playout.playing('annotate:radio_kind="karaoké":fake://9', "Air", "Sexy Boy")

    antenne = radio.on_air_now()
    assert antenne is not None and antenne.kind is NatureWeb.UNKNOWN


def test_un_direct_d_avant_le_redemarrage_restaure_son_libelle_et_sa_fin(
    tmp_path: Path,
) -> None:
    """Un direct n'est pas annoté : c'est son instruction qui le décrit,
    `live:<fin en secondes Unix>:<libellé>:<url>` (GOAL-088-T05). Sans elle, un
    `radio` redémarré pendant le flash laisserait le morceau d'avant à
    l'antenne jusqu'au bout de la case (SPECS.md §7 n°42)."""
    diffuseur = FakeDiffuseur()
    playout, radio, clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)
    fin = int((clock.now() + timedelta(minutes=6)).timestamp())

    playout.playing(f"live:{fin}:Flash franceinfo:https://exemple.test/direct.mp3")

    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.SHOW
    assert antenne.title == "Flash franceinfo"
    assert antenne.duration_seconds == 360, "la fin est absolue, pas une durée"


@pytest.mark.parametrize(
    "instruction",
    [
        "live:1788794282:Flash franceinfo",
        "live:tout-a-l-heure:Flash franceinfo:https://exemple.test/direct.mp3",
    ],
)
def test_une_instruction_de_direct_illisible_n_annonce_rien(
    instruction: str, tmp_path: Path
) -> None:
    """Tronquée ou mal datée, elle ne se devine pas : mieux vaut une antenne
    inconnue qu'un libellé et une fin inventés."""
    diffuseur = FakeDiffuseur()
    playout, radio, _clock = _playout_neuf(tmp_path, diffuseur)
    playout.declare_listeners(1)

    playout.playing(instruction)

    assert radio.on_air_now().title is None  # type: ignore[union-attr]


def test_un_titre_a_guillemets_et_virgules_traverse_l_annotation(tmp_path: Path) -> None:
    """L'analyseur de Liquidsoap refuse l'entrée entière sur une valeur mal
    citée, et elle n'est alors jamais jouée (docs/liquidsoap.md §13)."""
    epineux = Track(
        identifier="9",
        title='Ne dis rien, dit "il"\\ : voilà',
        artist="Air",
        genre="électro",
        duration=timedelta(seconds=200),
    )
    playout, radio, _clock = _playout(tmp_path, catalogue=[epineux])
    playout.declare_listeners(1)
    entry = playout.next_entry()
    assert entry is not None

    annotations, adresse = _lire_les_annotations(entry)

    assert annotations["radio_label"] == epineux.title
    assert adresse == "fake://9"

    playout.playing(entry)

    antenne = radio.on_air_now()
    assert antenne is not None and antenne.title == epineux.title


# ── Passer un épisode de plage pioche un autre épisode (GOAL-086-T05) ────────


def test_passer_un_episode_de_plage_pioche_un_autre_episode(tmp_path: Path) -> None:
    """La soirée du dimanche, sur la pile réelle : l'épisode « actus » passe,
    le vote est accepté, `/skip-fresh` part, et le `/next` suivant rend
    l'épisode d'un autre flux — pas la musique d'avance (SPECS.md §7 n°44)."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, radio, _state = _radio_du_dimanche(
        tmp_path, clock, ordres, addresses=ADRESSES_A_TROIS_FLUX
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert _sans_annotation(premier) == "https://exemple.test/a2.mp3"
    assert premier is not None
    playout.playing(premier)
    avance = playout.next_entry()
    assert avance is not None, "l'avance tirée pendant l'épisode"

    verdict = radio.vote(Vote.SKIP)
    assert verdict.accepted, verdict.reason
    assert ordres == ["skip-fresh"], "un /requeue de plus ferait redemander deux fois"

    suivant = playout.next_entry()
    assert _sans_annotation(suivant) == "https://exemple.test/a3.mp3"


def test_l_episode_passe_reste_inscrit_comme_diffuse(tmp_path: Path) -> None:
    """Il a réellement pris l'antenne : le repasser à la jonction suivante
    serait pire que de le passer (SPECS.md §4.11.1)."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, radio, state = _radio_du_dimanche(
        tmp_path, clock, ordres, addresses=ADRESSES_A_TROIS_FLUX
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    assert playout.next_entry() is not None
    assert radio.vote(Vote.SKIP).accepted

    passe = state.last_airing(f"{ACTUS.name}/{FLUX_ACTUS_BIS}")
    assert passe is not None and passe.episode == "a2"


def test_sans_autre_episode_neuf_le_stop_pendant_un_episode_est_refuse(tmp_path: Path) -> None:
    """Un seul flux, un seul épisode : il n'y a rien à mettre à la place, et le
    refus le dit plutôt que de couper vers la musique d'avance."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, radio, _state = _radio_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)

    verdict = radio.vote(Vote.SKIP)
    assert not verdict.accepted
    assert verdict.reason is not None and "aucun autre épisode à piocher" in verdict.reason
    assert ordres == []


def test_un_episode_restaure_apres_redemarrage_reste_passable(tmp_path: Path) -> None:
    """L'entrée porte `radio_skippable` : un processus neuf qui la reçoit à la
    ré-annonce retrouve un épisode passable, pas une émission ordinaire
    (SPECS.md §7 n°42 et n°44)."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    ancien, _radio, _state = _radio_du_dimanche(
        tmp_path, clock, ordres, addresses=ADRESSES_A_DEUX_FLUX
    )
    ancien.declare_listeners(1)
    entree = ancien.next_entry()
    assert entree is not None
    annotations, _ = _lire_les_annotations(entree)
    assert annotations["radio_skippable"] == "oui"

    neuf, radio, _autre = _radio_du_dimanche(
        tmp_path / "neuf", clock, ordres, addresses=ADRESSES_A_DEUX_FLUX
    )
    neuf.declare_listeners(1)
    neuf.playing(entree)
    antenne = radio.on_air_now()
    assert antenne is not None
    assert antenne.kind is NatureWeb.SHOW
    assert antenne.skippable


# ── Les deux entrées en vol d'un « Passer » (GOAL-087-T01) ───────────────────


def test_apres_un_passer_les_deux_entrees_en_vol_sont_des_episodes(tmp_path: Path) -> None:
    """`/skip-fresh` vide la file puis en résout une entrée fraîche : le fil
    d'avance demande un `/next`, `fetch()` un second, et les deux sont
    consommés (docs/liquidsoap.md §12 et §14). Si le second rendait une
    musique, elle se résoudrait la première et prendrait l'antenne au saut —
    exactement ce que la décision n°44 refuse."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, radio, _state = _radio_du_dimanche(
        tmp_path, clock, ordres, addresses=ADRESSES_A_TROIS_FLUX
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    assert playout.next_entry() is not None, "l'avance tirée pendant l'épisode"

    verdict = radio.vote(Vote.SKIP)
    assert verdict.accepted, verdict.reason

    en_vol = [playout.next_entry(), playout.next_entry()]
    adresses = [_sans_annotation(entree) for entree in en_vol]
    assert all(adresse is not None and adresse.endswith(".mp3") for adresse in adresses), (
        f"les deux entrées en vol sont des épisodes, pas une musique : {adresses}"
    )
    assert len(set(adresses)) == 2, "et jamais deux fois le même"


# ── Un épisode oublié du registre s'inscrit quand même (GOAL-087-T02) ────────


def test_un_episode_oublie_du_registre_s_inscrit_quand_il_joue(tmp_path: Path) -> None:
    """L'entrée se déclare par ses annotations, mais rien ne l'inscrivait comme
    diffusée : elle restait repiochable et pouvait repasser dans la même plage
    (docs/liquidsoap.md §14). Retrouvée par son adresse dans les catalogues en
    cache, sans réseau."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    ancien, _ = _playout_du_dimanche(tmp_path, clock, ordres)
    ancien.declare_listeners(1)
    entree = ancien.next_entry()
    assert _sans_annotation(entree) == "https://exemple.test/a1.mp3"

    neuf, etat = _playout_du_dimanche(tmp_path / "neuf", clock, ordres)
    neuf.declare_listeners(1)
    assert entree is not None
    neuf.playing(entree)

    passe = etat.last_airing(ACTUS.name)
    assert passe is not None and passe.episode == "a1"


def test_un_episode_introuvable_dans_les_catalogues_ne_s_inscrit_pas_et_le_dit(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Cache vide ou flux inconnu : il n'y a rien à inscrire, et se taire
    laisserait croire que la diffusion a été retenue."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, etat = _playout_du_dimanche(tmp_path, clock, ordres)
    playout.declare_listeners(1)
    inconnue = 'annotate:radio_kind="emission",radio_label="ailleurs":https://ailleurs.test/x.mp3'

    with caplog.at_level(logging.INFO):
        playout.playing(inconnue)

    assert "introuvable dans les catalogues" in caplog.text
    assert etat.last_airing(ACTUS.name) is None


def test_apres_un_passer_l_episode_qui_joue_en_second_est_inscrit(tmp_path: Path) -> None:
    """Les deux entrées en vol d'un « Passer » sont consommées, et la plus vite
    résolue prend l'antenne (SPECS.md §7 n°45). Celle de rang inférieur joue
    ensuite : les deux épisodes doivent s'inscrire, sinon le second repasserait
    dans la même plage (SPECS.md §4.11.1)."""
    ordres: list[str] = []
    clock = FrozenClock(DIMANCHE_20H)
    playout, radio, etat = _radio_du_dimanche(
        tmp_path, clock, ordres, addresses=ADRESSES_A_TROIS_FLUX
    )
    playout.declare_listeners(1)
    premier = playout.next_entry()
    assert premier is not None
    playout.playing(premier)
    assert playout.next_entry() is not None
    assert radio.vote(Vote.SKIP).accepted

    ancienne = playout.next_entry()
    recente = playout.next_entry()
    assert ancienne is not None and recente is not None
    clock.advance(timedelta(minutes=1))
    playout.playing(recente)
    clock.advance(timedelta(minutes=71))
    playout.playing(ancienne)

    assert etat.last_airing(f"{ACTUS.name}/{FLUX_ACTUS_TER}") is not None, "la plus ancienne"
    assert etat.last_airing(f"{ACTUS.name}/{FLUX_ACTUS}") is not None, "la plus récente"
