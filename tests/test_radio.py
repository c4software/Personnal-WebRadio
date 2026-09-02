"""La façade traduit fidèlement, et les deux vocabulaires ne divergent pas."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from tests.fakes import FakeSource, track
from webradio.adapters.web.api import Kind as NatureWeb
from webradio.adapters.web.api import Vote
from webradio.app.radio import ListenerCount, LiveRadio
from webradio.core.clock import FrozenClock
from webradio.core.control import Command, Control, Kind
from webradio.core.jingles import Jingles
from webradio.core.models import Track
from webradio.core.rng import ScriptedRandom


def _radio(skip: Callable[[], None] | None = None) -> tuple[LiveRadio, ListenerCount]:
    clock = FrozenClock(datetime(2026, 8, 30, 12, 0, tzinfo=UTC))
    control = Control(
        source=FakeSource([track("1", "Bowie", genre="rock")]),
        random=ScriptedRandom([0] * 50),
        jingles=Jingles(clock),
    )
    counter = ListenerCount()
    return LiveRadio(control, counter, skip=skip), counter


def test_les_deux_vocabulaires_de_nature_coincident() -> None:
    """La traduction se fait par valeur ; si les deux jeux divergent, ce test
    casse avant l'exécution."""
    assert {n.value for n in Kind} == {n.value for n in NatureWeb}


def test_les_deux_vocabulaires_de_vote_coincident() -> None:
    assert {c.value for c in Command} == {v.value for v in Vote}


def test_rien_ne_passe_quand_personne_n_ecoute() -> None:
    radio, _ = _radio()
    assert not radio.on_air()
    assert radio.on_air_now() is None


def test_l_antenne_rend_ce_que_le_programme_a_declare() -> None:
    radio, counter = _radio()
    counter.declare(on_air=True)
    radio.declare(
        Kind.MUSIC,
        Track("id", "Heroes", "Bowie", "rock", timedelta(seconds=200)),
    )
    vue = radio.on_air_now()
    assert vue is not None
    assert vue.kind is NatureWeb.MUSIC
    assert vue.title == "Heroes"
    assert vue.artist == "Bowie"


def test_un_jingle_n_a_ni_titre_ni_artiste() -> None:
    """Un habillage n'est pas un morceau : l'API doit pouvoir le dire."""
    radio, counter = _radio()
    counter.declare(on_air=True)
    radio.declare(Kind.JINGLE, None)
    vue = radio.on_air_now()
    assert vue is not None
    assert vue.kind is NatureWeb.JINGLE
    assert vue.title is None


def test_un_vote_pendant_un_jingle_est_refuse_avec_un_motif() -> None:
    radio, counter = _radio()
    counter.declare(on_air=True)
    radio.declare(Kind.JINGLE, None)
    verdict = radio.vote(Vote.SKIP)
    assert not verdict.accepted
    assert verdict.reason


def test_un_vote_accepte_est_retenu() -> None:
    radio, counter = _radio()
    retenus: list[tuple[Command, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifier))
    counter.declare(on_air=True)
    radio.declare(
        Kind.MUSIC,
        Track("id", "Heroes", "Bowie", "rock", timedelta(seconds=200)),
    )
    assert radio.vote(Vote.SKIP).accepted
    assert retenus == [(Command.SKIP, "id")]


def test_un_vote_refuse_n_enregistre_rien() -> None:
    """Sinon la radio apprendrait de gestes qui n'ont rien changé (SPECS.md §4.6)."""
    radio, counter = _radio()
    retenus: list[tuple[Command, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifier))
    counter.declare(on_air=True)
    radio.declare(Kind.JINGLE, None)
    assert not radio.vote(Vote.SKIP).accepted
    assert retenus == []


