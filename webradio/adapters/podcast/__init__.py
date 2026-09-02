"""Les flux de podcast des émissions (SPECS.md §4.11).

Le format RSS, ses `enclosure` et ses redirections restent confinés ici
(ARCHITECTURE.md §2.1). Le noyau ne connaît qu'un `Episode`.
"""

from webradio.adapters.podcast.feed import (
    Episode,
    HttpReader,
    PodcastFeed,
    PodcastUnavailable,
    UrllibReader,
)

__all__ = [
    "Episode",
    "HttpReader",
    "PodcastFeed",
    "PodcastUnavailable",
    "UrllibReader",
]
