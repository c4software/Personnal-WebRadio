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
from pathlib import Path

from webradio.app.playout import RadioProgramme
from webradio.app.radio import ListenerCount, LiveRadio
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

    def declare_listeners(self, count: int) -> None:
        self._auditeurs.declare(on_air=count > 0)
        if count == 0:
            logger.info("dernier auditeur parti : rien ne sera décodé ni demandé")
