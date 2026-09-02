"""Charnière entre Liquidsoap et le programme.

`RadioProgramme` rend une entrée et déclare sa nature au moment où il la
choisit. Liquidsoap demande toujours un morceau d'avance (docs/liquidsoap.md §3)
et ne le joue que plus tard. Cette classe retient ce qui a été demandé et ne
déclare à l'antenne que ce que Liquidsoap dit avoir commencé.

Rien ici ne décide : le programme choisit, Liquidsoap joue, on tient le
registre.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from webradio.app.playout import RadioProgramme, Upcoming
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.clock import Clock
from webradio.core.control import Kind
from webradio.core.models import Track

logger = logging.getLogger(__name__)

# Nombre d'entrées demandées mais pas encore commencées que l'on garde.
# Liquidsoap n'en a qu'une d'avance ; en garder plusieurs tolère un redémarrage.
PENDING_MAX = 8

# Un jingle court ne doit pas être mangé par le fondu de deux secondes des
# morceaux : il porte ses propres durées via les métadonnées `liq_fade_*` que
# `crossfade` honore (docs/liquidsoap.md §7, GOAL-022).
JINGLE_FADES = "annotate:liq_fade_in=0.2,liq_fade_out=0.2,liq_cross_duration=0.5:"

# Une piste au-dessus du plafond se coupe au plafond, fondue vers la suite par
# le crossfade comme une fin ordinaire (SPECS.md §7 n°32, docs/liquidsoap.md §7).
CUT_AT = "annotate:liq_cue_out={seconds:g}:"


@dataclass(frozen=True, slots=True)
class Pending:
    """Une entrée demandée par le diffuseur, pas encore à l'antenne.

    Elle est datée (décision n°33) par le moment qui l'a tirée (programme,
    occurrence de plage, ou rien) et par l'instant de la décision. Un moment
    fini, ou une heure pleine passée depuis, la rendent rassise : elle est
    remise en question avant de passer.
    """

    kind: Kind
    track: Track | None
    label: str | None
    moment: object = None
    decided_at: datetime | None = None

    @property
    def nature(self) -> tuple[Kind, Track | None, str | None]:
        return (self.kind, self.track, self.label)


class LiquidsoapPlayout:
    """Le `Playout` de `adapters/web/playout_api.py`, câblé au programme."""

    def __init__(
        self,
        programme: RadioProgramme,
        radio: LiveRadio,
        listeners: ListenerCount,
        ephemeral_dir: Path | None = None,
        *,
        clock: Clock | None = None,
        resume_fresh_after: timedelta | None = None,
        order_requeue: Callable[[], None] | None = None,
        order_skip: Callable[[], None] | None = None,
        max_duration: timedelta | None = None,
    ) -> None:
        self._programme = programme
        self._radio = radio
        self._auditeurs = listeners
        self._verrou = (
            threading.RLock()
        )  # réentrant : next_entry tient le verrou quand le programme rappelle on_kind
        self._derniere: tuple[Kind, Track | None, str | None] = (Kind.MUSIC, None, None)
        self._en_attente: dict[str, Pending] = {}
        # Dossier des fichiers à usage unique (cache YouTube) : un fichier lu
        # s'efface dès que la suite commence (GOAL-028).
        self._ephemere = ephemeral_dir
        self._entree_en_cours: str | None = None
        # Ce qui joue et depuis quand, pour estimer l'heure de chaque titre
        # d'avance (GOAL-058). Inconnu après un redémarrage et pour un direct.
        self._en_cours: Pending | None = None
        self._commence_a: datetime | None = None
        # Reprise à neuf après une longue pause (SPECS.md §7 n°30) : la pause se
        # date au départ du dernier auditeur et se juge au retour.
        self._horloge = clock
        self._reprise_a_neuf = resume_fresh_after
        self._ordonner_requeue = order_requeue
        self._ordonner_skip = order_skip
        self._plafond = max_duration
        self._pause_depuis: datetime | None = None

    def on_kind(self, kind: Kind, track: Track | None, label: str | None) -> None:
        """À brancher sur `RadioProgramme(on_kind=...)`. Retient sans déclarer."""
        with self._verrou:
            self._derniere = (kind, track, label)

    def next_entry(self) -> str | None:
        with self._verrou:
            entry = self._programme.next_entry()
            if entry is None:
                return None
            if self._derniere[0] is Kind.JINGLE:
                entry = JINGLE_FADES + entry
            else:
                entry = self._couper_au_plafond(entry)
            kind, track, label = self._derniere
            self._en_attente[entry] = Pending(
                kind,
                track,
                label,
                moment=self._programme.current_moment(),
                decided_at=None if self._horloge is None else self._horloge.now(),
            )
            while len(self._en_attente) > PENDING_MAX:
                oublie = next(iter(self._en_attente))
                del self._en_attente[oublie]
            self._programme.prepare(self._fin_estimee_de_l_avance())
            return entry

    def _fin_estimee_du_courant(self) -> datetime | None:
        """La fin estimée du morceau en cours : son début plus sa durée, coupée
        au plafond. `None` pour un direct, une entrée inconnue ou sans horloge."""
        if self._en_cours is None or self._commence_a is None or self._horloge is None:
            return None
        track = self._en_cours.track
        if self._en_cours.kind is not Kind.MUSIC or track is None:
            return None
        duree = track.duration
        if self._plafond is not None and duree > self._plafond:
            duree = self._plafond
        # Jamais dans le passé : après une pause sans auditeur, le morceau
        # commencé avant la pause finira au plus tôt maintenant.
        return max(self._commence_a + duree, self._horloge.now())

    def _fin_estimee_de_l_avance(self) -> datetime | None:
        """La fin estimée du courant plus ce qui attend chez le diffuseur, ou
        `None`. L'habillage compte pour zéro, sa durée n'est pas connue ici."""
        instant = self._fin_estimee_du_courant()
        if instant is None:
            return None
        with self._verrou:
            for entry, pending in self._en_attente.items():
                if entry != self._entree_en_cours and pending.track is not None:
                    instant = instant + pending.track.duration
        return instant

    def _couper_au_plafond(self, entry: str) -> str:
        """L'entrée, annotée pour se couper au plafond si sa piste le dépasse.

        Seule la musique se coupe : une émission a sa propre durée (SPECS.md
        §4.11), un jingle est court. Une entrée replacée après un encore revient
        déjà annotée, on ne la double pas.
        """
        kind, track, _ = self._derniere
        if (
            self._plafond is None
            or kind is not Kind.MUSIC
            or track is None
            or track.duration <= self._plafond
            or entry.startswith("annotate:")
        ):
            return entry
        logger.info(
            "« %s » dure %s : coupé au plafond (%s)", track.title, track.duration, self._plafond
        )
        return CUT_AT.format(seconds=self._plafond.total_seconds()) + entry

    def playing(self, entry: str, artist: str | None = None, title: str | None = None) -> None:
        with self._verrou:
            pending = self._en_attente.pop(entry, None)
            finie, self._entree_en_cours = self._entree_en_cours, entry
            self._en_cours = pending
            self._commence_a = None if self._horloge is None else self._horloge.now()
        self._effacer_si_ephemere(finie)
        if pending is None:
            if artist is None and title is None:
                # Sans étiquettes, rien à afficher, et déclarer une musique sans
                # titre ni artiste viderait l'antenne. Un direct s'annonce deux
                # fois, et la seconde annonce arrive après que la première a
                # consommé l'entrée (docs/liquidsoap.md §9).
                logger.info("entrée inconnue et sans étiquettes : l'antenne reste telle quelle")
                return
            # Après un redémarrage de `radio`, Liquidsoap joue encore un ou deux
            # morceaux demandés à l'ancien processus. On affiche les étiquettes
            # lues du fichier plutôt que rien.
            logger.info(
                "entrée demandée avant ce démarrage, affichée d'après ses étiquettes : %s — %s",
                artist,
                title,
            )
            self._radio.declare(Kind.MUSIC, None, title, artist_label=artist)
            return
        self._radio.declare(pending.kind, pending.track, pending.label)

    def _effacer_si_ephemere(self, entry: str | None) -> None:
        """Efface un fichier du dossier éphémère quand la suite commence.

        À ce moment le diffuseur a fini de le lire. Cela évite qu'un fichier
        volumineux traîne jusqu'à l'émission suivante (GOAL-028).
        """
        if entry is None or self._ephemere is None:
            return
        chemin = Path(entry)
        if chemin.parent == self._ephemere and chemin.is_file():
            chemin.unlink(missing_ok=True)
            logger.info("vidéo lue et effacée : %s", chemin.name)

    def up_next(self) -> tuple[Kind, Track | None, str | None] | None:
        """Le prochain contenu qui n'est pas un jingle, ou `None`.

        C'est le morceau d'avance du diffuseur (GOAL-035), ou à défaut ce que la
        file a déjà tiré. `None` quand rien n'attend : au démarrage, ou juste
        après qu'un encore a vidé l'avance.

        Les jingles sont sautés (GOAL-054) : le diffuseur ne garde qu'une entrée
        d'avance (`prefetch=1`, docs/liquidsoap.md §3), un jingle demandé
        viderait le panneau le temps d'une chanson.
        """
        for item in self.upcoming():
            if item.kind is not Kind.JINGLE:
                return (item.kind, item.track, item.label)
        return None

    def upcoming(self) -> list[Upcoming]:
        """Les prochains titres (GOAL-058) : ce que le diffuseur a déjà demandé,
        puis ce que le programme rendrait ensuite, avec l'heure estimée de chaque
        début quand le morceau en cours permet de l'estimer.
        """
        instant = self._fin_estimee_du_courant()
        items: list[Upcoming] = []
        with self._verrou:
            for entry, pending in self._en_attente.items():
                if entry == self._entree_en_cours:
                    continue
                label = pending.label
                if pending.kind is Kind.JINGLE and label is None:
                    label = Path(entry.rsplit(":", 1)[-1]).stem
                items.append(Upcoming(pending.kind, pending.track, label, instant))
                if pending.track is not None and instant is not None:
                    instant = instant + pending.track.duration
        items.extend(self._programme.upcoming(instant))
        return items

    def withdraw(self, identifier: str) -> bool:
        """Retire un titre qui attend, chez le diffuseur (l'avance se replace
        sans lui et le diffuseur redemande) ou dans la file. Faux s'il a déjà
        commencé (GOAL-058)."""
        with self._verrou:
            chez_le_diffuseur = [
                entry
                for entry, pending in self._en_attente.items()
                if entry != self._entree_en_cours
                and pending.track is not None
                and pending.track.identifier == identifier
            ]
            for entry in chez_le_diffuseur:
                del self._en_attente[entry]
        if chez_le_diffuseur:
            logger.info("retiré avant diffusion, le diffuseur redemande : %s", identifier)
            self.stash_for_replay()
            if self._ordonner_requeue is not None:
                self._ordonner_requeue()
            return True
        if not self._programme.withdraw(identifier):
            return False
        self._programme.prepare(self._fin_estimee_de_l_avance())
        return True

    def stash_for_replay(self) -> None:
        """Renvoie au programme les entrées demandées mais pas encore à
        l'antenne, pour les rejouer après un encore (GOAL-034).

        Le diffuseur vide son avance (`/requeue`) et son contenu se ressert tel
        quel, nature comprise, si son moment tient encore (décision n°33). Une
        entrée tirée sous un moment fini est jetée avec un message, le tirage
        suivant la remplace.
        """
        with self._verrou:
            en_avance = [
                (entry, pending)
                for entry, pending in self._en_attente.items()
                if entry != self._entree_en_cours
            ]
            for entry, _ in en_avance:
                del self._en_attente[entry]
        moment = self._programme.current_moment()
        for entry, pending in en_avance:
            shown = entry.split("?", 1)[0]
            if pending.moment != moment:
                logger.info("l'avance est rassise, son moment a fini : %s", shown)
                continue
            logger.info("l'avance se replace : %s", shown)
            self._programme.replay_later(entry, pending.kind, pending.track, pending.label)
        # Sans attendre que le diffuseur redemande, pour que la liste des
        # prochains titres montre le morceau forcé dès le vote (GOAL-067).
        self._programme.prepare(self._fin_estimee_de_l_avance())

    def drop_advance(self) -> None:
        """Jette l'avance sans rien replacer, chez le diffuseur comme dans la
        file, et fait redemander : ce qui a été tiré sous une suite rompue ne
        doit pas revenir (GOAL-059). Le morceau en cours finit, l'habillage dû
        reste dû."""
        with self._verrou:
            for entry in [e for e in self._en_attente if e != self._entree_en_cours]:
                del self._en_attente[entry]
        self._programme.forget_advance()
        logger.info("l'avance est jetée : la suite est rompue, le diffuseur redemande")
        if self._ordonner_requeue is not None:
            self._ordonner_requeue()

    def declare_listeners(self, count: int) -> None:
        """Déclare le compte d'auditeurs et, au retour après une longue pause,
        purge l'avance (SPECS.md §4.7).

        Le diffuseur annonce avant de rendre l'antenne (docs/liquidsoap.md
        §5.bis) : ce qui se décide ici s'applique pendant le silence. Le
        battement périodique redit le même compte : la pause se date à la
        première annonce à zéro seulement.
        """
        self._auditeurs.declare(on_air=count > 0)
        if count == 0:
            if self._pause_depuis is None:
                if self._horloge is not None:
                    self._pause_depuis = self._horloge.now()
                logger.info("dernier auditeur parti : rien ne sera décodé ni demandé")
            return
        pause_depuis, self._pause_depuis = self._pause_depuis, None
        if (
            pause_depuis is not None
            and self._horloge is not None
            and self._reprise_a_neuf is not None
        ):
            pause = self._horloge.now() - pause_depuis
            if pause > self._reprise_a_neuf:
                self._repartir_a_neuf(pause)
        self._remettre_l_avance_en_question()

    def _remettre_l_avance_en_question(self) -> None:
        """Remet en question l'avance du diffuseur à l'heure pleine et au
        changement de moment (décision n°33).

        Le diffuseur décide l'entrée de chaque jonction à la précédente : une
        heure pleine tombée entre les deux ne serait vue qu'à la jonction
        d'après, et le jingle arriverait une chanson trop tard. Le battement
        d'auditeurs sert d'horloge : quand une heure pleine est passée depuis
        la décision d'une entrée musique, ou que son moment a fini, l'avance
        est replacée (`stash_for_replay` jette ce qui est rassi) et le diffuseur
        redemande, comme pour un encore (GOAL-034). Il rend alors le générique,
        le jingle dû, puis l'entrée replacée ou un tirage neuf.

        Pendant une émission, l'heure ne compte pas, les jingles y sont
        abandonnés (SPECS.md §4.11). Un moment fini compte toujours.
        """
        if self._horloge is None or self._ordonner_requeue is None:
            return
        with self._verrou:
            en_avance = [
                pending
                for entry, pending in self._en_attente.items()
                if entry != self._entree_en_cours and pending.kind is Kind.MUSIC
            ]
        if not en_avance:
            return
        now = self._horloge.now()
        heure_pleine = now.replace(minute=0, second=0, microsecond=0)
        moment = self._programme.current_moment()
        rassise = any(pending.moment != moment for pending in en_avance)
        heure_passee = any(
            pending.decided_at is not None and pending.decided_at < heure_pleine
            for pending in en_avance
        )
        en_emission = self._radio.playing_kind() in (Kind.SHOW, Kind.NEWS)
        if not rassise and (en_emission or not heure_passee):
            return
        logger.info(
            "l'avance est remise en question (%s) : le diffuseur redemande",
            "son moment a fini" if rassise else "une heure pleine est passée",
        )
        self.stash_for_replay()
        self._ordonner_requeue()

    def _repartir_a_neuf(self, pause: timedelta) -> None:
        """Après une longue pause, tout repart d'un tirage neuf.

        L'ordre suit docs/liquidsoap.md §5.bis : oubli du programme d'abord (le
        recomplètement après le `/requeue` doit calculer à neuf), file du
        diffuseur ensuite, saut du morceau interrompu enfin.

        Le saut part toujours ; le diffuseur le refuse s'il n'a rien à couper
        (docs/liquidsoap.md §9). Ce processus, redémarré seul, ne sait pas ce
        que Liquidsoap tient : il n'a plus d'entrée en cours et laisserait
        finir un morceau ancien.
        """
        logger.info("pause de %s : la radio repart sur un tirage neuf", pause)
        with self._verrou:
            self._en_attente.clear()
        self._programme.forget_pending()
        if self._ordonner_requeue is not None:
            self._ordonner_requeue()
        if self._ordonner_skip is not None:
            self._ordonner_skip()
