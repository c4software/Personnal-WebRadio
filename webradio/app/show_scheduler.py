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
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import PodcastFeed, PodcastUnavailable
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.youtube.channel import YoutubeChannel, YoutubeUnavailable
from webradio.app.length import Length
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


@dataclass(frozen=True, slots=True)
class _Demandee:
    """Une émission rendue au diffuseur, qui n'a pas encore pris l'antenne.

    `airing` porte la clé de mémoire et le guid à inscrire pour un podcast ou
    une vidéo ; `slot` la case à retenir pour un direct. L'un ou l'autre.
    """

    show: str
    entry: str
    airing: tuple[str, str] | None = None
    slot: tuple[str, datetime] | None = None


@dataclass(frozen=True, slots=True)
class PodcastSlot:
    """La case ouverte d'une plage de podcasts, telle qu'elle date l'avance.

    `awaited` dit qu'un épisode de cette case est demandé sans avoir commencé :
    c'est ce qui fait changer la clé à sa prise d'antenne (décision n°43).
    """

    show: str
    start: datetime
    awaited: bool


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
        self._telechargements: set[str] = set()
        self._verrou_telechargements = threading.Lock()
        self._cases_rendues: set[tuple[str, datetime]] = set()
        # Ce qui a été rendu au diffuseur sans avoir encore commencé. Rien ne
        # s'inscrit avant `started()` : l'entrée n'est que l'avance du
        # diffuseur, et une purge peut la jeter (SPECS.md §4.11.1).
        self._demandee: _Demandee | None = None
        # Où lire les flux, et combien de temps avant l'ouverture d'une case.
        # `None` lit sur place, ce qui garde les tests déterministes ; la
        # production passe un fil, pour que le diffuseur n'attende jamais un
        # hébergeur (SPECS.md §4.11, GOAL-080).
        self._en_fond = in_background
        self._avance_de_lecture = preload
        self._lectures_lancees: set[str] = set()
        self._verrou_lectures = threading.Lock()

    def due(self) -> tuple[Show, str, str | None, Length, bool] | None:
        """L'émission due, l'adresse de son épisode, son titre, sa longueur et
        si elle se passe.

        Le titre (vidéo ou épisode) sert à l'antenne et au journal (GOAL-027) ;
        il vaut `None` s'il n'y en a pas. La longueur est la durée de l'épisode
        quand le flux la donne, la fin de la case pour un direct, et rien
        sinon (GOAL-085). Le dernier champ dit qu'un « Passer » a de quoi
        piocher : seul un épisode de plage l'a (SPECS.md §7 n°44).

        Rend `None` quand il n'y a pas d'émission : aucune case ouverte, flux
        injoignable, épisode déjà diffusé. Aucun de ces cas n'est une panne,
        la radio reste sur la musique (SPECS.md §4.11).
        """
        # Une émission déjà rendue attend son tour : le diffuseur peut
        # redemander avant de l'avoir commencée (docs/liquidsoap.md §3), et la
        # rendre deux fois la ferait passer deux fois.
        if self._demandee is not None:
            return None
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
            return self._direct_de(case)
        par_flux = catalogues.get(case.show.name, {})
        if case.show.name in self._youtube:
            return self._video_de(case.show, next(iter(par_flux.values()), []))
        return self._episode_de(case.show, par_flux)

    def open_band_slot(self) -> PodcastSlot | None:
        """La case ouverte d'une plage de podcasts, ou `None`.

        Elle entre dans la clé qui date l'avance (décision n°43, qui étend la
        n°33) : sans elle, la clé ne connaît que les plages et les programmes,
        et une musique tirée à 20 h 01 restait à l'antenne jusqu'à la fin de la
        plage musicale, par-dessus les cases de podcasts ouvertes entre-temps.

        Rien n'est lu ici : une plage déclare sa fin, sa case se connaît sans
        catalogue et sans réseau. Deux cases ouvertes, la première commencée
        l'emporte, comme dans `ShowSchedule.due`.
        """
        instant = self._horloge.now()
        ouvertes = [
            case
            for show in self._programme.shows
            if show.chains_episodes
            for case in [self._programme.open_slot(show, None, instant)]
            if case is not None
        ]
        if not ouvertes:
            return None
        case = min(ouvertes, key=lambda c: c.start)
        demandee = self._demandee is not None and self._demandee.show == case.show.name
        return PodcastSlot(show=case.show.name, start=case.start, awaited=demandee)

    def has_another_episode(self) -> bool:
        """Reste-t-il un épisode neuf à piocher dans la plage ouverte ?

        Lu au moment du vote, pour que le refus dise l'état d'aujourd'hui et
        non celui d'il y a une heure (SPECS.md §7 n°44). Rien n'est demandé au
        réseau : les catalogues sont ceux du cache, périmés acceptés, et le
        hasard n'est pas consommé — on compte les flux qui ont du neuf, on ne
        tire pas lequel. L'épisode à l'antenne est déjà inscrit comme diffusé
        (`started`), donc son flux ne compte plus s'il n'a que celui-là.
        """
        ouverte = self.open_band_slot()
        if ouverte is None:
            return False
        show = next((s for s in self._programme.shows if s.name == ouverte.show), None)
        if show is None:
            return False
        connus = 0
        for address in self._adresses.get(show.name, ()):
            episodes = self._flux.cached(address, stale_ok=True)
            if not episodes:
                continue
            connus += 1
            try:
                passe = self._etat.last_airing(self._cle_de_memoire(show, address))
            except StateUnavailable as failure:
                logger.warning("mémoire indisponible, on ne pioche pas : %s", failure)
                return False
            candidats = [
                Episode(
                    guid=e.identifier,
                    published_at=e.published_at,
                    duration=e.duration if e.duration is not None else timedelta(0),
                    kind="full",
                )
                for e in episodes
            ]
            if episode_to_air(candidats, passe.episode if passe is not None else None) is not None:
                return True
        if connus == 0:
            # Sans `podcast.cache_seconds`, rien n'est gardé et la seule façon
            # de savoir serait de relire les flux, ce que le vote ne peut pas
            # attendre. On refuse alors de piocher.
            logger.info("« %s » : aucun catalogue en cache, on ne pioche pas", show.name)
        return False

    def _direct_de(self, case: Slot) -> tuple[Show, str, str | None, Length, bool] | None:
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
        entry = f"live:{int(case.end.timestamp())}:{url}"
        self._demandee = _Demandee(show=case.show.name, entry=entry, slot=cle)
        logger.info(
            "direct « %s » jusqu'à %s — %s",
            case.show.name,
            case.end.astimezone().strftime("%H:%M:%S"),
            url.split("?", 1)[0],
        )
        return case.show, entry, None, Length(until=case.end), False

    def started(self, entry: str) -> None:
        """Inscrit la diffusion de l'entrée que le diffuseur vient de commencer.

        Rien ne s'inscrit à la demande : l'entrée rendue n'est que l'avance du
        diffuseur (docs/liquidsoap.md §3), et une purge peut la jeter sans
        l'avoir jouée. L'épisode resterait « diffusé » sans avoir passé, perdu
        jusqu'à la publication du suivant (SPECS.md §4.11.1).

        Une entrée qui n'est pas celle attendue ne fait rien : c'est à
        l'appelant de dire qu'une émission a été jetée (`dropped`).
        """
        demandee = self._demandee
        if demandee is None or demandee.entry != entry:
            return
        self._demandee = None
        if demandee.slot is not None:
            limite = self._horloge.now() - timedelta(days=2)
            self._cases_rendues = {c for c in self._cases_rendues if c[1] > limite}
            self._cases_rendues.add(demandee.slot)
        if demandee.airing is not None:
            key, episode = demandee.airing
            try:
                self._etat.record_airing(key, episode)
            except StateUnavailable as failure:
                logger.warning("diffusion non retenue, elle se rejouera : %s", failure)

    def dropped(self) -> None:
        """Oublie l'émission demandée qui n'a pas pris l'antenne.

        Une purge de l'avance (SPECS.md §7 n°22, n°30) ou une adresse que le
        diffuseur n'arrive pas à ouvrir la jettent. Rien n'ayant été inscrit,
        la case peut la redemander tant que sa fenêtre de rattrapage est
        ouverte (SPECS.md §4.11).
        """
        demandee, self._demandee = self._demandee, None
        if demandee is None:
            return
        logger.info("« %s » n'a pas pris l'antenne : elle reste à diffuser", demandee.show)

    @staticmethod
    def _nom_de_cache(show_name: str) -> str:
        """Un nom de fichier stable par émission : chaque téléchargement écrase
        le précédent, rien ne s'accumule (GOAL-028). Le fichier `.id` à côté
        dit quelle vidéo c'est."""
        return re.sub(r"[^a-z0-9]+", "-", show_name.lower()).strip("-") or "emission"

    def _video_de(
        self, show: Show, catalogue: list[EpisodeDuFlux]
    ) -> tuple[Show, str, str | None, Length, bool] | None:
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
            self._demandee = _Demandee(
                show=show.name, entry=str(fichier), airing=(show.name, chosen.guid)
            )
            titre = next((e.title for e in catalogue if e.identifier == chosen.guid), None)
            # La longueur reste inconnue : le fichier servi est celui du cache,
            # et sa durée n'est pas relue ici (GOAL-085).
            return show, str(fichier), titre, Length(), False
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
        pas dire si la case est encore ouverte (décision n°13). Sauf une plage,
        qui déclare sa fin : celle-là se sait fermée sans qu'on lise rien. Sans
        ce contrôle, ses flux étaient lus jusqu'à la veille de l'occurrence
        suivante.

        Un catalogue par flux, pas par émission : une plage podcasts en a
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
                videos = self._videos_de(chaine, show.name)
                if videos is not None:
                    catalogues[show.name] = {chaine: videos}
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
        chaine = self._youtube.get(show.name)
        if chaine is not None and self._youtube_adapter is not None:
            if self._youtube_adapter.cached(chaine) is None:
                self._en_fond_une_fois(
                    chaine, lambda: self._lire_la_chaine(chaine, show.name), en_fond
                )
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

    def _videos_de(self, chaine: str, show_name: str) -> list[EpisodeDuFlux] | None:
        """Le catalogue d'une chaîne, sans attendre le réseau quand un fil de
        fond est disponible.

        Lire une chaîne enchaîne un flux Atom et une résolution `yt-dlp`,
        chacune bornée par `youtube.timeout_seconds` : bien au-delà de ce que le
        diffuseur attend (SPECS.md §4.11). Même traitement que les podcasts.
        """
        adaptateur = self._youtube_adapter
        if adaptateur is None:
            return None
        en_fond = self._en_fond
        if en_fond is None:
            return self._lire_la_chaine(chaine, show_name)
        connu = adaptateur.cached(chaine)
        if connu is not None:
            return connu
        self._en_fond_une_fois(chaine, lambda: self._lire_la_chaine(chaine, show_name), en_fond)
        return adaptateur.cached(chaine, stale_ok=True)

    def _lire_la_chaine(self, chaine: str, show_name: str) -> list[EpisodeDuFlux] | None:
        if self._youtube_adapter is None:
            return None
        try:
            return self._youtube_adapter.episodes(chaine)
        except YoutubeUnavailable as failure:
            logger.warning(
                "chaîne YouTube de « %s » injoignable, case sautée : %s", show_name, failure
            )
            return None

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
        self._en_fond_une_fois(address, lambda: self._lire(address, show_name), en_fond)

    def _en_fond_une_fois(
        self,
        adresse: str,
        travail: Callable[[], object],
        en_fond: Callable[[Callable[[], None]], None],
    ) -> None:
        """Lance `travail` en fond, une seule fois par adresse à la fois.

        Le fil de fond est unique et partagé : plusieurs sources muettes y
        attendent chacune son délai, et sans ce témoin chaque jonction en
        empilerait une de plus sur la file.
        """
        with self._verrou_lectures:
            if adresse in self._lectures_lancees:
                return
            self._lectures_lancees.add(adresse)

        def au_travail() -> None:
            try:
                travail()
            finally:
                with self._verrou_lectures:
                    self._lectures_lancees.discard(adresse)

        en_fond(au_travail)

    def _episode_de(
        self, show: Show, par_flux: dict[str, list[EpisodeDuFlux]]
    ) -> tuple[Show, str, str | None, Length, bool] | None:
        """L'épisode à diffuser, tiré parmi les flux qui ont du neuf.

        La mémoire est par flux, pas par émission : une plage en a plusieurs, et
        ce qu'elle a déjà passé de l'un ne dit rien de l'autre (SPECS.md §7
        n°35). D'où la clé `<émission>/<flux>` dès qu'il y en a plusieurs ; une
        émission à flux unique garde le nom seul.
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
        self._demandee = _Demandee(
            show=show.name,
            entry=audio,
            airing=(self._cle_de_memoire(show, address), choisi.guid),
        )
        # La durée qu'un flux ne donne pas est remplacée par zéro plus haut :
        # la longueur reste alors inconnue (docs/podcast.md §1, GOAL-085).
        duree = choisi.duration if choisi.duration > timedelta(0) else None
        return show, audio, titre, Length(duration=duree), show.chains_episodes

    def _cle_de_memoire(self, show: Show, address: str) -> str:
        """Ce sous quoi la base retient une diffusion (ARCHITECTURE.md §5).

        Le nom seul quand l'émission n'a qu'un flux : c'est la clé historique,
        et la changer ferait rejouer une fois le dernier épisode de chaque
        émission au déploiement. `<émission>/<flux>` dès qu'il y en a plusieurs,
        chacun ayant sa propre notion de déjà passé.
        """
        if len(self._adresses.get(show.name, ())) <= 1:
            return show.name
        return f"{show.name}/{address}"
