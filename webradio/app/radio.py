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
from collections.abc import Callable

from webradio.adapters.web.api import Antenne, Radio, Verdict, Vote
from webradio.adapters.web.api import Nature as NatureWeb
from webradio.core.controle import Commande, Controle, Nature
from webradio.core.modeles import Piste


class RadioEnDirect(Radio):
    """Ce que la radio répond à l'API, à l'instant où on le lui demande.

    Elle ne décide de rien : `Controle` tranche les votes, la `Station` sait si
    la chaîne tourne. Elle observe et elle traduit.
    """

    def __init__(
        self,
        controle: Controle,
        en_diffusion: "CompteurAuditeurs",
        retenir: Callable[[Commande, Piste], None] | None = None,
    ) -> None:
        self._controle = controle
        self._station = en_diffusion
        self._retenir = retenir
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
        """Le vote passe au noyau, et n'est retenu que s'il a produit un effet.

        **Un vote refusé n'enregistre rien** (SPECS.md §4.6) : sinon la radio
        apprendrait de gestes qui n'ont rien changé, et l'auditeur pondérerait
        sa bibliothèque sans le savoir.

        Un vote accepté alors qu'aucune piste ne passe — c'est possible entre
        deux morceaux — n'a rien sur quoi porter : il agit, mais il ne
        s'apprend pas.
        """
        commande = Commande(vote.value)
        reponse = self._controle.voter(commande)
        if reponse.accepte and self._retenir is not None:
            with self._verrou:
                courante = self._piste
            if courante is not None:
                self._retenir(commande, courante)
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
