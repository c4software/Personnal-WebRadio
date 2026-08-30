"""Un ffmpeg par entrée, qui ramène n'importe quelle source au PCM du flux.

Pourquoi un processus par entrée plutôt qu'un démultiplexeur `concat` :
`docs/ffmpeg.md` §2.1. La file est **tirée** (ARCHITECTURE.md §2) — elle n'est
donc pas connue d'avance — et un décodeur choisi au dernier moment absorbe
l'hétérogénéité de la bibliothèque sans blanc à la jonction, y compris quand la
fréquence et le nombre de canaux changent.
"""

import logging
import subprocess
import threading
from dataclasses import dataclass
from typing import IO

logger = logging.getLogger(__name__)


class DecodageImpossible(Exception):
    """ffmpeg n'a pas pu être lancé pour cette entrée.

    Distincte d'un décodage qui échoue en cours : ici rien n'a démarré, et la
    cause est presque toujours la même — ffmpeg absent du `PATH`.
    """


@dataclass(frozen=True, slots=True)
class FormatPcm:
    """Le format d'échange interne, celui auquel toute entrée est ramenée.

    Il n'est pas négociable morceau par morceau : c'est précisément parce que
    tout le monde parle la même langue que l'encodeur n'a jamais à redémarrer,
    et donc que le flux ne se coupe pas (SPECS.md §4.9).
    """

    frequence_hz: int
    canaux: int
    echantillon: str = "s16le"

    def __post_init__(self) -> None:
        if self.frequence_hz <= 0:
            message = f"fréquence non valable : {self.frequence_hz}"
            raise ValueError(message)
        if self.canaux <= 0:
            message = f"nombre de canaux non valable : {self.canaux}"
            raise ValueError(message)


def journaliser_erreurs(flux: IO[bytes], origine: str) -> None:
    """Draine en continu la sortie d'erreur d'un ffmpeg, dans un fil dédié.

    Un tuyau d'erreur plein bloque le processus qui écrit dedans. La question
    était ouverte (`docs/ffmpeg.md` §4) ; la drainer est la seule réponse qui ne
    dépende pas du volume de messages, donc du fichier qu'on est en train de
    lire. Le fil est démon : il ne doit jamais retenir l'arrêt du programme.
    """

    def boucle() -> None:
        with flux:
            for ligne in flux:
                texte = ligne.decode("utf-8", errors="replace").rstrip()
                if texte:
                    logger.warning("%s : %s", origine, texte)

    threading.Thread(target=boucle, name=f"ffmpeg-erreurs-{origine}", daemon=True).start()


class Decodeur:
    """Ouvre un ffmpeg par entrée, tous vers le même PCM.

    `commande` est un paramètre parce que le nom du programme peut différer
    d'une machine à l'autre — et parce qu'un test doit pouvoir constater ce que
    fait la chaîne quand ffmpeg est absent.
    """

    def __init__(self, format_pcm: FormatPcm, commande: str = "ffmpeg") -> None:
        self._format = format_pcm
        self._commande = commande

    def arguments(self, entree: str) -> list[str]:
        """La ligne relevée dans `docs/ffmpeg.md` §2.1, et rien de plus.

        `-nostdin` parce qu'un ffmpeg qui hérite du terminal peut consommer les
        touches du processus parent ; `-loglevel error` parce que la sortie
        d'erreur est journalisée telle quelle et qu'un rapport de progression
        n'apprendrait rien.
        """
        return [
            self._commande,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-i",
            entree,
            "-f",
            self._format.echantillon,
            "-ar",
            str(self._format.frequence_hz),
            "-ac",
            str(self._format.canaux),
            "-",
        ]

    def ouvrir(self, entree: str, groupe: int = 0) -> subprocess.Popen[bytes]:
        """Lance le décodage de `entree` dans le groupe de processus `groupe`.

        `groupe` vaut le PID du meneur de la chaîne, ou 0 pour en fonder une.
        C'est ce qui répare la première cause du défaut de `docs/flux-icy.md`
        §3.bis : arrêter la chaîne, c'est signaler **un groupe**, pas un
        processus dont on aurait pensé à garder la référence.
        """
        try:
            processus = subprocess.Popen(
                self.arguments(entree),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                process_group=groupe,
            )
        except OSError as erreur:
            message = f"impossible de décoder « {entree} » : {erreur}"
            raise DecodageImpossible(message) from erreur
        if processus.stderr is not None:
            journaliser_erreurs(processus.stderr, f"décodeur {entree}")
        return processus
