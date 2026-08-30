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

from webradio.adapters.ffmpeg.decodeur import DecodageImpossible, Decodeur, FormatPcm
from webradio.adapters.ffmpeg.encodeur import Chaine, ChaineIndisponible, Encodeur, FormatFlux

FORMAT = FormatFlux(conteneur="mp3", debit_kbps=128, frequence_hz=44100, canaux=2)
INTROUVABLE = "ffmpeg-qui-n-existe-pas"
DELAI = 30.0


def fabriquer(dossier: Path, nom: str, secondes: float, frequence_hz: int, canaux: int) -> str:
    """Un fichier d'essai, produit par ffmpeg pour qu'il soit réellement décodable."""
    chemin = dossier / nom
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
            f"sine=frequency=440:duration={secondes}:sample_rate={frequence_hz}",
            "-ac",
            str(canaux),
            str(chemin),
        ],
        check=True,
    )
    return str(chemin)


def processus_du_groupe(groupe: int) -> list[str]:
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
    lignes = []
    for ligne in releve.stdout.splitlines():
        champs = ligne.split(maxsplit=1)
        if len(champs) == 2 and champs[0] == str(groupe):
            lignes.append(ligne.strip())
    return lignes


def decrire(octets: bytes, dossier: Path) -> dict[str, str]:
    """Ce que ffprobe dit d'un flux capté : codec, fréquence, canaux."""
    capture = dossier / "capture.mp3"
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
    return dict(ligne.split("=", 1) for ligne in releve.stdout.splitlines() if "=" in ligne)


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

    def suivante(self) -> str | None:
        self.journal.append("suivante")
        if not self._entrees:
            return None
        if self._rang >= len(self._entrees):
            if not self._boucler:
                return None
            self._rang = 0
        entree = self._entrees[self._rang]
        self._rang += 1
        return entree

    def preparer(self) -> None:
        self.journal.append("preparer")


class Collecteur:
    """Recueille le flux publié et prévient dès qu'il y en a assez."""

    def __init__(self, seuil: int) -> None:
        self._seuil = seuil
        self._verrou = threading.Lock()
        self.octets = bytearray()
        self.assez = threading.Event()
        self.repris = threading.Event()
        self.fin = threading.Event()
        self.raison = ""

    def publier(self, bloc: bytes) -> None:
        with self._verrou:
            self.octets.extend(bloc)
            if len(self.octets) >= self._seuil:
                self.assez.set()
        self.repris.set()

    def sur_fin(self, raison: str) -> None:
        self.raison = raison
        self.fin.set()


@pytest.fixture
def musique(tmp_path: Path) -> str:
    return fabriquer(tmp_path, "musique.mp3", 10, 44100, 2)


def test_le_decodeur_ramene_chaque_entree_au_meme_pcm(tmp_path: Path) -> None:
    """Deux entrées de formats différents rendent exactement la même quantité de PCM."""
    stereo = fabriquer(tmp_path, "stereo.mp3", 1, 44100, 2)
    mono = fabriquer(tmp_path, "mono.mp3", 1, 22050, 1)
    decodeur = Decodeur(FORMAT.pcm)

    tailles = []
    for entree in (stereo, mono):
        processus = decodeur.ouvrir(entree)
        assert processus.stdout is not None
        tailles.append(len(processus.stdout.read()))
        processus.wait(DELAI)

    attendu = 44100 * 2 * 2
    for taille in tailles:
        assert abs(taille - attendu) < attendu // 10
    assert abs(tailles[0] - tailles[1]) < attendu // 10


def test_une_entree_illisible_fait_echouer_le_decodeur(tmp_path: Path) -> None:
    faux = tmp_path / "pas-du-son.mp3"
    faux.write_text("ceci n'est pas de la musique")

    processus = Decodeur(FORMAT.pcm).ouvrir(str(faux))
    assert processus.stdout is not None
    assert processus.stdout.read() == b""
    assert processus.wait(DELAI) != 0


def test_le_decodeur_dit_pourquoi_il_ne_demarre_pas() -> None:
    with pytest.raises(DecodageImpossible):
        Decodeur(FORMAT.pcm, commande=INTROUVABLE).ouvrir("peu importe")


def test_un_pcm_sans_canal_est_refuse() -> None:
    with pytest.raises(ValueError, match="canaux"):
        FormatPcm(frequence_hz=44100, canaux=0)


def test_l_encodeur_cadence_le_flux_et_tient_son_format_du_parametre() -> None:
    """Le débit et la fréquence viennent du format, et `-re` est là."""
    arguments = Encodeur(
        FormatFlux(conteneur="mp3", debit_kbps=192, frequence_hz=48000, canaux=1)
    ).arguments()

    assert "-re" in arguments
    assert "192k" in arguments
    assert "48000" in arguments
    assert arguments[arguments.index("-f", arguments.index("-i")) + 1] == "mp3"


def test_un_debit_non_valable_est_refuse() -> None:
    with pytest.raises(ValueError, match="débit"):
        FormatFlux(conteneur="mp3", debit_kbps=0, frequence_hz=44100, canaux=2)


def test_un_conteneur_inconnu_est_refuse_avant_toute_diffusion() -> None:
    with pytest.raises(ChaineIndisponible, match="format de flux inconnu"):
        FormatFlux(conteneur="ogg", debit_kbps=128, frequence_hz=44100, canaux=2)


