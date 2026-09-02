"""Les émissions : quelle case est ouverte, et quel épisode elle diffuse."""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.shows import (
    ConflictingShows,
    Episode,
    Show,
    ShowSchedule,
    episode_to_air,
)

UNE_HEURE = timedelta(hours=1)
# 2026-08-30 est un dimanche ; le 2026-09-04 est un vendredi.
VENDREDI = datetime(2026, 9, 4, tzinfo=UTC)

FRENCH = Show(name="A la French", days=("friday",), hour=time(20))
LEGEND = Show(name="LEGEND", days=("tuesday", "thursday"), hour=time(21))
QUOTIDIENNE = Show(name="Quotidienne", days=("all",), hour=time(12))


def le_vendredi(hour: int, minute: int = 0) -> datetime:
    return VENDREDI.replace(hour=hour, minute=minute)


def test_une_emission_declaree_a_ses_jours_et_pas_aux_autres() -> None:
    assert FRENCH.a_lieu_le(VENDREDI.date())
    assert not FRENCH.a_lieu_le(VENDREDI.date() + timedelta(days=1))
    assert QUOTIDIENNE.a_lieu_le(VENDREDI.date())


def test_deux_emissions_a_la_meme_heure_le_meme_jour_refusent_le_demarrage() -> None:
    """La radio ne choisit pas à la place de l'utilisateur (SPECS.md §4.11) : le
    message nomme les deux émissions."""
    jumelle = Show(name="Doublon", days=("friday", "saturday"), hour=time(20))
    with pytest.raises(ConflictingShows) as leve:
        ShowSchedule([FRENCH, jumelle])
    assert "A la French" in str(leve.value)
    assert "Doublon" in str(leve.value)


def test_une_emission_quotidienne_entre_en_conflit_avec_n_importe_quel_jour() -> None:
    concurrente = Show(name="Midi pile", days=("wednesday",), hour=time(12))
    with pytest.raises(ConflictingShows, match="Midi pile"):
        ShowSchedule([QUOTIDIENNE, concurrente])


def test_deux_emissions_a_des_heures_differentes_ne_se_chevauchent_pas() -> None:
    """Le chevauchement se juge sur la case déclarée, pas sur la durée réelle."""
    assert ShowSchedule([FRENCH, LEGEND]).shows == (FRENCH, LEGEND)


def test_deux_emissions_le_meme_jour_a_des_jours_disjoints_sont_acceptees() -> None:
    autre = Show(name="Autre", days=("saturday",), hour=time(20))
    assert len(ShowSchedule([FRENCH, autre]).shows) == 2


def test_une_emission_est_due_a_son_heure() -> None:
    programme = ShowSchedule([FRENCH])
    case = programme.due({"A la French": UNE_HEURE}, le_vendredi(20))
    assert case is not None
    assert case.show is FRENCH
    assert case.start == le_vendredi(20)


