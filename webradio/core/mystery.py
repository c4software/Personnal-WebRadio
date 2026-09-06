"""Le thème qu'une plage n'a pas voulu choisir elle-même.

Une plage peut déclarer `random = "genre"` ou `random = "artist"` plutôt que
d'énumérer ses valeurs (SPECS.md §4.4) : la radio tire alors dans toute la
bibliothèque. Ce tirage a besoin de la source, d'où un module distinct de
`core/bands.py`.

Le tirage est figé sur l'occurrence : une soirée entière garde le thème tiré au
début. La mémoire porte sur la plage et l'occurrence, parce qu'on ne consulte
pas que l'occurrence courante : la préparation tire chaque titre d'avance sous
le moment de son heure estimée (décision n°34), donc sous des occurrences que
l'antenne n'a pas encore atteintes. Rien n'est persisté : une radio qui
redémarre retire.
"""

import logging
from collections import Counter
from collections.abc import Callable
from datetime import datetime

from webradio.core.bands import Band, Constraint
from webradio.core.models import Track
from webradio.core.rng import Random
from webradio.core.sources import MusicSource, SourceUnavailable

logger = logging.getLogger(__name__)

# Autant de thèmes retenus. Une journée compte quelques occurrences de plages au
# hasard, et la préparation en consulte quelques-unes d'avance ; au-delà, ce
# sont des soirées passées, que personne ne redemandera.
MEMOIRE_MAX = 32


class RandomTheme:
    """Tire le genre ou l'artiste d'une plage, une fois par occurrence."""

    def __init__(self, source: MusicSource, random: Random, min_theme_tracks: int = 0) -> None:
        self._source = source
        self._random = random
        # Titres exigés d'un artiste pour qu'une carte blanche le tire
        # (SPECS.md §7 n°36).
        self._vivier_minimal = min_theme_tracks
        self._tirages: dict[tuple[Band, datetime], Constraint] = {}
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
        retenu = self._tirages.get((band, occurrence))
        if retenu is not None:
            return retenu
        return self._retenir(band, occurrence, self._draw(band.random_theme, occurrence))

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
        previous = self._tirages.pop((band, occurrence), None)
        exclude = None if previous is None else previous.genre or previous.artist
        constraint = self._draw(band.random_theme, occurrence, exclude)
        if constraint is not None and constraint == previous:
            logger.info("thème retiré : la bibliothèque n'en offre pas d'autre que « %s »", exclude)
        return self._retenir(band, occurrence, constraint)

    def _retenir(
        self, band: Band, occurrence: datetime, constraint: Constraint | None
    ) -> Constraint | None:
        if constraint is None:
            return None
        self._tirages[(band, occurrence)] = constraint
        while len(self._tirages) > MEMOIRE_MAX:
            del self._tirages[next(iter(self._tirages))]
        return constraint

    def _draw(
        self, theme: str, occurrence: datetime, exclude: str | None = None
    ) -> Constraint | None:
        try:
            tracks = self._source.tracks(None)
            if theme == "genre":
                # Les genres sont comptés sur le parcours plutôt que demandés
                # à la source : c'est le seul décompte fiable, un genre pouvant
                # être déclaré sans piste (GOAL-049).
                assez = self._assez_fournis(tracks, occurrence, lambda t: t.genre)
                genres = sorted({t.genre for t in assez if t.genre})
                candidates = [g for g in genres if g != exclude] or genres
                if candidates:
                    return Constraint(genre=self._random.pick(candidates))
            else:
                # L'artiste se tire par une piste plutôt que par une méthode de
                # listage des artistes ajoutée au `Protocol` : une piste tirée
                # librement est déjà un échantillon de la bibliothèque, et une
                # méthode de plus aurait coûté à toutes les sources.
                assez = self._assez_fournis(tracks, occurrence, lambda t: t.artist)
                others = [t for t in assez if t.artist != exclude] or assez
                if others:
                    return Constraint(artist=self._random.pick(others).artist)
        except SourceUnavailable:
            self._report(occurrence, "la source ne répond pas")
            return None
        self._report(occurrence, "la bibliothèque est vide")
        return None

    def _assez_fournis(
        self, tracks: list[Track], occurrence: datetime, cle: Callable[[Track], str | None]
    ) -> list[Track]:
        """Les pistes dont le thème a assez de titres pour tenir une occurrence
        (SPECS.md §7 n°36). `cle` dit ce qu'est le thème : l'artiste, le genre.

        Le comptage ne coûte rien : le parcours est déjà chargé.

        Si aucun thème n'atteint le seuil, la contrainte est relâchée plutôt que
        la plage abandonnée, comme la non-répétition le fait déjà
        (SPECS.md §4.2). C'est journalisé une fois par occurrence.
        """
        if self._vivier_minimal <= 1:
            return tracks
        compte = Counter(cle(t) for t in tracks)
        assez = [t for t in tracks if compte[cle(t)] >= self._vivier_minimal]
        if assez:
            return assez
        self._report(
            occurrence,
            f"aucun thème n'a {self._vivier_minimal} titres, le seuil est relâché",
        )
        return tracks

    def _report(self, occurrence: datetime, reason: str) -> None:
        """Journalise une fois par occurrence, pas une fois par morceau.

        Le tirage est retenté à chaque jonction tant qu'il échoue. Le journaliser
        à chaque fois rendrait le journal illisible (SPECS.md §5).
        """
        if self._reported == occurrence:
            return
        self._reported = occurrence
        logger.warning("thème au hasard non tiré (%s) : la plage tire librement", reason)
