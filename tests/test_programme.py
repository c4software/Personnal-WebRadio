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
