"""Les émissions : ce qui est dû, ce qui est sauté, et ce qui ne se rejoue pas."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from webradio.adapters.podcast.feed import Episode as EpisodeDuFlux
from webradio.adapters.podcast.feed import PodcastUnavailable
from webradio.adapters.state.database import SqliteState, StateUnavailable
from webradio.adapters.youtube.channel import YoutubeUnavailable
from webradio.app.show_scheduler import PodcastSlot, Shows
from webradio.core.clock import FrozenClock
from webradio.core.rng import ScriptedRandom
from webradio.core.shows import Show, ShowSchedule

VENDREDI_20H = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)  # 2026-08-28 est un vendredi
SHOW = Show(name="A la French", days=("friday",), hour=time(20, 0))


class FakeFeed:
    """Un flux d'essai : rend les épisodes donnés, ou lève `PodcastUnavailable`."""

    def __init__(self, episodes: list[EpisodeDuFlux], *, injoignable: bool = False) -> None:
        self._episodes = episodes
        self.injoignable = injoignable
        self.lectures = 0

    def episodes(self, url: str) -> list[EpisodeDuFlux]:
        self.lectures += 1
        if self.injoignable:
            message = f"flux d'essai injoignable : {url}"
            raise PodcastUnavailable(message)
        return list(self._episodes)


def _episode(guid: str, days: int = 0, minutes: int = 90) -> EpisodeDuFlux:
    return EpisodeDuFlux(
        identifier=guid,
        title=f"épisode {guid}",
        published_at=VENDREDI_20H - timedelta(days=days),
        audio=f"https://exemple.test/{guid}.mp3",
        duration=timedelta(minutes=minutes),
    )


def _emissions(
    tmp_path: Path,
    feed: FakeFeed,
    clock: FrozenClock,
) -> tuple[Shows, SqliteState]:
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return (
        Shows(
            ShowSchedule([SHOW]),
            feed,  # type: ignore[arg-type]
            state,
            clock,
            {"A la French": ("https://exemple.test/flux.xml",)},
            ScriptedRandom([0] * 50),
        ),
        state,
    )


def test_une_emission_due_rend_l_url_de_son_episode(tmp_path: Path) -> None:
    feed = FakeFeed([_episode("ep1")])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = shows.due()
    assert due is not None
    assert due[0].name == "A la French"
    assert due[1] == "https://exemple.test/ep1.mp3"


def test_hors_de_sa_case_aucune_emission_n_est_due(tmp_path: Path) -> None:
    feed = FakeFeed([_episode("ep1")])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H - timedelta(days=1)))
    assert shows.due() is None


def test_un_episode_deja_diffuse_fait_sauter_la_case(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une émission sans épisode neuf n'a pas lieu (SPECS.md §4.11) : on ne
    redescend pas à l'avant-dernier épisode."""
    feed = FakeFeed([_episode("ep1")])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = shows.due()
    assert due is not None
    shows.started(due[1])
    with caplog.at_level(logging.INFO):
        assert shows.due() is None
    assert "rien de neuf" in caplog.text


def test_un_episode_neuf_rouvre_la_case(tmp_path: Path) -> None:
    feed = FakeFeed([_episode("ep1")])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    premier = shows.due()
    assert premier is not None
    shows.started(premier[1])
    feed._episodes = [_episode("ep2"), _episode("ep1", days=7)]
    due = shows.due()
    assert due is not None
    assert due[1].endswith("ep2.mp3")


def test_un_episode_jete_avant_l_antenne_reste_a_diffuser(tmp_path: Path) -> None:
    """L'entrée rendue n'est que l'avance du diffuseur : une purge peut la jeter
    sans l'avoir jouée. Inscrite à la demande, l'émission hebdomadaire était
    perdue jusqu'à l'épisode suivant (SPECS.md §4.11.1)."""
    feed = FakeFeed([_episode("ep1")])
    shows, state = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = shows.due()
    assert due is not None

    shows.dropped()

    encore = shows.due()
    assert encore is not None and encore[1] == due[1]
    assert state.last_airing("A la French") is None, "rien n'a passé, rien n'est retenu"


def test_un_episode_demande_n_est_pas_rendu_deux_fois_avant_de_commencer(
    tmp_path: Path,
) -> None:
    """Le diffuseur peut redemander avant de jouer ce qu'il a demandé
    (docs/liquidsoap.md §3) : le rendre deux fois le ferait passer deux fois."""
    feed = FakeFeed([_episode("ep1")])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    assert shows.due() is not None
    assert shows.due() is None


def test_un_episode_commence_est_retenu_comme_diffuse(tmp_path: Path) -> None:
    feed = FakeFeed([_episode("ep1")])
    shows, state = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = shows.due()
    assert due is not None

    shows.started(due[1])

    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "ep1"
    assert shows.due() is None, "elle est passée, la case est sautée"


def test_une_autre_entree_commencee_ne_retient_pas_l_episode(tmp_path: Path) -> None:
    """`started` ne vaut que pour l'entrée attendue : c'est l'appelant qui sait
    qu'une émission a été jetée."""
    feed = FakeFeed([_episode("ep1")])
    shows, state = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    assert shows.due() is not None

    shows.started("fake://1")

    assert state.last_airing("A la French") is None


class MemoireQuiNeRetientRien:
    """Une base qui se lit mais refuse d'écrire, comme un verrou pris par le
    serveur web au moment de l'inscription."""

    def last_airing(self, show: str) -> None:  # noqa: ARG002
        return None

    def record_airing(self, show: str, episode: str) -> None:
        message = f"verrou non obtenu pour « {show} », épisode {episode}"
        raise StateUnavailable(message)


def test_une_diffusion_non_retenue_se_journalise_et_se_rejouera(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sans mémoire, l'épisode repassera : c'est moins grave que de le perdre."""
    shows = Shows(
        ShowSchedule([SHOW]),
        FakeFeed([_episode("ep1")]),  # type: ignore[arg-type]
        MemoireQuiNeRetientRien(),  # type: ignore[arg-type]
        FrozenClock(VENDREDI_20H),
        {"A la French": ("https://exemple.test/flux.xml",)},
        ScriptedRandom([0] * 50),
    )
    due = shows.due()
    assert due is not None

    with caplog.at_level(logging.WARNING):
        shows.started(due[1])

    assert "se rejouera" in caplog.text
    assert shows.due() is not None


def test_un_flux_injoignable_ne_fait_pas_taire_la_radio(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une émission perdue n'est pas une panne : la musique continue."""
    feed = FakeFeed([], injoignable=True)
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))
    with caplog.at_level(logging.WARNING):
        assert shows.due() is None
    assert "injoignable" in caplog.text


