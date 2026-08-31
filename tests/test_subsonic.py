"""L'adaptateur Subsonic, contre des réponses HTTP **littérales**.

Les corps de réponse sont recopiés de [docs/subsonic.md](../docs/subsonic.md),
qui les a relevés contre une instance réelle. Aucun test ne touche au réseau :
le transport est un Fake versionné, pas un mock généré (AGENTS.md §4).

Les identifiants employés ici sont **fictifs**.
"""

import hashlib
import io
import logging
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta
from email.message import Message
from types import TracebackType

import pytest

from webradio.adapters.config.schema import SubsonicCredentials, SubsonicSettings
from webradio.adapters.sources.subsonic import (
    PAGE_SIZE,
    HttpResponse,
    SubsonicSource,
    UrllibTransport,
)
from webradio.core.clock import FrozenClock
from webradio.core.models import Track
from webradio.core.rng import ScriptedRandom
from webradio.core.sources import SourceUnavailable

UTILISATEUR = "auditeur-fictif"
MOT_DE_PASSE = "passe-fictif"

IDENTIFIANTS = SubsonicCredentials(
    url="http://exemple.local",
    username=UTILISATEUR,
    password=MOT_DE_PASSE,
)

# ── Corps relevés (docs/subsonic.md) ──────────────────────────────────────

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
{"subsonic-response": {"status": "ok", "version": "1.16.1", "searchResult3": {"song": [
  {"id": "0f1a", "title": "Un titre", "artist": "Un artiste", "album": "Un album",
   "genre": "Chanson française", "duration": 213, "suffix": "mp3", "bitRate": 320},
  {"id": "0f1b", "title": "Sans étiquette", "artist": "Un autre artiste",
   "duration": 187, "suffix": "mp3", "bitRate": 128}
]}}}
"""

GENRE_INEXISTANT = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "songsByGenre": {}}}
"""

CHANSONS_ABIMEES = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "searchResult3": {"song": [
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

JSON_TRONQUE = '{"subsonic-response": {"status": "ok", "searchResult3": {"song": [{"id": "0f1'

JSON_SANS_ENVELOPPE = '{"error": "quelque chose d\'autre"}'

PAGE_404 = "404 page not found\n"


class ScriptedTransport:
    """Un transport qui rend des réponses écrites d'avance, et retient les URL appelées."""

    def __init__(self, reponses: list[HttpResponse] | HttpResponse) -> None:
        self._reponses = reponses if isinstance(reponses, list) else [reponses]
        self.urls: list[str] = []

    def fetch(self, url: str) -> HttpResponse:
        self.urls.append(url)
        if len(self._reponses) == 1:
            return self._reponses[0]
        return self._reponses.pop(0)


class UnreachableTransport:
    """Le serveur ne répond pas du tout : aucune réponse, une erreur système."""

    def fetch(self, url: str) -> HttpResponse:
        message = f"connexion refusée pour {url}"
        raise ConnectionRefusedError(message)


UN_SOIR = datetime(2026, 8, 31, 20, 0, tzinfo=UTC)


def _reglages(resultats: int = 50, cache: float = 0.0) -> SubsonicSettings:
    return SubsonicSettings(
        artist_results=resultats,
        timeout_seconds=1.0,
        cache_seconds=cache,
    )


def _source(
    body: str = "",
    code: int = 200,
    *,
    transport: ScriptedTransport | UnreachableTransport | None = None,
    cache: float = 0.0,
    clock: FrozenClock | None = None,
) -> SubsonicSource:
    reel = transport if transport is not None else ScriptedTransport(HttpResponse(code, body))
    return SubsonicSource(
        credentials=IDENTIFIANTS,
        config=_reglages(cache=cache),
        # Un sel écrit à l'avance : deux exécutions produisent la même URL.
        random=ScriptedRandom([0] * 1000),
        transport=reel,
        clock=clock if clock is not None else FrozenClock(UN_SOIR),
    )


def _parametres(url: str) -> dict[str, str]:
    # `keep_blank_values` : la requête vide de search3 (`query=`) doit se voir.
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True))


