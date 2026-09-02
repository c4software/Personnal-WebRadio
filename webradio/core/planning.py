"""La grille effective : ce qui passera vraiment, période par période.

Le TOML déclare des périodes qui se recouvrent — une émission dans une plage,
un programme par-dessus une plage, une plage dans une autre. La radio les
arbitre à chaque jonction (`app/playout.py`), une seule à la fois ; ce module
fait le même arbitrage **sur une journée entière**, d'avance, pour qu'on
puisse montrer ce qui passera au lieu de ce qui a été déclaré (GOAL-068).

**Aucune règle n'est réécrite ici.** Les périodes sont interrogées avec leurs
propres prédicats — `Programming.programme_at`, `Schedule.band_at`,
`Show.a_lieu_le` — et l'ordre des natures est celui de la diffusion : émission
(SPECS.md §4.11), puis programme (§4.13), puis plage (§4.4). C'est ce qui
interdit à la grille annoncée et à la radio de diverger : elles posent la même
question aux mêmes objets.

La journée se balaie par **frontières**, pas minute par minute : les seuls
instants où l'occupant peut changer sont les heures déclarées, projetées sur
les dates de la fenêtre. Deux intervalles voisins de même occupant sont
recollés — c'est ce qui rend une plage qui enjambe minuit à sa vraie longueur.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from itertools import pairwise

from webradio.core.bands import Band, Schedule
from webradio.core.programmes import Programme, Programming
from webradio.core.shows import Show

# Ce qui peut occuper une période. Une émission n'est pas de la musique, mais
# elle occupe l'antenne, et c'est ce dont une grille parle.
Content = Band | Programme | Show


@dataclass(frozen=True, slots=True)
class Segment:
    """Une période telle qu'elle passera, et ce qui l'occupe.

    `end` vaut `None` pour une émission dont la durée n'est pas déclarée — un
    podcast, une chaîne YouTube : elle ne se connaît qu'une fois le flux lu, et
    l'annoncer serait inventer.

    `after_show` marque la musique qui **reprend après** une telle émission :
    son début est celui de l'émission, faute de mieux, et rien ne dit à quelle
    heure elle recommencera vraiment. Seule sa fin est sûre.
    """

    content: Content
    start: datetime
    end: datetime | None = None
    after_show: bool = False


@dataclass(frozen=True, slots=True)
class _Music:
    """Un morceau de journée occupé par de la musique, bornes connues.

    Un type à part de `Segment` pour une seule raison : une période musicale a
    toujours une fin, et le dire au typeur évite un garde-fou qui ne se
    déclencherait jamais.
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
        shows: Sequence[Show],
    ) -> None:
        self._plages = bands
        self._programmes = programmes
        self._emissions = tuple(shows)

    def day(self, midnight: datetime) -> list[Segment]:
        """Les périodes de la journée qui commence à `midnight`, dans l'ordre.

        Une période appartient au jour où elle **commence** : la fin de soirée
        du samedi qui court jusqu'à 02 h se lit au samedi, et le dimanche ne la
        reliste pas — c'est la règle de `Band.covers`, et celle qu'attend un
        lecteur de grille. La fenêtre balayée déborde donc d'un jour de chaque
        côté, pour qu'une période à cheval soit vue entière.

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
        # À début égal, l'émission passe devant : c'est elle qui interrompt.
        periodes.sort(key=lambda p: (p.start, 0 if isinstance(p.content, Show) else 1))
        fin = midnight + timedelta(days=1)
        return [p for p in periodes if midnight <= p.start < fin]

    def _musique(self, depuis: datetime, jusqu_a: datetime) -> list[_Music]:
        """La musique de la fenêtre, l'occupant recollé d'une frontière à l'autre."""
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

        Le même ordre qu'à la jonction (`app/playout.py`) : un programme est
        plus précis qu'une plage puisqu'il nomme des morceaux (SPECS.md §4.13).
        """
        programme = self._programmes.programme_at(instant)
        if programme is not None:
            return programme
        return self._plages.band_at(instant)

    def _frontieres(self, depuis: datetime, jusqu_a: datetime) -> list[datetime]:
        """Les instants où l'occupant peut changer : les heures déclarées.

        Projetées sur chaque date de la fenêtre sans regarder les jours : une
        heure de trop ne fait que couper une période que le recollage répare,
        là où une heure oubliée en inventerait une.
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
        """Les cases d'émission de la fenêtre, telles qu'elles sont déclarées.

        Seul un direct connaît sa fin d'avance (SPECS.md §4.11) : ailleurs, la
        durée vient du flux, et la case reste ouverte sans borne annonçable.
        """
        cases: list[Segment] = []
        jour = depuis.date()
        while jour <= jusqu_a.date():
            for emission in self._emissions:
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
        """Ce que la musique devient une fois l'émission passée devant elle.

        Une émission **remplace** la programmation (SPECS.md §4.11) : le temps
        qu'elle occupe est retiré à la musique. Sans durée déclarée, elle
        n'occupe rien de mesurable — elle coupe donc la période en deux, et ce
        qui suit est marqué comme reprenant après elle.
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
                # Ce qui reprend après un direct reprend à une heure connue :
                # sa fin est déclarée, contrairement à celle d'un podcast.
                restantes.append(replace(periode, start=fin, after_show=False))
        return restantes
