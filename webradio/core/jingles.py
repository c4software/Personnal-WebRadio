"""Quel jingle est dû à cette jonction, et dans quel ordre.

Ce module calcule des noms de fichiers, jamais leur existence : un jingle absent
n'est pas une erreur (SPECS.md §4.3), c'est l'adaptateur qui le constate à la
lecture. Le noyau ne regarde aucun disque (ARCHITECTURE.md §1.1).

Trois règles :

- un jingle horaire en retard passe quand même, dans la limite de sa péremption
  (SPECS.md §7 n°4, amendée par la n°29) : un morceau long qui enjambe une heure
  pleine est un cas nominal ;
- au-delà du délai de péremption, il est abandonné : un jingle de 19 h entendu
  après 22 h sonne comme une horloge cassée. Le jingle d'encore ne périme
  jamais, il répond à un vote et non à l'horloge ;
- rien ne passe pendant une émission, qui remplace la programmation, habillage
  compris (SPECS.md §7 n°15).
"""

from datetime import datetime, timedelta

from webradio.core.clock import Clock

JINGLE_ENCORE = "encore.mp3"
UNE_HEURE = timedelta(hours=1)


def jingle_name(instant: datetime) -> str:
    """`hours/14h.mp3` pour 14 h. Le nom du fichier est la programmation.

    Seule exception à la règle d'AGENTS.md §2 sur les valeurs en dur : pas de
    table à tenir à jour, on ajoute un jingle en déposant un fichier. Les
    horaires vivent dans `hours/` (GOAL-032), l'encore et les génériques à la
    racine.
    """
    return f"hours/{instant.hour:02d}h.mp3"


def full_hours_between(depuis: datetime, jusqu_a: datetime) -> list[datetime]:
    """Les heures pleines de `]depuis, jusqu_a]`, de la plus ancienne à la plus récente."""
    borne = depuis.replace(minute=0, second=0, microsecond=0) + UNE_HEURE
    franchies: list[datetime] = []
    while borne <= jusqu_a:
        franchies.append(borne)
        borne += UNE_HEURE
    return franchies


class Jingles:
    """Les jingles dus à la prochaine jonction ; `due_now` les rend et les oublie.

    L'instant de construction sert de repère : la radio ne rattrape pas les
    heures d'avant son démarrage (SPECS.md §1).
    """

    def __init__(
        self,
        clock: Clock,
        encore_name: str = JINGLE_ENCORE,
        expiry: timedelta | None = None,
    ) -> None:
        self._horloge = clock
        self._repere = clock.now()
        self._encore_du = False
        # Le nom du jingle d'encore est configurable (GOAL-031). Les jingles
        # horaires sont nommés par leur heure.
        self._nom_encore = encore_name
        # `None` : aucun jingle horaire ne périme (règle n°4 avant la n°29).
        self._peremption = expiry

    @property
    def encore_du(self) -> bool:
        return self._encore_du

    def mark_more(self) -> None:
        """Un `encore` accepté s'annonce à la jonction suivante (SPECS.md §4.6).

        Deux votes avant la même jonction ne font qu'un jingle : l'annonce porte
        sur le morceau qui suit, et il n'y en a qu'un.
        """
        self._encore_du = True

    def due_now(self, *, during_show: bool = False) -> tuple[str, ...]:
        """Les jingles à diffuser maintenant, dans l'ordre, l'encore en dernier.

        L'appel consomme : ce qui a été rendu ne le sera pas deux fois. Le repère
        avance même pendant une émission, sinon les heures abandonnées
        ressortiraient à la fin de l'épisode (décision n°15).
        """
        now = self._horloge.now()
        franchies = full_hours_between(self._repere, now)
        self._repere = now

        encore = self._encore_du
        self._encore_du = False

        if during_show:
            return ()

        if self._peremption is not None:
            franchies = [hour for hour in franchies if now - hour <= self._peremption]
        names = [jingle_name(hour) for hour in franchies]
        if encore:
            names.append(self._nom_encore)
        return tuple(names)