def test_une_emission_manquee_est_rattrapee_depuis_le_debut() -> None:
    """Branché à 20 h 40, l'épisode d'une heure démarre au début et finit à
    21 h 40 : le rattrapage décale la fin (SPECS.md §7 n°13)."""
    case = ShowSchedule([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(20, 40))
    assert case is not None
    assert case.start == le_vendredi(20)


def test_une_emission_manquee_au_dela_de_sa_duree_est_perdue() -> None:
    assert ShowSchedule([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(21, 10)) is None


def test_une_emission_dont_le_flux_est_injoignable_n_est_pas_rattrapee() -> None:
    """La durée n'est connue qu'après lecture du flux : sans elle, pas de
    rattrapage, la radio démarre sur la musique."""
    assert ShowSchedule([FRENCH]).due({}, le_vendredi(20, 10)) is None


def test_une_case_de_fin_de_soiree_reste_ouverte_apres_minuit() -> None:
    tardive = Show(name="Tardive", days=("friday",), hour=time(23, 30))
    case = ShowSchedule([tardive]).due(
        {"Tardive": timedelta(hours=2)},
        le_vendredi(23, 30) + timedelta(minutes=45),
    )
    assert case is not None
    assert case.start == le_vendredi(23, 30)


def test_aucune_case_ouverte_avant_l_heure_declaree() -> None:
    assert ShowSchedule([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(19, 59)) is None


def test_aucune_case_ouverte_un_jour_ou_l_emission_n_a_pas_lieu() -> None:
    samedi = le_vendredi(20) + timedelta(days=1)
    assert ShowSchedule([FRENCH]).due({"A la French": UNE_HEURE}, samedi) is None


def test_deux_cases_qui_se_recouvrent_par_la_duree_laissent_finir_la_premiere() -> None:
    """C'est la même règle que pour les plages thématiques : ne rien couper."""
    tardive = Show(name="Tardive", days=("friday",), hour=time(20, 30))
    programme = ShowSchedule([tardive, FRENCH])
    case = programme.due(
        {"A la French": timedelta(hours=2), "Tardive": UNE_HEURE},
        le_vendredi(20, 40),
    )
    assert case is not None
    assert case.show is FRENCH


def test_une_emission_sans_nom_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans nom"):
        Show(name="", days=("monday",), hour=time(20))


def test_une_emission_sans_jour_est_refusee() -> None:
    with pytest.raises(ValueError, match="aucun jour"):
        Show(name="Fantôme", days=(), hour=time(20))


def test_un_jour_inconnu_est_refuse_en_nommant_l_emission() -> None:
    with pytest.raises(ValueError, match="jour inconnu pour « Fantôme » : lundy"):
        Show(name="Fantôme", days=("lundy",), hour=time(20))


def episode(guid: str, jour: int, kind: str = "full") -> Episode:
    return Episode(
        guid=guid,
        published_at=datetime(2026, 8, jour, tzinfo=UTC),
        duration=UNE_HEURE,
        kind=kind,
    )


def test_l_episode_le_plus_recent_est_retenu() -> None:
    retenu = episode_to_air([episode("vieux", 1), episode("neuf", 20)])
    assert retenu is not None
    assert retenu.guid == "neuf"


def test_un_bonus_ou_un_trailer_n_est_pas_l_emission() -> None:
    """Une bande-annonce d'une minute trente ne doit pas passer à l'heure de
    l'émission (SPECS.md §7 n°14)."""
    retenu = episode_to_air(
        [
            episode("complet", 10),
            episode("cadeau", 25, kind="bonus"),
            episode("annonce", 28, kind="trailer"),
        ]
    )
    assert retenu is not None
    assert retenu.guid == "complet"


def test_un_episode_deja_diffuse_fait_sauter_la_case() -> None:
    """Une émission sans épisode neuf n'a pas lieu ; on ne redescend pas à
    l'avant-dernier, ce serait une rediffusion."""
    episodes = [episode("vieux", 1), episode("neuf", 20)]
    assert episode_to_air(episodes, already_aired="neuf") is None


def test_un_episode_retire_du_flux_ne_bloque_rien() -> None:
    """L'identifiant retenu ne correspond plus à rien : le plus récent est
    différent, donc diffusé (SPECS.md §4.11.1)."""
    retenu = episode_to_air([episode("neuf", 20)], already_aired="disparu")
    assert retenu is not None
    assert retenu.guid == "neuf"


def test_un_flux_sans_aucun_episode_complet_ne_diffuse_rien() -> None:
    assert episode_to_air([episode("annonce", 28, kind="trailer")]) is None
    assert episode_to_air([]) is None


def test_une_semaine_entiere_se_deroule_en_une_boucle_et_se_rejoue() -> None:
    """Horloge figée : sept jours se rejouent à l'identique."""

    def semaine() -> list[str]:
        programme = ShowSchedule([FRENCH, LEGEND, QUOTIDIENNE])
        durations = {"A la French": UNE_HEURE, "LEGEND": UNE_HEURE, "Quotidienne": UNE_HEURE}
        instant = datetime(2026, 8, 31, tzinfo=UTC)
        vues: list[str] = []
        for _ in range(7 * 24):
            case = programme.due(durations, instant)
            if case is not None:
                vues.append(f"{instant:%a %H}h {case.show.name}")
            instant += UNE_HEURE
        return vues

    premiere = semaine()
    assert premiere == semaine()
    assert sum(1 for v in premiere if "Quotidienne" in v) == 7
    assert sum(1 for v in premiere if "LEGEND" in v) == 2
    assert sum(1 for v in premiere if "A la French" in v) == 1


# ── Les directs (SPECS.md §7 n°22, GOAL-015) ────────────────────────────────

FLASH = Show(name="Flash", days=("all",), hour=time(12), duration=timedelta(minutes=9))


def test_un_direct_porte_sa_duree_et_le_dit() -> None:
    assert FLASH.is_live
    assert not QUOTIDIENNE.is_live


def test_un_direct_sans_duree_est_refuse() -> None:
    with pytest.raises(ValueError, match="durée nulle"):
        Show(name="Vide", days=("all",), hour=time(12), duration=timedelta(0))


def test_la_case_d_un_direct_est_ouverte_tant_qu_il_en_reste() -> None:
    grille = ShowSchedule([FLASH])
    case = grille.due({}, le_vendredi(12, 4))
    assert case is not None
    assert case.show is FLASH
    assert case.end == le_vendredi(12, 9)


def test_la_case_d_un_direct_se_ferme_a_la_seconde_declaree() -> None:
    grille = ShowSchedule([FLASH])
    assert grille.due({}, le_vendredi(12, 9)) is None


def test_un_podcast_n_a_pas_de_fin_connue_d_avance() -> None:
    grille = ShowSchedule([QUOTIDIENNE])
    case = grille.due({"Quotidienne": timedelta(minutes=30)}, le_vendredi(12, 4))
    assert case is not None
    assert case.end is None
