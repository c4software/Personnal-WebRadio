"""Les programmes : quels jours, quelles heures, quelle liste de lecture.

Un programme puise dans une **sélection faite à la main** (SPECS.md §4.13), là
où une plage thématique (`core/bands.py`) contraint un genre dans toute la
bibliothèque. Les deux répondent à la même question et coexistent
provisoirement (SPECS.md §7 n°19) ; ce module n'en sait rien et ne tranche pas
la priorité — c'est du câblage.

**Ce module ne va chercher aucune piste.** Il dit *quel programme est ouvert*,
et rien d'autre : le noyau ne parle à personne (AGENTS.md §2), et c'est ce qui
permet de dérouler une semaine entière de programmation en une boucle, sans
Navidrome ni réseau.

Le nom de la liste est transporté tel quel jusqu'à la source : le noyau ne
connaît que des noms, jamais l'identifiant opaque que Navidrome leur donne.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time

from webradio.core.clock import Clock

# Les sept jours, dans l'ordre de `datetime.weekday()` — lundi vaut 0. C'est la
# même convention que celle qu'`adapters/config/schema.py` impose aux émissions,
# volontairement recopiée plutôt qu'importée : le noyau ne dépend d'aucun
# adaptateur (ARCHITECTURE.md §2.1).
DAYS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

# Le raccourci d'un programme quotidien. L'écrire évite d'avoir à énumérer les
# sept jours pour dire « tous les jours », ce qu'un TOML ferait mal.
EVERY_DAY = "tous"


@dataclass(frozen=True, slots=True)
class Programme:
    """Un créneau nommé, et la liste de lecture dans laquelle on y tire.

    Un programme dont la fin précède le début enjambe minuit : « 22 h → 02 h »
    est une soirée, pas une erreur de saisie — comme pour une `Plage`.

    **Les jours nomment le jour où le programme commence.** Un programme du
    vendredi 22 h → 02 h couvre donc la nuit du vendredi au samedi : c'est ce
    que l'auteur a voulu dire en écrivant « le vendredi », et compter le samedi
    01 h comme un samedi ferait démarrer le programme une nuit trop tôt.
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

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une semaine entière se
    déroule alors en une boucle, et se rejoue à l'identique.

    Deux programmes qui se recouvrent ne sont pas refusés — la spécification ne
    réserve ce refus qu'aux émissions (SPECS.md §4.11) : c'est **le premier
    déclaré** qui l'emporte, exactement comme les plages de `core/bands.py`.
    Le résultat reste donc déterministe, et l'ordre du TOML est une réponse que
    l'auteur peut donner sans qu'on la lui demande.
    """

    def __init__(self, programmes: Sequence[Programme], clock: Clock) -> None:
        self._programmes = tuple(programmes)
        self._horloge = clock

    @property
    def programmes(self) -> tuple[Programme, ...]:
        return self._programmes

    def current_programme(self) -> Programme | None:
        instant = self._horloge.now()
        for programme in self._programmes:
            if programme.covers(instant):
                return programme
        return None

    def playlist_to_draw(self) -> str | None:
        """Le nom de la liste où tirer maintenant, `None` hors de tout programme.

        C'est un nom, pas un identifiant : la résolution appartient à la source,
        seule à savoir ce que Navidrome appelle une liste (SPECS.md §4.13).
        """
        programme = self.current_programme()
        return None if programme is None else programme.playlist
