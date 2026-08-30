"""La charnière : ce qu'elle traduit, ce qu'elle journalise, ce qu'elle refuse."""

import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from tests.fakes import FakeSource, track
from webradio.app.playout import RadioProgramme
from webradio.core.bands import Band, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Command, Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.programmes import Programme, Programming
from webradio.core.queue import Queue
from webradio.core.rng import ScriptedRandom
from webradio.core.rotation import Window

CATALOGUE = [
    track("1", "Air", genre="électro"),
    track("2", "Bowie", genre="rock"),
    track("3", "Portishead", genre="trip-hop"),
]
MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _programme(
    folder: Path,
    *,
    source: FakeSource | None = None,
    bands: list[Band] | None = None,
    clock: FrozenClock | None = None,
) -> tuple[RadioProgramme, list[tuple[Kind, Track | None, str | None]]]:
    reelle = source if source is not None else FakeSource(CATALOGUE)
    montre = clock if clock is not None else FrozenClock(MIDI)
    random = ScriptedRandom([0] * 200)
    vues: list[tuple[Kind, Track | None, str | None]] = []
    return (
        RadioProgramme(
            queue=Queue(reelle, random, Window(width=1)),
            source=reelle,
            grille=Schedule(bands or [], montre),
            jingles=Jingles(montre),
            clock=montre,
            random=random,
            jingle_folder=folder,
            on_kind=lambda n, p, e: vues.append((n, p, e)),
        ),
        vues,
    )


def test_la_suivante_est_une_entree_que_ffmpeg_peut_ouvrir(tmp_path: Path) -> None:
    programme, _ = _programme(tmp_path)
    assert programme.next_entry() == "fake://1"


def test_la_nature_est_declaree_a_chaque_morceau(tmp_path: Path) -> None:
    """C'est ce qui permet à l'API de dire ce qui passe, et au noyau de refuser
    un vote au bon moment."""
    programme, vues = _programme(tmp_path)
    programme.next_entry()
    assert vues[-1][0] is Kind.MUSIC
    assert vues[-1][1] is not None
    assert vues[-1][1].artist == "Air"


def test_un_jingle_du_et_present_passe_avant_la_musique(tmp_path: Path) -> None:
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"faux jingle")
    clock = FrozenClock(MIDI)
    programme, vues = _programme(tmp_path, clock=clock)
    clock.advance(timedelta(hours=1))
    assert programme.next_entry() == str(tmp_path / "hours" / "13h.mp3")
    assert vues[-1] == (Kind.JINGLE, None, None)


