"""Ce que le noyau manipule.

Rien ici ne connaît Navidrome, Subsonic, HTTP ni ffmpeg : ces détails restent
confinés dans leurs adaptateurs (ARCHITECTURE.md §2.1). Une piste est ce qu'il
faut pour décider — un artiste, un genre, une durée — plus un identifiant que
seule la source sait résoudre.
"""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class Track:
    """Un morceau, tel que le noyau a besoin de le connaître.

    `identifiant` est opaque : le noyau ne l'interprète jamais, il le rend à la
    source qui l'a produit. C'est ce qui permet à une source d'utiliser des
    identifiants Subsonic hexadécimaux sans que rien au-dessus ne le sache.
    """

    identifier: str
    title: str
    artist: str
    genre: str | None
    duration: timedelta

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
