"""L'API et la page : ce qu'elles disent, ce qu'elles refusent, et par où.

Le client de test de Flask suffit : aucun réseau, aucun serveur lancé.
"""

from datetime import timedelta

import pytest
from flask.testing import FlaskClient

from webradio.adapters.web import (
    Kind,
    OnAir,
    Verdict,
    Vote,
    create_app,
    create_view,
)
from webradio.adapters.web.api import PlayedEntry, VoteScore

RAFRAICHISSEMENT = timedelta(seconds=5)


class FakeRadio:
    """Une radio dont le test décide ce qu'elle passe et ce qu'elle refuse.

    C'est la frontière de l'API : trois questions, et rien derrière. Le noyau
    réel s'y branchera sans que l'API change.
    """

    def __init__(
        self,
        *,
        on_air_now: OnAir | None = None,
        verdict: Verdict | None = None,
    ) -> None:
        self._antenne = on_air_now
        self._verdict = verdict if verdict is not None else Verdict(accepted=True)
        self.votes: list[Vote] = []
        self._scores: list[VoteScore] = []
        self._erasable: list[tuple[str, str]] = []
        self.forgotten: list[tuple[str, str]] = []
        self._moment: str | None = None
        self._history: list[PlayedEntry] = []
        self._up_next: OnAir | None = None
        self._moment_random = False
        self.redraws = 0

    def on_air(self) -> bool:
        return self._antenne is not None

    def on_air_now(self) -> OnAir | None:
        return self._antenne

    def vote(self, vote: Vote) -> Verdict:
        self.votes.append(vote)
        return self._verdict

    def vote_scores(self) -> list[VoteScore]:
        return list(self._scores)

    def forget_vote(self, scope: str, target: str) -> bool:
        self.forgotten.append((scope, target))
        return (scope, target) in self._erasable

    def moment(self) -> str | None:
        return self._moment

    def history(self) -> list[PlayedEntry]:
        return list(self._history)

    def up_next(self) -> OnAir | None:
        return self._up_next

    def moment_random(self) -> bool:
        return self._moment_random

    def redraw_moment(self) -> Verdict:
        self.redraws += 1
        if not self._moment_random:
            return Verdict(accepted=False, reason="aucun thème tiré au sort en ce moment")
        self._moment = "Moment · Jazz (au hasard)"
        return Verdict(accepted=True)


def client(radio: FakeRadio) -> FlaskClient:
    app = create_app(radio, refresh=RAFRAICHISSEMENT)
    app.config.update(TESTING=True)
    return app.test_client()


MORCEAU = OnAir(kind=Kind.MUSIC, title="Sexy Boy", artist="Air")


def test_l_api_dit_ce_qui_passe_et_de_quelle_nature() -> None:
    answer = client(FakeRadio(on_air_now=MORCEAU)).get("/api/on-air")
    assert answer.status_code == 200
    assert answer.get_json() == {
        "on_air": True,
        "moment": None,
        "moment_random": False,
        "up_next": None,
        "on_air_now": {"kind": "musique", "title": "Sexy Boy", "artist": "Air"},
    }


@pytest.mark.parametrize(
    "kind",
    [Kind.MUSIC, Kind.JINGLE, Kind.NEWS, Kind.SHOW],
)
def test_l_api_distingue_les_quatre_natures(kind: Kind) -> None:
    answer = client(FakeRadio(on_air_now=OnAir(kind=kind))).get("/api/on-air")
    assert answer.get_json()["on_air_now"]["kind"] == str(kind)


def test_l_api_dit_quand_la_chaine_ne_tourne_pas() -> None:
    """La radio n'existe que lorsqu'on l'écoute (SPECS.md §1)."""
    answer = client(FakeRadio()).get("/api/on-air")
    assert answer.get_json() == {
        "on_air": False,
        "on_air_now": None,
        "moment": None,
        "moment_random": False,
        "up_next": None,
    }


def test_un_jingle_n_a_ni_titre_ni_artiste() -> None:
    answer = client(FakeRadio(on_air_now=OnAir(kind=Kind.JINGLE))).get("/api/on-air")
    assert answer.get_json()["on_air_now"] == {
        "kind": "jingle",
        "title": None,
        "artist": None,
    }


@pytest.mark.parametrize("vote", [Vote.SKIP, Vote.MORE])
def test_une_seule_voix_suffit_a_faire_passer_un_vote(vote: Vote) -> None:
    """Ni quorum, ni fenêtre de dépouillement (SPECS.md §4.6)."""
    radio = FakeRadio(on_air_now=MORCEAU)
    answer = client(radio).post(f"/api/votes/{vote}")
    assert answer.status_code == 200
    assert answer.get_json() == {"accepted": True, "vote": str(vote), "reason": None}
    assert radio.votes == [vote]


