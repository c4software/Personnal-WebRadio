"""La façade que l'API interroge, et le seul endroit qui traduit.

Le noyau parle en `control.Kind`, `Commande` et `Reponse` ; l'API parle en
`api.Nature`, `Vote` et `Verdict`. **Ce n'est pas une duplication à supprimer** :
c'est ce qui permet à `adapters/web/` de ne rien importer du noyau, et donc de
se tester sans lui. La traduction coûte vingt lignes ; la frontière qu'elle
achète vaut davantage.

Les deux jeux de valeurs coïncident (`"musique"`, `"stop"`…), et un test le
vérifie : le jour où ils divergeront, il cassera ici plutôt qu'à l'exécution.
"""

import threading
from collections.abc import Callable

from webradio.adapters.web.api import Kind as NatureWeb
from webradio.adapters.web.api import OnAir, Radio, Verdict, Vote
from webradio.core.control import Command, Control, Kind
from webradio.core.models import Track


class LiveRadio(Radio):
    """Ce que la radio répond à l'API, à l'instant où on le lui demande.

    Elle ne décide de rien : `Controle` tranche les votes, la `Station` sait si
    la chaîne tourne. Elle observe et elle traduit.
    """

    def __init__(
        self,
        control: Control,
        on_air: "ListenerCount",
        remember: Callable[[Command, Track], None] | None = None,
    ) -> None:
        self._controle = control
        self._station = on_air
        self._retenir = remember
        self._verrou = threading.Lock()
        self._nature = Kind.MUSIC
        self._piste: Track | None = None
        self._libelle: str | None = None

    def declare(self, kind: Kind, track: Track | None, label: str | None = None) -> None:
        """Appelée par le programme à chaque changement de ce qui passe.

        Deux destinataires : le noyau, qui en a besoin pour refuser un vote au
        bon moment, et l'API, qui l'affiche. `label` porte le nom de ce qui n'a
        pas de piste — une émission — parce que le flux, lui, ne porte aucune
        métadonnée (docs/franceinfo.md §1.bis) : ce qui s'affiche est ce qui a
        été déclaré (SPECS.md §4.8, GOAL-015).
        """
        with self._verrou:
            self._nature = kind
            self._piste = track
            self._libelle = label
        self._controle.declare(kind)

    def on_air(self) -> bool:
        return self._station.on_air

    def on_air_now(self) -> OnAir | None:
        if not self._station.on_air:
            return None
        with self._verrou:
            kind, track, label = self._nature, self._piste, self._libelle
        return OnAir(
            kind=NatureWeb(kind.value),
            title=track.title if track is not None else label,
            artist=track.artist if track is not None else None,
        )

    def vote(self, vote: Vote) -> Verdict:
        """Le vote passe au noyau, et n'est retenu que s'il a produit un effet.

        **Un vote refusé n'enregistre rien** (SPECS.md §4.6) : sinon la radio
        apprendrait de gestes qui n'ont rien changé, et l'auditeur pondérerait
        sa bibliothèque sans le savoir.

        Un vote accepté alors qu'aucune piste ne passe — c'est possible entre
        deux morceaux — n'a rien sur quoi porter : il agit, mais il ne
        s'apprend pas.
        """
        command = Command(vote.value)
        answer = self._controle.vote(command)
        if answer.accepted and self._retenir is not None:
            with self._verrou:
                courante = self._piste
            if courante is not None:
                self._retenir(command, courante)
        return Verdict(accepted=answer.accepted, reason=answer.reason or None)


class ListenerCount:
    """Ce que la façade a besoin de savoir de la station : rien de plus.

    Un `Protocol` d'une seule propriété plutôt qu'une dépendance vers
    `adapters/http` : la façade n'a aucune raison de connaître un serveur.
    """

    def __init__(self) -> None:
        self._en_antenne = False

    @property
    def on_air(self) -> bool:
        return self._en_antenne

    def declare(self, *, on_air: bool) -> None:
        self._en_antenne = on_air
