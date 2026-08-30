"""La façade que l'API interroge, et le seul endroit qui traduit.

Le noyau parle en `controle.Nature`, `Commande` et `Reponse` ; l'API parle en
`api.Nature`, `Vote` et `Verdict`. **Ce n'est pas une duplication à supprimer** :
c'est ce qui permet à `adapters/web/` de ne rien importer du noyau, et donc de
se tester sans lui. La traduction coûte vingt lignes ; la frontière qu'elle
achète vaut davantage.

Les deux jeux de valeurs coïncident (`"musique"`, `"stop"`…), et un test le
vérifie : le jour où ils divergeront, il cassera ici plutôt qu'à l'exécution.
"""

import threading

from webradio.adapters.web.api import Antenne, Radio, Verdict, Vote
from webradio.adapters.web.api import Nature as NatureWeb
from webradio.core.controle import Commande, Controle, Nature
from webradio.core.modeles import Piste


class RadioEnDirect(Radio):
    """Ce que la radio répond à l'API, à l'instant où on le lui demande.

    Elle ne décide de rien : `Controle` tranche les votes, la `Station` sait si
    la chaîne tourne. Elle observe et elle traduit.
    """

    def __init__(self, controle: Controle, en_diffusion: "CompteurAuditeurs") -> None:
        self._controle = controle
        self._station = en_diffusion
        self._verrou = threading.Lock()
        self._nature = Nature.MUSIQUE
        self._piste: Piste | None = None

    def declarer(self, nature: Nature, piste: Piste | None) -> None:
        """Appelée par le programme à chaque changement de ce qui passe.

        Deux destinataires : le noyau, qui en a besoin pour refuser un vote au
        bon moment, et l'API, qui l'affiche.
        """
        with self._verrou:
            self._nature = nature
            self._piste = piste
        self._controle.declarer(nature)

    def en_diffusion(self) -> bool:
        return self._station.en_antenne

    def antenne(self) -> Antenne | None:
        if not self._station.en_antenne:
            return None
        with self._verrou:
            nature, piste = self._nature, self._piste
        return Antenne(
            nature=NatureWeb(nature.value),
            titre=piste.titre if piste is not None else None,
            artiste=piste.artiste if piste is not None else None,
        )

    def voter(self, vote: Vote) -> Verdict:
        reponse = self._controle.voter(Commande(vote.value))
        return Verdict(accepte=reponse.accepte, motif=reponse.motif or None)


class CompteurAuditeurs:
    """Ce que la façade a besoin de savoir de la station : rien de plus.

    Un `Protocol` d'une seule propriété plutôt qu'une dépendance vers
    `adapters/http` : la façade n'a aucune raison de connaître un serveur.
    """

    def __init__(self) -> None:
        self._en_antenne = False

    @property
    def en_antenne(self) -> bool:
        return self._en_antenne

    def declarer(self, *, en_antenne: bool) -> None:
        self._en_antenne = en_antenne
