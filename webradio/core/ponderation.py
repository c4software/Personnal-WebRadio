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

from webradio.core.controle import Commande

DEMI_VIE_PAR_DEFAUT = timedelta(days=90)
PLANCHER_PAR_DEFAUT = 0.25
PLAFOND_PAR_DEFAUT = 4.0
POIDS_DIRECT = 1.0
POIDS_CROISE = 0.25

# Choisie pour retrouver les ordres de grandeur annoncés par SPECS.md §4.12 :
# un vote donne 1,5 ou 0,67 fois la chance normale, trois donnent 2,5 ou 0,4.
# La même pente des deux côtés garde `stop` et `encore` symétriques, ce qui est
# ce que l'auteur décrit.
PENTE_PAR_VOTE = 0.5


class Portee(Enum):
    """Sur quoi un vote pèse. Les deux, mais pas également (SPECS.md §7 n°16)."""

    PISTE = "piste"
    ARTISTE = "artiste"


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


def poids_du_vote(commande: Commande, portee: Portee) -> float:
    """1 sur ce que le geste désigne, 0,25 sur l'autre.

    On passe un *morceau*, on redemande un *artiste* : la piste seule aurait mis
    des mois à s'entendre, l'artiste seul aurait fait reculer tout un catalogue
    pour un titre détesté.
    """
    designe = Portee.PISTE if commande is Commande.STOP else Portee.ARTISTE
    return POIDS_DIRECT if portee is designe else POIDS_CROISE


def decroitre(
    score: float,
    ecoule: timedelta,
    demi_vie: timedelta = DEMI_VIE_PAR_DEFAUT,
) -> float:
    """`score * 2 ** (-ecoule / demi_vie)`. Un vote d'il y a un an ne pèse plus que 6 %."""
    if ecoule < timedelta(0):
        message = "le temps ne recule pas : une décroissance négative ferait grossir un vote"
        raise ValueError(message)
    if demi_vie <= timedelta(0):
        message = f"demi-vie non valable : {demi_vie}"
        raise ValueError(message)
    return score * 2 ** (-ecoule / demi_vie)


def enregistrer(
    score: float,
    ecoule: timedelta,
    increment: float,
    demi_vie: timedelta = DEMI_VIE_PAR_DEFAUT,
) -> float:
    """La décroissance s'applique **avant** d'ajouter le vote nouveau.

    L'ordre n'est pas un détail : ajouter d'abord ferait vieillir le vote qu'on
    vient de recevoir, et douze `stop` dont un seul est récent compteraient tous
    comme frais (ARCHITECTURE.md §5.2).
    """
    if increment < 0:
        message = f"un vote n'enlève rien : incrément non valable ({increment})"
        raise ValueError(message)
    return decroitre(score, ecoule, demi_vie) + increment


def multiplicateur(
    scores: Scores,
    *,
    plancher: float = PLANCHER_PAR_DEFAUT,
    plafond: float = PLAFOND_PAR_DEFAUT,
    pente: float = PENTE_PAR_VOTE,
) -> float:
    """La chance d'être tiré, en multiple de la normale, bornée des deux côtés.

    La forme `(1 + pente * encore) / (1 + pente * stop)` est retenue parce qu'elle
    rend exactement les ordres de grandeur de SPECS.md §4.12 et qu'elle ne peut
    jamais atteindre zéro par elle-même : le plancher est un garde-fou, pas la
    règle.
    """
    if plancher <= 0:
        message = "un plancher nul supprimerait un morceau : SPECS.md §4.12 l'interdit"
        raise ValueError(message)
    if plafond < plancher:
        message = f"plafond ({plafond}) sous le plancher ({plancher})"
        raise ValueError(message)
    brut = (1 + pente * scores.encore) / (1 + pente * scores.stop)
    return min(max(brut, plancher), plafond)


def poids_de_la_piste(
    piste: Scores,
    artiste: Scores,
    *,
    plancher: float = PLANCHER_PAR_DEFAUT,
    plafond: float = PLAFOND_PAR_DEFAUT,
    pente: float = PENTE_PAR_VOTE,
) -> float:
    """Les deux portées s'additionnent avant d'être bornées, jamais après.

    Multiplier deux multiplicateurs déjà bornés aurait donné [0,0625 ; 16] —
    quatre fois plus loin que ce que la décision n°17 autorise, et le plancher
    aurait cessé d'être celui qu'elle nomme.
    """
    cumul = Scores(stop=piste.stop + artiste.stop, encore=piste.encore + artiste.encore)
    return multiplicateur(cumul, plancher=plancher, plafond=plafond, pente=pente)
