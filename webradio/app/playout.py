"""Ce qui décide de la piste suivante, vu par la chaîne de diffusion.

C'est la charnière du projet : d'un côté le noyau, qui rend des `Choix` et des
`Piste` ; de l'autre la chaîne, qui ne veut qu'une chaîne de caractères que
Liquidsoap sait ouvrir (`app/liquidsoap_playout.py`, `Programme`).

Rien ici ne décide : la grille, le tirage, la non-répétition, les jingles et le
contrôle ont déjà tranché. Ce module traduit, et journalise ce qui a été
relâché en chemin.
"""

import logging
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from webradio.core.bands import Band, Schedule
from webradio.core.clock import Clock
from webradio.core.control import Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.programmes import Programme, Programming
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
        on_kind: Callable[[Kind, Track | None, str | None], None],
        programming: Programming | None = None,
        programme_window: Window | None = None,
        shows: "Shows | None" = None,
        control: Control | None = None,
        now_playing: Callable[[], Track | None] | None = None,
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
        self._controle = control
        self._a_l_antenne = now_playing
        self._derniere_piste: Track | None = None
        # Un programme a sa propre fenêtre de non-répétition : la liste est
        # courte, et partager celle du tirage libre ferait rétrécir l'une à
        # cause de l'autre (SPECS.md §4.13).
        self._fenetre_programme = programme_window if programme_window is not None else Window()
        # `Jingles.dus()` s'épuise en le disant : il rend tout ce qui est dû et
        # l'oublie. Ne consommer que le premier perdrait les autres — ce qui
        # est exactement ce que SPECS.md §4.3 refuse quand un morceau long a
        # enjambé deux heures. On garde donc ceux qu'on n'a pas encore servis.
        self._en_attente: deque[str] = deque()
        # Ce qui avait été demandé d'avance et qu'un encore a écarté : rejoué
        # tel quel APRÈS le jingle et le titre forcé — rien n'est jeté
        # (GOAL-034, schéma de l'auteur : Yamê → encore.mp3 → Yamê-2 → Tryo).
        self._a_rejouer: deque[tuple[str, Kind, Track | None, str | None]] = deque()
        # Le moment effectif — programme d'abord, sinon plage — vu à la
        # dernière jonction. `...` tant qu'aucune jonction n'a eu lieu : une
        # chaîne qui démarre AU MILIEU d'un moment ne rejoue pas son
        # générique (GOAL-029).
        self._moment_vu: object = ...

    def next_entry(self) -> str | None:
        show = self._prochaine_emission()
        if show is not None:
            return show
        jingle = self._prochain_jingle()
        if jingle is not None:
            self._sur_nature(Kind.JINGLE, None, None)
            return str(jingle)
        forced = self._piste_après_encore()
        if forced is not None:
            return forced
        if self._a_rejouer:
            entry, kind, track, label = self._a_rejouer.popleft()
            self._sur_nature(kind, track, label)
            if track is not None:
                self._derniere_piste = track
            return entry
        return self._prochaine_piste()

    def current_moment(self) -> object:
        """Ce qui tire la musique en ce moment : le programme ouvert, sinon
        l'occurrence de plage, sinon rien — le tirage libre.

        C'est la clé qui date une entrée d'avance (décision n°33) : la
        charnière la retient avec chaque entrée demandée, et compare.
        """
        if self._programmation is not None:
            programme = self._programmation.current_programme()
            if programme is not None:
                return programme
        return self._grille.current_moment()

    def prepared(self) -> Track | None:
        """Le morceau déjà tiré qui suivra, quand c'est bien la file qui parlera.

        « À suivre » ne voit que l'avance du diffuseur, et celle-ci n'est
        parfois que de l'habillage — le panneau restait alors vide le temps
        d'une chanson entière (GOAL-054). La file, elle, a déjà résolu la
        suite : il suffit de la lire.

        `None` pendant un **programme** : sa musique vient d'une liste, pas de
        la file (SPECS.md §4.13), et l'avance préparée ne passera pas. Annoncer
        un morceau qui ne viendra jamais serait pire que de n'annoncer rien.
        """
        if self._a_rejouer:
            # Une avance replacée par un « encore » passe AVANT le tirage
            # suivant (GOAL-034) : annoncer la file serait annoncer le mauvais.
            return None
        if self._programmation is not None and self._programmation.playlist_to_draw() is not None:
            return None
        return self._file.prepared(self._grille.current_moment())

    def replay_later(self, entry: str, kind: Kind, track: Track | None, label: str | None) -> None:
        """Replace une entrée déjà demandée, à jouer après l'effet d'un encore."""
        self._a_rejouer.append((entry, kind, track, label))

    def forget_pending(self) -> None:
        """Oublie ce qui attendait une jonction : la reprise se fait à neuf.

        Après une longue pause sans auditeur (SPECS.md §7 n°30), ce qui
        attendait ment : les génériques annoncent un moment fini, l'avance
        qu'un encore d'avant la pause avait replacée n'a plus son contexte.
        Le repère des moments repart comme au démarrage — une chaîne qui
        reprend au milieu d'un moment ne rejoue pas son générique (GOAL-029).
        L'encore lui-même n'est pas touché : un vote est une demande
        explicite, il survit à la pause.
        """
        self._en_attente.clear()
        self._a_rejouer.clear()
        self._moment_vu = ...
        # Et l'avance de la file, que la purge n'atteignait pas : `next_pick`
        # la sert sans regarder la contrainte, donc un morceau tiré à 19 h
        # serait passé à 7 h le lendemain — le contraire du tirage neuf promis
        # (SPECS.md §7 n°30). Trouvé le 2026-09-02 en câblant « À suivre ».
        self._file.forget_prepared()

    def prepare(self) -> None:
        """Résout le morceau suivant pendant que le courant joue.

        Appelée hors verrou par la chaîne : une source lente coûte alors du
        temps que personne n'attend, au lieu d'un trou à la jonction
        (docs/ffmpeg.md §2.2). Elle avale tout — se préparer est une commodité,
        jamais une cause d'arrêt.
        """
        try:
            self._file.prepare(self._grille.constraint_to_draw(self._hasard))
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
        show, audio, episode = due
        libelle = f"{show.name} · {episode}" if episode else show.name
        logger.info("émission « %s » à l'antenne", libelle)
        self._sur_nature(Kind.SHOW, None, libelle)
        return audio

    def _prochain_jingle(self) -> Path | None:
        """Le prochain jingle dû dont le fichier existe réellement.

        Le noyau dit **quels noms** sont dus ; savoir si le fichier est là est
        une question de système de fichiers, donc elle se règle ici. Un jingle
        absent ne signale rien : c'est le mode d'emploi (SPECS.md §4.3).

        Les jingles restants sont conservés pour les jonctions suivantes : ils
        passent tous, à la suite, dans l'ordre où le noyau les a rendus.

        Un nom peut avoir des **variantes** — `14h.mp3`, `14h-a.mp3`,
        `14h-b.mp3`… — et l'une d'elles est tirée au hasard injecté, pour que
        la radio ne serine pas le même jingle (GOAL-033). Le fichier de base
        est lui-même optionnel dès qu'une variante existe.
        """
        sortant, entrant = self._generiques_de_transition()
        if sortant is not None:
            self._en_attente.append(sortant)
        self._en_attente.extend(self._jingles.due_now())
        if entrant is not None:
            self._en_attente.append(entrant)
        while self._en_attente:
            path = self._dossier / self._en_attente.popleft()
            candidates = sorted(path.parent.glob(f"{path.stem}-*{path.suffix}"))
            if path.is_file():
                candidates.insert(0, path)
            if candidates:
                return candidates[0] if len(candidates) == 1 else self._hasard.pick(candidates)
        return None

    def _generiques_de_transition(self) -> tuple[str | None, str | None]:
        """Le générique de fin du moment qui s'achève, celui d'ouverture du
        moment qui commence — comme une radio classique (GOAL-029).

        Le moment effectif suit la règle de la musique : le programme
        l'emporte sur la plage. Les génériques sont optionnels, et un fichier
        absent sera ignoré comme tout jingle (SPECS.md §4.3).
        """
        courant: Programme | Band | None = None
        if self._programmation is not None:
            courant = self._programmation.current_programme()
        if courant is None:
            courant = self._grille.current_band()
        precedent, self._moment_vu = self._moment_vu, courant
        if precedent is ... or precedent == courant:
            return None, None
        sortant = precedent.outro if isinstance(precedent, Programme | Band) else None
        entrant = courant.intro if courant is not None else None
        return sortant, entrant

    def _prochaine_piste(self) -> str | None:
        """La piste suivante, en respectant l'ordre de priorité.

        **Une émission l'emporte sur un programme, un programme sur une plage
        thématique.** L'émission remplace toute la programmation (SPECS.md
        §4.11) ; le programme est plus précis qu'une plage puisqu'il nomme des
        morceaux plutôt qu'un genre (SPECS.md §4.13).

        La priorité programme/plage est **provisoire** : SPECS.md §7 n°19 n'est
        pas tranchée, et la coexistence des deux mécanismes reste en question.
        """
        # Un « encore » accepté force le prochain morceau chez le même artiste
        # (SPECS.md §4.6) — le noyau descend seul vers le genre puis le tirage
        # libre si l'artiste est épuisé, et chaque repli est dit.
        depuis_le_programme = self._piste_du_programme()
        if depuis_le_programme is not None:
            return depuis_le_programme
        try:
            pick = self._file.next_pick(self._grille.constraint_to_draw(self._hasard))
        except SourceUnavailable as failure:
            logger.warning("source injoignable, la radio coupe : %s", failure)
            return None
        except EmptyQueue as vide:
            logger.warning("plus rien à diffuser : %s", vide)
            return None
        for fallback in pick.fallbacks:
            logger.info("repli : %s", fallback)
        self._sur_nature(Kind.MUSIC, pick.track, None)
        self._derniere_piste = pick.track
        return self._source.entry(pick.track)

    def _piste_après_encore(self) -> str | None:
        """Le morceau forcé par un « encore », ou rien.

        L'ancre est le morceau **à l'antenne** ; à défaut — un redémarrage l'a
        oublié — le dernier morceau rendu. Sans ancre du tout, le vote a agi
        (pondération, jingle) mais n'a rien sur quoi forcer : on le dit.
        """
        if self._controle is None or not self._controle.take_more():
            return None
        courant = self._a_l_antenne() if self._a_l_antenne is not None else None
        if courant is None:
            courant = self._derniere_piste
        if courant is None:
            logger.info("encore sans morceau à l'antenne : rien à forcer")
            return None
        # Pendant un programme, « encore » cherche DANS la liste et y retombe,
        # jamais au-dehors (SPECS.md §7 n°20) : sortir de la liste sur un
        # encore trahirait le choix des morceaux.
        if self._programmation is not None:
            liste = self._programmation.playlist_to_draw()
            if liste is not None:
                return self._encore_dans_la_liste(liste, courant)
        try:
            pick = self._controle.track_after_more(courant)
        except (SourceUnavailable, EmptyQueue) as failure:
            logger.warning("encore sans suite : %s", failure)
            return None
        for fallback in pick.fallbacks:
            logger.info("repli d'encore : %s", fallback)
        self._sur_nature(Kind.MUSIC, pick.track, None)
        self._derniere_piste = pick.track
        return self._source.entry(pick.track)

    def _encore_dans_la_liste(self, liste: str, courant: Track) -> str | None:
        """Le même artiste, cherché dans la liste du programme ouvert.

        À défaut, `None` : le tirage retombe dans la liste par le chemin
        normal du programme — jamais au-dehors (SPECS.md §7 n°20).
        """
        try:
            tracks = self._source.tracks_from_playlist(liste)
        except SourceUnavailable as failure:
            logger.warning("encore dans « %s » : liste illisible — %s", liste, failure)
            return None
        du_meme = [
            t for t in tracks if t.artist == courant.artist and t.identifier != courant.identifier
        ]
        if not du_meme:
            logger.info("encore dans « %s » : artiste épuisé, on reste dans la liste", liste)
            return None
        track = self._hasard.pick(du_meme)
        self._fenetre_programme.remember(track)
        self._sur_nature(Kind.MUSIC, track, None)
        self._derniere_piste = track
        return self._source.entry(track)

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
        self._sur_nature(Kind.MUSIC, track, None)
        self._derniere_piste = track
        return self._source.entry(track)
