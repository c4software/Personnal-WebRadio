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
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import PodcastFeed, PodcastUnavailable
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.youtube.channel import YoutubeChannel, YoutubeUnavailable
from webradio.core.clock import Clock
from webradio.core.rng import Random
from webradio.core.shows import (
    Episode,
    Show,
    ShowSchedule,
    Slot,
    episode_among,
    episode_to_air,
)

logger = logging.getLogger(__name__)


class Shows:
    """L'émission due à l'antenne, et l'adresse audio à ouvrir pour la diffuser."""

    def __init__(
        self,
        programme: ShowSchedule,
        feed: PodcastFeed,
        state: SqliteState,
        clock: Clock,
        addresses: dict[str, tuple[str, ...]],
        random: Random,
        streams: dict[str, str] | None = None,
        youtube_channels: dict[str, str] | None = None,
        youtube: YoutubeChannel | None = None,
        youtube_cache: Path | None = None,
        in_background: Callable[[Callable[[], None]], None] | None = None,
        preload: timedelta | None = None,
    ) -> None:
        self._programme = programme
        self._flux = feed
        self._etat = state
        self._horloge = clock
        # Un nom d'émission vers ses flux. Une émission ordinaire en a un ;
        # une plage podcasts en a plusieurs, et tire lequel à chaque jonction
        # (SPECS.md §7 n°35).
        self._adresses = addresses
        self._hasard = random
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
        # Où lire les flux, et combien de temps avant l'ouverture d'une case.
        # `None` lit sur place, ce qui garde les tests déterministes ; la
        # production passe un fil, pour que le diffuseur n'attende jamais un
        # hébergeur (SPECS.md §4.11, GOAL-080).
        self._en_fond = in_background
        self._avance_de_lecture = preload
        self._lectures_lancees: set[str] = set()
        self._verrou_lectures = threading.Lock()

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
            for name, par_flux in catalogues.items()
            for episodes in [next(iter(par_flux.values()), [])]
            if episodes and episodes[0].duration is not None
        }
        case = self._programme.due(durations, instant)
        if case is None:
            return None
        if case.show.is_live:
            return self._direct_de(case, instant)
        par_flux = catalogues.get(case.show.name, {})
        if case.show.name in self._youtube:
            return self._video_de(case.show, next(iter(par_flux.values()), []))
        return self._episode_de(case.show, par_flux)

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

    def _catalogues(self, instant: object) -> dict[str, dict[str, list[EpisodeDuFlux]]]:
        """Lit les flux des émissions dont une case a pu commencer.

        On lit avant de savoir si on s'en servira : sans la durée, on ne peut
        pas dire si la case est encore ouverte (décision n°13). **Sauf une
        plage**, qui déclare sa fin : celle-là se sait fermée sans qu'on lise
        rien. Sans ce contrôle, ses flux étaient lus jusqu'à la veille de
        l'occurrence suivante — pour les six de l'auteur, deux jours par
        semaine au lieu de trois heures.

        Un catalogue **par flux**, pas par émission : une plage podcasts en a
        plusieurs et doit savoir lequel offre quoi.
        """
        catalogues: dict[str, dict[str, list[EpisodeDuFlux]]] = {}
        for show in self._programme.shows:
            if show.is_live:
                continue
            if self._programme.slot_start(show, instant) is None:  # type: ignore[arg-type]
                self._prechauffer(show, instant)  # type: ignore[arg-type]
                continue
            if show.chains_episodes and self._programme.open_slot(show, None, instant) is None:  # type: ignore[arg-type]
                continue
            chaine = self._youtube.get(show.name)
            if chaine is not None and self._youtube_adapter is not None:
                try:
                    catalogues[show.name] = {chaine: self._youtube_adapter.episodes(chaine)}
                except YoutubeUnavailable as failure:
                    logger.warning(
                        "chaîne YouTube de « %s » injoignable, case sautée : %s",
                        show.name,
                        failure,
                    )
                continue
            for address in self._adresses.get(show.name, ()):
                episodes = self._episodes_de(address, show.name)
                if episodes is not None:
                    catalogues.setdefault(show.name, {})[address] = episodes
        return catalogues

    def _prechauffer(self, show: Show, instant: datetime) -> None:
        """Lit les flux d'une case sur le point de s'ouvrir, pour qu'elle
        commence à l'heure plutôt qu'à la jonction d'après.

        L'avance est celle du cache : lire plus tôt ne servirait à rien, la
        garde aurait expiré (SPECS.md §6).
        """
        en_fond = self._en_fond
        if en_fond is None or self._avance_de_lecture is None:
            return
        if not self._programme.opens_within(show, instant, self._avance_de_lecture):
            return
        for address in self._adresses.get(show.name, ()):
            if self._flux.cached(address) is None:
                self._lire_en_fond(address, show.name, en_fond)

    def _episodes_de(self, address: str, show_name: str) -> list[EpisodeDuFlux] | None:
        """Le catalogue de ce flux, sans jamais attendre le réseau quand un fil
        de fond est disponible.

        Le diffuseur abandonne une requête au bout de son propre délai et coupe
        au deuxième échec (docs/liquidsoap.md §3) : trois flux lus l'un après
        l'autre le dépassaient (docs/podcast.md §4.bis). La lecture part donc en
        tâche de fond, et la case attend la jonction suivante plutôt que
        l'hébergeur.
        """
        en_fond = self._en_fond
        if en_fond is None:
            return self._lire(address, show_name)
        connu = self._flux.cached(address)
        if connu is not None:
            return connu
        self._lire_en_fond(address, show_name, en_fond)
        # Le catalogue périmé, le temps que la relecture aboutisse : la garde
        # expire au milieu d'un épisode long, et sans cela un morceau de
        # musique s'intercalait entre chaque épisode d'une plage.
        return self._flux.cached(address, stale_ok=True)

    def _lire(self, address: str, show_name: str) -> list[EpisodeDuFlux] | None:
        try:
            return self._flux.episodes(address)
        except PodcastUnavailable as failure:
            # Un flux muet ne prive pas les autres : une plage tire parmi ceux
            # qui ont répondu (SPECS.md §7 n°35).
            logger.warning(
                "flux « %s » de « %s » injoignable : %s",
                address.split("?", 1)[0],
                show_name,
                failure,
            )
            return None

    def _lire_en_fond(
        self, address: str, show_name: str, en_fond: Callable[[Callable[[], None]], None]
    ) -> None:
        """Une lecture à la fois par flux.

        Le fil de fond est unique et partagé : plusieurs flux muets y attendent
        chacun leur délai, et sans ce témoin chaque jonction en empilerait une
        de plus sur la file.
        """
        with self._verrou_lectures:
            if address in self._lectures_lancees:
                return
            self._lectures_lancees.add(address)

        def au_travail() -> None:
            try:
                self._lire(address, show_name)
            finally:
                with self._verrou_lectures:
                    self._lectures_lancees.discard(address)

        en_fond(au_travail)

    def _episode_de(
        self, show: Show, par_flux: dict[str, list[EpisodeDuFlux]]
    ) -> tuple[Show, str, str | None] | None:
        """L'épisode à diffuser, tiré parmi les flux qui ont du neuf.

        La mémoire est **par flux**, pas par émission : une plage en a
        plusieurs, et ce qu'elle a déjà passé de l'un ne dit rien de l'autre
        (SPECS.md §7 n°35). D'où la clé `<émission>/<flux>` dès qu'il y en a
        plusieurs ; une émission à flux unique garde le nom seul.
        """
        if not par_flux:
            return None
        catalogues: dict[str, list[Episode]] = {}
        deja: dict[str, str] = {}
        for address, episodes in par_flux.items():
            if not episodes:
                continue
            try:
                passe = self._etat.last_airing(self._cle_de_memoire(show, address))
            except StateUnavailable as failure:
                # Sans mémoire, on rediffuserait le même épisode en boucle.
                # Sauter la case est moins gênant (SPECS.md §4.11).
                logger.warning(
                    "mémoire indisponible, émission « %s » sautée : %s", show.name, failure
                )
                return None
            if passe is not None:
                deja[address] = passe.episode
            catalogues[address] = [
                Episode(
                    guid=e.identifier,
                    published_at=e.published_at,
                    duration=e.duration if e.duration is not None else timedelta(0),
                    kind="full",
                )
                for e in episodes
            ]
        tire = episode_among(catalogues, deja, self._hasard)
        if tire is None:
            logger.info("« %s » n'a rien de neuf : la case est sautée", show.name)
            return None
        address, choisi = tire
        catalogue = par_flux[address]
        if len(par_flux) > 1:
            logger.info(
                "« %s » tire le flux %s", show.name, address.split("?", 1)[0].rsplit("/", 1)[-1]
            )
        audio = next(e.audio for e in catalogue if e.identifier == choisi.guid)
        titre = next((e.title for e in catalogue if e.identifier == choisi.guid), None)
        try:
            self._etat.record_airing(self._cle_de_memoire(show, address), choisi.guid)
        except StateUnavailable as failure:
            logger.warning("diffusion non retenue, elle se rejouera : %s", failure)
        return show, audio, titre

    def _cle_de_memoire(self, show: Show, address: str) -> str:
        """Ce sous quoi la base retient une diffusion (ARCHITECTURE.md §5).

        Le nom seul quand l'émission n'a qu'un flux — c'est la clé historique,
        et la changer ferait rejouer une fois le dernier épisode de chaque
        émission au déploiement. `<émission>/<flux>` dès qu'il y en a
        plusieurs : chacun a sa propre notion de « déjà passé ».
        """
        if len(self._adresses.get(show.name, ())) <= 1:
            return show.name
        return f"{show.name}/{address}"