def test_un_jingle_du_mais_absent_ne_signale_rien(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """C'est le mode d'emploi normal, pas une dégradation (SPECS.md §4.3) : le
    dossier peut ne contenir que trois fichiers."""
    clock = FrozenClock(MIDI)
    programme, vues = _programme(tmp_path, clock=clock)
    clock.advance(timedelta(hours=1))
    with caplog.at_level(logging.WARNING):
        assert programme.next_entry() == "fake://1"
    assert caplog.text == ""
    assert vues[-1][0] is Kind.MUSIC


def test_le_repli_d_une_plage_sans_musique_est_journalise(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bands = [Band(MIDI.time(), time(23, 0), ("jazz",))]
    programme, _ = _programme(tmp_path, bands=bands)
    with caplog.at_level(logging.INFO):
        assert programme.next_entry() is not None
    assert "jazz" in caplog.text


def test_une_source_injoignable_fait_couper_en_le_disant(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """La radio ne se tait pas : elle coupe, et elle dit pourquoi
    (SPECS.md §5.1). Jamais un silence, jamais une boucle."""
    programme, _ = _programme(tmp_path, source=FakeSource(CATALOGUE, injoignable=True))
    with caplog.at_level(logging.WARNING):
        assert programme.next_entry() is None
    assert "injoignable" in caplog.text


def test_une_bibliotheque_vide_fait_couper_en_le_disant(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    programme, _ = _programme(tmp_path, source=FakeSource([]))
    with caplog.at_level(logging.WARNING):
        assert programme.next_entry() is None
    assert "plus rien" in caplog.text


def test_preparer_prend_de_l_avance(tmp_path: Path) -> None:
    """La contrainte de docs/ffmpeg.md §2.2 : résoudre pendant que le courant
    joue, pas à la jonction."""
    source = FakeSource(CATALOGUE)
    programme, _ = _programme(tmp_path, source=source)
    programme.prepare()
    appels = source.appels
    assert appels > 0
    programme.next_entry()
    assert source.appels == appels, "suivante() a réinterrogé la source"


def test_preparer_avale_une_panne_plutot_que_de_la_propager(tmp_path: Path) -> None:
    """Se préparer est une commodité : échouer à prendre de l'avance ne doit
    jamais tuer le fil qui alimente la chaîne."""
    programme, _ = _programme(tmp_path, source=FakeSource(CATALOGUE, injoignable=True))
    programme.prepare()


def test_plusieurs_jingles_dus_passent_a_la_suite(tmp_path: Path) -> None:
    """Un morceau long a enjambé deux heures : tous passent, le plus ancien
    d'abord (SPECS.md §4.3)."""
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"a")
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "14h.mp3").write_bytes(b"b")
    clock = FrozenClock(MIDI)
    programme, _ = _programme(tmp_path, clock=clock)
    clock.advance(timedelta(hours=2))
    assert programme.next_entry() == str(tmp_path / "hours" / "13h.mp3")
    assert programme.next_entry() == str(tmp_path / "hours" / "14h.mp3")
    assert programme.next_entry() == "fake://1"


def _avec_programme(
    folder: Path,
    *,
    clock: FrozenClock,
    listes: dict[str, list[Track]],
    programmes: list[Programme],
    bands: list[Band] | None = None,
) -> tuple[RadioProgramme, list[tuple[Kind, Track | None, str | None]]]:
    source = FakeSource(CATALOGUE, listes=listes)
    random = ScriptedRandom([0] * 200)
    vues: list[tuple[Kind, Track | None, str | None]] = []
    return (
        RadioProgramme(
            queue=Queue(source, random, Window(width=1)),
            source=source,
            grille=Schedule(bands or [], clock),
            jingles=Jingles(clock),
            clock=clock,
            random=random,
            jingle_folder=folder,
            on_kind=lambda n, p, e: vues.append((n, p, e)),
            programming=Programming(programmes, clock),
            programme_window=Window(width=1),
        ),
        vues,
    )


PROG = Programme(
    name="Le vendredi de Chloé",
    playlist="Chloé",
    days=("sunday",),
    start=time(11, 0),
    end=time(14, 0),
)
LISTE = [track("p1", "Nina Simone"), track("p2", "Chet Baker")]


def test_un_programme_ouvert_puise_dans_sa_liste(tmp_path: Path) -> None:
    clock = FrozenClock(MIDI)  # 2026-08-30 est un dimanche
    programme, vues = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    assert programme.next_entry() in {"fake://p1", "fake://p2"}
    assert vues[-1][1] is not None
    assert vues[-1][1].artist in {"Nina Simone", "Chet Baker"}


def test_hors_des_heures_du_programme_on_revient_au_tirage_libre(tmp_path: Path) -> None:
    clock = FrozenClock(MIDI)
    programme, _ = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    clock.advance(timedelta(hours=4))  # 16 h, le programme est fermé
    assert programme.next_entry() == "fake://1"


def test_le_programme_l_emporte_sur_une_plage_thematique(tmp_path: Path) -> None:
    """SPECS.md §4.13 : le programme est le plus précis. Ce choix est
    provisoire tant que §7 n°19 n'est pas tranchée."""
    bands = [Band(time(0, 0), time(23, 59), ("électro",))]
    clock = FrozenClock(MIDI)
    programme, _ = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG], bands=bands
    )
    assert programme.next_entry() in {"fake://p1", "fake://p2"}


