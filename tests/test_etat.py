"""L'état durable : ce qu'il retient, ce qu'il oublie, et ce qu'il refuse.

Chaque test travaille sur **son propre fichier temporaire** : une base partagée
entre tests ferait dépendre l'un de l'ordre d'exécution de l'autre.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from webradio.adapters.etat import EtatIndisponible, EtatSQLite, Portee
from webradio.core.clock import HorlogeFigee

DEPART = datetime(2026, 8, 30, 20, 0, tzinfo=UTC)
ATTENTE = timedelta(seconds=5)
DEMI_VIE = timedelta(days=90)


def etat(chemin: Path, horloge: HorlogeFigee) -> EtatSQLite:
    return EtatSQLite(chemin, horloge, delai_attente=ATTENTE, demi_vie_votes=DEMI_VIE)


def test_une_base_absente_se_cree_toute_seule(tmp_path: Path) -> None:
    """Perdre la base n'est pas une panne (ARCHITECTURE.md §5.0)."""
    chemin = tmp_path / "sous-dossier" / "etat.sqlite"
    etat(chemin, HorlogeFigee(DEPART))
    assert chemin.exists()


def test_une_base_vide_ne_connait_aucune_diffusion(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    assert e.derniere_diffusion("LEGEND") is None


def test_le_dernier_episode_diffuse_se_relit(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    e.enregistrer_diffusion("LEGEND", "guid-42")
    diffusion = e.derniere_diffusion("LEGEND")
    assert diffusion is not None
    assert diffusion.episode == "guid-42"
    assert diffusion.diffuse_le == DEPART


def test_une_nouvelle_diffusion_remplace_la_precedente(tmp_path: Path) -> None:
    """Un identifiant par émission, jamais un historique (ARCHITECTURE.md §5.0)."""
    horloge = HorlogeFigee(DEPART)
    e = etat(tmp_path / "etat.sqlite", horloge)
    e.enregistrer_diffusion("LEGEND", "guid-1")
    horloge.avancer(timedelta(days=7))
    e.enregistrer_diffusion("LEGEND", "guid-2")
    diffusion = e.derniere_diffusion("LEGEND")
    assert diffusion is not None
    assert diffusion.episode == "guid-2"


def test_deux_emissions_ne_se_melangent_pas(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    e.enregistrer_diffusion("LEGEND", "guid-legend")
    e.enregistrer_diffusion("A la French", "guid-french")
    legend = e.derniere_diffusion("LEGEND")
    french = e.derniere_diffusion("A la French")
    assert legend is not None
    assert french is not None
    assert (legend.episode, french.episode) == ("guid-legend", "guid-french")


def test_l_etat_survit_a_la_fermeture_du_programme(tmp_path: Path) -> None:
    """Deux processus vivants lisent la même base (ARCHITECTURE.md §5.1)."""
    chemin = tmp_path / "etat.sqlite"
    etat(chemin, HorlogeFigee(DEPART)).enregistrer_diffusion("LEGEND", "guid-42")
    relu = etat(chemin, HorlogeFigee(DEPART)).derniere_diffusion("LEGEND")
    assert relu is not None
    assert relu.episode == "guid-42"


def test_une_base_vide_rend_des_scores_neutres(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    scores = e.scores(Portee.PISTE, "inconnue")
    assert (scores.stop, scores.encore) == (0.0, 0.0)


def test_un_vote_s_ajoute_au_score_de_sa_cible(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    assert e.scores(Portee.PISTE, "piste-1").stop == pytest.approx(2.0)


def test_un_vote_porte_sur_la_piste_et_sur_l_artiste_separement(tmp_path: Path) -> None:
    """SPECS.md §4.12 : le barème est décidé au-dessus, la base additionne."""
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    e.enregistrer_vote(Portee.ARTISTE, "Bowie", stop=0.25)
    assert e.scores(Portee.PISTE, "piste-1").stop == pytest.approx(1.0)
    assert e.scores(Portee.ARTISTE, "Bowie").stop == pytest.approx(0.25)


def test_deux_portees_de_meme_nom_ne_se_confondent_pas(tmp_path: Path) -> None:
    e = etat(tmp_path / "etat.sqlite", HorlogeFigee(DEPART))
    e.enregistrer_vote(Portee.PISTE, "Bowie", encore=1.0)
    assert e.scores(Portee.ARTISTE, "Bowie").encore == pytest.approx(0.0)


def test_un_score_perd_la_moitie_de_son_poids_en_une_demi_vie(tmp_path: Path) -> None:
    """La décroissance vaut **à la lecture** (ARCHITECTURE.md §5.2)."""
    horloge = HorlogeFigee(DEPART)
    e = etat(tmp_path / "etat.sqlite", horloge)
    e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    horloge.avancer(DEMI_VIE)
    assert e.scores(Portee.PISTE, "piste-1").stop == pytest.approx(0.5)


def test_un_vote_ancien_ne_repasse_pas_pour_frais_quand_un_nouveau_arrive(
    tmp_path: Path,
) -> None:
    """Le piège que les compteurs entiers auraient laissé passer.

    Avec `stops INTEGER` et une seule date, deux `stop` à trois mois d'écart
    compteraient tous les deux comme frais : 2 au lieu de 1,5.
    """
    horloge = HorlogeFigee(DEPART)
    e = etat(tmp_path / "etat.sqlite", horloge)
    e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    horloge.avancer(DEMI_VIE)
    nouveaux = e.enregistrer_vote(Portee.PISTE, "piste-1", stop=1.0)
    assert nouveaux.stop == pytest.approx(1.5)
    assert e.scores(Portee.PISTE, "piste-1").stop == pytest.approx(1.5)


def test_un_score_ne_grossit_pas_si_l_horloge_recule(tmp_path: Path) -> None:
    """Une base recopiée d'une autre machine ne doit pas amplifier un vote."""
    chemin = tmp_path / "etat.sqlite"
    futur = etat(chemin, HorlogeFigee(DEPART + timedelta(days=365)))
    futur.enregistrer_vote(Portee.PISTE, "piste-1", encore=1.0)
    passe = etat(chemin, HorlogeFigee(DEPART))
    assert passe.scores(Portee.PISTE, "piste-1").encore == pytest.approx(1.0)


def test_un_delai_d_attente_nul_est_refuse(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="délai d'attente"):
        EtatSQLite(
            tmp_path / "etat.sqlite",
            HorlogeFigee(DEPART),
            delai_attente=timedelta(0),
            demi_vie_votes=DEMI_VIE,
        )


def test_une_demi_vie_nulle_est_refusee(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="demi-vie"):
        EtatSQLite(
            tmp_path / "etat.sqlite",
            HorlogeFigee(DEPART),
            delai_attente=ATTENTE,
            demi_vie_votes=timedelta(0),
        )


def test_un_fichier_qui_n_est_pas_une_base_est_signale(tmp_path: Path) -> None:
    """Une erreur technique devient une erreur métier (ARCHITECTURE.md §7)."""
    chemin = tmp_path / "etat.sqlite"
    chemin.write_bytes(b"ceci n'est pas une base de donnees")
    with pytest.raises(EtatIndisponible, match="illisible"):
        etat(chemin, HorlogeFigee(DEPART))


def test_un_chemin_impossible_a_ouvrir_est_signale(tmp_path: Path) -> None:
    dossier = tmp_path / "etat.sqlite"
    dossier.mkdir()
    with pytest.raises(EtatIndisponible, match="inaccessible"):
        etat(dossier, HorlogeFigee(DEPART))
