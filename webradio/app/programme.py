"""Ce qui décide de la piste suivante, vu par la chaîne de diffusion.

C'est la charnière du projet : d'un côté le noyau, qui rend des `Choix` et des
`Piste` ; de l'autre la chaîne, qui ne veut qu'une chaîne de caractères que
ffmpeg sait ouvrir (`adapters/ffmpeg/encodeur.py`, `Programme`).

Rien ici ne décide : la grille, le tirage, la non-répétition, les jingles et le
contrôle ont déjà tranché. Ce module traduit, et journalise ce qui a été
relâché en chemin.
"""

import logging
from collections import deque
from collections.abc import Callable
from pathlib import Path

from webradio.core.clock import Horloge
from webradio.core.controle import Nature
from webradio.core.file import File, FileVide
from webradio.core.grille import Grille
from webradio.core.jingles import Jingles
from webradio.core.modeles import Piste
from webradio.core.rng import Hasard
from webradio.core.sources import SourceIndisponible, SourceMusicale

logger = logging.getLogger(__name__)


class ProgrammeRadio:
    """La suite des entrées à diffuser, une par une.

    `suivante()` ne lève jamais : une source injoignable est contournée
    (SPECS.md §5.1), et `None` signifie « il n'y a plus rien », ce qui fait
    couper la radio **en le disant** plutôt que servir du silence.
    """

    def __init__(
        self,
        file: File,
        source: SourceMusicale,
        grille: Grille,
        jingles: Jingles,
        horloge: Horloge,
        hasard: Hasard,
        dossier_jingles: Path,
        *,
        sur_nature: Callable[[Nature, Piste | None], None],
    ) -> None:
        self._file = file
        self._source = source
        self._grille = grille
        self._jingles = jingles
        self._horloge = horloge
        self._hasard = hasard
        self._dossier = dossier_jingles
        self._sur_nature = sur_nature
        # `Jingles.dus()` s'épuise en le disant : il rend tout ce qui est dû et
        # l'oublie. Ne consommer que le premier perdrait les autres — ce qui
        # est exactement ce que SPECS.md §4.3 refuse quand un morceau long a
        # enjambé deux heures. On garde donc ceux qu'on n'a pas encore servis.
        self._en_attente: deque[str] = deque()

    def suivante(self) -> str | None:
        jingle = self._prochain_jingle()
        if jingle is not None:
            self._sur_nature(Nature.JINGLE, None)
            return str(jingle)
        return self._prochaine_piste()

    def preparer(self) -> None:
        """Résout le morceau suivant pendant que le courant joue.

        Appelée hors verrou par la chaîne : une source lente coûte alors du
        temps que personne n'attend, au lieu d'un trou à la jonction
        (docs/ffmpeg.md §2.2). Elle avale tout — se préparer est une commodité,
        jamais une cause d'arrêt.
        """
        try:
            self._file.preparer(self._grille.genre_a_tirer(self._hasard))
        except (SourceIndisponible, FileVide) as echec:
            logger.debug("préparation sans effet : %s", echec)

    def _prochain_jingle(self) -> Path | None:
        """Le prochain jingle dû dont le fichier existe réellement.

        Le noyau dit **quels noms** sont dus ; savoir si le fichier est là est
        une question de système de fichiers, donc elle se règle ici. Un jingle
        absent ne signale rien : c'est le mode d'emploi (SPECS.md §4.3).

        Les jingles restants sont conservés pour les jonctions suivantes : ils
        passent tous, à la suite, dans l'ordre où le noyau les a rendus.
        """
        self._en_attente.extend(self._jingles.dus())
        while self._en_attente:
            chemin = self._dossier / self._en_attente.popleft()
            if chemin.is_file():
                return chemin
        return None

    def _prochaine_piste(self) -> str | None:
        try:
            choix = self._file.suivant(self._grille.genre_a_tirer(self._hasard))
        except SourceIndisponible as panne:
            logger.warning("source injoignable, la radio coupe : %s", panne)
            return None
        except FileVide as vide:
            logger.warning("plus rien à diffuser : %s", vide)
            return None
        for repli in choix.replis:
            logger.info("repli : %s", repli)
        self._sur_nature(Nature.MUSIQUE, choix.piste)
        return self._source.entree(choix.piste)
