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
    # L'année de la piste, quand la bibliothèque la connaît : 6,7 % des pistes
    # réelles n'en ont pas (docs/subsonic.md §4.1), et elles restent valables —
    # elles ne participent simplement pas aux suites d'époque (GOAL-044).
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


def broadcastable(tracks: list[Track], ceiling: timedelta | None) -> list[Track]:
    """Les pistes qui tiennent sous le plafond de durée (SPECS.md §7 n°32).

    La limite exacte passe — « au-delà » est strict — et `None` ne filtre
    rien. Le filtre s'applique partout où une piste se choisit : tirage,
    suites, encore, listes des programmes. Les émissions, elles, ont leur
    propre durée et ne passent pas par ici.
    """
    if ceiling is None:
        return tracks
    return [track for track in tracks if track.duration <= ceiling]
