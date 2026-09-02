"""La seule source de temps du projet.

Aucun autre fichier n'appelle `datetime.now()` ou `time.time()` ; `verifier.sh`
le vérifie (AGENTS.md §2). Si l'heure se lisait n'importe où, on ne pourrait ni
rejouer une soirée, ni vérifier qu'un jingle tombe dans sa fenêtre
(ARCHITECTURE.md §3.1).
"""

from datetime import datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Ce que le noyau sait du temps : rien de plus que l'instant courant."""

    def now(self) -> datetime: ...


class SystemClock:
    """L'horloge réelle, seul endroit du projet qui lit le temps du système.

    En heure locale avec fuseau, pas en UTC : les heures du TOML sont celles de
    la personne qui écoute. En UTC, toute la grille serait décalée selon la
    saison sans que rien ne le signale (GOAL-015).
    """

    def now(self) -> datetime:
        return datetime.now().astimezone()


class FrozenClock:
    """Une horloge que le test déplace à volonté.

    Elle n'avance pas toute seule : une journée de programmation se déroule en
    quelques millisecondes et deux exécutions donnent le même résultat.
    """

    def __init__(self, depart: datetime) -> None:
        if depart.tzinfo is None:
            message = "une horloge sans fuseau produit des comparaisons fausses"
            raise ValueError(message)
        self._instant = depart

    def now(self) -> datetime:
        return self._instant

    def advance(self, duration: timedelta) -> None:
        if duration < timedelta(0):
            message = "le temps ne recule pas : un test qui en a besoin teste autre chose"
            raise ValueError(message)
        self._instant += duration

    def jump_to(self, instant: datetime) -> None:
        if instant < self._instant:
            message = "le temps ne recule pas : un test qui en a besoin teste autre chose"
            raise ValueError(message)
        self._instant = instant
