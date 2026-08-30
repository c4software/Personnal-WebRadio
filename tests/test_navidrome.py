"""L'adaptateur Navidrome, contre des réponses HTTP **littérales**.

Les corps de réponse sont recopiés de [docs/navidrome.md](../docs/navidrome.md),
qui les a relevés contre une instance réelle. Aucun test ne touche au réseau :
le transport est un Fake versionné, pas un mock généré (AGENTS.md §4).

Les identifiants employés ici sont **fictifs**.
"""

import hashlib
import io
import logging
import urllib.error
import urllib.parse
from datetime import timedelta
from email.message import Message
from types import TracebackType

import pytest

from webradio.adapters.config.schema import ConfigurationNavidrome, IdentifiantsNavidrome
from webradio.adapters.sources.navidrome import (
    PLAFOND_ECHANTILLON,
    ReponseHttp,
    SourceNavidrome,
    TransportUrllib,
)
from webradio.core.modeles import Piste
from webradio.core.rng import HasardScripte
from webradio.core.sources import SourceIndisponible

UTILISATEUR = "auditeur-fictif"
MOT_DE_PASSE = "passe-fictif"

IDENTIFIANTS = IdentifiantsNavidrome(
    url="http://exemple.local",
    utilisateur=UTILISATEUR,
    mot_de_passe=MOT_DE_PASSE,
)

# ── Corps relevés (docs/navidrome.md) ──────────────────────────────────────

MOT_DE_PASSE_FAUX = """
{"subsonic-response": {"status": "failed", "version": "1.16.1",
 "type": "navidrome", "serverVersion": "0.63.2",
 "error": {"code": 40, "message": "Wrong username or password"}}}
"""

IDENTIFIANT_INCONNU = """
{"subsonic-response": {"status": "failed", "version": "1.16.1",
 "error": {"code": 70, "message": "Song not found"}}}
"""

ECHEC_SANS_DETAIL = '{"subsonic-response": {"status": "failed", "version": "1.16.1"}}'

DEUX_CHANSONS = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "randomSongs": {"song": [
  {"id": "0f1a", "title": "Un titre", "artist": "Un artiste", "album": "Un album",
   "genre": "Chanson française", "duration": 213, "suffix": "mp3", "bitRate": 320},
  {"id": "0f1b", "title": "Sans étiquette", "artist": "Un autre artiste",
   "duration": 187, "suffix": "mp3", "bitRate": 128}
]}}}
"""

GENRE_INEXISTANT = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "randomSongs": {}}}
"""

CHANSONS_ABIMEES = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "randomSongs": {"song": [
  {"title": "Sans identifiant", "artist": "Un artiste", "duration": 200, "suffix": "mp3"},
  {"id": "0f1c", "title": "Durée nulle", "artist": "Un artiste", "duration": 0},
  {"id": "0f1d", "title": "Durée absente", "artist": "Un artiste"},
  "une chaîne au lieu d'une chanson",
  {"id": "0f1e", "title": "Valable", "artist": "Un artiste", "duration": 120}
]}}}
"""

RECHERCHE_ARTISTE = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "searchResult3": {"song": [
  {"id": "1a", "title": "La sienne", "artist": "Un artiste", "duration": 200, "genre": "Rock"},
  {"id": "1b", "title": "Celle du voisin", "artist": "Un artiste voisin", "duration": 190},
  {"id": "1c", "title": "La sienne encore", "artist": "Un artiste", "duration": 210}
]}}}
"""

GENRES = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "genres": {"genre": [
  {"value": "Chanson française", "songCount": 1280, "albumCount": 120},
  {"value": "Rock", "songCount": 357, "albumCount": 40},
  {"value": "Rock", "songCount": 357, "albumCount": 40},
  {"songCount": 12},
  {"value": "", "songCount": 0}
]}}}
"""

PAGE_HTML_EN_200 = """<!DOCTYPE html>
<html><head><title>502 Bad Gateway</title></head>
<body><h1>502 Bad Gateway</h1><p>nginx</p></body></html>
"""

JSON_TRONQUE = '{"subsonic-response": {"status": "ok", "randomSongs": {"song": [{"id": "0f1'

JSON_SANS_ENVELOPPE = '{"error": "quelque chose d\'autre"}'

PAGE_404 = "404 page not found\n"


class TransportScripte:
    """Un transport qui rend des réponses écrites d'avance, et retient les URL appelées."""

    def __init__(self, reponses: list[ReponseHttp] | ReponseHttp) -> None:
        self._reponses = reponses if isinstance(reponses, list) else [reponses]
        self.urls: list[str] = []

    def recuperer(self, url: str) -> ReponseHttp:
        self.urls.append(url)
        if len(self._reponses) == 1:
            return self._reponses[0]
        return self._reponses.pop(0)


