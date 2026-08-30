"""L'API et la page : ce qu'elles disent, ce qu'elles refusent, et par où.

Le client de test de Flask suffit : aucun réseau, aucun serveur lancé.
"""

from datetime import timedelta

import pytest
from flask.testing import FlaskClient

from webradio.adapters.web import (
    Antenne,
    Nature,
    Verdict,
    Vote,
    creer_application,
    creer_vue,
)

RAFRAICHISSEMENT = timedelta(seconds=5)


class FakeRadio:
    """Une radio dont le test décide ce qu'elle passe et ce qu'elle refuse.

    C'est la frontière de l'API : trois questions, et rien derrière. Le noyau
    réel s'y branchera sans que l'API change.
    """

    def __init__(
        self,
        *,
        antenne: Antenne | None = None,
        verdict: Verdict | None = None,
    ) -> None:
        self._antenne = antenne
        self._verdict = verdict if verdict is not None else Verdict(accepte=True)
        self.votes: list[Vote] = []

    def en_diffusion(self) -> bool:
        return self._antenne is not None

    def antenne(self) -> Antenne | None:
        return self._antenne

    def voter(self, vote: Vote) -> Verdict:
        self.votes.append(vote)
        return self._verdict


def client(radio: FakeRadio) -> FlaskClient:
    application = creer_application(radio, rafraichissement=RAFRAICHISSEMENT)
    application.config.update(TESTING=True)
    return application.test_client()


MORCEAU = Antenne(nature=Nature.MUSIQUE, titre="Sexy Boy", artiste="Air")


def test_l_api_dit_ce_qui_passe_et_de_quelle_nature() -> None:
    reponse = client(FakeRadio(antenne=MORCEAU)).get("/api/antenne")
    assert reponse.status_code == 200
    assert reponse.get_json() == {
        "en_diffusion": True,
        "antenne": {"nature": "musique", "titre": "Sexy Boy", "artiste": "Air"},
    }


@pytest.mark.parametrize(
    "nature",
    [Nature.MUSIQUE, Nature.JINGLE, Nature.FLASH, Nature.EMISSION],
)
def test_l_api_distingue_les_quatre_natures(nature: Nature) -> None:
    reponse = client(FakeRadio(antenne=Antenne(nature=nature))).get("/api/antenne")
    assert reponse.get_json()["antenne"]["nature"] == str(nature)


def test_l_api_dit_quand_la_chaine_ne_tourne_pas() -> None:
    """La radio n'existe que lorsqu'on l'écoute (SPECS.md §1)."""
    reponse = client(FakeRadio()).get("/api/antenne")
    assert reponse.get_json() == {"en_diffusion": False, "antenne": None}


def test_un_jingle_n_a_ni_titre_ni_artiste() -> None:
    reponse = client(FakeRadio(antenne=Antenne(nature=Nature.JINGLE))).get("/api/antenne")
    assert reponse.get_json()["antenne"] == {
        "nature": "jingle",
        "titre": None,
        "artiste": None,
    }


@pytest.mark.parametrize("vote", [Vote.STOP, Vote.ENCORE])
def test_une_seule_voix_suffit_a_faire_passer_un_vote(vote: Vote) -> None:
    """Ni quorum, ni fenêtre de dépouillement (SPECS.md §4.6)."""
    radio = FakeRadio(antenne=MORCEAU)
    reponse = client(radio).post(f"/api/votes/{vote}")
    assert reponse.status_code == 200
    assert reponse.get_json() == {"accepte": True, "vote": str(vote), "motif": None}
    assert radio.votes == [vote]


def test_un_vote_pendant_un_jingle_est_refuse_avec_son_motif() -> None:
    """Un refus muet est indistinguable d'une panne (ARCHITECTURE.md §6.1)."""
    motif = "un jingle passe : on ne demande pas « encore » d'un jingle"
    radio = FakeRadio(
        antenne=Antenne(nature=Nature.JINGLE),
        verdict=Verdict(accepte=False, motif=motif),
    )
    reponse = client(radio).post("/api/votes/encore")
    assert reponse.status_code == 409
    assert reponse.get_json() == {"accepte": False, "vote": "encore", "motif": motif}


def test_un_vote_pendant_une_emission_est_refuse_avec_son_motif() -> None:
    """On ne passe pas une émission (SPECS.md §4.11)."""
    motif = "une émission passe : elle remplace la programmation"
    radio = FakeRadio(
        antenne=Antenne(nature=Nature.EMISSION),
        verdict=Verdict(accepte=False, motif=motif),
    )
    reponse = client(radio).post("/api/votes/stop")
    assert reponse.status_code == 409
    assert reponse.get_json()["motif"] == motif


def test_un_vote_inconnu_est_refuse_en_disant_lequel() -> None:
    radio = FakeRadio(antenne=MORCEAU)
    reponse = client(radio).post("/api/votes/plus-fort")
    assert reponse.status_code == 400
    assert "plus-fort" in reponse.get_json()["motif"]
    assert radio.votes == []


def test_un_refus_sans_motif_est_impossible_a_construire() -> None:
    """La contrainte est portée par le type, pas par la discipline de l'appelant."""
    with pytest.raises(ValueError, match="refus sans motif"):
        Verdict(accepte=False)


def test_l_api_ne_rend_que_des_donnees() -> None:
    """L'API rend des données, la vue les met en page (AGENTS.md §2)."""
    reponse = client(FakeRadio(antenne=MORCEAU)).get("/api/antenne")
    assert reponse.mimetype == "application/json"
    assert b"<html" not in reponse.data


def test_la_page_ne_recoit_aucune_donnee_d_antenne() -> None:
    """L'interface n'a aucun chemin privilégié : elle passe par l'API.

    Si le titre du morceau apparaissait dans le HTML servi, c'est que la vue
    serait allée le chercher elle-même — un second chemin vers le noyau.
    """
    reponse = client(FakeRadio(antenne=MORCEAU)).get("/")
    assert reponse.status_code == 200
    assert b"Sexy Boy" not in reponse.data
    assert b"Air" not in reponse.data


def test_les_boutons_de_la_page_pointent_vers_l_api() -> None:
    reponse = client(FakeRadio(antenne=MORCEAU)).get("/")
    assert b"/api/votes/stop" in reponse.data
    assert b"/api/votes/encore" in reponse.data
    assert b"/api/antenne" in reponse.data


def test_la_page_est_faite_pour_un_telephone() -> None:
    reponse = client(FakeRadio()).get("/")
    assert b'name="viewport"' in reponse.data


def test_le_rafraichissement_de_la_page_vient_de_la_configuration() -> None:
    """Aucune durée en dur : cinq secondes doivent se retrouver dans la page."""
    reponse = client(FakeRadio()).get("/")
    assert b"5000" in reponse.data


def test_un_rafraichissement_nul_est_refuse() -> None:
    with pytest.raises(ValueError, match="rafraîchissement"):
        creer_vue(rafraichissement=timedelta(0))