def test_la_chaine_produit_un_flux_lisible_au_format_annonce(tmp_path: Path, musique: str) -> None:
    collecteur = Collecteur(seuil=32 * 1024)
    chaine = Chaine(FakeProgramme([musique]), FORMAT, collecteur.publier, collecteur.sur_fin)
    chaine.demarrer()
    try:
        assert collecteur.assez.wait(DELAI), "aucun octet servi"
    finally:
        chaine.arreter()

    releve = decrire(bytes(collecteur.octets), tmp_path)
    assert releve["codec_name"] == "mp3"
    assert releve["sample_rate"] == "44100"
    assert releve["channels"] == "2"


def test_l_arret_ne_laisse_aucun_processus_derriere_lui(musique: str) -> None:
    """Le test qui manquait à la maquette : il compte les processus, pas un booléen."""
    collecteur = Collecteur(seuil=8 * 1024)
    chaine = Chaine(
        FakeProgramme([musique], boucler=True), FORMAT, collecteur.publier, collecteur.sur_fin
    )
    chaine.demarrer()
    groupe = chaine.groupe
    assert collecteur.assez.wait(DELAI)
    assert processus_du_groupe(groupe), "la mesure elle-même doit voir les processus vivants"

    chaine.arreter()

    assert processus_du_groupe(groupe) == []
    assert chaine.groupe == 0


def test_l_arret_est_idempotent(musique: str) -> None:
    collecteur = Collecteur(seuil=1)
    chaine = Chaine(FakeProgramme([musique]), FORMAT, collecteur.publier, collecteur.sur_fin)
    chaine.demarrer()
    groupe = chaine.groupe
    chaine.arreter()
    chaine.arreter()
    assert processus_du_groupe(groupe) == []


def test_la_chaine_prend_de_l_avance_pendant_que_le_courant_joue(musique: str) -> None:
    """`preparer` tombe dès le morceau lancé, pas à la jonction suivante."""
    collecteur = Collecteur(seuil=8 * 1024)
    programme = FakeProgramme([musique], boucler=True)
    chaine = Chaine(programme, FORMAT, collecteur.publier, collecteur.sur_fin)
    chaine.demarrer()
    try:
        assert collecteur.assez.wait(DELAI)
    finally:
        chaine.arreter()

    assert programme.journal[:2] == ["suivante", "preparer"]


def test_un_programme_sans_rien_a_jouer_refuse_de_demarrer() -> None:
    collecteur = Collecteur(seuil=1)
    chaine = Chaine(FakeProgramme([]), FORMAT, collecteur.publier, collecteur.sur_fin)
    with pytest.raises(ChaineIndisponible, match="rien à jouer"):
        chaine.demarrer()
    assert chaine.groupe == 0


def test_un_ffmpeg_absent_refuse_de_demarrer(musique: str) -> None:
    collecteur = Collecteur(seuil=1)
    chaine = Chaine(
        FakeProgramme([musique]),
        FORMAT,
        collecteur.publier,
        collecteur.sur_fin,
        commande=INTROUVABLE,
    )
    with pytest.raises(ChaineIndisponible, match="n'a pas pu démarrer"):
        chaine.demarrer()


def test_la_radio_coupe_en_le_disant_quand_le_programme_s_epuise(tmp_path: Path) -> None:
    court = fabriquer(tmp_path, "court.mp3", 0.5, 44100, 2)
    collecteur = Collecteur(seuil=1)
    chaine = Chaine(FakeProgramme([court]), FORMAT, collecteur.publier, collecteur.sur_fin)
    chaine.demarrer()
    groupe = chaine.groupe
    try:
        assert collecteur.fin.wait(DELAI), "la chaîne n'a pas annoncé sa fin"
    finally:
        chaine.arreter()

    assert "plus rien à jouer" in collecteur.raison
    assert processus_du_groupe(groupe) == []


def test_une_entree_illisible_ne_fait_pas_taire_la_radio(tmp_path: Path) -> None:
    """Un morceau corrompu est sauté, et le flux continue (SPECS.md §5)."""
    casse = tmp_path / "casse.mp3"
    casse.write_text("pas du son")
    bon = fabriquer(tmp_path, "bon.mp3", 5, 44100, 2)

    collecteur = Collecteur(seuil=16 * 1024)
    chaine = Chaine(
        FakeProgramme([str(casse), bon]), FORMAT, collecteur.publier, collecteur.sur_fin
    )
    chaine.demarrer()
    try:
        assert collecteur.assez.wait(DELAI), "la radio s'est tue sur un morceau illisible"
    finally:
        chaine.arreter()


def test_la_chaine_se_releve_une_fois_puis_coupe_en_le_disant(musique: str) -> None:
    """ffmpeg meurt : relance unique, puis coupure — jamais de boucle (SPECS.md §5.1)."""
    collecteur = Collecteur(seuil=4 * 1024)
    chaine = Chaine(
        FakeProgramme([musique], boucler=True), FORMAT, collecteur.publier, collecteur.sur_fin
    )
    chaine.demarrer()
    groupe_initial = chaine.groupe
    try:
        assert collecteur.assez.wait(DELAI)

        os.killpg(groupe_initial, signal.SIGKILL)
        # Les octets déjà en tampon continuent d'arriver après la mort : c'est le
        # changement de groupe, non la reprise du flux, qui atteste la relance.
        nouveau = groupe_initial
        for _ in range(50):
            collecteur.repris.clear()
            assert collecteur.repris.wait(DELAI), "la chaîne ne s'est pas relevée"
            nouveau = chaine.groupe
            if nouveau not in (0, groupe_initial):
                break
        assert nouveau not in (0, groupe_initial)

        os.killpg(chaine.groupe, signal.SIGKILL)
        assert collecteur.fin.wait(DELAI), "la chaîne n'a pas coupé après la seconde mort"
        assert "ne se relève pas" in collecteur.raison
    finally:
        chaine.arreter()

    assert processus_du_groupe(groupe_initial) == []
