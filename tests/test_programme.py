"""La charnière : ce qu'elle traduit, ce qu'elle journalise, ce qu'elle refuse."""

import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from tests.fakes import FakeSource, piste
from webradio.app.programme import ProgrammeRadio
from webradio.core.clock import HorlogeFigee
from webradio.core.controle import Nature
from webradio.core.file import File
from webradio.core.grille import Grille, Plage
from webradio.core.jingles import Jingles
from webradio.core.modeles import Piste
from webradio.core.programmes import Programmation, Programme
from webradio.core.repetition import Fenetre
from webradio.core.rng import HasardScripte

CATALOGUE = [
    piste("1", "Air", genre="électro"),
    piste("2", "Bowie", genre="rock"),
    piste("3", "Portishead", genre="trip-hop"),
]
MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _programme(
    dossier: Path,
    *,
    source: FakeSource | None = None,
    plages: list[Plage] | None = None,
    horloge: HorlogeFigee | None = None,
) -> tuple[ProgrammeRadio, list[tuple[Nature, Piste | None]]]:
    reelle = source if source is not None else FakeSource(CATALOGUE)
    montre = horloge if horloge is not None else HorlogeFigee(MIDI)
    hasard = HasardScripte([0] * 200)
    vues: list[tuple[Nature, Piste | None]] = []
    return (
        ProgrammeRadio(
            file=File(reelle, hasard, Fenetre(largeur=1)),
            source=reelle,
            grille=Grille(plages or [], montre),
            jingles=Jingles(montre),
            horloge=montre,
            hasard=hasard,
            dossier_jingles=dossier,
            sur_nature=lambda n, p: vues.append((n, p)),
        ),
        vues,
    )


def test_la_suivante_est_une_entree_que_ffmpeg_peut_ouvrir(tmp_path: Path) -> None:
    programme, _ = _programme(tmp_path)
    assert programme.suivante() == "fake://1"


def test_la_nature_est_declaree_a_chaque_morceau(tmp_path: Path) -> None:
    """C'est ce qui permet à l'API de dire ce qui passe, et au noyau de refuser
    un vote au bon moment."""
    programme, vues = _programme(tmp_path)
    programme.suivante()
    assert vues[-1][0] is Nature.MUSIQUE
    assert vues[-1][1] is not None
    assert vues[-1][1].artiste == "Air"


def test_un_jingle_du_et_present_passe_avant_la_musique(tmp_path: Path) -> None:
    (tmp_path / "13h.mp3").write_bytes(b"faux jingle")
    horloge = HorlogeFigee(MIDI)
    programme, vues = _programme(tmp_path, horloge=horloge)
    horloge.avancer(timedelta(hours=1))
    assert programme.suivante() == str(tmp_path / "13h.mp3")
    assert vues[-1] == (Nature.JINGLE, None)


