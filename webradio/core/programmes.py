"""Les programmes : quels jours, quelles heures, quelle liste de lecture.

Un programme puise dans une liste de lecture (SPECS.md §4.13), là où une plage
thématique (`core/bands.py`) contraint un genre dans toute la bibliothèque. Les
deux coexistent (SPECS.md §7 n°19) ; la priorité entre eux se règle au câblage,
pas ici.

Ce module ne va chercher aucune piste : il dit quel programme est ouvert, sans
source ni réseau (AGENTS.md §2).

Le nom de la liste est transmis tel quel à la source : le noyau ne connaît pas
l'identifiant que la source lui donne.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from webradio.core.clock import Clock

# Dans l'ordre de `datetime.weekday()`, lundi vaut 0. Même convention que
# `adapters/config/schema.py`, recopiée plutôt qu'importée : le noyau ne dépend
# d'aucun adaptateur (ARCHITECTURE.md §2.1).
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

# Raccourci d'un programme quotidien, pour ne pas énumérer les sept jours.
EVERY_DAY = "all"


@dataclass(frozen=True, slots=True)
class Programme:
    """Un créneau nommé, et la liste de lecture dans laquelle on y tire.

    Un programme dont la fin précède le début enjambe minuit, comme une `Band`.

    Les jours désignent le jour où le programme commence : un programme du
    vendredi 22 h à 02 h couvre la nuit du vendredi au samedi.
    """

    name: str
    playlist: str
    days: tuple[str, ...]
    start: time
    end: time
    # Générique d'ouverture et de fermeture, comme pour une plage (GOAL-029).
    intro: str | None = None
    outro: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            message = "un programme sans nom ne peut être ni journalisé ni annoncé"
            raise ValueError(message)
        if not self.playlist:
            message = f"« {self.name} » ne désigne aucune liste de lecture"
            raise ValueError(message)
        if not self.days:
            message = f"« {self.name} » ne tombe aucun jour : ne pas le déclarer"
            raise ValueError(message)
        for jour in self.days:
            if jour not in DAYS and jour != EVERY_DAY:
                attendus = ", ".join((*DAYS, EVERY_DAY))
                message = f"« {jour} » n'est pas un jour ; attendu l'un de : {attendus}"
                raise ValueError(message)
        if self.start == self.end:
            message = f"programme vide : {self.start} → {self.end}"
            raise ValueError(message)

    @property
    def length(self) -> timedelta:
        """La durée déclarée du programme, minuit enjambé compris.

        Elle tranche un recouvrement : le plus court l'emporte. Le calcul est
        recopié de `core/bands.py` plutôt qu'importé, pour que les deux modules
        restent indépendants.
        """
        jour = date.min
        return (datetime.combine(jour, self.end) - datetime.combine(jour, self.start)) % timedelta(
            days=1
        )

    def covers(self, instant: datetime) -> bool:
        moment = instant.time()
        if self.start < self.end:
            return self.start <= moment < self.end and self._tombe_le(instant.weekday())
        if moment >= self.start:
            return self._tombe_le(instant.weekday())
        if moment < self.end:
            return self._tombe_le((instant.weekday() - 1) % len(DAYS))
        return False

    def _tombe_le(self, indice_du_jour: int) -> bool:
        return EVERY_DAY in self.days or DAYS[indice_du_jour] in self.days


class Programming:
    """Le programme ouvert maintenant, ou aucun.

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une semaine de programmation
    se rejoue à l'identique.

    Deux programmes qui se recouvrent ne sont pas refusés, seules les émissions
    le sont (SPECS.md §4.11) : le plus court l'emporte, comme pour les plages de
    `core/bands.py` (GOAL-068). À durée égale, le premier déclaré gagne, le
    résultat reste déterministe.
    """

    def __init__(self, programmes: Sequence[Programme], clock: Clock) -> None:
        self._programmes = tuple(programmes)
        # `sorted` est stable : deux programmes de même durée restent dans
        # l'ordre du TOML.
        self._par_duree = tuple(sorted(self._programmes, key=lambda p: p.length))
        self._horloge = clock

    @property
    def programmes(self) -> tuple[Programme, ...]:
        return self._programmes

    def current_programme(self) -> Programme | None:
        return self.programme_at(self._horloge.now())

    def programme_at(self, instant: datetime) -> Programme | None:
        for programme in self._par_duree:
            if programme.covers(instant):
                return programme
        return None

    def playlist_to_draw(self) -> str | None:
        """Le nom de la liste où tirer maintenant, `None` hors de tout programme.

        Un nom, pas un identifiant : la résolution appartient à la source
        (SPECS.md §4.13).
        """
        programme = self.current_programme()
        return None if programme is None else programme.playlist
