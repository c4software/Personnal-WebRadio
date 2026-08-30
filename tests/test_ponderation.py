"""La pondération : des scores de votes au multiplicateur, et ses bornes."""

from datetime import timedelta

import pytest

from webradio.core.controle import Commande
from webradio.core.ponderation import (
    DEMI_VIE_PAR_DEFAUT,
    PLAFOND_PAR_DEFAUT,
    PLANCHER_PAR_DEFAUT,
    Portee,
    Scores,
    decroitre,
    enregistrer,
    multiplicateur,
    poids_de_la_piste,
    poids_du_vote,
)

TROIS_MOIS = timedelta(days=90)


def test_la_demi_vie_par_defaut_est_de_trois_mois() -> None:
    assert DEMI_VIE_PAR_DEFAUT == TROIS_MOIS


def test_un_stop_compte_plein_sur_la_piste_et_un_quart_sur_l_artiste() -> None:
    """On passe un morceau, on redemande un artiste (SPECS.md §7 n°16)."""
    assert poids_du_vote(Commande.STOP, Portee.PISTE) == 1.0
    assert poids_du_vote(Commande.STOP, Portee.ARTISTE) == 0.25


def test_un_encore_compte_plein_sur_l_artiste_et_un_quart_sur_la_piste() -> None:
    assert poids_du_vote(Commande.ENCORE, Portee.ARTISTE) == 1.0
    assert poids_du_vote(Commande.ENCORE, Portee.PISTE) == 0.25


def test_un_vote_d_hier_compte_encore_plein() -> None:
    assert decroitre(1.0, timedelta(days=1)) == pytest.approx(0.992, abs=0.001)


def test_un_vote_de_trois_mois_compte_moitie() -> None:
    assert decroitre(1.0, TROIS_MOIS) == pytest.approx(0.5)


def test_un_vote_d_un_an_ne_compte_presque_plus() -> None:
    """C'est ce qui empêche la pondération de se retourner contre elle-même :
    sans oubli, la radio se fige sur le premier mois d'usage."""
    assert decroitre(1.0, timedelta(days=365)) == pytest.approx(0.06, abs=0.01)


def test_une_duree_negative_est_refusee() -> None:
    with pytest.raises(ValueError, match="le temps ne recule pas"):
        decroitre(1.0, timedelta(days=-1))


def test_une_demi_vie_nulle_est_refusee() -> None:
    with pytest.raises(ValueError, match="demi-vie"):
        decroitre(1.0, timedelta(days=1), timedelta(0))


def test_la_decroissance_precede_le_vote_nouveau() -> None:
    """Ajouter d'abord ferait vieillir le vote qu'on vient de recevoir, et douze
    `stop` dont un seul est récent compteraient tous comme frais."""
    assert enregistrer(1.0, TROIS_MOIS, 1.0) == pytest.approx(1.5)


def test_un_increment_negatif_est_refuse() -> None:
    with pytest.raises(ValueError, match="un vote n'enlève rien"):
        enregistrer(1.0, timedelta(0), -1.0)


def test_sans_aucun_vote_le_multiplicateur_est_neutre() -> None:
    assert multiplicateur(Scores()) == 1.0


def test_les_ordres_de_grandeur_annonces_sont_tenus() -> None:
    """SPECS.md §4.12 : un `stop` récent vaut environ 0,7 fois la chance
    normale, trois environ 0,4 ; un `encore` récent 1,5, trois 2,5."""
    assert multiplicateur(Scores(stop=1)) == pytest.approx(0.7, abs=0.05)
    assert multiplicateur(Scores(stop=3)) == pytest.approx(0.4, abs=0.05)
    assert multiplicateur(Scores(encore=1)) == pytest.approx(1.5, abs=0.05)
    assert multiplicateur(Scores(encore=3)) == pytest.approx(2.5, abs=0.05)


def test_le_plancher_n_est_jamais_zero() -> None:
    """Rien n'est jamais supprimé : c'est la différence entre une radio qui
    apprend et une radio qui se rétrécit (SPECS.md §7 n°17)."""
    assert multiplicateur(Scores(stop=1000)) == PLANCHER_PAR_DEFAUT
    assert PLANCHER_PAR_DEFAUT > 0


def test_le_plafond_empeche_un_artiste_de_saturer_la_radio() -> None:
    assert multiplicateur(Scores(encore=1000)) == PLAFOND_PAR_DEFAUT


def test_les_deux_votes_se_compensent() -> None:
    assert multiplicateur(Scores(stop=2, encore=2)) == 1.0


def test_un_plancher_nul_est_refuse() -> None:
    with pytest.raises(ValueError, match="plancher nul"):
        multiplicateur(Scores(), plancher=0.0)


def test_un_plafond_sous_le_plancher_est_refuse() -> None:
    with pytest.raises(ValueError, match="sous le plancher"):
        multiplicateur(Scores(), plancher=0.5, plafond=0.4)


def test_un_score_negatif_est_refuse() -> None:
    with pytest.raises(ValueError, match="ne peut pas être négatif"):
        Scores(stop=-1)
    with pytest.raises(ValueError, match="ne peut pas être négatif"):
        Scores(encore=-1)


def test_les_deux_portees_s_additionnent_avant_d_etre_bornees() -> None:
    """Multiplier deux multiplicateurs déjà bornés aurait donné [0,0625 ; 16],
    quatre fois plus loin que ce que la décision n°17 autorise."""
    assert poids_de_la_piste(Scores(stop=1), Scores(stop=1)) == multiplicateur(Scores(stop=2))
    assert poids_de_la_piste(Scores(stop=100), Scores(stop=100)) == PLANCHER_PAR_DEFAUT
    assert poids_de_la_piste(Scores(encore=100), Scores(encore=100)) == PLAFOND_PAR_DEFAUT


def test_dix_stop_sur_des_titres_differents_du_meme_artiste_finissent_par_se_voir() -> None:
    """Le poids croisé est ce qui fait qu'un signal répété porte (SPECS.md §4.12)."""
    artiste = Scores(stop=10 * poids_du_vote(Commande.STOP, Portee.ARTISTE))
    assert poids_de_la_piste(Scores(), artiste) < 0.5


def test_un_titre_passe_puis_oublie_revient_a_la_normale() -> None:
    """Trois `stop` d'il y a un an ne doivent presque plus se voir."""
    frais = Scores(stop=3.0)
    vieilli = Scores(stop=decroitre(3.0, timedelta(days=365)))
    assert multiplicateur(frais) == pytest.approx(0.4)
    assert multiplicateur(vieilli) == pytest.approx(1.0, abs=0.1)
