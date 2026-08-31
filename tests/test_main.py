"""L'assemblage : ce qu'il lit, ce qu'il construit, et ce qu'il refuse.

Ces tests ont remplacé ceux du squelette de `GOAL-001` : `main()` ne se contente
plus d'annoncer son nom, il lit une configuration et câble une radio.
"""

from datetime import time
from pathlib import Path

import pytest

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import Band as BandSettings
from webradio.adapters.config.schema import SettingsError
from webradio.app import main as module_main
from webradio.app.main import (
    _arguments,
    _libelle_de_plage,
    _libelle_du_moment,
    build,
    version,
)
from webradio.core.bands import Band, Constraint

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
    playout, radio = build(reglages_dessai)  # type: ignore[arg-type]
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


def test_le_planning_annonce_la_sorte_d_une_plage_au_hasard() -> None:
    """Le thème n'existera qu'à l'occurrence : d'avance, seule la sorte est vraie."""
    artiste = BandSettings(start=time(21), end=time(23), random_theme="artist")
    genre = BandSettings(start=time(21), end=time(23), random_theme="genre")
    declaree = BandSettings(start=time(8), end=time(10), genres=("jazz",))
    assert _libelle_de_plage(artiste) == ["Au hasard · un artiste"]
    assert _libelle_de_plage(genre) == ["Au hasard · un genre"]
    assert _libelle_de_plage(declaree) == ["jazz"]
