"""`stop` et `encore` : ce qu'ils obtiennent, et ce qu'ils se voient refuser."""

from datetime import UTC, datetime

import pytest

from tests.fakes import FakeSource, piste
from webradio.core.clock import HorlogeFigee
from webradio.core.controle import Commande, Controle, Nature
from webradio.core.file import File, FileVide
from webradio.core.jingles import JINGLE_ENCORE, Jingles
from webradio.core.modeles import Piste
from webradio.core.repetition import Fenetre
from webradio.core.rng import HasardScripte

BOWIE_1 = piste("1", "Bowie", "rock")
BOWIE_2 = piste("2", "Bowie", "rock")
AIR_1 = piste("3", "Air", "rock")
PORTISHEAD = piste("4", "Portishead", "trip-hop")


def jingles() -> Jingles:
    return Jingles(HorlogeFigee(datetime(2026, 8, 30, 14, 10, tzinfo=UTC)))


def controle(
    catalogue: list[Piste] | None = None,
    indices: list[int] | None = None,
    jeu: Jingles | None = None,
) -> Controle:
    pistes = [BOWIE_1, BOWIE_2, AIR_1, PORTISHEAD] if catalogue is None else catalogue
    return Controle(
        FakeSource(list(pistes)),
        HasardScripte(indices if indices is not None else [0] * 20),
        jeu if jeu is not None else jingles(),
    )


def test_un_seul_vote_suffit_a_passer_le_morceau() -> None:
    """Ni quorum, ni fenêtre de dépouillement (SPECS.md §7 n°10)."""
    c = controle()
    assert c.voter(Commande.STOP).accepte
    assert c.reclamer_saut()
    assert not c.reclamer_saut()


def test_un_encore_accepte_marque_le_jingle_de_vote_comme_du() -> None:
    jeu = jingles()
    c = controle(jeu=jeu)
    assert c.voter(Commande.ENCORE).accepte
    assert c.reclamer_encore()
    assert jeu.dus() == (JINGLE_ENCORE,)


def test_encore_ne_porte_que_sur_le_morceau_suivant() -> None:
    """Il n'installe pas un mode (SPECS.md §4.6) : une fois honoré, il s'éteint."""
    c = controle()
    c.voter(Commande.ENCORE)
    assert c.reclamer_encore()
    assert not c.reclamer_encore()


@pytest.mark.parametrize(
    ("nature", "attendu"),
    [
        (Nature.JINGLE, "jingle"),
        (Nature.FLASH, "flash"),
        (Nature.EMISSION, "émission"),
    ],
)
def test_un_vote_pendant_autre_chose_que_la_musique_est_refuse_avec_son_motif(
    nature: Nature, attendu: str
) -> None:
    """Un refus muet est indistinguable d'une panne, et pousse à réessayer."""
    c = controle()
    c.declarer(nature)
    reponse = c.voter(Commande.STOP)
    assert not reponse.accepte
    assert attendu in reponse.motif


def test_un_vote_refuse_n_est_ni_mis_en_attente_ni_applique_en_douce() -> None:
    """Les deux seraient des surprises (SPECS.md §4.6)."""
    jeu = jingles()
    c = controle(jeu=jeu)
    c.declarer(Nature.EMISSION)
    assert not c.voter(Commande.ENCORE).accepte
    c.declarer(Nature.MUSIQUE)
    assert not c.reclamer_encore()
    assert jeu.dus() == ()


def test_le_vote_redevient_possible_des_que_la_musique_revient() -> None:
    c = controle()
    c.declarer(Nature.JINGLE)
    assert not c.voter(Commande.STOP).accepte
    c.declarer(Nature.MUSIQUE)
    assert c.nature is Nature.MUSIQUE
    assert c.voter(Commande.STOP).accepte


def test_encore_sert_un_autre_morceau_du_meme_artiste() -> None:
    choix = controle().morceau_apres_encore(BOWIE_1)
    assert choix.piste == BOWIE_2
    assert choix.replis == ()


