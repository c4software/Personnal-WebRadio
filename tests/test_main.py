"""Le squelette se lance, annonce ce qu'il est, et s'arrête proprement."""

import logging

import pytest

from webradio.app.main import main, version


def test_le_squelette_sort_sans_erreur() -> None:
    assert main() == 0


def test_le_squelette_annonce_son_nom(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        main()
    assert "local-webradio" in caplog.text


def test_la_version_est_une_chaine_non_vide() -> None:
    assert isinstance(version(), str)
    assert version() != ""


def test_la_version_reste_lisible_hors_installation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le dépôt s'exécute aussi depuis les sources, sans avoir été installé.

    Sans ce repli, lancer le squelette dans un dépôt fraîchement cloné lèverait
    PackageNotFoundError au lieu de démarrer.
    """
    from importlib import metadata

    def absent(_: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", absent)
    assert version() == "0.0.0+source"
