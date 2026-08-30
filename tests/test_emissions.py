"""Les émissions : quelle case est ouverte, et quel épisode elle diffuse."""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.emissions import (
    Emission,
    EmissionsEnConflit,
    Episode,
    GrilleDesEmissions,
    episode_a_diffuser,
)

UNE_HEURE = timedelta(hours=1)
# 2026-08-30 est un dimanche ; le 2026-09-04 est un vendredi.
VENDREDI = datetime(2026, 9, 4, tzinfo=UTC)

FRENCH = Emission(nom="A la French", jours=("vendredi",), heure=time(20))
LEGEND = Emission(nom="LEGEND", jours=("mardi", "jeudi"), heure=time(21))
QUOTIDIENNE = Emission(nom="Quotidienne", jours=("tous",), heure=time(12))


def le_vendredi(heure: int, minute: int = 0) -> datetime:
    return VENDREDI.replace(hour=heure, minute=minute)


def test_une_emission_declaree_a_ses_jours_et_pas_aux_autres() -> None:
    assert FRENCH.a_lieu_le(VENDREDI.date())
    assert not FRENCH.a_lieu_le(VENDREDI.date() + timedelta(days=1))
    assert QUOTIDIENNE.a_lieu_le(VENDREDI.date())


def test_deux_emissions_a_la_meme_heure_le_meme_jour_refusent_le_demarrage() -> None:
    """La radio ne choisit pas à votre place et ne joue pas la première venue
    (SPECS.md §4.11) : elle les nomme toutes les deux."""
    jumelle = Emission(nom="Doublon", jours=("vendredi", "samedi"), heure=time(20))
    with pytest.raises(EmissionsEnConflit) as leve:
        GrilleDesEmissions([FRENCH, jumelle])
    assert "A la French" in str(leve.value)
    assert "Doublon" in str(leve.value)


def test_une_emission_quotidienne_entre_en_conflit_avec_n_importe_quel_jour() -> None:
    concurrente = Emission(nom="Midi pile", jours=("mercredi",), heure=time(12))
    with pytest.raises(EmissionsEnConflit, match="Midi pile"):
        GrilleDesEmissions([QUOTIDIENNE, concurrente])


def test_deux_emissions_a_des_heures_differentes_ne_se_chevauchent_pas() -> None:
    """Le chevauchement se juge sur la case déclarée, pas sur la durée réelle."""
    assert GrilleDesEmissions([FRENCH, LEGEND]).emissions == (FRENCH, LEGEND)


def test_deux_emissions_le_meme_jour_a_des_jours_disjoints_sont_acceptees() -> None:
    autre = Emission(nom="Autre", jours=("samedi",), heure=time(20))
    assert len(GrilleDesEmissions([FRENCH, autre]).emissions) == 2


def test_une_emission_est_due_a_son_heure() -> None:
    programme = GrilleDesEmissions([FRENCH])
    case = programme.due({"A la French": UNE_HEURE}, le_vendredi(20))
    assert case is not None
    assert case.emission is FRENCH
    assert case.debut == le_vendredi(20)


