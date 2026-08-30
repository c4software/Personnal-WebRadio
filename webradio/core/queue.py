"""La file de lecture : ce qui passe ensuite, et pourquoi.

Elle est **tirée, pas poussée** (ARCHITECTURE.md §2) : c'est l'encodeur qui
réclame le morceau suivant quand il en a besoin. Le noyau ne connaît ni le temps
réel, ni les tampons.

Elle **prend de l'avance** : `preparer()` résout le morceau suivant pendant que
le courant joue. C'est une contrainte que le relevé a imposée
([docs/ffmpeg.md](../../docs/ffmpeg.md) §2.2) — un tuyau qui se tarit ne fait
pas un blanc dans l'audio, il fait un trou dans le temps réel, donc un tampon
qui se vide chez l'auditeur, donc une déconnexion.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from webradio.core.models import Piste
from webradio.core.rotation import Fenetre
from webradio.core.rng import Hasard, HasardPondere
from webradio.core.sources import SourceMusicale

# Le poids d'une piste, fourni du dehors. La file ne va JAMAIS le chercher :
# les scores vivent dans une base, et le noyau ne parle à personne
# (ARCHITECTURE.md §1.1, §5.3).
Peser = Callable[[Piste], float]


@dataclass(frozen=True, slots=True)
class Choix:
    """Une piste, et ce qui a dû être relâché pour l'obtenir.

    `replis` n'est pas décoratif : SPECS.md §5 demande que chaque repli soit
    journalisé, et c'est ici qu'on sait lesquels ont eu lieu.
    """

    piste: Piste
    replis: tuple[str, ...] = ()


class FileVide(Exception):
    """Aucune piste ne peut être servie, même après tous les replis.

    Distinct d'une source injoignable : ici la source a répondu, elle n'a rien.
    """


class File:
    """Tire le morceau suivant, en relâchant les contraintes plutôt que de se taire."""

    def __init__(
        self,
        source: SourceMusicale,
        hasard: Hasard,
        fenetre: Fenetre | None = None,
        peser: Peser | None = None,
    ) -> None:
        self._source = source
        self._hasard = hasard
        self._fenetre = fenetre if fenetre is not None else Fenetre()
        self._peser = peser
        self._avance: Choix | None = None
        if peser is not None and not hasattr(hasard, "choisir_pondere"):
            # Refuser ici plutôt qu'au premier tirage : une file construite avec
            # des poids et un hasard qui ne sait pas les honorer tirerait
            # uniformément sans que rien ne le signale, et la pondération
            # semblerait « ne pas marcher » des semaines durant.
            message = "des poids sont fournis, mais ce hasard ne sait pas les honorer"
            raise TypeError(message)

    def preparer(self, genre: str | None = None) -> None:
        """Résout le morceau suivant à l'avance, sans le consommer.

        Appelée pendant que le courant joue. Une source lente coûte alors du
        temps que personne n'attend, au lieu d'un trou à la jonction.
        """
        if self._avance is None:
            self._avance = self._choisir(genre)

    def suivant(self, genre: str | None = None) -> Choix:
        """Le morceau suivant. Sert l'avance si elle existe, la calcule sinon."""
        choix = self._avance if self._avance is not None else self._choisir(genre)
        self._avance = None
        self._fenetre.retenir(choix.piste)
        return choix

    def _choisir(self, genre: str | None) -> Choix:
        replis: list[str] = []
        candidates = self._source.pistes(genre)

        # Une plage thématique sans musique ne fait pas taire la radio : on
        # revient au tirage libre (SPECS.md §4.4).
        if not candidates and genre is not None:
            replis.append(f"plage « {genre} » sans musique : tirage libre")
            candidates = self._source.pistes(None)

        if not candidates:
            message = "la source a répondu, mais elle n'a aucune piste"
            raise FileVide(message)

        # La fenêtre rétrécit plutôt que de bloquer le tirage (SPECS.md §4.2).
        #
        # La boucle se termine toujours : une fenêtre vide n'écarte personne,
        # donc `filtrer` rendrait `candidates`, qui n'est pas vide ici. Un
        # garde-fou supplémentaire serait du code qu'aucun test ne peut
        # atteindre — donc du code mort (AGENTS.md §2).
        autorisees = self._fenetre.filtrer(candidates)
        while not autorisees:
            self._fenetre.retrecir()
            replis.append("fenêtre de non-répétition rétrécie")
            autorisees = self._fenetre.filtrer(candidates)

        return Choix(self._tirer(autorisees), tuple(replis))

    def _tirer(self, parmi: list[Piste]) -> Piste:
        """Un tirage pondéré si les poids sont fournis, uniforme sinon.

        La pondération est une **capacité en plus**, jamais un réglage de la
        première (ARCHITECTURE.md §5.3) : sans `peser`, la file se comporte
        exactement comme avant, et rien de ce qui existait ne change de
        comportement.
        """
        if self._peser is None:
            return self._hasard.choisir(parmi)
        pondere = cast(HasardPondere, self._hasard)
        return pondere.choisir_pondere(parmi, [self._peser(p) for p in parmi])
