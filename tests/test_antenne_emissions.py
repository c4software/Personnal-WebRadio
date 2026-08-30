"""Les émissions : ce qui est dû, ce qui est sauté, et ce qui ne se rejoue pas."""

import logging
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

import pytest

from webradio.adapters.etat.base import EtatSQLite
from webradio.adapters.podcast.flux import Episode as EpisodeDuFlux
from webradio.adapters.podcast.flux import PodcastIndisponible
from webradio.app.antenne_emissions import Emissions
from webradio.core.clock import HorlogeFigee
from webradio.core.emissions import Emission, GrilleDesEmissions

VENDREDI_20H = datetime(2026, 8, 28, 20, 0, tzinfo=UTC)  # 2026-08-28 est un vendredi
EMISSION = Emission(nom="A la French", jours=("vendredi",), heure=time(20, 0))


class FauxFlux:
    """Un flux versionné : il rend ce qu'on lui a mis, ou il tombe en panne."""

    def __init__(self, episodes: list[EpisodeDuFlux], *, injoignable: bool = False) -> None:
        self._episodes = episodes
        self.injoignable = injoignable
        self.lectures = 0

    def episodes(self, url: str) -> list[EpisodeDuFlux]:
        self.lectures += 1
        if self.injoignable:
            message = f"flux d'essai injoignable : {url}"
            raise PodcastIndisponible(message)
        return list(self._episodes)


def _episode(guid: str, jours: int = 0, minutes: int = 90) -> EpisodeDuFlux:
    return EpisodeDuFlux(
        identifiant=guid,
        titre=f"épisode {guid}",
        publie_le=VENDREDI_20H - timedelta(days=jours),
        audio=f"https://exemple.test/{guid}.mp3",
        duree=timedelta(minutes=minutes),
    )


def _emissions(
    tmp_path: Path,
    flux: FauxFlux,
    horloge: HorlogeFigee,
) -> tuple[Emissions, EtatSQLite]:
    etat = EtatSQLite(
        tmp_path / "etat.sqlite3",
        horloge,
        delai_attente=timedelta(seconds=5),
        demi_vie_votes=timedelta(days=90),
    )
    return (
        Emissions(
            GrilleDesEmissions([EMISSION]),
            flux,  # type: ignore[arg-type]
            etat,
            horloge,
            {"A la French": "https://exemple.test/flux.xml"},
        ),
        etat,
    )


def test_une_emission_due_rend_l_url_de_son_episode(tmp_path: Path) -> None:
    flux = FauxFlux([_episode("ep1")])
    emissions, _ = _emissions(tmp_path, flux, HorlogeFigee(VENDREDI_20H))
    due = emissions.due()
    assert due is not None
    assert due[0].nom == "A la French"
    assert due[1] == "https://exemple.test/ep1.mp3"


def test_hors_de_sa_case_aucune_emission_n_est_due(tmp_path: Path) -> None:
    flux = FauxFlux([_episode("ep1")])
    emissions, _ = _emissions(tmp_path, flux, HorlogeFigee(VENDREDI_20H - timedelta(days=1)))
    assert emissions.due() is None


def test_un_episode_deja_diffuse_fait_sauter_la_case(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """« Une émission qui n'a rien de neuf est une émission qui n'a pas lieu »
    (SPECS.md §4.11). On ne redescend pas à l'avant-dernier."""
    flux = FauxFlux([_episode("ep1")])
    emissions, _ = _emissions(tmp_path, flux, HorlogeFigee(VENDREDI_20H))
    assert emissions.due() is not None
    with caplog.at_level(logging.INFO):
        assert emissions.due() is None
    assert "rien de neuf" in caplog.text


def test_un_episode_neuf_rouvre_la_case(tmp_path: Path) -> None:
    flux = FauxFlux([_episode("ep1")])
    emissions, _ = _emissions(tmp_path, flux, HorlogeFigee(VENDREDI_20H))
    emissions.due()
    flux._episodes = [_episode("ep2"), _episode("ep1", jours=7)]
    due = emissions.due()
    assert due is not None
    assert due[1].endswith("ep2.mp3")


def test_un_flux_injoignable_ne_fait_pas_taire_la_radio(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Une émission perdue n'est pas une panne : la musique continue."""
    flux = FauxFlux([], injoignable=True)
    emissions, _ = _emissions(tmp_path, flux, HorlogeFigee(VENDREDI_20H))
    with caplog.at_level(logging.WARNING):
        assert emissions.due() is None
    assert "injoignable" in caplog.text


def test_un_flux_vide_ne_donne_aucune_emission(tmp_path: Path) -> None:
    emissions, _ = _emissions(tmp_path, FauxFlux([]), HorlogeFigee(VENDREDI_20H))
    assert emissions.due() is None


def test_le_rattrapage_est_borne_par_la_duree_de_l_episode(tmp_path: Path) -> None:
    """Se brancher dans la fenêtre rattrape ; au-delà, l'émission est perdue
    (SPECS.md §7 n°13)."""
    flux = FauxFlux([_episode("ep1", minutes=60)])
    dans_la_fenetre = HorlogeFigee(VENDREDI_20H + timedelta(minutes=40))
    emissions, _ = _emissions(tmp_path, flux, dans_la_fenetre)
    assert emissions.due() is not None

    flux_bis = FauxFlux([_episode("ep1", minutes=60)])
    hors_fenetre = HorlogeFigee(VENDREDI_20H + timedelta(minutes=70))
    emissions_bis, _ = _emissions(tmp_path / "bis", flux_bis, hors_fenetre)
    (tmp_path / "bis").mkdir(exist_ok=True)
    assert emissions_bis.due() is None


def test_le_flux_est_lu_avant_de_savoir_s_il_servira(tmp_path: Path) -> None:
    """Le seul endroit du projet où une décision exige un appel réseau qui peut
    ne servir à rien : la durée borne le rattrapage, et elle n'est connue
    qu'après lecture (ARCHITECTURE.md §5.2)."""
    flux = FauxFlux([_episode("ep1", minutes=1)])
    tardif = HorlogeFigee(VENDREDI_20H + timedelta(hours=3))
    emissions, _ = _emissions(tmp_path, flux, tardif)
    assert emissions.due() is None
    assert flux.lectures == 1, "le flux aurait dû être lu malgré tout"
