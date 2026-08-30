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

from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.control import Kind
from webradio.core.models import Track

logger = logging.getLogger(__name__)

# Combien d'entrées demandées mais pas encore commencées on garde. Liquidsoap
# n'en a qu'une d'avance ; en garder quelques-unes tolère un redémarrage.
PENDING_MAX = 8


class LiquidsoapPlayout:
    """Le `Playout` de `adapters/web/playout_api.py`, câblé au programme."""

    def __init__(
        self,
        programme: RadioProgramme,
        radio: LiveRadio,
        listeners: ListenerCount,
    ) -> None:
        self._programme = programme
        self._radio = radio
        self._auditeurs = listeners
        self._verrou = (
            threading.RLock()
        )  # réentrant : next_entry tient le verrou quand le programme rappelle on_kind
        self._derniere: tuple[Kind, Track | None, str | None] = (Kind.MUSIC, None, None)
        self._en_attente: dict[str, tuple[Kind, Track | None, str | None]] = {}

    def on_kind(self, kind: Kind, track: Track | None, label: str | None) -> None:
        """À brancher sur `RadioProgramme(on_kind=...)` : retient, ne déclare pas."""
        with self._verrou:
            self._derniere = (kind, track, label)

    def next_entry(self) -> str | None:
        with self._verrou:
            entry = self._programme.next_entry()
            if entry is None:
                return None
            self._en_attente[entry] = self._derniere
            while len(self._en_attente) > PENDING_MAX:
                oublie = next(iter(self._en_attente))
                del self._en_attente[oublie]
            self._programme.prepare()
            return entry

    def playing(self, entry: str) -> None:
        with self._verrou:
            nature = self._en_attente.pop(entry, None)
        if nature is None:
            logger.warning("Liquidsoap joue une entrée que le programme n'a pas rendue : %s", entry)
            return
        kind, track, label = nature
        self._radio.declare(kind, track, label)

    def declare_listeners(self, count: int) -> None:
        self._auditeurs.declare(on_air=count > 0)
        if count == 0:
            logger.info("dernier auditeur parti : rien ne sera décodé ni demandé")
