"""La source Subsonic — le protocole ; Navidrome est l'instance relevée.

Tout ce fichier est écrit contre [docs/navidrome.md](../../../docs/navidrome.md),
un relevé établi contre une instance réelle. Six comportements constatés y
commandent le code, et chacun serait un défaut audible s'il était ignoré :

1. **Une authentification refusée arrive en HTTP 200** (§1.1). `status` est donc
   lu dans le corps à *chaque* appel, avant toute donnée : un client qui se
   fierait au code HTTP prendrait un mot de passe faux pour une bibliothèque
   vide, et la radio se tairait en annonçant qu'elle va bien.
2. **`getRandomSongs` tronque à 500 en silence** (§2.1). La demande est donc
   plafonnée ici, une fois, plutôt que crue sur parole.
3. **`search3` ramène aussi d'autres artistes** (§2.5). Le filtre sur l'égalité
   exacte du nom est ce qui empêche `encore` de servir un artiste que
   l'auditeur n'a pas demandé.
4. **Un genre inexistant rend `ok` et zéro piste** (§2.2). C'est une liste vide,
   pas une erreur : le repli sur le tirage libre se décide au-dessus.
5. **`genre` manque sur près d'une piste sur cinq** (§4). Ces pistes sont
   conservées avec `genre=None` : les refuser amputerait la radio de 18 % de la
   bibliothèque.
6. **Deux régimes d'erreur** (§5) : applicatif en HTTP 200 avec un code dans le
   corps, routage en HTTP 404 sans corps Subsonic. Les deux deviennent une
   `SourceIndisponible`, la seule chose que le noyau sait lire.
"""

import hashlib
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from webradio.adapters.config.schema import SubsonicCredentials, SubsonicSettings
from webradio.core.models import Track
from webradio.core.rng import Random
from webradio.core.sources import SourceUnavailable

journal = logging.getLogger(__name__)

API_PATH = "/rest"
API_VERSION = "1.16.1"
CLIENT_NAME = "local-webradio"
FORMAT_REPONSE = "json"
HTTP_OK = 200

# Le plafond de `getRandomSongs`, constaté : `size=501` rend 500 pistes avec
# `status: ok`. Ce n'est pas un réglage, c'est une propriété du serveur.
SAMPLE_CAP = 500

