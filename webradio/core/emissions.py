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

TOUS_LES_JOURS = "tous"
EPISODE_COMPLET = "full"

JOURS_DE_LA_SEMAINE = {
    "lundi": 0,
    "mardi": 1,
    "mercredi": 2,
    "jeudi": 3,
    "vendredi": 4,
    "samedi": 5,
    "dimanche": 6,
}


class EmissionsEnConflit(Exception):
    """Deux émissions à la même heure le même jour.

    La radio refuse de démarrer en les nommant toutes les deux (SPECS.md §4.11) :
    elle ne choisit pas à votre place, et elle ne joue pas la première venue.
    """


@dataclass(frozen=True, slots=True)
class Emission:
    """Une case déclarée : des jours, une heure. Rien de plus.

    Ce dénuement est délibéré (SPECS.md §4.11) : des champs déclaratifs
    n'exigent aucun analyseur syntaxique et couvrent les deux cas demandés. Une
    grammaire de récurrence n'arrivera qu'avec son deuxième cas d'usage.
    """

    nom: str
    jours: tuple[str, ...]
    heure: time

    def __post_init__(self) -> None:
        if not self.nom:
            message = "une émission sans nom ne peut pas être désignée dans un conflit"
            raise ValueError(message)
        if not self.jours:
            message = f"« {self.nom} » n'a aucun jour : elle n'aurait jamais lieu"
            raise ValueError(message)
        for jour in self.jours:
            if jour != TOUS_LES_JOURS and jour not in JOURS_DE_LA_SEMAINE:
                message = f"jour inconnu pour « {self.nom} » : {jour}"
                raise ValueError(message)

    def a_lieu_le(self, jour: date) -> bool:
        if TOUS_LES_JOURS in self.jours:
            return True
        return any(JOURS_DE_LA_SEMAINE[j] == jour.weekday() for j in self.jours if j != TOUS_LES_JOURS)


@dataclass(frozen=True, slots=True)
class Episode:
    """Un épisode tel que le noyau a besoin de le connaître.

    `nature` porte l'`itunes:episodeType` du flux : c'est ce qui permet
    d'écarter un `bonus` d'une minute trente à l'heure de l'émission.
    """

    guid: str
    publie_le: datetime
    duree: timedelta
    nature: str = EPISODE_COMPLET


@dataclass(frozen=True, slots=True)
class Case:
    """Une émission due, et l'heure à laquelle elle aurait dû commencer.

    Le début sert au rattrapage : l'épisode démarre **depuis le début**, donc
    une émission rattrapée décale sa propre fin (SPECS.md §7 n°13).
    """

    emission: Emission
    debut: datetime


def episode_a_diffuser(episodes: Sequence[Episode], deja_diffuse: str | None = None) -> Episode | None:
    """Le `full` le plus récent, sauf s'il a déjà été diffusé — alors la case est sautée.

    On ne redescend **pas** à l'avant-dernier : « une émission qui n'a rien de
    neuf est une émission qui n'a pas lieu » (SPECS.md §4.11). Rejouer l'épisode
    d'avant serait une rediffusion de plus, pas moins.
    """
    complets = [e for e in episodes if e.nature == EPISODE_COMPLET]
    if not complets:
        return None
    recent = max(complets, key=lambda e: e.publie_le)
    if recent.guid == deja_diffuse:
        return None
    return recent


class Programme:
    """Les cases déclarées, et celle qui est ouverte maintenant.

    Le conflit est refusé **à la construction**, pas au moment de diffuser : une
    configuration fautive empêche le démarrage plutôt que de produire une
    surprise trois jours plus tard (SPECS.md §6).
    """

    def __init__(self, emissions: Sequence[Emission]) -> None:
        self._emissions = tuple(emissions)
        self._refuser_les_conflits()

    @property
    def emissions(self) -> tuple[Emission, ...]:
        return self._emissions

    def _refuser_les_conflits(self) -> None:
        for rang, une in enumerate(self._emissions):
            for autre in self._emissions[rang + 1 :]:
                if une.heure == autre.heure and self._memes_jours(une, autre):
                    message = (
                        f"« {une.nom} » et « {autre.nom} » sont déclarées à "
                        f"{une.heure:%H:%M} le même jour"
                    )
                    raise EmissionsEnConflit(message)

    @staticmethod
    def _memes_jours(une: Emission, autre: Emission) -> bool:
        if TOUS_LES_JOURS in une.jours or TOUS_LES_JOURS in autre.jours:
            return True
        return bool(set(une.jours) & set(autre.jours))

    def debut_de_case(self, emission: Emission, instant: datetime) -> datetime | None:
        """Le début de la case la plus récente déjà commencée, ou `None`.

        La veille est examinée aussi : une case de 23 h 30 est encore en cours à
        00 h 15, et l'oublier aurait fait disparaître les émissions de fin de
        soirée.
        """
        for recul in (0, 1):
            jour = (instant - timedelta(days=recul)).date()
            if not emission.a_lieu_le(jour):
                continue
            debut = datetime.combine(jour, emission.heure, tzinfo=instant.tzinfo)
            if debut <= instant:
                return debut
        return None

    def case_ouverte(
        self,
        emission: Emission,
        duree: timedelta,
        instant: datetime,
    ) -> Case | None:
        """Une case n'est ouverte que pendant la durée de son propre épisode."""
        debut = self.debut_de_case(emission, instant)
        if debut is None or instant >= debut + duree:
            return None
        return Case(emission, debut)

    def due(self, durees: Mapping[str, timedelta], instant: datetime) -> Case | None:
        """La case ouverte maintenant, s'il y en a une.

        `durees` associe un nom d'émission à la durée de son épisode. Une
        émission absente de la table — flux injoignable au branchement — n'est
        pas rattrapée : la radio reste sur la musique (SPECS.md §4.11).

        Si deux cases se recouvrent par la durée de leurs épisodes, c'est **la
        première commencée** qui l'emporte : c'est la même règle que « la
        première finit » (SPECS.md §4.11), et elle ne coupe rien.
        """
        ouvertes: list[Case] = []
        for emission in self._emissions:
            duree = durees.get(emission.nom)
            if duree is None:
                continue
            case = self.case_ouverte(emission, duree, instant)
            if case is not None:
                ouvertes.append(case)
        if not ouvertes:
            return None
        return min(ouvertes, key=lambda c: c.debut)