def test_un_vote_sans_piste_courante_agit_sans_s_apprendre() -> None:
    """Entre deux morceaux, il n'y a rien sur quoi le vote puisse porter."""
    radio, counter = _radio()
    retenus: list[tuple[Command, str]] = []
    radio._retenir = lambda c, p: retenus.append((c, p.identifier))
    counter.declare(on_air=True)
    radio.declare(Kind.MUSIC, None)
    assert radio.vote(Vote.MORE).accepted
    assert retenus == []


def test_un_stop_accepte_ordonne_le_saut() -> None:
    """Un `stop` accepté passe le morceau en cours (SPECS.md §4.6, GOAL-017)."""
    sauts: list[bool] = []
    radio, _ = _radio(skip=lambda: sauts.append(True))
    verdict = radio.vote(Vote.SKIP)
    assert verdict.accepted
    assert sauts == [True]


def test_un_encore_accepte_n_ordonne_aucun_saut() -> None:
    sauts: list[bool] = []
    radio, _ = _radio(skip=lambda: sauts.append(True))
    assert radio.vote(Vote.MORE).accepted
    assert sauts == []


def test_un_stop_refuse_n_ordonne_aucun_saut() -> None:
    sauts: list[bool] = []
    radio, _ = _radio(skip=lambda: sauts.append(True))
    radio.declare(Kind.JINGLE, None)
    assert not radio.vote(Vote.SKIP).accepted
    assert sauts == []


def test_ce_qui_commence_entre_au_journal_sauf_les_jingles() -> None:
    """Le journal note ce qui commence, sauf l'habillage (GOAL-027)."""
    lignes: list[tuple[str, str, str]] = []
    radio, _ = _radio()
    radio._journaliser = lambda kind, titre, artiste: lignes.append((kind, titre, artiste))
    radio.declare(Kind.MUSIC, Track("1", "Sexy Boy", "Air", None, timedelta(seconds=90)))
    radio.declare(Kind.JINGLE, None)
    radio.declare(Kind.SHOW, None, "Flash franceinfo")
    radio.declare(Kind.MUSIC, None)  # rien à nommer : rien au journal
    assert lignes == [
        ("musique", "Sexy Boy", "Air"),
        ("emission", "Flash franceinfo", ""),
    ]


def test_un_encore_accepte_jette_l_avance_du_diffuseur() -> None:
    """L'effet suit la chanson en cours, pas celle d'après (GOAL-034)."""
    ordres: list[str] = []
    radio, _ = _radio(skip=lambda: ordres.append("skip"))
    radio._vider_l_avance = lambda: ordres.append("requeue")
    assert radio.vote(Vote.MORE).accepted
    assert ordres == ["requeue"]
    assert radio.vote(Vote.SKIP).accepted
    assert ordres == ["requeue", "skip"]


def test_sans_cablage_le_retirage_est_refuse_en_le_disant() -> None:
    radio, _ = _radio()
    assert not radio.moment_random()
    verdict = radio.redraw_moment()
    assert not verdict.accepted
    assert verdict.reason is not None and "rien à retirer" in verdict.reason


def test_le_retirage_est_relaye_tel_quel() -> None:
    """La façade relaie une décision du câblage, elle ne la prend pas."""
    from webradio.adapters.web.api import Verdict

    radio, _ = _radio()
    radio._moment_au_hasard = lambda: True
    radio._retirer = lambda: Verdict(accepted=True)
    assert radio.moment_random()
    assert radio.redraw_moment().accepted


def test_sans_cablage_rien_n_attend_et_rien_ne_se_retire() -> None:
    radio, counter = _radio()
    counter.declare(on_air=True)
    assert radio.upcoming() == []
    assert not radio.withdraw("x")


def test_la_liste_est_vide_quand_la_chaine_ne_tourne_pas() -> None:
    from webradio.adapters.web.api import UpcomingEntry

    radio, counter = _radio()
    radio._prochains = lambda: [UpcomingEntry(kind=NatureWeb.MUSIC, title="t", artist="a")]
    assert radio.upcoming() == []
    counter.declare(on_air=True)
    assert len(radio.upcoming()) == 1
