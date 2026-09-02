"""La piste suivante, vue par la chaîne de diffusion.

Ce module fait le lien entre le noyau, qui rend des `Pick` et des `Track`, et
la chaîne (`app/liquidsoap_playout.py`), qui n'attend qu'une chaîne de
caractères que Liquidsoap sait ouvrir.

Il ne décide rien : la grille, le tirage, la non-répétition, les jingles et le
contrôle ont déjà tranché. Il traduit, et journalise les replis.
"""

import logging
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from webradio.core.bands import Band, Schedule
from webradio.core.clock import Clock
from webradio.core.control import Control, Kind
from webradio.core.jingles import Jingles, full_hours_between, jingle_name
from webradio.core.models import Track
from webradio.core.planning import EffectiveSchedule, Segment
from webradio.core.programmes import Programme, Programming
from webradio.core.queue import EmptyQueue, Queue
from webradio.core.rng import Random
from webradio.core.rotation import Window
from webradio.core.shows import Show
from webradio.core.sources import MusicSource, SourceUnavailable

if TYPE_CHECKING:
    from webradio.app.show_scheduler import Shows

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Upcoming:
    """Une entrée de la liste des prochains titres (GOAL-058).

    `at` est l'heure estimée du début, `None` si rien ne permet de l'estimer.
    `expected` marque l'habillage prévu (jingle horaire, générique) qui n'est
    pas encore décidé, par opposition à ce qui est déjà tiré.
    """

    kind: Kind
    track: Track | None
    label: str | None
    at: datetime | None
    expected: bool = False


