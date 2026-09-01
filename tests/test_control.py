"""`stop` et `encore` : ce qu'ils obtiennent, et ce qu'ils se voient refuser."""

from datetime import UTC, datetime

import pytest

from tests.fakes import FakeSource, track
from webradio.core.clock import FrozenClock
from webradio.core.control import Command, Control, Kind
from webradio.core.jingles import JINGLE_ENCORE, Jingles
from webradio.core.models import Track
from webradio.core.queue import EmptyQueue, Queue
from webradio.core.rng import ScriptedRandom
from webradio.core.rotation import Window

BOWIE_1 = track("1", "Bowie", "rock")
BOWIE_2 = track("2", "Bowie", "rock")
AIR_1 = track("3", "Air", "rock")
PORTISHEAD = track("4", "Portishead", "trip-hop")


def jingles() -> Jingles:
    return Jingles(FrozenClock(datetime(2026, 8, 30, 14, 10, tzinfo=UTC)))


def control(
    catalogue: list[Track] | None = None,
    indices: list[int] | None = None,
    jeu: Jingles | None = None,
) -> Control:
    tracks = [BOWIE_1, BOWIE_2, AIR_1, PORTISHEAD] if catalogue is None else catalogue
    return Control(
        FakeSource(list(tracks)),
        ScriptedRandom(indices if indices is not None else [0] * 20),
        jeu if jeu is not None else jingles(),
    )


def test_un_seul_vote_suffit_a_passer_le_morceau() -> None:
    """Ni quorum, ni fenêtre de dépouillement (SPECS.md §7 n°10)."""
    c = control()
    assert c.vote(Command.SKIP).accepted
    assert c.take_skip()
    assert not c.take_skip()


def test_un_encore_accepte_marque_le_jingle_de_vote_comme_du() -> None:
    jeu = jingles()
    c = control(jeu=jeu)
    assert c.vote(Command.MORE).accepted
    assert c.take_more()
    assert jeu.due_now() == (JINGLE_ENCORE,)


def test_encore_ne_porte_que_sur_le_morceau_suivant() -> None:
    """Il n'installe pas un mode (SPECS.md §4.6) : une fois honoré, il s'éteint."""
    c = control()
    c.vote(Command.MORE)
    assert c.take_more()
    assert not c.take_more()


@pytest.mark.parametrize(
    ("kind", "attendu"),
    [
        (Kind.JINGLE, "jingle"),
        (Kind.NEWS, "flash"),
        (Kind.SHOW, "émission"),
    ],
)
def test_un_vote_pendant_autre_chose_que_la_musique_est_refuse_avec_son_motif(
    kind: Kind, attendu: str
) -> None:
    """Un refus muet est indistinguable d'une panne, et pousse à réessayer."""
    c = control()
    c.declare(kind)
    answer = c.vote(Command.SKIP)
    assert not answer.accepted
    assert attendu in answer.reason


def test_un_vote_refuse_n_est_ni_mis_en_attente_ni_applique_en_douce() -> None:
    """Les deux seraient des surprises (SPECS.md §4.6)."""
    jeu = jingles()
    c = control(jeu=jeu)
    c.declare(Kind.SHOW)
    assert not c.vote(Command.MORE).accepted
    c.declare(Kind.MUSIC)
    assert not c.take_more()
    assert jeu.due_now() == ()


def test_le_vote_redevient_possible_des_que_la_musique_revient() -> None:
    c = control()
    c.declare(Kind.JINGLE)
    assert not c.vote(Command.SKIP).accepted
    c.declare(Kind.MUSIC)
    assert c.kind is Kind.MUSIC
    assert c.vote(Command.SKIP).accepted


def test_encore_sert_un_autre_morceau_du_meme_artiste() -> None:
    pick = control().track_after_more(BOWIE_1)
    assert pick.track == BOWIE_2
    assert pick.fallbacks == ()


