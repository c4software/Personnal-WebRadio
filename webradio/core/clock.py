"""La seule source de temps du projet.

Aucun autre fichier n'a le droit d'appeler `datetime.now()` ou `time.time()` —
c'est un interdit contrôlé par `verifier.sh` (AGENTS.md §2).

La raison est dans ARCHITECTURE.md §3.1 : une radio *est* une grille horaire.
Si l'heure se lit n'importe où, on ne peut ni rejouer une soirée, ni vérifier
qu'un jingle tombe dans sa fenêtre — la moitié du produit devient intestable.
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Horloge(Protocol):
    """Ce que le noyau sait du temps : rien de plus que l'instant courant."""

    def maintenant(self) -> datetime: ...


class HorlogeSysteme:
    """L'horloge réelle. Le seul endroit du projet qui lit le temps du système."""

    def maintenant(self) -> datetime:
        return datetime.now(tz=UTC)


class HorlogeFigee:
    """Une horloge que le test déplace à volonté.

    Elle n'avance pas toute seule : une journée entière de programmation se
    déroule en quelques millisecondes, et deux exécutions donnent le même
    résultat.
    """

    def __init__(self, depart: datetime) -> None:
        if depart.tzinfo is None:
            message = "une horloge sans fuseau produit des comparaisons fausses"
            raise ValueError(message)
        self._instant = depart

    def maintenant(self) -> datetime:
        return self._instant

    def avancer(self, duree: timedelta) -> None:
        if duree < timedelta(0):
            message = "le temps ne recule pas : un test qui en a besoin teste autre chose"
            raise ValueError(message)
        self._instant += duree

    def aller_a(self, instant: datetime) -> None:
        if instant < self._instant:
            message = "le temps ne recule pas : un test qui en a besoin teste autre chose"
            raise ValueError(message)
        self._instant = instant
