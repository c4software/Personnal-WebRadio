"""La seule persistance du projet (ARCHITECTURE.md §5).

Trois tables : le dernier épisode diffusé de chaque émission, le journal des
titres sur vingt-quatre heures et les scores de vote. Toute table de plus
demande une décision écrite (ARCHITECTURE.md §5.0).
"""

from webradio.adapters.state.database import (
    Broadcast,
    Scope,
    Scores,
    SqliteState,
    StateUnavailable,
)

__all__ = ["Broadcast", "Scope", "Scores", "SqliteState", "StateUnavailable"]
