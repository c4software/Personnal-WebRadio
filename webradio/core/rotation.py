"""La règle de non-répétition, et ce qu'elle fait quand elle bloque.

SPECS.md §4.2 : un artiste ne revient pas avant que N **autres artistes** soient
passés. La règle compte des artistes distincts, pas des morceaux — trois titres
d'affilée du même artiste ne comptent que pour un.

Elle est audible, donc elle est de la spécification et non de l'implémentation :
un artiste qui réapparaît toutes les deux pistes s'entend comme un défaut.
"""

from dataclasses import dataclass, field

from webradio.core.models import Piste

DEFAUT_NON_REPETITION = 5


@dataclass
class Fenetre:
    """Les derniers artistes joués, du plus récent au plus ancien.

    `largeur` est le N de SPECS.md §4.2. Une largeur de 0 désactive la règle.
    """

    largeur: int = DEFAUT_NON_REPETITION
    _recents: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.largeur < 0:
            message = "une largeur négative n'a pas de sens : 0 désactive la règle"
            raise ValueError(message)

    @property
    def artistes(self) -> tuple[str, ...]:
        return tuple(self._recents)

    def retenir(self, piste: Piste) -> None:
        """Enregistre un passage.

        Rejouer le même artiste ne l'enfonce pas dans la fenêtre : il est déjà
        le plus récent, et l'y remettre deux fois ferait sortir un artiste de
        plus à chaque titre — la règle compte des artistes, pas des morceaux.
        """
        if piste.artiste in self._recents:
            self._recents.remove(piste.artiste)
        self._recents.insert(0, piste.artiste)
        del self._recents[self.largeur :]

    def autorise(self, piste: Piste) -> bool:
        return piste.artiste not in self._recents

    def filtrer(self, pistes: list[Piste]) -> list[Piste]:
        return [p for p in pistes if self.autorise(p)]

    def retrecir(self) -> bool:
        """Rétrécit la fenêtre d'un cran. Rend False si elle est déjà vide.

        SPECS.md §4.2 : sur une petite bibliothèque ou dans une plage thématique
        étroite, il peut ne rester aucun artiste autorisé. **La radio ne se tait
        pas** — elle relâche la contrainte plutôt que de s'arrêter.
        """
        if not self._recents:
            return False
        self._recents.pop()
        return True
