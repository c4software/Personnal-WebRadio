"""Tests de l'assemblage : lecture de la configuration et câblage de la radio."""

from datetime import UTC, datetime, time
from pathlib import Path

import pytest

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import SettingsError
from webradio.adapters.config.schema import Show as ShowSettings
from webradio.app import main as module_main
from webradio.app.main import (
    _arguments,
    _libelle_de_plage,
    _libelle_du_moment,
    _periode,
    build,
    semaine_effective,
    version,
)
from webradio.app.playout import Upcoming
from webradio.core.bands import Band, Constraint, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.control import Kind
from webradio.core.planning import EffectiveSchedule, Segment
from webradio.core.programmes import DAYS, Programming
from webradio.core.runs import Mode
from webradio.core.shows import Show as ShowCase
from webradio.core.shows import ShowSchedule

TOML_MINIMAL = """
[draw]
artist_gap = 5

[jingles]
folder = "{folder}"

[state]
database = "{database}"

[[shows]]
name = "Une émission"
feed = "https://exemple.test/flux.xml"
days = ["friday"]
time = "20:00"
"""

ENV_MINIMAL = """
SUBSONIC_URL=http://exemple.test
SUBSONIC_UTILISATEUR=auditeur-fictif
SUBSONIC_MOT_DE_PASSE=passe-fictif
"""


@pytest.fixture
def reglages_dessai(tmp_path: Path) -> object:
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(TOML_MINIMAL.format(folder=folder, database=tmp_path / "state.sqlite3"))
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    return load(toml, env, environment={})


def test_la_version_est_une_chaine_non_vide() -> None:
    assert isinstance(version(), str)
    assert version() != ""


def test_la_version_reste_lisible_hors_installation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lancée depuis les sources sans installation, la radio doit démarrer au
    lieu de lever `PackageNotFoundError`."""
    from importlib.metadata import PackageNotFoundError

    def absent(_: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(module_main, "_version", absent)
    assert version() == "0.0.0+source"


def test_les_chemins_ont_des_defauts_utilisables() -> None:
    """Sans argument, les chemins par défaut sont ceux documentés dans le README."""
    options = _arguments([])
    assert options.config == Path("webradio.toml")
    assert options.env == Path(".env")


def test_les_chemins_se_declarent() -> None:
    options = _arguments(["--config", "/ailleurs/r.toml", "--env", "/ailleurs/.env"])
    assert options.config == Path("/ailleurs/r.toml")
    assert options.env == Path("/ailleurs/.env")


def test_l_assemblage_construit_une_radio_qui_ne_tourne_pas(reglages_dessai: object) -> None:
    """Construire ne démarre rien : la radio tourne seulement avec un auditeur
    (SPECS.md §1)."""
    playout, radio, _grille = build(reglages_dessai)  # type: ignore[arg-type]
    assert not radio.on_air()
    assert radio.on_air_now() is None
    playout.declare_listeners(1)
    assert radio.on_air()


def test_une_configuration_invalide_empeche_le_demarrage(tmp_path: Path) -> None:
    """Une configuration invalide bloque le démarrage au lieu d'être ignorée en
    partie (SPECS.md §6)."""
    toml = tmp_path / "webradio.toml"
    toml.write_text("[flux]\naddress = 'x'\n")
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    with pytest.raises(SettingsError):
        load(toml, env, environment={})


def test_un_secret_dans_le_toml_est_refuse(tmp_path: Path) -> None:
    """Les secrets vont dans le .env, jamais dans le TOML (SPECS.md §6.2)."""
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(
        TOML_MINIMAL.format(folder=folder, database=tmp_path / "e.sqlite3")
        + '\n[subsonic]\nmot_de_passe = "ne devrait pas être ici"\n'
    )
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    with pytest.raises(SettingsError, match="mot_de_passe"):
        load(toml, env, environment={})


# ── Ce que voit l'auditeur d'une plage au hasard (GOAL-037) ─────────────────


def test_l_antenne_nomme_le_theme_tire_et_dit_qu_il_l_a_ete() -> None:
    """Le libellé dit que le thème a été tiré au sort, pour le distinguer d'une
    plage déclarée."""
    band = Band(start=time(21), end=time(23), random_theme="artist")
    assert _libelle_du_moment(band, Constraint(artist="Air")) == "Moment · Air (au hasard)"
    band_genre = Band(start=time(21), end=time(23), random_theme="genre")
    assert _libelle_du_moment(band_genre, Constraint(genre="dub")) == "Moment · dub (au hasard)"


def test_un_tirage_qui_n_a_pas_abouti_ne_nomme_rien() -> None:
    band = Band(start=time(21), end=time(23), random_theme="genre")
    assert _libelle_du_moment(band, None) == "Moment · au hasard"


def test_une_plage_declaree_s_annonce_comme_avant() -> None:
    band = Band(start=time(8), end=time(10), genres=("jazz", "soul"))
    assert _libelle_du_moment(band, None) == "Moment · jazz, soul"


# ── Le moment courant se nomme toujours (GOAL-066) ─────────────────────────


def test_une_plage_a_mode_seul_nomme_son_tirage_libre() -> None:
    """Sans genre ni artiste, le libellé nomme le tirage libre au lieu d'un
    « Moment · » vide."""
    band = Band(start=time(19), end=time(20), mode=Mode.ERA_FAN)
    assert _libelle_du_moment(band, None) == "Moment · tirage libre (passionné d'époque)"


def test_une_plage_declaree_dit_aussi_son_enchainement() -> None:
    """Le bouton « Autre thème » retire la suite, pas les genres : le libellé
    nomme le mode d'enchaînement."""
    band = Band(start=time(15), end=time(16), genres=("reggae", "dub"), mode=Mode.ARTIST_FAN)
    assert _libelle_du_moment(band, None) == "Moment · reggae, dub (passionné d'artiste)"
    double = Band(start=time(20), end=time(22), genres=("rock",), mode=Mode.DOUBLE_DOSE)
    assert _libelle_du_moment(double, None) == "Moment · rock (double dose)"


