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
from datetime import datetime, timedelta
from pathlib import Path

from webradio.app.playout import RadioProgramme
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
    ) -> None:
        self._programme = programme
        self._radio = radio
        self._auditeurs = listeners
        self._verrou = (
            threading.RLock()
        )  # réentrant : next_entry tient le verrou quand le programme rappelle on_kind
        self._derniere: tuple[Kind, Track | None, str | None] = (Kind.MUSIC, None, None)
        self._en_attente: dict[str, tuple[Kind, Track | None, str | None]] = {}
        # Le dossier des fichiers à usage unique — le cache YouTube : ce qui y
        # a été lu s'efface dès que la suite commence (GOAL-028).
        self._ephemere = ephemeral_dir
        self._entree_en_cours: str | None = None
        # La reprise à neuf après une longue pause (SPECS.md §7 n°30) : la
        # pause se date au départ du dernier auditeur, et se juge au retour.
        self._horloge = clock
        self._reprise_a_neuf = resume_fresh_after
        self._ordonner_requeue = order_requeue
        self._ordonner_skip = order_skip
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
            self._en_attente[entry] = self._derniere
            while len(self._en_attente) > PENDING_MAX:
                oublie = next(iter(self._en_attente))
                del self._en_attente[oublie]
            self._programme.prepare()
            return entry

    def playing(self, entry: str, artist: str | None = None, title: str | None = None) -> None:
        with self._verrou:
            nature = self._en_attente.pop(entry, None)
            finie, self._entree_en_cours = self._entree_en_cours, entry
        self._effacer_si_ephemere(finie)
        if nature is None:
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
        kind, track, label = nature
        self._radio.declare(kind, track, label)

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
        """
        with self._verrou:
            for entry, nature in self._en_attente.items():
                if entry == self._entree_en_cours:
                    continue
                if nature[0] is Kind.JINGLE:
                    # Dix secondes d'habillage ne sont pas « à suivre » : on
                    # annonce le premier vrai contenu (demandé par l'auteur).
                    continue
                return nature
        return None

    def stash_for_replay(self) -> None:
        """Les entrées demandées mais pas encore à l'antenne repartent au
        programme, pour être rejouées après l'effet d'un encore (GOAL-034).

        Rien n'est jeté : le diffuseur vide son avance (`/requeue`), et ce
        qu'elle contenait se ressert tel quel, nature comprise.
        """
        with self._verrou:
            en_avance = [
                (entry, nature)
                for entry, nature in self._en_attente.items()
                if entry != self._entree_en_cours
            ]
            for entry, _ in en_avance:
                del self._en_attente[entry]
        for entry, (kind, track, label) in en_avance:
            logger.info("l'avance se replace après l'encore : %s", entry.split("?", 1)[0])
            self._programme.replay_later(entry, kind, track, label)

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
        if pause_depuis is None or self._horloge is None or self._reprise_a_neuf is None:
            return
        pause = self._horloge.now() - pause_depuis
        if pause > self._reprise_a_neuf:
            self._repartir_a_neuf(pause)

    def _repartir_a_neuf(self, pause: timedelta) -> None:
        """Une longue pause a rassis l'avance : tout repart d'un tirage neuf.

        L'ordre suit le relevé (docs/liquidsoap.md §5.bis) : l'oubli du
        programme d'abord — le recomplètement qui suivra le `/requeue` doit
        calculer à neuf —, la file du diffuseur ensuite, le reliquat du
        morceau interrompu enfin. Et ce dernier seulement s'il y en a un :
        un saut sans morceau en cours reste enregistré et mangerait le
        premier morceau frais.
        """
        logger.info("pause de %s : la radio repart sur un tirage neuf", pause)
        with self._verrou:
            courant = self._entree_en_cours
            self._en_attente.clear()
        self._programme.forget_pending()
        if self._ordonner_requeue is not None:
            self._ordonner_requeue()
        if courant is not None and self._ordonner_skip is not None:
            self._ordonner_skip()
