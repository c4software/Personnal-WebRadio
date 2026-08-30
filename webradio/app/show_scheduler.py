"""Décider si une émission est due, et laquelle — la troisième charnière.

Elle relie trois choses qui ne se connaissent pas : le noyau qui sait *quelle
case est ouverte* (`core/emissions.py`), le flux de podcast qui sait *quels
épisodes existent* (`adapters/podcast/`), et la base qui sait *lequel a déjà été
diffusé* (`adapters/etat/`).

**C'est le seul endroit du projet où une décision exige un appel réseau qui peut
ne servir à rien** (ARCHITECTURE.md §5.2) : le rattrapage est borné par la durée
de l'épisode, et cette durée n'est connue qu'après avoir lu le flux. Il faut donc
interroger le podcast pour savoir s'il y a lieu de rattraper — avant même de
savoir si l'on s'en servira.
"""

import logging
from datetime import timedelta

from webradio.adapters.state.database import EtatIndisponible, EtatSQLite
from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import FluxPodcast, PodcastIndisponible
from webradio.core.clock import Horloge
from webradio.core.shows import Emission, Episode, GrilleDesEmissions, episode_a_diffuser

logger = logging.getLogger(__name__)


class Emissions:
    """Ce qui est dû à l'antenne, et l'URL audio à ouvrir pour le diffuser."""

    def __init__(
        self,
        programme: GrilleDesEmissions,
        flux: FluxPodcast,
        etat: EtatSQLite,
        horloge: Horloge,
        adresses: dict[str, str],
    ) -> None:
        self._programme = programme
        self._flux = flux
        self._etat = etat
        self._horloge = horloge
        self._adresses = adresses

    def due(self) -> tuple[Emission, str] | None:
        """L'émission due maintenant et l'URL de son épisode, ou rien.

        Rend `None` dans tous les cas où « il n'y a pas d'émission » — aucune
        case ouverte, flux injoignable, épisode déjà diffusé. Aucun n'est une
        panne : la radio reste sur la musique (SPECS.md §4.11).
        """
        instant = self._horloge.maintenant()
        catalogues = self._catalogues(instant)
        durees = {
            nom: episodes[0].duree
            for nom, episodes in catalogues.items()
            if episodes and episodes[0].duree is not None
        }
        case = self._programme.due(durees, instant)
        if case is None:
            return None
        return self._episode_de(case.emission, catalogues.get(case.emission.nom, []))

    def _catalogues(self, instant: object) -> dict[str, list[EpisodeDuFlux]]:
        """Lit les flux des émissions dont une case a pu commencer.

        On lit **avant** de savoir si l'on s'en servira : sans la durée, on ne
        peut pas dire si la case est encore ouverte. C'est le coût assumé de la
        décision n°13.
        """
        catalogues: dict[str, list[EpisodeDuFlux]] = {}
        for emission in self._programme.emissions:
            if self._programme.debut_de_case(emission, instant) is None:  # type: ignore[arg-type]
                continue
            adresse = self._adresses.get(emission.nom)
            if adresse is None:
                continue
            try:
                catalogues[emission.nom] = self._flux.episodes(adresse)
            except PodcastIndisponible as panne:
                logger.warning(
                    "flux de « %s » injoignable, pas de rattrapage : %s", emission.nom, panne
                )
        return catalogues

    def _episode_de(
        self, emission: Emission, catalogue: list[EpisodeDuFlux]
    ) -> tuple[Emission, str] | None:
        if not catalogue:
            return None
        try:
            deja = self._etat.derniere_diffusion(emission.nom)
        except EtatIndisponible as panne:
            # Sans mémoire, on rediffuserait en boucle. Mieux vaut sauter la
            # case : une émission manquée est bien moins gênante qu'une
            # émission qui repasse indéfiniment (SPECS.md §4.11).
            logger.warning("mémoire indisponible, émission « %s » sautée : %s", emission.nom, panne)
            return None
        choisi = episode_a_diffuser(
            [
                Episode(
                    guid=e.identifiant,
                    publie_le=e.publie_le,
                    duree=e.duree if e.duree is not None else timedelta(0),
                    nature="full",
                )
                for e in catalogue
            ],
            deja.episode if deja is not None else None,
        )
        if choisi is None:
            logger.info("« %s » n'a rien de neuf : la case est sautée", emission.nom)
            return None
        audio = next(e.audio for e in catalogue if e.identifiant == choisi.guid)
        try:
            self._etat.enregistrer_diffusion(emission.nom, choisi.guid)
        except EtatIndisponible as panne:
            logger.warning("diffusion non retenue, elle se rejouera : %s", panne)
        return emission, audio