class TransportInjoignable:
    """Le serveur ne répond pas du tout : aucune réponse, une erreur système."""

    def recuperer(self, url: str) -> ReponseHttp:
        message = f"connexion refusée pour {url}"
        raise ConnectionRefusedError(message)


def _reglages(taille: int = 100, resultats: int = 50) -> ConfigurationNavidrome:
    return ConfigurationNavidrome(
        taille_echantillon=taille,
        resultats_artiste=resultats,
        delai_secondes=1.0,
    )


def _source(
    corps: str = "",
    code: int = 200,
    *,
    transport: TransportScripte | TransportInjoignable | None = None,
    taille: int = 100,
) -> SourceNavidrome:
    reel = transport if transport is not None else TransportScripte(ReponseHttp(code, corps))
    return SourceNavidrome(
        identifiants=IDENTIFIANTS,
        reglages=_reglages(taille=taille),
        # Un sel écrit à l'avance : deux exécutions produisent la même URL.
        hasard=HasardScripte([0] * 1000),
        transport=reel,
    )


def _parametres(url: str) -> dict[str, str]:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))


def _empreinte(texte: str) -> str:
    return hashlib.md5(texte.encode("utf-8")).hexdigest()


# ── Le piège n°1 : un refus d'authentification arrive en HTTP 200 ──────────


def test_un_mot_de_passe_faux_leve_une_source_indisponible_malgre_un_code_200() -> None:
    source = _source(MOT_DE_PASSE_FAUX)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "40" in str(panne.value)
    assert "Wrong username or password" in str(panne.value)


def test_un_identifiant_inconnu_leve_une_source_indisponible() -> None:
    source = _source(IDENTIFIANT_INCONNU)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes_de("Un artiste")

    assert "70" in str(panne.value)


def test_un_echec_sans_detail_leve_quand_meme() -> None:
    source = _source(ECHEC_SANS_DETAIL)

    with pytest.raises(SourceIndisponible) as panne:
        source.genres()

    assert "getGenres" in str(panne.value)


