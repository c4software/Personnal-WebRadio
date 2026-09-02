"""La façade que l'API interroge, et le seul endroit qui traduit.

Le noyau parle en `control.Kind`, `Command` et `Answer` ; l'API parle en
`api.Kind`, `Vote` et `Verdict`. Cette traduction n'est pas une duplication à
supprimer : elle permet à `adapters/web/` de ne rien importer du noyau, et donc
de se tester sans lui.

Les deux jeux de valeurs coïncident (`"musique"`, `"stop"`), et un test le
vérifie.
"""

import threading
from collections.abc import Callable

from webradio.adapters.web.api import Kind as NatureWeb
from webradio.adapters.web.api import (
    OnAir,
    PlayedEntry,
    Radio,
    UpcomingEntry,
    Verdict,
    Vote,
    VoteScore,
)
from webradio.core.control import Command, Control, Kind
from webradio.core.models import Track

# Motif de refus d'un retirage hors d'une plage au hasard, ou sans câblage
# pour retirer (SPECS.md §4.4).
SANS_THEME_A_RETIRER = "aucun thème tiré au sort en ce moment : rien à retirer"


class LiveRadio(Radio):
    """Ce que la radio répond à l'API.

    Elle ne décide de rien : `Control` tranche les votes, `ListenerCount` sait
    si la chaîne tourne. Elle observe et traduit.
    """

    def __init__(
        self,
        control: Control,
        on_air: "ListenerCount",
        remember: Callable[[Command, Track], None] | None = None,
        list_votes: Callable[[], list[VoteScore]] | None = None,
        skip: Callable[[], None] | None = None,
        requeue: Callable[[], None] | None = None,
        forget: Callable[[str, str], bool] | None = None,
        moment: Callable[[], str | None] | None = None,
        up_next: Callable[[], OnAir | None] | None = None,
        journal: Callable[[str, str, str], None] | None = None,
        list_history: Callable[[], "list[PlayedEntry]"] | None = None,
        *,
        moment_random: Callable[[], bool] | None = None,
        redraw: Callable[[], Verdict] | None = None,
        upcoming: Callable[[], list[UpcomingEntry]] | None = None,
        withdraw: Callable[[str], bool] | None = None,
    ) -> None:
        self._controle = control
        self._station = on_air
        self._retenir = remember
        self._lister_votes = list_votes
        self._passer = skip
        self._vider_l_avance = requeue
        self._oublier = forget
        self._moment = moment
        self._journaliser = journal
        self._a_suivre = up_next
        self._lister_historique = list_history
        self._moment_au_hasard = moment_random
        self._retirer = redraw
        self._prochains = upcoming
        self._ecarter = withdraw
        self._verrou = threading.Lock()
        self._nature = Kind.MUSIC
        self._piste: Track | None = None
        self._libelle: str | None = None
        self._artiste_libelle: str | None = None

    def declare(
        self,
        kind: Kind,
        track: Track | None,
        label: str | None = None,
        artist_label: str | None = None,
    ) -> None:
        """Appelée par le programme à chaque changement de ce qui passe.

        Le noyau en a besoin pour refuser un vote au bon moment, l'API pour
        l'afficher. `label` porte le nom de ce qui n'a pas de piste, comme une
        émission : le flux ne porte aucune métadonnée (docs/franceinfo.md
        §1.bis), ce qui s'affiche est ce qui a été déclaré (SPECS.md §4.8,
        GOAL-015).
        """
        with self._verrou:
            self._nature = kind
            self._piste = track
            self._libelle = label
            self._artiste_libelle = artist_label
        self._controle.declare(kind)
        # Le journal des titres (SPECS.md §7 n°27) retient ce qui commence,
        # jingles exclus.
        titre = track.title if track is not None else label
        artiste = track.artist if track is not None else (artist_label or "")
        if self._journaliser is not None and kind is not Kind.JINGLE and titre:
            self._journaliser(str(kind.value), titre, artiste)

    def on_air(self) -> bool:
        return self._station.on_air

    def on_air_now(self) -> OnAir | None:
        if not self._station.on_air:
            return None
        with self._verrou:
            kind, track, label = self._nature, self._piste, self._libelle
            artist_label = self._artiste_libelle
        return OnAir(
            kind=NatureWeb(kind.value),
            title=track.title if track is not None else label,
            artist=track.artist if track is not None else artist_label,
        )

    def vote_scores(self) -> list[VoteScore]:
        """Sans base, aucune mémoire : liste vide (SPECS.md §4.12)."""
        if self._lister_votes is None:
            return []
        return self._lister_votes()

    def up_next(self) -> OnAir | None:
        if self._a_suivre is None or not self._station.on_air:
            return None
        return self._a_suivre()

    def history(self) -> "list[PlayedEntry]":
        if self._lister_historique is None:
            return []
        return self._lister_historique()

    def playing_track(self) -> Track | None:
        """La piste à l'antenne, sur laquelle porte un « encore » (SPECS.md §4.6).

        C'est le morceau entendu, pas celui demandé d'avance : il y a toujours
        un morceau d'écart (docs/liquidsoap.md §3).
        """
        with self._verrou:
            return self._piste

    def playing_kind(self) -> Kind:
        """La nature de ce qui passe. Pendant une émission, les jingles horaires
        sont abandonnés (SPECS.md §4.11)."""
        with self._verrou:
            return self._nature

    def moment(self) -> str | None:
        if self._moment is None:
            return None
        return self._moment()

    def upcoming(self) -> list[UpcomingEntry]:
        if self._prochains is None or not self._station.on_air:
            return []
        return self._prochains()

    def withdraw(self, identifier: str) -> bool:
        return self._ecarter is not None and self._ecarter(identifier)

    def moment_random(self) -> bool:
        return self._moment_au_hasard is not None and self._moment_au_hasard()

    def redraw_moment(self) -> Verdict:
        """Relaie le retirage au câblage, qui connaît la plage, le tirage et
        l'avance à purger (GOAL-057). Sans câblage, refus."""
        if self._retirer is None:
            return Verdict(accepted=False, reason=SANS_THEME_A_RETIRER)
        return self._retirer()

    def forget_vote(self, scope: str, target: str) -> bool:
        if self._oublier is None:
            return False
        return self._oublier(scope, target)

    def vote(self, vote: Vote) -> Verdict:
        """Passe le vote au noyau et ne le retient que s'il a été accepté.

        Un vote refusé n'enregistre rien (SPECS.md §4.6), sinon la radio
        apprendrait de gestes sans effet. Un vote accepté sans piste à
        l'antenne (possible entre deux morceaux) agit mais n'est pas retenu.
        """
        command = Command(vote.value)
        with self._verrou:
            courante = self._piste
        answer = self._controle.vote(command, playing=courante)
        if answer.accepted and command is Command.SKIP and self._passer is not None:
            # C'est le diffuseur qui coupe (SPECS.md §4.6). S'il est
            # injoignable, le vote reste enregistré : le morceau finira, mais
            # pèsera moins la prochaine fois.
            self._passer()
        if answer.accepted and command is Command.MORE and self._vider_l_avance is not None:
            # L'effet de l'encore (jingle puis même artiste) doit suivre la
            # chanson en cours, pas le morceau d'avance déjà demandé
            # (SPECS.md §4.6, GOAL-034).
            self._vider_l_avance()
        if answer.accepted and self._retenir is not None and courante is not None:
            self._retenir(command, courante)
        return Verdict(accepted=answer.accepted, reason=answer.reason or None)


class ListenerCount:
    """Si la chaîne tourne. La façade n'a pas besoin d'en savoir plus sur la
    station, et aucune raison de dépendre d'un serveur."""

    def __init__(self) -> None:
        self._en_antenne = False

    @property
    def on_air(self) -> bool:
        return self._en_antenne

    def declare(self, *, on_air: bool) -> None:
        self._en_antenne = on_air