def test_un_flux_vide_ne_donne_aucune_emission(tmp_path: Path) -> None:
    shows, _ = _emissions(tmp_path, FakeFeed([]), FrozenClock(VENDREDI_20H))
    assert shows.due() is None


def test_le_rattrapage_est_borne_par_la_duree_de_l_episode(tmp_path: Path) -> None:
    """Se brancher dans la fenêtre rattrape ; au-delà, l'émission est perdue
    (SPECS.md §7 n°13)."""
    feed = FakeFeed([_episode("ep1", minutes=60)])
    dans_la_fenetre = FrozenClock(VENDREDI_20H + timedelta(minutes=40))
    shows, _ = _emissions(tmp_path, feed, dans_la_fenetre)
    assert shows.due() is not None

    flux_bis = FakeFeed([_episode("ep1", minutes=60)])
    hors_fenetre = FrozenClock(VENDREDI_20H + timedelta(minutes=70))
    emissions_bis, _ = _emissions(tmp_path / "bis", flux_bis, hors_fenetre)
    (tmp_path / "bis").mkdir(exist_ok=True)
    assert emissions_bis.due() is None


def test_le_flux_est_lu_avant_de_savoir_s_il_servira(tmp_path: Path) -> None:
    """La durée borne le rattrapage et n'est connue qu'après lecture : le flux
    est lu même si l'émission est finalement perdue (ARCHITECTURE.md §5.2)."""
    feed = FakeFeed([_episode("ep1", minutes=1)])
    tardif = FrozenClock(VENDREDI_20H + timedelta(hours=3))
    shows, _ = _emissions(tmp_path, feed, tardif)
    assert shows.due() is None
    assert feed.lectures == 1, "le flux aurait dû être lu malgré tout"


# ── Les directs (GOAL-015) ──────────────────────────────────────────────────

FLASH = Show(name="Flash", days=("all",), hour=time(20), duration=timedelta(minutes=9))
FRANCEINFO = "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"


def _direct(tmp_path: Path, clock: FrozenClock, feed: FakeFeed | None = None) -> Shows:
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    # La case porte AUSSI un flux de podcast, joignable et non vide : un direct
    # qui irait le lire rendrait l'épisode au lieu de l'antenne, et le compteur
    # de lectures du Fake le dirait.
    return Shows(
        ShowSchedule([FLASH]),
        feed if feed is not None else FakeFeed([_episode("ep1")]),  # type: ignore[arg-type]
        state,
        clock,
        {"Flash": ("https://exemple.test/flux.xml",)},
        ScriptedRandom([0] * 50),
        streams={"Flash": FRANCEINFO},
    )


def test_un_direct_du_est_une_instruction_avec_son_heure_de_fin(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H + timedelta(minutes=2))
    due = _direct(tmp_path, clock).due()
    assert due is not None
    show, entry, _titre, _longueur, _passable = due
    assert show is FLASH
    fin = int((VENDREDI_20H + timedelta(minutes=9)).timestamp())
    assert entry == f"live:{fin}:Flash:{FRANCEINFO}"


