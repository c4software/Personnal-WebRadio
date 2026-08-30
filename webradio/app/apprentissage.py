"""Ce que la radio retient des votes, et ce qu'elle en fait au tirage.

C'est la seconde charnière du projet, symétrique de `programme.py` : d'un côté
le noyau, qui sait *combien pèse* un vote et *comment* les scores deviennent un
multiplicateur ; de l'autre la base, qui sait les *conserver*.

**Le noyau ne va jamais chercher un poids** (ARCHITECTURE.md §5.3) : c'est ce
module qui les lui fournit, comme on lui fournit des pistes.

Le noyau et la base ont chacun leur `Portee` et leurs `Scores`. Ce n'est **pas**
une duplication à supprimer : c'est ce qui permet à `adapters/etat/` de ne rien
importer du noyau et de se tester sans lui. La traduction tient en deux lignes,
et un test vérifie que les valeurs coïncident — le jour où elles divergeront, il
cassera ici plutôt qu'en base.
"""

import logging

from webradio.adapters.etat.base import EtatIndisponible, EtatSQLite
from webradio.adapters.etat.base import Portee as PorteeBase
from webradio.core.controle import Commande
from webradio.core.modeles import Piste
from webradio.core.ponderation import Portee, Scores, poids_de_la_piste, poids_du_vote

logger = logging.getLogger(__name__)


class Apprentissage:
    """Lit les poids avant un tirage, écrit les votes après qu'ils sont acceptés."""

    def __init__(
        self,
        base: EtatSQLite,
        *,
        plancher: float,
        plafond: float,
        pente: float,
        poids_croise: float,
    ) -> None:
        self._base = base
        self._plancher = plancher
        self._plafond = plafond
        self._pente = pente
        self._croise = poids_croise

    def peser(self, piste: Piste) -> float:
        """Le multiplicateur de chance d'une piste, borné.

        Une base injoignable ne fait pas taire la radio : on rend un poids
        neutre et l'on journalise. Un tirage sans mémoire vaut infiniment mieux
        qu'un tirage qui n'a pas lieu (SPECS.md §5).
        """
        try:
            piste_brute = self._base.scores(PorteeBase.PISTE, piste.identifiant)
            artiste_brut = self._base.scores(PorteeBase.ARTISTE, piste.artiste)
        except EtatIndisponible as panne:
            logger.warning("poids indisponibles, tirage neutre : %s", panne)
            return 1.0
        return poids_de_la_piste(
            Scores(stop=piste_brute.stop, encore=piste_brute.encore),
            Scores(stop=artiste_brut.stop, encore=artiste_brut.encore),
            plancher=self._plancher,
            plafond=self._plafond,
            pente=self._pente,
        )

    def retenir(self, commande: Commande, piste: Piste) -> None:
        """Enregistre un vote **accepté**, sur la piste et sur son artiste.

        À n'appeler que lorsque le vote a produit un effet : un vote refusé
        pendant un jingle ou une émission ne doit **rien** enregistrer
        (SPECS.md §4.6). Sinon la radio apprendrait de gestes qui n'ont rien
        changé, et l'auditeur pondérerait sans le savoir.
        """
        sur_la_piste = poids_du_vote(commande, Portee.PISTE)
        sur_l_artiste = poids_du_vote(commande, Portee.ARTISTE)
        try:
            self._ecrire(PorteeBase.PISTE, piste.identifiant, commande, sur_la_piste)
            self._ecrire(PorteeBase.ARTISTE, piste.artiste, commande, sur_l_artiste)
        except EtatIndisponible as panne:
            logger.warning("vote non retenu, la radio continue : %s", panne)

    def _ecrire(self, portee: PorteeBase, cible: str, commande: Commande, poids: float) -> None:
        if commande is Commande.STOP:
            self._base.enregistrer_vote(portee, cible, stop=poids)
        else:
            self._base.enregistrer_vote(portee, cible, encore=poids)