def _empreinte(texte: str) -> str:
    return hashlib.md5(texte.encode("utf-8")).hexdigest()


# ── Le piège n°1 : un refus d'authentification arrive en HTTP 200 ──────────


def test_un_mot_de_passe_faux_leve_une_source_indisponible_malgre_un_code_200() -> None:
    source = _source(MOT_DE_PASSE_FAUX)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "40" in str(failure.value)
    assert "Wrong username or password" in str(failure.value)


def test_un_identifiant_inconnu_leve_une_source_indisponible() -> None:
    source = _source(IDENTIFIANT_INCONNU)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks_by("Un artiste")

    assert "70" in str(failure.value)


def test_un_echec_sans_detail_leve_quand_meme() -> None:
    source = _source(ECHEC_SANS_DETAIL)

    with pytest.raises(SourceUnavailable) as failure:
        source.genres()

    assert "getGenres" in str(failure.value)


def test_aucun_secret_ne_parait_dans_les_journaux_ni_dans_le_message_de_panne(
    caplog: pytest.LogCaptureFixture,
) -> None:
    source = _source(MOT_DE_PASSE_FAUX)

    with caplog.at_level(logging.DEBUG), pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert MOT_DE_PASSE not in str(failure.value)
    assert MOT_DE_PASSE not in caplog.text
    assert "t=" not in caplog.text


# ── L'authentification : jeton dérivé, jamais de mot de passe en clair ─────


def test_le_mot_de_passe_ne_circule_jamais_en_clair() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    _source(transport=transport).tracks()

    (url,) = transport.urls
    assert MOT_DE_PASSE not in url
    assert "p=" not in _parametres(url)


def test_le_jeton_est_l_empreinte_du_mot_de_passe_et_du_sel() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    _source(transport=transport).tracks()

    params = _parametres(transport.urls[0])
    salt = params["s"]
    assert params["t"] == _empreinte(MOT_DE_PASSE + salt)
    assert params["u"] == UTILISATEUR
    assert params["v"] == "1.16.1"
    assert params["c"] == "local-webradio"
    assert params["f"] == "json"


# ── Le piège n°2 : la bibliothèque entière, page par page ──────────────────
# Les pages pleines sont générées : recopier 500 chansons littérales
# n'apprendrait rien de plus que leur forme, déjà relevée (docs/subsonic.md).


def _page(container: str, identifiers: list[str]) -> str:
    songs = ", ".join(
        f'{{"id": "{identifier}", "title": "T", "artist": "A", "duration": 100}}'
        for identifier in identifiers
    )
    return (
        f'{{"subsonic-response": {{"status": "ok", "version": "1.16.1", '
        f'"{container}": {{"song": [{songs}]}}}}}}'
    )


def test_la_bibliotheque_est_reunie_page_par_page_jusqu_a_une_page_courte() -> None:
    full = [f"p{index}" for index in range(PAGE_SIZE)]
    transport = ScriptedTransport(
        [
            HttpResponse(200, _page("searchResult3", full)),
            HttpResponse(200, _page("searchResult3", ["q0", "q1", "q2"])),
        ]
    )

    tracks = _source(transport=transport).tracks()

    assert len(tracks) == PAGE_SIZE + 3
    assert len({track.identifier for track in tracks}) == PAGE_SIZE + 3
    premieres = _parametres(transport.urls[0])
    assert premieres["query"] == ""
    assert premieres["songCount"] == str(PAGE_SIZE)
    assert premieres["songOffset"] == "0"
    assert _parametres(transport.urls[1])["songOffset"] == str(PAGE_SIZE)


