"""Le serveur du flux, et le cycle de vie de la chaîne.

SPECS.md §1 exige que **rien ne tourne tant que personne n'écoute**. C'est ce
qui a écarté Icecast (ARCHITECTURE.md §4) et c'est ce que la `Station`
implémente, littéralement : la chaîne naît à la première connexion et meurt à la
dernière, brutale comprise (SPECS.md §4.7).

Les en-têtes servis sont ceux que `docs/flux-icy.md` §1 a constatés acceptés :
`Content-Type: audio/mpeg`, `icy-name`, `icy-br`, et **ni `Content-Length` ni
`Transfer-Encoding`** — un flux de radio n'a pas de longueur.
"""

import logging
import threading
from collections.abc import Callable
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Protocol

from webradio.adapters.ffmpeg.encoder import ChainUnavailable, StreamFormat
from webradio.adapters.http.broadcast import Broadcast, Subscriber

logger = logging.getLogger(__name__)


class Feed(Protocol):
    """Ce que le serveur attend d'une chaîne : qu'elle démarre et qu'elle s'arrête.

    Le serveur ignore délibérément d'où viennent les octets — il ne les touche
    même pas, ils vont de la chaîne à la `Diffusion` sans passer par ici.
    """

    def start(self) -> None: ...

    def stop_all(self) -> None: ...


class Station:
    """La chaîne existe tant que quelqu'un écoute, et pas une seconde de plus."""

    def __init__(
        self,
        factory: Callable[[Broadcast], Feed],
        *,
        capacity_per_listener: int = 64,
    ) -> None:
        self._fabrique = factory
        self._capacite = capacity_per_listener
        self._verrou = threading.RLock()
        self._diffusion: Broadcast | None = None
        self._chaine: Feed | None = None

    @property
    def listeners(self) -> int:
        with self._verrou:
            return self._diffusion.listeners if self._diffusion is not None else 0

    @property
    def on_air(self) -> bool:
        with self._verrou:
            return self._chaine is not None

    def connect(self) -> Subscriber:
        """Branche un auditeur, en démarrant la chaîne s'il est le premier.

        Une chaîne qui refuse de démarrer laisse la station intacte : l'auditeur
        suivant réessaiera, et celui-ci reçoit une erreur explicite plutôt qu'un
        flux vide (SPECS.md §4.1).
        """
        with self._verrou:
            if self._diffusion is None:
                broadcast = Broadcast(self._capacite)
                chaine = self._fabrique(broadcast)
                chaine.start()
                self._diffusion, self._chaine = broadcast, chaine
                logger.info("premier auditeur : la chaîne démarre")
            return self._diffusion.subscribe()

    def disconnect(self, subscriber: Subscriber) -> None:
        """Débranche un auditeur, et arrête tout s'il était le dernier."""
        with self._verrou:
            if self._diffusion is None:
                return
            self._diffusion.unsubscribe(subscriber)
            if self._diffusion.listeners == 0:
                logger.info("dernier auditeur parti : la chaîne s'arrête")
                self.stop_all()

    def stop_all(self) -> None:
        """Arrête la chaîne et oublie la diffusion. Idempotente.

        Oublier la diffusion n'est pas un détail : un auditeur qui se rebranche
        redémarre une chaîne **neuve**, la radio ne reprend pas où elle en était
        (SPECS.md §4.7).
        """
        with self._verrou:
            chaine, self._chaine = self._chaine, None
            broadcast, self._diffusion = self._diffusion, None
        if chaine is not None:
            chaine.stop_all()
        if broadcast is not None:
            broadcast.close("la chaîne est arrêtée")


class StreamHandler(BaseHTTPRequestHandler):
    """Une connexion d'auditeur, de son branchement à sa déconnexion."""

    def __init__(
        self,
        *args: Any,
        station: Station,
        stream_format: StreamFormat,
        path: str,
        name: str,
        lock_timeout: float,
        **kwargs: Any,
    ) -> None:
        # Renseignés avant l'appel au parent : celui-ci traite la requête depuis
        # son propre constructeur.
        self._station = station
        self._format = stream_format
        self._chemin = path
        self._nom = name
        self._delai = lock_timeout
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path.split("?")[0] != self._chemin:
            self._repondre_texte(HTTPStatus.NOT_FOUND, f"le flux est servi sur {self._chemin}")
            return
        try:
            subscriber = self._station.connect()
        except ChainUnavailable as error:
            logger.error("branchement refusé : %s", error)
            self._repondre_texte(
                HTTPStatus.SERVICE_UNAVAILABLE, f"la radio ne démarre pas : {error}"
            )
            return
        try:
            self._servir(subscriber)
        finally:
            self._station.disconnect(subscriber)

    def log_message(self, format: str, *args: Any) -> None:
        """Le journal du serveur passe par `logging`, pas par la sortie d'erreur."""
        logger.debug("%s %s", self.address_string(), format % args)

    def _servir(self, subscriber: Subscriber) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self._format.type_mime)
        self.send_header("icy-name", self._nom)
        self.send_header("icy-br", str(self._format.bitrate_kbps))
        self.end_headers()
        try:
            for block in subscriber.blocks(self._delai):
                self.wfile.write(block)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            # La seule façon fiable de constater une déconnexion brutale : la
            # socket ne l'annonce pas, elle refuse la prochaine écriture
            # (docs/flux-icy.md §5).
            logger.info("auditeur débranché brutalement")

    def _repondre_texte(self, code: HTTPStatus, message: str) -> None:
        """Une erreur se dit en clair : jamais un 200 suivi d'un flux vide."""
        body = f"{message}\n".encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class StreamServer:
    """Le serveur HTTP qui sert le flux, et lui seul."""

    def __init__(
        self,
        station: Station,
        stream_format: StreamFormat,
        *,
        address: str,
        port: int,
        path: str,
        name: str,
        lock_timeout: float = 30.0,
        stop_timeout: float = 5.0,
    ) -> None:
        gestionnaire = partial(
            StreamHandler,
            station=station,
            stream_format=stream_format,
            path=path,
            name=name,
            lock_timeout=lock_timeout,
        )
        # Un fil par connexion, tous démons : une socket muette ne doit jamais
        # retenir l'arrêt du programme.
        self._serveur = ThreadingHTTPServer((address, port), gestionnaire)
        self._serveur.daemon_threads = True
        self._station = station
        self._delai_arret = stop_timeout
        self._fil: threading.Thread | None = None

    @property
    def port(self) -> int:
        """Le port réellement ouvert — un test demande le port 0 et le découvre ici."""
        return int(self._serveur.server_address[1])

    def start(self) -> None:
        self._fil = threading.Thread(
            target=self._serveur.serve_forever, name="serveur-flux", daemon=True
        )
        self._fil.start()
        logger.info("flux servi sur le port %d", self.port)

    def stop_all(self) -> None:
        """Ferme le serveur, puis la chaîne : plus personne ne peut se brancher."""
        self._serveur.shutdown()
        self._serveur.server_close()
        if self._fil is not None:
            self._fil.join(self._delai_arret)
        self._station.stop_all()