def test_un_jingle_du_mais_absent_ne_signale_rien(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """C'est le mode d'emploi normal, pas une dégradation (SPECS.md §4.3) : le
    dossier peut ne contenir que trois fichiers."""
    horloge = HorlogeFigee(MIDI)
    programme, vues = _programme(tmp_path, horloge=horloge)
    horloge.avancer(timedelta(hours=1))
    with caplog.at_level(logging.WARNING):
        assert programme.suivante() == "fake://1"
    assert caplog.text == ""
    assert vues[-1][0] is Nature.MUSIQUE


def test_le_repli_d_une_plage_sans_musique_est_journalise(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    plages = [Plage(MIDI.time(), time(23, 0), ("jazz",))]
    programme, _ = _programme(tmp_path, plages=plages)
    with caplog.at_level(logging.INFO):
        assert programme.suivante() is not None
    assert "jazz" in caplog.text


def test_une_source_injoignable_fait_couper_en_le_disant(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """La radio ne se tait pas : elle coupe, et elle dit pourquoi
    (SPECS.md §5.1). Jamais un silence, jamais une boucle."""
    programme, _ = _programme(tmp_path, source=FakeSource(CATALOGUE, injoignable=True))
    with caplog.at_level(logging.WARNING):
        assert programme.suivante() is None
    assert "injoignable" in caplog.text


def test_une_bibliotheque_vide_fait_couper_en_le_disant(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    programme, _ = _programme(tmp_path, source=FakeSource([]))
    with caplog.at_level(logging.WARNING):
        assert programme.suivante() is None
    assert "plus rien" in caplog.text


def test_preparer_prend_de_l_avance(tmp_path: Path) -> None:
    """La contrainte de docs/ffmpeg.md §2.2 : résoudre pendant que le courant
    joue, pas à la jonction."""
    source = FakeSource(CATALOGUE)
    programme, _ = _programme(tmp_path, source=source)
    programme.preparer()
    appels = source.appels
    assert appels > 0
    programme.suivante()
    assert source.appels == appels, "suivante() a réinterrogé la source"


def test_preparer_avale_une_panne_plutot_que_de_la_propager(tmp_path: Path) -> None:
    """Se préparer est une commodité : échouer à prendre de l'avance ne doit
    jamais tuer le fil qui alimente la chaîne."""
    programme, _ = _programme(tmp_path, source=FakeSource(CATALOGUE, injoignable=True))
    programme.preparer()


def test_plusieurs_jingles_dus_passent_a_la_suite(tmp_path: Path) -> None:
    """Un morceau long a enjambé deux heures : tous passent, le plus ancien
    d'abord (SPECS.md §4.3)."""
    (tmp_path / "13h.mp3").write_bytes(b"a")
    (tmp_path / "14h.mp3").write_bytes(b"b")
    horloge = HorlogeFigee(MIDI)
    programme, _ = _programme(tmp_path, horloge=horloge)
    horloge.avancer(timedelta(hours=2))
    assert programme.suivante() == str(tmp_path / "13h.mp3")
    assert programme.suivante() == str(tmp_path / "14h.mp3")
    assert programme.suivante() == "fake://1"


def _avec_programme(
    dossier: Path,
    *,
    horloge: HorlogeFigee,
    listes: dict[str, list[Piste]],
    programmes: list[Programme],
    plages: list[Plage] | None = None,
) -> tuple[ProgrammeRadio, list[tuple[Nature, Piste | None]]]:
    source = FakeSource(CATALOGUE, listes=listes)
    hasard = HasardScripte([0] * 200)
    vues: list[tuple[Nature, Piste | None]] = []
    return (
        ProgrammeRadio(
            file=File(source, hasard, Fenetre(largeur=1)),
            source=source,
            grille=Grille(plages or [], horloge),
            jingles=Jingles(horloge),
            horloge=horloge,
            hasard=hasard,
            dossier_jingles=dossier,
            sur_nature=lambda n, p: vues.append((n, p)),
            programmation=Programmation(programmes, horloge),
            fenetre_programme=Fenetre(largeur=1),
        ),
        vues,
    )


PROG = Programme(
    nom="Le vendredi de Chloé",
    playlist="Chloé",
    jours=("dimanche",),
    debut=time(11, 0),
    fin=time(14, 0),
)
LISTE = [piste("p1", "Nina Simone"), piste("p2", "Chet Baker")]


def test_un_programme_ouvert_puise_dans_sa_liste(tmp_path: Path) -> None:
    horloge = HorlogeFigee(MIDI)  # 2026-08-30 est un dimanche
    programme, vues = _avec_programme(
        tmp_path, horloge=horloge, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    assert programme.suivante() in {"fake://p1", "fake://p2"}
    assert vues[-1][1] is not None
    assert vues[-1][1].artiste in {"Nina Simone", "Chet Baker"}


def test_hors_des_heures_du_programme_on_revient_au_tirage_libre(tmp_path: Path) -> None:
    horloge = HorlogeFigee(MIDI)
    programme, _ = _avec_programme(
        tmp_path, horloge=horloge, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    horloge.avancer(timedelta(hours=4))  # 16 h, le programme est fermé
    assert programme.suivante() == "fake://1"


def test_le_programme_l_emporte_sur_une_plage_thematique(tmp_path: Path) -> None:
    """SPECS.md §4.13 : le programme est le plus précis. Ce choix est
    provisoire tant que §7 n°19 n'est pas tranchée."""
    plages = [Plage(time(0, 0), time(23, 59), ("électro",))]
    horloge = HorlogeFigee(MIDI)
    programme, _ = _avec_programme(
        tmp_path, horloge=horloge, listes={"Chloé": LISTE}, programmes=[PROG], plages=plages
    )
    assert programme.suivante() in {"fake://p1", "fake://p2"}


def test_une_liste_introuvable_replie_sur_le_tirage_libre(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une liste renommée ou vidée ne fait pas taire la radio (SPECS.md §7 n°21)."""
    horloge = HorlogeFigee(MIDI)
    programme, _ = _avec_programme(tmp_path, horloge=horloge, listes={}, programmes=[PROG])
    with caplog.at_level(logging.INFO):
        assert programme.suivante() == "fake://1"
    assert "Chloé" in caplog.text


def test_une_source_illisible_pendant_un_programme_replie_aussi(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    horloge = HorlogeFigee(MIDI)
    source = FakeSource(CATALOGUE, injoignable=True, listes={"Chloé": LISTE})
    hasard = HasardScripte([0] * 50)
    programme = ProgrammeRadio(
        file=File(source, hasard, Fenetre(largeur=1)),
        source=source,
        grille=Grille([], horloge),
        jingles=Jingles(horloge),
        horloge=horloge,
        hasard=hasard,
        dossier_jingles=tmp_path,
        sur_nature=lambda _n, _p: None,
        programmation=Programmation([PROG], horloge),
    )
    with caplog.at_level(logging.WARNING):
        assert programme.suivante() is None
    assert "illisible" in caplog.text


def test_une_liste_courte_ne_bloque_pas_le_programme(tmp_path: Path) -> None:
    """La fenêtre du programme rétrécit plutôt que de se taire.

    Une fenêtre de trois sur une liste de deux titres n'autorise personne dès
    le second morceau : sans rétrécissement, le programme se tairait.
    """
    horloge = HorlogeFigee(MIDI)
    source = FakeSource(CATALOGUE, listes={"Chloé": LISTE})
    hasard = HasardScripte([0] * 200)
    programme = ProgrammeRadio(
        file=File(source, hasard, Fenetre(largeur=1)),
        source=source,
        grille=Grille([], horloge),
        jingles=Jingles(horloge),
        horloge=horloge,
        hasard=hasard,
        dossier_jingles=tmp_path,
        sur_nature=lambda _n, _p: None,
        programmation=Programmation([PROG], horloge),
        fenetre_programme=Fenetre(largeur=3),
    )
    for _ in range(8):
        assert programme.suivante() in {"fake://p1", "fake://p2"}


def test_la_fenetre_du_programme_est_distincte_de_celle_du_tirage_libre(
    tmp_path: Path,
) -> None:
    """Partager la fenêtre ferait rétrécir l'une à cause de l'autre : une
    liste de deux titres condamnerait la bibliothèque entière."""
    horloge = HorlogeFigee(MIDI)
    programme, _ = _avec_programme(
        tmp_path, horloge=horloge, listes={"Chloé": LISTE}, programmes=[PROG]
    )
    for _ in range(4):
        programme.suivante()
    horloge.avancer(timedelta(hours=4))  # le programme se ferme
    assert programme.suivante() == "fake://1"