def test_un_theme_tire_au_sort_garde_son_enchainement() -> None:
    band = Band(start=time(21), end=time(23), random_theme="genre", mode=Mode.ERA_FAN)
    assert _libelle_du_moment(band, Constraint(genre="dub")) == (
        "Moment · dub (au hasard) (passionné d'époque)"
    )
    assert _libelle_du_moment(band, None) == "Moment · au hasard (passionné d'époque)"


def test_le_planning_annonce_la_sorte_d_une_plage_au_hasard() -> None:
    """Le thème n'est tiré qu'à l'occurrence : le planning n'annonce que sa sorte."""
    artiste = Band(start=time(21), end=time(23), random_theme="artist")
    genre = Band(start=time(21), end=time(23), random_theme="genre")
    declaree = Band(start=time(8), end=time(10), genres=("jazz",))
    assert _libelle_de_plage(artiste) == ["Au hasard · un artiste"]
    assert _libelle_de_plage(genre) == ["Au hasard · un genre"]
    assert _libelle_de_plage(declaree) == ["jazz"]


def test_hors_d_une_plage_au_hasard_l_assemblage_refuse_de_retirer(
    reglages_dessai: object,
) -> None:
    """Sans plage au hasard en cours, le retirage est refusé avec son motif
    (GOAL-057)."""
    _playout, radio, _grille = build(reglages_dessai)  # type: ignore[arg-type]
    assert not radio.moment_random()
    verdict = radio.redraw_moment()
    assert not verdict.accepted
    assert verdict.reason is not None and "rien à retirer" in verdict.reason


def test_l_assemblage_cable_la_liste_des_prochains_titres(reglages_dessai: object) -> None:
    """Rien n'attend tant que le diffuseur n'a rien demandé, et retirer un
    inconnu rend `False` sans lever (GOAL-058)."""
    playout, radio, _grille = build(reglages_dessai)  # type: ignore[arg-type]
    playout.declare_listeners(1)
    assert radio.upcoming() == []
    assert not radio.withdraw("inconnu")


TOML_EPOQUES = (
    TOML_MINIMAL
    + """
[[bands]]
start = "00:00"
end = "23:59"
mode = "era_fan"
"""
)


def test_une_plage_a_suite_au_hasard_se_retire(tmp_path: Path) -> None:
    """Le mode era_fan compte comme une plage au hasard : le retirage y est
    accepté (GOAL-059)."""
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(TOML_EPOQUES.format(folder=folder, database=tmp_path / "state.sqlite3"))
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    _playout, radio, _grille = build(load(toml, env, environment={}))
    assert radio.moment_random()
    assert radio.redraw_moment().accepted


def test_les_decennies_du_toml_arrivent_jusqu_a_la_grille(tmp_path: Path) -> None:
    """La clé `eras` traverse le schéma et le câblage : sans elle, la plage
    tirerait dans toutes les décennies (GOAL-071)."""
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(
        (TOML_EPOQUES + "eras = [2000, 2010]\n").format(
            folder=folder, database=tmp_path / "state.sqlite3"
        )
    )
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    _playout, _radio, grille = build(load(toml, env, environment={}))
    journee = grille.day(datetime(2026, 9, 2, tzinfo=UTC))
    plages = [s.content for s in journee if isinstance(s.content, Band)]
    assert [p.eras for p in plages] == [(2000, 2010)]


# ── La semaine du Planning, déjà fusionnée (GOAL-068) ──────────────────────


