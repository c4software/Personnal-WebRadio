"""D'où vient la musique.

Ce dossier confine **l'API Subsonic** — le sel, le jeton, `u`, `v`, `c`, et la
forme des réponses (ARCHITECTURE.md §2.1). Au-dessus de lui, plus personne ne
connaît de code HTTP : le noyau ne voit que des `Piste` et, en cas de panne, une
`SourceIndisponible`.

**Une seule source est écrite** — Navidrome. Tant qu'il n'y en a qu'une, aucun
code ne doit supposer qu'il y en a plusieurs (SPECS.md §7 n°12).
"""

from webradio.adapters.sources.navidrome import (
    HttpResponse,
    HttpTransport,
    NavidromeSource,
    UrllibTransport,
)

__all__ = ["HttpResponse", "HttpTransport", "NavidromeSource", "UrllibTransport"]
