"""Sources de musique.

Ce dossier confine l'API Subsonic : sel, jeton, paramètres `u`, `v`, `c` et
forme des réponses (ARCHITECTURE.md §2.1). Au-dessus, le noyau ne voit que des
`Track` et, en cas de panne, une `SourceUnavailable`.

Une seule source est écrite, Subsonic, relevée contre Navidrome. Tant qu'il n'y
en a qu'une, aucun code ne doit supposer qu'il y en a plusieurs
(SPECS.md §7 n°12).
"""

from webradio.adapters.sources.subsonic import (
    HttpResponse,
    HttpTransport,
    SubsonicSource,
    UrllibTransport,
)

__all__ = ["HttpResponse", "HttpTransport", "SubsonicSource", "UrllibTransport"]