def test_un_vote_pendant_un_jingle_est_refuse_avec_son_motif() -> None:
    """Un refus muet est indistinguable d'une panne (ARCHITECTURE.md §6.1)."""
    reason = "un jingle passe : on ne demande pas « encore » d'un jingle"
    radio = FakeRadio(
        on_air_now=OnAir(kind=Kind.JINGLE),
        verdict=Verdict(accepted=False, reason=reason),
    )
    answer = client(radio).post("/api/votes/encore")
    assert answer.status_code == 409
    assert answer.get_json() == {"accepted": False, "vote": "encore", "reason": reason}


def test_un_vote_pendant_une_emission_est_refuse_avec_son_motif() -> None:
    """On ne passe pas une émission (SPECS.md §4.11)."""
    reason = "une émission passe : elle remplace la programmation"
    radio = FakeRadio(
        on_air_now=OnAir(kind=Kind.SHOW),
        verdict=Verdict(accepted=False, reason=reason),
    )
    answer = client(radio).post("/api/votes/stop")
    assert answer.status_code == 409
    assert answer.get_json()["reason"] == reason


def test_un_vote_inconnu_est_refuse_en_disant_lequel() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    answer = client(radio).post("/api/votes/plus-fort")
    assert answer.status_code == 400
    assert "plus-fort" in answer.get_json()["reason"]
    assert radio.votes == []


def test_un_refus_sans_motif_est_impossible_a_construire() -> None:
    """La contrainte est portée par le type, pas par la discipline de l'appelant."""
    with pytest.raises(ValueError, match="refus sans motif"):
        Verdict(accepted=False)


def test_l_api_ne_rend_que_des_donnees() -> None:
    """L'API rend des données, la vue les met en page (AGENTS.md §2)."""
    answer = client(FakeRadio(on_air_now=MORCEAU)).get("/api/on-air")
    assert answer.mimetype == "application/json"
    assert b"<html" not in answer.data


def test_la_page_ne_recoit_aucune_donnee_d_antenne() -> None:
    """L'interface n'a aucun chemin privilégié : elle passe par l'API.

    Si le titre du morceau apparaissait dans le HTML servi, c'est que la vue
    serait allée le chercher elle-même — un second chemin vers le noyau.
    """
    answer = client(FakeRadio(on_air_now=MORCEAU)).get("/")
    assert answer.status_code == 200
    assert b"Sexy Boy" not in answer.data
    assert b"Air" not in answer.data


def test_les_boutons_de_la_page_pointent_vers_l_api() -> None:
    answer = client(FakeRadio(on_air_now=MORCEAU)).get("/")
    assert b"/api/votes/stop" in answer.data
    assert b"/api/votes/encore" in answer.data
    assert b"/api/on-air" in answer.data


def test_la_page_est_faite_pour_un_telephone() -> None:
    answer = client(FakeRadio()).get("/")
    assert b'name="viewport"' in answer.data


def test_le_rafraichissement_de_la_page_vient_de_la_configuration() -> None:
    """Aucune durée en dur : cinq secondes doivent se retrouver dans la page."""
    answer = client(FakeRadio()).get("/")
    assert b"5000" in answer.data


def test_un_rafraichissement_nul_est_refuse() -> None:
    with pytest.raises(ValueError, match="rafraîchissement"):
        create_view(refresh=timedelta(0))


# ── La page des votes (GOAL-018) ────────────────────────────────────────────


def test_l_api_liste_ce_que_les_votes_ont_laisse() -> None:
    radio = FakeRadio()
    radio._scores = [VoteScore(scope="artiste", target="Air", stop=0.0, encore=2.5)]
    answer = client(radio).get("/api/votes")
    assert answer.status_code == 200
    assert answer.get_json() == {
        "votes": [{"scope": "artiste", "target": "Air", "key": "Air", "stop": 0.0, "encore": 2.5}]
    }


def test_sans_aucun_vote_la_liste_est_vide_pas_une_erreur() -> None:
    answer = client(FakeRadio()).get("/api/votes")
    assert answer.get_json() == {"votes": []}


def test_la_page_pointe_vers_la_route_des_votes() -> None:
    answer = client(FakeRadio()).get("/")
    assert b"/api/votes" in answer.data


def test_la_page_embarque_vue_plutot_qu_un_cdn() -> None:
    """La radio est un objet local : la page doit s'afficher sans internet."""
    answer = client(FakeRadio()).get("/")
    assert b"vue.global.prod.js" in answer.data
    assert b"cdn." not in answer.data and b"unpkg" not in answer.data


