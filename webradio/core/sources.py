"""La frontière entre le noyau et ce qui détient la musique.

Le noyau ne connaît que ce `Protocol`. Navidrome en est la seule implémentation
écrite aujourd'hui ; le mécanisme est néanmoins complet, et c'est un **écart
assumé** à l'interdit d'anticipation d'AGENTS.md §2, consigné dans
ARCHITECTURE.md §9.1.

La conduite qui accompagne cet écart : tant que le registre ne contient qu'une
source, **aucun code ne doit supposer qu'il en contient plusieurs**. Les
questions que soulèverait une deuxième source — comment combiner les tirages,
si la non-répétition vaut par source ou globalement — sont explicitement non
spécifiées (SPECS.md §7 n°12). Y répondre en implémentant serait la seconde
anticipation, celle-là non consignée.
"""

from typing import Protocol

from webradio.core.modeles import Piste


class SourceIndisponible(Exception):
    """La source ne répond pas, ou répond ce qu'on ne sait pas lire.

    Traduite au plus près de son origine : au-dessus des adaptateurs, plus
    personne ne connaît de code HTTP ni de nom d'exception réseau
    (ARCHITECTURE.md §7).
    """


class SourceMusicale(Protocol):
    """Trois capacités, et pas une de plus.

    Tout le reste — la grille, le tirage, la non-répétition — est décidé
    au-dessus et ne dépend d'aucune source.
    """

    def pistes(self, genre: str | None = None) -> list[Piste]:
        """Les pistes disponibles, éventuellement restreintes à un genre.

        Une source qui ne connaît pas le genre demandé rend une liste vide
        plutôt que de lever : le repli sur le tirage libre se décide au-dessus,
        avec le contexte (SPECS.md §4.4).
        """
        ...

    def pistes_de(self, artiste: str) -> list[Piste]:
        """Les autres pistes d'un artiste. C'est ce dont `encore` dépend."""
        ...

    def genres(self) -> list[str]:
        """Les genres que cette source connaît."""
        ...

    def entree(self, piste: Piste) -> str:
        """Ce qu'il faut ouvrir pour entendre cette piste.

        Un chemin ou une URL — la chaîne de diffusion ne fait pas la différence
        et ne l'interprète jamais. C'est ici que l'identifiant opaque de la
        piste redevient quelque chose de lisible, et c'est le seul endroit du
        projet qui sache le faire.
        """
        ...
