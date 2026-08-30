"""La seule persistance du projet (ARCHITECTURE.md §5).

Deux tables, et pas une de plus : le dernier épisode diffusé de chaque émission,
et les scores de vote. La garde d'ARCHITECTURE.md §5.0 reste en vigueur pour la
troisième — elle n'arrive qu'avec une décision écrite.
"""

from webradio.adapters.state.database import (
    Broadcast,
    Scope,
    Scores,
    SqliteState,
    StateUnavailable,
)

__all__ = ["Broadcast", "Scope", "Scores", "SqliteState", "StateUnavailable"]
