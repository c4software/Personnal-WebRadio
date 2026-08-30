"""Les plages thématiques : à quelle heure, quel genre.

**La grille n'est consultée qu'au moment du tirage** (SPECS.md §4.4, décision
n°5). C'est ce qui explique l'absence, ici, de toute notion de « fin de plage » :
un morceau tiré à 09 h 58 dans la plage « jazz » y termine, même s'il déborde de
quatre minutes. Ajouter une durée à connaître d'avance aurait ouvert une famille
de cas limites — et une coupure — pour un gain nul.

Le repli d'une plage sans musique sur le tirage libre n'est pas non plus ici : il
se décide là où l'on sait ce que la source a répondu, c'est-à-dire dans
`core/queue.py`, qui le journalise déjà.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from webradio.core.clock import Clock
from webradio.core.rng import Random
from webradio.core.shows import EVERY_DAY, WEEKDAYS


@dataclass(frozen=True, slots=True)
class Constraint:
    """Ce qu'une plage impose au tirage : un genre, ou un artiste.

    Jamais les deux — une plage déclare l'un ou l'autre (GOAL-023), et la
    source ne sait de toute façon répondre qu'à une question à la fois.
    """

    genre: str | None = None
    artist: str | None = None


@dataclass(frozen=True, slots=True)
class Band:
    """Une tranche de la journée et le ou les genres qu'on y tire.

    Une plage dont la fin précède le début enjambe minuit : « 22 h → 02 h » est
    une soirée, pas une erreur de saisie.
    """

    start: time
    end: time
    genres: tuple[str, ...] = ()
    # Une heure entière d'un seul artiste, ou de quelques-uns (GOAL-023).
    artists: tuple[str, ...] = ()
    # Aucun jour déclaré = tous les jours — c'est le comportement historique,
    # et le seul qui ne surprenne pas une configuration existante.
    days: tuple[str, ...] = field(default=(EVERY_DAY,))

    def __post_init__(self) -> None:
        for jour in self.days:
            if jour != EVERY_DAY and jour not in WEEKDAYS:
                message = f"jour inconnu pour la plage {self.start:%H:%M} : {jour}"
                raise ValueError(message)
        if not self.days:
            message = f"la plage {self.start:%H:%M} n'a aucun jour : elle n'aurait jamais lieu"
            raise ValueError(message)
        if bool(self.genres) == bool(self.artists):
            message = (
                "une plage déclare des genres OU des artistes — ni les deux, ni aucun des deux"
            )
            raise ValueError(message)
        if self.start == self.end:
            message = f"plage vide : {self.start} → {self.end}"
            raise ValueError(message)

    def _a_lieu_le(self, jour: date) -> bool:
        if EVERY_DAY in self.days:
            return True
        return any(WEEKDAYS[j] == jour.weekday() for j in self.days if j != EVERY_DAY)

    def covers(self, instant: datetime) -> bool:
        """L'instant tombe-t-il dans la plage, jour compris ?

        Une plage qui enjambe minuit appartient au jour où elle **commence** :
        « samedi 22 h → 02 h » couvre dimanche 01 h. C'est la même règle que
        les cases d'émission de fin de soirée (`core/shows.py`).
        """
        moment = instant.time()
        if self.start < self.end:
            return self.start <= moment < self.end and self._a_lieu_le(instant.date())
        if moment >= self.start:
            return self._a_lieu_le(instant.date())
        if moment < self.end:
            return self._a_lieu_le((instant - timedelta(days=1)).date())
        return False


class Schedule:
    """Le genre à tirer maintenant, ou rien du tout.

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une journée entière de
    programmation se déroule alors en une boucle, et se rejoue à l'identique.

    Deux plages qui se recouvrent ne sont pas refusées — la spécification ne
    l'exige que des émissions (SPECS.md §4.11) : c'est **la première déclarée**
    qui l'emporte. Le résultat reste donc déterministe, et l'ordre du TOML est
    une réponse que l'auteur peut donner sans qu'on la lui demande.
    """

    def __init__(self, bands: Sequence[Band], clock: Clock) -> None:
        self._plages = tuple(bands)
        self._horloge = clock

    @property
    def bands(self) -> tuple[Band, ...]:
        return self._plages

    def current_band(self) -> Band | None:
        instant = self._horloge.now()
        for band in self._plages:
            if band.covers(instant):
                return band
        return None

    def constraint_to_draw(self, random: Random) -> Constraint | None:
        """La contrainte à imposer à la source, `None` pour un tirage libre.

        Une plage peut déclarer plusieurs genres — ou artistes (SPECS.md §4.4,
        GOAL-023) — alors que la source n'accepte qu'une valeur : c'est le
        hasard injecté qui tranche, pour que la soirée reste rejouable.
        """
        band = self.current_band()
        if band is None:
            return None
        if band.artists:
            values = band.artists
            value = values[0] if len(values) == 1 else random.pick(list(values))
            return Constraint(artist=value)
        values = band.genres
        value = values[0] if len(values) == 1 else random.pick(list(values))
        return Constraint(genre=value)
