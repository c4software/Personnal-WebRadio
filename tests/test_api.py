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
from webradio.adapters.web.api import PlayedEntry, UpcomingEntry, VoteScore

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
        self._upcoming: list[UpcomingEntry] = []
        self.withdrawn: list[str] = []

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

    def upcoming(self) -> list[UpcomingEntry]:
        return list(self._upcoming)

    def withdraw(self, identifier: str) -> bool:
        self.withdrawn.append(identifier)
        return any(e.identifier == identifier for e in self._upcoming)

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
    grille: dict[str, object] = {"days": {"monday": [{"start": "08:00", "end": "10:00"}]}}
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT, planning=grille)
    app.config.update(TESTING=True)
    assert app.test_client().get("/api/planning").get_json() == grille


def test_sans_planning_la_route_rend_une_grille_vide() -> None:
    answer = client(FakeRadio()).get("/api/planning")
    assert answer.get_json() == {"days": {}}


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
    """Le bouton « Autre thème » passe par l'API, comme tout bouton (SPECS.md §4.8).
    Il s'appelait « Retirer » — à double sens avec le retrait d'un titre de la
    liste (l'auteur, 2026-09-02)."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert "/api/moment/redraw" in page
    assert "momentRandom" in page
    assert '@click="retirer()">Autre thème</button>' in page
    assert ">Retirer</button>" not in page


A_VENIR = [
    UpcomingEntry(
        kind=Kind.MUSIC, title="Kelly Watch the Stars", artist="Air", identifier="a1", at="16:03"
    ),
    UpcomingEntry(kind=Kind.JINGLE, title="16 h", artist=None, at="16:06", expected=True),
    UpcomingEntry(kind=Kind.MUSIC, title="Heroes", artist="Bowie", identifier="b1", at="16:06"),
]


def test_l_api_liste_les_prochains_titres_dans_l_ordre() -> None:
    """GOAL-058 : la liste, habillage prévu compris, avec l'heure estimée."""
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._upcoming = A_VENIR
    answer = client(radio).get("/api/up-next")
    assert answer.status_code == 200
    assert answer.get_json() == {
        "up_next": [
            {
                "kind": "musique",
                "title": "Kelly Watch the Stars",
                "artist": "Air",
                "identifier": "a1",
                "at": "16:03",
                "expected": False,
            },
            {
                "kind": "jingle",
                "title": "16 h",
                "artist": None,
                "identifier": "",
                "at": "16:06",
                "expected": True,
            },
            {
                "kind": "musique",
                "title": "Heroes",
                "artist": "Bowie",
                "identifier": "b1",
                "at": "16:06",
                "expected": False,
            },
        ]
    }


def test_sans_rien_d_avance_la_liste_est_vide_pas_une_erreur() -> None:
    assert client(FakeRadio()).get("/api/up-next").get_json() == {"up_next": []}


def test_retirer_un_titre_qui_attend() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    radio._upcoming = A_VENIR
    answer = client(radio).delete("/api/up-next/b1")
    assert answer.status_code == 200
    assert answer.get_json() == {"withdrawn": True}
    assert radio.withdrawn == ["b1"]


def test_retirer_un_titre_qui_n_attend_plus_rend_404() -> None:
    radio = FakeRadio(on_air_now=MORCEAU)
    answer = client(radio).delete("/api/up-next/parti")
    assert answer.status_code == 404
    assert answer.get_json()["withdrawn"] is False


def test_la_page_pointe_vers_la_liste_des_prochains_titres() -> None:
    """Le tiroir des prochains titres passe par l'API, comme tout le reste
    (SPECS.md §4.8) : la page porte l'adresse, et rien d'autre."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert "/api/up-next" in page
    assert "Prochains titres" in page
    assert "chargerProchains" in page


def test_sans_adresse_de_flux_la_page_n_a_pas_de_lecteur() -> None:
    """GOAL-060 : rien n'est écrit en dur — pas d'adresse, pas de lecteur."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert 'const FLUX_DECLARE = ""' in page


