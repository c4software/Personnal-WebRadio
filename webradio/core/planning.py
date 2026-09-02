"""La grille effective : ce qui passera vraiment, période par période.

Le TOML déclare des périodes qui se recouvrent (une émission dans une plage,
un programme par-dessus une plage). La radio les arbitre à chaque jonction
(`app/playout.py`) ; ce module fait le même arbitrage sur une journée entière,
d'avance, pour montrer ce qui passera plutôt que ce qui a été déclaré
(GOAL-068).

Aucune règle n'est réécrite ici. Les périodes sont interrogées avec leurs
propres prédicats (`Programming.programme_at`, `Schedule.band_at`,
`Show.a_lieu_le`), dans l'ordre de la diffusion : émission (SPECS.md §4.11),
puis programme (§4.13), puis plage (§4.4). La grille annoncée et la radio
posent ainsi la même question aux mêmes objets.

La journée se balaie par frontières, pas minute par minute : l'occupant ne
peut changer qu'aux heures déclarées, projetées sur les dates de la fenêtre.
Deux intervalles voisins de même occupant sont recollés, ce qui rend à une
plage qui enjambe minuit sa vraie longueur.
"""

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from itertools import pairwise

from webradio.core.bands import Band, Schedule
from webradio.core.programmes import Programme, Programming
from webradio.core.shows import Show, ShowSchedule

# Ce qui peut occuper une période. Une émission n'est pas de la musique, mais
# elle occupe l'antenne.
Content = Band | Programme | Show


@dataclass(frozen=True, slots=True)
class Segment:
    """Une période telle qu'elle passera, et ce qui l'occupe.

    `end` vaut `None` pour une émission sans durée déclarée (podcast, chaîne
    YouTube) : sa durée n'est connue qu'une fois le flux lu.

    `after_show` marque la musique qui reprend après une telle émission : son
    `start` est celui de l'émission, faute de mieux, et seule sa fin est sûre.
    """

    content: Content
    start: datetime
    end: datetime | None = None
    after_show: bool = False


@dataclass(frozen=True, slots=True)
class _Music:
    """Une période occupée par de la musique, bornes connues.

    Distinct de `Segment` parce qu'une période musicale a toujours une fin :
    le typeur le sait, et on évite un garde-fou sur `end is None`.
    """

    content: Programme | Band
    start: datetime
    end: datetime
    after_show: bool = False