def test_le_libelle_d_un_direct_perd_ses_deux_points(tmp_path: Path) -> None:
    """Le diffuseur découpe l'instruction sur les deux-points et recompose
    l'URL depuis le dernier champ (`radio.liq`) : un nom d'émission ponctué
    décalerait l'adresse. L'API garantit un libellé sans deux-points
    (SPECS.md §4.9)."""
    clock = FrozenClock(VENDREDI_20H)
    ponctue = Show(name="Flash : info", days=("all",), hour=time(20), duration=timedelta(minutes=9))
    shows = Shows(
        ShowSchedule([ponctue]),
        FakeFeed([]),  # type: ignore[arg-type]
        SqliteState(
            tmp_path / "etat.sqlite3",
            clock,
            lock_timeout=timedelta(seconds=5),
            vote_half_life=timedelta(days=90),
        ),
        clock,
        {},
        ScriptedRandom([0] * 50),
        streams={"Flash : info": FRANCEINFO},
    )

    due = shows.due()

    assert due is not None
    fin = int((VENDREDI_20H + timedelta(minutes=9)).timestamp())
    assert due[1] == f"live:{fin}:Flash info:{FRANCEINFO}"


def test_un_direct_n_est_rendu_qu_une_fois_par_case(tmp_path: Path) -> None:
    """Sinon il redémarrerait à chaque jonction jusqu'à la fin de la case."""
    clock = FrozenClock(VENDREDI_20H)
    shows = _direct(tmp_path, clock)
    due = shows.due()
    assert due is not None
    shows.started(due[1])
    clock.advance(timedelta(minutes=3))
    assert shows.due() is None


def test_un_direct_demande_ne_se_redemande_pas_avant_d_avoir_commence(tmp_path: Path) -> None:
    """Le script redemande une entrée aussitôt après une instruction de direct
    (`radio.liq`) : sans la garde, le direct serait relancé dans la foulée."""
    clock = FrozenClock(VENDREDI_20H)
    shows = _direct(tmp_path, clock)
    assert shows.due() is not None
    assert shows.due() is None


def test_un_direct_jete_avant_l_antenne_peut_reprendre_sa_case(tmp_path: Path) -> None:
    """La case n'est retenue qu'une fois le direct commencé : jeté avant, il
    n'a pas eu lieu, et la case tient jusqu'à sa fin (SPECS.md §7 n°22)."""
    clock = FrozenClock(VENDREDI_20H)
    shows = _direct(tmp_path, clock)
    assert shows.due() is not None

    shows.dropped()
    clock.advance(timedelta(minutes=3))

    due = shows.due()
    assert due is not None
    fin = int((VENDREDI_20H + timedelta(minutes=9)).timestamp())
    assert due[1] == f"live:{fin}:Flash:{FRANCEINFO}", "la fin reste celle de la case"


def test_une_case_de_direct_finie_est_sautee_sans_rattrapage(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H + timedelta(minutes=9))
    assert _direct(tmp_path, clock).due() is None


def test_un_direct_ne_lit_aucun_flux_et_ne_laisse_aucune_trace(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H)
    feed = FakeFeed([_episode("ep1")])
    shows = _direct(tmp_path, clock, feed)

    due = shows.due()

    assert due is not None
    fin = int((VENDREDI_20H + timedelta(minutes=9)).timestamp())
    assert due[1] == f"live:{fin}:Flash:{FRANCEINFO}", "l'antenne, pas l'épisode du flux"
    assert feed.lectures == 0
    # La base ne doit connaître aucune diffusion : un direct ne se mémorise pas.
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    assert state.last_airing("Flash") is None


# ── Une chaîne YouTube comme émission (GOAL-025) ────────────────────────────

HARDISK = Show(name="Hardisk", days=("all",), hour=time(20))


class FakeYoutube:
    """Fidèle au vrai : un cache qu'une lecture réussie remplit, et qu'une
    panne laisse vide."""

    def __init__(self, episodes: list[EpisodeDuFlux], *, injoignable: bool = False) -> None:
        self._episodes = episodes
        self._injoignable = injoignable
        self.telecharges: list[tuple[str, str]] = []
        self._garde: list[EpisodeDuFlux] | None = None
        self.lues = 0

    def cached(self, _url: str, *, stale_ok: bool = False) -> list[EpisodeDuFlux] | None:
        # Le faux cache ne périme pas : ce que `stale_ok` change n'est pas
        # observable ici, et le vrai a ses propres tests.
        del stale_ok
        return None if self._garde is None else list(self._garde)

    def episodes(self, _url: str) -> list[EpisodeDuFlux]:
        self.lues += 1
        if self._injoignable:
            message = "chaîne d'essai injoignable"
            raise YoutubeUnavailable(message)
        self._garde = list(self._episodes)
        return list(self._episodes)

    def download(self, video_url: str, destination: str) -> None:
        """Le vrai téléchargement est en tâche de fond ; le test écrit lui-même
        le fichier pour simuler la fin."""
        self.telecharges.append((video_url, destination))


def _youtube_show(
    tmp_path: Path, yt: FakeYoutube, clock: FrozenClock, *, cache: Path | None = None
) -> Shows:
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return Shows(
        ShowSchedule([HARDISK]),
        FakeFeed([], injoignable=True),  # type: ignore[arg-type]
        state,
        clock,
        {},
        ScriptedRandom([0] * 50),
        youtube_channels={"Hardisk": "https://www.youtube.com/@hardisk"},
        youtube=yt,  # type: ignore[arg-type]
        youtube_cache=cache if cache is not None else tmp_path / "cache",
    )