def test_la_page_porte_l_adresse_du_flux_declaree() -> None:
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT, stream_url=":8000/flux")
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)
    assert 'const FLUX_DECLARE = ":8000/flux"' in page
    assert 'preload="none"' in page
    assert "mediaSession" in page


def test_le_lecteur_est_une_barre_hors_des_onglets() -> None:
    """GOAL-062 : la barre de lecture vit hors des sections d'onglet, pour
    rester sous le pouce quand on passe aux votes ou au planning ; et les
    commandes de l'écran de verrouillage passent par le même bouton."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert '<footer class="barre"' in page
    assert '<button v-if="flux" type="button" class="jouer"' in page
    assert 'class="lecteur"' not in page
    assert page.index('class="barre"') > page.index("<section v-else>")
    assert "setActionHandler(action, () => this.basculerEcoute())" in page


def test_les_prochains_titres_se_deploient_dans_le_lecteur() -> None:
    """GOAL-062-T02, demandé par l'auteur : la liste vit dans la barre, avec
    son bouton ; et les votes suivent la scène au lieu d'être fixés en bas."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert 'class="tiroir"' not in page
    assert page.index('class="liste"') > page.index('<footer class="barre"')
    assert 'class="ouvrir-liste"' in page
    assert 'class="boutons"' not in page
    assert page.index('class="votes"') < page.index("<section v-else-if=\"onglet === 'votes'\">")


def test_la_page_grise_les_votes_sans_auditeur() -> None:
    """GOAL-061 : la page ne décide rien, mais elle n'offre pas un bouton
    dont l'effet serait invisible — sans antenne, rien sur quoi voter."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert 'this.antenne === null || this.antenne.kind !== "musique"' in page


def test_sans_antenne_la_page_montre_une_carte_de_veille_sobre() -> None:
    """GOAL-063-T01, rectifiée par l'auteur : la carte de veille reste, mais
    sans « La radio dort » — elle dit qu'il n'y a rien à l'antenne."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert "dort" not in page
    assert 'class="carte scene veille"' in page
    assert "Rien à l'antenne" in page


def test_la_page_a_une_icone_et_nomme_l_onglet_d_apres_ce_qui_passe() -> None:
    """GOAL-063-T02 : un favicon servi avec la page, et un titre d'onglet
    qui suit l'antenne — sans que la vue aille chercher l'antenne elle-même."""
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT)
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)
    assert 'rel="icon" type="image/svg+xml" href="/static/favicon.svg"' in page
    assert "document.title = a === null" in page
    icone = app.test_client().get("/static/favicon.svg")
    assert icone.status_code == 200
    assert icone.mimetype == "image/svg+xml"


def test_la_page_s_installe_comme_une_application() -> None:
    """GOAL-063-T03 : un manifeste servi avec son type, des icônes PNG pour
    l'écran d'accueil, et les balises qu'iOS lit à la place du manifeste."""
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT)
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)
    assert 'rel="manifest" href="/static/manifest.webmanifest"' in page
    assert 'rel="apple-touch-icon"' in page
    assert 'name="apple-mobile-web-app-capable" content="yes"' in page
    manifeste = app.test_client().get("/static/manifest.webmanifest")
    assert manifeste.status_code == 200
    assert manifeste.mimetype == "application/manifest+json"
    contenu = manifeste.get_json(force=True)
    assert contenu["display"] == "standalone"
    for icone in contenu["icons"]:
        assert app.test_client().get("/static/" + icone["src"]).status_code == 200


def test_la_feuille_de_style_est_un_fichier_servi_avec_la_page() -> None:
    """GOAL-064-T01 : la CSS sort du gabarit et se sert comme Vue, en local."""
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT)
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)
    assert 'rel="stylesheet" href="/static/style.css"' in page
    assert "<style" not in page
    feuille = app.test_client().get("/static/style.css")
    assert feuille.status_code == 200
    assert feuille.mimetype == "text/css"
    assert ".barre" in feuille.get_data(as_text=True)


