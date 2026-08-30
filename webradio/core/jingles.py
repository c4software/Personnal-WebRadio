"""Quel jingle est dû à cette jonction, et dans quel ordre.

Ce module calcule **des noms de fichiers**, jamais leur existence : un jingle
absent n'est pas une erreur, c'est le mode d'emploi (SPECS.md §4.3), et c'est un
adaptateur qui le constatera au moment de le lire. Le noyau ne regarde aucun
disque (ARCHITECTURE.md §1.1).

Deux règles commandent tout le reste :

- **aucun jingle n'est abandonné pour cause de retard** (SPECS.md §7 n°4). Un
  morceau de soixante-dix minutes enjambe deux heures pleines : les deux jingles
  passent, dans l'ordre chronologique. C'est un cas nominal ;
- **sauf pendant une émission**, qui remplace la programmation, habillage
  compris (SPECS.md §7 n°15). C'est la seule exception, et elle ne tient pas au
  retard mais à la nature de l'émission.
"""

from datetime import datetime, timedelta

from webradio.core.clock import Horloge

JINGLE_ENCORE = "encore.mp3"
UNE_HEURE = timedelta(hours=1)


def nom_du_jingle(instant: datetime) -> str:
    """`14h.mp3` pour 14 h. Le nom du fichier *est* la programmation.

    Seule exception à « rien en dur » (AGENTS.md §2) : il n'y a pas de table de
    correspondance à tenir à jour, on ajoute un jingle en déposant un fichier.
    """
    return f"{instant.hour:02d}h.mp3"


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

    def __init__(self, horloge: Horloge) -> None:
        self._horloge = horloge
        self._repere = horloge.maintenant()
        self._encore_du = False

    @property
    def encore_du(self) -> bool:
        return self._encore_du

    def marquer_encore(self) -> None:
        """Un `encore` accepté s'annonce à la jonction suivante (SPECS.md §4.6).

        Deux votes avant la même jonction ne font pas deux jingles : l'accusé de
        réception porte sur le morceau qui suit, et il n'y en a qu'un.
        """
        self._encore_du = True

    def dus(self, *, pendant_emission: bool = False) -> tuple[str, ...]:
        """Les jingles à diffuser ici, dans l'ordre, `encore.mp3` en dernier.

        L'appel **consomme** : ce qui a été rendu ne le sera pas deux fois. Le
        repère avance même pendant une émission, sans quoi les heures abandonnées
        ressortiraient à la fin de l'épisode — ce que la décision n°15 refuse
        explicitement.
        """
        maintenant = self._horloge.maintenant()
        franchies = _heures_pleines(self._repere, maintenant)
        self._repere = maintenant

        encore = self._encore_du
        self._encore_du = False

        if pendant_emission:
            return ()

        noms = [nom_du_jingle(heure) for heure in franchies]
        if encore:
            noms.append(JINGLE_ENCORE)
        return tuple(noms)
