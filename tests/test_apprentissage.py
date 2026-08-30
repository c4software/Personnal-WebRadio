"""L'apprentissage : ce qu'il lit, ce qu'il écrit, et ce qu'il refuse d'écrire."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.fakes import piste
from webradio.adapters.etat.base import EtatSQLite
from webradio.adapters.etat.base import Portee as PorteeBase
from webradio.app.apprentissage import Apprentissage
from webradio.core.clock import HorlogeFigee
from webradio.core.controle import Commande
from webradio.core.ponderation import Portee

MIDI = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _apprentissage(tmp_path: Path, horloge: HorlogeFigee | None = None) -> Apprentissage:
    base = EtatSQLite(
        tmp_path / "etat.sqlite3",
        horloge=horloge or HorlogeFigee(MIDI),
        delai_attente=timedelta(seconds=5),
        demi_vie_votes=timedelta(days=90),
    )
    return Apprentissage(base, plancher=0.25, plafond=4.0, pente=0.5, poids_croise=0.25)


def test_les_deux_vocabulaires_de_portee_coincident() -> None:
    """Le noyau et la base ont chacun leur `Portee`. Le jour où elles
    divergeront, ce test cassera ici plutôt qu'en base."""
    assert {p.value for p in Portee} == {p.value for p in PorteeBase}


def test_une_piste_inconnue_pese_neutre(tmp_path: Path) -> None:
    """Une base vide se comporte comme « personne n'a jamais voté »."""
    assert _apprentissage(tmp_path).peser(piste("1", "Bowie")) == pytest.approx(1.0)


def test_un_stop_fait_reculer_la_piste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = piste("1", "Bowie")
    a.retenir(Commande.STOP, p)
    assert a.peser(p) < 1.0


def test_un_encore_fait_avancer_l_artiste(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    a.retenir(Commande.ENCORE, piste("1", "Bowie"))
    # Un autre titre du même artiste profite du vote : c'est la portée croisée.
    assert a.peser(piste("2", "Bowie")) > 1.0


def test_le_vote_porte_sur_les_deux_mais_pas_egalement(tmp_path: Path) -> None:
    """Un `stop` compte 1 sur la piste et 0,25 sur l'artiste (SPECS.md §4.12) :
    la piste visée doit donc reculer plus qu'un autre titre du même artiste."""
    a = _apprentissage(tmp_path)
    visee = piste("1", "Bowie")
    voisine = piste("2", "Bowie")
    a.retenir(Commande.STOP, visee)
    assert a.peser(visee) < a.peser(voisine) < 1.0


def test_le_poids_ne_descend_jamais_a_zero(tmp_path: Path) -> None:
    """Rien n'est jamais supprimé : le plancher est 0,25 fois, pas 0
    (SPECS.md §7 n°17)."""
    a = _apprentissage(tmp_path)
    p = piste("1", "Bowie")
    for _ in range(50):
        a.retenir(Commande.STOP, p)
    assert a.peser(p) == pytest.approx(0.25)


def test_le_poids_ne_depasse_jamais_le_plafond(tmp_path: Path) -> None:
    a = _apprentissage(tmp_path)
    p = piste("1", "Bowie")
    for _ in range(50):
        a.retenir(Commande.ENCORE, p)
    assert a.peser(p) == pytest.approx(4.0)


def test_les_votes_s_oublient_avec_le_temps(tmp_path: Path) -> None:
    """Sans oubli, la radio se figerait sur ce qu'on a cliqué le premier mois
    (SPECS.md §7 n°18)."""
    horloge = HorlogeFigee(MIDI)
    a = _apprentissage(tmp_path, horloge)
    p = piste("1", "Bowie")
    for _ in range(5):
        a.retenir(Commande.STOP, p)
    juste_apres = a.peser(p)
    horloge.avancer(timedelta(days=365 * 2))
    bien_plus_tard = a.peser(p)
    assert juste_apres < bien_plus_tard < 1.0


def test_une_base_devenue_injoignable_rend_un_poids_neutre(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Un tirage sans mémoire vaut infiniment mieux qu'un tirage qui n'a pas
    lieu : la radio ne se tait pas (SPECS.md §5.1).

    La base est construite normalement, **puis** rendue inaccessible — c'est le
    régime « en cours de diffusion ». Une base injoignable **au démarrage**,
    elle, échoue bruyamment, et c'est voulu : les deux régimes d'erreur de
    SPECS.md §5 sont bien distincts.
    """
    dossier = tmp_path / "etat"
    dossier.mkdir()
    a = _apprentissage(dossier)
    p = piste("1", "Bowie")
    a.retenir(Commande.STOP, p)
    assert a.peser(p) < 1.0

    dossier.chmod(0o500)
    (dossier / "etat.sqlite3").chmod(0o000)
    try:
        with caplog.at_level(logging.WARNING):
            assert a.peser(p) == pytest.approx(1.0)
        assert "tirage neutre" in caplog.text
    finally:
        (dossier / "etat.sqlite3").chmod(0o600)
        dossier.chmod(0o700)


def test_un_vote_non_retenu_ne_fait_pas_taire_la_radio(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Perdre un vote est regrettable ; couper la radio pour cela serait pire."""
    dossier = tmp_path / "etat"
    dossier.mkdir()
    a = _apprentissage(dossier)
    a.retenir(Commande.STOP, piste("1", "Bowie"))
    (dossier / "etat.sqlite3").chmod(0o400)
    try:
        with caplog.at_level(logging.WARNING):
            a.retenir(Commande.ENCORE, piste("2", "Air"))
        assert "non retenu" in caplog.text
    finally:
        (dossier / "etat.sqlite3").chmod(0o600)
