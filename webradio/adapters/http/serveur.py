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

from webradio.adapters.ffmpeg.encodeur import ChaineIndisponible, FormatFlux
from webradio.adapters.http.diffusion import Abonne, Diffusion

logger = logging.getLogger(__name__)


class Alimentation(Protocol):
    """Ce que le serveur attend d'une chaîne : qu'elle démarre et qu'elle s'arrête.

    Le serveur ignore délibérément d'où viennent les octets — il ne les touche
    même pas, ils vont de la chaîne à la `Diffusion` sans passer par ici.
    """

    def demarrer(self) -> None: ...

    def arreter(self) -> None: ...


class Station:
    """La chaîne existe tant que quelqu'un écoute, et pas une seconde de plus."""

    def __init__(
        self,
        fabrique: Callable[[Diffusion], Alimentation],
        *,
        capacite_par_auditeur: int = 64,
    ) -> None:
        self._fabrique = fabrique
        self._capacite = capacite_par_auditeur
        self._verrou = threading.RLock()
        self._diffusion: Diffusion | None = None
        self._chaine: Alimentation | None = None

    @property
    def auditeurs(self) -> int:
        with self._verrou:
            return self._diffusion.auditeurs if self._diffusion is not None else 0

    @property
    def en_antenne(self) -> bool:
        with self._verrou:
            return self._chaine is not None

    def brancher(self) -> Abonne:
        """Branche un auditeur, en démarrant la chaîne s'il est le premier.

        Une chaîne qui refuse de démarrer laisse la station intacte : l'auditeur
        suivant réessaiera, et celui-ci reçoit une erreur explicite plutôt qu'un
        flux vide (SPECS.md §4.1).
        """
        with self._verrou:
            if self._diffusion is None:
                diffusion = Diffusion(self._capacite)
                chaine = self._fabrique(diffusion)
                chaine.demarrer()
                self._diffusion, self._chaine = diffusion, chaine
                logger.info("premier auditeur : la chaîne démarre")
            return self._diffusion.abonner()

    def debrancher(self, abonne: Abonne) -> None:
        """Débranche un auditeur, et arrête tout s'il était le dernier."""
        with self._verrou:
            if self._diffusion is None:
                return
            self._diffusion.desabonner(abonne)
            if self._diffusion.auditeurs == 0:
                logger.info("dernier auditeur parti : la chaîne s'arrête")
                self.arreter()

    def arreter(self) -> None:
        """Arrête la chaîne et oublie la diffusion. Idempotente.

        Oublier la diffusion n'est pas un détail : un auditeur qui se rebranche
        redémarre une chaîne **neuve**, la radio ne reprend pas où elle en était
        (SPECS.md §4.7).
        """
        with self._verrou:
            chaine, self._chaine = self._chaine, None
            diffusion, self._diffusion = self._diffusion, None
        if chaine is not None:
            chaine.arreter()
        if diffusion is not None:
            diffusion.fermer("la chaîne est arrêtée")


class GestionnaireFlux(BaseHTTPRequestHandler):
    """Une connexion d'auditeur, de son branchement à sa déconnexion."""

    def __init__(
        self,
        *args: Any,
        station: Station,
        format_flux: FormatFlux,
        chemin: str,
        nom: str,
        delai_attente: float,
        **kwargs: Any,
    ) -> None:
        # Renseignés avant l'appel au parent : celui-ci traite la requête depuis
        # son propre constructeur.
        self._station = station
        self._format = format_flux
        self._chemin = chemin
        self._nom = nom
        self._delai = delai_attente
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        if self.path.split("?")[0] != self._chemin:
            self._repondre_texte(HTTPStatus.NOT_FOUND, f"le flux est servi sur {self._chemin}")
            return
        try:
            abonne = self._station.brancher()
        except ChaineIndisponible as erreur:
            logger.error("branchement refusé : %s", erreur)
            self._repondre_texte(
                HTTPStatus.SERVICE_UNAVAILABLE, f"la radio ne démarre pas : {erreur}"
            )
            return
        try:
            self._servir(abonne)
        finally:
            self._station.debrancher(abonne)

    def log_message(self, format: str, *args: Any) -> None:
        """Le journal du serveur passe par `logging`, pas par la sortie d'erreur."""
        logger.debug("%s %s", self.address_string(), format % args)

    def _servir(self, abonne: Abonne) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self._format.type_mime)
        self.send_header("icy-name", self._nom)
        self.send_header("icy-br", str(self._format.debit_kbps))
        self.end_headers()
        try:
            for bloc in abonne.blocs(self._delai):
                self.wfile.write(bloc)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            # La seule façon fiable de constater une déconnexion brutale : la
            # socket ne l'annonce pas, elle refuse la prochaine écriture
            # (docs/flux-icy.md §5).
            logger.info("auditeur débranché brutalement")

    def _repondre_texte(self, code: HTTPStatus, message: str) -> None:
        """Une erreur se dit en clair : jamais un 200 suivi d'un flux vide."""
        corps = f"{message}\n".encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


class ServeurFlux:
    """Le serveur HTTP qui sert le flux, et lui seul."""

    def __init__(
        self,
        station: Station,
        format_flux: FormatFlux,
        *,
        adresse: str,
        port: int,
        chemin: str,
        nom: str,
        delai_attente: float = 30.0,
        delai_arret: float = 5.0,
    ) -> None:
        gestionnaire = partial(
            GestionnaireFlux,
            station=station,
            format_flux=format_flux,
            chemin=chemin,
            nom=nom,
            delai_attente=delai_attente,
        )
        # Un fil par connexion, tous démons : une socket muette ne doit jamais
        # retenir l'arrêt du programme.
        self._serveur = ThreadingHTTPServer((adresse, port), gestionnaire)
        self._serveur.daemon_threads = True
        self._station = station
        self._delai_arret = delai_arret
        self._fil: threading.Thread | None = None

    @property
    def port(self) -> int:
        """Le port réellement ouvert — un test demande le port 0 et le découvre ici."""
        return int(self._serveur.server_address[1])

    def demarrer(self) -> None:
        self._fil = threading.Thread(
            target=self._serveur.serve_forever, name="serveur-flux", daemon=True
        )
        self._fil.start()
        logger.info("flux servi sur le port %d", self.port)

    def arreter(self) -> None:
        """Ferme le serveur, puis la chaîne : plus personne ne peut se brancher."""
        self._serveur.shutdown()
        self._serveur.server_close()
        if self._fil is not None:
            self._fil.join(self._delai_arret)
        self._station.arreter()
