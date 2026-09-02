"""Le thème qu'une plage n'a pas voulu choisir elle-même.

Une plage peut déclarer `random = "genre"` ou `random = "artist"` plutôt que
d'énumérer ses valeurs (SPECS.md §4.4) : la radio tire alors dans toute la
bibliothèque. Ce tirage a besoin de la source, d'où un module distinct de
`core/bands.py`.

Le tirage est figé sur l'occurrence : une soirée entière garde le thème tiré au
début. La mémoire tient en une seule entrée, l'occurrence courante ; rien n'est
persisté, une radio qui redémarre retire.
"""

import logging
from datetime import datetime

from webradio.core.bands import Band, Constraint
from webradio.core.rng import Random
from webradio.core.sources import MusicSource, SourceUnavailable

logger = logging.getLogger(__name__)


class RandomTheme:
    """Tire le genre ou l'artiste d'une plage, une fois par occurrence."""

    def __init__(self, source: MusicSource, random: Random) -> None:
        self._source = source
        self._random = random
        self._occurrence: datetime | None = None
        self._constraint: Constraint | None = None
        self._reported: datetime | None = None

    def constraint_for(self, band: Band, instant: datetime) -> Constraint | None:
        """La contrainte de cette occurrence, `None` si le tirage n'a pas été possible.

        `None` vaut tirage libre, comme une plage thématique sans musique
        (`core/queue.py`). Rien n'est mémorisé dans ce cas, pour que la jonction
        suivante retente.
        """
        if band.random_theme is None:
            message = f"la plage {band.start:%H:%M} ne demande aucun thème à tirer"
            raise ValueError(message)
        occurrence = band.occurrence_start(instant)
        if occurrence == self._occurrence:
            return self._constraint
        return self._retenir(occurrence, self._draw(band.random_theme, occurrence))

    def redraw(self, band: Band, instant: datetime) -> Constraint | None:
        """Retire un autre thème pour l'occurrence courante (GOAL-057).

        L'ancien thème est écarté du tirage, sauf si la bibliothèque n'en offre
        qu'un ; ce cas est journalisé. Sans thème déjà tiré, c'est un tirage
        ordinaire.
        """
        if band.random_theme is None:
            message = f"la plage {band.start:%H:%M} ne demande aucun thème à tirer"
            raise ValueError(message)
        occurrence = band.occurrence_start(instant)
        previous = self._constraint if occurrence == self._occurrence else None
        exclude = None if previous is None else previous.genre or previous.artist
        constraint = self._draw(band.random_theme, occurrence, exclude)
        if constraint is not None and constraint == previous:
            logger.info("thème retiré : la bibliothèque n'en offre pas d'autre que « %s »", exclude)
        self._occurrence = None
        return self._retenir(occurrence, constraint)

    def _retenir(self, occurrence: datetime, constraint: Constraint | None) -> Constraint | None:
        if constraint is None:
            return None
        self._occurrence = occurrence
        self._constraint = constraint
        return constraint

    def _draw(
        self, theme: str, occurrence: datetime, exclude: str | None = None
    ) -> Constraint | None:
        try:
            if theme == "genre":
                genres = self._source.genres()
                candidates = [g for g in genres if g != exclude] or genres
                if candidates:
                    return Constraint(genre=self._random.pick(candidates))
            else:
                # L'artiste se tire par une piste plutôt que par une méthode de
                # listage des artistes ajoutée au `Protocol` : une piste tirée
                # librement est déjà un échantillon de la bibliothèque, et une
                # méthode de plus aurait coûté à toutes les sources.
                tracks = self._source.tracks(None)
                others = [t for t in tracks if t.artist != exclude] or tracks
                if others:
                    return Constraint(artist=self._random.pick(others).artist)
        except SourceUnavailable:
            self._report(occurrence, "la source ne répond pas")
            return None
        self._report(occurrence, "la bibliothèque est vide")
        return None

    def _report(self, occurrence: datetime, reason: str) -> None:
        """Journalise une fois par occurrence, pas une fois par morceau.

        Le tirage est retenté à chaque jonction tant qu'il échoue. Le journaliser
        à chaque fois rendrait le journal illisible (SPECS.md §5).
        """
        if self._reported == occurrence:
            return
        self._reported = occurrence
        logger.warning("thème au hasard non tiré (%s) : la plage tire librement", reason)