def test_un_serveur_qui_ignore_l_offset_ne_fait_pas_boucler_le_parcours(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # §2.6.2 : un paramètre inconnu est ignoré en silence. Un serveur qui
    # ignorerait l'offset resservirait la même page pleine indéfiniment.
    page = HttpResponse(200, _page("searchResult3", [f"p{index}" for index in range(PAGE_SIZE)]))
    transport = ScriptedTransport([page, page])

    with caplog.at_level(logging.WARNING):
        tracks = _source(transport=transport).tracks()

    assert len(tracks) == PAGE_SIZE
    assert "ressert" in caplog.text


def test_le_filtre_par_genre_passe_par_get_songs_by_genre_pagine() -> None:
    transport = ScriptedTransport(HttpResponse(200, _page("songsByGenre", ["r1", "r2"])))

    tracks = _source(transport=transport).tracks(genre="Rock")

    assert [track.identifier for track in tracks] == ["r1", "r2"]
    params = _parametres(transport.urls[0])
    assert "getSongsByGenre" in transport.urls[0]
    assert params["genre"] == "Rock"
    assert params["count"] == str(PAGE_SIZE)
    assert params["offset"] == "0"


# ── Le cache : la bibliothèque n'est pas re-parcourue à chaque tirage ──────


def test_un_second_tirage_dans_la_fenetre_ne_refait_aucun_appel() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    clock = FrozenClock(UN_SOIR)
    source = _source(transport=transport, cache=3600.0, clock=clock)

    premier = source.tracks()
    clock.advance(timedelta(minutes=59))
    second = source.tracks()

    assert len(transport.urls) == 1
    assert [track.identifier for track in second] == [track.identifier for track in premier]


def test_le_cache_expire_et_le_parcours_est_refait() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    clock = FrozenClock(UN_SOIR)
    source = _source(transport=transport, cache=3600.0, clock=clock)

    source.tracks()
    clock.advance(timedelta(hours=1))
    source.tracks()

    assert len(transport.urls) == 2


def test_chaque_genre_a_sa_propre_entree_de_cache() -> None:
    transport = ScriptedTransport(
        [
            HttpResponse(200, DEUX_CHANSONS),
            HttpResponse(200, _page("songsByGenre", ["r1"])),
        ]
    )
    source = _source(transport=transport, cache=3600.0)

    source.tracks()
    source.tracks(genre="Rock")
    source.tracks()
    source.tracks(genre="Rock")

    assert len(transport.urls) == 2


def test_une_duree_nulle_refait_les_appels_a_chaque_tirage() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    source = _source(transport=transport, cache=0.0)

    source.tracks()
    source.tracks()

    assert len(transport.urls) == 2


def test_une_panne_n_entre_pas_au_cache() -> None:
    transport = ScriptedTransport(
        [
            HttpResponse(200, PAGE_HTML_EN_200),
            HttpResponse(200, DEUX_CHANSONS),
        ]
    )
    source = _source(transport=transport, cache=3600.0)

    with pytest.raises(SourceUnavailable):
        source.tracks()

    assert len(source.tracks()) == 2


def test_muter_le_resultat_ne_corrompt_pas_le_cache() -> None:
    transport = ScriptedTransport(HttpResponse(200, DEUX_CHANSONS))
    source = _source(transport=transport, cache=3600.0)

    source.tracks().clear()

    assert len(source.tracks()) == 2


# ── Les pièges n°4 et n°5 : genre inexistant, genre manquant ───────────────


def test_un_genre_inexistant_rend_une_liste_vide_sans_lever() -> None:
    transport = ScriptedTransport(HttpResponse(200, GENRE_INEXISTANT))
    source = _source(transport=transport)

    assert source.tracks(genre="Genre qui n'existe pas") == []
    assert _parametres(transport.urls[0])["genre"] == "Genre qui n'existe pas"


def test_une_piste_sans_genre_est_conservee() -> None:
    tracks = _source(DEUX_CHANSONS).tracks()

    assert [track.genre for track in tracks] == ["Chanson française", None]
    assert tracks[0].duration.total_seconds() == 213
    assert tracks[0].identifier == "0f1a"


def test_l_annee_est_mappee_et_son_absence_vaut_sans_annee() -> None:
    """docs/subsonic.md §4.1 : `year` est un entier, absent sur 6,7 % des
    pistes ; toute autre forme vaut « sans année », jamais un rejet."""
    reponse = """
{"subsonic-response": {"status": "ok", "version": "1.16.1", "searchResult3": {"song": [
  {"id": "a1", "title": "Datée", "artist": "Un artiste", "duration": 200, "year": 1977},
  {"id": "a2", "title": "Sans année", "artist": "Un artiste", "duration": 200},
  {"id": "a3", "title": "Année étrange", "artist": "Un artiste", "duration": 200, "year": "1977"},
  {"id": "a4", "title": "Année booléenne", "artist": "Un artiste", "duration": 200, "year": true}
]}}}
"""
    tracks = _source(reponse).tracks()

    assert [track.year for track in tracks] == [1977, None, None, None]


def test_une_piste_inexploitable_est_ecartee_sans_faire_echouer_l_appel(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        tracks = _source(CHANSONS_ABIMEES).tracks()

    assert [track.identifier for track in tracks] == ["0f1e"]
    assert caplog.text.count("ignorée") == 4


# ── Le piège n°3 : `search3` ramène aussi d'autres artistes ────────────────


def test_les_pistes_d_un_artiste_excluent_les_autres_artistes() -> None:
    transport = ScriptedTransport(HttpResponse(200, RECHERCHE_ARTISTE))
    tracks = _source(transport=transport).tracks_by("Un artiste")

    assert [track.identifier for track in tracks] == ["1a", "1c"]
    params = _parametres(transport.urls[0])
    assert params["query"] == "Un artiste"
    assert params["songCount"] == "50"


def test_un_artiste_absent_de_la_bibliotheque_rend_une_liste_vide() -> None:
    assert _source(GENRE_INEXISTANT).tracks_by("Personne") == []


# ── Le piège n°6 : les deux régimes d'erreur ───────────────────────────────


def test_un_404_sans_corps_subsonic_leve_une_source_indisponible() -> None:
    source = _source(PAGE_404, code=404)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "404" in str(failure.value)


def test_une_page_html_rendue_en_200_leve_une_source_indisponible() -> None:
    source = _source(PAGE_HTML_EN_200)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "JSON" in str(failure.value)


def test_un_json_tronque_leve_une_source_indisponible() -> None:
    source = _source(JSON_TRONQUE)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "JSON" in str(failure.value)


def test_un_json_sans_enveloppe_subsonic_leve_une_source_indisponible() -> None:
    source = _source(JSON_SANS_ENVELOPPE)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "subsonic-response" in str(failure.value)


def test_un_corps_json_qui_n_est_pas_un_objet_leve_une_source_indisponible() -> None:
    source = _source("[1, 2, 3]")

    with pytest.raises(SourceUnavailable):
        source.tracks()


def test_un_serveur_injoignable_devient_une_source_indisponible() -> None:
    source = _source(transport=UnreachableTransport())

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks()

    assert "injoignable" in str(failure.value)


# ── Les genres connus ──────────────────────────────────────────────────────


def test_les_genres_sont_rendus_dedoublonnes_et_ordonnes() -> None:
    assert _source(GENRES).genres() == ["Chanson française", "Rock"]


def test_une_reponse_sans_genres_rend_une_liste_vide() -> None:
    assert _source('{"subsonic-response": {"status": "ok"}}').genres() == []


def test_des_genres_d_un_type_inattendu_rendent_une_liste_vide() -> None:
    body = '{"subsonic-response": {"status": "ok", "genres": {"genre": "Rock"}}}'

    assert _source(body).genres() == []


# ── Le transport réel, sans réseau ─────────────────────────────────────────


class _ReponseUrllib:
    """Ce que `urlopen` rend : un gestionnaire de contexte avec un code et un corps."""

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._corps = body

    def __enter__(self) -> "_ReponseUrllib":
        return self

    def __exit__(
        self,
        genre: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return self._corps


def test_le_transport_rend_le_code_et_le_corps() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        return _ReponseUrllib(200, b'{"ok": true}')

    transport = UrllibTransport(timeout_seconds=1.0, ouvrir=ouvrir)

    answer = transport.fetch("http://exemple.local/rest/ping")

    assert answer == HttpResponse(code=200, body='{"ok": true}')


def test_le_transport_rend_une_erreur_http_comme_une_reponse_ordinaire() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        raise urllib.error.HTTPError(
            url="http://exemple.local/rest/inconnu",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=io.BytesIO(PAGE_404.encode("utf-8")),
        )

    transport = UrllibTransport(timeout_seconds=1.0, ouvrir=ouvrir)
    answer = transport.fetch("http://exemple.local/rest/inconnu")

    assert answer.code == 404
    assert answer.body == PAGE_404


def test_le_transport_traduit_une_panne_de_connexion() -> None:
    def ouvrir(requete: object, timeout: float) -> _ReponseUrllib:  # noqa: ARG001
        raise urllib.error.URLError("connexion refusée")

    transport = UrllibTransport(timeout_seconds=1.0, ouvrir=ouvrir)

    with pytest.raises(SourceUnavailable) as failure:
        transport.fetch("http://exemple.local/rest/ping")

    assert "injoignable" in str(failure.value)


def test_le_transport_par_defaut_existe_sans_etre_appele() -> None:
    """Construire le transport réel ne touche à rien : rien n'est ouvert avant un appel."""
    transport = UrllibTransport(timeout_seconds=1.0)

    assert transport is not None


def test_entree_rend_une_url_de_flux_portant_le_jeton() -> None:
    """La chaîne de diffusion ouvre cette URL telle quelle : c'est le seul
    endroit du projet où l'identifiant opaque redevient lisible."""
    source = _source()
    track = Track(
        identifier="piste-1",
        title="un titre",
        artist="un artiste",
        genre=None,
        duration=timedelta(seconds=180),
    )
    url = source.entry(track)
    assert "stream.view" in url
    assert "id=piste-1" in url
    assert "t=" in url and "s=" in url
    assert MOT_DE_PASSE not in url


# ── Les listes de lecture (docs/subsonic.md §2.6) ─────────────────────────

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
    transport = ScriptedTransport(
        [HttpResponse(200, LISTES), HttpResponse(200, LISTE_CHLOE)],
    )
    source = _source(transport=transport)

    tracks = source.tracks_from_playlist("Chloé")

    assert [track.title for track in tracks] == ["La première", "Sans étiquette"]
    assert _parametres(transport.urls[0])["u"] == UTILISATEUR
    assert _parametres(transport.urls[1])["id"] == "pl-1"


def test_le_song_count_annonce_n_est_pas_ce_qui_est_rendu() -> None:
    """67 annoncés, deux entrées rendues : une liste se juge sur ses entrées
    (docs/subsonic.md §2.6.1)."""
    source = _source(
        transport=ScriptedTransport([HttpResponse(200, LISTES), HttpResponse(200, LISTE_CHLOE)])
    )

    assert len(source.tracks_from_playlist("Chloé")) == 2


def test_une_piste_de_liste_sans_genre_reste_retenue() -> None:
    source = _source(
        transport=ScriptedTransport([HttpResponse(200, LISTES), HttpResponse(200, LISTE_CHLOE)])
    )

    tracks = source.tracks_from_playlist("Chloé")

    assert tracks[0].genre == "Chanson française"
    assert tracks[1].genre is None


def test_un_nom_de_liste_inconnu_rend_une_liste_vide_sans_lever(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Le repli sur le tirage libre se décide au-dessus (SPECS.md §7 n°21)."""
    transport = ScriptedTransport([HttpResponse(200, LISTES)])
    source = _source(transport=transport)

    with caplog.at_level(logging.INFO):
        tracks = source.tracks_from_playlist("Inconnue")

    assert tracks == []
    assert len(transport.urls) == 1
    assert "Inconnue" in caplog.text


def test_aucune_liste_declaree_rend_une_liste_vide() -> None:
    source = _source(transport=ScriptedTransport([HttpResponse(200, AUCUNE_LISTE)]))

    assert source.tracks_from_playlist("Chloé") == []


def test_deux_listes_homonymes_retiennent_la_premiere_en_le_disant(
    caplog: pytest.LogCaptureFixture,
) -> None:
    transport = ScriptedTransport(
        [HttpResponse(200, LISTES_HOMONYMES), HttpResponse(200, LISTE_CHLOE)]
    )
    source = _source(transport=transport)

    with caplog.at_level(logging.WARNING):
        source.tracks_from_playlist("Chloé")

    assert _parametres(transport.urls[1])["id"] == "pl-1"
    assert "Chloé" in caplog.text


def test_une_liste_sans_entree_rend_une_liste_vide(caplog: pytest.LogCaptureFixture) -> None:
    source = _source(
        transport=ScriptedTransport([HttpResponse(200, LISTES), HttpResponse(200, LISTE_VIDE)])
    )

    with caplog.at_level(logging.INFO):
        tracks = source.tracks_from_playlist("Chloé")

    assert tracks == []
    assert "Chloé" in caplog.text


def test_les_entrees_abimees_d_une_liste_sont_ecartees_et_les_autres_gardees() -> None:
    source = _source(
        transport=ScriptedTransport([HttpResponse(200, LISTES), HttpResponse(200, LISTE_ABIMEE)])
    )

    tracks = source.tracks_from_playlist("Chloé")

    assert [track.identifier for track in tracks] == ["0f2d"]


def test_une_liste_disparue_entre_les_deux_appels_leve_une_source_indisponible() -> None:
    """La liste existait à l'instant de `getPlaylists` et plus à celui de
    `getPlaylist` : HTTP 200, code 70. C'est une panne de source, et le repli
    est celui que la charnière applique déjà à toutes les pannes."""
    source = _source(
        transport=ScriptedTransport(
            [HttpResponse(200, LISTES), HttpResponse(200, LISTE_INTROUVABLE)]
        )
    )

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks_from_playlist("Chloé")

    assert "70" in str(failure.value)
    assert "playlist not found" in str(failure.value)


def test_une_page_html_en_200_a_la_place_des_listes_leve_une_source_indisponible() -> None:
    source = _source(PAGE_HTML_EN_200)

    with pytest.raises(SourceUnavailable) as failure:
        source.tracks_from_playlist("Chloé")

    assert "getPlaylists" in str(failure.value)


def test_des_listes_sans_enveloppe_attendue_rendent_une_liste_vide() -> None:
    """Un contenant absent ou d'un type inattendu n'est pas une panne : c'est
    une bibliothèque sans liste de lecture."""
    sans_contenant = '{"subsonic-response": {"status": "ok", "playlists": {"playlist": "rien"}}}'
    source = _source(transport=ScriptedTransport([HttpResponse(200, sans_contenant)]))

    assert source.tracks_from_playlist("Chloé") == []


def test_une_liste_dont_les_entrees_ont_un_type_inattendu_rend_une_liste_vide() -> None:
    entrees_folles = '{"subsonic-response": {"status": "ok", "playlist": {"entry": "rien"}}}'
    source = _source(
        transport=ScriptedTransport([HttpResponse(200, LISTES), HttpResponse(200, entrees_folles)])
    )

    assert source.tracks_from_playlist("Chloé") == []


def test_aucun_secret_ne_parait_dans_les_journaux_d_une_liste_de_lecture(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Les URL portent le jeton : elles n'ont leur place dans aucun journal."""
    source = _source(transport=ScriptedTransport([HttpResponse(200, LISTES)]))

    with caplog.at_level(logging.DEBUG):
        source.tracks_from_playlist("Inconnue")

    assert MOT_DE_PASSE not in caplog.text
    assert "/rest/" not in caplog.text
