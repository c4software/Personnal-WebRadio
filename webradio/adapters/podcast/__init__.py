"""Les flux de podcast des émissions (SPECS.md §4.11).

Le format RSS, ses `enclosure` et ses redirections restent confinés ici
(ARCHITECTURE.md §2.1) : au-dessus, le noyau ne connaît qu'un `Episode`.
"""

from webradio.adapters.podcast.feed import (
    Episode,
    FluxPodcast,
    LecteurHttp,
    LecteurUrllib,
    PodcastIndisponible,
)

__all__ = [
    "Episode",
    "FluxPodcast",
    "LecteurHttp",
    "LecteurUrllib",
    "PodcastIndisponible",
]
