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

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import Config
from webradio.adapters.ffmpeg.encoder import Chain, StreamFormat
from webradio.adapters.http.broadcast import Broadcast
from webradio.adapters.http.server import Station, StreamServer
from webradio.adapters.podcast.feed import PodcastFeed, UrllibReader
from webradio.adapters.sources.navidrome import NavidromeSource, UrllibTransport
from webradio.adapters.state.database import SqliteState
from webradio.adapters.web.views import create_app
from webradio.app.learning import Learning
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
STREAM_PATH = "/flux"


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


def build(config: Config) -> tuple[StreamServer, LiveRadio, Station]:
    """Câble le tout, et rend ce qu'il faut pour le lancer et l'observer."""
    settings = config.settings
    clock = SystemClock()
    random = RealRandom()

    # L'état est ouvert au démarrage : une base inaccessible **à ce moment-là**
    # est une erreur de configuration et doit se dire (SPECS.md §5). Devenue
    # inaccessible en cours, elle ne fait que rendre des poids neutres
    # (`app/apprentissage.py`).
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
        [Band(p.start, p.end, p.genres) for p in settings.bands],
        clock,
    )
    jingles = Jingles(clock)
    control = Control(source=source, random=random, jingles=jingles)
    counter = ListenerCount()
    radio = LiveRadio(control, counter, learning.remember)

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
        on_kind=radio.declare,
        programming=Programming(
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
        ),
        programme_window=Window(settings.draw.artist_gap),
        shows=Shows(
            ShowSchedule([Show(name=e.name, days=e.days, hour=e.hour) for e in settings.shows]),
            PodcastFeed(
                UrllibReader(lock_timeout=timedelta(seconds=settings.podcast.timeout_seconds))
            ),
            state,
            clock,
            {e.name: e.feed for e in settings.shows},
        ),
    )

    stream_format = StreamFormat(
        container=settings.feed.format,
        bitrate_kbps=settings.feed.bitrate_kbps,
        sample_rate_hz=settings.feed.sample_rate_hz,
        channels=settings.feed.channels,
    )
    station = Station(_fabrique_de_chaine(programme, stream_format, counter))
    server = StreamServer(
        station,
        stream_format,
        address=settings.feed.address,
        port=settings.feed.port,
        path=STREAM_PATH,
        name=NAME,
    )
    return server, radio, station


def _fabrique_de_chaine(
    programme: RadioProgramme,
    stream_format: StreamFormat,
    counter: ListenerCount,
) -> Callable[[Broadcast], Chain]:
    """Rend de quoi construire une chaîne, en tenant le compteur à jour.

    Le compteur existe pour que l'API sache si quelqu'un écoute **sans rien
    connaître du serveur** (`app/radio.py`) : c'est la seule information que la
    façade a besoin de recevoir d'en bas.
    """

    def build_chain(broadcast: Broadcast) -> Chain:
        counter.declare(on_air=True)

        def end(reason: str) -> None:
            counter.declare(on_air=False)
            logger.warning("la chaîne s'arrête : %s", reason)

        return Chain(programme, stream_format, broadcast.publish, end)

    return build_chain


def main(argv: list[str] | None = None) -> int:
    """Démarre, sert, et s'arrête proprement sur SIGTERM.

    Rend un code de sortie plutôt que d'appeler `sys.exit` : une fonction qui
    rend une valeur se teste, une fonction qui quitte le processus non.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    options = _arguments(argv)
    logger.info("%s %s", NAME, version())

    config = load(options.config, options.env)
    server, radio, _ = build(config)
    web = config.settings.web
    app = create_app(
        radio,
        refresh=timedelta(seconds=web.refresh_seconds),
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
    server.start()
    logger.info("flux sur %s, interface sur le port %d", STREAM_PATH, web.port)

    shutdown.wait()
    logger.info("arrêt demandé")
    server.stop_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
