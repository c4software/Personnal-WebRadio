"""L'encodeur unique, et la chaîne qui l'alimente.

Un seul ffmpeg encode le flux servi à tout le monde, du démarrage à la dernière
déconnexion : c'est ce qui garantit qu'aucun lecteur ne voit le format changer
en cours de route (SPECS.md §4.9), et c'est aussi pourquoi cinq auditeurs
coûtent le prix d'un (`docs/ffmpeg.md` §2.bis).

Deux fils tournent autour de lui, et la séparation n'est pas décorative : écrire
dans son entrée et lire sa sortie depuis le même fil s'interbloque dès que l'un
des deux tuyaux se remplit.
"""

import logging
import os
import signal
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Protocol
from urllib.parse import urlsplit, urlunsplit

from webradio.adapters.ffmpeg.decoder import (
    DecodeFailed,
    Decoder,
    PcmFormat,
    journaliser_erreurs,
)

logger = logging.getLogger(__name__)

# Le seul conteneur constaté avec de vrais lecteurs (docs/flux-icy.md §1). Un
# format inconnu est refusé au démarrage plutôt que servi sous un type MIME
# approximatif : un lecteur qui reçoit le mauvais type ne décroche pas, il ne
# démarre jamais.
MIME_TYPES = {"mp3": "audio/mpeg"}


class ChainUnavailable(Exception):
    """La chaîne refuse de démarrer, et elle dit pourquoi.

    C'est le régime « au démarrage » d'ARCHITECTURE.md §7 : l'erreur est fatale
    et remonte jusqu'à l'auditeur sous forme de réponse HTTP explicite, jamais
    sous forme de flux vide (SPECS.md §4.1).
    """


def _sans_secret(entry: str) -> str:
    """Une entrée réduite à ce qui se journalise sans danger.

    Une entrée est un chemin **ou une URL**, et l'URL d'une source porte des
    identifiants — jeton dérivé, nom d'utilisateur (`adapters/sources/`). Les
    journaliser telle quelle les répandrait dans tous les fichiers de journal de
    la machine, ce qu'AGENTS.md §2 interdit.

    Le défaut a été trouvé en exécutant la radio, jamais par un test : une URL
    ne ressemble pas à un secret, et rien ne signalait qu'elle en portait un.
    """
    if "://" not in entry:
        return entry
    decoupee = urlsplit(entry)
    return urlunsplit((decoupee.scheme, decoupee.hostname or "", decoupee.path, "", ""))


@dataclass(frozen=True, slots=True)
class StreamFormat:
    """Ce que reçoit l'auditeur, fixé une fois pour toutes au démarrage."""

    container: str
    bitrate_kbps: int
    sample_rate_hz: int
    channels: int

    def __post_init__(self) -> None:
        if self.container not in MIME_TYPES:
            message = f"format de flux inconnu : « {self.container} »"
            raise ChainUnavailable(message)
        if self.bitrate_kbps <= 0:
            message = f"débit non valable : {self.bitrate_kbps}"
            raise ValueError(message)

    @property
    def type_mime(self) -> str:
        return MIME_TYPES[self.container]

    @property
    def pcm(self) -> PcmFormat:
        """Le PCM auquel les entrées sont ramenées : celui du flux, sans détour."""
        return PcmFormat(sample_rate_hz=self.sample_rate_hz, channels=self.channels)


class Programme(Protocol):
    """Ce que la chaîne attend de ce qui décide : des entrées, une par une.

    Une « entrée » est un chemin ou une URL que ffmpeg sait ouvrir. La chaîne ne
    l'interprète jamais : elle ignore s'il s'agit d'un morceau, d'un jingle ou
    d'un flash — c'est le sens du chemin d'insertion unique de
    `docs/ffmpeg.md` §2.ter.
    """

    def next_entry(self) -> str | None:
        """L'entrée suivante, ou `None` quand il n'y a plus rien à jouer.

        `None` n'est pas une panne : c'est ce qui fait couper la radio en le
        disant, plutôt que de boucler sur ce qui vient de passer (SPECS.md §5.1).

        Ni cette méthode ni `preparer` ne lèvent : une source injoignable est
        une panne que le programme contourne lui-même, en réessayant et en
        journalisant (SPECS.md §5.1). La chaîne n'en connaît que le verdict.
        """
        ...

    def prepare(self) -> None:
        """Résout l'entrée d'après pendant que la courante joue.

        Un tuyau qui se tarit ne fait pas un blanc dans l'audio : il fait un trou
        dans le temps réel, donc un tampon qui se vide chez l'auditeur
        (`docs/ffmpeg.md` §2.2).
        """
        ...