class EffectiveSchedule:
    """La grille des périodes qui passeront, journée par journée."""

    def __init__(
        self,
        bands: Schedule,
        programmes: Programming,
        shows: ShowSchedule,
    ) -> None:
        self._plages = bands
        self._programmes = programmes
        self._emissions = shows

    def day(self, midnight: datetime) -> list[Segment]:
        """Les périodes de la journée qui commence à `midnight`, dans l'ordre.

        Une période appartient au jour où elle commence, comme dans
        `Band.covers` : une plage du samedi soir qui finit à 02 h se lit au
        samedi, pas au dimanche. La fenêtre balayée déborde d'un jour de chaque
        côté pour voir entière une période à cheval sur minuit.

        Les trous sont volontaires : hors de toute plage, le tirage est libre
        (SPECS.md §4.4) et rien n'est annoncé.
        """
        veille = midnight - timedelta(days=1)
        lendemain = midnight + timedelta(days=2)
        musique = self._musique(veille, lendemain)
        emissions = self._emissions_de(veille, lendemain)
        for emission in emissions:
            musique = self._interrompre(musique, emission)
        periodes = [
            Segment(m.content, m.start, m.end, after_show=m.after_show) for m in musique
        ] + emissions
        # À début égal, l'émission passe devant, c'est elle qui interrompt.
        periodes.sort(key=lambda p: (p.start, 0 if isinstance(p.content, Show) else 1))
        fin = midnight + timedelta(days=1)
        return [p for p in periodes if midnight <= p.start < fin]

    def next_replacement(self, depuis: datetime, jusqu_a: datetime) -> Segment | None:
        """La première période qui remplacera la file entre ces deux instants,
        ou `None`.

        Une émission remplace toute la programmation (SPECS.md §4.11) ; un
        programme puise sa musique dans une liste, pas dans la file (§4.13).
        Dans les deux cas, ce que la file a préparé pour cette heure ne
        passera pas.
        """
        candidates = self._emissions_de(depuis, jusqu_a)
        candidates += self._programmes_de(depuis, jusqu_a)
        return min(candidates, key=lambda p: p.start, default=None)

    def served_from(self, instant: datetime) -> datetime:
        """Le premier instant, à partir de `instant`, où la file sera servie.

        Un titre tiré pour une heure couverte par un programme ou un direct
        serait jeté à la jonction, et la file serait vide à la reprise. On
        tire donc pour l'heure où le créneau commencera vraiment (GOAL-068).

        Une émission sans durée déclarée ne se saute pas : sa fin est
        inconnue.
        """
        # Borner à une itération par période déclarée : un programme quotidien
        # qui couvre presque toute la journée se rattraperait lui-même le
        # lendemain, et la boucle ne finirait jamais.
        for _ in range(len(self._emissions.shows) + len(self._programmes.programmes)):
            fin = self._fin_de_ce_qui_remplace(instant)
            if fin is None:
                return instant
            instant = fin
        return instant

    def _fin_de_ce_qui_remplace(self, instant: datetime) -> datetime | None:
        """La fin de l'émission ou du programme qui occupe cet instant, sinon `None`."""
        for emission in self._emissions.shows:
            if emission.duration is None:
                continue
            debut = self._emissions.slot_start(emission, instant)
            if debut is not None and instant < debut + emission.duration:
                return debut + emission.duration
        programme = self._programmes.programme_at(instant)
        if programme is None:
            return None
        return self._fin_du_programme(programme, instant)

    def _programmes_de(self, depuis: datetime, jusqu_a: datetime) -> list[Segment]:
        """Les programmes qui s'ouvrent dans la fenêtre.

        Un programme recouvert par un plus court ne s'ouvre pas : c'est
        `Programming` qui tranche, avec la règle de la diffusion (§4.13).
        """
        ouvertures: list[Segment] = []
        jour = depuis.date()
        while jour <= jusqu_a.date():
            for programme in self._programmes.programmes:
                debut = datetime.combine(jour, programme.start, tzinfo=depuis.tzinfo)
                if not depuis <= debut < jusqu_a:
                    continue
                if self._programmes.programme_at(debut) is not programme:
                    continue
                ouvertures.append(Segment(programme, debut, debut + programme.length))
            jour += timedelta(days=1)
        return ouvertures

    @staticmethod
    def _fin_du_programme(programme: Programme, instant: datetime) -> datetime:
        """La fin de l'occurrence en cours, le lendemain si elle enjambe minuit."""
        fin = datetime.combine(instant.date(), programme.end, tzinfo=instant.tzinfo)
        return fin if fin > instant else fin + timedelta(days=1)

    def _musique(self, depuis: datetime, jusqu_a: datetime) -> list[_Music]:
        """La musique de la fenêtre, les intervalles de même occupant recollés."""
        frontieres = self._frontieres(depuis, jusqu_a)
        periodes: list[_Music] = []
        for debut, suite in pairwise(frontieres):
            occupant = self._musique_a(debut + (suite - debut) / 2)
            if occupant is None:
                continue
            precedente = periodes[-1] if periodes else None
            if (
                precedente is not None
                and precedente.content == occupant
                and precedente.end == debut
            ):
                periodes[-1] = replace(precedente, end=suite)
            else:
                periodes.append(_Music(occupant, debut, suite))
        return periodes

    def _musique_a(self, instant: datetime) -> Programme | Band | None:
        """Ce qui tire la musique à cet instant : le programme, sinon la plage.

        Le même ordre qu'à la jonction (`app/playout.py`, SPECS.md §4.13).
        """
        programme = self._programmes.programme_at(instant)
        if programme is not None:
            return programme
        return self._plages.band_at(instant)

    def _frontieres(self, depuis: datetime, jusqu_a: datetime) -> list[datetime]:
        """Les instants où l'occupant peut changer : les heures déclarées.

        Projetées sur chaque date de la fenêtre sans filtrer par jour : une
        heure de trop coupe une période que le recollage répare, alors qu'une
        heure oubliée fausserait la grille.
        """
        heures: set[time] = set()
        for plage in self._plages.bands:
            heures |= {plage.start, plage.end}
        for programme in self._programmes.programmes:
            heures |= {programme.start, programme.end}
        instants = {depuis, jusqu_a}
        jour = depuis.date()
        while jour <= jusqu_a.date():
            for heure in heures:
                instant = datetime.combine(jour, heure, tzinfo=depuis.tzinfo)
                if depuis <= instant <= jusqu_a:
                    instants.add(instant)
            jour += timedelta(days=1)
        return sorted(instants)

    def _emissions_de(self, depuis: datetime, jusqu_a: datetime) -> list[Segment]:
        """Les cases d'émission de la fenêtre, telles que déclarées.

        Seul un direct connaît sa fin d'avance (SPECS.md §4.11) ; sinon la
        durée vient du flux et `end` reste `None`.
        """
        cases: list[Segment] = []
        jour = depuis.date()
        while jour <= jusqu_a.date():
            for emission in self._emissions.shows:
                if not emission.a_lieu_le(jour):
                    continue
                debut = datetime.combine(jour, emission.hour, tzinfo=depuis.tzinfo)
                if not depuis <= debut < jusqu_a:
                    continue
                fin = None if emission.duration is None else debut + emission.duration
                cases.append(Segment(emission, debut, fin))
            jour += timedelta(days=1)
        return cases

    def _interrompre(self, musique: list[_Music], emission: Segment) -> list[_Music]:
        """La musique une fois l'émission passée devant elle.

        Une émission remplace la programmation (SPECS.md §4.11) : le temps
        qu'elle occupe est retiré à la musique. Sans durée déclarée, elle
        coupe la période en deux et la suite est marquée `after_show`.
        """
        if emission.end is None:
            return self._couper(musique, emission.start)
        return self._retirer(musique, emission.start, emission.end)

    @staticmethod
    def _couper(musique: list[_Music], instant: datetime) -> list[_Music]:
        restantes: list[_Music] = []
        for periode in musique:
            if not periode.start <= instant < periode.end:
                restantes.append(periode)
                continue
            if periode.start < instant:
                restantes.append(replace(periode, end=instant))
            restantes.append(replace(periode, start=instant, after_show=True))
        return restantes

    @staticmethod
    def _retirer(musique: list[_Music], debut: datetime, fin: datetime) -> list[_Music]:
        restantes: list[_Music] = []
        for periode in musique:
            if debut >= periode.end or fin <= periode.start:
                restantes.append(periode)
                continue
            if periode.start < debut:
                restantes.append(replace(periode, end=debut))
            if fin < periode.end:
                # Après un direct, la reprise a une heure connue : sa fin est
                # déclarée, contrairement à celle d'un podcast.
                restantes.append(replace(periode, start=fin, after_show=False))
        return restantes
