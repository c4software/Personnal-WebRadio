"""Le point d'entrée, et le seul endroit qui connaît tout le monde.

L'assemblage se fait à la main, une fois au démarrage : pas de conteneur, pas de
framework (ARCHITECTURE.md §3). C'est ici — et uniquement ici — que le noyau,
les adaptateurs et la configuration se rencontrent.

Rien de ce fichier ne décide : il construit, il branche, et il attend.
"""

import argparse
import logging
import signal
import sys
import threading
from collections.abc import Callable
from datetime import timedelta
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version
from pathlib import Path

from webradio.adapters.config.chargement import charger
from webradio.adapters.config.schema import Reglages
from webradio.adapters.etat.base import EtatSQLite
from webradio.adapters.ffmpeg.encodeur import Chaine, FormatFlux
from webradio.adapters.http.diffusion import Diffusion
from webradio.adapters.http.serveur import ServeurFlux, Station
from webradio.adapters.sources.navidrome import SourceNavidrome, TransportUrllib
from webradio.adapters.web.vues import creer_application
from webradio.app.apprentissage import Apprentissage
from webradio.app.programme import ProgrammeRadio
from webradio.app.radio import CompteurAuditeurs, RadioEnDirect
from webradio.core.clock import HorlogeSysteme
from webradio.core.controle import Controle
from webradio.core.file import File
from webradio.core.grille import Grille, Plage
from webradio.core.jingles import Jingles
from webradio.core.ponderation import PENTE_PAR_VOTE
from webradio.core.programmes import Programmation, Programme
from webradio.core.repetition import Fenetre
from webradio.core.rng import HasardReel

logger = logging.getLogger(__name__)

NOM = "local-webradio"
CHEMIN_DU_FLUX = "/flux"


def version() -> str:
    """La version déclarée du paquet.

    Lue depuis les métadonnées d'installation plutôt que recopiée ici : deux
    endroits qui portent le même numéro finissent toujours par diverger.
    """
    try:
        return _version("local-webradio")
    except PackageNotFoundError:
        return "0.0.0+source"


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    analyseur = argparse.ArgumentParser(prog=NOM, description="Une radio qui n'existe que branchée")
    analyseur.add_argument("--config", type=Path, default=Path("webradio.toml"))
    analyseur.add_argument("--env", type=Path, default=Path(".env"))
    return analyseur.parse_args(argv)


def construire(reglages: Reglages) -> tuple[ServeurFlux, RadioEnDirect, Station]:
    """Câble le tout, et rend ce qu'il faut pour le lancer et l'observer."""
    config = reglages.configuration
    horloge = HorlogeSysteme()
    hasard = HasardReel()

    # L'état est ouvert au démarrage : une base inaccessible **à ce moment-là**
    # est une erreur de configuration et doit se dire (SPECS.md §5). Devenue
    # inaccessible en cours, elle ne fait que rendre des poids neutres
    # (`app/apprentissage.py`).
    etat = EtatSQLite(
        Path(config.etat.base),
        horloge,
        delai_attente=timedelta(seconds=config.etat.delai_secondes),
        demi_vie_votes=timedelta(days=config.tirage.votes.demi_vie_jours),
    )
    apprentissage = Apprentissage(
        etat,
        plancher=config.tirage.votes.plancher,
        plafond=config.tirage.votes.plafond,
        pente=PENTE_PAR_VOTE,
        poids_croise=config.tirage.votes.poids_croise,
    )

    source = SourceNavidrome(
        identifiants=reglages.identifiants,
        reglages=config.navidrome,
        hasard=hasard,
        transport=TransportUrllib(config.navidrome.delai_secondes),
    )
    grille = Grille(
        [Plage(p.debut, p.fin, p.genres) for p in config.plages],
        horloge,
    )
    jingles = Jingles(horloge)
    controle = Controle(source=source, hasard=hasard, jingles=jingles)
    compteur = CompteurAuditeurs()
    radio = RadioEnDirect(controle, compteur, apprentissage.retenir)

    programme = ProgrammeRadio(
        file=File(
            source,
            hasard,
            Fenetre(config.tirage.non_repetition_artistes),
            peser=apprentissage.peser,
        ),
        source=source,
        grille=grille,
        jingles=jingles,
        horloge=horloge,
        hasard=hasard,
        dossier_jingles=Path(config.jingles.dossier),
        sur_nature=radio.declarer,
        programmation=Programmation(
            [
                Programme(
                    nom=p.nom,
                    playlist=p.playlist,
                    jours=p.jours,
                    debut=p.debut,
                    fin=p.fin,
                )
                for p in config.programmes
            ],
            horloge,
        ),
        fenetre_programme=Fenetre(config.tirage.non_repetition_artistes),
    )

    format_flux = FormatFlux(
        conteneur=config.flux.format,
        debit_kbps=config.flux.debit_kbps,
        frequence_hz=config.flux.frequence_hz,
        canaux=config.flux.canaux,
    )
    station = Station(_fabrique_de_chaine(programme, format_flux, compteur))
    serveur = ServeurFlux(
        station,
        format_flux,
        adresse=config.flux.adresse,
        port=config.flux.port,
        chemin=CHEMIN_DU_FLUX,
        nom=NOM,
    )
    return serveur, radio, station


def _fabrique_de_chaine(
    programme: ProgrammeRadio,
    format_flux: FormatFlux,
    compteur: CompteurAuditeurs,
) -> Callable[[Diffusion], Chaine]:
    """Rend de quoi construire une chaîne, en tenant le compteur à jour.

    Le compteur existe pour que l'API sache si quelqu'un écoute **sans rien
    connaître du serveur** (`app/radio.py`) : c'est la seule information que la
    façade a besoin de recevoir d'en bas.
    """

    def construire_la_chaine(diffusion: Diffusion) -> Chaine:
        compteur.declarer(en_antenne=True)

        def fin(raison: str) -> None:
            compteur.declarer(en_antenne=False)
            logger.warning("la chaîne s'arrête : %s", raison)

        return Chaine(programme, format_flux, diffusion.publier, fin)

    return construire_la_chaine


def main(argv: list[str] | None = None) -> int:
    """Démarre, sert, et s'arrête proprement sur SIGTERM.

    Rend un code de sortie plutôt que d'appeler `sys.exit` : une fonction qui
    rend une valeur se teste, une fonction qui quitte le processus non.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    options = _arguments(argv)
    logger.info("%s %s", NOM, version())

    reglages = charger(options.config, options.env)
    serveur, radio, _ = construire(reglages)
    web = reglages.configuration.web
    application = creer_application(
        radio,
        rafraichissement=timedelta(seconds=web.rafraichissement_secondes),
    )

    arret = threading.Event()

    def demander_larret(*_: object) -> None:
        arret.set()

    signal.signal(signal.SIGTERM, demander_larret)
    signal.signal(signal.SIGINT, demander_larret)

    fil_web = threading.Thread(
        target=lambda: application.run(host=web.adresse, port=web.port, threaded=True),
        daemon=True,
    )
    fil_web.start()
    serveur.demarrer()
    logger.info("flux sur %s, interface sur le port %d", CHEMIN_DU_FLUX, web.port)

    arret.wait()
    logger.info("arrêt demandé")
    serveur.arreter()
    return 0


if __name__ == "__main__":
    sys.exit(main())