def test_une_liste_introuvable_replie_sur_le_tirage_libre(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une liste renommée ou vidée ne fait pas taire la radio (SPECS.md §7 n°21)."""
    clock = FrozenClock(MIDI)
    programme, _ = _avec_programme(tmp_path, clock=clock, listes={}, programmes=[PROG])
    with caplog.at_level(logging.INFO):
        assert programme.next_entry() == "fake://1"
    assert "Chloé" in caplog.text


def test_une_source_illisible_pendant_un_programme_replie_aussi(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    clock = FrozenClock(MIDI)
    source = FakeSource(CATALOGUE, injoignable=True, listes={"Chloé": LISTE})
    random = ScriptedRandom([0] * 50)
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([], clock),
        jingles=Jingles(clock),
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda _n, _p, _e: None,
        programming=Programming([PROG], clock),
    )
    with caplog.at_level(logging.WARNING):
        assert programme.next_entry() is None
    assert "illisible" in caplog.text


def test_une_liste_courte_ne_bloque_pas_le_programme(tmp_path: Path) -> None:
    """La fenêtre du programme rétrécit plutôt que de se taire.

    Une fenêtre de trois sur une liste de deux titres n'autorise personne dès
    le second morceau : sans rétrécissement, le programme se tairait.
    """
    clock = FrozenClock(MIDI)
    source = FakeSource(CATALOGUE, listes={"Chloé": LISTE})
    random = ScriptedRandom([0] * 200)
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([], clock),
        jingles=Jingles(clock),
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda _n, _p, _e: None,
        programming=Programming([PROG], clock),
        programme_window=Window(width=3),
    )
    for _ in range(8):
        assert programme.next_entry() in {"fake://p1", "fake://p2"}


def test_la_fenetre_du_programme_est_distincte_de_celle_du_tirage_libre(
    tmp_path: Path,
) -> None:
    """Partager la fenêtre ferait rétrécir l'une à cause de l'autre : une
    liste de deux titres condamnerait la bibliothèque entière."""
    clock = FrozenClock(MIDI)
    programme, _ = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    for _ in range(4):
        programme.next_entry()
    clock.advance(timedelta(hours=4))  # le programme se ferme
    assert programme.next_entry() == "fake://1"


def test_un_jingle_du_passe_meme_quand_les_emissions_sont_cablees(tmp_path: Path) -> None:
    """GOAL-014-T01 — le défaut que 376 tests n'ont pas vu.

    `Jingles.due_now()` **consomme**. Demander aux émissions si l'une est due,
    puis demander les jingles, ne doit pas avaler les jingles au passage : sans
    émission due, ils passent — sinon aucun `20h.mp3` ni `encore.mp3` ne sort
    jamais dès que des émissions sont déclarées, c'est-à-dire toujours.
    """
    from webradio.adapters.state.database import SqliteState
    from webradio.app.show_scheduler import Shows
    from webradio.core.shows import ShowSchedule

    (tmp_path / "hours").mkdir(exist_ok=True)

    (tmp_path / "hours" / "13h.mp3").write_bytes(b"faux jingle")
    clock = FrozenClock(MIDI)
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    aucune_emission = Shows(
        ShowSchedule([]),
        _FeedSansEpisode(),  # type: ignore[arg-type]
        state,
        clock,
        {},
    )
    source = FakeSource(CATALOGUE)
    random = ScriptedRandom([0] * 200)
    vues: list[tuple[Kind, Track | None, str | None]] = []
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([], clock),
        jingles=Jingles(clock),
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda n, p, e: vues.append((n, p, e)),
        shows=aucune_emission,
    )
    clock.advance(timedelta(hours=1))

    assert programme.next_entry() == str(tmp_path / "hours" / "13h.mp3")
    assert vues[-1] == (Kind.JINGLE, None, None)


class _FeedSansEpisode:
    def episodes(self, url: str) -> list[object]:  # noqa: ARG002 — l'interface l'impose
        return []


# ── L'effet d'un « encore » sur le tirage (GOAL-024) ────────────────────────


def _programme_pilote(
    tmp_path: Path, *, source: FakeSource | None = None, programming: Programming | None = None
) -> tuple[RadioProgramme, Control]:
    reelle = source if source is not None else FakeSource(CATALOGUE)
    clock = FrozenClock(MIDI)
    random = ScriptedRandom([0] * 200)
    control = Control(source=reelle, random=random, jingles=Jingles(clock))
    programme = RadioProgramme(
        queue=Queue(reelle, random, Window(width=1)),
        source=reelle,
        grille=Schedule([], clock),
        jingles=Jingles(clock),
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda _n, _p, _e: None,
        programming=programming,
        control=control,
        now_playing=lambda: None,
    )
    return programme, control


def test_un_encore_force_le_prochain_morceau_chez_le_meme_artiste(tmp_path: Path) -> None:
    """SPECS.md §4.6 : « le prochain morceau est du même artiste » — au-delà
    de la pondération. C'est le trou jumeau de GOAL-017."""
    source = FakeSource(
        [
            track("1", "Bowie", genre="rock"),
            track("2", "Air", genre="électro"),
            track("3", "Bowie", genre="rock"),
        ]
    )
    programme, control = _programme_pilote(tmp_path, source=source)
    premier = programme.next_entry()
    assert premier == "fake://1"
    assert control.vote(Command.MORE).accepted

    suivant = programme.next_entry()

    assert suivant == "fake://3"  # l'autre Bowie, jamais Air


def test_un_encore_pendant_un_programme_reste_dans_la_liste(tmp_path: Path) -> None:
    """SPECS.md §7 n°20 : jamais au-dehors, même sur un encore."""
    bowie_liste = track("1", "Bowie", genre="rock")
    bowie_hors_liste = track("2", "Bowie", genre="rock")
    air_liste = track("3", "Air", genre="électro")
    source = FakeSource(
        [bowie_liste, bowie_hors_liste, air_liste],
        listes={"Soirée": [bowie_liste, air_liste]},
    )
    programming = Programming(
        [
            Programme(
                name="Soirée",
                playlist="Soirée",
                days=("sunday",),
                start=time(11),
                end=time(14),
            )
        ],
        FrozenClock(MIDI),
    )
    programme, control = _programme_pilote(tmp_path, source=source, programming=programming)
    premier = programme.next_entry()
    assert premier == "fake://1"  # Bowie, dans la liste
    assert control.vote(Command.MORE).accepted

    suivant = programme.next_entry()

    # Le seul autre Bowie (2) est HORS liste : on retombe dans la liste (3),
    # on ne sort jamais.
    assert suivant == "fake://3"


# ── Les génériques d'ouverture et de fermeture (GOAL-029) ───────────────────


def _matinale(tmp_path: Path) -> tuple[RadioProgramme, FrozenClock]:
    matin = Band(
        start=time(8),
        end=time(10),
        genres=("électro",),
        intro="matinale-debut.mp3",
        outro="matinale-fin.mp3",
    )
    clock = FrozenClock(datetime(2026, 8, 30, 7, 58, tzinfo=UTC))
    random = ScriptedRandom([0] * 50)
    source = FakeSource(CATALOGUE)
    programme = RadioProgramme(
        queue=Queue(source, random, Window(width=1)),
        source=source,
        grille=Schedule([matin], clock),
        jingles=Jingles(clock),
        clock=clock,
        random=random,
        jingle_folder=tmp_path,
        on_kind=lambda _n, _p, _e: None,
    )
    return programme, clock


def test_le_generique_d_ouverture_passe_a_l_entree_du_moment(tmp_path: Path) -> None:
    (tmp_path / "matinale-debut.mp3").write_bytes(b"generique")
    programme, clock = _matinale(tmp_path)
    assert programme.next_entry() == "fake://1"  # 07:58 : tirage libre
    clock.advance(timedelta(minutes=3))  # 08:01 : la matinale est ouverte

    assert programme.next_entry() == str(tmp_path / "matinale-debut.mp3")
    assert programme.next_entry() == "fake://1"  # puis la musique du moment


def test_le_generique_de_fin_passe_a_la_sortie_et_avant_le_jingle_horaire(
    tmp_path: Path,
) -> None:
    (tmp_path / "matinale-fin.mp3").write_bytes(b"generique")
    (tmp_path / "hours").mkdir(exist_ok=True)
    (tmp_path / "hours" / "10h.mp3").write_bytes(b"jingle horaire")
    programme, clock = _matinale(tmp_path)
    clock.advance(timedelta(minutes=3))  # 08:01, dans la matinale
    programme.next_entry()
    clock.advance(timedelta(hours=2))  # 10:01 : la matinale est finie

    assert programme.next_entry() == str(tmp_path / "matinale-fin.mp3")
    assert programme.next_entry() == str(tmp_path / "hours" / "10h.mp3")
    # fake://1 a joué à 08:01 : la fenêtre de non-répétition l'écarte encore.
    assert programme.next_entry() == "fake://2"


def test_un_generique_absent_ne_signale_rien(tmp_path: Path) -> None:
    """Optionnel veut dire optionnel : ni fichier, ni erreur, ni silence."""
    programme, clock = _matinale(tmp_path)
    programme.next_entry()
    clock.advance(timedelta(minutes=3))
    assert programme.next_entry() == "fake://1"  # aucun fichier : la musique


def test_demarrer_au_milieu_d_un_moment_ne_rejoue_pas_son_generique(
    tmp_path: Path,
) -> None:
    (tmp_path / "matinale-debut.mp3").write_bytes(b"generique")
    programme, clock = _matinale(tmp_path)
    clock.advance(timedelta(minutes=32))  # première jonction à 08:30
    assert programme.next_entry() == "fake://1"
