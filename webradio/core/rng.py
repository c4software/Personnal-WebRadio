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