def test_aucun_secret_ne_parait_dans_les_journaux_ni_dans_le_message_de_panne(
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = _source(MOT_DE_PASSE_FAUX)

    with caplog.at_level(logging.DEBUG), pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert MOT_DE_PASSE not in str(panne.value)
    assert MOT_DE_PASSE not in caplog.text
    assert "t=" not in caplog.text


# ── L'authentification : jeton dérivé, jamais de mot de passe en clair ─────


def test_le_mot_de_passe_ne_circule_jamais_en_clair() -> None:
    transport = TransportScripte(ReponseHttp(200, DEUX_CHANSONS))
    _source(transport=transport).pistes()

    (url,) = transport.urls
    assert MOT_DE_PASSE not in url
    assert "p=" not in _parametres(url)


def test_le_jeton_est_l_empreinte_du_mot_de_passe_et_du_sel() -> None:
    transport = TransportScripte(ReponseHttp(200, DEUX_CHANSONS))
    _source(transport=transport).pistes()

    parametres = _parametres(transport.urls[0])
    sel = parametres["s"]
    assert parametres["t"] == _empreinte(MOT_DE_PASSE + sel)
    assert parametres["u"] == UTILISATEUR
    assert parametres["v"] == "1.16.1"
    assert parametres["c"] == "local-webradio"
    assert parametres["f"] == "json"


# ── Le piège n°2 : la troncature silencieuse à 500 ─────────────────────────


def test_une_taille_au_dessus_du_plafond_est_ramenee_a_500(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = TransportScripte(ReponseHttp(200, DEUX_CHANSONS))

    with caplog.at_level(logging.WARNING):
        source = _source(transport=transport, taille=1000)
    source.pistes()

    assert _parametres(transport.urls[0])["size"] == str(PLAFOND_ECHANTILLON)
    assert "tronque" in caplog.text


def test_une_taille_sous_le_plafond_est_demandee_telle_quelle() -> None:
    transport = TransportScripte(ReponseHttp(200, DEUX_CHANSONS))
    _source(transport=transport, taille=100).pistes()

    assert _parametres(transport.urls[0])["size"] == "100"


# ── Les pièges n°4 et n°5 : genre inexistant, genre manquant ───────────────


def test_un_genre_inexistant_rend_une_liste_vide_sans_lever() -> None:
    transport = TransportScripte(ReponseHttp(200, GENRE_INEXISTANT))
    source = _source(transport=transport)

    assert source.pistes(genre="Genre qui n'existe pas") == []
    assert _parametres(transport.urls[0])["genre"] == "Genre qui n'existe pas"


def test_une_piste_sans_genre_est_conservee() -> None:
    pistes = _source(DEUX_CHANSONS).pistes()

    assert [piste.genre for piste in pistes] == ["Chanson française", None]
    assert pistes[0].duree.total_seconds() == 213
    assert pistes[0].identifiant == "0f1a"


def test_une_piste_inexploitable_est_ecartee_sans_faire_echouer_l_appel(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        pistes = _source(CHANSONS_ABIMEES).pistes()

    assert [piste.identifiant for piste in pistes] == ["0f1e"]
    assert caplog.text.count("ignorée") == 4


# ── Le piège n°3 : `search3` ramène aussi d'autres artistes ────────────────


def test_les_pistes_d_un_artiste_excluent_les_autres_artistes() -> None:
    transport = TransportScripte(ReponseHttp(200, RECHERCHE_ARTISTE))
    pistes = _source(transport=transport).pistes_de("Un artiste")

    assert [piste.identifiant for piste in pistes] == ["1a", "1c"]
    parametres = _parametres(transport.urls[0])
    assert parametres["query"] == "Un artiste"
    assert parametres["songCount"] == "50"


def test_un_artiste_absent_de_la_bibliotheque_rend_une_liste_vide() -> None:
    assert _source(GENRE_INEXISTANT).pistes_de("Personne") == []


# ── Le piège n°6 : les deux régimes d'erreur ───────────────────────────────


def test_un_404_sans_corps_subsonic_leve_une_source_indisponible() -> None:
    source = _source(PAGE_404, code=404)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "404" in str(panne.value)


def test_une_page_html_rendue_en_200_leve_une_source_indisponible() -> None:
    source = _source(PAGE_HTML_EN_200)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "JSON" in str(panne.value)


def test_un_json_tronque_leve_une_source_indisponible() -> None:
    source = _source(JSON_TRONQUE)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "JSON" in str(panne.value)


def test_un_json_sans_enveloppe_subsonic_leve_une_source_indisponible() -> None:
    source = _source(JSON_SANS_ENVELOPPE)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "subsonic-response" in str(panne.value)


def test_un_corps_json_qui_n_est_pas_un_objet_leve_une_source_indisponible() -> None:
    source = _source("[1, 2, 3]")

    with pytest.raises(SourceIndisponible):
        source.pistes()


def test_un_serveur_injoignable_devient_une_source_indisponible() -> None:
    source = _source(transport=TransportInjoignable())

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes()

    assert "injoignable" in str(panne.value)


# ── Les genres connus ──────────────────────────────────────────────────────


def test_les_genres_sont_rendus_dedoublonnes_et_ordonnes() -> None:
    assert _source(GENRES).genres() == ["Chanson française", "Rock"]


def test_une_reponse_sans_genres_rend_une_liste_vide() -> None:
    assert _source('{"subsonic-response": {"status": "ok"}}').genres() == []


def test_des_genres_d_un_type_inattendu_rendent_une_liste_vide() -> None:
    corps = '{"subsonic-response": {"status": "ok", "genres": {"genre": "Rock"}}}'

    assert _source(corps).genres() == []


# ── Le transport réel, sans réseau ─────────────────────────────────────────


class _ReponseUrllib:
    """Ce que `urlopen` rend : un gestionnaire de contexte avec un code et un corps."""

    def __init__(self, status: int, corps: bytes) -> None:
        self.status = status
        self._corps = corps

    def __enter__(self) -> "_ReponseUrllib":
        return self

    def __exit__(
        self,
        genre: type[BaseException] | None,
        valeur: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return self._corps


def test_le_transport_rend_le_code_et_le_corps() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        return _ReponseUrllib(200, b'{"ok": true}')

    transport = TransportUrllib(delai_secondes=1.0, ouvrir=ouvrir)

    reponse = transport.recuperer("http://exemple.local/rest/ping")

    assert reponse == ReponseHttp(code=200, corps='{"ok": true}')


def test_le_transport_rend_une_erreur_http_comme_une_reponse_ordinaire() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        raise urllib.error.HTTPError(
            url="http://exemple.local/rest/inconnu",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=io.BytesIO(PAGE_404.encode("utf-8")),
        )

    transport = TransportUrllib(delai_secondes=1.0, ouvrir=ouvrir)
    reponse = transport.recuperer("http://exemple.local/rest/inconnu")

    assert reponse.code == 404
    assert reponse.corps == PAGE_404


def test_le_transport_traduit_une_panne_de_connexion() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        raise urllib.error.URLError("connexion refusée")

    transport = TransportUrllib(delai_secondes=1.0, ouvrir=ouvrir)

    with pytest.raises(SourceIndisponible) as panne:
        transport.recuperer("http://exemple.local/rest/ping")

    assert "injoignable" in str(panne.value)


def test_le_transport_par_defaut_existe_sans_etre_appele() -> None:
    """Construire le transport réel ne touche à rien : rien n'est ouvert avant un appel."""
    transport = TransportUrllib(delai_secondes=1.0)

    assert transport is not None


def test_entree_rend_une_url_de_flux_portant_le_jeton() -> None:
    """La chaîne de diffusion ouvre cette URL telle quelle : c'est le seul
    endroit du projet où l'identifiant opaque redevient lisible."""
    source = _source()
    piste = Piste(
        identifiant="piste-1",
        titre="un titre",
        artiste="un artiste",
        genre=None,
        duree=timedelta(seconds=180),
    )
    url = source.entree(piste)
    assert "stream.view" in url
    assert "id=piste-1" in url
    assert "t=" in url and "s=" in url
    assert MOT_DE_PASSE not in url


# ── Les listes de lecture (docs/navidrome.md §2.6) ─────────────────────────

LISTES = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlists": {"playlist": [
  {"id": "pl-1", "name": "Chloé", "songCount": 67, "duration": 14000},
  {"id": "pl-2", "name": "Soirée", "songCount": 26, "duration": 6100},
  {"name": "Sans identifiant", "songCount": 3}
]}}}
"""

LISTES_HOMONYMES = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlists": {"playlist": [
  {"id": "pl-1", "name": "Chloé", "songCount": 67},
  {"id": "pl-9", "name": "Chloé", "songCount": 4},
  "une chaîne au lieu d'une liste"
]}}}
"""

