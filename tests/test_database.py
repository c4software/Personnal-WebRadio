"""L'état durable : ce qu'il retient, ce qu'il oublie, et ce qu'il refuse.

Chaque test travaille sur **son propre fichier temporaire** : une base partagée
entre tests ferait dépendre l'un de l'ordre d'exécution de l'autre.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from webradio.adapters.state import Scope, SqliteState, StateUnavailable
from webradio.core.clock import FrozenClock

DEPART = datetime(2026, 8, 30, 20, 0, tzinfo=UTC)
ATTENTE = timedelta(seconds=5)
DEMI_VIE = timedelta(days=90)


def state(path: Path, clock: FrozenClock) -> SqliteState:
    return SqliteState(path, clock, lock_timeout=ATTENTE, vote_half_life=DEMI_VIE)


def test_une_base_absente_se_cree_toute_seule(tmp_path: Path) -> None:
    """Perdre la base n'est pas une panne (ARCHITECTURE.md §5.0)."""
    path = tmp_path / "sous-dossier" / "etat.sqlite"
    state(path, FrozenClock(DEPART))
    assert path.exists()


def test_une_base_vide_ne_connait_aucune_diffusion(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    assert e.last_airing("LEGEND") is None


def test_le_dernier_episode_diffuse_se_relit(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_airing("LEGEND", "guid-42")
    broadcast = e.last_airing("LEGEND")
    assert broadcast is not None
    assert broadcast.episode == "guid-42"
    assert broadcast.diffuse_le == DEPART


def test_une_nouvelle_diffusion_remplace_la_precedente(tmp_path: Path) -> None:
    """Un identifiant par émission, jamais un historique (ARCHITECTURE.md §5.0)."""
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_airing("LEGEND", "guid-1")
    clock.advance(timedelta(days=7))
    e.record_airing("LEGEND", "guid-2")
    broadcast = e.last_airing("LEGEND")
    assert broadcast is not None
    assert broadcast.episode == "guid-2"


def test_deux_emissions_ne_se_melangent_pas(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_airing("LEGEND", "guid-legend")
    e.record_airing("A la French", "guid-french")
    legend = e.last_airing("LEGEND")
    french = e.last_airing("A la French")
    assert legend is not None
    assert french is not None
    assert (legend.episode, french.episode) == ("guid-legend", "guid-french")


def test_l_etat_survit_a_la_fermeture_du_programme(tmp_path: Path) -> None:
    """Deux processus vivants lisent la même base (ARCHITECTURE.md §5.1)."""
    path = tmp_path / "etat.sqlite"
    state(path, FrozenClock(DEPART)).record_airing("LEGEND", "guid-42")
    relu = state(path, FrozenClock(DEPART)).last_airing("LEGEND")
    assert relu is not None
    assert relu.episode == "guid-42"


def test_une_base_vide_rend_des_scores_neutres(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    scores = e.scores(Scope.TRACK, "inconnue")
    assert (scores.stop, scores.encore) == (0.0, 0.0)


def test_un_vote_s_ajoute_au_score_de_sa_cible(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    assert e.scores(Scope.TRACK, "piste-1").stop == pytest.approx(2.0)


def test_un_vote_porte_sur_la_piste_et_sur_l_artiste_separement(tmp_path: Path) -> None:
    """SPECS.md §4.12 : le barème est décidé au-dessus, la base additionne."""
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    e.record_vote(Scope.ARTIST, "Bowie", stop=0.25)
    assert e.scores(Scope.TRACK, "piste-1").stop == pytest.approx(1.0)
    assert e.scores(Scope.ARTIST, "Bowie").stop == pytest.approx(0.25)


def test_deux_portees_de_meme_nom_ne_se_confondent_pas(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "Bowie", encore=1.0)
    assert e.scores(Scope.ARTIST, "Bowie").encore == pytest.approx(0.0)


def test_un_score_perd_la_moitie_de_son_poids_en_une_demi_vie(tmp_path: Path) -> None:
    """La décroissance vaut **à la lecture** (ARCHITECTURE.md §5.2)."""
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    clock.advance(DEMI_VIE)
    assert e.scores(Scope.TRACK, "piste-1").stop == pytest.approx(0.5)


def test_un_vote_ancien_ne_repasse_pas_pour_frais_quand_un_nouveau_arrive(
    tmp_path: Path,
) -> None:
    """Le piège que les compteurs entiers auraient laissé passer.

    Avec `stops INTEGER` et une seule date, deux `stop` à trois mois d'écart
    compteraient tous les deux comme frais : 2 au lieu de 1,5.
    """
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    clock.advance(DEMI_VIE)
    nouveaux = e.record_vote(Scope.TRACK, "piste-1", stop=1.0)
    assert nouveaux.stop == pytest.approx(1.5)
    assert e.scores(Scope.TRACK, "piste-1").stop == pytest.approx(1.5)


def test_un_score_ne_grossit_pas_si_l_horloge_recule(tmp_path: Path) -> None:
    """Une base recopiée d'une autre machine ne doit pas amplifier un vote."""
    path = tmp_path / "etat.sqlite"
    futur = state(path, FrozenClock(DEPART + timedelta(days=365)))
    futur.record_vote(Scope.TRACK, "piste-1", encore=1.0)
    passe = state(path, FrozenClock(DEPART))
    assert passe.scores(Scope.TRACK, "piste-1").encore == pytest.approx(1.0)


def test_un_delai_d_attente_nul_est_refuse(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="délai d'attente"):
        SqliteState(
            tmp_path / "etat.sqlite",
            FrozenClock(DEPART),
            lock_timeout=timedelta(0),
            vote_half_life=DEMI_VIE,
        )


def test_une_demi_vie_nulle_est_refusee(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="demi-vie"):
        SqliteState(
            tmp_path / "etat.sqlite",
            FrozenClock(DEPART),
            lock_timeout=ATTENTE,
            vote_half_life=timedelta(0),
        )


def test_un_fichier_qui_n_est_pas_une_base_est_signale(tmp_path: Path) -> None:
    """Une erreur technique devient une erreur métier (ARCHITECTURE.md §7)."""
    path = tmp_path / "etat.sqlite"
    path.write_bytes(b"ceci n'est pas une base de donnees")
    with pytest.raises(StateUnavailable, match="illisible"):
        state(path, FrozenClock(DEPART))


def test_un_chemin_impossible_a_ouvrir_est_signale(tmp_path: Path) -> None:
    folder = tmp_path / "etat.sqlite"
    folder.mkdir()
    with pytest.raises(StateUnavailable, match="inaccessible"):
        state(folder, FrozenClock(DEPART))


# ── Tout lire pour la page des votes (GOAL-018) ─────────────────────────────


def test_all_scores_rend_tout_decroissance_comprise(tmp_path: Path) -> None:
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_vote(Scope.ARTIST, "Air", encore=2.0)
    e.record_vote(Scope.TRACK, "t1", stop=1.0)
    clock.advance(timedelta(days=90))  # une demi-vie

    tout = e.all_scores()

    assert [(scope, key) for scope, key, _, _ in tout] == [
        (Scope.ARTIST, "Air"),
        (Scope.TRACK, "t1"),
    ]
    assert tout[0][3].encore == pytest.approx(1.0)
    assert tout[1][3].stop == pytest.approx(0.5)


def test_all_scores_sans_vote_rend_une_liste_vide(tmp_path: Path) -> None:
    assert state(tmp_path / "etat.sqlite", FrozenClock(DEPART)).all_scores() == []


def test_le_libelle_est_retenu_au_vote_et_rendu_a_la_lecture(tmp_path: Path) -> None:
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "id-opaque", stop=1.0, label="Sexy Boy — Air")

    tout = e.all_scores()

    assert tout[0][1] == "id-opaque"  # la clé brute, pour l'effacement
    assert tout[0][2] == "Sexy Boy — Air"


def test_un_vote_d_avant_la_migration_garde_sa_cible_brute(tmp_path: Path) -> None:
    """La colonne arrive par migration : sans libellé, la cible reste lisible."""
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "id-opaque", stop=1.0)
    assert e.all_scores()[0][2] == "id-opaque"


def test_la_migration_ajoute_la_colonne_a_une_base_d_avant(tmp_path: Path) -> None:
    import sqlite3

    path = tmp_path / "etat.sqlite"
    brut = sqlite3.connect(path)
    with brut:
        brut.executescript(
            """
            CREATE TABLE votes (
                portee TEXT NOT NULL, cible TEXT NOT NULL,
                score_stop REAL NOT NULL DEFAULT 0, score_encore REAL NOT NULL DEFAULT 0,
                vu_le TEXT NOT NULL, PRIMARY KEY (portee, cible));
            INSERT INTO votes VALUES ('artiste', 'Air', 0, 2.0, '2026-08-30T20:00:00+00:00');
            """
        )
    brut.close()
    e = state(path, FrozenClock(DEPART))
    assert e.all_scores()[0][2] == "Air"


def test_un_vote_efface_disparait_et_le_dit(tmp_path: Path) -> None:
    """GOAL-021 : un vote donné par erreur s'efface — et une cible inconnue le dit."""
    e = state(tmp_path / "etat.sqlite", FrozenClock(DEPART))
    e.record_vote(Scope.TRACK, "t1", stop=1.0)
    assert e.delete_vote(Scope.TRACK, "t1") is True
    assert e.all_scores() == []
    assert e.delete_vote(Scope.TRACK, "t1") is False


# ── Le journal des titres (GOAL-027) ────────────────────────────────────────


def test_le_journal_rend_le_plus_recent_d_abord(tmp_path: Path) -> None:
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_play("musique", "Radiate", "Jack Johnson")
    clock.advance(timedelta(minutes=4))
    e.record_play("emission", "Alcatraz")

    journal = e.history()

    assert [(titre, artiste) for _, _, titre, artiste in journal] == [
        ("Alcatraz", ""),
        ("Radiate", "Jack Johnson"),
    ]


def test_le_journal_oublie_au_dela_d_un_jour(tmp_path: Path) -> None:
    """Un journal, pas une archive (SPECS.md §2 tient toujours) — 24 h."""
    clock = FrozenClock(DEPART)
    e = state(tmp_path / "etat.sqlite", clock)
    e.record_play("musique", "avant-hier")
    clock.advance(timedelta(hours=25))
    e.record_play("musique", "à l'instant")

    journal = e.history()

    assert [titre for _, _, titre, _ in journal] == ["à l'instant"]
