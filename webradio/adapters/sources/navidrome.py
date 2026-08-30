"""La source Navidrome, via l'API Subsonic.

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

from webradio.adapters.config.schema import ConfigurationNavidrome, IdentifiantsNavidrome
from webradio.core.models import Piste
from webradio.core.rng import Hasard
from webradio.core.sources import SourceIndisponible

journal = logging.getLogger(__name__)

CHEMIN_API = "/rest"
VERSION_API = "1.16.1"
NOM_CLIENT = "local-webradio"
FORMAT_REPONSE = "json"
CODE_HTTP_OK = 200

# Le plafond de `getRandomSongs`, constaté : `size=501` rend 500 pistes avec
# `status: ok`. Ce n'est pas un réglage, c'est une propriété du serveur.
PLAFOND_ECHANTILLON = 500

# Le sel accompagne le jeton dans l'URL ; sa seule exigence est de varier d'un
# appel à l'autre. Il est tiré par le hasard injecté, parce que `random` et
# `secrets` sont interdits partout ailleurs que dans `core/rng.py`.
ALPHABET_SEL = list("0123456789abcdef")
LONGUEUR_SEL = 12


@dataclass(frozen=True, slots=True)
class ReponseHttp:
    """Ce que l'adaptateur a besoin de savoir d'une réponse : un code et un corps.

    Le corps est du texte et non du JSON déjà analysé : la seule chose dont on
    soit sûr, c'est qu'un serveur peut répondre autre chose que ce qu'il promet.
    """

    code: int
    corps: str


class TransportHttp(Protocol):
    """Le seul point par lequel ce dossier touche au réseau.

    L'isoler derrière un `Protocol` est ce qui permet de tester l'adaptateur
    contre des réponses littérales, sans réseau (AGENTS.md §4).
    """

    def recuperer(self, url: str) -> ReponseHttp: ...


class TransportUrllib:
    """Le transport réel, sur `urllib` de la bibliothèque standard.

    Une erreur HTTP est rendue comme une réponse ordinaire — le code fait partie
    de ce que l'adaptateur doit examiner — tandis qu'une panne de connexion, qui
    ne produit aucune réponse, devient tout de suite une `SourceIndisponible`.
    """

    def __init__(
        self,
        delai_secondes: float,
        ouvrir: Callable[..., Any] | None = None,
    ) -> None:
        self._delai = delai_secondes
        self._ouvrir = urllib.request.urlopen if ouvrir is None else ouvrir

    def recuperer(self, url: str) -> ReponseHttp:
        requete = urllib.request.Request(url, headers={"User-Agent": NOM_CLIENT})
        try:
            with self._ouvrir(requete, timeout=self._delai) as reponse:
                return ReponseHttp(code=int(reponse.status), corps=_texte(reponse.read()))
        except urllib.error.HTTPError as erreur:
            return ReponseHttp(code=int(erreur.code), corps=_texte(erreur.read()))
        except OSError as erreur:
            message = f"Navidrome injoignable : {erreur}"
            raise SourceIndisponible(message) from erreur


def _texte(brut: bytes) -> str:
    return brut.decode("utf-8", errors="replace")


class SourceNavidrome:
    """La bibliothèque Navidrome, vue comme une `SourceMusicale`."""

    def __init__(
        self,
        identifiants: IdentifiantsNavidrome,
        reglages: ConfigurationNavidrome,
        hasard: Hasard,
        transport: TransportHttp,
    ) -> None:
        self._identifiants = identifiants
        self._reglages = reglages
        self._hasard = hasard
        self._transport = transport
        self._taille = self._plafonner(reglages.taille_echantillon)

    def _plafonner(self, demandee: int) -> int:
        """Le dépassement est ramené au plafond une fois, au démarrage, et dit.

        Le serveur tronque sans rien signaler : croire une demande de 1000
        pistes reviendrait à tirer dans 500 en pensant tirer dans 1000.
        """
        if demandee > PLAFOND_ECHANTILLON:
            journal.warning(
                "taille d'échantillon %d ramenée à %d : le serveur tronque en silence au-delà",
                demandee,
                PLAFOND_ECHANTILLON,
            )
            return PLAFOND_ECHANTILLON
        return demandee

    def pistes(self, genre: str | None = None) -> list[Piste]:
        parametres = {"size": str(self._taille)}
        if genre is not None:
            parametres["genre"] = genre
        enveloppe = self._appeler("getRandomSongs", parametres)
        pistes = self._pistes_de_la_liste(enveloppe, "randomSongs")
        if genre is not None and not pistes:
            journal.info(
                "le genre « %s » ne rend aucune piste : le repli se décide plus haut", genre
            )
        return pistes

    def pistes_de(self, artiste: str) -> list[Piste]:
        """Les pistes de cet artiste, et de lui seul.

        `search3` ramène aussi des voisins : sur 50 résultats relevés pour un
        artiste, 49 étaient de lui et un ne l'était pas. Sans l'égalité exacte,
        `encore` servirait cet intrus.
        """
        enveloppe = self._appeler(
            "search3",
            {
                "query": artiste,
                "songCount": str(self._reglages.resultats_artiste),
                "artistCount": "0",
                "albumCount": "0",
            },
        )
        trouvees = self._pistes_de_la_liste(enveloppe, "searchResult3")
        retenues = [piste for piste in trouvees if piste.artiste == artiste]
        ecartees = len(trouvees) - len(retenues)
        if ecartees:
            journal.debug(
                "%d résultat(s) écarté(s) pour « %s » : la recherche ramène d'autres artistes",
                ecartees,
                artiste,
            )
        return retenues

    def genres(self) -> list[str]:
        """Les genres connus du serveur, dédoublonnés et ordonnés.

        L'ordre du serveur n'est pas garanti stable ; le trier rend deux
        démarrages comparables, ce que le tri seul suffit à obtenir.
        """
        enveloppe = self._appeler("getGenres", {})
        contenu = enveloppe.get("genres")
        entrees = contenu.get("genre") if isinstance(contenu, Mapping) else None
        if not isinstance(entrees, Sequence) or isinstance(entrees, str):
            return []
        noms = {
            entree["value"]
            for entree in entrees
            if isinstance(entree, Mapping)
            and isinstance(entree.get("value"), str)
            and entree["value"]
        }
        return sorted(noms)

    def pistes_de_la_liste_de_lecture(self, nom: str) -> list[Piste]:
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
        identifiant = self._identifiant_de_liste(nom)
        if identifiant is None:
            journal.info(
                "aucune liste de lecture ne s'appelle « %s » : le repli se décide plus haut", nom
            )
            return []
        enveloppe = self._appeler("getPlaylist", {"id": identifiant})
        pistes = self._entrees_de_liste(enveloppe)
        if not pistes:
            journal.info("la liste « %s » ne rend aucune piste : le repli se décide plus haut", nom)
        return pistes

    def _identifiant_de_liste(self, nom: str) -> str | None:
        """Traduit un nom de liste en identifiant Subsonic, par égalité exacte.

        L'égalité exacte plutôt qu'une comparaison indulgente : deux listes
        peuvent différer par une seule majuscule, et servir l'une pour l'autre
        se remarquerait à l'antenne bien plus tard que le repli journalisé.
        """
        enveloppe = self._appeler("getPlaylists", {})
        contenu = enveloppe.get("playlists")
        brutes = contenu.get("playlist") if isinstance(contenu, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return None
        trouves: list[str] = []
        for brute in brutes:
            if not isinstance(brute, Mapping):
                continue
            identifiant = brute.get("id")
            if brute.get("name") == nom and isinstance(identifiant, str) and identifiant:
                trouves.append(identifiant)
        if not trouves:
            return None
        if len(trouves) > 1:
            journal.warning(
                "%d listes de lecture s'appellent « %s » : la première est retenue",
                len(trouves),
                nom,
            )
        return trouves[0]

    def _entrees_de_liste(self, enveloppe: Mapping[str, Any]) -> list[Piste]:
        """Les entrées d'une liste, sous la clé `entry` et non `song`.

        C'est la seule différence de forme avec les autres réponses : les
        entrées sont des chansons ordinaires, converties comme partout ailleurs,
        et les incomplètes sont écartées de la même façon.
        """
        contenu = enveloppe.get("playlist")
        brutes = contenu.get("entry") if isinstance(contenu, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        return [piste for brute in brutes if (piste := _en_piste(brute)) is not None]

    def entree(self, piste: Piste) -> str:
        """L'URL de flux de la piste, jeton compris.

        `stream` plutôt que `download` : le relevé a constaté qu'ils rendent le
        même octet près sur cette instance, et `stream` est celui que la
        spécification Subsonic destine à la lecture.

        L'URL porte le jeton d'authentification : elle ne doit donc **jamais**
        paraître dans un journal (AGENTS.md §2). Elle est rendue à la chaîne de
        diffusion, qui l'ouvre et ne la consigne pas.
        """
        return self._url("stream.view", {"id": piste.identifiant})

    def _sel(self) -> str:
        return "".join(self._hasard.choisir(ALPHABET_SEL) for _ in range(LONGUEUR_SEL))

    def _url(self, methode: str, parametres: Mapping[str, str]) -> str:
        """Construit l'appel authentifié par jeton dérivé.

        Le mot de passe ne circule jamais : seul `md5(motdepasse + sel)` part sur
        le réseau, et le sel change à chaque appel (docs/navidrome.md §1).
        """
        sel = self._sel()
        empreinte = hashlib.md5((self._identifiants.mot_de_passe + sel).encode("utf-8")).hexdigest()
        commun = {
            "u": self._identifiants.utilisateur,
            "t": empreinte,
            "s": sel,
            "v": VERSION_API,
            "c": NOM_CLIENT,
            "f": FORMAT_REPONSE,
        }
        requete = urllib.parse.urlencode({**commun, **parametres})
        return f"{self._identifiants.url}{CHEMIN_API}/{methode}?{requete}"

    def _appeler(self, methode: str, parametres: Mapping[str, str]) -> Mapping[str, Any]:
        """Un appel, et les quatre façons dont il peut mal tourner.

        Aucun message ne contient l'URL : elle porte le jeton et le sel, et un
        journal n'est pas un endroit où les écrire (AGENTS.md §2).
        """
        try:
            reponse = self._transport.recuperer(self._url(methode, parametres))
        except OSError as erreur:
            message = f"« {methode} » : Navidrome injoignable ({erreur})"
            raise SourceIndisponible(message) from erreur

        if reponse.code != CODE_HTTP_OK:
            message = (
                f"« {methode} » a répondu HTTP {reponse.code}, sans corps Subsonic exploitable"
            )
            raise SourceIndisponible(message)

        try:
            donnees = json.loads(reponse.corps)
        except json.JSONDecodeError as erreur:
            message = (
                f"« {methode} » a répondu HTTP 200 avec un corps qui n'est pas du JSON "
                "(une page d'erreur intercalée, ou une réponse tronquée)"
            )
            raise SourceIndisponible(message) from erreur

        enveloppe = donnees.get("subsonic-response") if isinstance(donnees, Mapping) else None
        if not isinstance(enveloppe, Mapping):
            message = f"« {methode} » a répondu du JSON sans enveloppe « subsonic-response »"
            raise SourceIndisponible(message)

        if enveloppe.get("status") != "ok":
            raise SourceIndisponible(_echec(methode, enveloppe))
        return enveloppe

    def _pistes_de_la_liste(self, enveloppe: Mapping[str, Any], contenant: str) -> list[Piste]:
        """Extrait les pistes d'une réponse valable.

        Un contenant absent n'est pas une anomalie : c'est ce que rend un genre
        inexistant, avec `status: ok` (docs/navidrome.md §2.2).
        """
        contenu = enveloppe.get(contenant)
        brutes = contenu.get("song") if isinstance(contenu, Mapping) else None
        if not isinstance(brutes, Sequence) or isinstance(brutes, str):
            return []
        pistes = [piste for brute in brutes if (piste := _en_piste(brute)) is not None]
        return pistes


def _echec(methode: str, enveloppe: Mapping[str, Any]) -> str:
    """Le message d'un refus applicatif, arrivé en HTTP 200.

    Le code Subsonic est repris tel quel : c'est lui qui distingue un mot de
    passe faux (40) d'un identifiant inconnu (70), et la distinction est ce qui
    évite de chercher une panne réseau là où il y a une erreur de configuration.
    """
    erreur = enveloppe.get("error")
    if isinstance(erreur, Mapping):
        code = erreur.get("code")
        texte = erreur.get("message")
        return f"« {methode} » a échoué en HTTP 200 : code Subsonic {code} ({texte})"
    return f"« {methode} » a échoué en HTTP 200, sans détail d'erreur"


def _en_piste(brute: Any) -> Piste | None:
    """Traduit une chanson Subsonic en `Piste`, ou l'écarte en le disant.

    `genre` est facultatif — il manque sur près d'une piste sur cinq — mais un
    identifiant, un artiste et une durée ne le sont pas : sans eux, la piste ne
    peut être ni résolue, ni soumise à la non-répétition.
    """
    if not isinstance(brute, Mapping):
        journal.warning("entrée ignorée : une chanson est attendue, pas %s", type(brute).__name__)
        return None
    identifiant = brute.get("id")
    titre = brute.get("title")
    artiste = brute.get("artist")
    duree = brute.get("duration")
    genre = brute.get("genre")
    if (
        not isinstance(identifiant, str)
        or not isinstance(titre, str)
        or not isinstance(artiste, str)
        or isinstance(duree, bool)
        or not isinstance(duree, int)
    ):
        journal.warning("chanson ignorée : champ obligatoire absent ou d'un type inattendu")
        return None
    try:
        return Piste(
            identifiant=identifiant,
            titre=titre,
            artiste=artiste,
            genre=genre if isinstance(genre, str) and genre else None,
            duree=timedelta(seconds=duree),
        )
    except ValueError as erreur:
        journal.warning("chanson ignorée : %s", erreur)
        return None
