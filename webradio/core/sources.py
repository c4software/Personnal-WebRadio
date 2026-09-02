"""Frontière entre le noyau et la source de musique.

Le noyau ne connaît que ce `Protocol`. Subsonic en est la seule implémentation.
Le mécanisme est un écart assumé à l'interdit d'anticipation d'AGENTS.md §2,
consigné dans ARCHITECTURE.md §9.1.

Tant qu'il n'y a qu'une source, aucun code ne doit supposer qu'il y en a
plusieurs. Comment combiner les tirages, ou si la non-répétition vaut par source
ou globalement, n'est pas spécifié (SPECS.md §7 n°12).
"""

from typing import Protocol

from webradio.core.models import Track


class SourceUnavailable(Exception):
    """La source ne répond pas, ou répond quelque chose d'illisible.

    Levée par les adaptateurs : au-dessus, personne ne connaît de code HTTP ni
    d'exception réseau (ARCHITECTURE.md §7).
    """


class MusicSource(Protocol):
    """Ce que le noyau attend d'une source.

    Grille, tirage et non-répétition sont décidés au-dessus et ne dépendent
    d'aucune source.
    """

    def tracks(self, genre: str | None = None) -> list[Track]:
        """Les pistes disponibles, éventuellement restreintes à un genre.

        Un genre inconnu rend une liste vide, pas une exception : le repli sur
        le tirage libre se décide au-dessus (SPECS.md §4.4).
        """
        ...

    def tracks_by(self, artist: str) -> list[Track]:
        """Les pistes d'un artiste, pour `encore`."""
        ...

    def tracks_from_playlist(self, name: str) -> list[Track]:
        """Les pistes d'une liste de lecture, désignée par son nom.

        Le noyau ne connaît que des noms, ceux que le TOML déclare ;
        l'identifiant interne de la source ne remonte jamais (SPECS.md §4.13).

        Une liste introuvable, renommée ou vide rend une liste vide, pas une
        exception : le repli se décide au-dessus (SPECS.md §7 n°21).
        """
        ...

    def genres(self) -> list[str]:
        """Les genres que cette source connaît."""
        ...

    def entry(self, track: Track) -> str:
        """Ce que la chaîne de diffusion doit ouvrir pour jouer cette piste.

        Un chemin ou une URL, que la chaîne de diffusion n'interprète jamais.
        Seule la source sait traduire l'identifiant opaque d'une piste.
        """
        ...
