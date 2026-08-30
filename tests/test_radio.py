"""La façade traduit fidèlement, et les deux vocabulaires ne divergent pas."""

from datetime import UTC, datetime, timedelta

from tests.fakes import FakeSource, piste
from webradio.adapters.web.api import Nature as NatureWeb
from webradio.adapters.web.api import Vote
from webradio.app.radio import CompteurAuditeurs, RadioEnDirect
from webradio.core.clock import HorlogeFigee
from webradio.core.control import Commande, Controle, Nature
from webradio.core.jingles import Jingles
from webradio.core.models import Piste
from webradio.core.rng import HasardScripte


def _radio() -> tuple[RadioEnDirect, CompteurAuditeurs]:
    horloge = HorlogeFigee(datetime(2026, 8, 30, 12, 0, tzinfo=UTC))
    controle = Controle(
        source=FakeSource([piste("1", "Bowie", genre="rock")]),
        hasard=HasardScripte([0] * 50),
        jingles=Jingles(horloge),
    )
    compteur = CompteurAuditeurs()
    return RadioEnDirect(controle, compteur), compteur


def test_les_deux_vocabulaires_de_nature_coincident() -> None:
    """La traduction se fait par valeur. Le jour où les deux jeux divergeront,
    ce test cassera ici plutôt qu'à l'exécution."""
    assert {n.value for n in Nature} == {n.value for n in NatureWeb}


def test_les_deux_vocabulaires_de_vote_coincident() -> None:
    assert {c.value for c in Commande} == {v.value for v in Vote}


def test_rien_ne_passe_quand_personne_n_ecoute() -> None:
    radio, _ = _radio()
    assert not radio.en_diffusion()
    assert radio.antenne() is None


def test_l_antenne_rend_ce_que_le_programme_a_declare() -> None:
    radio, compteur = _radio()
    compteur.declarer(en_antenne=True)
    radio.declarer(
        Nature.MUSIQUE,
        Piste("id", "Heroes", "Bowie", "rock", timedelta(seconds=200)),
    )
    vue = radio.antenne()
    assert vue is not None
    assert vue.nature is NatureWeb.MUSIQUE
    assert vue.titre == "Heroes"
    assert vue.artiste == "Bowie"


def test_un_jingle_n_a_ni_titre_ni_artiste() -> None:
    """Un habillage n'est pas un morceau : l'API doit pouvoir le dire."""
    radio, compteur = _radio()
    compteur.declarer(en_antenne=True)
    radio.declarer(Nature.JINGLE, None)
    vue = radio.antenne()
    assert vue is not None
    assert vue.nature is NatureWeb.JINGLE
    assert vue.titre is None


def test_un_vote_pendant_un_jingle_est_refuse_avec_un_motif() -> None:
    radio, compteur = _radio()
    compteur.declarer(en_antenne=True)
    radio.declarer(Nature.JINGLE, None)
    verdict = radio.voter(Vote.STOP)
    assert not verdict.accepte
    assert verdict.motif


def test_un_vote_accepte_est_retenu() -> None:
    radio, compteur = _radio()
    retenus: list[tuple[Commande, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifiant))
    compteur.declarer(en_antenne=True)
    radio.declarer(
        Nature.MUSIQUE,
        Piste("id", "Heroes", "Bowie", "rock", timedelta(seconds=200)),
    )
    assert radio.voter(Vote.STOP).accepte
    assert retenus == [(Commande.STOP, "id")]


def test_un_vote_refuse_n_enregistre_rien() -> None:
    """Sinon la radio apprendrait de gestes qui n'ont rien changé, et
    l'auditeur pondérerait sa bibliothèque sans le savoir (SPECS.md §4.6)."""
    radio, compteur = _radio()
    retenus: list[tuple[Commande, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifiant))
    compteur.declarer(en_antenne=True)
    radio.declarer(Nature.JINGLE, None)
    assert not radio.voter(Vote.STOP).accepte
    assert retenus == []


def test_un_vote_sans_piste_courante_agit_sans_s_apprendre() -> None:
    """Entre deux morceaux, il n'y a rien sur quoi le vote puisse porter."""
    radio, compteur = _radio()
    retenus: list[tuple[Commande, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifiant))
    compteur.declarer(en_antenne=True)
    radio.declarer(Nature.MUSIQUE, None)
    assert radio.voter(Vote.ENCORE).accepte
    assert retenus == []
