"""Les plages thématiques : à quelle heure, quel genre.

La grille n'est consultée qu'au moment du tirage (SPECS.md §4.4, décision n°5).
Il n'y a donc pas de notion de fin de plage : un morceau tiré dans une plage y
termine, même s'il déborde.

Le repli d'une plage sans musique sur le tirage libre se décide dans
`core/queue.py`, qui sait ce que la source a répondu et le journalise.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta

from webradio.core.clock import Clock
from webradio.core.rng import Random
from webradio.core.runs import Mode
from webradio.core.shows import EVERY_DAY, WEEKDAYS

# Les thèmes qu'une plage peut demander de tirer au sort (GOAL-037).
RANDOM_THEMES = ("genre", "artist")


@dataclass(frozen=True, slots=True)
class Constraint:
    """Ce qu'une plage impose au tirage : un genre ou un artiste, jamais les deux.

    Une plage déclare l'un ou l'autre (GOAL-023), et la source ne répond qu'à
    une question à la fois.

    `mode` demande en plus que les tirages s'enchaînent (décision n°31).
    `run_key` identifie l'occurrence de plage qui a émis la contrainte : c'est
    la clé de remise à zéro des suites. Elle est exclue de l'égalité, car une
    plage multi-genres retire un genre à chaque jonction et la suite doit y
    survivre.
    """

    genre: str | None = None
    artist: str | None = None
    mode: Mode | None = None
    run_key: object | None = field(default=None, compare=False)


# Tire le thème d'une plage qui a délégué son choix (GOAL-037). Déclaré ici et
# non dans `core/mystery.py`, qui importe `Band` et `Constraint` : l'importer en
# retour ferait un cycle.
ThemeResolver = Callable[["Band", datetime], Constraint | None]


@dataclass(frozen=True, slots=True)
class Band:
    """Une tranche de la journée et le ou les genres qu'on y tire.

    Une plage dont la fin précède le début enjambe minuit.
    """

    start: time
    end: time
    genres: tuple[str, ...] = ()
    # Un ou plusieurs artistes pour toute la plage (GOAL-023).
    artists: tuple[str, ...] = ()
    # La radio tire un genre ou un artiste de la bibliothèque au début de
    # l'occurrence et s'y tient jusqu'à sa fin (GOAL-037). Exclusif de `genres`
    # et `artists`. Le tirage vit dans `core/mystery.py`, qui a accès à la source.
    random_theme: str | None = None
    # Noms de fichiers dans le dossier des jingles, optionnels. Absents, rien ne
    # se passe ni ne se signale (SPECS.md §4.3, GOAL-029).
    intro: str | None = None
    outro: str | None = None
    # Aucun jour déclaré vaut tous les jours : comportement historique, à garder
    # pour les configurations existantes.
    days: tuple[str, ...] = field(default=(EVERY_DAY,))
    # Les tirages de la plage s'enchaînent (décision n°31). Combinable avec le
    # thème. Une plage à mode seul est un tirage libre enchaîné.
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

    @property
    def length(self) -> timedelta:
        """La durée déclarée de la plage, minuit enjambé compris.

        Elle tranche un recouvrement : la plus courte l'emporte (SPECS.md §4.4).
        Le calcul est recopié dans `core/programmes.py` plutôt qu'importé, pour
        que les deux modules restent indépendants.
        """
        jour = date.min
        return (datetime.combine(jour, self.end) - datetime.combine(jour, self.start)) % timedelta(
            days=1
        )

    def _a_lieu_le(self, jour: date) -> bool:
        if EVERY_DAY in self.days:
            return True
        return any(WEEKDAYS[j] == jour.weekday() for j in self.days if j != EVERY_DAY)

    def covers(self, instant: datetime) -> bool:
        """L'instant tombe-t-il dans la plage, jour compris ?

        Une plage qui enjambe minuit appartient au jour où elle commence : une
        plage du samedi 22 h à 02 h couvre le dimanche 01 h. Même règle que
        les cases d'émission de `core/shows.py`.
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
        """Le début de l'occurrence courante de la plage.

        Un thème tiré au sort (GOAL-037) vaut pour une occurrence : comparer ces
        débuts dit s'il faut retirer. Minuit enjambé suit la règle de `covers`.

        N'a de sens que si `covers(instant)` est vrai.
        """
        day = instant.date()
        if self.start > self.end and instant.time() < self.end:
            day = (instant - timedelta(days=1)).date()
        return datetime.combine(day, self.start, tzinfo=instant.tzinfo)


