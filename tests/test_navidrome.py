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
