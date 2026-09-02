"""La seule source de hasard du projet.

Aucun autre fichier n'importe `random` ou `secrets` : ruff le bannit et
`verifier.sh` le vérifie (AGENTS.md §2). Même raison que pour l'horloge
(ARCHITECTURE.md §3.1) : si le hasard se puise n'importe où, aucune émission ne
se rejoue et le tirage n'est pas vérifiable.
"""

# Seul import autorisé, voir la docstring du module.
import random  # noqa: TID251
from typing import Protocol, TypeVar

T = TypeVar("T")


class Random(Protocol):
    """Ce que le noyau sait du hasard : choisir dans une suite non vide."""

    def pick(self, parmi: list[T]) -> T: ...


class WeightedRandom(Random, Protocol):
    """Le tirage pondéré, déclaré à part du tirage uniforme.

    Ce qui n'a besoin que d'un tirage uniforme ne dépend que de `Random`
    (ARCHITECTURE.md §5.3) : les poids viennent des votes (SPECS.md §4.12), et
    la file n'en a pas toujours.
    """

    def pick_weighted(self, parmi: list[T], weight: list[float]) -> T: ...


def _verifier(parmi: list[T], weight: list[float]) -> None:
    """Vérifie les poids reçus avant un tirage pondéré."""
    if not parmi:
        message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
        raise ValueError(message)
    if len(weight) != len(parmi):
        message = f"{len(weight)} poids pour {len(parmi)} éléments : la correspondance est perdue"
        raise ValueError(message)
    if any(p < 0 for p in weight):
        message = "un poids négatif n'a pas de sens : le plancher de SPECS.md §4.12 est 0,25"
        raise ValueError(message)
    if sum(weight) <= 0:
        message = "des poids tous nuls supprimeraient tout le monde : SPECS.md §4.12 l'interdit"
        raise ValueError(message)


class RealRandom:
    """Le tirage réel, semé explicitement.

    La graine est un paramètre : une émission peut être rejouée à l'identique.
    """

    def __init__(self, graine: int | None = None) -> None:
        self._alea = random.Random(graine)

    def pick(self, parmi: list[T]) -> T:
        if not parmi:
            message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
            raise ValueError(message)
        return self._alea.choice(parmi)

    def pick_weighted(self, parmi: list[T], weight: list[float]) -> T:
        """Un seul tirage uniforme, ramené sur les poids cumulés.

        On passe par `random()` plutôt que par une commodité de la bibliothèque
        standard pour qu'à graine et poids fixés la même émission se rejoue à
        l'identique (ARCHITECTURE.md §5.3).
        """
        _verifier(parmi, weight)
        seuil = self._alea.random() * sum(weight)
        total = 0.0
        for element, poid in zip(parmi[:-1], weight[:-1], strict=True):
            total += poid
            if seuil < total:
                return element
        return parmi[-1]


class ScriptedRandom:
    """Un hasard dont le test écrit la suite à l'avance.

    Plus lisible qu'une graine quand le test porte sur quel morceau sort :
    `ScriptedRandom([0, 2, 1])` dit ce qui sera choisi.
    """

    def __init__(self, indices: list[int]) -> None:
        self._indices = list(indices)
        self._rang = 0

    def pick(self, parmi: list[T]) -> T:
        if not parmi:
            message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
            raise ValueError(message)
        if self._rang >= len(self._indices):
            message = f"le script est épuisé après {len(self._indices)} tirages"
            raise ValueError(message)
        i = self._indices[self._rang] % len(parmi)
        self._rang += 1
        return parmi[i]

    def pick_weighted(self, parmi: list[T], weight: list[float]) -> T:
        """Le script dit quel élément sort ; les poids restent vérifiés.

        Le double ne doit pas être plus indulgent que la production
        (AGENTS.md §4.1).
        """
        _verifier(parmi, weight)
        return self.pick(parmi)