AUCUNE_LISTE = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlists": {}}}
"""

# `songCount` annonce 67 là où deux entrées seulement sont rendues : c'est le
# constat du relevé §2.6.1, recopié tel quel.
LISTE_CHLOE = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlist": {
 "id": "pl-1", "name": "Chloé", "songCount": 67, "entry": [
  {"id": "0f2a", "title": "La première", "artist": "Une artiste",
   "genre": "Chanson française", "duration": 205, "suffix": "mp3"},
  {"id": "0f2b", "title": "Sans étiquette", "artist": "Un autre artiste",
   "duration": 178, "suffix": "mp3"}
]}}}
"""

LISTE_VIDE = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlist": {
 "id": "pl-1", "name": "Chloé", "songCount": 67}}}
"""

LISTE_ABIMEE = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "playlist": {
 "id": "pl-1", "name": "Chloé", "entry": [
  {"title": "Sans identifiant", "artist": "Une artiste", "duration": 200},
  {"id": "0f2c", "title": "Durée nulle", "artist": "Une artiste", "duration": 0},
  42,
  {"id": "0f2d", "title": "Valable", "artist": "Une artiste", "duration": 130}
]}}}
"""

LISTE_INTROUVABLE = """
{"subsonic-response": {"status": "failed", "version": "1.16.1",
 "error": {"code": 70, "message": "playlist not found"}}}
"""


def test_une_liste_de_lecture_est_resolue_par_son_nom() -> None:
    """Le TOML déclare un nom ; l'identifiant Subsonic ne remonte jamais au noyau."""
    transport = TransportScripte(
        [ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_CHLOE)],
    )
    source = _source(transport=transport)

    pistes = source.pistes_de_la_liste_de_lecture("Chloé")

    assert [piste.titre for piste in pistes] == ["La première", "Sans étiquette"]
    assert _parametres(transport.urls[0])["u"] == UTILISATEUR
    assert _parametres(transport.urls[1])["id"] == "pl-1"


def test_le_song_count_annonce_n_est_pas_ce_qui_est_rendu() -> None:
    """67 annoncés, deux entrées rendues : une liste se juge sur ses entrées
    (docs/navidrome.md §2.6.1)."""
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_CHLOE)])
    )

    assert len(source.pistes_de_la_liste_de_lecture("Chloé")) == 2


