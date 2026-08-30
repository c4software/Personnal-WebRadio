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
from typing import TYPE_CHECKING

from webradio.core.clock import Horloge
from webradio.core.control import Nature
from webradio.core.queue import File, FileVide
from webradio.core.bands import Grille
from webradio.core.jingles import Jingles
from webradio.core.models import Piste
from webradio.core.programmes import Programmation
from webradio.core.rotation import Fenetre
from webradio.core.rng import Hasard
from webradio.core.sources import SourceIndisponible, SourceMusicale

if TYPE_CHECKING:
    from webradio.app.show_scheduler import Emissions

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
        programmation: Programmation | None = None,
        fenetre_programme: Fenetre | None = None,
        emissions: "Emissions | None" = None,
    ) -> None:
        self._file = file
        self._source = source
        self._grille = grille
        self._jingles = jingles
        self._horloge = horloge
        self._hasard = hasard
        self._dossier = dossier_jingles
        self._sur_nature = sur_nature
        self._programmation = programmation
        self._emissions = emissions
        # Un programme a sa propre fenêtre de non-répétition : la liste est
        # courte, et partager celle du tirage libre ferait rétrécir l'une à
        # cause de l'autre (SPECS.md §4.13).
        self._fenetre_programme = fenetre_programme if fenetre_programme is not None else Fenetre()
        # `Jingles.dus()` s'épuise en le disant : il rend tout ce qui est dû et
        # l'oublie. Ne consommer que le premier perdrait les autres — ce qui
        # est exactement ce que SPECS.md §4.3 refuse quand un morceau long a
        # enjambé deux heures. On garde donc ceux qu'on n'a pas encore servis.
        self._en_attente: deque[str] = deque()

    def suivante(self) -> str | None:
        emission = self._prochaine_emission()
        if emission is not None:
            return emission
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

    def _prochaine_emission(self) -> str | None:
        """Une émission due l'emporte sur tout le reste.

        Elle **remplace** la programmation, habillage compris : ni grille, ni
        non-répétition, ni jingle (SPECS.md §4.11). Les jingles dus pendant sa
        durée sont abandonnés, ce dont `core/jingles.py` se charge — on lui dit
        simplement qu'une émission passe.
        """
        if self._emissions is None:
            return None
        due = self._emissions.due()
        self._jingles.dus(pendant_emission=due is not None)
        if due is None:
            return None
        emission, audio = due
        logger.info("émission « %s » à l'antenne", emission.nom)
        self._sur_nature(Nature.EMISSION, None)
        return audio

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
        """La piste suivante, en respectant l'ordre de priorité.

        **Une émission l'emporte sur un programme, un programme sur une plage
        thématique.** L'émission remplace toute la programmation (SPECS.md
        §4.11) ; le programme est plus précis qu'une plage puisqu'il nomme des
        morceaux plutôt qu'un genre (SPECS.md §4.13).

        La priorité programme/plage est **provisoire** : SPECS.md §7 n°19 n'est
        pas tranchée, et la coexistence des deux mécanismes reste en question.
        """
        depuis_le_programme = self._piste_du_programme()
        if depuis_le_programme is not None:
            return depuis_le_programme
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

    def _piste_du_programme(self) -> str | None:
        """Un morceau tiré dans la liste du programme ouvert, s'il y en a un.

        Rend `None` quand aucun programme n'est ouvert **et** quand la liste ne
        donne rien : une liste introuvable, vidée ou renommée ne fait pas taire
        la radio, elle se replie sur le tirage libre (SPECS.md §7 n°21). Le
        repli est journalisé, parce qu'une liste qui ne répond plus est presque
        toujours une faute de frappe qu'on veut voir.
        """
        if self._programmation is None:
            return None
        nom = self._programmation.playlist_a_tirer()
        if nom is None:
            return None
        try:
            pistes = self._source.pistes_de_la_liste_de_lecture(nom)
        except SourceIndisponible as panne:
            logger.warning("liste « %s » illisible, repli sur le tirage libre : %s", nom, panne)
            return None
        if not pistes:
            logger.info("liste « %s » introuvable ou vide, repli sur le tirage libre", nom)
            return None
        autorisees = self._fenetre_programme.filtrer(pistes)
        while not autorisees:
            self._fenetre_programme.retrecir()
            autorisees = self._fenetre_programme.filtrer(pistes)
        piste = self._hasard.choisir(autorisees)
        self._fenetre_programme.retenir(piste)
        self._sur_nature(Nature.MUSIQUE, piste)
        return self._source.entree(piste)
