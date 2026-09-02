"""Source Subsonic (protocole), relevée contre Navidrome.

Le code suit docs/subsonic.md. Les comportements constatés qui le contraignent :

1. Une authentification refusée arrive en HTTP 200 (§1.1). `status` est lu dans
   le corps à chaque appel, avant toute donnée.
2. La bibliothèque se parcourt entière, par pages de 500 (§2.7). La fin d'un
   parcours se reconnaît à une page plus courte que demandé, jamais à un
   compteur annoncé (§2.7.3).
3. `search3` ramène aussi d'autres artistes (§2.5). Le filtre sur l'égalité
   exacte du nom évite qu'`encore` serve un artiste non demandé.
4. Un genre inexistant rend `ok` et zéro piste (§2.2). C'est une liste vide, pas
   une erreur : le repli se décide au-dessus.
5. `genre` manque sur près d'une piste sur cinq (§4). Ces pistes sont conservées
   avec `genre=None`.
6. Deux régimes d'erreur (§5) : applicatif en HTTP 200 avec un code dans le
   corps, routage en HTTP 404 sans corps Subsonic. Les deux deviennent une
   `SourceUnavailable`.
"""

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from webradio.adapters.config.schema import SubsonicCredentials, SubsonicSettings
from webradio.core.clock import Clock
from webradio.core.models import Track
from webradio.core.rng import Random
from webradio.core.sources import SourceUnavailable

journal = logging.getLogger(__name__)

API_PATH = "/rest"
API_VERSION = "1.16.1"
CLIENT_NAME = "local-webradio"
FORMAT_REPONSE = "json"
HTTP_OK = 200

# Taille d'une page de parcours : 500 est le plafond de `getSongsByGenre`, qui
# tronque au-delà sans le signaler (docs/subsonic.md §2.7.2).
PAGE_SIZE = 500

