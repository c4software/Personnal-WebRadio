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
    lookahead: int = 1,
) -> tuple[RadioProgramme, list[tuple[Kind, Track | None, str | None]]]:
    reelle = source if source is not None else FakeSource(CATALOGUE)
    montre = clock if clock is not None else FrozenClock(MIDI)
    random = ScriptedRandom([0] * 200)
    vues: list[tuple[Kind, Track | None, str | None]] = []
    return (
        RadioProgramme(
            queue=Queue(reelle, random, Window(width=1), lookahead=lookahead),
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


def test_l_oubli_jette_les_jingles_en_attente(tmp_path: Path) -> None:
    """Deux heures dues à la même jonction : la première sert, la seconde
    attend — et l'oubli (SPECS.md §7 n°30) la jette avec le reste."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    (tmp_path / "hours" / "14h.mp3").write_bytes(b"jingle")
    montre = FrozenClock(MIDI)
    programme, _ = _programme(tmp_path, clock=montre)
    montre.advance(timedelta(hours=2))
    entry = programme.next_entry()
    assert entry is not None and "13h.mp3" in entry
    programme.forget_pending()
    assert programme.next_entry() == "fake://1"


def test_l_oubli_jette_l_avance_replacee_par_un_encore(tmp_path: Path) -> None:
    """Ce qu'un encore d'avant la pause avait replacé n'a plus son contexte."""
    programme, _ = _programme(tmp_path)
    programme.replay_later("fake://2", Kind.MUSIC, CATALOGUE[1], None)
    programme.forget_pending()
    assert programme.next_entry() == "fake://1"


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


def test_le_programme_dit_le_morceau_qu_il_a_prepare(tmp_path: Path) -> None:
    """GOAL-054 : « À suivre » se replie là-dessus quand la file du diffuseur
    n'a que de l'habillage."""
    clock = FrozenClock(MIDI)
    programme, _ = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    clock.advance(timedelta(hours=4))  # 16 h, hors du programme : la file parle
    assert programme.upcoming() == [], "rien n'est préparé tant qu'on n'a pas préparé"
    programme.prepare()
    (annonce,) = programme.upcoming()
    assert annonce.kind is Kind.MUSIC and annonce.track is not None
    assert programme.next_entry() == "fake://1"


def test_pendant_un_programme_rien_n_est_annonce(tmp_path: Path) -> None:
    """Sa musique vient d'une liste, pas de la file (SPECS.md §4.13) : l'avance
    préparée ne passera pas, et l'annoncer serait promettre un morceau qui ne
    vient jamais."""
    clock = FrozenClock(MIDI)  # 2026-08-30 est un dimanche, le programme est ouvert
    programme, _ = _avec_programme(
        tmp_path, clock=clock, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    programme.prepare()
    assert programme.upcoming() == []


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
    # UNE seule instance de Jingles, partagée comme dans main.py : le contrôle
    # y marque l'encore, le programme l'y lit.
    jingles = Jingles(clock)
    control = Control(source=reelle, random=random, jingles=jingles)
    programme = RadioProgramme(
        queue=Queue(reelle, random, Window(width=1)),
        source=reelle,
        grille=Schedule([], clock),
        jingles=jingles,
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


# ── Les variantes de jingles (GOAL-033) ─────────────────────────────────────


def test_les_variantes_d_un_jingle_se_tirent_au_hasard_injecte(tmp_path: Path) -> None:
    """`14h.mp3`, `14h-a.mp3`, `14h-b.mp3`… — l'une au hasard, rejouable."""
    (tmp_path / "hours").mkdir()
    for nom in ("13h.mp3", "13h-a.mp3", "13h-b.mp3"):
        (tmp_path / "hours" / nom).write_bytes(b"jingle")
    clock = FrozenClock(MIDI)
    # ScriptedRandom : le tirage de la piste (0), puis celui de la variante (2).
    programme, _ = _programme(tmp_path, clock=clock)
    clock.advance(timedelta(hours=1))

    choisi = programme.next_entry()

    assert choisi is not None
    assert Path(choisi).name in {"13h.mp3", "13h-a.mp3", "13h-b.mp3"}


def test_les_variantes_suffisent_sans_fichier_de_base(tmp_path: Path) -> None:
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h-b.mp3").write_bytes(b"jingle")
    clock = FrozenClock(MIDI)
    programme, vues = _programme(tmp_path, clock=clock)
    clock.advance(timedelta(hours=1))

    assert programme.next_entry() == str(tmp_path / "hours" / "13h-b.mp3")
    assert vues[-1] == (Kind.JINGLE, None, None)


def test_un_generique_a_aussi_ses_variantes(tmp_path: Path) -> None:
    (tmp_path / "matinale-debut-a.mp3").write_bytes(b"generique")
    (tmp_path / "matinale-debut-b.mp3").write_bytes(b"generique")
    programme, clock = _matinale(tmp_path)
    programme.next_entry()
    clock.advance(timedelta(minutes=3))

    choisi = programme.next_entry()

    assert choisi is not None
    assert Path(choisi).name.startswith("matinale-debut-")


def test_une_entree_replacee_passe_apres_le_force_et_avant_le_tirage(tmp_path: Path) -> None:
    """GOAL-034, schéma de l'auteur : Yamê → encore.mp3 → Yamê-2 → Tryo."""
    (tmp_path / "encore.mp3").write_bytes(b"annonce")
    source = FakeSource(
        [
            track("1", "Bowie", genre="rock"),
            track("2", "Air", genre="électro"),
            track("3", "Bowie", genre="rock"),
        ]
    )
    programme, control = _programme_pilote(tmp_path, source=source)
    assert programme.next_entry() == "fake://1"  # Bowie à l'antenne
    assert control.vote(Command.MORE).accepted
    # L'avance (Air) est replacée par la charnière, comme après /requeue.
    programme.replay_later("fake://2", Kind.MUSIC, source.tracks(None)[1], None)

    assert programme.next_entry() == str(tmp_path / "encore.mp3")  # l'annonce
    assert programme.next_entry() == "fake://3"  # le même artiste, forcé
    assert programme.next_entry() == "fake://2"  # l'avance replacée — rien de jeté


def test_un_programme_sert_aussi_ses_titres_longs(tmp_path: Path) -> None:
    """SPECS.md §7 n°32 révisée : une piste longue se choisit comme les autres —
    c'est la diffusion qui la coupera au plafond, pas le tirage qui l'écarte."""
    clock = FrozenClock(MIDI)
    liste = [
        track("long", "Nina Simone", secondes=2400),
        track("ok", "Chet Baker", secondes=200),
    ]
    source = FakeSource(CATALOGUE, listes={"Chloé": liste})
    random = ScriptedRandom([0] * 20)
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
    assert programme.next_entry() == "fake://long"


def test_a_la_jonction_qui_suit_un_changement_de_plage_l_avance_est_retiree(
    tmp_path: Path,
) -> None:
    """Rejoue le 2026-09-02 : à 15 h 59 le programme prend de l'avance sous
    la plage de 15 h ; à 16 h 03, la plage a changé, et c'est un morceau de
    la nouvelle plage qui doit sortir — pas l'avance rassise (décision n°33)."""
    montre = FrozenClock(MIDI.replace(hour=15, minute=59))
    plages = [
        Band(start=time(15, 0), end=time(16, 0), genres=("trip-hop",)),
        Band(start=time(16, 0), end=time(17, 0), genres=("rock",)),
    ]
    programme, vues = _programme(tmp_path, bands=plages, clock=montre)
    assert programme.next_entry() == "fake://3"
    programme.prepare()
    montre.advance(timedelta(minutes=4))
    assert programme.next_entry() == "fake://2"
    assert vues[-1][1] is not None and vues[-1][1].genre == "rock"


DEUX_PLAGES = [
    Band(start=time(12, 0), end=time(13, 0), genres=("trip-hop",)),
    Band(start=time(13, 0), end=time(14, 0), genres=("rock",), intro="bands/rock.mp3"),
]


def test_chaque_creneau_d_avance_se_tire_sous_le_moment_ou_il_commencera(
    tmp_path: Path,
) -> None:
    """GOAL-058, idée de l'auteur : planifier d'avance, c'est tirer chaque
    titre sous la plage qu'il trouvera en commençant — durée après durée."""
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=3)
    programme.prepare(from_instant=montre.now() + timedelta(minutes=3))  # 12 h 58
    genres = [item.track.genre for item in programme.upcoming() if item.track is not None]
    assert genres == ["trip-hop", "rock", "rock"]  # 12 h 58, 13 h 01, 13 h 04


def test_sans_estimation_l_avance_se_tire_sous_le_moment_present(tmp_path: Path) -> None:
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=2)
    programme.prepare()
    assert [i.track.genre for i in programme.upcoming() if i.track] == ["trip-hop", "trip-hop"]


def test_la_liste_annonce_l_heure_estimee_et_l_habillage_prevu(tmp_path: Path) -> None:
    """Le jingle de 13 h et le générique de la plage de 13 h figurent dans la
    liste, à la jonction qui les rendra — prévus, pas encore décidés."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    (tmp_path / "bands").mkdir()
    (tmp_path / "bands" / "rock.mp3").write_bytes(b"generique")
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=3)
    depart = MIDI.replace(minute=58)
    programme.prepare(from_instant=depart)
    liste = programme.upcoming(depart)
    assert [(i.kind, i.label, i.expected) for i in liste] == [
        (Kind.MUSIC, None, False),
        (Kind.JINGLE, "13 h", True),
        (Kind.JINGLE, "rock", True),
        (Kind.MUSIC, None, False),
        (Kind.MUSIC, None, False),
    ]
    assert [i.at for i in liste] == [
        depart,
        depart + timedelta(minutes=3),
        depart + timedelta(minutes=3),
        depart + timedelta(minutes=3),
        depart + timedelta(minutes=6),
    ]


def test_un_jingle_absent_n_est_pas_prevu(tmp_path: Path) -> None:
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=2)
    depart = MIDI.replace(minute=58)
    programme.prepare(from_instant=depart)
    assert all(i.kind is Kind.MUSIC for i in programme.upcoming(depart))


def test_un_creneau_qui_a_glisse_fait_retirer_la_suite(tmp_path: Path) -> None:
    """Tiré pour 12 h 58, 13 h 01, 13 h 04 ; un saut avance tout : le premier
    créneau tombe à 13 h 10, sous la plage de 13 h — tout est retiré."""
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=3)
    programme.prepare(from_instant=MIDI.replace(minute=58))
    montre.advance(timedelta(minutes=15))
    programme.prepare(from_instant=MIDI.replace(hour=13, minute=10))
    assert [i.track.genre for i in programme.upcoming() if i.track] == ["rock", "rock", "rock"]


def test_la_liste_ne_montre_pas_une_avance_rassise(tmp_path: Path) -> None:
    """Entre la jonction et la préparation suivante, la liste lit l'avance
    telle quelle : elle s'arrête à la première entrée dont le moment a fini."""
    montre = FrozenClock(MIDI.replace(minute=55))
    programme, _ = _programme(tmp_path, bands=DEUX_PLAGES, clock=montre, lookahead=2)
    programme.prepare()
    montre.advance(timedelta(minutes=10))  # 13 h 05 : la plage de 12 h a fini
    assert programme.upcoming() == []


def test_retirer_un_titre_de_l_avance_du_programme(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    programme, _ = _programme(tmp_path, lookahead=2)
    programme.prepare()
    premier = programme.upcoming()[0].track
    assert premier is not None
    with caplog.at_level(logging.INFO):
        assert programme.withdraw(premier.identifier)
    assert "retiré avant diffusion" in caplog.text
    assert premier not in [i.track for i in programme.upcoming()]
    assert not programme.withdraw(premier.identifier)


def test_ce_qui_attend_deja_passe_avant_l_avance_dans_la_liste(tmp_path: Path) -> None:
    """Un jingle dû et une entrée replacée par un encore passent avant la
    file : la liste les montre dans cet ordre, sans rien décider."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    (tmp_path / "hours" / "14h.mp3").write_bytes(b"jingle")
    montre = FrozenClock(MIDI)
    programme, _ = _programme(tmp_path, clock=montre, lookahead=1)
    montre.advance(timedelta(hours=2))
    assert "13h" in str(programme.next_entry())  # 14h reste en attente
    programme.replay_later("fake://9", Kind.MUSIC, track("9", "Yamê"), None)
    programme.prepare()
    liste = programme.upcoming()
    assert [(i.kind, i.label) for i in liste][:2] == [(Kind.JINGLE, "14h"), (Kind.MUSIC, None)]
    assert liste[1].track is not None and liste[1].track.artist == "Yamê"
    assert liste[2].kind is Kind.MUSIC


def test_rompre_la_suite_et_jeter_l_avance_de_la_file(tmp_path: Path) -> None:
    """GOAL-059 : l'avance part, l'habillage dû reste."""
    (tmp_path / "hours").mkdir()
    (tmp_path / "hours" / "13h.mp3").write_bytes(b"jingle")
    (tmp_path / "hours" / "14h.mp3").write_bytes(b"jingle")
    montre = FrozenClock(MIDI)
    programme, _ = _programme(tmp_path, clock=montre, lookahead=2)
    assert not programme.break_run(), "sans suites, rien à rompre"
    montre.advance(timedelta(hours=2))
    programme.next_entry()  # 13h ; 14h reste dû
    programme.prepare()
    programme.forget_advance()
    liste = programme.upcoming()
    assert [(i.kind, i.label) for i in liste] == [(Kind.JINGLE, "14h")]
