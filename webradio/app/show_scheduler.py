"""Décider si une émission est due, et laquelle — la troisième charnière.

Elle relie trois choses qui ne se connaissent pas : le noyau qui sait *quelle
case est ouverte* (`core/shows.py`), le flux de podcast qui sait *quels
épisodes existent* (`adapters/podcast/`), et la base qui sait *lequel a déjà été
diffusé* (`adapters/state/`).

**C'est le seul endroit du projet où une décision exige un appel réseau qui peut
ne servir à rien** (ARCHITECTURE.md §5.2) : le rattrapage est borné par la durée
de l'épisode, et cette durée n'est connue qu'après avoir lu le flux. Il faut donc
interroger le podcast pour savoir s'il y a lieu de rattraper — avant même de
savoir si l'on s'en servira.
"""

import logging
from datetime import datetime, timedelta

from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import PodcastFeed, PodcastUnavailable
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.youtube.channel import YoutubeChannel, YoutubeUnavailable
from webradio.core.clock import Clock
from webradio.core.shows import Episode, Show, ShowSchedule, Slot, episode_to_air

logger = logging.getLogger(__name__)


class Shows:
    """Ce qui est dû à l'antenne, et l'URL audio à ouvrir pour le diffuser."""

    def __init__(
        self,
        programme: ShowSchedule,
        feed: PodcastFeed,
        state: SqliteState,
        clock: Clock,
        addresses: dict[str, str],
        streams: dict[str, str] | None = None,
        youtube_channels: dict[str, str] | None = None,
        youtube: YoutubeChannel | None = None,
    ) -> None:
        self._programme = programme
        self._flux = feed
        self._etat = state
        self._horloge = clock
        self._adresses = addresses
        # Les directs : nom → URL. Ils ne passent ni par le podcast ni par la
        # base ; une case n'est rendue qu'une fois, et ce registre suffit
        # (SPECS.md §7 n°22 : « elle se produit à chaque occurrence de sa case »).
        self._directs = streams or {}
        # Les chaînes YouTube : même mécanique que les podcasts — la dernière
        # vidéo non diffusée, la case bornée par sa durée (docs/youtube.md §2).
        self._youtube = youtube_channels or {}
        self._youtube_adapter = youtube
        self._cases_rendues: set[tuple[str, datetime]] = set()

    def due(self) -> tuple[Show, str] | None:
        """L'émission due maintenant et l'URL de son épisode, ou rien.

        Rend `None` dans tous les cas où « il n'y a pas d'émission » — aucune
        case ouverte, flux injoignable, épisode déjà diffusé. Aucun n'est une
        panne : la radio reste sur la musique (SPECS.md §4.11).
        """
        instant = self._horloge.now()
        catalogues = self._catalogues(instant)
        durations = {
            name: episodes[0].duration
            for name, episodes in catalogues.items()
            if episodes and episodes[0].duration is not None
        }
        case = self._programme.due(durations, instant)
        if case is None:
            return None
        if case.show.is_live:
            return self._direct_de(case, instant)
        return self._episode_de(case.show, catalogues.get(case.show.name, []))

    def _direct_de(self, case: Slot, instant: datetime) -> tuple[Show, str] | None:
        """Un direct, rendu **une fois par case**, avec l'heure absolue de sa fin.

        L'entrée `live:<fin en secondes Unix>:<url>` est une instruction pour
        Liquidsoap (`adapters/liquidsoap/radio.liq`) : capter cette URL, et
        couper à cette heure — quelle que soit l'heure où la jonction arrive.
        La deuxième demande dans la même case rend la musique : sinon, le
        direct redémarrerait à chaque jonction jusqu'à la fin de la case.
        """
        cle = (case.show.name, case.start)
        if cle in self._cases_rendues:
            return None
        url = self._directs.get(case.show.name)
        if url is None or case.end is None:
            return None
        self._cases_rendues.add(cle)
        self._cases_rendues = {c for c in self._cases_rendues if c[1] > instant - timedelta(days=2)}
        logger.info(
            "direct « %s » jusqu'à %s — %s",
            case.show.name,
            case.end.astimezone().strftime("%H:%M:%S"),
            url.split("?", 1)[0],
        )
        return case.show, f"live:{int(case.end.timestamp())}:{url}"

    def _catalogues(self, instant: object) -> dict[str, list[EpisodeDuFlux]]:
        """Lit les flux des émissions dont une case a pu commencer.

        On lit **avant** de savoir si l'on s'en servira : sans la durée, on ne
        peut pas dire si la case est encore ouverte. C'est le coût assumé de la
        décision n°13.
        """
        catalogues: dict[str, list[EpisodeDuFlux]] = {}
        for show in self._programme.shows:
            if show.is_live:
                continue
            if self._programme.slot_start(show, instant) is None:  # type: ignore[arg-type]
                continue
            chaine = self._youtube.get(show.name)
            if chaine is not None and self._youtube_adapter is not None:
                try:
                    catalogues[show.name] = self._youtube_adapter.episodes(chaine)
                except YoutubeUnavailable as failure:
                    logger.warning(
                        "chaîne YouTube de « %s » injoignable, case sautée : %s",
                        show.name,
                        failure,
                    )
                continue
            address = self._adresses.get(show.name)
            if address is None:
                continue
            try:
                catalogues[show.name] = self._flux.episodes(address)
            except PodcastUnavailable as failure:
                logger.warning(
                    "flux de « %s » injoignable, pas de rattrapage : %s", show.name, failure
                )
        return catalogues

    def _episode_de(self, show: Show, catalogue: list[EpisodeDuFlux]) -> tuple[Show, str] | None:
        if not catalogue:
            return None
        try:
            deja = self._etat.last_airing(show.name)
        except StateUnavailable as failure:
            # Sans mémoire, on rediffuserait en boucle. Mieux vaut sauter la
            # case : une émission manquée est bien moins gênante qu'une
            # émission qui repasse indéfiniment (SPECS.md §4.11).
            logger.warning("mémoire indisponible, émission « %s » sautée : %s", show.name, failure)
            return None
        choisi = episode_to_air(
            [
                Episode(
                    guid=e.identifier,
                    published_at=e.published_at,
                    duration=e.duration if e.duration is not None else timedelta(0),
                    kind="full",
                )
                for e in catalogue
            ],
            deja.episode if deja is not None else None,
        )
        if choisi is None:
            logger.info("« %s » n'a rien de neuf : la case est sautée", show.name)
            return None
        audio = next(e.audio for e in catalogue if e.identifier == choisi.guid)
        try:
            self._etat.record_airing(show.name, choisi.guid)
        except StateUnavailable as failure:
            logger.warning("diffusion non retenue, elle se rejouera : %s", failure)
        return show, audio
