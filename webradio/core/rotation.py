"""La règle de non-répétition, et ce qu'elle fait quand elle bloque.

SPECS.md §4.2 : un artiste ne revient pas avant que N autres artistes soient
passés. La règle compte des artistes distincts, pas des morceaux.
"""

from dataclasses import dataclass, field

from webradio.core.models import Track

DEFAULT_ARTIST_GAP = 5


@dataclass
class Window:
    """Les derniers artistes joués, du plus récent au plus ancien.

    `width` est le N de SPECS.md §4.2. Une largeur de 0 désactive la règle.
    """

    width: int = DEFAULT_ARTIST_GAP
    _recents: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.width < 0:
            message = "une largeur négative n'a pas de sens : 0 désactive la règle"
            raise ValueError(message)

    @property
    def artists(self) -> tuple[str, ...]:
        return tuple(self._recents)

    def remember(self, track: Track) -> None:
        """Enregistre un passage.

        Rejouer le même artiste ne l'enfonce pas dans la fenêtre : il est déjà
        le plus récent. L'y remettre ferait sortir un artiste de plus à chaque
        titre, alors que la règle compte des artistes, pas des morceaux.
        """
        if track.artist in self._recents:
            self._recents.remove(track.artist)
        self._recents.insert(0, track.artist)
        del self._recents[self.width :]

    def allows(self, track: Track) -> bool:
        return track.artist not in self._recents

    def filter_out(self, tracks: list[Track]) -> list[Track]:
        return [p for p in tracks if self.allows(p)]

    def shrink(self) -> bool:
        """Rétrécit la fenêtre d'un cran. Rend `False` si elle est déjà vide.

        Sur une petite bibliothèque ou une plage étroite, il peut ne rester
        aucun artiste autorisé : la radio relâche la contrainte plutôt que de
        se taire (SPECS.md §4.2).
        """
        if not self._recents:
            return False
        self._recents.pop()
        return True
