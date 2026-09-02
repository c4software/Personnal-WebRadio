"""Des scores de votes au multiplicateur de chance.

Le noyau reçoit les scores, il ne lit aucune base (ARCHITECTURE.md §5.3) : un
adaptateur les charge.

Trois décisions portent ce module (SPECS.md §7) :

- n°16 : le poids d'un vote dépend de sa portée, piste ou artiste (voir
  `vote_weight`) ;
- n°18 : les votes s'oublient, demi-vie de trois mois. Sans oubli, la radio
  pénaliserait durablement ce qu'elle joue le plus, donc ce qu'on passe le plus
  (SPECS.md §4.12) ;
- n°17 : le multiplicateur est borné à [0,25 ; 4]. Le plancher n'est jamais
  zéro, un morceau ne sort jamais du tirage.
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from webradio.core.control import Command

DEFAULT_HALF_LIFE = timedelta(days=90)
DEFAULT_FLOOR = 0.25
DEFAULT_CEILING = 4.0
POIDS_DIRECT = 1.0

# Retrouve les ordres de grandeur de SPECS.md §4.12 : un vote donne 1,5 ou 0,67
# fois la chance normale, trois votes 2,5 ou 0,4. La même pente des deux côtés
# garde `stop` et `encore` symétriques.
SLOPE_PER_VOTE = 0.5


class Scope(Enum):
    """La portée d'un vote : la piste ou son artiste (SPECS.md §7 n°16)."""

    TRACK = "piste"
    ARTIST = "artiste"


@dataclass(frozen=True, slots=True)
class Scores:
    """Les scores accumulés par une cible, décroissance déjà appliquée.

    Deux nombres plutôt qu'une liste de votes : conserver chaque vote ferait
    grossir la base sans fin (ARCHITECTURE.md §5.2).
    """

    stop: float = 0.0
    encore: float = 0.0

    def __post_init__(self) -> None:
        if self.stop < 0 or self.encore < 0:
            message = f"un score de vote ne peut pas être négatif : {self}"
            raise ValueError(message)


def vote_weight(command: Command, scope: Scope) -> float:
    """Le poids d'un vote sur une portée : 1 sur l'artiste, 0 sur la piste.

    Le barème est le même pour `stop` et `encore`. Compter aussi sur la piste
    surpondérait : un artiste très présent finissait par écraser le tirage
    (SPECS.md §7 n°16). Un poids nul ne s'enregistre pas.
    """
    del command  # le barème est le même pour les deux gestes
    return POIDS_DIRECT if scope is Scope.ARTIST else 0.0


def decay(
    score: float,
    ecoule: timedelta,
    half_life: timedelta = DEFAULT_HALF_LIFE,
) -> float:
    """`score * 2 ** (-ecoule / half_life)`. Un vote d'il y a un an pèse encore 6 %."""
    if ecoule < timedelta(0):
        message = "le temps ne recule pas : une décroissance négative ferait grossir un vote"
        raise ValueError(message)
    if half_life <= timedelta(0):
        message = f"demi-vie non valable : {half_life}"
        raise ValueError(message)
    return score * 2 ** (-ecoule / half_life)


def record(
    score: float,
    ecoule: timedelta,
    increment: float,
    half_life: timedelta = DEFAULT_HALF_LIFE,
) -> float:
    """Applique la décroissance, puis ajoute le vote nouveau.

    L'ordre compte : ajouter d'abord ferait vieillir le vote qu'on vient de
    recevoir (ARCHITECTURE.md §5.2).
    """
    if increment < 0:
        message = f"un vote n'enlève rien : incrément non valable ({increment})"
        raise ValueError(message)
    return decay(score, ecoule, half_life) + increment


def multiplier(
    scores: Scores,
    *,
    floor: float = DEFAULT_FLOOR,
    ceiling: float = DEFAULT_CEILING,
    slope: float = SLOPE_PER_VOTE,
) -> float:
    """Le multiplicateur de chance d'une cible, borné entre `floor` et `ceiling`.

    La forme `(1 + slope * encore) / (1 + slope * stop)` rend les ordres de
    grandeur de SPECS.md §4.12 et ne peut pas atteindre zéro par elle-même : le
    plancher est un garde-fou.
    """
    if floor <= 0:
        message = "un plancher nul supprimerait un morceau : SPECS.md §4.12 l'interdit"
        raise ValueError(message)
    if ceiling < floor:
        message = f"plafond ({ceiling}) sous le plancher ({floor})"
        raise ValueError(message)
    brut = (1 + slope * scores.encore) / (1 + slope * scores.stop)
    return min(max(brut, floor), ceiling)


def track_weight(
    track: Scores,
    artist: Scores,
    *,
    floor: float = DEFAULT_FLOOR,
    ceiling: float = DEFAULT_CEILING,
    slope: float = SLOPE_PER_VOTE,
) -> float:
    """Le multiplicateur d'une piste, scores de la piste et de l'artiste additionnés.

    L'addition précède le bornage. Multiplier deux multiplicateurs déjà bornés
    donnerait [0,0625 ; 16], hors des bornes de la décision n°17.
    """
    total = Scores(stop=track.stop + artist.stop, encore=track.encore + artist.encore)
    return multiplier(total, floor=floor, ceiling=ceiling, slope=slope)
