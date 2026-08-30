"""Les programmes : quand ils s'ouvrent, et ce qu'ils refusent.

Aucune infrastructure : l'horloge est figée, la semaine se déroule en une
boucle, et deux exécutions donnent le même résultat (AGENTS.md §4).
"""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.clock import HorlogeFigee
from webradio.core.programmes import JOURS, TOUS_LES_JOURS, Programmation, Programme

# Le 2026-08-28 est un vendredi ; les instants d'essai se comptent à partir de lui.
VENDREDI = datetime(2026, 8, 28, tzinfo=UTC)

CHLOE = Programme(
    nom="Le vendredi de Chloé",
    playlist="Chloé",
    jours=("vendredi",),
    debut=time(18),
    fin=time(20),
)
QUOTIDIEN = Programme(
    nom="Le réveil",
    playlist="Matin",
    jours=(TOUS_LES_JOURS,),
    debut=time(7),
    fin=time(9),
)


def a(depart: datetime, heure: int, minute: int = 0) -> HorlogeFigee:
    return HorlogeFigee(depart + timedelta(hours=heure, minutes=minute))


def test_hors_de_tout_programme_rien_n_est_ouvert() -> None:
    programmation = Programmation([CHLOE, QUOTIDIEN], a(VENDREDI, 15))

    assert programmation.programme_courant() is None
    assert programmation.playlist_a_tirer() is None


def test_un_programme_ouvre_le_jour_et_a_l_heure_declares() -> None:
    programmation = Programmation([CHLOE], a(VENDREDI, 19))

    assert programmation.programme_courant() is CHLOE
    assert programmation.playlist_a_tirer() == "Chloé"


def test_le_meme_creneau_un_autre_jour_n_ouvre_rien() -> None:
    """C'est la différence avec une plage thématique : un programme a des jours."""
    assert Programmation([CHLOE], a(VENDREDI + timedelta(days=1), 19)).programme_courant() is None


def test_le_debut_est_inclus_et_la_fin_exclue() -> None:
    """Sans cette convention, deux programmes qui se touchent se recouvriraient
    d'une minute — et le second n'aurait jamais son heure pleine."""
    assert Programmation([CHLOE], a(VENDREDI, 18)).programme_courant() is CHLOE
    assert Programmation([CHLOE], a(VENDREDI, 19, 59)).programme_courant() is CHLOE
    assert Programmation([CHLOE], a(VENDREDI, 20)).programme_courant() is None


def test_tous_ouvre_les_sept_jours() -> None:
    for decalage in range(len(JOURS)):
        programmation = Programmation([QUOTIDIEN], a(VENDREDI + timedelta(days=decalage), 8))
        assert programmation.programme_courant() is QUOTIDIEN


def test_un_programme_qui_enjambe_minuit_appartient_au_jour_ou_il_commence() -> None:
    """« Le vendredi, 22 h → 02 h » est la nuit du vendredi au samedi : compter
    le samedi 01 h comme un samedi le ferait démarrer une nuit trop tôt."""
    nuit = Programme(
        nom="La nuit du vendredi",
        playlist="Nuit",
        jours=("vendredi",),
        debut=time(22),
        fin=time(2),
    )

    assert Programmation([nuit], a(VENDREDI, 23)).programme_courant() is nuit
    assert Programmation([nuit], a(VENDREDI + timedelta(days=1), 1)).programme_courant() is nuit
    assert Programmation([nuit], a(VENDREDI, 1)).programme_courant() is None
    assert Programmation([nuit], a(VENDREDI + timedelta(days=1), 23)).programme_courant() is None
    assert Programmation([nuit], a(VENDREDI, 12)).programme_courant() is None


def test_une_nuit_du_dimanche_se_prolonge_le_lundi_matin() -> None:
    """Le lundi est le seul jour dont la veille change de semaine : c'est là
    que le calcul du jour précédent se casserait s'il ne bouclait pas."""
    nuit = Programme(
        nom="La nuit du dimanche",
        playlist="Nuit",
        jours=("dimanche",),
        debut=time(23),
        fin=time(1),
    )
    lundi = VENDREDI + timedelta(days=3)

    assert Programmation([nuit], a(lundi, 0, 30)).programme_courant() is nuit
    assert Programmation([nuit], a(lundi, 23)).programme_courant() is None


def test_le_premier_programme_declare_l_emporte_sur_un_recouvrement() -> None:
    tot = Programme(
        nom="Le premier", playlist="A", jours=(TOUS_LES_JOURS,), debut=time(8), fin=time(12)
    )
    tard = Programme(
        nom="Le second", playlist="B", jours=(TOUS_LES_JOURS,), debut=time(10), fin=time(14)
    )

    assert Programmation([tot, tard], a(VENDREDI, 11)).programme_courant() is tot
    assert Programmation([tard, tot], a(VENDREDI, 11)).programme_courant() is tard


def test_les_programmes_declares_restent_lisibles_dans_leur_ordre() -> None:
    programmation = Programmation([CHLOE, QUOTIDIEN], a(VENDREDI, 15))

    assert programmation.programmes == (CHLOE, QUOTIDIEN)


def test_une_journee_entiere_se_deroule_sans_infrastructure() -> None:
    ouverts = [
        Programmation([QUOTIDIEN, CHLOE], a(VENDREDI, heure)).programme_courant()
        for heure in range(24)
    ]

    assert ouverts.count(QUOTIDIEN) == 2
    assert ouverts.count(CHLOE) == 2
    assert ouverts.count(None) == 20


@pytest.mark.parametrize(
    ("champs", "attendu"),
    [
        ({"nom": ""}, "sans nom"),
        ({"playlist": ""}, "aucune liste de lecture"),
        ({"jours": ()}, "aucun jour"),
        ({"jours": ("friday",)}, "n'est pas un jour"),
        ({"fin": time(18)}, "programme vide"),
    ],
)
def test_un_programme_impossible_est_refuse_a_la_construction(
    champs: dict[str, object], attendu: str
) -> None:
    """Une déclaration fautive se voit au démarrage, pas à l'antenne."""
    valides: dict[str, object] = {
        "nom": "Le vendredi de Chloé",
        "playlist": "Chloé",
        "jours": ("vendredi",),
        "debut": time(18),
        "fin": time(20),
    }

    with pytest.raises(ValueError, match=attendu):
        Programme(**{**valides, **champs})  # type: ignore[arg-type]
