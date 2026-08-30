"""`stop` et `encore` : leur effet, et ce qu'ils refusent.

**Ce sont des décisions, donc du noyau** (ARCHITECTURE.md §6) : leur effet se
spécifie et se teste sans Flask, sans HTTP et sans navigateur. L'API traduit un
refus en réponse HTTP ; elle ne le décide pas.

Trois règles tranchées portent ce module :

- **une voix suffit** (SPECS.md §7 n°10) : ni quorum, ni dépouillement ;
- **un refus est explicite et motivé** (SPECS.md §4.6) : un refus muet est
  indistinguable d'une panne, et pousse à réessayer ;
- **`encore` outrepasse la non-répétition** (SPECS.md §7 n°7), et les morceaux
  qu'il sert n'entrent pas dans la fenêtre — sans quoi un long enchaînement
  condamnerait l'artiste pour longtemps après. C'est pourquoi aucune `Fenetre`
  n'apparaît ici : ne pas la connaître est la façon la plus sûre de ne pas la
  nourrir.
"""

from dataclasses import dataclass
from enum import Enum

from webradio.core.queue import Choix, FileVide
from webradio.core.jingles import Jingles
from webradio.core.models import Piste
from webradio.core.rng import Hasard
from webradio.core.sources import SourceMusicale


class Nature(Enum):
    """Ce qui passe à l'antenne. C'est le noyau qui le sait, donc qui refuse."""

    MUSIQUE = "musique"
    JINGLE = "jingle"
    FLASH = "flash"
    EMISSION = "emission"


class Commande(Enum):
    STOP = "stop"
    ENCORE = "encore"


MOTIFS_DE_REFUS = {
    Nature.JINGLE: "un jingle est en cours : on ne passe pas un jingle",
    Nature.FLASH: "un flash d'information est en cours : on ne passe pas un flash",
    Nature.EMISSION: "une émission est en cours : on ne passe pas une émission",
}


@dataclass(frozen=True, slots=True)
class Reponse:
    """Le sort d'un vote. `motif` est vide quand il est accepté.

    Un booléen seul aurait suffi à la file, pas à l'auditeur : c'est le motif
    qui distingue « refusé » de « en panne » (ARCHITECTURE.md §6.1).
    """

    accepte: bool
    motif: str = ""


class Controle:
    """L'effet des deux commandes sur ce que la file rendra ensuite."""

    def __init__(
        self,
        source: SourceMusicale,
        hasard: Hasard,
        jingles: Jingles,
        nature: Nature = Nature.MUSIQUE,
    ) -> None:
        self._source = source
        self._hasard = hasard
        self._jingles = jingles
        self._nature = nature
        self._saut_demande = False
        self._encore_demande = False
        self._servis: set[str] = set()

    @property
    def nature(self) -> Nature:
        return self._nature

    def declarer(self, nature: Nature) -> None:
        """Ce qui passe maintenant. C'est ce qui rend les refus possibles."""
        self._nature = nature

    def voter(self, commande: Commande) -> Reponse:
        """Le premier vote reçu s'applique : une voix suffit (SPECS.md §7 n°10)."""
        motif = MOTIFS_DE_REFUS.get(self._nature)
        if motif is not None:
            return Reponse(accepte=False, motif=motif)
        if commande is Commande.STOP:
            self._saut_demande = True
        else:
            self._encore_demande = True
            self._jingles.marquer_encore()
        return Reponse(accepte=True)

    def reclamer_saut(self) -> bool:
        """Y a-t-il un `stop` à honorer ? L'appel le consomme."""
        demande = self._saut_demande
        self._saut_demande = False
        return demande

    def reclamer_encore(self) -> bool:
        """Y a-t-il un `encore` à honorer ? L'appel le consomme.

        `encore` porte sur le morceau **suivant**, pas sur toute la suite : il
        n'installe pas un mode (SPECS.md §4.6).
        """
        demande = self._encore_demande
        self._encore_demande = False
        return demande

    def morceau_apres_encore(self, courant: Piste) -> Choix:
        """Même artiste, puis même genre, puis tirage libre — et chaque repli est dit.

        Ce qui borne l'enchaînement n'est pas un compteur mais la bibliothèque
        elle-même (SPECS.md §7 n°7) : quand l'artiste n'a plus de morceau non
        joué, on descend d'un cran.
        """
        replis: list[str] = []
        ecartes = self._servis | {courant.identifiant}

        candidates = [
            p for p in self._source.pistes_de(courant.artiste) if p.identifiant not in ecartes
        ]

        if not candidates:
            replis.append(f"artiste « {courant.artiste} » épuisé")
            if courant.genre is None:
                replis.append("morceau sans genre : tirage libre")
            else:
                candidates = [
                    p for p in self._source.pistes(courant.genre) if p.identifiant not in ecartes
                ]
                if not candidates:
                    replis.append(f"genre « {courant.genre} » épuisé : tirage libre")

        if not candidates:
            candidates = [p for p in self._source.pistes(None) if p.identifiant not in ecartes]
            # La chaîne d'`encore` s'arrête là où la bibliothèque s'arrête : on
            # relâche alors « non déjà servi » plutôt que de faire taire la radio
            # (SPECS.md §5.1).
            if not candidates:
                self._servis.clear()
                replis.append("bibliothèque entièrement servie : la chaîne repart")
                candidates = self._source.pistes(None)

        if not candidates:
            message = "la source a répondu, mais elle n'a aucune piste"
            raise FileVide(message)

        choisi = self._hasard.choisir(candidates)
        self._servis.add(choisi.identifiant)
        return Choix(choisi, tuple(replis))
