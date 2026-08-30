"""Doubles versionnés.

Des Fakes, jamais des mocks générés à la volée (AGENTS.md §4) : un Fake se lit,
se pas-à-pas, et son comportement est écrit une fois pour toutes.
"""

from datetime import timedelta

from webradio.core.modeles import Piste
from webradio.core.sources import SourceIndisponible


def piste(
    identifiant: str,
    artiste: str,
    genre: str | None = None,
    secondes: int = 180,
) -> Piste:
    return Piste(
        identifiant=identifiant,
        titre=f"titre {identifiant}",
        artiste=artiste,
        genre=genre,
        duree=timedelta(seconds=secondes),
    )


class FakeSource:
    """Une bibliothèque en mémoire, qui peut aussi tomber en panne sur commande."""

    def __init__(
        self,
        catalogue: list[Piste],
        *,
        injoignable: bool = False,
        listes: dict[str, list[Piste]] | None = None,
    ) -> None:
        self._catalogue = list(catalogue)
        self._listes = dict(listes or {})
        self.injoignable = injoignable
        self.appels = 0

    def _verifier(self) -> None:
        self.appels += 1
        if self.injoignable:
            message = "source d'essai déclarée injoignable"
            raise SourceIndisponible(message)

    def pistes(self, genre: str | None = None) -> list[Piste]:
        self._verifier()
        if genre is None:
            return list(self._catalogue)
        return [p for p in self._catalogue if p.genre == genre]

    def pistes_de(self, artiste: str) -> list[Piste]:
        self._verifier()
        return [p for p in self._catalogue if p.artiste == artiste]

    def genres(self) -> list[str]:
        self._verifier()
        return sorted({p.genre for p in self._catalogue if p.genre is not None})

    def pistes_de_la_liste_de_lecture(self, nom: str) -> list[Piste]:
        """Une liste inconnue rend une liste vide, comme une vraie source : le
        repli se décide au-dessus, avec le contexte."""
        self._verifier()
        return list(self._listes.get(nom, []))

    def entree(self, piste: Piste) -> str:
        """Une entrée factice mais reconnaissable.

        Elle ne consulte pas le catalogue : une source réelle non plus — elle
        construit une adresse depuis l'identifiant, sans vérifier qu'il existe.
        """
        return f"fake://{piste.identifiant}"
