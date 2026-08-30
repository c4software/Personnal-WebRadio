"""Le point d'entrée, et le seul endroit qui connaît tout le monde.

L'assemblage se fait à la main, une fois au démarrage : pas de conteneur, pas de
framework (ARCHITECTURE.md §3). C'est ici — et uniquement ici — que le noyau,
les adaptateurs et la configuration se rencontrent.

Rien de ce fichier ne décide : il construit, il branche, et il attend.
"""

import argparse
import logging
import os
import signal
import sys
import threading
from datetime import timedelta
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version
from pathlib import Path

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import Config
from webradio.adapters.podcast.feed import PodcastFeed, UrllibReader
from webradio.adapters.sources.navidrome import NavidromeSource, UrllibTransport
from webradio.adapters.state.database import Scope as StateScope
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.web.api import VoteScore
from webradio.adapters.web.views import create_app
from webradio.app.learning import Learning
from webradio.app.liquidsoap_playout import LiquidsoapPlayout
from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.app.show_scheduler import Shows
from webradio.core.bands import Band, Schedule
from webradio.core.clock import SystemClock
from webradio.core.control import Control
from webradio.core.jingles import Jingles
from webradio.core.programmes import Programme, Programming
from webradio.core.queue import Queue
from webradio.core.rng import RealRandom
from webradio.core.rotation import Window
from webradio.core.shows import Show, ShowSchedule
from webradio.core.weighting import SLOPE_PER_VOTE

logger = logging.getLogger(__name__)