class RadioProgramme:
    """La suite des entrées à diffuser, une par une.

    `next_entry()` ne lève jamais : une source injoignable est contournée
    (SPECS.md §5.1). `None` signifie qu'il n'y a plus rien à diffuser, et la
    radio coupe en le journalisant plutôt que de servir du silence.
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
        effective: EffectiveSchedule | None = None,
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
        # Facultative : sans elle, l'avance s'estime sur les seules plages.
        self._effective = effective
        self._controle = control
        self._a_l_antenne = now_playing
        # Le morceau forcé par un encore, résolu dès la préparation pour que la
        # liste des prochains titres le montre (GOAL-067). L'ancre est gardée
        # pour en tirer un autre du même artiste si on le retire.
        self._encore_force: Track | None = None
        self._encore_ancre: Track | None = None
        # Un programme a sa propre fenêtre de non-répétition : sa liste est
        # courte, et partager celle du tirage libre ferait rétrécir l'une à
        # cause de l'autre (SPECS.md §4.13).
        self._fenetre_programme = programme_window if programme_window is not None else Window()
        # `Jingles.due_now()` rend tous les jingles dus et les oublie. On garde
        # ceux qui n'ont pas encore été servis, sinon un morceau long qui
        # enjambe deux heures en perdrait un (SPECS.md §4.3).
        self._en_attente: deque[str] = deque()
        # L'avance écartée par un encore, rejouée telle quelle après le jingle
        # et le titre forcé (GOAL-034).
        self._a_rejouer: deque[tuple[str, Kind, Track | None, str | None]] = deque()
        # Le moment effectif (programme, sinon plage) vu à la dernière
        # jonction. `...` tant qu'aucune jonction n'a eu lieu : une chaîne qui
        # démarre au milieu d'un moment ne rejoue pas son générique (GOAL-029).
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
            return entry
        return self._prochaine_piste()

    def current_moment(self) -> object:
        """Ce qui tire la musique en ce moment : le programme ouvert, sinon
        l'occurrence de plage, sinon `None` (tirage libre).

        Sert de clé pour dater une entrée d'avance (décision n°33) : la chaîne
        la retient avec chaque entrée demandée, puis compare à la jonction.
        """
        if self._programmation is not None:
            programme = self._programmation.current_programme()
            if programme is not None:
                return programme
        return self._grille.current_moment()

    def replay_later(self, entry: str, kind: Kind, track: Track | None, label: str | None) -> None:
        """Replace une entrée déjà demandée, à jouer après l'effet d'un encore."""
        self._a_rejouer.append((entry, kind, track, label))

    def forget_pending(self) -> None:
        """Oublie ce qui attendait une jonction, pour reprendre à neuf.

        Après une longue pause sans auditeur (SPECS.md §7 n°30), les jingles
        en attente et l'avance replacée par un encore n'ont plus de contexte
        valable. Le repère des moments repart comme au démarrage : une chaîne
        qui reprend au milieu d'un moment ne rejoue pas son générique
        (GOAL-029). L'encore voté n'est pas touché, il survit à la pause.
        """
        self._en_attente.clear()
        self._a_rejouer.clear()
        self._moment_vu = ...
        # `next_pick` sert l'avance sans regarder la contrainte : un morceau
        # tiré à 19 h passerait à 7 h le lendemain (SPECS.md §7 n°30).
        self._file.forget_prepared()

    def prepare(self, from_instant: datetime | None = None) -> None:
        """Résout les morceaux suivants pendant que le courant joue.

        Appelée hors verrou par la chaîne, pour qu'une source lente ne creuse
        pas un trou à la jonction (docs/ffmpeg.md §2.2). Ne lève jamais : la
        préparation est une commodité, pas une cause d'arrêt.

        `from_instant` est l'heure estimée du début du premier titre de
        l'avance (GOAL-058) : chaque créneau est tiré sous le moment qu'il
        trouvera en commençant, durée après durée. Sans estimation, tout se
        tire sous le moment présent, et l'avance datée (décision n°33) tranche
        à la jonction.

        Un créneau qui tomberait pendant un programme ou un direct est reporté
        à leur fin (GOAL-068) : la file n'y est pas servie, et un titre tiré
        pour cette heure-là serait jeté à la jonction, laissant la file vide à
        la reprise.
        """
        self._resoudre_encore()
        depart = self._horloge.now() if from_instant is None else from_instant
        self._file.revalidate(self._moments_des_creneaux(depart))
        instant = self._fin_des_creneaux(depart)
        try:
            while self._file.wants_more():
                instant = self._servi_a_partir_de(instant)
                self._file.prepare(self._grille.constraint_to_draw(self._hasard, at=instant))
                instant = instant + self._file.advance[-1].duration
        except (SourceUnavailable, EmptyQueue) as echec:
            logger.debug("préparation sans effet : %s", echec)

    def _servi_a_partir_de(self, instant: datetime) -> datetime:
        """L'heure réelle du début de ce créneau (GOAL-068). Sans grille
        effective, `instant` tel quel : les programmes et les directs sont
        alors ignorés."""
        if self._effective is None:
            return instant
        return self._effective.served_from(instant)

    def _moments_des_creneaux(self, depart: datetime) -> list[object]:
        moments: list[object] = []
        instant = depart
        for track in self._file.advance:
            instant = self._servi_a_partir_de(instant)
            moments.append(self._grille.moment_at(instant))
            instant = instant + track.duration
        return moments

    def _fin_des_creneaux(self, depart: datetime) -> datetime:
        instant = depart
        for track in self._file.advance:
            instant = self._servi_a_partir_de(instant) + track.duration
        return instant

    def upcoming(self, from_instant: datetime | None = None) -> list[Upcoming]:
        """Les entrées à venir, dans l'ordre, avec l'heure estimée de chaque
        début (GOAL-058) : ce qui attend déjà, puis l'avance de la file, avec
        entre les deux l'habillage prévu (jingles horaires, génériques).

        Rien n'est décidé ici : la liste dit ce que `next_entry` rendrait si
        les durées estimées tenaient. Pendant un programme, l'avance de la
        file n'y figure pas, sa musique vient d'une liste (SPECS.md §4.13).
        """
        instant = from_instant
        items: list[Upcoming] = []
        for name in self._en_attente:
            items.append(Upcoming(Kind.JINGLE, None, Path(name).stem, instant))
        if self._encore_force is not None:
            items.append(Upcoming(Kind.MUSIC, self._encore_force, None, instant))
            if instant is not None:
                instant = instant + self._encore_force.duration
        for _, kind, track, label in self._a_rejouer:
            items.append(Upcoming(kind, track, label, instant))
            if track is not None and instant is not None:
                instant = instant + track.duration
        if self._programmation is not None and self._programmation.playlist_to_draw() is not None:
            return items
        precedent = instant
        for index, (track, moment) in enumerate(self._file.dated_advance):
            # La lecture est concurrente de la jonction : on ne décide rien et
            # on s'arrête à la première entrée rassise, comme `revalidate`.
            # Sans heure estimée, seule la tête se juge, contre l'instant
            # présent : la suite a pu être tirée pour un moment à venir.
            if instant is not None:
                # Le même report qu'à la préparation, sinon les deux heures
                # divergent et un titre tiré pour l'heure d'après un direct
                # est jugé rassis (GOAL-070).
                instant = self._servi_a_partir_de(instant)
                if precedent is not None:
                    remplacement = self._remplacement_entre(precedent, instant)
                    if remplacement is not None:
                        annonce = self._annonce_du_remplacement(remplacement)
                        items.extend(annonce)
                        # La suite ne se date qu'après une émission nommée
                        # dont la fin est déclarée (SPECS.md §4.8).
                        if not annonce or remplacement.end is None:
                            break
                rassise = moment != self._grille.moment_at(instant)
            else:
                rassise = index == 0 and moment != self._grille.current_moment()
            if rassise:
                break
            if instant is not None and precedent is not None:
                items.extend(self._habillage_prevu(precedent, instant))
            items.append(Upcoming(Kind.MUSIC, track, None, instant))
            precedent = instant
            instant = None if instant is None else instant + track.duration
        return items

    def _remplacement_entre(self, depuis: datetime, jusqu_a: datetime) -> Segment | None:
        """L'émission ou le programme qui remplacera la file entre ces deux
        heures, ou `None`. Sans grille effective, toujours `None` (GOAL-068)."""
        if self._effective is None:
            return None
        return self._effective.next_replacement(depuis, jusqu_a)

    @staticmethod
    def _annonce_du_remplacement(remplacement: Segment) -> list[Upcoming]:
        """L'annonce du remplacement : le nom d'une émission, rien pour un
        programme, que la radio n'annonce pas (SPECS.md §4.8)."""
        if not isinstance(remplacement.content, Show):
            return []
        nom = remplacement.content.name
        return [Upcoming(Kind.SHOW, None, nom, remplacement.start, True)]

    def _habillage_prevu(self, depuis: datetime, jusqu_a: datetime) -> list[Upcoming]:
        """Les jingles et génériques que la jonction de `jusqu_a` rendrait,
        dans l'ordre de `_prochain_jingle` : générique sortant, heures pleines,
        générique entrant. Seuls les fichiers présents sont listés."""
        prevus: list[Upcoming] = []
        avant, apres = self._moment_effectif_a(depuis), self._moment_effectif_a(jusqu_a)
        if avant != apres:
            sortant = avant.outro if isinstance(avant, Programme | Band) else None
            if sortant is not None and self._variantes(sortant):
                prevus.append(Upcoming(Kind.JINGLE, None, Path(sortant).stem, jusqu_a, True))
        for heure in full_hours_between(depuis, jusqu_a):
            if self._variantes(jingle_name(heure)):
                prevus.append(Upcoming(Kind.JINGLE, None, f"{heure:%H} h", jusqu_a, True))
        entrant = apres.intro if avant != apres and apres is not None else None
        if entrant is not None and self._variantes(entrant):
            prevus.append(Upcoming(Kind.JINGLE, None, Path(entrant).stem, jusqu_a, True))
        return prevus

    def _moment_effectif_a(self, instant: datetime) -> Programme | Band | None:
        if self._programmation is not None:
            programme = self._programmation.programme_at(instant)
            if programme is not None:
                return programme
        return self._grille.band_at(instant)

    def break_run(self) -> bool:
        """Rompt la suite au hasard en cours, s'il y en a une (GOAL-059)."""
        return self._file.break_run()

    def forget_advance(self) -> None:
        """Jette l'avance de la file, et elle seule : les jingles en attente
        et l'encore restent dus (GOAL-059)."""
        self._file.forget_prepared()

    def withdraw(self, identifier: str) -> bool:
        """Retire un titre de l'avance de la file, un autre sera tiré à sa
        place (GOAL-058). Le morceau forcé par un encore se retire aussi, un
        autre du même artiste le remplace (GOAL-067). Rend `False` si
        l'identifiant n'est pas dans l'avance."""
        force, ancre = self._encore_force, self._encore_ancre
        if (
            force is not None
            and force.identifier == identifier
            and ancre is not None
            and self._controle is not None
        ):
            self._encore_force = self._morceau_du_meme(self._controle, ancre)
            logger.info("retiré avant diffusion, l'encore en force un autre : %s", identifier)
            return True
        if not self._file.withdraw(identifier):
            return False
        logger.info("retiré avant diffusion : %s", identifier)
        return True

    def _prochaine_emission(self) -> str | None:
        """L'émission due, ou `None`. Elle l'emporte sur tout le reste.

        Elle remplace la programmation, habillage compris (SPECS.md §4.11).
        Les jingles dus pendant sa durée sont abandonnés par `core/jingles.py`,
        à qui on signale simplement qu'une émission passe.
        """
        if self._emissions is None:
            return None
        due = self._emissions.due()
        # `due_now()` consomme : garder ce qu'il rend, sinon les jingles dus
        # sont perdus à chaque jonction (GOAL-014-T01). Pendant une émission,
        # il rend () et c'est voulu.
        self._en_attente.extend(self._jingles.due_now(during_show=due is not None))
        if due is None:
            return None
        show, audio, episode = due
        libelle = f"{show.name} · {episode}" if episode else show.name
        logger.info("émission « %s » à l'antenne", libelle)
        self._sur_nature(Kind.SHOW, None, libelle)
        return audio

    def _prochain_jingle(self) -> Path | None:
        """Le prochain jingle dû dont le fichier existe, ou `None`.

        Le noyau dit quels noms sont dus ; l'existence du fichier se vérifie
        ici. Un jingle absent est ignoré sans message (SPECS.md §4.3). Les
        jingles restants sont gardés pour les jonctions suivantes, dans l'ordre
        où le noyau les a rendus.

        Un nom peut avoir des variantes (`14h.mp3`, `14h-a.mp3`, `14h-b.mp3`),
        et l'une d'elles est tirée au hasard injecté (GOAL-033). Le fichier de
        base est optionnel dès qu'une variante existe.
        """
        sortant, entrant = self._generiques_de_transition()
        if sortant is not None:
            self._en_attente.append(sortant)
        self._en_attente.extend(self._jingles.due_now())
        if entrant is not None:
            self._en_attente.append(entrant)
        while self._en_attente:
            candidates = self._variantes(self._en_attente.popleft())
            if candidates:
                return candidates[0] if len(candidates) == 1 else self._hasard.pick(candidates)
        return None

    def _variantes(self, name: str) -> list[Path]:
        """Les fichiers qui répondent à ce nom : lui-même, puis ses variantes."""
        path = self._dossier / name
        candidates = sorted(path.parent.glob(f"{path.stem}-*{path.suffix}"))
        if path.is_file():
            candidates.insert(0, path)
        return candidates

    def _generiques_de_transition(self) -> tuple[str | None, str | None]:
        """Le générique de fin du moment qui s'achève et celui d'ouverture du
        moment qui commence (GOAL-029), chacun `None` s'il n'y a rien à jouer.

        Le moment effectif suit la règle de la musique : le programme
        l'emporte sur la plage. Un générique absent est ignoré comme tout
        jingle (SPECS.md §4.3).
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
        """La piste suivante : celle du programme ouvert, sinon celle de la
        file. `None` si la source est injoignable ou la file vide.

        Un programme l'emporte sur une plage, car il nomme des morceaux plutôt
        qu'un genre (SPECS.md §4.13). Cette priorité est provisoire, SPECS.md
        §7 n°19 n'est pas tranchée.
        """
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
        return self._source.entry(pick.track)

    def _piste_après_encore(self) -> str | None:
        """Le morceau forcé par un encore, ou `None`."""
        self._resoudre_encore()
        track = self._encore_force
        if track is None:
            return None
        self._encore_force, self._encore_ancre = None, None
        self._sur_nature(Kind.MUSIC, track, None)
        return self._source.entry(track)

    def _resoudre_encore(self) -> None:
        """Consomme l'encore voté, s'il y en a un, et tire le morceau qu'il force.

        Fait à la préparation plutôt qu'à la jonction (GOAL-067) : la liste
        des prochains titres le montre, et l'ancre est bien le morceau du vote.
        À la jonction, c'est déjà le jingle d'encore qui passe. Sans ancre, le
        vote a agi (pondération, jingle) mais ne force rien, et on le
        journalise.
        """
        if self._controle is None:
            return
        more = self._controle.take_more()
        if more is None:
            return
        if more.anchor is None:
            logger.info("encore sans morceau à l'antenne : rien à forcer")
            return
        self._encore_ancre = more.anchor
        self._encore_force = self._morceau_du_meme(self._controle, more.anchor)

    def _morceau_du_meme(self, control: Control, courant: Track) -> Track | None:
        """Le morceau qu'un encore sur `courant` force : le même artiste, puis
        les replis du noyau, chacun journalisé. Pendant un programme, cherché
        dans la liste et jamais au-dehors (SPECS.md §7 n°20).
        """
        if self._programmation is not None:
            liste = self._programmation.playlist_to_draw()
            if liste is not None:
                return self._encore_dans_la_liste(liste, courant)
        try:
            pick = control.track_after_more(courant)
        except (SourceUnavailable, EmptyQueue) as failure:
            logger.warning("encore sans suite : %s", failure)
            return None
        for fallback in pick.fallbacks:
            logger.info("repli d'encore : %s", fallback)
        return pick.track

    def _encore_dans_la_liste(self, liste: str, courant: Track) -> Track | None:
        """Un autre morceau du même artiste dans la liste du programme ouvert.

        À défaut, `None` : le tirage retombe dans la liste par le chemin
        normal du programme, jamais au-dehors (SPECS.md §7 n°20).
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
        return track

    def _piste_du_programme(self) -> str | None:
        """Un morceau tiré dans la liste du programme ouvert, s'il y en a un.

        Rend `None` sans programme ouvert, et aussi quand la liste est
        introuvable, vide ou illisible : la radio se replie alors sur le
        tirage libre (SPECS.md §7 n°21). Le repli est journalisé, une liste
        qui ne répond plus est souvent une faute de frappe.
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
        return self._source.entry(track)
