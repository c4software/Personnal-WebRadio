"""La file de lecture : ce qui passe ensuite, et pourquoi.

Elle est **tirée, pas poussée** (ARCHITECTURE.md §2) : c'est l'encodeur qui
réclame le morceau suivant quand il en a besoin. Le noyau ne connaît ni le temps
réel, ni les tampons.

Elle **prend de l'avance** : `preparer()` résout le morceau suivant pendant que
le courant joue. C'est une contrainte que le relevé a imposée
([docs/ffmpeg.md](../../docs/ffmpeg.md) §2.2) — un tuyau qui se tarit ne fait
pas un blanc dans l'audio, il fait un trou dans le temps réel, donc un tampon
qui se vide chez l'auditeur, donc une déconnexion.
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

# Le poids d'une piste, fourni du dehors. La file ne va JAMAIS le chercher :
# les scores vivent dans une base, et le noyau ne parle à personne
# (ARCHITECTURE.md §1.1, §5.3).
Weigh = Callable[[Track], float]


@dataclass(frozen=True, slots=True)
class Pick:
    """Une piste, et ce qui a dû être relâché pour l'obtenir.

    `replis` n'est pas décoratif : SPECS.md §5 demande que chaque repli soit
    journalisé, et c'est ici qu'on sait lesquels ont eu lieu.
    """

    track: Track
    fallbacks: tuple[str, ...] = ()


class EmptyQueue(Exception):
    """Aucune piste ne peut être servie, même après tous les replis.

    Distinct d'une source injoignable : ici la source a répondu, elle n'a rien.
    """


class Queue:
    """Tire le morceau suivant, en relâchant les contraintes plutôt que de se taire."""

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
        # L'avance — jusqu'à `lookahead` titres, dans l'ordre de passage —
        # chacun avec la clé du moment qui l'a tiré (décision n°33) : une
        # avance dont le moment a fini est rassise, elle ne passe pas.
        self._avance: list[tuple[Pick, object]] = []
        if weigh is not None and not hasattr(random, "pick_weighted"):
            # Refuser ici plutôt qu'au premier tirage : une file construite avec
            # des poids et un hasard qui ne sait pas les honorer tirerait
            # uniformément sans que rien ne le signale, et la pondération
            # semblerait « ne pas marcher » des semaines durant.
            message = "des poids sont fournis, mais ce hasard ne sait pas les honorer"
            raise TypeError(message)

    def prepare(self, constraint: Constraint | None = None) -> None:
        """Résout un morceau de plus à l'avance, sans le consommer, tant que
        l'avance n'est pas pleine.

        Appelée pendant que le courant joue. Une source lente coûte alors du
        temps que personne n'attend, au lieu d'un trou à la jonction. La
        contrainte est celle du **moment où ce titre commencera** — c'est
        l'appelant qui l'estime (GOAL-058) ; ici on ne fait que tirer.
        """
        if self.wants_more():
            self._avance.append((self._choisir(constraint), self._cle_de_suite(constraint)))

    def wants_more(self) -> bool:
        return len(self._avance) < self._profondeur

    def revalidate(self, moments: Sequence[object]) -> None:
        """Coupe l'avance à la première entrée dont le moment n'est plus celui
        de son créneau (décision n°33).

        `moments` dit, créneau par créneau, sous quelle clé le titre devrait
        avoir été tiré. Tout ce qui suit une entrée rassise part avec elle :
        les créneaux d'après ont glissé, ils seront retirés.
        """
        for index, (_, tire_sous) in enumerate(self._avance):
            attendu = moments[index] if index < len(moments) else None
            if tire_sous != attendu:
                del self._avance[index:]
                return

    @property
    def advance(self) -> tuple[Track, ...]:
        """Ce qui attend, dans l'ordre de passage — sans le consommer."""
        return tuple(pick.track for pick, _ in self._avance)

    @property
    def dated_advance(self) -> tuple[tuple[Track, object], ...]:
        """L'avance avec, pour chaque titre, la clé du moment qui l'a tiré.

        Elle sert à **dire** ce qui vient (GOAL-054, GOAL-058), jamais à
        décider : c'est ce que `next_pick` servira **si les moments
        tiennent** — celui qui lit compare, et n'annonce pas une avance
        rassise, qui ne passera pas.
        """
        return tuple((pick.track, moment) for pick, moment in self._avance)

    def withdraw(self, identifier: str) -> bool:
        """Retire un titre de l'avance : il ne passera pas (GOAL-058). Faux
        s'il n'y attendait pas — il a pu commencer entre-temps."""
        for index, (pick, _) in enumerate(self._avance):
            if pick.track.identifier == identifier:
                del self._avance[index]
                # Retiré vaut passé pour la fenêtre : sinon, sur une petite
                # bibliothèque, le tirage de remplacement le rendrait aussitôt.
                self._fenetre.remember(pick.track)
                return True
        return False

    def break_run(self) -> bool:
        """Rompt la suite au hasard en cours : le prochain tirage ouvre une
        autre suite, d'une autre ancre (GOAL-059). Faux s'il n'y en a pas."""
        return self._suites is not None and self._suites.break_run()

    def forget_prepared(self) -> None:
        """Jette l'avance déjà résolue : le prochain tirage repart à neuf.

        Le moment ne suffit pas toujours à la juger rassise : après une longue
        pause sans auditeur, la même plage peut être encore ouverte, et le
        « tirage neuf » de SPECS.md §7 n°30 vaut quand même.
        """
        self._avance.clear()

    def next_pick(self, constraint: Constraint | None = None) -> Pick:
        """Le morceau suivant. Sert la tête de l'avance si son moment tient,
        tire sinon — et laisse le reste de l'avance en place : si la tête a
        été tirée pour un moment qui n'est pas encore venu, la suite l'a été
        aussi, et elle servira à son heure."""
        pick = self._fraiche(constraint)
        if pick is None:
            pick = self._choisir(constraint)
        self._fenetre.remember(pick.track)
        return pick

    def _fraiche(self, constraint: Constraint | None) -> Pick | None:
        """La tête de l'avance, consommée, si elle a été tirée sous le moment
        de cette contrainte.

        La clé est celle des suites : l'occurrence de plage — une plage
        multi-genres retire un genre à chaque jonction sans changer de moment,
        et son avance survit — ou la contrainte elle-même, ou rien en tirage
        libre.
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

        # Une suite d'artiste SUIT l'artiste, même si la plage a retiré un
        # autre genre entre-temps : c'est le chemin de l'encore (SPECS.md
        # §4.6), et c'est ce qui fait qu'une « double dose » tient sur une
        # plage multi-genres.
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

            # Une plage — thématique ou d'artiste — sans musique ne fait pas
            # taire la radio : on revient au tirage libre (SPECS.md §4.4).
            if not candidates and constraint is not None:
                asked = constraint.artist if constraint.artist is not None else constraint.genre
                fallbacks.append(f"plage « {asked} » sans musique : tirage libre")
                candidates = self._source.tracks(None)

            if not candidates:
                message = "la source a répondu, mais elle n'a aucune piste"
                raise EmptyQueue(message)

            # Une suite d'époque filtre les candidats de la plage : l'époque
            # traverse les genres, elle n'a pas de requête à elle.
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
            # Une suite rompue sur demande (GOAL-059) : la nouvelle ancre
            # évite l'ancienne — sauf si la bibliothèque n'offre rien d'autre.
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
            # outrepasse la fenêtre, comme l'encore (SPECS.md §4.6). La
            # fenêtre le retient quand même (`next_pick`) : la règle reprend
            # dès la fin de la suite.
            allowed = candidates
        else:
            # La fenêtre voit aussi ce qui ATTEND : un artiste tiré d'avance
            # est déjà « passé » pour les tirages qui suivent, sinon l'avance
            # le répéterait (GOAL-058). Elle rétrécit plutôt que de bloquer le
            # tirage (SPECS.md §4.2) ; l'attente s'efface en dernier — la
            # boucle se termine : une fenêtre vide n'écarte personne, donc
            # `filter_out` rendrait `candidates`, non vide ici.
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
        """La clé de remise à zéro des suites : l'occurrence de plage quand la
        grille l'a donnée, la contrainte elle-même sinon."""
        if constraint is None:
            return None
        return constraint.run_key if constraint.run_key is not None else constraint

    def _tirer(self, parmi: list[Track]) -> Track:
        """Un tirage pondéré si les poids sont fournis, uniforme sinon.

        La pondération est une **capacité en plus**, jamais un réglage de la
        première (ARCHITECTURE.md §5.3) : sans `peser`, la file se comporte
        exactement comme avant, et rien de ce qui existait ne change de
        comportement.
        """
        if self._peser is None:
            return self._hasard.pick(parmi)
        pondere = cast(WeightedRandom, self._hasard)
        return pondere.pick_weighted(parmi, [self._peser(p) for p in parmi])
