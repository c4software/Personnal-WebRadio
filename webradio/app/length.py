"""La longueur attendue de ce qui passe.

Elle voyage avec la déclaration, de ce qui choisit l'entrée jusqu'à la façade,
pour que l'antenne sache dire l'écoulé (SPECS.md §4.8, GOAL-085).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Length:
    """Combien de temps ce qui passe doit durer.

    Soit une durée (`duration`), soit une fin absolue (`until`) pour un direct,
    dont la case coupe à l'heure quelle que soit l'heure de la jonction. Les
    deux valent `None` quand rien ne permet de le savoir : une vidéo YouTube,
    un jingle, un épisode dont le flux ne donne pas sa durée.
    """

    duration: timedelta | None = None
    until: datetime | None = None

    def since(self, declared_at: datetime) -> timedelta | None:
        """La durée totale, vue depuis l'instant de déclaration, ou `None`.

        Une fin absolue déjà passée rend une durée nulle plutôt que négative :
        le diffuseur a annoncé le direct après sa fin.
        """
        if self.duration is not None:
            return self.duration
        if self.until is None:
            return None
        return max(self.until - declared_at, timedelta(0))