def test_la_page_anime_les_onglets_les_chansons_et_les_listes() -> None:
    """GOAL-064-T02 : les transitions sont celles de Vue, les cascades de
    liste tiennent à un rang posé par le gabarit, et tout s'éteint sous
    prefers-reduced-motion."""
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT)
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)
    assert '<Transition name="onglet" mode="out-in">' in page
    assert page.count('<Transition name="chanson" mode="out-in">') == 2
    assert page.count("'--i': i") == 5
    feuille = app.test_client().get("/static/style.css").get_data(as_text=True)
    assert "@keyframes entrer" in feuille
    assert "prefers-reduced-motion" in feuille
    # Les lignes de la liste du lecteur entrent par le haut : vers le bas,
    # elles agrandissaient la zone défilante le temps de l'animation.
    assert (
        "@keyframes entrer-du-haut { from { opacity: 0; transform: translateY(-0.4rem); }"
        in feuille
    )
    assert ".prochain {\n  animation: entrer-du-haut" in feuille


def test_le_lecteur_propose_une_enceinte_seulement_en_ecoute() -> None:
    """GOAL-065 : le renvoi vers une enceinte passe par l'API Remote Playback
    du navigateur, sans SDK tiers ; le bouton n'existe qu'en écoute et
    quand le navigateur a trouvé une cible."""
    page = client(FakeRadio()).get("/").get_data(as_text=True)
    assert '<button v-if="ecoute && castDisponible" type="button" class="cast"' in page
    assert "audio.remote.watchAvailability(" in page
    assert "audio.remote.prompt()" in page
    assert "webkitShowPlaybackTargetPicker" in page
    assert "gstatic.com" not in page and "cast_sender" not in page


def test_tout_le_dossier_static_est_empaquete() -> None:
    """Les tests lisent la source, pas le paquet installé : une feuille de
    style ajoutée sans son motif dans pyproject.toml donnait des 404 dans
    l'image (constaté par l'auteur le 2026-09-02, GOAL-064)."""
    import tomllib
    from fnmatch import fnmatch
    from pathlib import Path

    racine = Path(__file__).resolve().parent.parent
    with (racine / "pyproject.toml").open("rb") as fichier:
        motifs = tomllib.load(fichier)["tool"]["setuptools"]["package-data"]["webradio"]
    dossier = racine / "webradio" / "adapters" / "web" / "static"
    for fichier_statique in dossier.iterdir():
        relatif = fichier_statique.relative_to(racine / "webradio").as_posix()
        assert any(fnmatch(relatif, motif) for motif in motifs), relatif


def test_les_pictos_de_la_page_sont_dessines_et_non_des_emoji() -> None:
    """GOAL-069, demandé par l'auteur : « le picto volume est une emoji, c'est
    pas top ». Un emoji ne suit ni la couleur ni la taille du reste, et change
    de dessin d'un système à l'autre — les pictos de la barre sont des SVG en
    ligne qui prennent `currentColor`."""
    app = create_app(FakeRadio(), refresh=RAFRAICHISSEMENT, stream_url=":8000/flux")
    app.config.update(TESTING=True)
    page = app.test_client().get("/").get_data(as_text=True)

    assert '<label v-if="flux" class="volume"' in page
    volume = page[page.index('class="volume"') :]
    assert volume[: volume.index("</label>")].count("<svg") == 1
    # Les plans supérieurs d'Unicode, c'est là que vivent les pictogrammes en
    # couleur ; les flèches et les croix de la page restent en deçà.
    emoji = sorted({c for c in page if ord(c) > 0x1F000})
    assert emoji == [], f"pictogramme en couleur dans la page : {emoji}"
