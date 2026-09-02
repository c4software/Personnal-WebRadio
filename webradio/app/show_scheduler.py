"""Décider si une émission est due, et laquelle.

Ce module relie le noyau, qui sait quelle case est ouverte (`core/shows.py`),
le flux de podcast, qui sait quels épisodes existent (`adapters/podcast/`), et
la base, qui sait lequel a déjà été diffusé (`adapters/state/`).

C'est le seul endroit où une décision exige un appel réseau qui peut ne servir
à rien (ARCHITECTURE.md §5.2) : le rattrapage est borné par la durée de
l'épisode, connue seulement après lecture du flux.
"""

import logging
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import PodcastFeed, PodcastUnavailable
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.youtube.channel import YoutubeChannel, YoutubeUnavailable
from webradio.core.clock import Clock
from webradio.core.shows import Episode, Show, ShowSchedule, Slot, episode_to_air

logger = logging.getLogger(__name__)


class Shows:
    """L'émission due à l'antenne, et l'adresse audio à ouvrir pour la diffuser."""

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
        youtube_cache: Path | None = None,
    ) -> None:
        self._programme = programme
        self._flux = feed
        self._etat = state
        self._horloge = clock
        self._adresses = addresses
        # Les directs (nom vers URL) ne passent ni par le podcast ni par la
        # base : chaque occurrence de la case est diffusée (SPECS.md §7 n°22),
        # et `_cases_rendues` suffit pour ne la rendre qu'une fois.
        self._directs = streams or {}
        # Les chaînes YouTube suivent la mécanique des podcasts : dernière
        # vidéo non diffusée, case bornée par sa durée (docs/youtube.md §2).
        self._youtube = youtube_channels or {}
        self._youtube_adapter = youtube
        self._youtube_cache = youtube_cache
        # Les identifiants des vidéos en cours de téléchargement.
        self._telechargements: set[str] = set()
        self._verrou_telechargements = threading.Lock()
        self._cases_rendues: set[tuple[str, datetime]] = set()

    def due(self) -> tuple[Show, str, str | None] | None:
        """L'émission due, l'adresse de son épisode, et le titre de l'épisode.

        Le titre (vidéo ou épisode) sert à l'antenne et au journal (GOAL-027) ;
        il vaut `None` s'il n'y en a pas.

        Rend `None` quand il n'y a pas d'émission : aucune case ouverte, flux
        injoignable, épisode déjà diffusé. Aucun de ces cas n'est une panne,
        la radio reste sur la musique (SPECS.md §4.11).
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
        if case.show.name in self._youtube:
            return self._video_de(case.show, catalogues.get(case.show.name, []))
        return self._episode_de(case.show, catalogues.get(case.show.name, []))

    def _direct_de(self, case: Slot, instant: datetime) -> tuple[Show, str, str | None] | None:
        """Un direct, rendu une fois par case, avec l'heure absolue de sa fin.

        L'entrée `live:<fin en secondes Unix>:<url>` est lue par Liquidsoap
        (`adapters/liquidsoap/radio.liq`) : capter cette URL et couper à cette
        heure, quelle que soit l'heure de la jonction. Une deuxième demande
        dans la même case rend `None`, sinon le direct redémarrerait à chaque
        jonction jusqu'à la fin de la case.
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
        return case.show, f"live:{int(case.end.timestamp())}:{url}", None

    @staticmethod
    def _nom_de_cache(show_name: str) -> str:
        """Un nom de fichier stable par émission : chaque téléchargement écrase
        le précédent, rien ne s'accumule (GOAL-028). Le fichier `.id` à côté
        dit quelle vidéo c'est."""
        return re.sub(r"[^a-z0-9]+", "-", show_name.lower()).strip("-") or "emission"

    def _video_de(
        self, show: Show, catalogue: list[EpisodeDuFlux]
    ) -> tuple[Show, str, str | None] | None:
        """La dernière vidéo, servie depuis le cache local, jamais par son URL.

        Servir l'URL googlevideo faisait télécharger le diffuseur à la
        jonction, avec un blanc de trente à soixante secondes
        (docs/youtube.md §5). Sans fichier prêt, le téléchargement part en
        tâche de fond et la fonction rend `None` ; la vidéo passera à une
        jonction suivante, si la case est encore ouverte.
        """
        if not catalogue or self._youtube_adapter is None or self._youtube_cache is None:
            return None
        chosen = self._choisir_l_episode(show, catalogue)
        if chosen is None:
            return None
        nom = self._nom_de_cache(show.name)
        fichier = self._youtube_cache / f"{nom}.m4a"
        temoin = self._youtube_cache / f"{nom}.id"
        # Le fichier n'est servi que s'il correspond à la vidéo choisie, sinon
        # un reste d'une autre semaine passerait à sa place.
        est_la_bonne = (
            fichier.is_file() and temoin.is_file() and temoin.read_text().strip() == chosen.guid
        )
        if est_la_bonne:
            try:
                self._etat.record_airing(show.name, chosen.guid)
            except StateUnavailable as failure:
                logger.warning("diffusion non retenue, elle se rejouera : %s", failure)
            titre = next((e.title for e in catalogue if e.identifier == chosen.guid), None)
            return show, str(fichier), titre
        self._telecharger_en_fond(show.name, nom, chosen.guid)
        return None

    def _telecharger_en_fond(self, show_name: str, nom: str, video: str) -> None:
        with self._verrou_telechargements:
            if video in self._telechargements:
                return
            self._telechargements.add(video)
        logger.info("« %s » : téléchargement de %s — la musique continue", show_name, video)

        def au_travail() -> None:
            assert self._youtube_adapter is not None and self._youtube_cache is not None
            try:
                self._youtube_cache.mkdir(parents=True, exist_ok=True)
                cible = self._youtube_cache / f"{nom}.m4a"
                temoin = self._youtube_cache / f"{nom}.id"
                # Le `.id` est supprimé avant le fichier : à aucun moment un
                # vieux fichier ne peut passer pour la nouvelle vidéo.
                temoin.unlink(missing_ok=True)
                cible.unlink(missing_ok=True)
                (self._youtube_cache / f"{nom}.m4a.part").unlink(missing_ok=True)
                self._youtube_adapter.download(
                    f"https://www.youtube.com/watch?v={video}", str(cible)
                )
                temoin.write_text(video)
                logger.info("« %s » : %s est prêt, il partira à la jonction", show_name, video)
            except YoutubeUnavailable as failure:
                logger.warning("« %s » : téléchargement en échec — %s", show_name, failure)
            finally:
                with self._verrou_telechargements:
                    self._telechargements.discard(video)

        threading.Thread(target=au_travail, name=f"youtube-{video}", daemon=True).start()

    def _choisir_l_episode(self, show: Show, catalogue: list[EpisodeDuFlux]) -> Episode | None:
        try:
            deja = self._etat.last_airing(show.name)
        except StateUnavailable as failure:
            logger.warning("mémoire indisponible, émission « %s » sautée : %s", show.name, failure)
            return None
        chosen = episode_to_air(
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
        if chosen is None:
            logger.info("« %s » n'a rien de neuf : la case est sautée", show.name)
        return chosen

    def _catalogues(self, instant: object) -> dict[str, list[EpisodeDuFlux]]:
        """Lit les flux des émissions dont une case a pu commencer.

        On lit avant de savoir si on s'en servira : sans la durée, on ne peut
        pas dire si la case est encore ouverte (décision n°13).
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

    def _episode_de(
        self, show: Show, catalogue: list[EpisodeDuFlux]
    ) -> tuple[Show, str, str | None] | None:
        if not catalogue:
            return None
        try:
            deja = self._etat.last_airing(show.name)
        except StateUnavailable as failure:
            # Sans mémoire, on rediffuserait le même épisode en boucle. Sauter
            # la case est moins gênant (SPECS.md §4.11).
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
        titre = next((e.title for e in catalogue if e.identifier == choisi.guid), None)
        try:
            self._etat.record_airing(show.name, choisi.guid)
        except StateUnavailable as failure:
            logger.warning("diffusion non retenue, elle se rejouera : %s", failure)
        return show, audio, titre
