"""Les plages thématiques : à quelle heure, quel genre.

**La grille n'est consultée qu'au moment du tirage** (SPECS.md §4.4, décision
n°5). C'est ce qui explique l'absence, ici, de toute notion de « fin de plage » :
un morceau tiré à 09 h 58 dans la plage « jazz » y termine, même s'il déborde de
quatre minutes. Ajouter une durée à connaître d'avance aurait ouvert une famille
de cas limites — et une coupure — pour un gain nul.

Le repli d'une plage sans musique sur le tirage libre n'est pas non plus ici : il
se décide là où l'on sait ce que la source a répondu, c'est-à-dire dans
`core/file.py`, qui le journalise déjà.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import time

from webradio.core.clock import Horloge
from webradio.core.rng import Hasard


@dataclass(frozen=True, slots=True)
class Plage:
    """Une tranche de la journée et le ou les genres qu'on y tire.

    Une plage dont la fin précède le début enjambe minuit : « 22 h → 02 h » est
    une soirée, pas une erreur de saisie.
    """

    debut: time
    fin: time
    genres: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.genres:
            message = "une plage sans genre ne restreint rien : ne pas la déclarer"
            raise ValueError(message)
        if self.debut == self.fin:
            message = f"plage vide : {self.debut} → {self.fin}"
            raise ValueError(message)

    def couvre(self, moment: time) -> bool:
        if self.debut < self.fin:
            return self.debut <= moment < self.fin
        return moment >= self.debut or moment < self.fin


class Grille:
    """Le genre à tirer maintenant, ou rien du tout.

    L'horloge est injectée (ARCHITECTURE.md §3.1) : une journée entière de
    programmation se déroule alors en une boucle, et se rejoue à l'identique.

    Deux plages qui se recouvrent ne sont pas refusées — la spécification ne
    l'exige que des émissions (SPECS.md §4.11) : c'est **la première déclarée**
    qui l'emporte. Le résultat reste donc déterministe, et l'ordre du TOML est
    une réponse que l'auteur peut donner sans qu'on la lui demande.
    """

    def __init__(self, plages: Sequence[Plage], horloge: Horloge) -> None:
        self._plages = tuple(plages)
        self._horloge = horloge

    @property
    def plages(self) -> tuple[Plage, ...]:
        return self._plages

    def plage_courante(self) -> Plage | None:
        moment = self._horloge.maintenant().time()
        for plage in self._plages:
            if plage.couvre(moment):
                return plage
        return None

    def genre_a_tirer(self, hasard: Hasard) -> str | None:
        """Le genre à demander à la source, `None` pour un tirage libre.

        Une plage peut déclarer plusieurs genres (SPECS.md §4.4) alors que la
        source n'en accepte qu'un : c'est le hasard injecté qui tranche, pour
        que la soirée reste rejouable.
        """
        plage = self.plage_courante()
        if plage is None:
            return None
        if len(plage.genres) == 1:
            return plage.genres[0]
        return hasard.choisir(list(plage.genres))
