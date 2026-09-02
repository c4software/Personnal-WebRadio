"""Ce que le noyau manipule.

Rien ici ne connaît Navidrome, Subsonic, HTTP ni ffmpeg (ARCHITECTURE.md §2.1).
Une piste est ce qu'il faut pour décider, plus un identifiant que seule la
source sait résoudre.
"""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class Track:
    """Un morceau, tel que le noyau a besoin de le connaître.

    `identifier` est opaque : le noyau ne l'interprète jamais, il le rend à la
    source qui l'a produit.
    """

    identifier: str
    title: str
    artist: str
    genre: str | None
    duration: timedelta
    # L'année, quand la bibliothèque la connaît (docs/subsonic.md §4.1). Une
    # piste sans année reste valable, elle ne participe pas aux suites d'époque
    # (GOAL-044).
    year: int | None = None

    def __post_init__(self) -> None:
        if not self.identifier:
            message = "une piste sans identifiant ne peut pas être résolue par sa source"
            raise ValueError(message)
        if not self.artist:
            message = "une piste sans artiste rendrait la non-répétition inapplicable"
            raise ValueError(message)
        if self.duration <= timedelta(0):
            message = f"durée non valable pour « {self.title} » : {self.duration}"
            raise ValueError(message)