def test_encore_outrepasse_la_non_repetition() -> None:
    """Les deux se contrediraient sinon : l'une réclame le même artiste,
    l'autre le lui interdit. C'est `encore` qui gagne (SPECS.md §7 n°7)."""
    fenetre = Fenetre(largeur=5)
    fenetre.retenir(BOWIE_1)
    assert not fenetre.autorise(BOWIE_2)
    assert controle().morceau_apres_encore(BOWIE_1).piste == BOWIE_2


def test_les_morceaux_servis_par_encore_n_entrent_pas_dans_la_fenetre() -> None:
    """Sans cela, un long enchaînement condamnerait l'artiste pour longtemps
    après (SPECS.md §4.6). La fenêtre est nourrie par la file, pas par `encore`."""
    source = FakeSource([BOWIE_1, BOWIE_2, AIR_1, PORTISHEAD])
    fenetre = Fenetre(largeur=5)
    file = File(source, HasardScripte([0]), fenetre)
    file.suivant()
    avant = fenetre.artistes
    c = Controle(source, HasardScripte([0, 0]), jingles())
    c.morceau_apres_encore(BOWIE_1)
    assert fenetre.artistes == avant


def test_un_artiste_epuise_se_replie_sur_le_genre() -> None:
    """Ce qui borne `encore` est la bibliothèque : quand Bowie n'a plus de
    morceau non joué, on descend d'un cran (SPECS.md §4.6)."""
    c = controle()
    c.morceau_apres_encore(BOWIE_1)
    c.morceau_apres_encore(BOWIE_2)
    choix = c.morceau_apres_encore(BOWIE_1)
    assert choix.piste == AIR_1
    assert choix.replis == ("artiste « Bowie » épuisé",)


def test_un_genre_epuise_se_replie_sur_le_tirage_libre() -> None:
    c = controle()
    c.morceau_apres_encore(BOWIE_1)
    c.morceau_apres_encore(BOWIE_2)
    c.morceau_apres_encore(BOWIE_1)
    choix = c.morceau_apres_encore(AIR_1)
    assert choix.piste == PORTISHEAD
    assert choix.replis == ("artiste « Air » épuisé", "genre « rock » épuisé : tirage libre")


def test_un_morceau_sans_genre_se_replie_directement_sur_le_tirage_libre() -> None:
    solo = piste("9", "Solo", None)
    c = controle([solo, PORTISHEAD])
    choix = c.morceau_apres_encore(solo)
    assert choix.piste == PORTISHEAD
    assert choix.replis == ("artiste « Solo » épuisé", "morceau sans genre : tirage libre")


def test_une_bibliotheque_entierement_servie_ne_fait_pas_taire_la_radio() -> None:
    """« Une radio ne se tait pas » (SPECS.md §5.1) : la chaîne d'`encore`
    repart plutôt que de rendre le silence."""
    c = controle([BOWIE_1])
    choix = c.morceau_apres_encore(BOWIE_1)
    assert choix.piste == BOWIE_1
    assert "la chaîne repart" in choix.replis[-1]


def test_encore_s_enchaine_sans_limite_borne_par_la_bibliotheque() -> None:
    """Aucun compteur, aucun plafond (SPECS.md §7 n°7) : ce qui borne est la
    bibliothèque, et elle n'arrête jamais la radio."""
    c = controle(indices=[0] * 30)
    courant = BOWIE_1
    for _ in range(20):
        courant = c.morceau_apres_encore(courant).piste
    assert courant.identifiant in {"1", "2", "3", "4"}


def test_une_source_vide_refuse_de_servir_un_encore() -> None:
    """Distinct d'une source injoignable : ici elle a répondu, elle n'a rien."""
    c = Controle(FakeSource([]), HasardScripte([0]), jingles())
    with pytest.raises(FileVide, match="aucune piste"):
        c.morceau_apres_encore(BOWIE_1)
