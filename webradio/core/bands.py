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

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta

from webradio.core.clock import Clock
from webradio.core.rng import Random
from webradio.core.runs import Mode
from webradio.core.shows import EVERY_DAY, WEEKDAYS

# Ce qu'une plage peut demander de tirer au sort à sa place (GOAL-037).
RANDOM_THEMES = ("genre", "artist")


@dataclass(frozen=True, slots=True)
class Constraint:
    """Ce qu'une plage impose au tirage : un genre, ou un artiste.

    Jamais les deux — une plage déclare l'un ou l'autre (GOAL-023), et la
    source ne sait de toute façon répondre qu'à une question à la fois.

    `mode` demande en plus que les tirages s'enchaînent (décision n°31) ;
    `run_key` identifie l'occurrence de plage qui a émis la contrainte — c'est
    la clé de remise à zéro des suites, et elle est HORS de l'égalité : une
    plage multi-genres retire un genre à chaque jonction, et la suite doit y
    survivre.
    """

    genre: str | None = None
    artist: str | None = None
    mode: Mode | None = None
    run_key: object | None = field(default=None, compare=False)


# Ce qui sait tirer le thème d'une plage qui a délégué son choix : la plage et
# l'instant, une contrainte ou rien (GOAL-037). Déclaré ici comme un simple
# appel plutôt qu'importé de `core/mystery.py` — ce module-là a besoin de `Band`
# et de `Constraint`, et l'importer en retour ferait un cycle.
ThemeResolver = Callable[["Band", datetime], Constraint | None]


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
    # « Choisis toi-même » : la radio tire un genre ou un artiste de la
    # bibliothèque au début de l'occurrence, et s'y tient jusqu'à sa fin
    # (GOAL-037). Exclusif de `genres` et `artists` — le tirage lui-même vit
    # dans `core/mystery.py`, car il a besoin de la source.
    random_theme: str | None = None
    # Générique d'ouverture et de fermeture — des NOMS de fichiers dans le
    # dossier des jingles, optionnels : absents, rien ne se passe et rien ne
    # se signale, comme tout jingle (SPECS.md §4.3, GOAL-029).
    intro: str | None = None
    outro: str | None = None
    # Aucun jour déclaré = tous les jours — c'est le comportement historique,
    # et le seul qui ne surprenne pas une configuration existante.
    days: tuple[str, ...] = field(default=(EVERY_DAY,))
    # Les tirages de la plage s'enchaînent (décision n°31) : double dose,
    # passionné d'époque ou d'artiste. Combinable avec le thème — et une plage
    # à mode SEUL est un tirage libre enchaîné.
    mode: Mode | None = None

    def __post_init__(self) -> None:
        for jour in self.days:
            if jour != EVERY_DAY and jour not in WEEKDAYS:
                message = f"jour inconnu pour la plage {self.start:%H:%M} : {jour}"
                raise ValueError(message)
        if not self.days:
            message = f"la plage {self.start:%H:%M} n'a aucun jour : elle n'aurait jamais lieu"
            raise ValueError(message)
        if self.random_theme is not None and self.random_theme not in RANDOM_THEMES:
            message = (
                f"thème à tirer inconnu pour la plage {self.start:%H:%M} : "
                f"{self.random_theme} (attendu : {' ou '.join(RANDOM_THEMES)})"
            )
            raise ValueError(message)
        declared = sum((bool(self.genres), bool(self.artists), self.random_theme is not None))
        if declared > 1 or (declared == 0 and self.mode is None):
            message = (
                "une plage déclare des genres, des artistes OU un thème à tirer — "
                "exactement un des trois, sauf à porter un mode seul"
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

    def occurrence_start(self, instant: datetime) -> datetime:
        """Le moment où l'occurrence courante de la plage a commencé.

        C'est la clé qui distingue « la même soirée » de « le samedi suivant » :
        un thème tiré au sort (GOAL-037) vaut pour une occurrence, et retirer ou
        non se décide en comparant ces débuts. Minuit enjambé suit la règle de
        `covers` : l'occurrence appartient au jour où elle commence.

        N'a de sens que si `covers(instant)` est vrai — hors de la plage, il n'y
        a pas d'occurrence courante.
        """
        day = instant.date()
        if self.start > self.end and instant.time() < self.end:
            day = (instant - timedelta(days=1)).date()
        return datetime.combine(day, self.start, tzinfo=instant.tzinfo)


class Schedule:
    """Le genre à tirer maintenant, ou rien du tout.

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une journée entière de
    programmation se déroule alors en une boucle, et se rejoue à l'identique.

    Deux plages qui se recouvrent ne sont pas refusées — la spécification ne
    l'exige que des émissions (SPECS.md §4.11) : c'est **la première déclarée**
    qui l'emporte. Le résultat reste donc déterministe, et l'ordre du TOML est
    une réponse que l'auteur peut donner sans qu'on la lui demande.
    """

    def __init__(
        self,
        bands: Sequence[Band],
        clock: Clock,
        resolve_random_theme: ThemeResolver | None = None,
    ) -> None:
        self._plages = tuple(bands)
        self._horloge = clock
        self._tirer_theme = resolve_random_theme

    @property
    def bands(self) -> tuple[Band, ...]:
        return self._plages

    def current_band(self) -> Band | None:
        return self._band_at(self._horloge.now())

    def _band_at(self, instant: datetime) -> Band | None:
        for band in self._plages:
            if band.covers(instant):
                return band
        return None

    def constraint_to_draw(self, random: Random) -> Constraint | None:
        """La contrainte à imposer à la source, `None` pour un tirage libre.

        Une plage peut déclarer plusieurs genres — ou artistes (SPECS.md §4.4,
        GOAL-023) — alors que la source n'accepte qu'une valeur : c'est le
        hasard injecté qui tranche, pour que la soirée reste rejouable.

        L'horloge n'est lue **qu'une fois** : la plage retenue et l'occurrence
        dont on tire le thème doivent parler du même instant, sinon un morceau
        tiré à 22 h 59 min 59 s pourrait chercher le thème de la plage suivante.
        """
        instant = self._horloge.now()
        band = self._band_at(instant)
        if band is None:
            return None
        # La clé des suites (décision n°31) : l'occurrence, pas la contrainte —
        # une plage multi-genres retire un genre à chaque jonction, et la suite
        # doit y survivre ; l'occurrence suivante, elle, repart à zéro.
        key = (band, band.occurrence_start(instant))
        if band.random_theme is not None:
            if self._tirer_theme is None:
                # Refuser bruyamment plutôt que de tirer librement : une plage
                # « au hasard » sans résolveur passerait pour une plage sans
                # musique, et le défaut de câblage ne s'entendrait pas — il
                # ressemblerait à une bibliothèque mal rangée.
                message = "une plage demande un thème à tirer, mais aucun résolveur n'est fourni"
                raise ValueError(message)
            resolved = self._tirer_theme(band, instant)
            if resolved is None:
                return Constraint(mode=band.mode, run_key=key) if band.mode is not None else None
            return replace(resolved, mode=band.mode, run_key=key)
        if band.artists:
            values = band.artists
            value = values[0] if len(values) == 1 else random.pick(list(values))
            return Constraint(artist=value, mode=band.mode, run_key=key)
        if band.genres:
            values = band.genres
            value = values[0] if len(values) == 1 else random.pick(list(values))
            return Constraint(genre=value, mode=band.mode, run_key=key)
        # Une plage à mode seul : un tirage libre, mais enchaîné.
        return Constraint(mode=band.mode, run_key=key)