def test_encore_outrepasse_la_non_repetition() -> None:
    """Les deux se contrediraient sinon : l'une réclame le même artiste,
    l'autre le lui interdit. C'est `encore` qui gagne (SPECS.md §7 n°7)."""
    window = Window(width=5)
    window.remember(BOWIE_1)
    assert not window.allows(BOWIE_2)
    assert control().track_after_more(BOWIE_1).track == BOWIE_2


def test_les_morceaux_servis_par_encore_n_entrent_pas_dans_la_fenetre() -> None:
    """Sans cela, un long enchaînement condamnerait l'artiste pour longtemps
    après (SPECS.md §4.6). La fenêtre est nourrie par la file, pas par `encore`."""
    source = FakeSource([BOWIE_1, BOWIE_2, AIR_1, PORTISHEAD])
    window = Window(width=5)
    queue = Queue(source, ScriptedRandom([0]), window)
    queue.next_pick()
    avant = window.artists
    c = Control(source, ScriptedRandom([0, 0]), jingles())
    c.track_after_more(BOWIE_1)
    assert window.artists == avant


def test_un_artiste_epuise_se_replie_sur_le_genre() -> None:
    """Ce qui borne `encore` est la bibliothèque : quand Bowie n'a plus de
    morceau non joué, on descend d'un cran (SPECS.md §4.6)."""
    c = control()
    c.track_after_more(BOWIE_1)
    c.track_after_more(BOWIE_2)
    pick = c.track_after_more(BOWIE_1)
    assert pick.track == AIR_1
    assert pick.fallbacks == ("artiste « Bowie » épuisé",)


def test_un_genre_epuise_se_replie_sur_le_tirage_libre() -> None:
    c = control()
    c.track_after_more(BOWIE_1)
    c.track_after_more(BOWIE_2)
    c.track_after_more(BOWIE_1)
    pick = c.track_after_more(AIR_1)
    assert pick.track == PORTISHEAD
    assert pick.fallbacks == ("artiste « Air » épuisé", "genre « rock » épuisé : tirage libre")


def test_un_morceau_sans_genre_se_replie_directement_sur_le_tirage_libre() -> None:
    solo = track("9", "Solo", None)
    c = control([solo, PORTISHEAD])
    pick = c.track_after_more(solo)
    assert pick.track == PORTISHEAD
    assert pick.fallbacks == ("artiste « Solo » épuisé", "morceau sans genre : tirage libre")


def test_une_bibliotheque_entierement_servie_ne_fait_pas_taire_la_radio() -> None:
    """« Une radio ne se tait pas » (SPECS.md §5.1) : la chaîne d'`encore`
    repart plutôt que de rendre le silence."""
    c = control([BOWIE_1])
    pick = c.track_after_more(BOWIE_1)
    assert pick.track == BOWIE_1
    assert "la chaîne repart" in pick.fallbacks[-1]


def test_encore_s_enchaine_sans_limite_borne_par_la_bibliotheque() -> None:
    """Aucun compteur, aucun plafond (SPECS.md §7 n°7) : ce qui borne est la
    bibliothèque, et elle n'arrête jamais la radio."""
    c = control(indices=[0] * 30)
    courant = BOWIE_1
    for _ in range(20):
        courant = c.track_after_more(courant).track
    assert courant.identifier in {"1", "2", "3", "4"}


def test_une_source_vide_refuse_de_servir_un_encore() -> None:
    """Distinct d'une source injoignable : ici elle a répondu, elle n'a rien."""
    c = Control(FakeSource([]), ScriptedRandom([0]), jingles())
    with pytest.raises(EmptyQueue, match="aucune piste"):
        c.track_after_more(BOWIE_1)


def test_l_encore_sert_aussi_une_piste_longue() -> None:
    """SPECS.md §7 n°32 révisée : une piste longue se choisit comme les
    autres — la diffusion la coupera au plafond, l'encore ne l'écarte pas."""
    courant = track("a1", "Air", genre="électro", secondes=200)
    long = track("a2", "Air", genre="électro", secondes=2400)
    c = Control(FakeSource([courant, long]), ScriptedRandom([0]), jingles())
    pick = c.track_after_more(courant)
    assert pick.track.identifier == "a2"
    assert pick.fallbacks == ()
