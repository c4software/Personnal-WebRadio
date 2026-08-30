"""La chaîne de diffusion, éprouvée contre le vrai ffmpeg.

Ces tests lancent des processus. C'est délibéré : ce que `GOAL-004` doit
garantir — pas de blanc à la jonction, aucun orphelin à l'arrêt — ne se constate
pas contre un double. Le défaut de `docs/flux-icy.md` §3.bis avait justement
échappé à un test qui regardait un booléen.

Les fichiers d'essai sont fabriqués par ffmpeg lui-même (`sine=…`) : aucun
fichier audio n'entre dans le dépôt.
"""

import os
import signal
import subprocess
import threading
from pathlib import Path

import pytest

from webradio.adapters.ffmpeg.decoder import DecodeFailed, Decoder, PcmFormat
from webradio.adapters.ffmpeg.encoder import (
    Chain,
    ChainUnavailable,
    Encoder,
    StreamFormat,
    _sans_secret,
)

FORMAT = StreamFormat(container="mp3", bitrate_kbps=128, sample_rate_hz=44100, channels=2)
INTROUVABLE = "ffmpeg-qui-n-existe-pas"
DELAI = 30.0


def fabriquer(folder: Path, name: str, secondes: float, sample_rate_hz: int, channels: int) -> str:
    """Un fichier d'essai, produit par ffmpeg pour qu'il soit réellement décodable."""
    path = folder / name
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:duration={secondes}:sample_rate={sample_rate_hz}",
            "-ac",
            str(channels),
            str(path),
        ],
        check=True,
    )
    return str(path)


def group_processes(group: int) -> list[str]:
    """Les processus vivants — zombies compris — rattachés à un groupe.

    C'est la seule mesure qui vaille pour l'arrêt : un booléen serait passé au
    vert alors que deux ffmpeg survivaient (`docs/flux-icy.md` §3.bis), et un
    `<defunct>` compte comme un survivant.
    """
    releve = subprocess.run(
        ["ps", "-e", "-o", "pgid=,pid=,stat=,comm="],
        capture_output=True,
        text=True,
        check=True,
    )
    rows = []
    for row in releve.stdout.splitlines():
        champs = row.split(maxsplit=1)
        if len(champs) == 2 and champs[0] == str(group):
            rows.append(row.strip())
    return rows


