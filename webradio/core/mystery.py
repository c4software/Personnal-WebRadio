"""Le thème qu'une plage n'a pas voulu choisir elle-même.

Une plage peut déclarer `random = "genre"` ou `random = "artist"` plutôt que
d'énumérer ses valeurs (SPECS.md §4.4) : la radio tire alors dans **toute la
bibliothèque**. Ce tirage ne pouvait pas rester dans `core/bands.py` — il a
besoin de la source, alors qu'une plage n'est qu'une tranche d'horloge.

Le tirage est **figé sur l'occurrence** : une soirée entière garde le genre
sorti à 21 h, et c'est ce qui distingue une plage « au hasard » d'un tirage
libre. La mémoire tient donc en une seule entrée — l'occurrence courante, et
elle seule : rien n'est persisté, une radio qui redémarre retire.
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
        """La contrainte de cette occurrence, `None` s'il n'a pas été possible de tirer.

        `None` n'est pas une panne : c'est le tirage libre, exactement comme une
        plage thématique sans musique (`core/queue.py`). Rien n'est mémorisé
        dans ce cas, pour que la jonction suivante retente — une source qui
        revient au bout de deux minutes ne condamne pas la soirée entière.
        """
        if band.random_theme is None:
            message = f"la plage {band.start:%H:%M} ne demande aucun thème à tirer"
            raise ValueError(message)
        occurrence = band.occurrence_start(instant)
        if occurrence == self._occurrence:
            return self._constraint
        constraint = self._draw(band.random_theme, occurrence)
        if constraint is None:
            return None
        self._occurrence = occurrence
        self._constraint = constraint
        return constraint

    def _draw(self, theme: str, occurrence: datetime) -> Constraint | None:
        try:
            if theme == "genre":
                genres = self._source.genres()
                if genres:
                    return Constraint(genre=self._random.pick(genres))
            else:
                # L'artiste se tire par une piste, et non par une capacité
                # « lister les artistes » ajoutée au `Protocol` : le réservoir
                # voulu est la bibliothèque, et une piste tirée librement en est
                # déjà un échantillon. Une capacité de plus pour un seul appel
                # aurait coûté à toutes les sources à venir.
                tracks = self._source.tracks(None)
                if tracks:
                    return Constraint(artist=self._random.pick(tracks).artist)
        except SourceUnavailable:
            self._report(occurrence, "la source ne répond pas")
            return None
        self._report(occurrence, "la bibliothèque est vide")
        return None

    def _report(self, occurrence: datetime, reason: str) -> None:
        """Une fois par occurrence, pas une fois par morceau.

        Le tirage est retenté à chaque jonction tant qu'il échoue — c'est voulu.
        Le journaliser autant de fois noierait tout le reste sous une plage
        entière de la même ligne, et SPECS.md §5 demande un journal qu'on puisse
        lire.
        """
        if self._reported == occurrence:
            return
        self._reported = occurrence
        logger.warning("thème au hasard non tiré (%s) : la plage tire librement", reason)