class Encoder:
    """L'unique ffmpeg qui produit le flux, cadencé au temps réel."""

    def __init__(self, stream_format: StreamFormat, command: str = "ffmpeg") -> None:
        self._format = stream_format
        self._commande = command

    def arguments(self) -> list[str]:
        """La ligne relevée dans `docs/ffmpeg.md` §2.1.

        `-re` n'est pas un réglage de confort : sans lui ffmpeg encode 95 fois
        plus vite que le temps réel (§2.3) et la bibliothèque entière passerait
        en quelques minutes.
        """
        pcm = self._format.pcm
        return [
            self._commande,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-re",
            "-f",
            pcm.sample,
            "-ar",
            str(pcm.sample_rate_hz),
            "-ac",
            str(pcm.channels),
            "-i",
            "-",
            "-f",
            self._format.container,
            "-b:a",
            f"{self._format.bitrate_kbps}k",
            "-",
        ]

    def start(self) -> subprocess.Popen[bytes]:
        """Lance l'encodeur, meneur de son propre groupe de processus.

        `process_group=0` le fait chef de groupe : son PID devient l'identifiant
        du groupe, et les décodeurs viendront s'y ranger. C'est ce qui permet
        d'arrêter **tout l'arbre** d'un seul signal (`docs/flux-icy.md` §3.bis).
        """
        try:
            processes = subprocess.Popen(
                self.arguments(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                process_group=0,
            )
        except OSError as error:
            message = f"l'encodeur n'a pas pu démarrer : {error}"
            raise ChainUnavailable(message) from error
        if processes.stderr is not None:
            journaliser_erreurs(processes.stderr, "encodeur")
        return processes


class Chain:
    """Le programme, les décodeurs, l'encodeur : un flux d'octets, et son arrêt.

    Elle ne connaît personne au-dessus d'elle : elle pousse ses octets dans
    `publier` et annonce sa fin par `sur_fin`. C'est ce qui évite le second
    défaut de `docs/flux-icy.md` §3.bis — aucun autre fil ne déréférence un
    processus qui vient de disparaître, puisque aucun autre fil ne le connaît.
    """

    def __init__(
        self,
        programme: Programme,
        stream_format: StreamFormat,
        publish: Callable[[bytes], None],
        on_end: Callable[[str], None],
        *,
        command: str = "ffmpeg",
        block_size: int = 4096,
        restarts: int = 1,
        stop_timeout: float = 5.0,
    ) -> None:
        self._programme = programme
        self._encodeur = Encoder(stream_format, command)
        self._decodeur = Decoder(stream_format.pcm, command)
        self._publier = publish
        self._sur_fin = on_end
        self._taille_bloc = block_size
        self._relances_restantes = restarts
        self._delai_arret = stop_timeout

        # `_etat` protège tout ce que deux fils peuvent voir changer, et sert
        # aussi de signal : le lecteur y attend la génération suivante quand
        # l'encodeur est mort et que la pompe le relance.
        self._etat = threading.Condition()
        self._processus: list[subprocess.Popen[bytes]] = []
        self._encodeur_actif: subprocess.Popen[bytes] | None = None
        self._decodeur_actif: subprocess.Popen[bytes] | None = None
        self._groupe = 0
        self._generation = 0
        self._fini = False
        self._arrete = False
        self._pompe: threading.Thread | None = None
        self._lecteur: threading.Thread | None = None

    @property
    def group(self) -> int:
        """Le groupe de processus de la chaîne courante, 0 si rien ne tourne."""
        with self._etat:
            return self._groupe

    def start(self) -> None:
        """Monte la chaîne, ou refuse en disant pourquoi.

        Tout ce qui échoue ici est fatal : aucun auditeur ne doit recevoir un flux
        vide parce que ffmpeg est absent ou que la bibliothèque n'a rien
        (SPECS.md §4.1).
        """
        with self._etat:
            self._monter()
            self._pompe = threading.Thread(target=self._pomper, name="chaine-pompe", daemon=True)
            self._lecteur = threading.Thread(
                target=self._lire_sortie, name="chaine-lecteur", daemon=True
            )
        self._programme.prepare()
        self._pompe.start()
        self._lecteur.start()

    def stop_all(self) -> None:
        """Arrête tout l'arbre de processus, et n'en laisse aucun derrière.

        Idempotente, et appelable depuis n'importe quel fil — y compris depuis la
        pompe elle-même, qui ne peut pas s'attendre.
        """
        with self._etat:
            if self._arrete:
                return
            self._arrete = True
            self._fini = True
            group = self._groupe
            processes = list(self._processus)
            self._processus.clear()
            self._encodeur_actif = None
            self._decodeur_actif = None
            self._groupe = 0
            self._etat.notify_all()

        _arreter_arbre(group, processes, self._delai_arret)

        courant = threading.current_thread()
        for fil in (self._pompe, self._lecteur):
            if fil is not None and fil is not courant:
                fil.join(self._delai_arret)

        # Les sorties ne sont fermées qu'une fois le lecteur parti : fermer un
        # tuyau qu'un autre fil est en train de lire, c'est reproduire sous une
        # autre forme la course de docs/flux-icy.md §3.bis.
        for termine in processes:
            _fermer_sortie(termine)

    # ── Montage et démontage ───────────────────────────────────────────────

    def _monter(self) -> None:
        """Démarre l'encodeur puis le premier décodeur. Appelée sous `_etat`."""
        premiere = self._programme.next_entry()
        if premiere is None:
            message = "le programme n'a rien à jouer : la radio ne démarre pas"
            raise ChainUnavailable(message)

        encoder = self._encodeur.start()
        self._encodeur_actif = encoder
        self._processus.append(encoder)
        self._groupe = encoder.pid

        try:
            self._ouvrir_decodeur(premiere)
        except DecodeFailed as error:
            self._demonter()
            raise ChainUnavailable(str(error)) from error

        self._generation += 1
        self._etat.notify_all()

    def _ouvrir_decodeur(self, entry: str) -> None:
        """Appelée sous `_etat`.

        Elle ne prend pas l'avance elle-même : `preparer` peut être lent — c'est
        même sa raison d'être — et le tenir sous le verrou empêcherait le lecteur
        de publier pendant ce temps, donc creuserait le trou qu'il doit combler.
        """
        decoder = self._decodeur.ouvrir(entry, self._groupe)
        self._decodeur_actif = decoder
        self._processus.append(decoder)
        logger.info("à l'antenne : %s", _sans_secret(entry))

    def _demonter(self) -> None:
        """Tue le groupe courant et récolte les processus. Appelée sous `_etat`."""
        group = self._groupe
        processes = list(self._processus)
        self._processus.clear()
        self._encodeur_actif = None
        self._decodeur_actif = None
        self._groupe = 0
        _arreter_arbre(group, processes, self._delai_arret)

    def _terminer(self, reason: str) -> None:
        logger.error("la radio coupe : %s", reason)
        self.stop_all()
        self._sur_fin(reason)

    # ── La pompe : décodeur → encodeur ─────────────────────────────────────

    def _pomper(self) -> None:
        """Verse le PCM du décodeur courant dans l'encodeur, morceau après morceau.

        Elle ne déréférence jamais un processus qu'elle n'a pas d'abord copié
        sous verrou : c'est la seconde cause du défaut de `docs/flux-icy.md`
        §3.bis, un `NoneType` lu pendant que l'arrêt effaçait la référence.
        """
        while not self._fini:
            with self._etat:
                decoder = self._decodeur_actif
            if decoder is None or decoder.stdout is None:
                return
            block = _lire(decoder.stdout, self._taille_bloc)
            if block:
                if not self._ecrire(block) and not self._relancer("l'encodeur s'est arrêté"):
                    return
                continue
            if not self._enchainer(decoder):
                return

    def _ecrire(self, block: bytes) -> bool:
        with self._etat:
            encoder = self._encodeur_actif
        if encoder is None or encoder.stdin is None:
            return False
        try:
            encoder.stdin.write(block)
            encoder.stdin.flush()
        except (BrokenPipeError, OSError, ValueError):
            return False
        return True

    def _enchainer(self, termine: subprocess.Popen[bytes]) -> bool:
        """Passe à l'entrée suivante. Rend `False` quand il n'y a plus rien à pomper."""
        code = self._recolter_decodeur(termine)
        if code != 0:
            logger.warning("entrée illisible (code %s) : la radio passe à la suivante", code)

        with self._etat:
            encoder = self._encodeur_actif
        if encoder is not None and encoder.poll() is not None:
            return self._relancer("l'encodeur s'est arrêté")

        next_entry = self._programme.next_entry()
        if next_entry is None:
            self._terminer("le programme n'a plus rien à jouer")
            return False

        try:
            with self._etat:
                if self._fini:
                    return False
                self._ouvrir_decodeur(next_entry)
        except DecodeFailed as error:
            # Un décodeur qui ne se lance pas n'est pas un morceau illisible :
            # celui-là échoue en cours et le suivant le remplace. Ici, c'est
            # ffmpeg lui-même qui manque, et le suivant échouerait pareil.
            self._terminer(str(error))
            return False
        self._programme.prepare()
        return True

    def _recolter_decodeur(self, termine: subprocess.Popen[bytes]) -> int | None:
        """Récolte le décodeur épuisé et l'oublie.

        Sans cet oubli, une nuit de diffusion laisserait derrière elle un
        `<defunct>` et deux descripteurs par morceau joué : l'arrêt final serait
        propre, et la chaîne aurait pourtant fui pendant huit heures.
        """
        code = termine.poll()
        if code is None:
            code = termine.wait(self._delai_arret)
        # Sans risque ici : la pompe est le seul fil qui lise cette sortie, et
        # c'est elle qui exécute cette ligne.
        _fermer_sortie(termine)
        with self._etat:
            if termine in self._processus:
                self._processus.remove(termine)
        return code

    def _relancer(self, reason: str) -> bool:
        """Relance la chaîne **une fois**, puis coupe (SPECS.md §5.1).

        Ne jamais relancer indéfiniment : une panne masquée n'est jamais réparée,
        et l'auditeur qui se rebranche redémarre de toute façon une chaîne neuve
        (SPECS.md §4.7).
        """
        if self._fini:
            return False
        if self._relances_restantes <= 0:
            self._terminer(f"{reason}, et elle ne se relève pas")
            return False
        self._relances_restantes -= 1
        logger.warning("%s : la chaîne est relancée une fois", reason)
        try:
            with self._etat:
                self._demonter()
                self._monter()
        except ChainUnavailable as error:
            self._terminer(f"la relance a échoué : {error}")
            return False
        self._programme.prepare()
        return True

    # ── Le lecteur : encodeur → auditeurs ──────────────────────────────────

    def _lire_sortie(self) -> None:
        """Publie ce que produit l'encodeur, et survit à sa relance.

        Un flux tari ne signifie pas la fin : il peut être une relance en cours.
        Le lecteur attend donc la génération suivante au lieu de conclure — sans
        quoi une relance réussie ne servirait plus personne.
        """
        while not self._fini:
            with self._etat:
                encoder = self._encodeur_actif
                generation = self._generation
            if encoder is None or encoder.stdout is None:
                return
            block = _lire(encoder.stdout, self._taille_bloc)
            if block:
                self._publier(block)
                continue
            if not self._attendre_relance(generation):
                return

    def _attendre_relance(self, generation: int) -> bool:
        """Attend qu'une nouvelle génération d'encodeur prenne le relais.

        Rend `False` si la chaîne est finie ou si rien n'est reparti : le lecteur
        s'arrête alors sans avoir touché au processus disparu.
        """
        with self._etat:
            self._etat.wait_for(
                lambda: self._fini or self._generation != generation,
                timeout=self._delai_arret,
            )
            return not self._fini and self._generation != generation


def _lire(feed: IO[bytes], taille: int) -> bytes:
    """Lit sans exiger que le tuyau existe encore.

    Un tuyau fermé sous les pieds du lecteur lève `ValueError`, pas `OSError` :
    les deux valent ici « il n'y a plus rien à lire », et c'est cette lecture-là
    qui remplace le déréférencement fautif de `docs/flux-icy.md` §3.bis.
    """
    try:
        return feed.read(taille)
    except (OSError, ValueError):
        return b""


def _arreter_arbre(group: int, processes: list[subprocess.Popen[bytes]], timeout: float) -> None:
    """Signale le groupe entier, puis récolte chaque processus.

    Les deux moitiés comptent. Le signal de groupe atteint ce dont on n'a pas
    gardé la référence ; la récolte évite les `<defunct>` — et c'est exactement
    ce qu'un test sur un booléen aurait manqué (`docs/flux-icy.md` §3.bis).
    """
    if group:
        _signaler(group, signal.SIGTERM)
    survivors = [p for p in processes if not _recolter(p, timeout)]
    if survivors:
        if group:
            _signaler(group, signal.SIGKILL)
        for restant in survivors:
            if not _recolter(restant, timeout):
                logger.error("un processus ffmpeg (%s) survit à l'arrêt", restant.pid)
    for termine in processes:
        _fermer_entree(termine)


def _signaler(group: int, signalement: signal.Signals) -> None:
    try:
        os.killpg(group, signalement)
    except (ProcessLookupError, PermissionError) as error:
        logger.debug("le groupe %s ne peut plus être signalé : %s", group, error)


def _recolter(processes: subprocess.Popen[bytes], timeout: float) -> bool:
    try:
        processes.wait(timeout)
    except subprocess.TimeoutExpired:
        return False
    return True


def _fermer_entree(processes: subprocess.Popen[bytes]) -> None:
    _fermer(processes.stdin, processes.pid)


def _fermer_sortie(processes: subprocess.Popen[bytes]) -> None:
    _fermer(processes.stdout, processes.pid)


def _fermer(pipe: IO[bytes] | None, pid: int) -> None:
    if pipe is None:
        return
    try:
        pipe.close()
    except OSError as error:
        logger.debug("tuyau déjà fermé pour %s : %s", pid, error)
