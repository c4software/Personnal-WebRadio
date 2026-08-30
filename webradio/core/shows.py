"""Quelle émission est due, et quel épisode elle diffuse.

Le noyau ne va chercher aucun flux RSS : les épisodes lui sont **fournis**, comme
les pistes (ARCHITECTURE.md §1.1). Ce module répond à deux questions, et à
aucune autre :

- **une case est-elle ouverte maintenant ?** Une émission manquée est rattrapée
  dans la limite de sa propre durée, depuis le début (SPECS.md §7 n°13) — d'où
  le fait que la durée soit un paramètre : elle n'est connue qu'après lecture du
  flux, et c'est assumé ;
- **quel épisode retenir ?** Le `full` le plus récent non encore diffusé ; s'il a
  déjà été diffusé, la case est **sautée** (SPECS.md §7 n°14).

Une émission **suspend** la grille, la non-répétition et les jingles : pour le
noyau, cela ne se traduit par aucun code ici, mais par l'absence de tirage
pendant sa durée (ARCHITECTURE.md §5.2).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

EVERY_DAY = "tous"
EPISODE_COMPLET = "full"

WEEKDAYS = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


class ConflictingShows(Exception):
    """Deux émissions à la même heure le même jour.

    La radio refuse de démarrer en les nommant toutes les deux (SPECS.md §4.11) :
    elle ne choisit pas à votre place, et elle ne joue pas la première venue.
    """


@dataclass(frozen=True, slots=True)
class Show:
    """Une case déclarée : des jours, une heure. Rien de plus.

    Ce dénuement est délibéré (SPECS.md §4.11) : des champs déclaratifs
    n'exigent aucun analyseur syntaxique et couvrent les deux cas demandés. Une
    grammaire de récurrence n'arrivera qu'avec son deuxième cas d'usage.
    """

    name: str
    days: tuple[str, ...]
    hour: time
    # Un direct n'a pas d'épisode qui se termine de lui-même : sa durée est
    # déclarée, et c'est ce qui borne sa case (SPECS.md §4.11, §7 n°22). `None`
    # pour un podcast, dont la durée se lit dans le flux.
    duration: timedelta | None = None

    @property
    def is_live(self) -> bool:
        return self.duration is not None

    def __post_init__(self) -> None:
        if self.duration is not None and self.duration <= timedelta(0):
            message = f"« {self.name} » a une durée nulle : elle ne diffuserait rien"
            raise ValueError(message)
        if not self.name:
            message = "une émission sans nom ne peut pas être désignée dans un conflit"
            raise ValueError(message)
        if not self.days:
            message = f"« {self.name} » n'a aucun jour : elle n'aurait jamais lieu"
            raise ValueError(message)
        for jour in self.days:
            if jour != EVERY_DAY and jour not in WEEKDAYS:
                message = f"jour inconnu pour « {self.name} » : {jour}"
                raise ValueError(message)

    def a_lieu_le(self, jour: date) -> bool:
        if EVERY_DAY in self.days:
            return True
        return any(WEEKDAYS[j] == jour.weekday() for j in self.days if j != EVERY_DAY)


@dataclass(frozen=True, slots=True)
class Episode:
    """Un épisode tel que le noyau a besoin de le connaître.

    `nature` porte l'`itunes:episodeType` du flux : c'est ce qui permet
    d'écarter un `bonus` d'une minute trente à l'heure de l'émission.
    """

    guid: str
    published_at: datetime
    duration: timedelta
    kind: str = EPISODE_COMPLET


@dataclass(frozen=True, slots=True)
class Slot:
    """Une émission due, et l'heure à laquelle elle aurait dû commencer.

    Le début sert au rattrapage : l'épisode démarre **depuis le début**, donc
    une émission rattrapée décale sa propre fin (SPECS.md §7 n°13).
    """

    show: Show
    start: datetime
    end: datetime | None = None
    """La fin de la case, connue d'avance pour un direct seulement."""


