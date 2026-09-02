"""Flask, l'API et les gabarits Jinja2 (ARCHITECTURE.md §6).

Seul dossier du dépôt où `flask` et `jinja2` peuvent être importés ; c'est
contrôlé par `verifier.sh` (AGENTS.md §2).
"""

from webradio.adapters.web.api import (
    Kind,
    OnAir,
    Radio,
    UpcomingEntry,
    Verdict,
    Vote,
    create_api,
)
from webradio.adapters.web.playout_api import Playout, create_playout_api
from webradio.adapters.web.views import create_app, create_view

__all__ = [
    "Kind",
    "OnAir",
    "Playout",
    "Radio",
    "UpcomingEntry",
    "Verdict",
    "Vote",
    "create_api",
    "create_app",
    "create_playout_api",
    "create_view",
]
