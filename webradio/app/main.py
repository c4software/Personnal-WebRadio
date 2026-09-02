"""Le point d'entrée, et le seul module qui connaît tout le monde.

L'assemblage se fait à la main, une fois au démarrage, sans conteneur ni
framework (ARCHITECTURE.md §3). C'est le seul endroit où le noyau, les
adaptateurs et la configuration se rencontrent. Ce module ne décide rien : il
construit, branche et attend.
"""

import argparse
import logging
import os
import signal
import sys
import threading
from collections.abc import Mapping, Sequence
from datetime import timedelta
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version
from pathlib import Path

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import Config
from webradio.adapters.config.schema import Show as ShowSettings
from webradio.adapters.podcast.feed import PodcastFeed, UrllibReader
from webradio.adapters.sources.subsonic import SubsonicSource, UrllibTransport
from webradio.adapters.state.database import Scope as StateScope
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.web.api import Kind as WebKind
from webradio.adapters.web.api import OnAir, PlayedEntry, UpcomingEntry, Verdict, VoteScore
from webradio.adapters.web.views import create_app
from webradio.adapters.youtube.channel import YoutubeChannel
from webradio.app.learning import Learning
from webradio.app.liquidsoap_playout import LiquidsoapPlayout
from webradio.app.playout import RadioProgramme
from webradio.app.radio import SANS_THEME_A_RETIRER, ListenerCount, LiveRadio
from webradio.app.show_scheduler import Shows
from webradio.core.bands import Band, Constraint, Schedule
from webradio.core.clock import Clock, SystemClock
from webradio.core.control import Control
from webradio.core.jingles import Jingles
from webradio.core.mystery import RandomTheme
from webradio.core.planning import EffectiveSchedule, Segment
from webradio.core.programmes import DAYS, Programme, Programming
from webradio.core.queue import Queue
from webradio.core.rng import RealRandom
from webradio.core.rotation import Window
from webradio.core.runs import Mode, Runs
from webradio.core.shows import Show, ShowSchedule
from webradio.core.weighting import SLOPE_PER_VOTE

logger = logging.getLogger(__name__)

NAME = "local-webradio"


