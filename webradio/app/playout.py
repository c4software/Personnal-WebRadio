"""Ce qui décide de la piste suivante, vu par la chaîne de diffusion.

C'est la charnière du projet : d'un côté le noyau, qui rend des `Choix` et des
`Piste` ; de l'autre la chaîne, qui ne veut qu'une chaîne de caractères que
ffmpeg sait ouvrir (`adapters/ffmpeg/encoder.py`, `Programme`).

Rien ici ne décide : la grille, le tirage, la non-répétition, les jingles et le
contrôle ont déjà tranché. Ce module traduit, et journalise ce qui a été
relâché en chemin.
"""

import logging
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from webradio.core.bands import Schedule
from webradio.core.clock import Clock
from webradio.core.control import Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.programmes import Programming
from webradio.core.queue import EmptyQueue, Queue
from webradio.core.rng import Random
from webradio.core.rotation import Window
from webradio.core.sources import MusicSource, SourceUnavailable

if TYPE_CHECKING:
    from webradio.app.show_scheduler import Shows

logger = logging.getLogger(__name__)


class RadioProgramme:
    """La suite des entrées à diffuser, une par une.

    `suivante()` ne lève jamais : une source injoignable est contournée
    (SPECS.md §5.1), et `None` signifie « il n'y a plus rien », ce qui fait
    couper la radio **en le disant** plutôt que servir du silence.
    """

    def __init__(
        self,
        queue: Queue,
        source: MusicSource,
        grille: Schedule,
        jingles: Jingles,
        clock: Clock,
        random: Random,
        jingle_folder: Path,
        *,
        on_kind: Callable[[Kind, Track | None], None],
        programming: Programming | None = None,
        programme_window: Window | None = None,
        shows: "Shows | None" = None,
    ) -> None:
        self._file = queue
        self._source = source
        self._grille = grille
        self._jingles = jingles
        self._horloge = clock
        self._hasard = random
        self._dossier = jingle_folder
        self._sur_nature = on_kind
        self._programmation = programming
        self._emissions = shows
        # Un programme a sa propre fenêtre de non-répétition : la liste est
        # courte, et partager celle du tirage libre ferait rétrécir l'une à
        # cause de l'autre (SPECS.md §4.13).
        self._fenetre_programme = programme_window if programme_window is not None else Window()
        # `Jingles.dus()` s'épuise en le disant : il rend tout ce qui est dû et
        # l'oublie. Ne consommer que le premier perdrait les autres — ce qui
        # est exactement ce que SPECS.md §4.3 refuse quand un morceau long a
        # enjambé deux heures. On garde donc ceux qu'on n'a pas encore servis.
        self._en_attente: deque[str] = deque()

    def next_entry(self) -> str | None:
        show = self._prochaine_emission()
        if show is not None:
            return show
        jingle = self._prochain_jingle()
        if jingle is not None:
            self._sur_nature(Kind.JINGLE, None)
            return str(jingle)
        return self._prochaine_piste()

    def prepare(self) -> None:
        """Résout le morceau suivant pendant que le courant joue.

        Appelée hors verrou par la chaîne : une source lente coûte alors du
        temps que personne n'attend, au lieu d'un trou à la jonction
        (docs/ffmpeg.md §2.2). Elle avale tout — se préparer est une commodité,
        jamais une cause d'arrêt.
        """
        try:
            self._file.prepare(self._grille.genre_to_draw(self._hasard))
        except (SourceUnavailable, EmptyQueue) as echec:
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
        # `due_now()` consomme : ce qu'il rend ici doit être gardé, sinon les
        # jingles dus sont avalés à chaque jonction et ne sortent jamais
        # (GOAL-014-T01). Pendant une émission, il rend () et c'est voulu.
        self._en_attente.extend(self._jingles.due_now(during_show=due is not None))
        if due is None:
            return None
        show, audio = due
        logger.info("émission « %s » à l'antenne", show.name)
        self._sur_nature(Kind.SHOW, None)
        return audio

    def _prochain_jingle(self) -> Path | None:
        """Le prochain jingle dû dont le fichier existe réellement.

        Le noyau dit **quels noms** sont dus ; savoir si le fichier est là est
        une question de système de fichiers, donc elle se règle ici. Un jingle
        absent ne signale rien : c'est le mode d'emploi (SPECS.md §4.3).

        Les jingles restants sont conservés pour les jonctions suivantes : ils
        passent tous, à la suite, dans l'ordre où le noyau les a rendus.
        """
        self._en_attente.extend(self._jingles.due_now())
        while self._en_attente:
            path = self._dossier / self._en_attente.popleft()
            if path.is_file():
                return path
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
            pick = self._file.next_pick(self._grille.genre_to_draw(self._hasard))
        except SourceUnavailable as failure:
            logger.warning("source injoignable, la radio coupe : %s", failure)
            return None
        except EmptyQueue as vide:
            logger.warning("plus rien à diffuser : %s", vide)
            return None
        for fallback in pick.fallbacks:
            logger.info("repli : %s", fallback)
        self._sur_nature(Kind.MUSIC, pick.track)
        return self._source.entry(pick.track)

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
        name = self._programmation.playlist_to_draw()
        if name is None:
            return None
        try:
            tracks = self._source.tracks_from_playlist(name)
        except SourceUnavailable as failure:
            logger.warning("liste « %s » illisible, repli sur le tirage libre : %s", name, failure)
            return None
        if not tracks:
            logger.info("liste « %s » introuvable ou vide, repli sur le tirage libre", name)
            return None
        allowed = self._fenetre_programme.filter_out(tracks)
        while not allowed:
            self._fenetre_programme.shrink()
            allowed = self._fenetre_programme.filter_out(tracks)
        track = self._hasard.pick(allowed)
        self._fenetre_programme.remember(track)
        self._sur_nature(Kind.MUSIC, track)
        return self._source.entry(track)
