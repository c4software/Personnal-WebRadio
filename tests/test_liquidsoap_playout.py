"""Tests de `LiquidsoapPlayout` : une entrée demandée n'est pas encore à l'antenne (GOAL-016)."""

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from tests.fakes import FakeSource, track
from webradio.adapters.web.api import Vote
from webradio.app.liquidsoap_playout import LiquidsoapPlayout
from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.bands import Band, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
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
    max_duration: timedelta | None = None,
    catalogue: list[Track] | None = None,
    bands: list[Band] | None = None,
    lookahead: int = 1,
) -> tuple[LiquidsoapPlayout, LiveRadio, FrozenClock]:
    clock = FrozenClock(MIDI)
    random = ScriptedRandom([0] * 100)
    source = FakeSource(catalogue if catalogue is not None else CATALOGUE)
    jingles = Jingles(clock)
    counter = ListenerCount()
    control = Control(source=source, random=random, jingles=jingles)
    branche: list[LiquidsoapPlayout] = []
    # Même câblage que main.py : un encore replace l'avance du diffuseur, et
    # le programme connaît le morceau en cours.
    radio = LiveRadio(control, counter, requeue=lambda: branche[0].stash_for_replay())
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1), lookahead=lookahead),
        source=source,
        grille=Schedule(bands or [], clock),
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=folder,
        on_kind=lambda kind, piste, e: branche[0].on_kind(kind, piste, e),
        control=control,
        now_playing=radio.playing_track,
    )
    playout = LiquidsoapPlayout(
        programme,
        radio,
        counter,
        clock=clock,
        resume_fresh_after=resume_fresh_after,
        order_requeue=order_requeue,
        order_skip=order_skip,
        max_duration=max_duration,
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
    assert playout.next_entry() == "annotate:liq_cue_out=1200:fake://long"


def test_une_piste_sous_le_plafond_passe_sans_annotation(tmp_path: Path) -> None:
    playout, _, _ = _playout(tmp_path, max_duration=timedelta(minutes=20))
    assert playout.next_entry() == "fake://1"


def test_sans_plafond_une_piste_longue_passe_entiere(tmp_path: Path) -> None:
    longue = [track("long", "Air", genre="électro", secondes=2400)]
    playout, _, _ = _playout(tmp_path, catalogue=longue)
    assert playout.next_entry() == "fake://long"


def test_une_entree_replacee_apres_un_encore_ne_s_annote_pas_deux_fois(tmp_path: Path) -> None:
    """L'avance replacée après un encore est déjà annotée (GOAL-034) : la
    resservir ne doit pas ajouter un second `annotate:`."""
    longues = [
        track("long1", "Air", genre="électro", secondes=2400),
        track("long2", "Bowie", genre="rock", secondes=2400),
    ]
    playout, _, _ = _playout(tmp_path, max_duration=timedelta(minutes=20), catalogue=longues)
    annotee = playout.next_entry()
    assert annotee == "annotate:liq_cue_out=1200:fake://long1"
    playout.stash_for_replay()
    assert playout.next_entry() == annotee


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
        on_kind=lambda _kind, _piste, _e: None,
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
    assert premier == "fake://1"  # Air, à l'antenne
    playout.playing(premier)
    assert playout.next_entry() == "fake://2"  # Bowie, avance du diffuseur

    assert radio.vote(Vote.MORE).accepted

    a_venir = [u.track.identifier for u in playout.upcoming() if u.track is not None]
    assert a_venir[:2] == ["3", "2"]
    assert playout.next_entry() == "fake://3"


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
    assert premier == "fake://1"
    playout.playing(premier)
    assert playout.next_entry() == "fake://3"  # l'avance, tirée sous 12 h

    clock.advance(timedelta(hours=1, minutes=1))
    playout.stash_for_replay()

    # La suite est tirée à neuf sans attendre que le diffuseur redemande
    # (GOAL-067) : elle est déjà sous la plage de 13 h.
    a_suivre = playout.up_next()
    assert a_suivre is not None and a_suivre[1] is not None
    assert a_suivre[1].identifier == "2"
    assert playout.next_entry() == "fake://2", "tiré sous la plage de 13 h, pas replacé"


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
    assert _avance_demandee(playout) == "fake://3"
    clock.advance(timedelta(hours=1, seconds=10))
    playout.declare_listeners(1)
    assert ordres == ["requeue"]
    assert playout.next_entry() == "fake://2"


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
