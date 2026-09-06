"""Doubles versionnés.

Des Fakes, jamais des mocks générés à la volée (AGENTS.md §4) : un Fake se lit
et son comportement est écrit une fois pour toutes.
"""

import threading
from datetime import datetime, timedelta

from webradio.adapters.state.database import Scope as PorteeBase
from webradio.adapters.state.database import Scores as ScoresBase
from webradio.adapters.state.database import SqliteState
from webradio.app.playout import RadioProgramme
from webradio.core.control import Kind
from webradio.core.models import Track
from webradio.core.sources import SourceUnavailable


def track(
    identifier: str,
    artist: str,
    genre: str | None = None,
    secondes: int = 180,
    year: int | None = None,
) -> Track:
    return Track(
        identifier=identifier,
        title=f"titre {identifier}",
        artist=artist,
        genre=genre,
        duration=timedelta(seconds=secondes),
        year=year,
    )


class FakeSource:
    """Une bibliothèque en mémoire, qui peut aussi tomber en panne sur commande."""

    def __init__(
        self,
        catalogue: list[Track],
        *,
        injoignable: bool = False,
        listes: dict[str, list[Track]] | None = None,
    ) -> None:
        self._catalogue = list(catalogue)
        self._listes = dict(listes or {})
        self.injoignable = injoignable
        self.appels = 0

    def _verifier(self) -> None:
        self.appels += 1
        if self.injoignable:
            message = "source d'essai déclarée injoignable"
            raise SourceUnavailable(message)

    def tracks(self, genre: str | None = None) -> list[Track]:
        self._verifier()
        if genre is None:
            return list(self._catalogue)
        return [p for p in self._catalogue if p.genre == genre]

    def tracks_by(self, artist: str) -> list[Track]:
        self._verifier()
        return [p for p in self._catalogue if p.artist == artist]

    def tracks_from_playlist(self, name: str) -> list[Track]:
        """Une liste inconnue rend une liste vide, comme une vraie source ; le
        repli se décide au-dessus."""
        self._verifier()
        return list(self._listes.get(name, []))

    def entry(self, track: Track) -> str:
        """Une entrée factice mais reconnaissable.

        Elle ne consulte pas le catalogue, comme une source réelle qui construit
        l'adresse depuis l'identifiant sans vérifier qu'il existe.
        """
        return f"fake://{track.identifier}"


def verrou_tenu(verrou: threading.RLock) -> bool:
    """Vrai si le verrou est tenu au moment de l'appel.

    Le verrou est réentrant : le redemander depuis le fil qui le tient réussit
    toujours, et ne prouverait rien. On le demande donc depuis un fil neuf,
    joint aussitôt, ce qui rend une réponse franche sans attente ni `sleep`
    (AGENTS.md §4).
    """
    reponse: list[bool] = []

    def essayer() -> None:
        pris = verrou.acquire(blocking=False)
        if pris:
            verrou.release()
        reponse.append(pris)

    fil = threading.Thread(target=essayer)
    fil.start()
    fil.join()
    return not reponse[0]


class FakeSourceEpieLeVerrou(FakeSource):
    """Une source qui note, parcours par parcours, si le verrou de la charnière
    était tenu (GOAL-075-T04).

    Un parcours coûte une dizaine d'appels à la vraie source ; le faire sous le
    verrou fait attendre `/playout/next` et `/playing`.
    """

    def epier(self, verrou: threading.RLock) -> None:
        self.parcours: list[tuple[str | None, bool]] = []
        self._verrou_epie = verrou

    def tracks(self, genre: str | None = None) -> list[Track]:
        self.parcours.append((genre, verrou_tenu(self._verrou_epie)))
        return super().tracks(genre)


class FakeProgrammeEpieLeVerrou(RadioProgramme):
    """Un programme qui note, geste par geste, si le verrou de la charnière
    était tenu au moment où sa file a été touchée (GOAL-083-T06).

    La préparation de fond lit et écrit la file dans un autre fil ; tout geste
    venu d'une requête doit donc passer sous le même verrou.
    """

    def epier(self, verrou: threading.RLock) -> None:
        self.verrous: dict[str, bool] = {}
        self._verrou_epie = verrou

    def _tenu(self, geste: str) -> None:
        self.verrous[geste] = verrou_tenu(self._verrou_epie)

    def prepare(self, from_instant: datetime | None = None) -> None:
        self._tenu("prepare")
        super().prepare(from_instant)

    def withdraw(self, identifier: str) -> bool:
        self._tenu("withdraw")
        return super().withdraw(identifier)

    def forget_advance(self) -> None:
        self._tenu("forget_advance")
        super().forget_advance()

    def forget_pending(self) -> None:
        self._tenu("forget_pending")
        super().forget_pending()

    def break_run(self) -> bool:
        self._tenu("break_run")
        return super().break_run()

    def current_moment(self) -> object:
        self._tenu("current_moment")
        return super().current_moment()

    def replay_later(self, entry: str, kind: Kind, track: Track | None, label: str | None) -> None:
        self._tenu("replay_later")
        super().replay_later(entry, kind, track, label)


class FakeEtatQuiCompteSesLectures(SqliteState):
    """Une base qui compte ses lectures de scores (GOAL-075-T05).

    Le tirage libre pèse toute la bibliothèque : lire les scores par candidat
    faisait autant de requêtes qu'il y a de pistes.
    """

    lectures = 0

    def scores(self, scope: PorteeBase, target: str) -> ScoresBase:
        self.lectures += 1
        return super().scores(scope, target)

    def all_scores(self) -> list[tuple[PorteeBase, str, str, ScoresBase]]:
        self.lectures += 1
        return super().all_scores()
