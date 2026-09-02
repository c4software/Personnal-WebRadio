"""Les suites d'une plage : double dose, passionné d'époque, passionné d'artiste.

Une plage peut demander que ses tirages s'enchaînent (SPECS.md §4.4, décision
n°31) : le premier morceau tiré pose une ancre, son artiste ou sa décennie, et
les tirages suivants s'y tiennent pendant une suite dont la longueur est tirée
par le hasard injecté. Ce module ne cherche aucune musique : il dit au tirage ce
que la suite en cours impose et observe ce qui a été tiré. `core/queue.py`
filtre, journalise les ruptures et tire.

Deux cas limites :

- une piste sans année ne pose pas d'ancre d'époque (docs/subsonic.md §4.1) et
  le tirage reste un tirage simple ;
- le même titre ne repasse jamais dans une même suite : une décennie maigre
  croisée avec une plage étroite se rompt plutôt que de boucler.
"""

from dataclasses import dataclass
from enum import Enum

from webradio.core.models import Track
from webradio.core.rng import Random


class Mode(Enum):
    """Ce qu'une plage peut demander d'enchaîner."""

    DOUBLE_DOSE = "double_dose"
    ERA_FAN = "era_fan"
    ARTIST_FAN = "artist_fan"


# Bornes inclusives des longueurs de suite (décision n°31). La longueur se tire
# par `pick` sur l'étendue : rien de plus n'est demandé au hasard, et une suite
# se rejoue à graine fixée.
RUN_SPANS: dict[Mode, tuple[int, int]] = {
    Mode.DOUBLE_DOSE: (2, 2),
    Mode.ERA_FAN: (2, 6),
    Mode.ARTIST_FAN: (3, 6),
}


def era_of(track: Track) -> int | None:
    """La décennie d'une piste datée (1977 donne 1970), `None` sans année."""
    if track.year is None:
        return None
    return track.year // 10 * 10


@dataclass(frozen=True, slots=True)
class Directive:
    """Ce que la suite en cours impose au prochain tirage."""

    artist: str | None = None
    era: int | None = None
    exclude: frozenset[str] = frozenset()
    # L'ancre à éviter pour la suite qui s'ouvre, après une rupture sur demande
    # (GOAL-059).
    avoid_artist: str | None = None
    avoid_era: int | None = None
    # Une suite d'artiste répète l'artiste par construction : elle outrepasse la
    # fenêtre de non-répétition, comme l'encore (SPECS.md §4.6). Une suite
    # d'époque varie les artistes, la fenêtre s'applique.
    bypass_window: bool = False


class Runs:
    """La suite en cours, et ce qu'elle impose.

    Remise à zéro quand la contrainte de plage change : deux tirages de la même
    plage la partagent, un changement de plage ou le tirage libre la change. Un
    thème au hasard est figé sur l'occurrence (`core/mystery.py`) et donne la
    même contrainte toute la soirée.
    """

    def __init__(self, random: Random) -> None:
        self._hasard = random
        self._base: object = None
        self._mode: Mode | None = None
        self._anchor_artist: str | None = None
        self._anchor_era: int | None = None
        self._remaining = 0
        self._played: set[str] = set()
        self._avoid_artist: str | None = None
        self._avoid_era: int | None = None

    def break_run(self) -> bool:
        """Rompt la suite en cours ; la prochaine ancre évitera la sienne (GOAL-059).

        Rend `False` hors mode ou en double dose, dont l'artiste n'est pas une
        ancre tirée pour durer.
        """
        if self._mode not in (Mode.ERA_FAN, Mode.ARTIST_FAN):
            return False
        self._avoid_artist, self._avoid_era = self._anchor_artist, self._anchor_era
        self._remaining = 0
        self._played = set()
        return True

    def directive(self, constraint: object, mode: Mode | None) -> Directive | None:
        """Ce que le prochain tirage doit respecter, ou `None` pour un tirage d'ancre."""
        self._rebase(constraint, mode)
        if self._mode is None:
            return None
        if self._remaining <= 0:
            if self._avoid_artist is None and self._avoid_era is None:
                return None
            return Directive(avoid_artist=self._avoid_artist, avoid_era=self._avoid_era)
        if self._mode is Mode.ERA_FAN:
            return Directive(era=self._anchor_era, exclude=frozenset(self._played))
        return Directive(
            artist=self._anchor_artist, exclude=frozenset(self._played), bypass_window=True
        )

    def observe(self, constraint: object, mode: Mode | None, track: Track) -> None:
        """Enregistre le tirage : la suite avance, ou une nouvelle s'ouvre.

        Un morceau qui ne colle pas à l'ancre (le tirage a dû rompre la suite,
        faute de candidats) devient la nouvelle ancre.
        """
        self._rebase(constraint, mode)
        if self._mode is None:
            return
        if self._remaining > 0 and self._matches(track):
            self._remaining -= 1
            self._played.add(track.identifier)
            return
        self._start(self._mode, track)

    def _rebase(self, constraint: object, mode: Mode | None) -> None:
        if constraint == self._base and mode is self._mode:
            return
        self._base = constraint
        self._mode = mode
        self._anchor_artist = None
        self._anchor_era = None
        self._remaining = 0
        self._played = set()
        self._avoid_artist = None
        self._avoid_era = None

    def _matches(self, track: Track) -> bool:
        if self._mode is Mode.ERA_FAN:
            return era_of(track) == self._anchor_era
        return track.artist == self._anchor_artist

    def _start(self, mode: Mode, track: Track) -> None:
        self._anchor_artist = None
        self._anchor_era = None
        self._remaining = 0
        self._played = set()
        self._avoid_artist = None
        self._avoid_era = None
        if mode is Mode.ERA_FAN:
            era = era_of(track)
            if era is None:
                # Pas d'ancre sans année : tirage simple, et le hasard n'est
                # pas consommé pour que la soirée se rejoue.
                return
            self._anchor_era = era
        else:
            self._anchor_artist = track.artist
        lo, hi = RUN_SPANS[mode]
        length = lo if lo == hi else self._hasard.pick(list(range(lo, hi + 1)))
        self._remaining = length - 1
        self._played = {track.identifier}
