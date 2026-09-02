"""L'assemblage : ce qu'il lit, ce qu'il construit, et ce qu'il refuse.

Ces tests ont remplacé ceux du squelette de `GOAL-001` : `main()` ne se contente
plus d'annoncer son nom, il lit une configuration et câble une radio.
"""

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
    build,
    semaine_effective,
    version,
)
from webradio.core.bands import Band, Constraint, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.planning import EffectiveSchedule
from webradio.core.programmes import DAYS, Programming
from webradio.core.runs import Mode
from webradio.core.shows import Show as ShowCase

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
    """Le dépôt s'exécute aussi depuis les sources, sans avoir été installé.

    Sans ce repli, lancer la radio dans un dépôt fraîchement cloné lèverait
    `PackageNotFoundError` au lieu de démarrer.
    """
    from importlib.metadata import PackageNotFoundError

    def absent(_: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(module_main, "_version", absent)
    assert version() == "0.0.0+source"


def test_les_chemins_ont_des_defauts_utilisables() -> None:
    """Lancée sans argument dans le dépôt, la radio doit trouver sa
    configuration : c'est ce que documente le README."""
    options = _arguments([])
    assert options.config == Path("webradio.toml")
    assert options.env == Path(".env")


def test_les_chemins_se_declarent() -> None:
    options = _arguments(["--config", "/ailleurs/r.toml", "--env", "/ailleurs/.env"])
    assert options.config == Path("/ailleurs/r.toml")
    assert options.env == Path("/ailleurs/.env")


def test_l_assemblage_construit_une_radio_qui_ne_tourne_pas(reglages_dessai: object) -> None:
    """Construire n'est pas démarrer : rien ne tourne tant que personne
    n'écoute (SPECS.md §1)."""
    playout, radio, _grille = build(reglages_dessai)  # type: ignore[arg-type]
    assert not radio.on_air()
    assert radio.on_air_now() is None
    playout.declare_listeners(1)
    assert radio.on_air()


def test_une_configuration_invalide_empeche_le_demarrage(tmp_path: Path) -> None:
    """Une radio qui démarre en ignorant la moitié de sa configuration est pire
    qu'une radio qui refuse de démarrer (SPECS.md §6)."""
    toml = tmp_path / "webradio.toml"
    toml.write_text("[flux]\naddress = 'x'\n")
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    with pytest.raises(SettingsError):
        load(toml, env, environment={})


def test_un_secret_dans_le_toml_est_refuse(tmp_path: Path) -> None:
    """La séparation .env / TOML ne tiendrait pas une semaine sans ce refus
    (SPECS.md §6.2)."""
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
    """Sans le « au hasard », l'auditeur croirait à une plage déclarée."""
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
    """Sans genre ni artiste, la page affichait un « Moment · » orphelin à côté
    du bouton « Autre thème »."""
    band = Band(start=time(19), end=time(20), mode=Mode.ERA_FAN)
    assert _libelle_du_moment(band, None) == "Moment · tirage libre (passionné d'époque)"


def test_une_plage_declaree_dit_aussi_son_enchainement() -> None:
    """Le bouton retire la suite, pas les genres : l'antenne dit laquelle."""
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
    """Le thème n'existera qu'à l'occurrence : d'avance, seule la sorte est vraie."""
    artiste = Band(start=time(21), end=time(23), random_theme="artist")
    genre = Band(start=time(21), end=time(23), random_theme="genre")
    declaree = Band(start=time(8), end=time(10), genres=("jazz",))
    assert _libelle_de_plage(artiste) == ["Au hasard · un artiste"]
    assert _libelle_de_plage(genre) == ["Au hasard · un genre"]
    assert _libelle_de_plage(declaree) == ["jazz"]


def test_hors_d_une_plage_au_hasard_l_assemblage_refuse_de_retirer(
    reglages_dessai: object,
) -> None:
    """GOAL-057 : sans plage au hasard en cours, il n'y a rien à retirer, et
    c'est dit — pas un tirage libre silencieux."""
    _playout, radio, _grille = build(reglages_dessai)  # type: ignore[arg-type]
    assert not radio.moment_random()
    verdict = radio.redraw_moment()
    assert not verdict.accepted
    assert verdict.reason is not None and "rien à retirer" in verdict.reason


def test_l_assemblage_cable_la_liste_des_prochains_titres(reglages_dessai: object) -> None:
    """GOAL-058 : rien n'attend tant que le diffuseur n'a rien demandé, et
    retirer un inconnu est faux — pas une erreur."""
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
    """GOAL-059 : « année aléatoire », c'est le mode era_fan — retirer y vaut."""
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(TOML_EPOQUES.format(folder=folder, database=tmp_path / "state.sqlite3"))
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    _playout, radio, _grille = build(load(toml, env, environment={}))
    assert radio.moment_random()
    assert radio.redraw_moment().accepted


# ── La semaine du Planning, déjà fusionnée (GOAL-068) ──────────────────────


def test_la_semaine_du_planning_est_deja_fusionnee() -> None:
    """Ce que la page reçoit, c'est ce qui passera : l'émission d'abord, puis
    la plage qui reprend après elle — plus deux créneaux côte à côte."""
    horloge = FrozenClock(datetime(2026, 9, 2, 14, 30, tzinfo=UTC))
    guitares = Band(start=time(20), end=time(22), genres=("Rock",), mode=Mode.DOUBLE_DOSE)
    hardisk = ShowCase(name="Hardisk", days=("wednesday",), hour=time(20))
    grille = EffectiveSchedule(Schedule([guitares], horloge), Programming([], horloge), [hardisk])
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
    """Sept journées, quel que soit le jour de démarrage : la grille ne dépend
    que du jour de la semaine, jamais de la date."""
    guitares = Band(start=time(20), end=time(22), genres=("Rock",))
    samedi = FrozenClock(datetime(2026, 9, 5, 3, tzinfo=UTC))
    grille = EffectiveSchedule(Schedule([guitares], samedi), Programming([], samedi), [])

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