def test_la_semaine_du_planning_est_deja_fusionnee() -> None:
    """La page reçoit la grille effective : l'émission, puis la plage qui
    reprend après elle, et non deux créneaux indépendants."""
    horloge = FrozenClock(datetime(2026, 9, 2, 14, 30, tzinfo=UTC))
    guitares = Band(start=time(20), end=time(22), genres=("Rock",), mode=Mode.DOUBLE_DOSE)
    hardisk = ShowCase(name="Hardisk", days=("wednesday",), hour=time(20))
    grille = EffectiveSchedule(
        Schedule([guitares], horloge), Programming([], horloge), ShowSchedule([hardisk])
    )
    declaree = ShowSettings(
        name="Hardisk",
        days=("wednesday",),
        hour=time(20),
        youtube="https://exemple.test/@hardisk",
    )

    jours = semaine_effective(grille, [declaree], horloge)["days"]

    assert isinstance(jours, dict)
    assert set(jours) == set(DAYS)
    assert jours["wednesday"] == [
        {
            "start": "20:00",
            "end": None,
            "after_show": False,
            "kind": "emission",
            "name": "Hardisk",
            "live": False,
            "youtube": True,
            "duration_minutes": None,
            "feeds": 0,
        },
        {
            "start": "20:00",
            "end": "22:00",
            "after_show": True,
            "kind": "moment",
            "genres": ["Rock"],
            "mode": "double_dose",
        },
    ]


def test_la_semaine_du_planning_couvre_les_sept_jours_depuis_aujourd_hui() -> None:
    """Sept journées quel que soit le jour de démarrage : la grille dépend du
    jour de la semaine, pas de la date."""
    guitares = Band(start=time(20), end=time(22), genres=("Rock",))
    samedi = FrozenClock(datetime(2026, 9, 5, 3, tzinfo=UTC))
    grille = EffectiveSchedule(
        Schedule([guitares], samedi), Programming([], samedi), ShowSchedule([])
    )

    jours = semaine_effective(grille, [], samedi)["days"]

    assert isinstance(jours, dict)
    assert set(jours) == set(DAYS)
    assert all(
        journee
        == [
            {
                "start": "20:00",
                "end": "22:00",
                "after_show": False,
                "kind": "moment",
                "genres": ["Rock"],
                "mode": None,
            }
        ]
        for journee in jours.values()
    )


def test_une_plage_de_podcasts_se_lit_comme_telle_dans_le_planning() -> None:
    """La page nomme un podcast, un direct et une chaîne ; elle doit pouvoir
    nommer une plage aussi, et dire combien de flux elle tire (GOAL-077)."""
    horloge = FrozenClock(datetime(2026, 9, 5, 14, 30, tzinfo=UTC))
    plage = ShowCase(name="Podcasts", days=("saturday",), hour=time(20), end=time(23))
    grille = EffectiveSchedule(
        Schedule([], horloge), Programming([], horloge), ShowSchedule([plage])
    )
    declaree = ShowSettings(
        name="Podcasts",
        days=("saturday",),
        hour=time(20),
        end=time(23),
        feeds=("https://a.test/rss", "https://b.test/rss", "https://c.test/rss"),
    )

    jours = semaine_effective(grille, [declaree], horloge)["days"]

    assert isinstance(jours, dict)
    assert jours["saturday"] == [
        {
            "start": "20:00",
            "end": "23:00",
            "after_show": False,
            "kind": "emission",
            "name": "Podcasts",
            "live": False,
            "youtube": False,
            "duration_minutes": None,
            "feeds": 3,
        }
    ]


TOML_PODCASTS = (
    TOML_MINIMAL
    + """
[[shows]]
name = "Podcasts - actus"
feeds = ["https://a.test/rss", "https://b.test/rss", "https://c.test/rss"]
days = ["sunday"]
time = "20:00"
end = "21:00"
"""
)


def test_une_periode_cousue_est_rendue_comme_au_planning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La liste et le Planning doivent dire la même chose d'une même période :
    l'entrée cousue porte le dictionnaire de `_periode` (GOAL-078)."""
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(TOML_PODCASTS.format(folder=folder, database=tmp_path / "state.sqlite3"))
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    reglages = load(toml, env, environment={})
    playout, radio, _grille = build(reglages)
    playout.declare_listeners(1)
    plage = ShowCase(name="Podcasts - actus", days=("sunday",), hour=time(20), end=time(21))
    segment = Segment(
        content=plage,
        start=datetime(2026, 9, 6, 20, tzinfo=UTC),
        end=datetime(2026, 9, 6, 21, tzinfo=UTC),
    )
    monkeypatch.setattr(
        playout,
        "upcoming",
        lambda: [
            Upcoming(Kind.SHOW, None, "Podcasts - actus", None, expected=True, period=segment)
        ],
    )

    entrees = radio.upcoming()

    assert len(entrees) == 1
    assert entrees[0].title == "Podcasts - actus"
    assert entrees[0].identifier == ""
    assert entrees[0].expected
    assert entrees[0].at is None
    assert entrees[0].period == _periode(segment, {e.name: e for e in reglages.settings.shows})