def test_une_emission_manquee_est_rattrapee_depuis_le_debut() -> None:
    """Branché à 20 h 40, l'épisode d'une heure démarre au début et finit à
    21 h 40 : le rattrapage décale sa propre fin (SPECS.md §7 n°13)."""
    case = GrilleDesEmissions([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(20, 40))
    assert case is not None
    assert case.debut == le_vendredi(20)


def test_une_emission_manquee_au_dela_de_sa_duree_est_perdue() -> None:
    assert GrilleDesEmissions([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(21, 10)) is None


def test_une_emission_dont_le_flux_est_injoignable_n_est_pas_rattrapee() -> None:
    """La durée n'est connue qu'après lecture du flux : sans elle, pas de
    rattrapage — la radio démarre sur la musique."""
    assert GrilleDesEmissions([FRENCH]).due({}, le_vendredi(20, 10)) is None


def test_une_case_de_fin_de_soiree_reste_ouverte_apres_minuit() -> None:
    tardive = Emission(nom="Tardive", jours=("vendredi",), heure=time(23, 30))
    case = GrilleDesEmissions([tardive]).due(
        {"Tardive": timedelta(hours=2)},
        le_vendredi(23, 30) + timedelta(minutes=45),
    )
    assert case is not None
    assert case.debut == le_vendredi(23, 30)


def test_aucune_case_ouverte_avant_l_heure_declaree() -> None:
    assert GrilleDesEmissions([FRENCH]).due({"A la French": UNE_HEURE}, le_vendredi(19, 59)) is None


def test_aucune_case_ouverte_un_jour_ou_l_emission_n_a_pas_lieu() -> None:
    samedi = le_vendredi(20) + timedelta(days=1)
    assert GrilleDesEmissions([FRENCH]).due({"A la French": UNE_HEURE}, samedi) is None


def test_deux_cases_qui_se_recouvrent_par_la_duree_laissent_finir_la_premiere() -> None:
    """C'est la même règle que pour les plages thématiques : ne rien couper."""
    tardive = Emission(nom="Tardive", jours=("vendredi",), heure=time(20, 30))
    programme = GrilleDesEmissions([tardive, FRENCH])
    case = programme.due(
        {"A la French": timedelta(hours=2), "Tardive": UNE_HEURE},
        le_vendredi(20, 40),
    )
    assert case is not None
    assert case.emission is FRENCH


def test_une_emission_sans_nom_est_refusee() -> None:
    with pytest.raises(ValueError, match="sans nom"):
        Emission(nom="", jours=("lundi",), heure=time(20))


def test_une_emission_sans_jour_est_refusee() -> None:
    with pytest.raises(ValueError, match="aucun jour"):
        Emission(nom="Fantôme", jours=(), heure=time(20))


def test_un_jour_inconnu_est_refuse_en_nommant_l_emission() -> None:
    with pytest.raises(ValueError, match="jour inconnu pour « Fantôme » : lundy"):
        Emission(nom="Fantôme", jours=("lundy",), heure=time(20))


def episode(guid: str, jour: int, nature: str = "full") -> Episode:
    return Episode(
        guid=guid,
        publie_le=datetime(2026, 8, jour, tzinfo=UTC),
        duree=UNE_HEURE,
        nature=nature,
    )


def test_l_episode_le_plus_recent_est_retenu() -> None:
    retenu = episode_a_diffuser([episode("vieux", 1), episode("neuf", 20)])
    assert retenu is not None
    assert retenu.guid == "neuf"


def test_un_bonus_ou_un_trailer_n_est_pas_l_emission() -> None:
    """Un podcast qui publie une bande-annonce d'une minute trente ne doit pas
    la voir passer à l'heure de son émission (SPECS.md §7 n°14)."""
    retenu = episode_a_diffuser(
        [
            episode("complet", 10),
            episode("cadeau", 25, nature="bonus"),
            episode("annonce", 28, nature="trailer"),
        ]
    )
    assert retenu is not None
    assert retenu.guid == "complet"


def test_un_episode_deja_diffuse_fait_sauter_la_case() -> None:
    """Une émission qui n'a rien de neuf est une émission qui n'a pas lieu —
    et on ne redescend pas à l'avant-dernier, ce serait une rediffusion de plus."""
    episodes = [episode("vieux", 1), episode("neuf", 20)]
    assert episode_a_diffuser(episodes, deja_diffuse="neuf") is None


def test_un_episode_retire_du_flux_ne_bloque_rien() -> None:
    """L'identifiant retenu ne correspond plus à rien, donc le plus récent est
    forcément différent, donc il est diffusé (SPECS.md §4.11.1)."""
    retenu = episode_a_diffuser([episode("neuf", 20)], deja_diffuse="disparu")
    assert retenu is not None
    assert retenu.guid == "neuf"


def test_un_flux_sans_aucun_episode_complet_ne_diffuse_rien() -> None:
    assert episode_a_diffuser([episode("annonce", 28, nature="trailer")]) is None
    assert episode_a_diffuser([]) is None


def test_une_semaine_entiere_se_deroule_en_une_boucle_et_se_rejoue() -> None:
    """Horloge figée : sept jours de programmation en quelques millisecondes."""

    def semaine() -> list[str]:
        programme = GrilleDesEmissions([FRENCH, LEGEND, QUOTIDIENNE])
        durees = {"A la French": UNE_HEURE, "LEGEND": UNE_HEURE, "Quotidienne": UNE_HEURE}
        instant = datetime(2026, 8, 31, tzinfo=UTC)
        vues: list[str] = []
        for _ in range(7 * 24):
            case = programme.due(durees, instant)
            if case is not None:
                vues.append(f"{instant:%a %H}h {case.emission.nom}")
            instant += UNE_HEURE
        return vues

    premiere = semaine()
    assert premiere == semaine()
    assert sum(1 for v in premiere if "Quotidienne" in v) == 7
    assert sum(1 for v in premiere if "LEGEND" in v) == 2
    assert sum(1 for v in premiere if "A la French" in v) == 1