def decrire(octets: bytes, folder: Path) -> dict[str, str]:
    """Ce que ffprobe dit d'un flux capté : codec, fréquence, canaux."""
    capture = folder / "capture.mp3"
    capture.write_bytes(octets)
    releve = subprocess.run(
        [
            "ffprobe",
            "-hide_banner",
            "-loglevel",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,sample_rate,channels",
            "-of",
            "default=noprint_wrappers=1",
            str(capture),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return dict(row.split("=", 1) for row in releve.stdout.splitlines() if "=" in row)


class FakeProgramme:
    """Une suite d'entrées écrite d'avance, qui note l'ordre des appels.

    L'ordre est ce qui compte : `preparer` doit tomber pendant qu'un morceau
    joue, jamais à la jonction (`docs/ffmpeg.md` §2.2).
    """

    def __init__(self, entrees: list[str], *, boucler: bool = False) -> None:
        self._entrees = list(entrees)
        self._boucler = boucler
        self._rang = 0
        self.journal: list[str] = []

    def next_entry(self) -> str | None:
        self.journal.append("suivante")
        if not self._entrees:
            return None
        if self._rang >= len(self._entrees):
            if not self._boucler:
                return None
            self._rang = 0
        entry = self._entrees[self._rang]
        self._rang += 1
        return entry

    def prepare(self) -> None:
        self.journal.append("preparer")


class Collector:
    """Recueille le flux publié et prévient dès qu'il y en a assez."""

    def __init__(self, seuil: int) -> None:
        self._seuil = seuil
        self._verrou = threading.Lock()
        self.octets = bytearray()
        self.assez = threading.Event()
        self.repris = threading.Event()
        self.end = threading.Event()
        self.reason = ""

    def publish(self, block: bytes) -> None:
        with self._verrou:
            self.octets.extend(block)
            if len(self.octets) >= self._seuil:
                self.assez.set()
        self.repris.set()

    def on_end(self, reason: str) -> None:
        self.reason = reason
        self.end.set()


@pytest.fixture
def musique(tmp_path: Path) -> str:
    return fabriquer(tmp_path, "musique.mp3", 10, 44100, 2)


def test_le_decodeur_ramene_chaque_entree_au_meme_pcm(tmp_path: Path) -> None:
    """Deux entrées de formats différents rendent exactement la même quantité de PCM."""
    stereo = fabriquer(tmp_path, "stereo.mp3", 1, 44100, 2)
    mono = fabriquer(tmp_path, "mono.mp3", 1, 22050, 1)
    decoder = Decoder(FORMAT.pcm)

    tailles = []
    for entry in (stereo, mono):
        processes = decoder.ouvrir(entry)
        assert processes.stdout is not None
        tailles.append(len(processes.stdout.read()))
        processes.wait(DELAI)

    attendu = 44100 * 2 * 2
    for taille in tailles:
        assert abs(taille - attendu) < attendu // 10
    assert abs(tailles[0] - tailles[1]) < attendu // 10


def test_une_entree_illisible_fait_echouer_le_decodeur(tmp_path: Path) -> None:
    faux = tmp_path / "pas-du-son.mp3"
    faux.write_text("ceci n'est pas de la musique")

    processes = Decoder(FORMAT.pcm).ouvrir(str(faux))
    assert processes.stdout is not None
    assert processes.stdout.read() == b""
    assert processes.wait(DELAI) != 0


def test_le_decodeur_dit_pourquoi_il_ne_demarre_pas() -> None:
    with pytest.raises(DecodeFailed):
        Decoder(FORMAT.pcm, command=INTROUVABLE).ouvrir("peu importe")


def test_un_pcm_sans_canal_est_refuse() -> None:
    with pytest.raises(ValueError, match="canaux"):
        PcmFormat(sample_rate_hz=44100, channels=0)


def test_l_encodeur_cadence_le_flux_et_tient_son_format_du_parametre() -> None:
    """Le débit et la fréquence viennent du format, et `-re` est là."""
    arguments = Encoder(
        StreamFormat(container="mp3", bitrate_kbps=192, sample_rate_hz=48000, channels=1)
    ).arguments()

    assert "-re" in arguments
    assert "192k" in arguments
    assert "48000" in arguments
    assert arguments[arguments.index("-f", arguments.index("-i")) + 1] == "mp3"


def test_un_debit_non_valable_est_refuse() -> None:
    with pytest.raises(ValueError, match="débit"):
        StreamFormat(container="mp3", bitrate_kbps=0, sample_rate_hz=44100, channels=2)


def test_un_conteneur_inconnu_est_refuse_avant_toute_diffusion() -> None:
    with pytest.raises(ChainUnavailable, match="format de flux inconnu"):
        StreamFormat(container="ogg", bitrate_kbps=128, sample_rate_hz=44100, channels=2)


def test_la_chaine_produit_un_flux_lisible_au_format_annonce(tmp_path: Path, musique: str) -> None:
    collecteur = Collector(seuil=32 * 1024)
    chaine = Chain(FakeProgramme([musique]), FORMAT, collecteur.publish, collecteur.on_end)
    chaine.start()
    try:
        assert collecteur.assez.wait(DELAI), "aucun octet servi"
    finally:
        chaine.stop_all()

    releve = decrire(bytes(collecteur.octets), tmp_path)
    assert releve["codec_name"] == "mp3"
    assert releve["sample_rate"] == "44100"
    assert releve["channels"] == "2"


def test_l_arret_ne_laisse_aucun_processus_derriere_lui(musique: str) -> None:
    """Le test qui manquait à la maquette : il compte les processus, pas un booléen."""
    collecteur = Collector(seuil=8 * 1024)
    chaine = Chain(
        FakeProgramme([musique], boucler=True), FORMAT, collecteur.publish, collecteur.on_end
    )
    chaine.start()
    group = chaine.group
    assert collecteur.assez.wait(DELAI)
    assert group_processes(group), "la mesure elle-même doit voir les processus vivants"

    chaine.stop_all()

    assert group_processes(group) == []
    assert chaine.group == 0


def test_l_arret_est_idempotent(musique: str) -> None:
    collecteur = Collector(seuil=1)
    chaine = Chain(FakeProgramme([musique]), FORMAT, collecteur.publish, collecteur.on_end)
    chaine.start()
    group = chaine.group
    chaine.stop_all()
    chaine.stop_all()
    assert group_processes(group) == []


def test_la_chaine_prend_de_l_avance_pendant_que_le_courant_joue(musique: str) -> None:
    """`preparer` tombe dès le morceau lancé, pas à la jonction suivante."""
    collecteur = Collector(seuil=8 * 1024)
    programme = FakeProgramme([musique], boucler=True)
    chaine = Chain(programme, FORMAT, collecteur.publish, collecteur.on_end)
    chaine.start()
    try:
        assert collecteur.assez.wait(DELAI)
    finally:
        chaine.stop_all()

    assert programme.journal[:2] == ["suivante", "preparer"]


def test_un_programme_sans_rien_a_jouer_refuse_de_demarrer() -> None:
    collecteur = Collector(seuil=1)
    chaine = Chain(FakeProgramme([]), FORMAT, collecteur.publish, collecteur.on_end)
    with pytest.raises(ChainUnavailable, match="rien à jouer"):
        chaine.start()
    assert chaine.group == 0


def test_un_ffmpeg_absent_refuse_de_demarrer(musique: str) -> None:
    collecteur = Collector(seuil=1)
    chaine = Chain(
        FakeProgramme([musique]),
        FORMAT,
        collecteur.publish,
        collecteur.on_end,
        command=INTROUVABLE,
    )
    with pytest.raises(ChainUnavailable, match="n'a pas pu démarrer"):
        chaine.start()


def test_la_radio_coupe_en_le_disant_quand_le_programme_s_epuise(tmp_path: Path) -> None:
    court = fabriquer(tmp_path, "court.mp3", 0.5, 44100, 2)
    collecteur = Collector(seuil=1)
    chaine = Chain(FakeProgramme([court]), FORMAT, collecteur.publish, collecteur.on_end)
    chaine.start()
    group = chaine.group
    try:
        assert collecteur.end.wait(DELAI), "la chaîne n'a pas annoncé sa fin"
    finally:
        chaine.stop_all()

    assert "plus rien à jouer" in collecteur.reason
    assert group_processes(group) == []


def test_une_entree_illisible_ne_fait_pas_taire_la_radio(tmp_path: Path) -> None:
    """Un morceau corrompu est sauté, et le flux continue (SPECS.md §5)."""
    casse = tmp_path / "casse.mp3"
    casse.write_text("pas du son")
    bon = fabriquer(tmp_path, "bon.mp3", 5, 44100, 2)

    collecteur = Collector(seuil=16 * 1024)
    chaine = Chain(FakeProgramme([str(casse), bon]), FORMAT, collecteur.publish, collecteur.on_end)
    chaine.start()
    try:
        assert collecteur.assez.wait(DELAI), "la radio s'est tue sur un morceau illisible"
    finally:
        chaine.stop_all()


def test_la_chaine_se_releve_une_fois_puis_coupe_en_le_disant(musique: str) -> None:
    """ffmpeg meurt : relance unique, puis coupure — jamais de boucle (SPECS.md §5.1)."""
    collecteur = Collector(seuil=4 * 1024)
    chaine = Chain(
        FakeProgramme([musique], boucler=True), FORMAT, collecteur.publish, collecteur.on_end
    )
    chaine.start()
    groupe_initial = chaine.group
    try:
        assert collecteur.assez.wait(DELAI)

        os.killpg(groupe_initial, signal.SIGKILL)
        # Les octets déjà en tampon continuent d'arriver après la mort : c'est le
        # changement de groupe, non la reprise du flux, qui atteste la relance.
        nouveau = groupe_initial
        for _ in range(50):
            collecteur.repris.clear()
            assert collecteur.repris.wait(DELAI), "la chaîne ne s'est pas relevée"
            nouveau = chaine.group
            if nouveau not in (0, groupe_initial):
                break
        assert nouveau not in (0, groupe_initial)

        os.killpg(chaine.group, signal.SIGKILL)
        assert collecteur.end.wait(DELAI), "la chaîne n'a pas coupé après la seconde mort"
        assert "ne se relève pas" in collecteur.reason
    finally:
        chaine.stop_all()

    assert group_processes(groupe_initial) == []


def test_une_url_journalisee_perd_son_jeton() -> None:
    """Défaut trouvé en exécutant la radio, jamais par un test.

    Le journal portait `…stream.view?u=<utilisateur>&t=<jeton>&s=<sel>…` — soit
    les identifiants Navidrome répandus dans tous les fichiers de journal de la
    machine, ce qu'AGENTS.md §2 interdit. Une URL ne ressemble pas à un secret,
    et rien ne signalait qu'elle en portait un.
    """
    url = (
        "http://music/rest/stream.view"
        "?u=auditeur&t=7b53b54309774c29f2c1874cf74bd53c&s=95fdc898&id=AWFr5"
    )
    reduite = _sans_secret(url)
    assert "auditeur" not in reduite
    assert "7b53b54309774c29f2c1874cf74bd53c" not in reduite
    assert "95fdc898" not in reduite
    assert reduite == "http://music/rest/stream.view"


def test_un_chemin_de_fichier_est_journalise_tel_quel() -> None:
    """Un jingle local n'a rien à cacher, et le masquer rendrait le journal
    inutile pour diagnostiquer un fichier manquant."""
    assert _sans_secret("/var/lib/jingles/14h.mp3") == "/var/lib/jingles/14h.mp3"


def test_le_journal_de_la_chaine_ne_porte_aucun_jeton(caplog: pytest.LogCaptureFixture) -> None:
    """Le contrôle au bon endroit : ce qui sort réellement du logger."""
    import logging

    from webradio.adapters.ffmpeg import encoder as encoder

    with caplog.at_level(logging.INFO, logger=encoder.__name__):
        encoder.logger.info(
            "à l'antenne : %s",
            encoder._sans_secret("http://music/rest/stream.view?u=moi&t=secret123&s=sel"),
        )
    assert "secret123" not in caplog.text
    assert "u=moi" not in caplog.text
