"""Ce que Liquidsoap demande, traduit pour le programme — la quatrième charnière.

D'un côté `RadioProgramme`, qui rend une entrée et **déclare sa nature au
moment où il la choisit** ; de l'autre Liquidsoap, qui demande toujours un
morceau d'avance (docs/liquidsoap.md §3) et ne joue celui-ci que plus tard.
Entre les deux, cette classe retient ce qui a été demandé, et ne déclare
« à l'antenne » que ce que Liquidsoap dit avoir **commencé**.

Rien ici ne décide : le programme a choisi, Liquidsoap joue, on tient le
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

# Combien d'entrées demandées mais pas encore commencées on garde. Liquidsoap
# n'en a qu'une d'avance ; en garder quelques-unes tolère un redémarrage.
PENDING_MAX = 8

# Un jingle de dix secondes n'a pas à être mangé par le fondu de deux secondes
# des morceaux : il porte ses propres durées, par les métadonnées que
# `crossfade` honore (`liq_fade_*`, relevé docs/liquidsoap.md §7). Demandé par
# l'auteur à l'écoute (GOAL-022).
JINGLE_FADES = "annotate:liq_fade_in=0.2,liq_fade_out=0.2,liq_cross_duration=0.5:"

# Une piste au-dessus du plafond se joue mais se coupe au plafond, fondue vers
# la suite par le crossfade comme une fin de piste ordinaire (SPECS.md §7
# n°32 révisée, relevé docs/liquidsoap.md §7).
CUT_AT = "annotate:liq_cue_out={seconds:g}:"


@dataclass(frozen=True, slots=True)
class Pending:
    """Une entrée demandée par le diffuseur, pas encore à l'antenne.

    Elle est **datée** (décision n°33) : par le moment qui l'a tirée — le
    programme, l'occurrence de plage, ou rien — et par l'instant de la
    décision. Un moment qui a fini, ou une heure pleine passée depuis, la
    rendent rassise : elle est remise en question avant de passer.
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
        # Le dossier des fichiers à usage unique — le cache YouTube : ce qui y
        # a été lu s'efface dès que la suite commence (GOAL-028).
        self._ephemere = ephemeral_dir
        self._entree_en_cours: str | None = None
        # Ce qui joue, et depuis quand : c'est ce qui permet d'estimer quand
        # la jonction suivante tombera, donc l'heure de chaque titre d'avance
        # (GOAL-058). Inconnu après un redémarrage, et pour un direct.
        self._en_cours: Pending | None = None
        self._commence_a: datetime | None = None
        # La reprise à neuf après une longue pause (SPECS.md §7 n°30) : la
        # pause se date au départ du dernier auditeur, et se juge au retour.
        self._horloge = clock
        self._reprise_a_neuf = resume_fresh_after
        self._ordonner_requeue = order_requeue
        self._ordonner_skip = order_skip
        self._plafond = max_duration
        self._pause_depuis: datetime | None = None

    def on_kind(self, kind: Kind, track: Track | None, label: str | None) -> None:
        """À brancher sur `RadioProgramme(on_kind=...)` : retient, ne déclare pas."""
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
        """Quand le morceau en cours finira, si on peut le savoir : son début
        plus sa durée — coupée au plafond. Rien pour un direct, une entrée
        inconnue, ou sans horloge."""
        if self._en_cours is None or self._commence_a is None or self._horloge is None:
            return None
        track = self._en_cours.track
        if self._en_cours.kind is not Kind.MUSIC or track is None:
            return None
        duree = track.duration
        if self._plafond is not None and duree > self._plafond:
            duree = self._plafond
        # Jamais dans le passé : après une pause sans auditeur, le morceau
        # commencé il y a longtemps finira au plus tôt maintenant.
        return max(self._commence_a + duree, self._horloge.now())

    def _fin_estimee_de_l_avance(self) -> datetime | None:
        """Quand la file parlera : la fin du courant, puis ce qui attend déjà
        chez le diffuseur. L'habillage compte pour zéro — une dizaine de
        secondes, dont la durée n'est pas connue ici."""
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
        §4.11), un jingle est court par construction. Une entrée replacée
        après un encore revient déjà annotée — on ne la double pas.
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
                # Sans étiquettes, il n'y a rien à afficher — et déclarer
                # « musique, sans titre ni artiste » VIDE l'antenne. C'est ce
                # qui a effacé « Matinale franceinfo » le 2026-09-02 : le
                # direct s'annonce deux fois, et la seconde annonce arrive
                # après que la première a consommé l'entrée
                # (docs/liquidsoap.md §9).
                logger.info("entrée inconnue et sans étiquettes : l'antenne reste telle quelle")
                return
            # Après un redémarrage de `radio`, Liquidsoap joue encore un ou
            # deux morceaux demandés à l'ancien processus. Plutôt que rien,
            # on affiche les étiquettes que le décodeur a lues du fichier.
            logger.info(
                "entrée demandée avant ce démarrage, affichée d'après ses étiquettes : %s — %s",
                artist,
                title,
            )
            self._radio.declare(Kind.MUSIC, None, title, artist_label=artist)
            return
        self._radio.declare(pending.kind, pending.track, pending.label)

    def _effacer_si_ephemere(self, entry: str | None) -> None:
        """Une vidéo lue ne sert plus : elle s'efface quand la suite commence.

        C'est le moment sûr — le diffuseur a fini de la lire — et c'est ce qui
        évite qu'un fichier de soixante mégaoctets traîne jusqu'à l'émission
        suivante (question de l'auteur, GOAL-028).
        """
        if entry is None or self._ephemere is None:
            return
        chemin = Path(entry)
        if chemin.parent == self._ephemere and chemin.is_file():
            chemin.unlink(missing_ok=True)
            logger.info("vidéo lue et effacée : %s", chemin.name)

    def up_next(self) -> tuple[Kind, Track | None, str | None] | None:
        """La prochaine entrée déjà demandée — la file, vue de la charnière.

        C'est le morceau d'avance du diffuseur (GOAL-035) : demandé, pas
        encore à l'antenne. `None` quand rien n'attend — au tout début, ou
        juste après qu'un encore a vidé l'avance.

        **Et quand cette avance n'est que de l'habillage, on regarde
        derrière** (GOAL-054) : le diffuseur ne garde qu'une entrée d'avance
        (`prefetch=1`, docs/liquidsoap.md §3), donc un jingle demandé suffisait
        à vider le panneau le temps d'une chanson entière — une quarantaine de
        fois par jour. La file, elle, a déjà tiré la suite.
        """
        for item in self.upcoming():
            # Dix secondes d'habillage ne sont pas « à suivre » : on annonce
            # le premier vrai contenu (demandé par l'auteur).
            if item.kind is not Kind.JINGLE:
                return (item.kind, item.track, item.label)
        return None

    def upcoming(self) -> list[Upcoming]:
        """La liste des prochains titres (GOAL-058) : ce que le diffuseur a
        déjà demandé, puis ce que le programme rendrait ensuite — avec l'heure
        estimée de chaque début quand le morceau en cours permet de l'estimer.
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
        """Retire un titre qui attend : chez le diffuseur — l'avance se
        replace sans lui et le diffuseur redemande — ou dans la file. Faux
        s'il n'attend plus : il a commencé entre-temps (GOAL-058)."""
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
        """Les entrées demandées mais pas encore à l'antenne repartent au
        programme, pour être rejouées après l'effet d'un encore (GOAL-034).

        Le diffuseur vide son avance (`/requeue`), et ce qu'elle contenait se
        ressert tel quel, nature comprise — **si son moment tient encore**
        (décision n°33). Une entrée tirée sous un moment qui a fini est
        rassise : elle est jetée en le disant, et le tirage suivant la
        remplace sous le moment courant.
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

    def declare_listeners(self, count: int) -> None:
        """Le compte d'auditeurs — et, au retour après une longue pause, la
        purge (SPECS.md §4.7).

        Le diffuseur annonce AVANT de rendre l'antenne (docs/liquidsoap.md
        §5.bis) : tout ce qui se décide ici s'applique pendant que l'auditeur
        n'entend encore que le silence. Le battement périodique redit le même
        compte : la pause se date à la première annonce à zéro, pas aux
        suivantes.
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
        """L'avance du diffuseur, jugée à l'heure pleine et au moment (n°33).

        Le diffuseur décide l'entrée de chaque jonction à la précédente : une
        heure pleine tombée entre les deux n'était vue qu'à la jonction
        d'après, et le jingle arrivait une chanson trop tard — 16 h 07 pour
        16 h, le 2026-09-02. Le battement d'auditeurs, toutes les quinze
        secondes, est l'horloge dont dispose la charnière : quand une heure
        pleine est passée depuis la décision d'une entrée musique, ou que son
        moment a fini, elle est replacée (`stash_for_replay`, qui jette ce qui
        est rassi) et le diffuseur redemande — le chemin de l'encore
        (GOAL-034). Il rend alors le générique, le jingle dû, puis l'entrée
        replacée ou un tirage neuf.

        Pendant une émission, l'heure ne compte pas — les jingles y sont
        abandonnés (SPECS.md §4.11) — mais un moment fini compte toujours.
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
        """Une longue pause a rassis l'avance : tout repart d'un tirage neuf.

        L'ordre suit le relevé (docs/liquidsoap.md §5.bis) : l'oubli du
        programme d'abord — le recomplètement qui suivra le `/requeue` doit
        calculer à neuf —, la file du diffuseur ensuite, le reliquat du
        morceau interrompu enfin.

        **Le saut part toujours**, et c'est le diffuseur qui le refuse s'il n'a
        rien à couper (docs/liquidsoap.md §9). Le garder ici demandait à ce
        processus de savoir ce que Liquidsoap tient : redémarré seul — ce qui
        est arrivé le 2026-09-02 — il n'a plus d'entrée en cours et laissait
        passer neuf minutes d'un morceau de la veille.
        """
        logger.info("pause de %s : la radio repart sur un tirage neuf", pause)
        with self._verrou:
            self._en_attente.clear()
        self._programme.forget_pending()
        if self._ordonner_requeue is not None:
            self._ordonner_requeue()
        if self._ordonner_skip is not None:
            self._ordonner_skip()