class Schedule:
    """Le genre à tirer maintenant, ou rien.

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une journée de programmation
    se rejoue à l'identique.

    Deux plages qui se recouvrent ne sont pas refusées, seules les émissions le
    sont (SPECS.md §4.11) : la plus courte l'emporte (GOAL-068). À durée égale,
    la première déclarée gagne, le résultat reste déterministe.
    """

    def __init__(
        self,
        bands: Sequence[Band],
        clock: Clock,
        resolve_random_theme: ThemeResolver | None = None,
    ) -> None:
        self._plages = tuple(bands)
        # `sorted` est stable : deux plages de même durée restent dans l'ordre du TOML.
        self._par_duree = tuple(sorted(self._plages, key=lambda plage: plage.length))
        self._horloge = clock
        self._tirer_theme = resolve_random_theme

    @property
    def bands(self) -> tuple[Band, ...]:
        return self._plages

    def current_band(self) -> Band | None:
        return self._band_at(self._horloge.now())

    def band_at(self, instant: datetime) -> Band | None:
        """La plage qui couvre cet instant, pour estimer celle d'un titre tiré
        d'avance (GOAL-058)."""
        return self._band_at(instant)

    def current_moment(self) -> object:
        """La clé de l'occurrence de plage en cours, `None` hors de toute plage.

        Clé des suites (décision n°31) et de l'avance (décision n°33) : une
        entrée tirée sous une autre clé est rassise.
        """
        return self.moment_at(self._horloge.now())

    def moment_at(self, instant: datetime) -> object:
        band = self._band_at(instant)
        if band is None:
            return None
        return self._moment_key(band, instant, self._resolve(band, instant))

    @staticmethod
    def _moment_key(band: Band, instant: datetime, resolved: Constraint | None) -> object:
        """L'occurrence et, pour une plage au hasard, le thème tiré.

        Retirer le thème (GOAL-057) ouvre un nouveau moment : l'avance tirée
        sous l'ancien devient rassise (décision n°33). Retirer le même thème ne
        change rien.
        """
        occurrence = band.occurrence_start(instant)
        if band.random_theme is None:
            return (band, occurrence)
        theme = None if resolved is None else (resolved.genre, resolved.artist)
        return (band, occurrence, theme)

    def _resolve(self, band: Band, instant: datetime) -> Constraint | None:
        if band.random_theme is None:
            return None
        if self._tirer_theme is None:
            # Refuser plutôt que tirer librement : sans résolveur, la plage
            # passerait pour une plage sans musique et le défaut de câblage
            # resterait invisible.
            message = "une plage demande un thème à tirer, mais aucun résolveur n'est fourni"
            raise ValueError(message)
        return self._tirer_theme(band, instant)

    def _band_at(self, instant: datetime) -> Band | None:
        for band in self._par_duree:
            if band.covers(instant):
                return band
        return None

    def constraint_to_draw(self, random: Random, at: datetime | None = None) -> Constraint | None:
        """La contrainte à imposer à la source, `None` pour un tirage libre.

        Une plage peut déclarer plusieurs genres ou artistes (SPECS.md §4.4,
        GOAL-023) alors que la source n'accepte qu'une valeur : le hasard
        injecté tranche, pour que le tirage reste rejouable.

        L'horloge n'est lue qu'une fois : la plage retenue et l'occurrence dont
        on tire le thème doivent correspondre au même instant. `at` remplace
        l'instant présent par le début estimé du titre (GOAL-058).
        """
        instant = self._horloge.now() if at is None else at
        band = self._band_at(instant)
        if band is None:
            return None
        # La clé des suites (décision n°31) est l'occurrence, pas la contrainte :
        # une plage multi-genres retire un genre à chaque jonction et la suite
        # doit y survivre. L'occurrence suivante repart à zéro.
        resolved = self._resolve(band, instant)
        key = self._moment_key(band, instant, resolved)
        if band.random_theme is not None:
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
        # Plage à mode seul : tirage libre enchaîné.
        return Constraint(mode=band.mode, run_key=key)
