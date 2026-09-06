"""`stop` et `encore` : leur effet, et ce qu'ils refusent.

Ce sont des décisions, donc du noyau (ARCHITECTURE.md §6) : leur effet se teste
sans Flask ni HTTP. L'API traduit un refus en réponse HTTP, elle ne le décide pas.

Trois règles :

- une voix suffit, ni quorum ni dépouillement (SPECS.md §7 n°10) ;
- un refus est explicite et motivé (SPECS.md §4.6), sinon il est indistinguable
  d'une panne ;
- `encore` outrepasse la non-répétition (SPECS.md §7 n°7), et les morceaux qu'il
  sert n'entrent pas dans la fenêtre, sinon un long enchaînement bloquerait
  l'artiste longtemps après. C'est pourquoi aucune `Window` n'apparaît ici.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.queue import EmptyQueue, Pick
from webradio.core.rng import Random
from webradio.core.sources import MusicSource


class Kind(Enum):
    """La nature de ce qui passe à l'antenne. C'est elle qui décide des refus."""

    MUSIC = "musique"
    JINGLE = "jingle"
    NEWS = "flash"
    SHOW = "emission"
    # Un processus qui vient de démarrer n'a reçu aucune annonce du diffuseur,
    # qui n'annonce qu'au début d'une entrée : il ne sait pas ce qui passe et
    # ne peut pas juger un vote (SPECS.md §7 n°42).
    UNKNOWN = "inconnu"


class Command(Enum):
    SKIP = "stop"
    MORE = "encore"


# Combien de titres passés à l'antenne l'encore garde en mémoire. Sans borne,
# la mémoire finirait par écarter tout l'artiste après quelques mois de
# diffusion, et le repli sur le genre deviendrait la règle (SPECS.md §4.6).
PLAYED_MAX = 200


REFUSAL_REASONS = {
    Kind.JINGLE: "un jingle est en cours : on ne passe pas un jingle",
    Kind.NEWS: "un flash d'information est en cours : on ne passe pas un flash",
    Kind.SHOW: "une émission est en cours : on ne passe pas une émission",
    Kind.UNKNOWN: "la radio vient de redémarrer : elle ne sait pas encore ce qui passe",
}

# Un épisode de plage se passe, mais on ne demande pas « encore » d'une
# émission : il n'y a ni artiste ni genre à prolonger (SPECS.md §7 n°44).
ENCORE_PENDANT_UNE_EMISSION = (
    "une émission est en cours : on ne demande pas « encore » d'une émission"
)

# Passer un épisode, c'est en piocher un autre. Sans autre épisode neuf, il n'y
# a rien à mettre à la place (SPECS.md §4.11, §7 n°44).
SANS_AUTRE_EPISODE = "aucun autre épisode à piocher : l'épisode finit"


@dataclass(frozen=True, slots=True)
class Answer:
    """Le sort d'un vote. `reason` est vide quand il est accepté.

    Le motif permet à l'auditeur de distinguer un refus d'une panne
    (ARCHITECTURE.md §6.1).
    """

    accepted: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class More:
    """Un `encore` à honorer, et la chanson qu'il visait.

    L'ancre est la chanson que l'auditeur entendait en votant, pas celle de la
    jonction (déjà `encore.mp3`) ni le morceau d'avance, qui a toujours un titre
    d'écart (docs/liquidsoap.md §3, GOAL-067). `None` quand le vote est tombé
    entre deux morceaux : l'encore agit, sans rien à forcer.
    """

    anchor: Track | None


class Control:
    """L'effet des deux commandes sur ce que la file rendra ensuite."""

    def __init__(
        self,
        source: MusicSource,
        random: Random,
        jingles: Jingles,
        kind: Kind = Kind.UNKNOWN,
        *,
        another_episode: Callable[[], bool] | None = None,
    ) -> None:
        self._source = source
        self._hasard = random
        self._jingles = jingles
        self._nature = kind
        # Ce qui passe est-il un épisode de plage, donc passable ? Déclaré avec
        # la nature, parce que seule la charnière sait d'où vient l'entrée.
        self._passable = False
        # Y a-t-il un autre épisode neuf à piocher ? Lu au moment du vote, pas
        # à la déclaration : une case peut s'être fermée entre-temps, et un
        # drapeau posé il y a une heure mentirait (SPECS.md §7 n°44). Sans
        # rappel, un épisode passable ne l'est pas : rien ne garantit qu'il y a
        # de quoi le remplacer.
        self._autre_episode = another_episode
        self._saut_demande = False
        self._encore: More | None = None
        self._servis: set[str] = set()
        # Ce que la file a passé à l'antenne. « Non joué » (SPECS.md §4.6) ne se
        # limite pas à ce que l'encore a servi lui-même : la file joue b1 puis
        # b2, et un encore sur b2 rendait b1, qui venait de passer.
        self._joues: deque[str] = deque(maxlen=PLAYED_MAX)

    @property
    def kind(self) -> Kind:
        return self._nature

    @property
    def skippable(self) -> bool:
        return self._passable

    def declare(self, kind: Kind, *, skippable: bool = False) -> None:
        """Déclare ce qui passe maintenant, ce qui permet les refus.

        `skippable` marque un épisode d'une plage de podcasts : celui-là se
        passe, en piochant un autre épisode (SPECS.md §7 n°44).
        """
        self._nature = kind
        self._passable = skippable

    def vote(self, command: Command, playing: Track | None = None) -> Answer:
        """Applique le vote : une voix suffit (SPECS.md §7 n°10).

        `playing` est la chanson à l'antenne au moment du vote, celle qu'un
        `encore` vise (GOAL-067). Deux votes avant la même jonction gardent la
        dernière ancre.
        """
        if self._nature is Kind.SHOW:
            refus = self._refus_pendant_une_emission(command)
            if refus is not None:
                return refus
        else:
            reason = REFUSAL_REASONS.get(self._nature)
            if reason is not None:
                return Answer(accepted=False, reason=reason)
        if command is Command.SKIP:
            self._saut_demande = True
        else:
            self._encore = More(playing)
            self._jingles.mark_more()
        return Answer(accepted=True)

    def _refus_pendant_une_emission(self, command: Command) -> Answer | None:
        """Le refus qui s'applique pendant une émission, ou `None` si le vote
        passe.

        Seul un `stop` sur un épisode de plage passe, et seulement s'il reste
        un épisode neuf à piocher : la question se pose au réseau de la
        charnière, pas ici (SPECS.md §7 n°44).
        """
        if command is Command.MORE:
            return Answer(accepted=False, reason=ENCORE_PENDANT_UNE_EMISSION)
        if not self._passable:
            return Answer(accepted=False, reason=REFUSAL_REASONS[Kind.SHOW])
        if self._autre_episode is None or not self._autre_episode():
            return Answer(accepted=False, reason=SANS_AUTRE_EPISODE)
        return None

    def take_skip(self) -> bool:
        """Vrai s'il y a un `stop` à honorer. L'appel le consomme."""
        requested = self._saut_demande
        self._saut_demande = False
        return requested

    def take_more(self) -> More | None:
        """L'`encore` à honorer avec son ancre, ou `None`. L'appel le consomme.

        `encore` porte sur le morceau suivant seulement, pas sur toute la suite
        (SPECS.md §4.6).
        """
        requested = self._encore
        self._encore = None
        return requested

    def played(self, track: Track) -> None:
        """Retient un titre passé à l'antenne, pour que l'encore ne le rende pas.

        À appeler à la prise d'antenne, pas à la demande : l'avance du diffuseur
        peut être jetée sans passer (docs/liquidsoap.md §3).
        """
        if track.identifier in self._joues:
            self._joues.remove(track.identifier)
        self._joues.append(track.identifier)

    def track_after_more(self, courant: Track) -> Pick:
        """Même artiste, puis même genre, puis tirage libre ; chaque repli est rapporté.

        L'enchaînement est borné par la bibliothèque, pas par un compteur
        (SPECS.md §7 n°7) : sans morceau non joué de l'artiste, on descend d'un
        cran.
        """
        fallbacks: list[str] = []
        ecartes = self._servis | set(self._joues) | {courant.identifier}

        candidates = [
            p for p in self._source.tracks_by(courant.artist) if p.identifier not in ecartes
        ]

        if not candidates:
            fallbacks.append(f"artiste « {courant.artist} » épuisé")
            if courant.genre is None:
                fallbacks.append("morceau sans genre : tirage libre")
            else:
                candidates = [
                    p for p in self._source.tracks(courant.genre) if p.identifier not in ecartes
                ]
                if not candidates:
                    fallbacks.append(f"genre « {courant.genre} » épuisé : tirage libre")

        if not candidates:
            candidates = [p for p in self._source.tracks(None) if p.identifier not in ecartes]
            # Quand toute la bibliothèque a été servie, on relâche l'exclusion
            # des morceaux déjà servis plutôt que de faire taire la radio
            # (SPECS.md §5.1). La mémoire des titres passés n'est pas vidée :
            # elle est bornée et se renouvelle d'elle-même, et la vider ferait
            # revenir aussitôt ce qui vient de passer.
            if not candidates:
                self._servis.clear()
                fallbacks.append("bibliothèque entièrement servie : la chaîne repart")
                candidates = self._source.tracks(None)

        if not candidates:
            message = "la source a répondu, mais elle n'a aucune piste"
            raise EmptyQueue(message)

        choisi = self._hasard.pick(candidates)
        self._servis.add(choisi.identifier)
        return Pick(choisi, tuple(fallbacks))
