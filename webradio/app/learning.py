"""Ce que la radio retient des votes, et ce qu'elle en fait au tirage.

Le noyau sait combien pèse un vote et comment les scores deviennent un
multiplicateur ; la base sait les conserver. Le noyau ne va jamais chercher un
poids (ARCHITECTURE.md §5.3) : ce module les lui fournit.

Le noyau et la base ont chacun leur `Scope` et leurs `Scores`. Ce n'est pas une
duplication : c'est ce qui permet à `adapters/state/` de ne rien importer du
noyau. La traduction tient ici, et un test vérifie que les valeurs coïncident.
"""

import logging
from collections.abc import Mapping, Sequence

from webradio.adapters.state.database import Scope as PorteeBase
from webradio.adapters.state.database import Scores as ScoresBase
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

    def weigh(self, tracks: Sequence[Track]) -> list[float]:
        """Les multiplicateurs de chance de ces pistes, bornés, dans leur ordre.

        Les scores sont lus en une fois pour tout le tirage. Deux requêtes par
        candidat coûtaient 1,3 s sur une bibliothèque de 5 700 pistes, à chaque
        tirage libre (GOAL-075-T05) ; la table des votes, elle, ne compte que
        les cibles votées. `all_scores` applique la même décroissance à la
        lecture que `scores` (ARCHITECTURE.md §5.2).

        Une base injoignable ne fait pas taire la radio : on rend des poids
        neutres et on journalise (SPECS.md §5).
        """
        try:
            releve = {
                (scope, cible): valeurs for scope, cible, _, valeurs in self._base.all_scores()
            }
        except StateUnavailable as failure:
            logger.warning("poids indisponibles, tirage neutre : %s", failure)
            return [1.0] * len(tracks)
        return [self._poids(piste, releve) for piste in tracks]

    def _poids(self, track: Track, releve: Mapping[tuple[PorteeBase, str], ScoresBase]) -> float:
        piste_brute = releve.get((PorteeBase.TRACK, track.identifier), ScoresBase())
        artiste_brut = releve.get((PorteeBase.ARTIST, track.artist), ScoresBase())
        return track_weight(
            Scores(stop=piste_brute.stop, encore=piste_brute.encore),
            Scores(stop=artiste_brut.stop, encore=artiste_brut.encore),
            floor=self._plancher,
            ceiling=self._plafond,
            slope=self._pente,
        )

    def remember(self, command: Command, track: Track) -> None:
        """Enregistre un vote accepté, sur la piste et sur son artiste.

        À n'appeler que si le vote a produit un effet : un vote refusé pendant
        un jingle ou une émission ne doit rien enregistrer (SPECS.md §4.6).
        """
        sur_la_piste = vote_weight(Scope.TRACK)
        sur_l_artiste = vote_weight(Scope.ARTIST)
        try:
            # Le libellé est retenu au moment du vote : l'identifiant Subsonic
            # est opaque et illisible sur la page des votes (GOAL-020).
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