def _video(guid: str, minutes: int = 29) -> EpisodeDuFlux:
    return EpisodeDuFlux(
        identifier=guid,
        title=f"vidéo {guid}",
        published_at=VENDREDI_20H - timedelta(days=1),
        audio=f"https://googlevideo.test/{guid}",
        duration=timedelta(minutes=minutes),
    )


def _attendre_le_telechargement(yt: FakeYoutube) -> None:
    import time as _time

    for _ in range(50):
        if yt.telecharges:
            return
        _time.sleep(0.01)
    message = "le téléchargement de fond n'a jamais démarré"
    raise AssertionError(message)


def test_sans_fichier_local_la_musique_continue_et_le_telechargement_part(
    tmp_path: Path,
) -> None:
    """Jamais l'URL directe, qui donne trente secondes de blanc (GOAL-028,
    docs/youtube.md §5)."""
    clock = FrozenClock(VENDREDI_20H)
    yt = FakeYoutube([_video("v1")])
    shows = _youtube_show(tmp_path, yt, clock)

    assert shows.due() is None  # la musique continue
    _attendre_le_telechargement(yt)
    # Un nom stable par émission : le téléchargement suivant écrase le
    # précédent, rien ne s'accumule.
    assert yt.telecharges == [
        ("https://www.youtube.com/watch?v=v1", str(tmp_path / "cache" / "hardisk.m4a"))
    ]


def test_le_fichier_pret_part_a_la_jonction_et_une_seule_fois(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H)
    yt = FakeYoutube([_video("v1")])
    shows = _youtube_show(tmp_path, yt, clock)
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "hardisk.m4a").write_bytes(b"audio")
    (tmp_path / "cache" / "hardisk.id").write_text("v1")

    due = shows.due()

    assert due is not None
    assert due[0].name == "Hardisk"
    assert due[1] == str(tmp_path / "cache" / "hardisk.m4a")
    shows.started(due[1])
    assert shows.due() is None  # déjà diffusée : la case est sautée


def test_un_reste_d_une_autre_video_n_est_jamais_servi(tmp_path: Path) -> None:
    """Le nom est stable : sans témoin `.id` assorti, le fichier est un reste.
    On retélécharge par-dessus, on ne le diffuse pas."""
    clock = FrozenClock(VENDREDI_20H)
    yt = FakeYoutube([_video("v2")])
    shows = _youtube_show(tmp_path, yt, clock)
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "hardisk.m4a").write_bytes(b"vieille video")
    (tmp_path / "cache" / "hardisk.id").write_text("v1")

    assert shows.due() is None  # jamais la vieille
    _attendre_le_telechargement(yt)
    assert yt.telecharges[0][0].endswith("v=v2")


def test_une_chaine_injoignable_laisse_la_musique(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H)
    assert _youtube_show(tmp_path, FakeYoutube([], injoignable=True), clock).due() is None


# ── Une plage podcasts : plusieurs flux, un tirage par jonction (n°35) ───────


class FeedParUrl:
    """Un flux d'essai qui rend un catalogue différent selon l'adresse."""

    def __init__(self, par_url: dict[str, list[EpisodeDuFlux]]) -> None:
        self._par_url = par_url
        self.lues: list[str] = []

    def episodes(self, url: str) -> list[EpisodeDuFlux]:
        self.lues.append(url)
        if url not in self._par_url:
            message = f"flux d'essai injoignable : {url}"
            raise PodcastUnavailable(message)
        return list(self._par_url[url])

    def cached(self, url: str, *, stale_ok: bool = False) -> list[EpisodeDuFlux] | None:
        """Le cache est chaud : une plage relit ses flux à chaque jonction, et
        `podcast.cache_seconds` vaut 900 s par défaut."""
        del stale_ok
        return list(self._par_url.get(url, []))


LEGEND_URL = "https://exemple.test/legend.xml"
KONBINI_URL = "https://exemple.test/konbini.xml"
PLAGE = Show(name="Soirée podcasts", days=("friday",), hour=time(20), end=time(23))


def _plage(
    tmp_path: Path, feed: FeedParUrl, clock: FrozenClock, indices: list[int] | None = None
) -> tuple[Shows, SqliteState]:
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return (
        Shows(
            ShowSchedule([PLAGE]),
            feed,  # type: ignore[arg-type]
            state,
            clock,
            {"Soirée podcasts": (LEGEND_URL, KONBINI_URL)},
            ScriptedRandom(indices if indices is not None else [0] * 50),
        ),
        state,
    )