def test_un_vote_donne_par_erreur_s_efface() -> None:
    radio = FakeRadio()
    radio._erasable = [("piste", "id-1")]
    answer = client(radio).delete("/api/votes/piste/id-1")
    assert answer.status_code == 200
    assert answer.get_json() == {"deleted": True}
    assert radio.forgotten == [("piste", "id-1")]


def test_effacer_un_vote_inconnu_rend_404() -> None:
    answer = client(FakeRadio()).delete("/api/votes/piste/fantome")
    assert answer.status_code == 404


def test_effacer_une_portee_inconnue_rend_400_sans_toucher_la_base() -> None:
    radio = FakeRadio()
    answer = client(radio).delete("/api/votes/album/x")
    assert answer.status_code == 400
    assert radio.forgotten == []


def test_le_planning_est_celui_du_demarrage() -> None:
    grille: dict[str, object] = {"bands": [{"start": "08:00"}], "programmes": [], "shows": []}
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT, planning=grille)
    app.config.update(TESTING=True)
    assert app.test_client().get("/api/planning").get_json() == grille


def test_sans_planning_la_route_rend_une_grille_vide() -> None:
    answer = client(FakeRadio()).get("/api/planning")
    assert answer.get_json() == {"bands": [], "programmes": [], "shows": []}


def test_le_moment_declare_accompagne_l_antenne() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._moment = "Moment · Rock, Pop"
    answer = client(radio).get("/api/on-air")
    assert answer.get_json()["moment"] == "Moment · Rock, Pop"


# ── Le journal des titres (GOAL-027, SPECS §7 n°27) ─────────────────────────


def test_l_historique_se_lit_du_plus_recent_au_plus_ancien() -> None:
    radio = FakeRadio()
    radio._history = [
        PlayedEntry(on="2026-09-02", at="22:49", kind="emission", title="Alcatraz", artist=""),
        PlayedEntry(
            on="2026-09-01", at="22:45", kind="musique", title="Radiate", artist="Jack Johnson"
        ),
    ]
    answer = client(radio).get("/api/history")
    assert answer.status_code == 200
    assert answer.get_json() == {
        "history": [
            {
                "on": "2026-09-02",
                "at": "22:49",
                "kind": "emission",
                "title": "Alcatraz",
                "artist": "",
            },
            {
                "on": "2026-09-01",
                "at": "22:45",
                "kind": "musique",
                "title": "Radiate",
                "artist": "Jack Johnson",
            },
        ]
    }


def test_la_page_range_le_journal_par_jour_et_par_heure() -> None:
    """GOAL-052 : le journal couvre 24 h, donc deux fois la même heure. Grouper
    sur l'heure seule empilait le 08 h d'hier sous celui d'aujourd'hui, et
    l'ordre paraissait faux alors qu'il ne l'était pas."""
    page = client(FakeRadio()).get("/").data
    assert b"pagesHistorique" in page
    assert b"p.jour === jour && p.heure === heure" in page
    assert b"suffixeDuJour" in page


def test_sans_historique_la_liste_est_vide_pas_une_erreur() -> None:
    assert client(FakeRadio()).get("/api/history").get_json() == {"history": []}


def test_l_api_dit_ce_qui_suit() -> None:
    """GOAL-035 : le morceau d'avance, déjà demandé, s'annonce."""
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._up_next = OnAir(kind=Kind.MUSIC, title="Radiate", artist="Jack Johnson")
    answer = client(radio).get("/api/on-air")
    assert answer.get_json()["up_next"] == {
        "kind": "musique",
        "title": "Radiate",
        "artist": "Jack Johnson",
    }


def test_retirer_le_theme_d_une_plage_au_hasard_dit_le_nouveau_moment() -> None:
    """GOAL-057 : la réponse dit déjà ce qui vient — l'interface n'a pas à
    attendre le rafraîchissement suivant."""
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._moment_random = True
    answer = client(radio).post("/api/moment/redraw")
    assert answer.status_code == 200
    assert answer.get_json() == {
        "accepted": True,
        "reason": None,
        "moment": "Moment · Jazz (au hasard)",
    }
    assert radio.redraws == 1


def test_retirer_hors_d_une_plage_au_hasard_est_refuse_avec_son_motif() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    answer = client(radio).post("/api/moment/redraw")
    assert answer.status_code == 409
    assert answer.get_json()["accepted"] is False
    assert "aucun thème" in answer.get_json()["reason"]


def test_l_api_dit_si_le_moment_a_ete_tire_au_sort() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._moment_random = True
    assert client(radio).get("/api/on-air").get_json()["moment_random"] is True


def test_la_page_pointe_vers_la_route_du_retirage() -> None:
    """Le bouton « Retirer » passe par l'API, comme tout bouton (SPECS.md §4.8)."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert "/api/moment/redraw" in page
    assert "momentRandom" in page
