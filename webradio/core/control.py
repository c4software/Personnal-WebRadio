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


class Command(Enum):
    SKIP = "stop"
    MORE = "encore"


REFUSAL_REASONS = {
    Kind.JINGLE: "un jingle est en cours : on ne passe pas un jingle",
    Kind.NEWS: "un flash d'information est en cours : on ne passe pas un flash",
    Kind.SHOW: "une émission est en cours : on ne passe pas une émission",
}


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
        kind: Kind = Kind.MUSIC,
    ) -> None:
        self._source = source
        self._hasard = random
        self._jingles = jingles
        self._nature = kind
        self._saut_demande = False
        self._encore: More | None = None
        self._servis: set[str] = set()

    @property
    def kind(self) -> Kind:
        return self._nature

    def declare(self, kind: Kind) -> None:
        """Déclare ce qui passe maintenant, ce qui permet les refus."""
        self._nature = kind

    def vote(self, command: Command, playing: Track | None = None) -> Answer:
        """Applique le vote : une voix suffit (SPECS.md §7 n°10).

        `playing` est la chanson à l'antenne au moment du vote, celle qu'un
        `encore` vise (GOAL-067). Deux votes avant la même jonction gardent la
        dernière ancre.
        """
        reason = REFUSAL_REASONS.get(self._nature)
        if reason is not None:
            return Answer(accepted=False, reason=reason)
        if command is Command.SKIP:
            self._saut_demande = True
        else:
            self._encore = More(playing)
            self._jingles.mark_more()
        return Answer(accepted=True)

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

    def track_after_more(self, courant: Track) -> Pick:
        """Même artiste, puis même genre, puis tirage libre ; chaque repli est rapporté.

        L'enchaînement est borné par la bibliothèque, pas par un compteur
        (SPECS.md §7 n°7) : sans morceau non joué de l'artiste, on descend d'un
        cran.
        """
        fallbacks: list[str] = []
        ecartes = self._servis | {courant.identifier}

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
            # (SPECS.md §5.1).
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