def test_une_plage_lit_tous_ses_flux_et_tire_l_un_d_eux(tmp_path: Path) -> None:
    """Chaque flux a sa propre notion de « plus récent non diffusé » : il faut
    donc les lire tous avant de tirer (SPECS.md §7 n°35)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = emissions.due()

    assert due is not None
    assert sorted(feed.lues) == sorted([LEGEND_URL, KONBINI_URL])
    assert due[1] in ("https://exemple.test/l1.mp3", "https://exemple.test/k1.mp3")


def test_un_flux_injoignable_ne_prive_pas_la_plage_des_autres(tmp_path: Path) -> None:
    """Une émission à flux unique n'a pas lieu si son flux est muet. Une plage,
    si : elle tire parmi ceux qui ont répondu."""
    feed = FeedParUrl({KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = emissions.due()

    assert due is not None
    assert due[1] == "https://exemple.test/k1.mp3"


def test_la_memoire_d_une_plage_est_tenue_par_flux(tmp_path: Path) -> None:
    """Ce qu'une plage a déjà passé d'un flux ne dit rien de l'autre : sans une
    mémoire par flux, un seul épisode diffusé fermerait toute la case."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    horloge = FrozenClock(VENDREDI_20H)
    emissions, _ = _plage(tmp_path, feed, horloge, indices=[0, 0])

    premier = emissions.due()
    assert premier is not None
    emissions.started(premier[1])
    second = emissions.due()
    assert second is not None
    emissions.started(second[1])

    assert premier[1] != second[1], "le flux épuisé sort de la pioche, l'autre reste"
    assert emissions.due() is None, "les deux épuisés, la case est sautée"


def test_une_emission_a_flux_unique_garde_sa_cle_de_memoire_historique(tmp_path: Path) -> None:
    """Changer la clé ferait rejouer une fois le dernier épisode de chaque
    émission au déploiement. Le nom seul reste la clé tant qu'il n'y a qu'un
    flux (ARCHITECTURE.md §5)."""
    feed = FakeFeed([_episode("e1")])
    emissions, state = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = emissions.due()
    assert due is not None
    emissions.started(due[1])

    passe = state.last_airing("A la French")
    assert passe is not None and passe.episode == "e1"


def test_une_plage_fermee_ne_fait_lire_aucun_flux(tmp_path: Path) -> None:
    """Une plage déclare sa fin : elle se sait fermée sans qu'on lise rien.
    Sans ce contrôle, ses flux étaient lus jusqu'à la veille de l'occurrence
    suivante — deux jours par semaine pour trois heures d'antenne, et autant
    d'occasions qu'un hébergeur muet fasse expirer la requête (GOAL-080)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    lendemain = VENDREDI_20H + timedelta(days=1)
    emissions, _ = _plage(tmp_path, feed, FrozenClock(lendemain))

    assert emissions.due() is None
    assert feed.lues == [], "la case est fermée, rien n'avait à être lu"


def test_une_plage_ouverte_lit_bien_ses_flux(tmp_path: Path) -> None:
    """Le pendant du test précédent : le contrôle ne doit pas fermer la case
    quand elle est ouverte."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H + timedelta(hours=2)))

    assert emissions.due() is not None
    assert sorted(feed.lues) == sorted([LEGEND_URL, KONBINI_URL])


def test_tous_les_flux_d_une_plage_injoignables_sautent_la_case(tmp_path: Path) -> None:
    """Aucun n'a répondu : la case est sautée et la musique continue, comme
    une émission dont le flux est muet (SPECS.md §4.11)."""
    feed = FeedParUrl({})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    assert emissions.due() is None
    assert sorted(feed.lues) == sorted([LEGEND_URL, KONBINI_URL]), "les deux ont été tentés"


class MemoireMuette:
    """Une base qui refuse de répondre, comme un verrou jamais obtenu."""

    def last_airing(self, show: str) -> None:
        message = f"verrou non obtenu pour « {show} »"
        raise StateUnavailable(message)

    def record_airing(self, show: str, episode: str) -> None:
        message = f"verrou non obtenu pour « {show} », épisode {episode}"
        raise StateUnavailable(message)


def test_une_plage_sans_memoire_saute_sa_case() -> None:
    """Sans mémoire on rediffuserait le même épisode en boucle : sauter est
    moins gênant (SPECS.md §4.11). La règle vaut pour une plage comme pour une
    émission."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions = Shows(
        ShowSchedule([PLAGE]),
        feed,  # type: ignore[arg-type]
        MemoireMuette(),  # type: ignore[arg-type]
        FrozenClock(VENDREDI_20H),
        {"Soirée podcasts": (LEGEND_URL, KONBINI_URL)},
        ScriptedRandom([0] * 50),
    )

    assert emissions.due() is None


# ── Le diffuseur n'attend jamais un hébergeur (GOAL-080-T05) ─────────────────


class FeedLent:
    """Un flux d'essai fidèle au vrai : un cache qui **expire**, et une panne
    qui n'y entre pas.

    Un faux cache éternel aurait caché le défaut que ce fichier teste plus bas :
    la garde expire au milieu d'un épisode long."""

    def __init__(
        self,
        par_url: dict[str, list[EpisodeDuFlux]],
        clock: FrozenClock | None = None,
        garde: timedelta | None = None,
    ) -> None:
        self._par_url = par_url
        self._horloge = clock
        self._garde_duree = garde
        self._garde: dict[str, tuple[datetime, list[EpisodeDuFlux]]] = {}
        self.lues: list[str] = []

    def cached(self, url: str, *, stale_ok: bool = False) -> list[EpisodeDuFlux] | None:
        connu = self._garde.get(url)
        if connu is None:
            return None
        expire = (
            self._horloge is not None
            and self._garde_duree is not None
            and self._horloge.now() - connu[0] >= self._garde_duree
        )
        if expire and not stale_ok:
            return None
        return list(connu[1])

    def episodes(self, url: str) -> list[EpisodeDuFlux]:
        self.lues.append(url)
        if url not in self._par_url:
            message = f"flux d'essai injoignable : {url}"
            raise PodcastUnavailable(message)
        quand = self._horloge.now() if self._horloge is not None else VENDREDI_20H
        self._garde[url] = (quand, list(self._par_url[url]))
        return list(self._par_url[url])


