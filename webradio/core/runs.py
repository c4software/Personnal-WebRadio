"""Les suites d'une plage : double dose, passionné d'époque, passionné d'artiste.

Une plage peut demander que ses tirages s'enchaînent (SPECS.md §4.4, décision
n°31) : le premier morceau tiré pose une ancre, son artiste ou sa décennie, et
les tirages suivants s'y tiennent pendant une suite dont la longueur est tirée
par le hasard injecté. Ce module ne cherche aucune musique : il dit au tirage ce
que la suite en cours impose et observe ce qui a été tiré. `core/queue.py`
filtre, journalise les ruptures et tire.

L'état est tenu par occurrence de plage : l'avance est tirée créneau par créneau
sous des occurrences différentes (décision n°34), et un créneau de la plage
suivante ne doit pas effacer la suite en cours.

Deux cas limites :

- une piste sans année ne pose pas d'ancre d'époque (docs/subsonic.md §4.1) et
  le tirage reste un tirage simple ;
- le même titre ne repasse jamais dans une même suite : une décennie maigre
  croisée avec une plage étroite se rompt plutôt que de boucler.
"""

from dataclasses import dataclass, field
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

# Autant de suites retenues, une par clé de moment. La préparation tire quelques
# créneaux d'avance sous des occurrences que l'antenne n'a pas atteintes
# (décision n°34) ; au-delà ce sont des moments passés. Même borne que la
# mémoire des thèmes au hasard (`core/mystery.py`).
MEMOIRE_MAX = 32


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


@dataclass(slots=True)
class _Run:
    """L'état d'une suite pour une clé de moment."""

    mode: Mode | None = None
    anchor_artist: str | None = None
    anchor_era: int | None = None
    remaining: int = 0
    played: set[str] = field(default_factory=set)
    avoid_artist: str | None = None
    avoid_era: int | None = None


class Runs:
    """Les suites en cours, une par occurrence de plage, et ce qu'elles imposent.

    La clé est celle du moment (décision n°31) : deux tirages de la même
    occurrence partagent la suite, une autre plage ou le tirage libre en a une
    autre. Un thème au hasard est figé sur l'occurrence (`core/mystery.py`) et
    donne la même contrainte toute la soirée.

    L'état est indexé par clé et non unique, parce que l'avance est tirée
    créneau par créneau sous des occurrences différentes (décision n°34) :
    préparer un titre pour la plage suivante effaçait sinon la suite en cours.
    """

    def __init__(self, random: Random) -> None:
        self._hasard = random
        self._suites: dict[object, _Run] = {}

    def break_run(self, constraint: object) -> bool:
        """Rompt la suite de cette clé ; la prochaine ancre évitera la sienne
        (GOAL-059).

        Rend `False` hors mode ou en double dose, dont l'artiste n'est pas une
        ancre tirée pour durer.
        """
        suite = self._suites.get(constraint)
        if suite is None or suite.mode not in (Mode.ERA_FAN, Mode.ARTIST_FAN):
            return False
        suite.avoid_artist, suite.avoid_era = suite.anchor_artist, suite.anchor_era
        suite.remaining = 0
        suite.played = set()
        return True

    def directive(self, constraint: object, mode: Mode | None) -> Directive | None:
        """Ce que le prochain tirage doit respecter, ou `None` pour un tirage d'ancre."""
        suite = self._etat(constraint, mode)
        if suite.mode is None:
            return None
        if suite.remaining <= 0:
            if suite.avoid_artist is None and suite.avoid_era is None:
                return None
            return Directive(avoid_artist=suite.avoid_artist, avoid_era=suite.avoid_era)
        if suite.mode is Mode.ERA_FAN:
            return Directive(era=suite.anchor_era, exclude=frozenset(suite.played))
        return Directive(
            artist=suite.anchor_artist, exclude=frozenset(suite.played), bypass_window=True
        )

    def observe(self, constraint: object, mode: Mode | None, track: Track) -> None:
        """Enregistre le tirage : la suite avance, ou une nouvelle s'ouvre.

        Un morceau qui ne colle pas à l'ancre (le tirage a dû rompre la suite,
        faute de candidats) devient la nouvelle ancre.
        """
        suite = self._etat(constraint, mode)
        if suite.mode is None:
            return
        if suite.remaining > 0 and self._matches(suite, track):
            suite.remaining -= 1
            suite.played.add(track.identifier)
            return
        self._start(suite, suite.mode, track)

    def _etat(self, constraint: object, mode: Mode | None) -> _Run:
        """L'état de cette clé, neuf si elle est inconnue ou si son mode a changé.

        La mémoire est bornée : une clé oubliée repart à zéro, comme celle des
        thèmes au hasard (`core/mystery.py`).
        """
        suite = self._suites.get(constraint)
        if suite is not None and suite.mode is mode:
            return suite
        suite = _Run(mode=mode)
        self._suites[constraint] = suite
        while len(self._suites) > MEMOIRE_MAX:
            del self._suites[next(iter(self._suites))]
        return suite

    @staticmethod
    def _matches(suite: _Run, track: Track) -> bool:
        if suite.mode is Mode.ERA_FAN:
            return era_of(track) == suite.anchor_era
        return track.artist == suite.anchor_artist

    def _start(self, suite: _Run, mode: Mode, track: Track) -> None:
        suite.anchor_artist = None
        suite.anchor_era = None
        suite.remaining = 0
        suite.played = set()
        suite.avoid_artist = None
        suite.avoid_era = None
        if mode is Mode.ERA_FAN:
            era = era_of(track)
            if era is None:
                # Pas d'ancre sans année : tirage simple, et le hasard n'est
                # pas consommé pour que la soirée se rejoue.
                return
            suite.anchor_era = era
        else:
            suite.anchor_artist = track.artist
        lo, hi = RUN_SPANS[mode]
        length = lo if lo == hi else self._hasard.pick(list(range(lo, hi + 1)))
        suite.remaining = length - 1
        suite.played = {track.identifier}
