"""Flask, l'API et les gabarits Jinja2 (ARCHITECTURE.md §6).

C'est le **seul** dossier du dépôt où `flask` et `jinja2` ont le droit d'être
importés — un interdit contrôlé par `verifier.sh` (AGENTS.md §2).
"""

from webradio.adapters.web.api import (
    Antenne,
    Nature,
    Radio,
    Verdict,
    Vote,
    creer_api,
)
from webradio.adapters.web.views import creer_application, creer_vue

__all__ = [
    "Antenne",
    "Nature",
    "Radio",
    "Verdict",
    "Vote",
    "creer_api",
    "creer_application",
    "creer_vue",
]