def _plage_en_fond(
    tmp_path: Path, feed: FeedLent, clock: FrozenClock, reportees: list[Callable[[], None]]
) -> Shows:
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        clock,
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    return Shows(
        ShowSchedule([PLAGE]),
        feed,  # type: ignore[arg-type]
        state,
        clock,
        {"Soirée podcasts": (LEGEND_URL, KONBINI_URL)},
        ScriptedRandom([0] * 50),
        in_background=reportees.append,
        preload=timedelta(minutes=15),
    )


def test_la_premiere_jonction_ne_lit_aucun_flux_et_rend_la_main(tmp_path: Path) -> None:
    """Le diffuseur abandonne une requête au bout de dix secondes et coupe au
    deuxième échec : trois flux lus l'un après l'autre le dépassent. La lecture
    part en tâche de fond, et la case attend la jonction suivante plutôt que
    l'hébergeur (GOAL-080)."""
    feed = FeedLent({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    reportees: list[Callable[[], None]] = []
    emissions = _plage_en_fond(tmp_path, feed, FrozenClock(VENDREDI_20H), reportees)

    assert emissions.due() is None, "rien n'est encore lu, la musique continue"
    assert feed.lues == [], "aucun aller au réseau pendant la requête"
    assert len(reportees) == 2, "les deux flux sont partis en tâche de fond"


def test_la_jonction_suivante_sert_ce_que_le_fond_a_lu(tmp_path: Path) -> None:
    feed = FeedLent({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    reportees: list[Callable[[], None]] = []
    emissions = _plage_en_fond(tmp_path, feed, FrozenClock(VENDREDI_20H), reportees)
    emissions.due()

    for lire in reportees:
        lire()

    assert emissions.due() is not None


def test_un_flux_deja_lance_n_est_pas_relance_a_chaque_jonction(tmp_path: Path) -> None:
    """Les jonctions se suivent plus vite qu'un hébergeur lent ne répond : sans
    ce garde-fou, chacune empilerait une lecture de plus."""
    feed = FeedLent({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    reportees: list[Callable[[], None]] = []
    emissions = _plage_en_fond(tmp_path, feed, FrozenClock(VENDREDI_20H), reportees)

    emissions.due()
    emissions.due()
    emissions.due()

    assert len(reportees) == 2, "une lecture en cours par flux, pas une par jonction"


def test_les_flux_se_lisent_avant_l_ouverture_de_la_case(tmp_path: Path) -> None:
    """Sans cela la plage commencerait à la jonction d'après son heure, soit
    plusieurs minutes en retard."""
    feed = FeedLent({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    reportees: list[Callable[[], None]] = []
    dix_minutes_avant = VENDREDI_20H - timedelta(minutes=10)
    emissions = _plage_en_fond(tmp_path, feed, FrozenClock(dix_minutes_avant), reportees)

    assert emissions.due() is None, "la case n'est pas encore ouverte"
    assert len(reportees) == 2, "ses flux sont déjà partis en lecture"


def test_une_plage_n_intercale_pas_de_musique_entre_deux_episodes(tmp_path: Path) -> None:
    """La garde du cache expire au milieu d'un épisode long — soixante-dix
    minutes contre quinze de garde. Sans servir le catalogue périmé pendant la
    relecture, la jonction suivante ne trouvait rien et rendait la main à la
    musique : un morceau s'intercalait entre chaque épisode (GOAL-081)."""
    horloge = FrozenClock(VENDREDI_20H)
    feed = FeedLent(
        {LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]},
        horloge,
        timedelta(minutes=15),
    )
    reportees: list[Callable[[], None]] = []
    emissions = _plage_en_fond(tmp_path, feed, horloge, reportees)
    emissions.due()
    for lire in list(reportees):
        lire()
    reportees.clear()

    premier = emissions.due()
    assert premier is not None, "le premier épisode part"
    emissions.started(premier[1])
    horloge.advance(timedelta(minutes=70))

    assert emissions.due() is not None, "le second aussi, la garde a pourtant expiré"


def test_le_catalogue_perime_est_relu_en_fond_pendant_qu_il_sert(tmp_path: Path) -> None:
    """Servir du périmé n'est acceptable que si la relecture part aussitôt :
    sinon un épisode publié n'apparaîtrait jamais."""
    horloge = FrozenClock(VENDREDI_20H)
    feed = FeedLent({LEGEND_URL: [_episode("l1")]}, horloge, timedelta(minutes=15))
    reportees: list[Callable[[], None]] = []
    emissions = _plage_en_fond(tmp_path, feed, horloge, reportees)
    emissions.due()
    for lire in list(reportees):
        lire()
    reportees.clear()
    horloge.advance(timedelta(minutes=20))

    emissions.due()

    assert reportees, "la relecture est partie en même temps que le périmé était servi"


def test_une_chaine_youtube_se_lit_aussi_hors_de_la_requete(tmp_path: Path) -> None:
    """Lire une chaîne enchaîne un flux Atom et une résolution `yt-dlp`,
    chacune bornée par `youtube.timeout_seconds` : bien au-delà de ce que le
    diffuseur attend. Même traitement que les podcasts (GOAL-081-T04)."""
    yt = FakeYoutube([_episode("v1")])
    reportees: list[Callable[[], None]] = []
    state = SqliteState(
        tmp_path / "etat.sqlite3",
        FrozenClock(VENDREDI_20H),
        lock_timeout=timedelta(seconds=5),
        vote_half_life=timedelta(days=90),
    )
    emissions = Shows(
        ShowSchedule([HARDISK]),
        FakeFeed([], injoignable=True),  # type: ignore[arg-type]
        state,
        FrozenClock(VENDREDI_20H),
        {},
        ScriptedRandom([0] * 50),
        youtube_channels={"Hardisk": "https://www.youtube.com/@hardisk"},
        youtube=yt,  # type: ignore[arg-type]
        youtube_cache=tmp_path / "cache",
        in_background=reportees.append,
        preload=timedelta(minutes=15),
    )

    assert emissions.due() is None, "rien n'est lu, la musique continue"
    assert yt.lues == 0, "aucun appel à yt-dlp pendant la requête"
    assert len(reportees) == 1, "la lecture est reportée, pas abandonnée"

    for lire in reportees:
        lire()

    assert yt.lues == 1


def test_une_emission_due_rend_la_duree_de_son_episode(tmp_path: Path) -> None:
    feed = FakeFeed([_episode("ep1", minutes=42)])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = shows.due()

    assert due is not None
    assert due[3].duration == timedelta(minutes=42)
    assert due[3].until is None


def test_un_episode_sans_duree_dans_le_flux_ne_rend_aucune_longueur(tmp_path: Path) -> None:
    """Rien n'est inventé quand le flux ne donne pas `itunes:duration`
    (docs/podcast.md §1). Seule une plage y arrive : une émission ordinaire
    sans durée n'ouvre pas sa case."""
    sans_duree = EpisodeDuFlux(
        identifier="l1",
        title="épisode l1",
        published_at=VENDREDI_20H,
        audio="https://exemple.test/l1.mp3",
        duration=None,
    )
    feed = FeedParUrl({LEGEND_URL: [sans_duree]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = emissions.due()

    assert due is not None
    assert due[3].duration is None
    assert due[3].until is None


def test_un_direct_rend_la_fin_de_sa_case_comme_longueur(tmp_path: Path) -> None:
    clock = FrozenClock(VENDREDI_20H + timedelta(minutes=2))

    due = _direct(tmp_path, clock).due()

    assert due is not None
    assert due[3].until == VENDREDI_20H + timedelta(minutes=9)
    assert due[3].duration is None


def test_la_cle_de_l_avance_ne_bouge_pas_pendant_un_episode(tmp_path: Path) -> None:
    """La clé qui date l'avance ne change qu'à l'ouverture ou à la fermeture
    d'une case, et au passage de demandé à commencé (décision n°43). Si elle
    bougeait au fil du temps, le battement de quinze secondes ordonnerait un
    `/requeue` de plus à chaque passage."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    horloge = FrozenClock(VENDREDI_20H)
    emissions, _ = _plage(tmp_path, feed, horloge)

    assert emissions.open_band_slot() == PodcastSlot(PLAGE.name, VENDREDI_20H, awaited=False)
    due = emissions.due()
    assert due is not None
    demandee = emissions.open_band_slot()
    assert demandee is not None and demandee.awaited, "il est demandé, il n'a pas commencé"

    emissions.started(due[1])
    en_cours = emissions.open_band_slot()
    assert en_cours == PodcastSlot(PLAGE.name, VENDREDI_20H, awaited=False)
    horloge.advance(timedelta(minutes=15))
    assert emissions.open_band_slot() == en_cours, "quinze minutes plus tard, la même case"

    horloge.advance(timedelta(hours=3))
    assert emissions.open_band_slot() is None, "la plage est fermée"


def test_une_emission_ordinaire_n_entre_pas_dans_la_cle_de_l_avance(tmp_path: Path) -> None:
    """Seule une plage y entre : la case d'un podcast seul ou d'un direct est à
    elle, et l'épisode entamé avant sa fin finit (SPECS.md §7 n°5)."""
    feed = FakeFeed([_episode("ep1")])
    emissions, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))

    assert emissions.due() is not None
    assert emissions.open_band_slot() is None


# ── Un épisode de plage se passe (GOAL-086-T05) ─────────────────────────────


def test_l_episode_d_une_plage_se_dit_passable(tmp_path: Path) -> None:
    """Une plage enchaîne : il y a de quoi piocher (SPECS.md §7 n°44)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    due = emissions.due()

    assert due is not None and due[4] is True


def test_l_episode_d_un_podcast_seul_ne_se_dit_pas_passable(tmp_path: Path) -> None:
    """Hors plage, l'épisode est le seul de sa case : rien à piocher."""
    shows, _ = _emissions(tmp_path, FakeFeed([_episode("ep1")]), FrozenClock(VENDREDI_20H))

    due = shows.due()

    assert due is not None and due[4] is False


def test_un_direct_ne_se_dit_pas_passable(tmp_path: Path) -> None:
    due = _direct(tmp_path, FrozenClock(VENDREDI_20H + timedelta(minutes=2))).due()

    assert due is not None and due[4] is False


def test_une_plage_dit_qu_il_reste_un_episode_a_piocher(tmp_path: Path) -> None:
    """Le premier épisode a pris l'antenne et s'est inscrit ; l'autre flux a
    encore du neuf, donc « Passer » a de quoi piocher."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = emissions.due()
    assert due is not None
    emissions.started(due[1])

    assert emissions.has_another_episode()


def test_une_plage_dont_les_flux_sont_epuises_n_a_plus_rien_a_piocher(tmp_path: Path) -> None:
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))
    for _ in range(2):
        due = emissions.due()
        assert due is not None
        emissions.started(due[1])

    assert not emissions.has_another_episode()


def test_la_pioche_ne_lit_aucun_flux_ni_ne_consomme_le_hasard(tmp_path: Path) -> None:
    """Le rappel est lu au vote : il ne peut ni attendre un hébergeur, ni faire
    dériver la soirée en consommant un tirage (AGENTS.md §2)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))
    due = emissions.due()
    assert due is not None
    emissions.started(due[1])
    lues = list(feed.lues)

    assert emissions.has_another_episode()
    assert feed.lues == lues, "aucune lecture de flux"
    assert emissions.due() is not None, "le tirage suivant n'a pas dérivé"


def test_hors_d_une_plage_ouverte_il_n_y_a_rien_a_piocher(tmp_path: Path) -> None:
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H - timedelta(hours=1)))

    assert not emissions.has_another_episode()


# ── Une plage sert plusieurs demandes à la fois (GOAL-087-T01) ───────────────


def test_pendant_une_plage_une_seconde_demande_sert_un_autre_episode(tmp_path: Path) -> None:
    """`/skip-fresh` met deux entrées en vol, et les deux doivent être des
    épisodes : une musique se résout bien plus vite qu'un épisode de 50 à
    120 Mo, et prendrait l'antenne au saut (SPECS.md §7 n°45)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    premier = emissions.due()
    second = emissions.due()

    assert premier is not None and second is not None
    assert premier[1] != second[1], "deux flux, deux épisodes"


def test_le_meme_episode_n_est_jamais_demande_deux_fois(tmp_path: Path) -> None:
    """Un épisode déjà demandé compte comme diffusé pour la pioche suivante :
    son flux en sort, sinon la plage passerait deux fois le même."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    servis = [emissions.due(), emissions.due(), emissions.due()]

    adresses = [due[1] for due in servis if due is not None]
    assert len(adresses) == 2, "deux flux, deux épisodes, puis plus rien"
    assert len(set(adresses)) == 2


def test_sans_autre_episode_la_seconde_demande_rend_none(tmp_path: Path) -> None:
    """Un seul flux avec du neuf : la seconde demande n'a rien à servir, et la
    musique reprend comme pour toute case sans épisode (SPECS.md §4.11)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))

    assert emissions.due() is not None
    assert emissions.due() is None


def test_un_podcast_seul_ne_sert_qu_une_demande_par_case(tmp_path: Path) -> None:
    """Hors plage, la case n'enchaîne rien : une demande à la fois, comme
    avant (SPECS.md §7 n°14)."""
    feed = FakeFeed([_episode("ep1"), _episode("ep0", days=7)])
    shows, _ = _emissions(tmp_path, feed, FrozenClock(VENDREDI_20H))

    assert shows.due() is not None
    assert shows.due() is None


def test_un_episode_demande_ne_compte_pas_comme_une_pioche_possible(tmp_path: Path) -> None:
    """Il est déjà en vol chez le diffuseur : le proposer au vote ferait
    piocher ce que le diffuseur tient déjà (SPECS.md §7 n°44)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, _ = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))
    premier = emissions.due()
    assert premier is not None
    emissions.started(premier[1])
    assert emissions.due() is not None, "l'autre flux est demandé d'avance"

    assert not emissions.has_another_episode()


def test_une_demande_abandonnee_ne_fait_pas_oublier_les_autres(tmp_path: Path) -> None:
    """`dropped` nomme l'entrée qu'il abandonne : les autres sont encore en vol
    et vont passer (SPECS.md §7 n°45)."""
    feed = FeedParUrl({LEGEND_URL: [_episode("l1")], KONBINI_URL: [_episode("k1")]})
    emissions, state = _plage(tmp_path, feed, FrozenClock(VENDREDI_20H))
    premier = emissions.due()
    second = emissions.due()
    assert premier is not None and second is not None

    # Les flux se piochent dans l'ordre de leur nom : konbini d'abord, legend
    # ensuite (`episode_among`).
    emissions.dropped(premier[1])
    emissions.started(second[1])

    assert state.last_airing(f"{PLAGE.name}/{LEGEND_URL}") is not None
