"""Ce que la radio retient des votes, et ce qu'elle en fait au tirage.

C'est la seconde charnière du projet, symétrique de `playout.py` : d'un côté
le noyau, qui sait *combien pèse* un vote et *comment* les scores deviennent un
multiplicateur ; de l'autre la base, qui sait les *conserver*.

**Le noyau ne va jamais chercher un poids** (ARCHITECTURE.md §5.3) : c'est ce
module qui les lui fournit, comme on lui fournit des pistes.

Le noyau et la base ont chacun leur `Scope` et leurs `Scores`. Ce n'est **pas**
une duplication à supprimer : c'est ce qui permet à `adapters/state/` de ne rien
importer du noyau et de se tester sans lui. La traduction tient en deux lignes,
et un test vérifie que les valeurs coïncident — le jour où elles divergeront, il
cassera ici plutôt qu'en base.
"""

import logging

from webradio.adapters.state.database import Scope as PorteeBase
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.core.control import Command
from webradio.core.models import Track
from webradio.core.weighting import Scope, Scores, track_weight, vote_weight

logger = logging.getLogger(__name__)


class Learning:
    """Lit les poids avant un tirage, écrit les votes après qu'ils sont acceptés."""

    def __init__(
        self,
        database: SqliteState,
        *,
        floor: float,
        ceiling: float,
        slope: float,
    ) -> None:
        self._base = database
        self._plancher = floor
        self._plafond = ceiling
        self._pente = slope

    def weigh(self, track: Track) -> float:
        """Le multiplicateur de chance d'une piste, borné.

        Une base injoignable ne fait pas taire la radio : on rend un poids
        neutre et l'on journalise. Un tirage sans mémoire vaut infiniment mieux
        qu'un tirage qui n'a pas lieu (SPECS.md §5).
        """
        try:
            piste_brute = self._base.scores(PorteeBase.TRACK, track.identifier)
            artiste_brut = self._base.scores(PorteeBase.ARTIST, track.artist)
        except StateUnavailable as failure:
            logger.warning("poids indisponibles, tirage neutre : %s", failure)
            return 1.0
        return track_weight(
            Scores(stop=piste_brute.stop, encore=piste_brute.encore),
            Scores(stop=artiste_brut.stop, encore=artiste_brut.encore),
            floor=self._plancher,
            ceiling=self._plafond,
            slope=self._pente,
        )

    def remember(self, command: Command, track: Track) -> None:
        """Enregistre un vote **accepté**, sur la piste et sur son artiste.

        À n'appeler que lorsque le vote a produit un effet : un vote refusé
        pendant un jingle ou une émission ne doit **rien** enregistrer
        (SPECS.md §4.6). Sinon la radio apprendrait de gestes qui n'ont rien
        changé, et l'auditeur pondérerait sans le savoir.
        """
        sur_la_piste = vote_weight(command, Scope.TRACK)
        sur_l_artiste = vote_weight(command, Scope.ARTIST)
        try:
            # Le libellé humain est retenu AU MOMENT du vote : l'identifiant
            # Subsonic est opaque, et personne ne veut lire « CpW34RBmv… »
            # sur la page des votes (GOAL-020).
            self._ecrire(
                PorteeBase.TRACK,
                track.identifier,
                command,
                sur_la_piste,
                label=f"{track.title} — {track.artist}",
            )
            self._ecrire(PorteeBase.ARTIST, track.artist, command, sur_l_artiste)
        except StateUnavailable as failure:
            logger.warning("vote non retenu, la radio continue : %s", failure)

    def _ecrire(
        self,
        scope: PorteeBase,
        target: str,
        command: Command,
        weight: float,
        label: str = "",
    ) -> None:
        if weight == 0.0:
            return
        if command is Command.SKIP:
            self._base.record_vote(scope, target, stop=weight, label=label)
        else:
            self._base.record_vote(scope, target, encore=weight, label=label)