def episode_to_air(episodes: Sequence[Episode], already_aired: str | None = None) -> Episode | None:
    """Le `full` le plus récent, sauf s'il a déjà été diffusé — alors la case est sautée.

    On ne redescend **pas** à l'avant-dernier : « une émission qui n'a rien de
    neuf est une émission qui n'a pas lieu » (SPECS.md §4.11). Rejouer l'épisode
    d'avant serait une rediffusion de plus, pas moins.
    """
    complets = [e for e in episodes if e.kind == EPISODE_COMPLET]
    if not complets:
        return None
    recent = max(complets, key=lambda e: e.published_at)
    if recent.guid == already_aired:
        return None
    return recent


class ShowSchedule:
    # Nommée « GrilleDesEmissions » et non « Programme » : depuis SPECS.md §4.13,
    # un *programme* est une plage de temps alimentée par une liste de lecture
    # (`core/programmes.py`). Deux classes du même nom pour deux choses
    # différentes, c'est une collision que le câblage a révélée.
    """Les cases déclarées, et celle qui est ouverte maintenant.

    Le conflit est refusé **à la construction**, pas au moment de diffuser : une
    configuration fautive empêche le démarrage plutôt que de produire une
    surprise trois jours plus tard (SPECS.md §6).
    """

    def __init__(self, shows: Sequence[Show]) -> None:
        self._emissions = tuple(shows)
        self._refuser_les_conflits()

    @property
    def shows(self) -> tuple[Show, ...]:
        return self._emissions

    def _refuser_les_conflits(self) -> None:
        for index, une in enumerate(self._emissions):
            for autre in self._emissions[index + 1 :]:
                if une.hour == autre.hour and self._memes_jours(une, autre):
                    message = (
                        f"« {une.name} » et « {autre.name} » sont déclarées à "
                        f"{une.hour:%H:%M} le même jour"
                    )
                    raise ConflictingShows(message)

    @staticmethod
    def _memes_jours(une: Show, autre: Show) -> bool:
        if EVERY_DAY in une.days or EVERY_DAY in autre.days:
            return True
        return bool(set(une.days) & set(autre.days))

    def slot_start(self, show: Show, instant: datetime) -> datetime | None:
        """Le début de la case la plus récente déjà commencée, ou `None`.

        La veille est examinée aussi : une case de 23 h 30 est encore en cours à
        00 h 15, et l'oublier aurait fait disparaître les émissions de fin de
        soirée.
        """
        for recul in (0, 1):
            jour = (instant - timedelta(days=recul)).date()
            if not show.a_lieu_le(jour):
                continue
            start = datetime.combine(jour, show.hour, tzinfo=instant.tzinfo)
            if start <= instant:
                return start
        return None

    def open_slot(
        self,
        show: Show,
        duration: timedelta,
        instant: datetime,
    ) -> Slot | None:
        """Une case n'est ouverte que pendant la durée de son propre épisode."""
        start = self.slot_start(show, instant)
        if start is None or instant >= start + duration:
            return None
        return Slot(show, start, start + duration if show.is_live else None)

    def due(self, durations: Mapping[str, timedelta], instant: datetime) -> Slot | None:
        """La case ouverte maintenant, s'il y en a une.

        `durees` associe un nom d'émission à la durée de son épisode. Une
        émission absente de la table — flux injoignable au branchement — n'est
        pas rattrapée : la radio reste sur la musique (SPECS.md §4.11). Un
        **direct** porte sa durée lui-même : sa case est ouverte tant qu'il en
        reste, et il n'y a rien à rattraper (§7 n°22).

        Si deux cases se recouvrent par la durée de leurs épisodes, c'est **la
        première commencée** qui l'emporte : c'est la même règle que « la
        première finit » (SPECS.md §4.11), et elle ne coupe rien.
        """
        ouvertes: list[Slot] = []
        for show in self._emissions:
            duration = show.duration if show.is_live else durations.get(show.name)
            if duration is None:
                continue
            case = self.open_slot(show, duration, instant)
            if case is not None:
                ouvertes.append(case)
        if not ouvertes:
            return None
        return min(ouvertes, key=lambda c: c.start)
