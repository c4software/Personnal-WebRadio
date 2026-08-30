"""Doubles versionnés.

Des Fakes, jamais des mocks générés à la volée (AGENTS.md §4) : un Fake se lit,
se pas-à-pas, et son comportement est écrit une fois pour toutes.
"""

from datetime import timedelta

from webradio.core.models import Track
from webradio.core.sources import SourceUnavailable


def track(
    identifier: str,
    artist: str,
    genre: str | None = None,
    secondes: int = 180,
) -> Track:
    return Track(
        identifier=identifier,
        title=f"titre {identifier}",
        artist=artist,
        genre=genre,
        duration=timedelta(seconds=secondes),
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

    def genres(self) -> list[str]:
        self._verifier()
        return sorted({p.genre for p in self._catalogue if p.genre is not None})

    def tracks_from_playlist(self, name: str) -> list[Track]:
        """Une liste inconnue rend une liste vide, comme une vraie source : le
        repli se décide au-dessus, avec le contexte."""
        self._verifier()
        return list(self._listes.get(name, []))

    def entry(self, track: Track) -> str:
        """Une entrée factice mais reconnaissable.

        Elle ne consulte pas le catalogue : une source réelle non plus — elle
        construit une adresse depuis l'identifiant, sans vérifier qu'il existe.
        """
        return f"fake://{track.identifier}"
