"""Flask, l'API et les gabarits Jinja2 (ARCHITECTURE.md §6).

C'est le **seul** dossier du dépôt où `flask` et `jinja2` ont le droit d'être
importés — un interdit contrôlé par `verifier.sh` (AGENTS.md §2).
"""

from webradio.adapters.web.api import (
    Kind,
    OnAir,
    Radio,
    Verdict,
    Vote,
    create_api,
)
from webradio.adapters.web.views import create_app, create_view

__all__ = [
    "Kind",
    "OnAir",
    "Radio",
    "Verdict",
    "Vote",
    "create_api",
    "create_app",
    "create_view",
]