# Le sel accompagne le jeton dans l'URL ; sa seule exigence est de varier d'un
# appel à l'autre. Il est tiré par le hasard injecté, parce que `random` et
# `secrets` sont interdits partout ailleurs que dans `core/rng.py`.
SALT_ALPHABET = list("0123456789abcdef")
SALT_LENGTH = 12


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Ce que l'adaptateur a besoin de savoir d'une réponse : un code et un corps.

    Le corps est du texte et non du JSON déjà analysé : la seule chose dont on
    soit sûr, c'est qu'un serveur peut répondre autre chose que ce qu'il promet.
    """

    code: int
    body: str


class HttpTransport(Protocol):
    """Le seul point par lequel ce dossier touche au réseau.

    L'isoler derrière un `Protocol` est ce qui permet de tester l'adaptateur
    contre des réponses littérales, sans réseau (AGENTS.md §4).
    """

    def fetch(self, url: str) -> HttpResponse: ...


class UrllibTransport:
    """Le transport réel, sur `urllib` de la bibliothèque standard.

    Une erreur HTTP est rendue comme une réponse ordinaire — le code fait partie
    de ce que l'adaptateur doit examiner — tandis qu'une panne de connexion, qui
    ne produit aucune réponse, devient tout de suite une `SourceIndisponible`.
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
    ) -> None:
        self._identifiants = credentials
        self._reglages = config
        self._hasard = random
        self._transport = transport
        self._taille = self._plafonner(config.sample_size)

    def _plafonner(self, requested: int) -> int:
        """Le dépassement est ramené au plafond une fois, au démarrage, et dit.

        Le serveur tronque sans rien signaler : croire une demande de 1000
        pistes reviendrait à tirer dans 500 en pensant tirer dans 1000.
        """
        if requested > SAMPLE_CAP:
            journal.warning(
                "taille d'échantillon %d ramenée à %d : le serveur tronque en silence au-delà",
                requested,
                SAMPLE_CAP,
            )
            return SAMPLE_CAP
        return requested

    def tracks(self, genre: str | None = None) -> list[Track]:
        params = {"size": str(self._taille)}
        if genre is not None:
            params["genre"] = genre
        envelope = self._appeler("getRandomSongs", params)
        tracks = self._pistes_de_la_liste(envelope, "randomSongs")
        if genre is not None and not tracks:
            journal.info(
                "le genre « %s » ne rend aucune piste : le repli se décide plus haut", genre
            )
        return tracks

    def tracks_by(self, artist: str) -> list[Track]:
        """Les pistes de cet artiste, et de lui seul.

        `search3` ramène aussi des voisins : sur 50 résultats relevés pour un
        artiste, 49 étaient de lui et un ne l'était pas. Sans l'égalité exacte,
        `encore` servirait cet intrus.
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
        """Les genres connus du serveur, dédoublonnés et ordonnés.

        L'ordre du serveur n'est pas garanti stable ; le trier rend deux
        démarrages comparables, ce que le tri seul suffit à obtenir.
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

        Deux appels, et c'est irréductible : le TOML déclare un **nom**
        (`playlist = "Chloé"`) tandis que `getPlaylist` réclame un identifiant.
        `getPlaylists` fait la traduction, et elle est refaite à chaque fois —
        une liste renommée entre deux programmes ne doit pas rester résolue sur
        un identifiant périmé.

        Un nom inconnu rend une liste vide plutôt que de lever : c'est la
        convention de `pistes()` pour un genre inconnu, et le repli sur le
        tirage libre se décide au-dessus (SPECS.md §7 n°21).

        **`songCount` n'est jamais lu** : il a été constaté à 67 sur une liste
        qui n'a rendu que 32 entrées, toutes distinctes, sans que la cause soit
        établie (docs/navidrome.md §2.6.1). Une liste se juge sur ce que
        `getPlaylist` rend.
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
        """Traduit un nom de liste en identifiant Subsonic, par égalité exacte.

        L'égalité exacte plutôt qu'une comparaison indulgente : deux listes
        peuvent différer par une seule majuscule, et servir l'une pour l'autre
        se remarquerait à l'antenne bien plus tard que le repli journalisé.
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
        """Les entrées d'une liste, sous la clé `entry` et non `song`.

        C'est la seule différence de forme avec les autres réponses : les
        entrées sont des chansons ordinaires, converties comme partout ailleurs,
        et les incomplètes sont écartées de la même façon.
        """
        content = envelope.get("playlist")
        brutes = content.get("entry") if isinstance(content, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        return [track for brute in brutes if (track := _en_piste(brute)) is not None]

    def entry(self, track: Track) -> str:
        """L'URL de flux de la piste, jeton compris.

        `stream` plutôt que `download` : le relevé a constaté qu'ils rendent le
        même octet près sur cette instance, et `stream` est celui que la
        spécification Subsonic destine à la lecture.

        L'URL porte le jeton d'authentification : elle ne doit donc **jamais**
        paraître dans un journal (AGENTS.md §2). Elle est rendue à la chaîne de
        diffusion, qui l'ouvre et ne la consigne pas.
        """
        return self._url("stream.view", {"id": track.identifier})

    def _sel(self) -> str:
        return "".join(self._hasard.pick(SALT_ALPHABET) for _ in range(SALT_LENGTH))

    def _url(self, method: str, params: Mapping[str, str]) -> str:
        """Construit l'appel authentifié par jeton dérivé.

        Le mot de passe ne circule jamais : seul `md5(motdepasse + sel)` part sur
        le réseau, et le sel change à chaque appel (docs/navidrome.md §1).
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
        """Un appel, et les quatre façons dont il peut mal tourner.

        Aucun message ne contient l'URL : elle porte le jeton et le sel, et un
        journal n'est pas un endroit où les écrire (AGENTS.md §2).
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

        Un contenant absent n'est pas une anomalie : c'est ce que rend un genre
        inexistant, avec `status: ok` (docs/navidrome.md §2.2).
        """
        content = envelope.get(contenant)
        brutes = content.get("song") if isinstance(content, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        tracks = [track for brute in brutes if (track := _en_piste(brute)) is not None]
        return tracks


def _echec(method: str, envelope: Mapping[str, Any]) -> str:
    """Le message d'un refus applicatif, arrivé en HTTP 200.

    Le code Subsonic est repris tel quel : c'est lui qui distingue un mot de
    passe faux (40) d'un identifiant inconnu (70), et la distinction est ce qui
    évite de chercher une panne réseau là où il y a une erreur de configuration.
    """
    error = envelope.get("error")
    if isinstance(error, Mapping):
        code = error.get("code")
        texte = error.get("message")
        return f"« {method} » a échoué en HTTP 200 : code Subsonic {code} ({texte})"
    return f"« {method} » a échoué en HTTP 200, sans détail d'erreur"


def _en_piste(brute: Any) -> Track | None:
    """Traduit une chanson Subsonic en `Piste`, ou l'écarte en le disant.

    `genre` est facultatif — il manque sur près d'une piste sur cinq — mais un
    identifiant, un artiste et une durée ne le sont pas : sans eux, la piste ne
    peut être ni résolue, ni soumise à la non-répétition.
    """
    if not isinstance(brute, Mapping):
        journal.warning("entrée ignorée : une chanson est attendue, pas %s", type(brute).__name__)
        return None
    identifier = brute.get("id")
    title = brute.get("title")
    artist = brute.get("artist")
    duration = brute.get("duration")
    genre = brute.get("genre")
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
        )
    except ValueError as error:
        journal.warning("chanson ignorée : %s", error)
        return None