def test_une_piste_de_liste_sans_genre_reste_retenue() -> None:
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_CHLOE)])
    )

    pistes = source.pistes_de_la_liste_de_lecture("Chloé")

    assert pistes[0].genre == "Chanson française"
    assert pistes[1].genre is None


def test_un_nom_de_liste_inconnu_rend_une_liste_vide_sans_lever(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Le repli sur le tirage libre se décide au-dessus (SPECS.md §7 n°21)."""
    transport = TransportScripte([ReponseHttp(200, LISTES)])
    source = _source(transport=transport)

    with caplog.at_level(logging.INFO):
        pistes = source.pistes_de_la_liste_de_lecture("Inconnue")

    assert pistes == []
    assert len(transport.urls) == 1
    assert "Inconnue" in caplog.text


def test_aucune_liste_declaree_rend_une_liste_vide() -> None:
    source = _source(transport=TransportScripte([ReponseHttp(200, AUCUNE_LISTE)]))

    assert source.pistes_de_la_liste_de_lecture("Chloé") == []


def test_deux_listes_homonymes_retiennent_la_premiere_en_le_disant(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = TransportScripte(
        [ReponseHttp(200, LISTES_HOMONYMES), ReponseHttp(200, LISTE_CHLOE)]
    )
    source = _source(transport=transport)

    with caplog.at_level(logging.WARNING):
        source.pistes_de_la_liste_de_lecture("Chloé")

    assert _parametres(transport.urls[1])["id"] == "pl-1"
    assert "Chloé" in caplog.text


def test_une_liste_sans_entree_rend_une_liste_vide(caplog: pytest.LogCaptureFixture) -> None:
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_VIDE)])
    )

    with caplog.at_level(logging.INFO):
        pistes = source.pistes_de_la_liste_de_lecture("Chloé")

    assert pistes == []
    assert "Chloé" in caplog.text


def test_les_entrees_abimees_d_une_liste_sont_ecartees_et_les_autres_gardees() -> None:
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_ABIMEE)])
    )

    pistes = source.pistes_de_la_liste_de_lecture("Chloé")

    assert [piste.identifiant for piste in pistes] == ["0f2d"]


def test_une_liste_disparue_entre_les_deux_appels_leve_une_source_indisponible() -> None:
    """La liste existait à l'instant de `getPlaylists` et plus à celui de
    `getPlaylist` : HTTP 200, code 70. C'est une panne de source, et le repli
    est celui que la charnière applique déjà à toutes les pannes."""
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, LISTE_INTROUVABLE)])
    )

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes_de_la_liste_de_lecture("Chloé")

    assert "70" in str(panne.value)
    assert "playlist not found" in str(panne.value)


def test_une_page_html_en_200_a_la_place_des_listes_leve_une_source_indisponible() -> None:
    source = _source(PAGE_HTML_EN_200)

    with pytest.raises(SourceIndisponible) as panne:
        source.pistes_de_la_liste_de_lecture("Chloé")

    assert "getPlaylists" in str(panne.value)


def test_des_listes_sans_enveloppe_attendue_rendent_une_liste_vide() -> None:
    """Un contenant absent ou d'un type inattendu n'est pas une panne : c'est
    une bibliothèque sans liste de lecture."""
    sans_contenant = '{"subsonic-response": {"status": "ok", "playlists": {"playlist": "rien"}}}'
    source = _source(transport=TransportScripte([ReponseHttp(200, sans_contenant)]))

    assert source.pistes_de_la_liste_de_lecture("Chloé") == []


def test_une_liste_dont_les_entrees_ont_un_type_inattendu_rend_une_liste_vide() -> None:
    entrees_folles = '{"subsonic-response": {"status": "ok", "playlist": {"entry": "rien"}}}'
    source = _source(
        transport=TransportScripte([ReponseHttp(200, LISTES), ReponseHttp(200, entrees_folles)])
    )

    assert source.pistes_de_la_liste_de_lecture("Chloé") == []


def test_aucun_secret_ne_parait_dans_les_journaux_d_une_liste_de_lecture(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Les URL portent le jeton : elles n'ont leur place dans aucun journal."""
    source = _source(transport=TransportScripte([ReponseHttp(200, LISTES)]))

    with caplog.at_level(logging.DEBUG):
        source.pistes_de_la_liste_de_lecture("Inconnue")

    assert MOT_DE_PASSE not in caplog.text
    assert "/rest/" not in caplog.text