# Le sel doit seulement varier d'un appel à l'autre. Il est tiré par le hasard
# injecté, car `random` et `secrets` sont réservés à `core/rng.py`.
SALT_ALPHABET = list("0123456789abcdef")
SALT_LENGTH = 12


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Une réponse HTTP : code et corps.

    Le corps est du texte brut, pas du JSON analysé : le serveur peut répondre
    autre chose que du JSON.
    """

    code: int
    body: str


class HttpTransport(Protocol):
    """Le seul accès réseau de ce dossier.

    Le `Protocol` permet de tester l'adaptateur contre des réponses littérales,
    sans réseau (AGENTS.md §4).
    """

    def fetch(self, url: str) -> HttpResponse: ...


class UrllibTransport:
    """Transport réel, sur `urllib`.

    Une erreur HTTP est rendue comme une réponse ordinaire, l'adaptateur examine
    le code. Une panne de connexion, sans réponse, lève `SourceUnavailable`.
    """

    def __init__(
        self,
        timeout_seconds: float,
        ouvrir: Callable[..., Any] | None = None,
    ) -> None:
        self._delai = timeout_seconds
        self._ouvrir = urllib.request.urlopen if ouvrir is None else ouvrir

    def fetch(self, url: str) -> HttpResponse:
        requete = urllib.request.Request(url, headers={"User-Agent": CLIENT_NAME})
        try:
            with self._ouvrir(requete, timeout=self._delai) as answer:
                return HttpResponse(code=int(answer.status), body=_texte(answer.read()))
        except urllib.error.HTTPError as error:
            return HttpResponse(code=int(error.code), body=_texte(error.read()))
        except OSError as error:
            message = f"serveur Subsonic injoignable : {error}"
            raise SourceUnavailable(message) from error


def _texte(brut: bytes) -> str:
    return brut.decode("utf-8", errors="replace")


class SubsonicSource:
    """Une bibliothèque servie en Subsonic, vue comme une `MusicSource`."""

    def __init__(
        self,
        credentials: SubsonicCredentials,
        config: SubsonicSettings,
        random: Random,
        transport: HttpTransport,
        clock: Clock,
    ) -> None:
        self._identifiants = credentials
        self._reglages = config
        self._hasard = random
        self._transport = transport
        self._horloge = clock
        self._duree_cache = timedelta(seconds=config.cache_seconds)
        self._cache: dict[str | None, tuple[datetime, list[Track]]] = {}

    def tracks(self, genre: str | None = None) -> list[Track]:
        """La bibliothèque entière, ou tout un genre, jamais un échantillon.

        Le tirage appartient au noyau (docs/subsonic.md §2.4) et doit voir
        toutes les pistes.

        Le parcours coûte une dizaine d'appels : il est mis en cache pendant
        `cache_seconds`, une entrée par genre. Seul un parcours réussi entre au
        cache, une panne se propage telle quelle (SPECS.md §5). Un ajout sur le
        serveur n'apparaît qu'à l'expiration. `tracks_by` et les listes de
        lecture ne sont pas mises en cache : l'encore est rare, et une liste
        renommée ne doit pas rester résolue (§2.6).
        """
        now = self._horloge.now()
        entry = self._cache.get(genre)
        if entry is not None and now - entry[0] < self._duree_cache:
            return list(entry[1])
        tracks = self._parcourir(genre)
        self._cache[genre] = (now, tracks)
        return list(tracks)

    def _parcourir(self, genre: str | None) -> list[Track]:
        if genre is None:
            tracks = self._paginer(
                "search3",
                {"query": "", "artistCount": "0", "albumCount": "0"},
                container="searchResult3",
                count_key="songCount",
                offset_key="songOffset",
            )
        else:
            tracks = self._paginer(
                "getSongsByGenre",
                {"genre": genre},
                container="songsByGenre",
                count_key="count",
                offset_key="offset",
            )
            if not tracks:
                journal.info(
                    "le genre « %s » ne rend aucune piste : le repli se décide plus haut", genre
                )
        return tracks

    def _paginer(
        self,
        method: str,
        params: Mapping[str, str],
        *,
        container: str,
        count_key: str,
        offset_key: str,
    ) -> list[Track]:
        """Réunit toutes les pages ; la fin est une page plus courte que demandé.

        Les compteurs annoncés ne sont pas lus, ils divergent des pistes rendues
        (docs/subsonic.md §2.7.3). Si le serveur ignore l'offset (§2.6.2), la
        même page revient indéfiniment : une page sans piste nouvelle arrête le
        parcours avec un avertissement.
        """
        gathered: list[Track] = []
        seen: set[str] = set()
        offset = 0
        while True:
            envelope = self._appeler(
                method,
                {**params, count_key: str(PAGE_SIZE), offset_key: str(offset)},
            )
            page = self._pistes_de_la_liste(envelope, container)
            fresh = [track for track in page if track.identifier not in seen]
            if page and not fresh:
                journal.warning(
                    "« %s » ressert les mêmes pistes malgré l'offset %d : parcours arrêté à %d",
                    method,
                    offset,
                    len(gathered),
                )
                return gathered
            gathered.extend(fresh)
            seen.update(track.identifier for track in fresh)
            if len(page) < PAGE_SIZE:
                return gathered
            offset += len(page)

    def tracks_by(self, artist: str) -> list[Track]:
        """Les pistes de cet artiste, filtrées par égalité exacte du nom.

        `search3` ramène aussi d'autres artistes (docs/subsonic.md §2.5).
        """
        envelope = self._appeler(
            "search3",
            {
                "query": artist,
                "songCount": str(self._reglages.artist_results),
                "artistCount": "0",
                "albumCount": "0",
            },
        )
        trouvees = self._pistes_de_la_liste(envelope, "searchResult3")
        retenues = [track for track in trouvees if track.artist == artist]
        ecartees = len(trouvees) - len(retenues)
        if ecartees:
            journal.debug(
                "%d résultat(s) écarté(s) pour « %s » : la recherche ramène d'autres artistes",
                ecartees,
                artist,
            )
        return retenues

    def genres(self) -> list[str]:
        """Les genres connus du serveur, dédoublonnés et triés.

        L'ordre du serveur n'est pas garanti stable.
        """
        envelope = self._appeler("getGenres", {})
        content = envelope.get("genres")
        entrees = content.get("genre") if isinstance(content, Mapping) else None
        if not isinstance(entrees, Sequence) or isinstance(entrees, str):
            return []
        names = {
            entry["value"]
            for entry in entrees
            if isinstance(entry, Mapping) and isinstance(entry.get("value"), str) and entry["value"]
        }
        return sorted(names)

    def tracks_from_playlist(self, name: str) -> list[Track]:
        """Les pistes d'une liste de lecture désignée par son nom.

        Deux appels : le TOML déclare un nom, `getPlaylist` réclame un
        identifiant. La traduction par `getPlaylists` est refaite à chaque fois,
        pour qu'une liste renommée ne reste pas résolue sur un identifiant
        périmé.

        Un nom inconnu rend une liste vide, comme `tracks()` pour un genre
        inconnu : le repli se décide au-dessus (SPECS.md §7 n°21).

        `songCount` n'est jamais lu, il diverge des entrées rendues
        (docs/subsonic.md §2.6.1).
        """
        identifier = self._identifiant_de_liste(name)
        if identifier is None:
            journal.info(
                "aucune liste de lecture ne s'appelle « %s » : le repli se décide plus haut", name
            )
            return []
        envelope = self._appeler("getPlaylist", {"id": identifier})
        tracks = self._entrees_de_liste(envelope)
        if not tracks:
            journal.info(
                "la liste « %s » ne rend aucune piste : le repli se décide plus haut", name
            )
        return tracks

    def _identifiant_de_liste(self, name: str) -> str | None:
        """Traduit un nom de liste en identifiant Subsonic, ou `None`.

        Égalité exacte : deux listes peuvent ne différer que par la casse.
        """
        envelope = self._appeler("getPlaylists", {})
        content = envelope.get("playlists")
        brutes = content.get("playlist") if isinstance(content, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return None
        trouves: list[str] = []
        for brute in brutes:
            if not isinstance(brute, Mapping):
                continue
            identifier = brute.get("id")
            if brute.get("name") == name and isinstance(identifier, str) and identifier:
                trouves.append(identifier)
        if not trouves:
            return None
        if len(trouves) > 1:
            journal.warning(
                "%d listes de lecture s'appellent « %s » : la première est retenue",
                len(trouves),
                name,
            )
        return trouves[0]

    def _entrees_de_liste(self, envelope: Mapping[str, Any]) -> list[Track]:
        """Les entrées d'une liste, sous la clé `entry` et non `song`."""
        content = envelope.get("playlist")
        brutes = content.get("entry") if isinstance(content, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        return [track for brute in brutes if (track := _en_piste(brute)) is not None]

    def entry(self, track: Track) -> str:
        """L'URL de flux de la piste, jeton compris.

        `stream` plutôt que `download` : même contenu sur l'instance relevée, et
        c'est l'endpoint prévu pour la lecture.

        L'URL porte le jeton : elle ne doit jamais paraître dans un journal
        (AGENTS.md §2).
        """
        return self._url("stream.view", {"id": track.identifier})

    def _sel(self) -> str:
        return "".join(self._hasard.pick(SALT_ALPHABET) for _ in range(SALT_LENGTH))

    def _url(self, method: str, params: Mapping[str, str]) -> str:
        """Construit l'URL authentifiée par jeton.

        Seul `md5(mot de passe + sel)` circule, avec un sel neuf à chaque appel
        (docs/subsonic.md §1).
        """
        salt = self._sel()
        empreinte = hashlib.md5((self._identifiants.password + salt).encode("utf-8")).hexdigest()
        commun = {
            "u": self._identifiants.username,
            "t": empreinte,
            "s": salt,
            "v": API_VERSION,
            "c": CLIENT_NAME,
            "f": FORMAT_REPONSE,
        }
        requete = urllib.parse.urlencode({**commun, **params})
        return f"{self._identifiants.url}{API_PATH}/{method}?{requete}"

    def _appeler(self, method: str, params: Mapping[str, str]) -> Mapping[str, Any]:
        """Un appel, ou `SourceUnavailable` en cas d'échec.

        Les messages ne contiennent jamais l'URL, qui porte le jeton
        (AGENTS.md §2).
        """
        try:
            answer = self._transport.fetch(self._url(method, params))
        except OSError as error:
            message = f"« {method} » : serveur Subsonic injoignable ({error})"
            raise SourceUnavailable(message) from error

        if answer.code != HTTP_OK:
            message = f"« {method} » a répondu HTTP {answer.code}, sans corps Subsonic exploitable"
            raise SourceUnavailable(message)

        try:
            donnees = json.loads(answer.body)
        except json.JSONDecodeError as error:
            message = (
                f"« {method} » a répondu HTTP 200 avec un corps qui n'est pas du JSON "
                "(une page d'erreur intercalée, ou une réponse tronquée)"
            )
            raise SourceUnavailable(message) from error

        envelope = donnees.get("subsonic-response") if isinstance(donnees, Mapping) else None
        if not isinstance(envelope, Mapping):
            message = f"« {method} » a répondu du JSON sans enveloppe « subsonic-response »"
            raise SourceUnavailable(message)

        if envelope.get("status") != "ok":
            raise SourceUnavailable(_echec(method, envelope))
        return envelope

    def _pistes_de_la_liste(self, envelope: Mapping[str, Any], contenant: str) -> list[Track]:
        """Extrait les pistes d'une réponse valable.

        Un contenant absent est normal : c'est ce que rend un genre inexistant,
        avec `status: ok` (docs/subsonic.md §2.2).
        """
        content = envelope.get(contenant)
        brutes = content.get("song") if isinstance(content, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        tracks = [track for brute in brutes if (track := _en_piste(brute)) is not None]
        return tracks


def _echec(method: str, envelope: Mapping[str, Any]) -> str:
    """Le message d'un refus applicatif, arrivé en HTTP 200.

    Le code Subsonic est repris tel quel : il distingue un mot de passe faux (40)
    d'un identifiant inconnu (70).
    """
    error = envelope.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        texte = error.get("message")
        return f"« {method} » a échoué en HTTP 200 : code Subsonic {code} ({texte})"
    return f"« {method} » a échoué en HTTP 200, sans détail d'erreur"


def _en_piste(brute: Any) -> Track | None:
    """Traduit une chanson Subsonic en `Track`, ou `None` avec un avertissement.

    `genre` et `year` sont facultatifs. Identifiant, titre, artiste et durée sont
    obligatoires : sans eux la piste ne peut être ni résolue, ni soumise à la
    non-répétition.
    """
    if not isinstance(brute, Mapping):
        journal.warning("entrée ignorée : une chanson est attendue, pas %s", type(brute).__name__)
        return None
    identifier = brute.get("id")
    title = brute.get("title")
    artist = brute.get("artist")
    duration = brute.get("duration")
    genre = brute.get("genre")
    year = brute.get("year")
    if (
        not isinstance(identifier, str)
        or not isinstance(title, str)
        or not isinstance(artist, str)
        or isinstance(duration, bool)
        or not isinstance(duration, int)
    ):
        journal.warning("chanson ignorée : champ obligatoire absent ou d'un type inattendu")
        return None
    try:
        return Track(
            identifier=identifier,
            title=title,
            artist=artist,
            genre=genre if isinstance(genre, str) and genre else None,
            duration=timedelta(seconds=duration),
            # Un entier quand la piste est datée (docs/subsonic.md §4.1), sinon
            # sans année.
            year=year if isinstance(year, int) and not isinstance(year, bool) else None,
        )
    except ValueError as error:
        journal.warning("chanson ignorée : %s", error)
        return None
