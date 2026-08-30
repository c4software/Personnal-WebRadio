"""Un flux, N connexions : le fan-out.

Le même encodage alimente tout le monde, et tout le monde entend la même chose
au même instant (SPECS.md §4.1). La contrainte qui commande la forme du code est
dans ARCHITECTURE.md §4.1 : **un auditeur lent ne doit ralentir ni l'encodage,
ni les autres**.

D'où le choix d'une file bornée par auditeur plutôt que d'une écriture directe
dans la socket : publier ne bloque jamais. Quand une file déborde, c'est cette
connexion-là qu'on abandonne — pas la radio qu'on ralentit.
"""

import logging
import queue
import threading
from collections.abc import Iterator

logger = logging.getLogger(__name__)


class Abonne:
    """Une connexion branchée sur le flux, et le tampon qui la protège.

    `None` déposé dans la file signifie « c'est fini » : c'est ce qui réveille
    un auditeur bloqué en attente sans avoir à fermer sa socket depuis un autre
    fil, ce qui reviendrait à déréférencer ce qu'un fil est en train de lire.
    """

    def __init__(self, capacite: int) -> None:
        if capacite <= 0:
            message = f"capacité de tampon non valable : {capacite}"
            raise ValueError(message)
        self._blocs: queue.Queue[bytes | None] = queue.Queue(maxsize=capacite)
        self._ferme = False

    @property
    def ferme(self) -> bool:
        return self._ferme

    def deposer(self, bloc: bytes) -> bool:
        """Dépose un bloc. Rend `False` si l'auditeur ne suit plus."""
        if self._ferme:
            return False
        try:
            self._blocs.put_nowait(bloc)
        except queue.Full:
            return False
        return True

    def fermer(self) -> None:
        """Annonce la fin à qui lit ce flux. Idempotente.

        La sentinelle est déposée de force si nécessaire : une file pleine est
        justement le cas où il faut réveiller l'auditeur.
        """
        if self._ferme:
            return
        self._ferme = True
        try:
            self._blocs.put_nowait(None)
        except queue.Full:
            self._vider()
            self._blocs.put_nowait(None)

    def _vider(self) -> None:
        while True:
            try:
                self._blocs.get_nowait()
            except queue.Empty:
                return

    def blocs(self, delai: float) -> Iterator[bytes]:
        """Les blocs à écrire dans la socket, jusqu'à la fin du flux.

        `delai` borne l'attente pour qu'une chaîne muette — un ffmpeg qui ne
        produit plus rien sans être mort — ne laisse pas la connexion pendue
        indéfiniment.
        """
        while True:
            try:
                bloc = self._blocs.get(timeout=delai)
            except queue.Empty:
                if self._ferme:
                    return
                continue
            if bloc is None:
                return
            yield bloc


class Diffusion:
    """Le point de partage entre la chaîne et les auditeurs."""

    def __init__(self, capacite_par_auditeur: int = 64) -> None:
        self._capacite = capacite_par_auditeur
        self._verrou = threading.Lock()
        self._abonnes: list[Abonne] = []

    @property
    def auditeurs(self) -> int:
        with self._verrou:
            return len(self._abonnes)

    def abonner(self) -> Abonne:
        abonne = Abonne(self._capacite)
        with self._verrou:
            self._abonnes.append(abonne)
        return abonne

    def desabonner(self, abonne: Abonne) -> None:
        """Retire un auditeur. Idempotente : une déconnexion peut être vue deux fois."""
        with self._verrou:
            if abonne in self._abonnes:
                self._abonnes.remove(abonne)
        abonne.fermer()

    def publier(self, bloc: bytes) -> None:
        """Verse le même bloc à tout le monde, sans jamais attendre personne."""
        with self._verrou:
            lents = [abonne for abonne in self._abonnes if not abonne.deposer(bloc)]
            for lent in lents:
                self._abonnes.remove(lent)
        for lent in lents:
            logger.warning("auditeur trop lent : sa connexion est abandonnée")
            lent.fermer()

    def fermer(self, raison: str) -> None:
        """Termine toutes les connexions, en disant pourquoi.

        Appelée quand la chaîne coupe (SPECS.md §5.1) : l'auditeur voit son flux
        s'arrêter, et se rebranchera sur une chaîne neuve s'il le souhaite.
        """
        with self._verrou:
            partants = list(self._abonnes)
            self._abonnes.clear()
        logger.info("fin du flux pour %d auditeur(s) : %s", len(partants), raison)
        for partant in partants:
            partant.fermer()
