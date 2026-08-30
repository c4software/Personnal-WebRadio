"""Les programmes : quand ils s'ouvrent, et ce qu'ils refusent.

Aucune infrastructure : l'horloge est figée, la semaine se déroule en une
boucle, et deux exécutions donnent le même résultat (AGENTS.md §4).
"""

from datetime import UTC, datetime, time, timedelta

import pytest

from webradio.core.clock import FrozenClock
from webradio.core.programmes import DAYS, EVERY_DAY, Programme, Programming

# Le 2026-08-28 est un vendredi ; les instants d'essai se comptent à partir de lui.
VENDREDI = datetime(2026, 8, 28, tzinfo=UTC)

CHLOE = Programme(
    name="Le vendredi de Chloé",
    playlist="Chloé",
    days=("vendredi",),
    start=time(18),
    end=time(20),
)
QUOTIDIEN = Programme(
    name="Le réveil",
    playlist="Matin",
    days=(EVERY_DAY,),
    start=time(7),
    end=time(9),
)


def a(depart: datetime, hour: int, minute: int = 0) -> FrozenClock:
    return FrozenClock(depart + timedelta(hours=hour, minutes=minute))


def test_hors_de_tout_programme_rien_n_est_ouvert() -> None:
    programming = Programming([CHLOE, QUOTIDIEN], a(VENDREDI, 15))

    assert programming.current_programme() is None
    assert programming.playlist_to_draw() is None


def test_un_programme_ouvre_le_jour_et_a_l_heure_declares() -> None:
    programming = Programming([CHLOE], a(VENDREDI, 19))

    assert programming.current_programme() is CHLOE
    assert programming.playlist_to_draw() == "Chloé"


def test_le_meme_creneau_un_autre_jour_n_ouvre_rien() -> None:
    """C'est la différence avec une plage thématique : un programme a des jours."""
    assert Programming([CHLOE], a(VENDREDI + timedelta(days=1), 19)).current_programme() is None


def test_le_debut_est_inclus_et_la_fin_exclue() -> None:
    """Sans cette convention, deux programmes qui se touchent se recouvriraient
    d'une minute — et le second n'aurait jamais son heure pleine."""
    assert Programming([CHLOE], a(VENDREDI, 18)).current_programme() is CHLOE
    assert Programming([CHLOE], a(VENDREDI, 19, 59)).current_programme() is CHLOE
    assert Programming([CHLOE], a(VENDREDI, 20)).current_programme() is None


def test_tous_ouvre_les_sept_jours() -> None:
    for decalage in range(len(DAYS)):
        programming = Programming([QUOTIDIEN], a(VENDREDI + timedelta(days=decalage), 8))
        assert programming.current_programme() is QUOTIDIEN


def test_un_programme_qui_enjambe_minuit_appartient_au_jour_ou_il_commence() -> None:
    """« Le vendredi, 22 h → 02 h » est la nuit du vendredi au samedi : compter
    le samedi 01 h comme un samedi le ferait démarrer une nuit trop tôt."""
    nuit = Programme(
        name="La nuit du vendredi",
        playlist="Nuit",
        days=("vendredi",),
        start=time(22),
        end=time(2),
    )

    assert Programming([nuit], a(VENDREDI, 23)).current_programme() is nuit
    assert Programming([nuit], a(VENDREDI + timedelta(days=1), 1)).current_programme() is nuit
    assert Programming([nuit], a(VENDREDI, 1)).current_programme() is None
    assert Programming([nuit], a(VENDREDI + timedelta(days=1), 23)).current_programme() is None
    assert Programming([nuit], a(VENDREDI, 12)).current_programme() is None


def test_une_nuit_du_dimanche_se_prolonge_le_lundi_matin() -> None:
    """Le lundi est le seul jour dont la veille change de semaine : c'est là
    que le calcul du jour précédent se casserait s'il ne bouclait pas."""
    nuit = Programme(
        name="La nuit du dimanche",
        playlist="Nuit",
        days=("dimanche",),
        start=time(23),
        end=time(1),
    )
    lundi = VENDREDI + timedelta(days=3)

    assert Programming([nuit], a(lundi, 0, 30)).current_programme() is nuit
    assert Programming([nuit], a(lundi, 23)).current_programme() is None


def test_le_premier_programme_declare_l_emporte_sur_un_recouvrement() -> None:
    tot = Programme(name="Le premier", playlist="A", days=(EVERY_DAY,), start=time(8), end=time(12))
    tard = Programme(
        name="Le second", playlist="B", days=(EVERY_DAY,), start=time(10), end=time(14)
    )

    assert Programming([tot, tard], a(VENDREDI, 11)).current_programme() is tot
    assert Programming([tard, tot], a(VENDREDI, 11)).current_programme() is tard


def test_les_programmes_declares_restent_lisibles_dans_leur_ordre() -> None:
    programming = Programming([CHLOE, QUOTIDIEN], a(VENDREDI, 15))

    assert programming.programmes == (CHLOE, QUOTIDIEN)


def test_une_journee_entiere_se_deroule_sans_infrastructure() -> None:
    ouverts = [
        Programming([QUOTIDIEN, CHLOE], a(VENDREDI, hour)).current_programme() for hour in range(24)
    ]

    assert ouverts.count(QUOTIDIEN) == 2
    assert ouverts.count(CHLOE) == 2
    assert ouverts.count(None) == 20


@pytest.mark.parametrize(
    ("champs", "attendu"),
    [
        ({"name": ""}, "sans nom"),
        ({"playlist": ""}, "aucune liste de lecture"),
        ({"days": ()}, "aucun jour"),
        ({"days": ("friday",)}, "n'est pas un jour"),
        ({"end": time(18)}, "programme vide"),
    ],
)
def test_un_programme_impossible_est_refuse_a_la_construction(
    champs: dict[str, object], attendu: str
) -> None:
    """Une déclaration fautive se voit au démarrage, pas à l'antenne."""
    valides: dict[str, object] = {
        "name": "Le vendredi de Chloé",
        "playlist": "Chloé",
        "days": ("vendredi",),
        "start": time(18),
        "end": time(20),
    }

    with pytest.raises(ValueError, match=attendu):
        Programme(**{**valides, **champs})  # type: ignore[arg-type]
