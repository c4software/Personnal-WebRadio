"""La seule source de hasard du projet.

Aucun autre fichier n'a le droit d'importer `random` ou `secrets` — ruff le
bannit à l'import, et `verifier.sh` le vérifie aussi (AGENTS.md §2).

La raison est symétrique de celle de l'horloge (ARCHITECTURE.md §3.1) : une
radio *est* un tirage. Si le hasard se puise n'importe où, aucune émission ne se
rejoue, et « le tirage évite-t-il de répéter un artiste ? » devient une question
sans réponse vérifiable.
"""

import random  # noqa: TID251 — le seul endroit autorisé ; voir l'en-tête
from typing import Protocol, TypeVar

T = TypeVar("T")


class Hasard(Protocol):
    """Ce que le noyau sait du hasard : choisir dans une suite non vide."""

    def choisir(self, parmi: list[T]) -> T: ...


class HasardPondere(Hasard, Protocol):
    """Le tirage pondéré est une capacité **différente**, pas un réglage de la première.

    Elle est déclarée à part (ARCHITECTURE.md §5.3) pour que tout ce qui n'a
    besoin que d'un tirage uniforme continue de ne dépendre que de `Hasard` :
    les poids viennent des votes (SPECS.md §4.12), et la file n'en a pas
    toujours.
    """

    def choisir_pondere(self, parmi: list[T], poids: list[float]) -> T: ...


def _verifier(parmi: list[T], poids: list[float]) -> None:
    """Les poids sont fournis au noyau : c'est ici qu'on refuse ce qui n'a pas de sens."""
    if not parmi:
        message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
        raise ValueError(message)
    if len(poids) != len(parmi):
        message = f"{len(poids)} poids pour {len(parmi)} éléments : la correspondance est perdue"
        raise ValueError(message)
    if any(p < 0 for p in poids):
        message = "un poids négatif n'a pas de sens : le plancher de SPECS.md §4.12 est 0,25"
        raise ValueError(message)
    if sum(poids) <= 0:
        message = "des poids tous nuls supprimeraient tout le monde : SPECS.md §4.12 l'interdit"
        raise ValueError(message)


class HasardReel:
    """Le tirage réel, semé explicitement.

    La graine est un paramètre et non une valeur cachée : une émission dont on
    n'aime pas l'enchaînement peut être rejouée à l'identique pour comprendre
    pourquoi.
    """

    def __init__(self, graine: int | None = None) -> None:
        self._alea = random.Random(graine)

    def choisir(self, parmi: list[T]) -> T:
        if not parmi:
            message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
            raise ValueError(message)
        return self._alea.choice(parmi)

    def choisir_pondere(self, parmi: list[T], poids: list[float]) -> T:
        """Un seul tirage uniforme, ramené sur les poids cumulés.

        Passer par `random()` plutôt que par une commodité de la bibliothèque
        garde la propriété qui compte : à graine et poids fixés, la même
        émission se rejoue à l'identique (ARCHITECTURE.md §5.3).
        """
        _verifier(parmi, poids)
        seuil = self._alea.random() * sum(poids)
        cumul = 0.0
        for element, poid in zip(parmi[:-1], poids[:-1], strict=True):
            cumul += poid
            if seuil < cumul:
                return element
        return parmi[-1]


class HasardScripte:
    """Un hasard dont le test écrit la suite à l'avance.

    Plus lisible qu'une graine quand le test porte sur *quel* morceau sort, et
    non sur la distribution : `HasardScripte([0, 2, 1])` dit exactement ce qui
    va être choisi.
    """

    def __init__(self, indices: list[int]) -> None:
        self._indices = list(indices)
        self._rang = 0

    def choisir(self, parmi: list[T]) -> T:
        if not parmi:
            message = "tirer dans une suite vide n'a pas de résultat : le repli se décide au-dessus"
            raise ValueError(message)
        if self._rang >= len(self._indices):
            message = f"le script est épuisé après {len(self._indices)} tirages"
            raise ValueError(message)
        i = self._indices[self._rang] % len(parmi)
        self._rang += 1
        return parmi[i]

    def choisir_pondere(self, parmi: list[T], poids: list[float]) -> T:
        """Le script dit *quel* élément sort ; les poids restent vérifiés.

        Un test qui écrit sa suite ne teste pas la distribution — mais il ne
        doit pas pour autant laisser passer des poids incohérents, sinon le
        double serait plus indulgent que la production (AGENTS.md §4.1).
        """
        _verifier(parmi, poids)
        return self.choisir(parmi)