def version() -> str:
    """La version du paquet, lue dans les métadonnées d'installation pour ne
    pas la dupliquer ici."""
    try:
        return _version("local-webradio")
    except PackageNotFoundError:
        return "0.0.0+source"


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=NAME, description="Une radio qui n'existe que branchée")
    parser.add_argument("--config", type=Path, default=Path("webradio.toml"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    return parser.parse_args(argv)


def _libelle_de_plage(band: Band) -> list[str]:
    """Les libellés que le planning affiche pour une plage.

    Une plage au hasard n'a pas encore de thème, il est tiré à l'occurrence.
    Le planning annonce donc seulement la sorte du tirage.
    """
    if band.random_theme == "artist":
        return ["Au hasard · un artiste"]
    if band.random_theme == "genre":
        return ["Au hasard · un genre"]
    if not band.artists and not band.genres:
        # Plage à mode seul (SPECS.md §7 n°31).
        return ["Tirage libre"]
    return list(band.artists or band.genres)


def semaine_effective(
    grille: EffectiveSchedule,
    shows: Sequence[ShowSettings],
    clock: Clock,
) -> dict[str, object]:
    """La semaine que le Planning affiche, sept journées déjà fusionnées.

    Calculée une fois au démarrage : la grille ne dépend que du jour de la
    semaine. La page reçoit ce qui passera et n'a pas à recoller les périodes
    elle-même, un gabarit ne décide rien (AGENTS.md §2).
    """
    declarees = {e.name: e for e in shows}
    minuit = clock.now().replace(hour=0, minute=0, second=0, microsecond=0)
    jours: dict[str, object] = {}
    for decalage in range(len(DAYS)):
        debut = minuit + timedelta(days=decalage)
        jours[DAYS[debut.weekday()]] = [
            _periode(segment, declarees) for segment in grille.day(debut)
        ]
    return {"days": jours}


def _periode(segment: Segment, shows: Mapping[str, ShowSettings]) -> dict[str, object]:
    """Une période de la grille effective, en données pour la page.

    Les valeurs sont structurées, pas rédigées : c'est la page qui nomme un
    mode, une liste ou un podcast (SPECS.md §4.8).
    """
    content = segment.content
    periode: dict[str, object] = {
        "start": f"{segment.start:%H:%M}",
        "end": None if segment.end is None else f"{segment.end:%H:%M}",
        # Musique qui reprend après une émission de durée inconnue : `start`
        # est alors l'heure de l'émission, pas celle de la reprise.
        "after_show": segment.after_show,
    }
    if isinstance(content, Band):
        # Le mode d'enchaînement brut (SPECS.md §7 n°31), la page le traduit.
        mode = None if content.mode is None else content.mode.value
        return {**periode, "kind": "moment", "genres": _libelle_de_plage(content), "mode": mode}
    if isinstance(content, Programme):
        return {**periode, "kind": "programme", "name": content.name, "playlist": content.playlist}
    declaree = shows[content.name]
    return {
        **periode,
        "kind": "emission",
        "name": content.name,
        "live": declaree.stream is not None,
        "youtube": declaree.youtube is not None,
        "duration_minutes": declaree.duration_minutes,
    }


# Le nom d'un mode d'enchaînement à l'antenne (SPECS.md §7 n°31), identique à
# celui du Planning.
MODES = {
    Mode.DOUBLE_DOSE: "double dose",
    Mode.ERA_FAN: "passionné d'époque",
    Mode.ARTIST_FAN: "passionné d'artiste",
}


def _libelle_du_moment(band: Band, drawn: Constraint | None) -> str:
    """Le libellé de la plage en cours, tel que l'antenne l'annonce.

    Une plage au hasard nomme son tirage avec la mention « (au hasard) »,
    pour qu'on comprenne qu'il change demain. Tant que le tirage n'a pas
    abouti (`drawn` à `None`), la plage tire librement et le libellé le dit.

    Le libellé n'est jamais vide (GOAL-066) : une plage à mode seul (SPECS.md
    §7 n°31) est annoncée comme un tirage libre, et toute plage à mode suffixe
    son enchaînement avec les mots de `MODES`.
    """
    enchainement = f" ({MODES[band.mode]})" if band.mode is not None else ""
    if band.random_theme is None:
        theme = ", ".join(band.artists or band.genres) or "tirage libre"
        return f"Moment · {theme}{enchainement}"
    if drawn is None:
        return f"Moment · au hasard{enchainement}"
    return f"Moment · {drawn.artist or drawn.genre} (au hasard){enchainement}"


def build(config: Config) -> tuple[LiquidsoapPlayout, LiveRadio, EffectiveSchedule]:
    """Câble le tout, et rend ce que Liquidsoap et l'API interrogent.

    Le flux lui-même est encodé et servi par Liquidsoap (ARCHITECTURE.md §4),
    qui demande quoi jouer par `adapters/web/playout_api.py`.

    La grille effective est construite ici, avec les mêmes plages, programmes
    et cases que la radio, pour que le Planning et l'antenne ne divergent pas.
    """
    settings = config.settings
    clock = SystemClock()
    random = RealRandom()

    # Une base inaccessible au démarrage est une erreur de configuration et
    # doit lever (SPECS.md §5). Devenue inaccessible en cours de route, elle
    # rend seulement des poids neutres (`app/learning.py`).
    state = SqliteState(
        Path(settings.state.database),
        clock,
        lock_timeout=timedelta(seconds=settings.state.timeout_seconds),
        vote_half_life=timedelta(days=settings.draw.votes.half_life_days),
    )
    learning = Learning(
        state,
        floor=settings.draw.votes.floor,
        ceiling=settings.draw.votes.ceiling,
        slope=SLOPE_PER_VOTE,
    )

    source = SubsonicSource(
        credentials=config.credentials,
        config=settings.subsonic,
        random=random,
        transport=UrllibTransport(settings.subsonic.timeout_seconds),
        clock=clock,
    )
    theme_au_hasard = RandomTheme(source, random)
    grille = Schedule(
        [
            Band(
                p.start,
                p.end,
                p.genres,
                artists=p.artists,
                random_theme=p.random_theme,
                days=p.days,
                intro=p.intro,
                outro=p.outro,
                mode=Mode(p.mode) if p.mode is not None else None,
            )
            for p in settings.bands
        ],
        clock,
        resolve_random_theme=theme_au_hasard.constraint_for,
    )
    # `0` : jamais périmé, l'ancienne règle n°4.
    peremption = settings.jingles.expiry_seconds
    jingles = Jingles(
        clock,
        encore_name=settings.jingles.encore,
        expiry=timedelta(seconds=peremption) if peremption > 0 else None,
    )
    control = Control(source=source, random=random, jingles=jingles)
    counter = ListenerCount()

    def lister_votes() -> "list[VoteScore]":
        try:
            return [
                VoteScore(
                    scope="piste" if scope is StateScope.TRACK else "artiste",
                    target=label,
                    key=key,
                    stop=scores.stop,
                    encore=scores.encore,
                )
                for scope, key, label, scores in state.all_scores()
            ]
        except StateUnavailable as failure:
            logger.warning("votes illisibles, page vide : %s", failure)
            return []

    # Le saut s'ordonne au diffuseur par la route qu'il enregistre (`radio.liq`,
    # GOAL-017). L'adresse vient de l'environnement, comme tout le câblage
    # entre services (docker-compose.yml).
    liquidsoap = os.environ.get("LIQUIDSOAP_URL", "http://127.0.0.1:8000")

    def _ordonner(chemin: str, consequence: str) -> None:
        import http.client
        import urllib.error
        import urllib.request

        try:
            with urllib.request.urlopen(
                urllib.request.Request(f"{liquidsoap}{chemin}", method="POST"), timeout=3
            ):
                pass
        except (urllib.error.URLError, http.client.HTTPException, OSError) as failure:
            logger.warning("le diffuseur n'a pas pris %s : %s — %s", chemin, failure, consequence)

    def demander_le_saut() -> None:
        _ordonner("/skip", "le morceau finira")

    def vider_l_avance() -> None:
        # Replacer l'avance avant que le diffuseur la vide, pour ne rien
        # perdre (GOAL-034).
        branche[0].stash_for_replay()
        _ordonner("/requeue", "l'encore portera un morceau plus tard")

    programmation = Programming(
        [
            Programme(
                name=p.name,
                playlist=p.playlist,
                days=p.days,
                start=p.start,
                end=p.end,
                intro=p.intro,
                outro=p.outro,
            )
            for p in settings.programmes
        ],
        clock,
    )

    def ce_qui_suit() -> "OnAir | None":
        nature = branche[0].up_next()
        if nature is None:
            return None
        kind, track, label = nature
        return OnAir(
            kind=WebKind(kind.value),
            title=track.title if track is not None else label,
            artist=track.artist if track is not None else None,
        )

    def prochains_titres() -> list[UpcomingEntry]:
        """La liste de `RadioProgramme.upcoming()` pour l'API : heure estimée
        en heure locale, identifiant pour retirer, vide pour l'habillage."""
        return [
            UpcomingEntry(
                kind=WebKind(item.kind.value),
                title=item.track.title if item.track is not None else item.label,
                artist=item.track.artist if item.track is not None else None,
                identifier=item.track.identifier if item.track is not None else "",
                at=None if item.at is None else item.at.astimezone().strftime("%H:%M"),
                expected=item.expected,
            )
            for item in branche[0].upcoming()
        ]

    def retirer_le_titre(identifier: str) -> bool:
        return branche[0].withdraw(identifier)

    def moment_courant() -> str | None:
        """Le libellé du moment en cours, ou `None`. Le programme l'emporte
        sur la plage (SPECS.md §4.13)."""
        programme = programmation.current_programme()
        if programme is not None:
            return f"Programme · {programme.name}"
        band = grille.current_band()
        if band is None:
            return None
        # Le tirage est déjà figé pour l'occurrence : on lit, on ne décide pas.
        tire = theme_au_hasard.constraint_for(band, clock.now()) if band.random_theme else None
        return _libelle_du_moment(band, tire)

    def plage_au_hasard_en_cours() -> Band | None:
        """La plage en cours si son thème ou sa suite (GOAL-059) est tiré au
        sort, sinon `None`. Un programme ouvert l'emporte (SPECS.md §4.13)."""
        if programmation.current_programme() is not None:
            return None
        band = grille.current_band()
        if band is None:
            return None
        au_hasard = band.random_theme is not None or band.mode in (Mode.ERA_FAN, Mode.ARTIST_FAN)
        return band if au_hasard else None

    def moment_au_hasard() -> bool:
        return plage_au_hasard_en_cours() is not None

    def retirer_le_theme() -> Verdict:
        """Retire le thème puis jette l'avance : le morceau en cours finit, et
        le nouveau thème joue dès la jonction suivante (GOAL-057). L'avance
        tirée sous l'ancien thème est rassise (SPECS.md §7 n°33)."""
        band = plage_au_hasard_en_cours()
        if band is None:
            return Verdict(accepted=False, reason=SANS_THEME_A_RETIRER)
        if band.random_theme is not None:
            theme_au_hasard.redraw(band, clock.now())
            vider_l_avance()
            return Verdict(accepted=True)
        # Suite au hasard (GOAL-059) : rompue, et l'avance jetée sans être
        # replacée, car le moment n'a pas changé, seule l'ancre a changé. Sans
        # suite en cours, le prochain tirage en ouvre une de toute façon.
        programme.break_run()
        branche[0].drop_advance()
        return Verdict(accepted=True)

    def journaliser_le_titre(kind: str, title: str, artist: str) -> None:
        try:
            state.record_play(kind, title, artist)
        except StateUnavailable as failure:
            logger.warning("titre non journalisé, la radio continue : %s", failure)

    def lister_l_historique() -> list[PlayedEntry]:
        try:
            return [
                PlayedEntry(
                    on=joue_le.astimezone().strftime("%Y-%m-%d"),
                    at=joue_le.astimezone().strftime("%H:%M"),
                    kind=nature,
                    title=titre,
                    artist=artiste,
                )
                for joue_le, nature, titre, artiste in state.history()
            ]
        except StateUnavailable as failure:
            logger.warning("historique illisible, page vide : %s", failure)
            return []

    def oublier_le_vote(scope: str, target: str) -> bool:
        try:
            return state.delete_vote(
                StateScope.TRACK if scope == "piste" else StateScope.ARTIST, target
            )
        except StateUnavailable as failure:
            logger.warning("vote non effacé : %s", failure)
            return False

    radio = LiveRadio(
        control,
        counter,
        learning.remember,
        lister_votes,
        demander_le_saut,
        vider_l_avance,
        oublier_le_vote,
        moment_courant,
        ce_qui_suit,
        journaliser_le_titre,
        lister_l_historique,
        moment_random=moment_au_hasard,
        redraw=retirer_le_theme,
        upcoming=prochains_titres,
        withdraw=retirer_le_titre,
    )
    # Le programme déclare la nature de ce qu'il choisit ; la chaîne ne la
    # transmet à la façade que quand Liquidsoap commence réellement le morceau.
    branche: list[LiquidsoapPlayout] = []

    cases = [
        Show(
            name=e.name,
            days=e.days,
            hour=e.hour,
            duration=(
                timedelta(minutes=e.duration_minutes) if e.duration_minutes is not None else None
            ),
        )
        for e in settings.shows
    ]
    cases_declarees = ShowSchedule(cases)
    # Faite des mêmes objets que la radio, pour que le Planning et la chaîne
    # ne divergent pas.
    grille_effective = EffectiveSchedule(grille, programmation, cases_declarees)

    programme = RadioProgramme(
        queue=Queue(
            source,
            random,
            Window(settings.draw.artist_gap),
            weigh=learning.weigh,
            runs=Runs(random),
            lookahead=settings.draw.lookahead,
        ),
        source=source,
        grille=grille,
        jingles=jingles,
        clock=clock,
        random=random,
        jingle_folder=Path(settings.jingles.folder),
        on_kind=lambda kind, track, label: branche[0].on_kind(kind, track, label),
        programming=programmation,
        programme_window=Window(settings.draw.artist_gap),
        shows=Shows(
            cases_declarees,
            PodcastFeed(
                UrllibReader(lock_timeout=timedelta(seconds=settings.podcast.timeout_seconds))
            ),
            state,
            clock,
            {e.name: e.feed for e in settings.shows if e.feed is not None},
            streams={e.name: e.stream for e in settings.shows if e.stream is not None},
            youtube_channels={e.name: e.youtube for e in settings.shows if e.youtube is not None},
            youtube=YoutubeChannel(timedelta(seconds=settings.youtube.timeout_seconds)),
            youtube_cache=Path(settings.state.database).parent / "cache",
        ),
        effective=grille_effective,
        control=control,
        now_playing=lambda: radio.playing_track(),
    )

    reprise = settings.playout.resume_fresh_seconds
    minutes = settings.draw.max_track_minutes
    playout = LiquidsoapPlayout(
        programme,
        radio,
        counter,
        ephemeral_dir=Path(settings.state.database).parent / "cache",
        clock=clock,
        resume_fresh_after=timedelta(seconds=reprise) if reprise > 0 else None,
        max_duration=timedelta(minutes=minutes) if minutes > 0 else None,
        # La purge ne replace rien, contrairement à `vider_l_avance` : l'avance
        # rassise ne doit pas revenir (SPECS.md §7 n°30).
        order_requeue=lambda: _ordonner("/requeue", "l'avance rassise partira quand même"),
        order_skip=lambda: _ordonner("/skip", "le reliquat du morceau interrompu passera"),
    )
    branche.append(playout)
    return playout, radio, grille_effective


def main(argv: list[str] | None = None) -> int:
    """Démarre, sert, et s'arrête proprement sur SIGTERM ou SIGINT.

    Rend un code de sortie plutôt que d'appeler `sys.exit`, pour rester
    testable.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    options = _arguments(argv)
    logger.info("%s %s", NAME, version())

    config = load(options.config, options.env)
    playout, radio, grille_effective = build(config)
    web = config.settings.web
    planning = semaine_effective(grille_effective, config.settings.shows, SystemClock())
    app = create_app(
        radio,
        refresh=timedelta(seconds=web.refresh_seconds),
        playout=playout,
        planning=planning,
        stream_url=web.stream_url,
    )

    shutdown = threading.Event()

    def demander_larret(*_: object) -> None:
        shutdown.set()

    signal.signal(signal.SIGTERM, demander_larret)
    signal.signal(signal.SIGINT, demander_larret)

    web_thread = threading.Thread(
        target=lambda: app.run(host=web.address, port=web.port, threaded=True),
        daemon=True,
    )
    web_thread.start()
    logger.info("interface, API et routes de Liquidsoap sur le port %d", web.port)

    shutdown.wait()
    logger.info("arrêt demandé")
    return 0


if __name__ == "__main__":
    sys.exit(main())
