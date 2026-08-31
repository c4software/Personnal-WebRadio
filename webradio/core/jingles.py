"""Quel jingle est dû à cette jonction, et dans quel ordre.

Ce module calcule **des noms de fichiers**, jamais leur existence : un jingle
absent n'est pas une erreur, c'est le mode d'emploi (SPECS.md §4.3), et c'est un
adaptateur qui le constatera au moment de le lire. Le noyau ne regarde aucun
disque (ARCHITECTURE.md §1.1).

Trois règles commandent tout le reste :

- **un jingle horaire en retard passe quand même**, dans la limite de sa
  péremption (SPECS.md §7 n°4, amendée par la n°29) : un morceau long qui
  enjambe une heure pleine n'abandonne pas le jingle, c'est un cas nominal ;
- **mais pas au-delà** : à plus du délai de péremption de son heure pleine, un
  jingle horaire est abandonné — un `19h.mp3` entendu à 22 h 28, après une
  longue pause sans auditeur, sonne comme une horloge cassée (constaté le
  2026-08-31). Le jingle d'« encore » ne périme jamais : il répond à un vote,
  pas à l'horloge ;
- **rien ne passe pendant une émission**, qui remplace la programmation,
  habillage compris (SPECS.md §7 n°15). Cette exception-là ne tient pas au
  retard mais à la nature de l'émission.
"""

from datetime import datetime, timedelta

from webradio.core.clock import Clock

JINGLE_ENCORE = "encore.mp3"
UNE_HEURE = timedelta(hours=1)


def jingle_name(instant: datetime) -> str:
    """`hours/14h.mp3` pour 14 h. Le nom du fichier *est* la programmation.

    Seule exception à « rien en dur » (AGENTS.md §2) : il n'y a pas de table de
    correspondance à tenir à jour, on ajoute un jingle en déposant un fichier.
    Les horaires vivent dans `hours/` (GOAL-032) : vingt-quatre fichiers
    potentiels méritaient leur tiroir — l'« encore » et les génériques restent
    à la racine, ou où leur nom le dit.
    """
    return f"hours/{instant.hour:02d}h.mp3"


def _heures_pleines(depuis: datetime, jusqu_a: datetime) -> list[datetime]:
    """Les heures pleines de `]depuis, jusqu_a]`, de la plus ancienne à la plus récente."""
    borne = depuis.replace(minute=0, second=0, microsecond=0) + UNE_HEURE
    franchies: list[datetime] = []
    while borne <= jusqu_a:
        franchies.append(borne)
        borne += UNE_HEURE
    return franchies


class Jingles:
    """Ce qui est dû à la prochaine jonction, et qui s'épuise en le disant.

    L'instant de construction sert de repère de départ : la radio ne rattrape
    pas les heures d'avant son démarrage — elle n'existe que lorsqu'on l'écoute
    (SPECS.md §1).
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
        # Le nom du jingle d'« encore » se configure (GOAL-031) : les jingles
        # horaires restent nommés par leur heure, c'est leur programmation.
        self._nom_encore = encore_name
        # `None` : aucun jingle horaire ne périme — l'ancienne règle n°4.
        self._peremption = expiry

    @property
    def encore_du(self) -> bool:
        return self._encore_du

    def mark_more(self) -> None:
        """Un `encore` accepté s'annonce à la jonction suivante (SPECS.md §4.6).

        Deux votes avant la même jonction ne font pas deux jingles : l'accusé de
        réception porte sur le morceau qui suit, et il n'y en a qu'un.
        """
        self._encore_du = True

    def due_now(self, *, during_show: bool = False) -> tuple[str, ...]:
        """Les jingles à diffuser ici, dans l'ordre, `encore.mp3` en dernier.

        L'appel **consomme** : ce qui a été rendu ne le sera pas deux fois. Le
        repère avance même pendant une émission, sans quoi les heures abandonnées
        ressortiraient à la fin de l'épisode — ce que la décision n°15 refuse
        explicitement.
        """
        now = self._horloge.now()
        franchies = _heures_pleines(self._repere, now)
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