NAME = "local-webradio"


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
    parser = argparse.ArgumentParser(prog=NAME, description="Une radio qui n'existe que branchée")
    parser.add_argument("--config", type=Path, default=Path("webradio.toml"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    return parser.parse_args(argv)


def build(config: Config) -> tuple[LiquidsoapPlayout, LiveRadio]:
    """Câble le tout, et rend ce que Liquidsoap et l'API interrogent.

    Le flux lui-même n'est pas ici : Liquidsoap l'encode et le sert
    (ARCHITECTURE.md §4), et vient demander quoi jouer par `adapters/web/playout_api.py`.
    """
    settings = config.settings
    clock = SystemClock()
    random = RealRandom()

    # L'état est ouvert au démarrage : une base inaccessible **à ce moment-là**
    # est une erreur de configuration et doit se dire (SPECS.md §5). Devenue
    # inaccessible en cours, elle ne fait que rendre des poids neutres
    # (`app/learning.py`).
    state = SqliteState(
        Path(settings.state.database),
        clock,
        lock_timeout=timedelta(seconds=settings.state.timeout_seconds),
        vote_half_life=timedelta(days=settings.draw.votes.half_life_days),
    )
    learning = Learning(
        state,
        floor=settings.draw.votes.floor,
        ceiling=settings.draw.votes.ceiling,
        slope=SLOPE_PER_VOTE,
        cross_weight=settings.draw.votes.cross_weight,
    )

    source = NavidromeSource(
        credentials=config.credentials,
        config=settings.navidrome,
        random=random,
        transport=UrllibTransport(settings.navidrome.timeout_seconds),
    )
    grille = Schedule(
        [Band(p.start, p.end, p.genres, artists=p.artists, days=p.days) for p in settings.bands],
        clock,
    )
    jingles = Jingles(clock)
    control = Control(source=source, random=random, jingles=jingles)
    counter = ListenerCount()

    def lister_votes() -> "list[VoteScore]":
        try:
            return [
                VoteScore(
                    scope="piste" if scope is StateScope.TRACK else "artiste",
                    target=label,
                    key=key,
                    stop=scores.stop,
                    encore=scores.encore,
                )
                for scope, key, label, scores in state.all_scores()
            ]
        except StateUnavailable as failure:
            logger.warning("votes illisibles, page vide : %s", failure)
            return []

    # Le saut s'ordonne au diffuseur, par la route qu'il enregistre chez lui
    # (`radio.liq`, GOAL-017). L'adresse vient de l'environnement, comme tout
    # le câblage entre services (docker-compose.yml).
    liquidsoap = os.environ.get("LIQUIDSOAP_URL", "http://127.0.0.1:8000")

    def demander_le_saut() -> None:
        import http.client
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(
                urllib.request.Request(f"{liquidsoap}/skip", method="POST"), timeout=3
            ):
                pass
        except (urllib.error.URLError, http.client.HTTPException, OSError) as failure:
            logger.warning("le diffuseur n'a pas pris le saut, le morceau finira : %s", failure)

    programmation = Programming(
        [
            Programme(
                name=p.name,
                playlist=p.playlist,
                days=p.days,
                start=p.start,
                end=p.end,
            )
            for p in settings.programmes
        ],
        clock,
    )

    def moment_courant() -> str | None:
        """Programme d'abord — il l'emporte sur la plage (SPECS.md §4.13)."""
        programme = programmation.current_programme()
        if programme is not None:
            return f"Programme · {programme.name}"
        band = grille.current_band()
        if band is not None:
            return f"Moment · {', '.join(band.artists or band.genres)}"
        return None

    def oublier_le_vote(scope: str, target: str) -> bool:
        try:
            return state.delete_vote(
                StateScope.TRACK if scope == "piste" else StateScope.ARTIST, target
            )
        except StateUnavailable as failure:
            logger.warning("vote non effacé : %s", failure)
            return False

    radio = LiveRadio(
        control,
        counter,
        learning.remember,
        lister_votes,
        demander_le_saut,
        oublier_le_vote,
        moment_courant,
    )
    # Le programme déclare la nature de ce qu'il choisit ; la charnière ne la
    # transmet à la façade que lorsque Liquidsoap commence réellement le morceau.
    branche: list[LiquidsoapPlayout] = []

    programme = RadioProgramme(
        queue=Queue(
            source,
            random,
            Window(settings.draw.artist_gap),
            weigh=learning.weigh,
        ),
        source=source,
        grille=grille,
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=Path(settings.jingles.folder),
        on_kind=lambda kind, track, label: branche[0].on_kind(kind, track, label),
        programming=programmation,
        programme_window=Window(settings.draw.artist_gap),
        shows=Shows(
            ShowSchedule(
                [
                    Show(
                        name=e.name,
                        days=e.days,
                        hour=e.hour,
                        duration=(
                            timedelta(minutes=e.duration_minutes)
                            if e.duration_minutes is not None
                            else None
                        ),
                    )
                    for e in settings.shows
                ]
            ),
            PodcastFeed(
                UrllibReader(lock_timeout=timedelta(seconds=settings.podcast.timeout_seconds))
            ),
            state,
            clock,
            {e.name: e.feed for e in settings.shows if e.feed is not None},
            streams={e.name: e.stream for e in settings.shows if e.stream is not None},
        ),
        control=control,
        now_playing=lambda: radio.playing_track(),
    )

    playout = LiquidsoapPlayout(programme, radio, counter)
    branche.append(playout)
    return playout, radio


def main(argv: list[str] | None = None) -> int:
    """Démarre, sert, et s'arrête proprement sur SIGTERM.

    Rend un code de sortie plutôt que d'appeler `sys.exit` : une fonction qui
    rend une valeur se teste, une fonction qui quitte le processus non.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    options = _arguments(argv)
    logger.info("%s %s", NAME, version())

    config = load(options.config, options.env)
    playout, radio = build(config)
    web = config.settings.web
    s = config.settings
    planning: dict[str, object] = {
        "bands": [
            {
                "start": f"{b.start:%H:%M}",
                "end": f"{b.end:%H:%M}",
                "genres": list(b.artists or b.genres),
                "days": list(b.days),
            }
            for b in s.bands
        ],
        "programmes": [
            {
                "name": p.name,
                "playlist": p.playlist,
                "days": list(p.days),
                "start": f"{p.start:%H:%M}",
                "end": f"{p.end:%H:%M}",
            }
            for p in s.programmes
        ],
        "shows": [
            {
                "name": e.name,
                "days": list(e.days),
                "time": f"{e.hour:%H:%M}",
                "live": e.stream is not None,
                "duration_minutes": e.duration_minutes,
            }
            for e in s.shows
        ],
    }
    app = create_app(
        radio,
        refresh=timedelta(seconds=web.refresh_seconds),
        playout=playout,
        planning=planning,
    )

    shutdown = threading.Event()

    def demander_larret(*_: object) -> None:
        shutdown.set()

    signal.signal(signal.SIGTERM, demander_larret)
    signal.signal(signal.SIGINT, demander_larret)

    web_thread = threading.Thread(
        target=lambda: app.run(host=web.address, port=web.port, threaded=True),
        daemon=True,
    )
    web_thread.start()
    logger.info("interface, API et routes de Liquidsoap sur le port %d", web.port)

    shutdown.wait()
    logger.info("arrêt demandé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
