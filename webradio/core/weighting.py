"""Des scores de votes au multiplicateur de chance.

Le noyau **reçoit** les scores, il ne lit aucune base (ARCHITECTURE.md §5.3) :
un adaptateur les charge, la frontière tient sans exception.

Trois décisions tranchées le 2026-08-30 tiennent dans ce fichier :

- **n°16** — un `stop` compte 1 sur la piste et 0,25 sur l'artiste ; un `encore`
  l'inverse. Chaque geste garde le sens qu'il a, et un signal répété finit tout
  de même par porter ;
- **n°18** — les votes s'oublient, demi-vie de trois mois. C'est la seule des
  trois qui **corrige** le biais de SPECS.md §4.12 au lieu de l'amplifier :
  sans oubli, la radio pénalise durablement ce qu'on aime le plus, puisque c'est
  ce qu'elle joue le plus, donc ce qu'on passe le plus ;
- **n°17** — le multiplicateur est borné à [0,25 ; 4]. **Le plancher n'est jamais
  zéro** : c'est la différence entre une radio qui apprend et une radio qui se
  rétrécit.
"""

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from webradio.core.control import Command

DEFAULT_HALF_LIFE = timedelta(days=90)
DEFAULT_FLOOR = 0.25
DEFAULT_CEILING = 4.0
POIDS_DIRECT = 1.0
POIDS_CROISE = 0.25

# Choisie pour retrouver les ordres de grandeur annoncés par SPECS.md §4.12 :
# un vote donne 1,5 ou 0,67 fois la chance normale, trois donnent 2,5 ou 0,4.
# La même pente des deux côtés garde `stop` et `encore` symétriques, ce qui est
# ce que l'auteur décrit.
SLOPE_PER_VOTE = 0.5


class Scope(Enum):
    """Sur quoi un vote pèse. Les deux, mais pas également (SPECS.md §7 n°16)."""

    TRACK = "piste"
    ARTIST = "artiste"


@dataclass(frozen=True, slots=True)
class Scores:
    """Ce qu'une cible a accumulé, décroissance déjà appliquée.

    Deux nombres et pas une liste de votes : conserver chaque vote aurait fait
    grossir la base indéfiniment pour une information qui se résume
    (ARCHITECTURE.md §5.2).
    """

    stop: float = 0.0
    encore: float = 0.0

    def __post_init__(self) -> None:
        if self.stop < 0 or self.encore < 0:
            message = f"un score de vote ne peut pas être négatif : {self}"
            raise ValueError(message)


def vote_weight(command: Command, scope: Scope) -> float:
    """1 sur ce que le geste désigne, 0,25 sur l'autre.

    On passe un *morceau*, on redemande un *artiste* : la piste seule aurait mis
    des mois à s'entendre, l'artiste seul aurait fait reculer tout un catalogue
    pour un titre détesté.
    """
    designe = Scope.TRACK if command is Command.SKIP else Scope.ARTIST
    return POIDS_DIRECT if scope is designe else POIDS_CROISE


def decay(
    score: float,
    ecoule: timedelta,
    half_life: timedelta = DEFAULT_HALF_LIFE,
) -> float:
    """`score * 2 ** (-ecoule / demi_vie)`. Un vote d'il y a un an ne pèse plus que 6 %."""
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
    """La décroissance s'applique **avant** d'ajouter le vote nouveau.

    L'ordre n'est pas un détail : ajouter d'abord ferait vieillir le vote qu'on
    vient de recevoir, et douze `stop` dont un seul est récent compteraient tous
    comme frais (ARCHITECTURE.md §5.2).
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
    """La chance d'être tiré, en multiple de la normale, bornée des deux côtés.

    La forme `(1 + pente * encore) / (1 + pente * stop)` est retenue parce qu'elle
    rend exactement les ordres de grandeur de SPECS.md §4.12 et qu'elle ne peut
    jamais atteindre zéro par elle-même : le plancher est un garde-fou, pas la
    règle.
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
    """Les deux portées s'additionnent avant d'être bornées, jamais après.

    Multiplier deux multiplicateurs déjà bornés aurait donné [0,0625 ; 16] —
    quatre fois plus loin que ce que la décision n°17 autorise, et le plancher
    aurait cessé d'être celui qu'elle nomme.
    """
    total = Scores(stop=track.stop + artist.stop, encore=track.encore + artist.encore)
    return multiplier(total, floor=floor, ceiling=ceiling, slope=slope)
