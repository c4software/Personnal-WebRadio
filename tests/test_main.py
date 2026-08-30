"""L'assemblage : ce qu'il lit, ce qu'il construit, et ce qu'il refuse.

Ces tests ont remplacé ceux du squelette de `GOAL-001` : `main()` ne se contente
plus d'annoncer son nom, il lit une configuration et câble une radio.
"""

from pathlib import Path

import pytest

from webradio.adapters.config.loading import load
from webradio.adapters.config.schema import SettingsError
from webradio.app import main as module_main
from webradio.app.main import _arguments, build, version

TOML_MINIMAL = """
[flux]
adresse = "127.0.0.1"
port = 8123
format = "mp3"
debit_kbps = 128
frequence_hz = 44100
canaux = 2

[tirage]
non_repetition_artistes = 5

[jingles]
dossier = "{folder}"

[etat]
base = "{database}"

[[emissions]]
nom = "Une émission"
flux = "https://exemple.test/flux.xml"
jours = ["vendredi"]
heure = "20:00"
"""

ENV_MINIMAL = """
NAVIDROME_URL=http://exemple.test
NAVIDROME_UTILISATEUR=auditeur-fictif
NAVIDROME_MOT_DE_PASSE=passe-fictif
"""


@pytest.fixture
def reglages_dessai(tmp_path: Path) -> object:
    folder = tmp_path / "jingles"
    folder.mkdir()
    toml = tmp_path / "webradio.toml"
    toml.write_text(TOML_MINIMAL.format(folder=folder, database=tmp_path / "etat.sqlite3"))
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
    server, radio, station = build(reglages_dessai)  # type: ignore[arg-type]
    assert not radio.on_air()
    assert radio.on_air_now() is None
    assert station.listeners == 0
    assert not station.on_air
    assert server is not None


def test_une_configuration_invalide_empeche_le_demarrage(tmp_path: Path) -> None:
    """Une radio qui démarre en ignorant la moitié de sa configuration est pire
    qu'une radio qui refuse de démarrer (SPECS.md §6)."""
    toml = tmp_path / "webradio.toml"
    toml.write_text("[flux]\nadresse = 'x'\n")
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
        + '\n[navidrome]\nmot_de_passe = "ne devrait pas être ici"\n'
    )
    env = tmp_path / ".env"
    env.write_text(ENV_MINIMAL)
    with pytest.raises(SettingsError, match="mot_de_passe"):
        load(toml, env, environment={})
