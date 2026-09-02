"""La file de lecture : ce qui passe ensuite, et pourquoi.

Elle est tirée, pas poussée (ARCHITECTURE.md §2) : l'encodeur réclame le morceau
suivant quand il en a besoin. Le noyau ne connaît ni le temps réel ni les tampons.

Elle prend de l'avance : `prepare()` résout le morceau suivant pendant que le
courant joue. Un tuyau qui se tarit vide le tampon de l'auditeur et le déconnecte
(docs/ffmpeg.md §2.2).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast

from webradio.core.bands import Constraint
from webradio.core.models import Track
from webradio.core.rng import Random, WeightedRandom
from webradio.core.rotation import Window
from webradio.core.runs import Directive, Runs, era_of
from webradio.core.sources import MusicSource

# Le poids d'une piste, fourni de l'extérieur. Les scores vivent dans une base
# et le noyau n'y accède pas (ARCHITECTURE.md §1.1, §5.3).
Weigh = Callable[[Track], float]


@dataclass(frozen=True, slots=True)
class Pick:
    """Une piste, et les replis qu'il a fallu pour l'obtenir.

    `fallbacks` est journalisé par l'appelant : SPECS.md §5 l'exige.
    """

    track: Track
    fallbacks: tuple[str, ...] = ()


class EmptyQueue(Exception):
    """Aucune piste à servir, même après tous les replis.

    Distinct d'une source injoignable : ici la source a répondu, mais elle est vide.
    """


class Queue:
    """Tire le morceau suivant, en relâchant les contraintes plutôt que de ne rien servir."""

    def __init__(
        self,
        source: MusicSource,
        random: Random,
        window: Window | None = None,
        weigh: Weigh | None = None,
        runs: Runs | None = None,
        lookahead: int = 1,
    ) -> None:
        self._source = source
        self._hasard = random
        self._fenetre = window if window is not None else Window()
        self._peser = weigh
        self._suites = runs
        if lookahead < 1:
            message = "une avance nulle laisserait un trou à chaque jonction (docs/ffmpeg.md §2.2)"
            raise ValueError(message)
        self._profondeur = lookahead
        # Jusqu'à `lookahead` titres dans l'ordre de passage, chacun avec la clé
        # du moment qui l'a tiré (décision n°33). Une entrée dont le moment est
        # fini est rassise et ne passe pas.
        self._avance: list[tuple[Pick, object]] = []
        if weigh is not None and not hasattr(random, "pick_weighted"):
            # Refuser à la construction plutôt qu'au premier tirage : sinon la
            # file tirerait uniformément sans rien signaler.
            message = "des poids sont fournis, mais ce hasard ne sait pas les honorer"
            raise TypeError(message)

    def prepare(self, constraint: Constraint | None = None) -> None:
        """Résout un morceau de plus à l'avance, sans le consommer, si l'avance
        n'est pas pleine.

        À appeler pendant que le courant joue, pour qu'une source lente ne fasse
        pas de trou à la jonction. La contrainte est celle du moment où ce titre
        commencera, estimé par l'appelant (GOAL-058).
        """
        if self.wants_more():
            self._avance.append((self._choisir(constraint), self._cle_de_suite(constraint)))

    def wants_more(self) -> bool:
        return len(self._avance) < self._profondeur

    def revalidate(self, moments: Sequence[object]) -> None:
        """Coupe l'avance à partir de la première entrée dont le moment ne
        correspond plus à son créneau (décision n°33).

        `moments` donne, créneau par créneau, la clé sous laquelle le titre
        aurait dû être tiré. Les entrées qui suivent une entrée rassise sont
        retirées aussi : leurs créneaux ont glissé.
        """
        for index, (_, tire_sous) in enumerate(self._avance):
            attendu = moments[index] if index < len(moments) else None
            if tire_sous != attendu:
                del self._avance[index:]
                return

    @property
    def advance(self) -> tuple[Track, ...]:
        """Les titres en attente, dans l'ordre de passage, sans les consommer."""
        return tuple(pick.track for pick, _ in self._avance)

    @property
    def dated_advance(self) -> tuple[tuple[Track, object], ...]:
        """L'avance avec, pour chaque titre, la clé du moment qui l'a tiré.

        Sert à annoncer ce qui vient (GOAL-054, GOAL-058), pas à décider :
        `next_pick` ne servira ces titres que si leurs moments tiennent. Le
        lecteur compare les clés pour ne pas annoncer une entrée rassise.
        """
        return tuple((pick.track, moment) for pick, moment in self._avance)

    def withdraw(self, identifier: str) -> bool:
        """Retire un titre de l'avance (GOAL-058). Renvoie `False` s'il n'y
        était pas, par exemple s'il a commencé entre-temps."""
        for index, (pick, _) in enumerate(self._avance):
            if pick.track.identifier == identifier:
                del self._avance[index]
                # Un titre retiré compte comme passé pour la fenêtre, sinon le
                # tirage de remplacement pourrait le rendre aussitôt.
                self._fenetre.remember(pick.track)
                return True
        return False

    def break_run(self) -> bool:
        """Rompt la suite en cours : le prochain tirage ouvre une autre suite,
        sur une autre ancre (GOAL-059). Renvoie `False` s'il n'y en a pas."""
        return self._suites is not None and self._suites.break_run()

    def forget_prepared(self) -> None:
        """Vide l'avance : le prochain tirage repart à neuf.

        Le moment ne suffit pas toujours : après une longue pause sans auditeur,
        la même plage peut être encore ouverte, et le tirage neuf de SPECS.md §7
        n°30 s'applique quand même.
        """
        self._avance.clear()

    def next_pick(self, constraint: Constraint | None = None) -> Pick:
        """Le morceau suivant : la tête de l'avance si son moment tient, un
        nouveau tirage sinon.

        Le reste de l'avance est laissé en place : si la tête a été tirée pour
        un moment à venir, les suivants aussi, et ils serviront à leur heure.
        """
        pick = self._fraiche(constraint)
        if pick is None:
            pick = self._choisir(constraint)
        self._fenetre.remember(pick.track)
        return pick

    def _fraiche(self, constraint: Constraint | None) -> Pick | None:
        """Consomme et rend la tête de l'avance si elle a été tirée sous le
        moment de cette contrainte, `None` sinon.

        La clé est celle des suites (`_cle_de_suite`) : une plage multi-genres
        retire un genre à chaque jonction sans changer de moment, son avance
        survit.
        """
        if not self._avance:
            return None
        pick, moment = self._avance[0]
        if moment != self._cle_de_suite(constraint):
            return None
        del self._avance[0]
        return pick

    def _choisir(self, constraint: Constraint | None) -> Pick:
        fallbacks: list[str] = []
        directive = self._directive(constraint)

        # Une suite d'artiste suit l'artiste même si la plage a retiré un autre
        # genre entre-temps, comme l'encore (SPECS.md §4.6). C'est ce qui fait
        # tenir une double dose sur une plage multi-genres.
        candidates: list[Track] = []
        if directive is not None and directive.artist is not None:
            candidates = [
                t
                for t in self._source.tracks_by(directive.artist)
                if t.identifier not in directive.exclude
            ]
            if not candidates:
                fallbacks.append(f"suite rompue : plus rien de « {directive.artist} »")
                directive = None

        if not candidates:
            if constraint is not None and constraint.artist is not None:
                candidates = self._source.tracks_by(constraint.artist)
            else:
                candidates = self._source.tracks(constraint.genre if constraint else None)

            # Une plage sans musique ne fait pas taire la radio : repli sur le
            # tirage libre (SPECS.md §4.4).
            if not candidates and constraint is not None:
                asked = constraint.artist if constraint.artist is not None else constraint.genre
                fallbacks.append(f"plage « {asked} » sans musique : tirage libre")
                candidates = self._source.tracks(None)

            if not candidates:
                message = "la source a répondu, mais elle n'a aucune piste"
                raise EmptyQueue(message)

            # Une plage peut borner ses décennies (GOAL-071). Le filtre est ici
            # parce que c'est ici que l'ancre d'une vague se tire : ancrée hors
            # des décennies déclarées, la vague entière y serait.
            if constraint is not None and constraint.eras:
                datees = [t for t in candidates if era_of(t) in constraint.eras]
                if datees:
                    candidates = datees
                else:
                    annees = ", ".join(str(era) for era in constraint.eras)
                    fallbacks.append(f"rien des années {annees} : décennies ignorées")

            # Une suite d'époque filtre les candidats de la plage : la source
            # n'a pas de requête par époque.
            if directive is not None and directive.era is not None:
                enchaines = [
                    t
                    for t in candidates
                    if era_of(t) == directive.era and t.identifier not in directive.exclude
                ]
                if enchaines:
                    candidates = enchaines
                else:
                    fallbacks.append(f"suite rompue : plus rien des années {directive.era}")
                    directive = None

        if directive is not None and (directive.avoid_artist or directive.avoid_era is not None):
            # Suite rompue sur demande (GOAL-059) : la nouvelle ancre évite
            # l'ancienne, sauf si la bibliothèque n'offre rien d'autre.
            autres = [
                t
                for t in candidates
                if t.artist != directive.avoid_artist and era_of(t) != directive.avoid_era
            ]
            if autres:
                candidates = autres
            else:
                evite = directive.avoid_artist or f"les années {directive.avoid_era}"
                fallbacks.append(f"suite rompue : rien d'autre que « {evite} »")

        if directive is not None and directive.bypass_window:
            # Une suite d'artiste répète l'artiste par construction : elle
            # outrepasse la fenêtre, comme l'encore (SPECS.md §4.6). La fenêtre
            # retient quand même le titre (`next_pick`), la règle reprend à la
            # fin de la suite.
            allowed = candidates
        else:
            # Les artistes déjà en attente comptent comme passés, sinon l'avance
            # les répéterait (GOAL-058). La fenêtre rétrécit plutôt que de
            # bloquer le tirage (SPECS.md §4.2) ; l'attente s'efface en dernier.
            # La boucle se termine : une fenêtre vide n'écarte personne et
            # `candidates` n'est pas vide ici.
            en_attente = {pick.track.artist for pick, _ in self._avance}
            allowed = [
                t for t in self._fenetre.filter_out(candidates) if t.artist not in en_attente
            ]
            while not allowed:
                if not self._fenetre.shrink():
                    fallbacks.append("un artiste déjà en attente repasse")
                    allowed = candidates
                    break
                fallbacks.append("fenêtre de non-répétition rétrécie")
                allowed = [
                    t for t in self._fenetre.filter_out(candidates) if t.artist not in en_attente
                ]

        track = self._tirer(allowed)
        if self._suites is not None:
            self._suites.observe(
                self._cle_de_suite(constraint),
                constraint.mode if constraint is not None else None,
                track,
            )
        return Pick(track, tuple(fallbacks))

    def _directive(self, constraint: Constraint | None) -> Directive | None:
        if self._suites is None:
            return None
        return self._suites.directive(
            self._cle_de_suite(constraint),
            constraint.mode if constraint is not None else None,
        )

    @staticmethod
    def _cle_de_suite(constraint: Constraint | None) -> object:
        """La clé de remise à zéro des suites : l'occurrence de plage si la
        grille l'a donnée, la contrainte elle-même sinon."""
        if constraint is None:
            return None
        return constraint.run_key if constraint.run_key is not None else constraint

    def _tirer(self, parmi: list[Track]) -> Track:
        """Un tirage pondéré si les poids sont fournis, uniforme sinon.

        Sans `weigh`, le comportement est inchangé (ARCHITECTURE.md §5.3).
        """
        if self._peser is None:
            return self._hasard.pick(parmi)
        pondere = cast(WeightedRandom, self._hasard)
        return pondere.pick_weighted(parmi, [self._peser(p) for p in parmi])
