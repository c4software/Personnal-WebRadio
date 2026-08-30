"""Lire un flux de podcast, et n'en retenir que ce qui se diffuse.

Tout ce qui suit vient du relevé [docs/podcast.md](../../../docs/podcast.md),
établi contre les deux flux réellement déclarés. Rien n'y est déduit d'une
norme : « RSS avec des `<enclosure>` » est une convention, pas un standard
respecté (AGENTS.md §3).

Trois constats du relevé pilotent ce module :

- **`itunes:episodeType` : `full` seulement.** *A la French* expose un `bonus`
  en tête de flux et *LEGEND* un `trailer`. Diffuser une bande-annonce d'une
  minute trente à l'heure de l'émission serait un défaut audible
  (SPECS.md §4.11, docs/podcast.md §3.4).
- **`enclosure/length` ment.** Acast insère de la publicité à la volée
  (`livestitches`) : +2 Mo sur LEGEND, +350 octets sur *A la French*. Le champ
  décrit un fichier qui n'est pas celui qu'on reçoit — il n'est lu nulle part
  ici, et ce n'est pas un oubli (docs/podcast.md §2.1).
- **`Accept-Ranges: bytes`** : ffmpeg consomme l'URL directement, il n'y a rien
  à télécharger (docs/podcast.md §2.2). Ce module ne rapatrie que le XML.

`xml.etree.ElementTree` de la bibliothèque standard suffit : `feedparser`
ajouterait une dépendance pour lire quatre balises.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
AIRABLE_KIND = "full"
ALLOWED_SCHEMES = frozenset({"http", "https"})


class PodcastUnavailable(Exception):
    """Le flux ne répond pas, ou répond ce qu'on ne sait pas lire.

    Ce n'est pas une panne de la radio (SPECS.md §5) : la case est sautée, la
    musique continue, et l'appelant journalise. L'exception existe pour que ce
    soit une décision prise en haut, pas un silence pris ici.
    """


@dataclass(frozen=True, slots=True)
class Episode:
    """Un épisode diffusable, tel que la radio a besoin de le connaître.

    `duree` est facultative parce que `itunes:duration` est une extension : les
    deux flux relevés l'exposent toujours, un troisième pourrait ne pas le
    faire. Sans elle, la fenêtre de rattrapage (SPECS.md §4.11) n'est pas
    calculable — c'est à l'appelant de le décider, pas à cet adaptateur de le
    supposer.

    La durée annoncée est par ailleurs **optimiste d'environ 2 %** : elle ne
    compte pas la publicité insérée à la volée (docs/podcast.md §2.1).
    """

    identifier: str
    title: str
    published_at: datetime
    audio: str
    duration: timedelta | None = None


class HttpReader(Protocol):
    """Ce dont la lecture d'un flux a besoin du réseau, et rien de plus.

    Un `Protocol` plutôt qu'un appel direct : c'est ce qui rend les cas du
    relevé — flux injoignable, XML malformé, page HTML en 200 — testables sans
    réseau, contre des réponses littérales (AGENTS.md §4).
    """

    def read(self, url: str) -> bytes: ...


class UrllibReader:
    """Le lecteur réel, sur `urllib` de la bibliothèque standard.

    Le flux fait 3,5 Mo et se lit d'un bloc, une fois par branchement : rien
    n'y justifie une dépendance HTTP supplémentaire.
    """

    def __init__(self, *, lock_timeout: timedelta) -> None:
        """`delai_attente` vient du TOML : aucune durée ne s'écrit dans le code."""
        if lock_timeout <= timedelta(0):
            message = "un délai d'attente nul rendrait tout flux injoignable"
            raise ValueError(message)
        self._delai_attente = lock_timeout

    def read(self, url: str) -> bytes:
        if urlsplit(url).scheme not in ALLOWED_SCHEMES:
            message = f"schéma d'URL refusé pour un flux de podcast : {url}"
            raise PodcastUnavailable(message)
        try:
            with urlopen(url, timeout=self._delai_attente.total_seconds()) as answer:
                content: bytes = answer.read()
        except (URLError, OSError, ValueError) as error:
            message = f"flux de podcast injoignable : {url}"
            raise PodcastUnavailable(message) from error
        return content


def _duree(texte: str | None) -> timedelta | None:
    """`itunes:duration` s'écrit en secondes, en `MM:SS` ou en `HH:MM:SS`.

    Les trois formes circulent ; une durée qu'on ne sait pas lire vaut mieux
    absente que fausse, puisqu'elle bornerait le rattrapage.
    """
    if texte is None:
        return None
    morceaux = texte.strip().split(":")
    try:
        values = [int(m) for m in morceaux]
    except ValueError:
        return None
    if not 1 <= len(values) <= 3:
        return None
    hours, minutes, secondes = ([0] * (3 - len(values))) + values
    return timedelta(hours=hours, minutes=minutes, seconds=secondes)


def _publie_le(texte: str | None) -> datetime | None:
    """`pubDate` au format RFC 2822. Une date illisible rend l'épisode inclassable.

    Sans date, « le plus récent » (SPECS.md §7 n°14) n'a pas de sens : l'épisode
    est écarté plutôt que placé au hasard dans l'ordre.
    """
    if texte is None:
        return None
    try:
        instant = parsedate_to_datetime(texte)
    except (TypeError, ValueError):
        return None
    if instant.tzinfo is None:
        return instant.replace(tzinfo=UTC)
    return instant


def _texte(item: ElementTree.Element, path: str) -> str | None:
    element = item.find(path)
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


class PodcastFeed:
    """Rend les épisodes diffusables d'un flux, du plus récent au plus ancien."""

    def __init__(self, reader: HttpReader) -> None:
        self._lecteur = reader

    def episodes(self, url: str) -> list[Episode]:
        """Les épisodes `full` du flux, triés du plus récent au plus ancien.

        Un flux vide, ou dont aucun épisode n'est diffusable, rend une liste
        vide : ce n'est pas une erreur, c'est une émission qui n'a pas lieu
        (SPECS.md §4.11). Un flux injoignable ou illisible, lui, lève.
        """
        root = self._analyser(self._lecteur.read(url), url)
        episodes = sorted(self._extraire(root, url), key=lambda e: e.published_at, reverse=True)
        logger.debug("flux %s : %d épisode(s) diffusable(s)", url, len(episodes))
        return episodes

    def _analyser(self, content: bytes, url: str) -> ElementTree.Element:
        """Un XML malformé, ou une page HTML servie en 200, ne sont pas des flux.

        Le second cas est le piège du relevé (docs/podcast.md §5) : un portail
        captif ou une page d'erreur répond `200`, et se lit parfois comme du
        XML. Contrôler la racine `rss` est ce qui les sépare.
        """
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as error:
            message = f"flux de podcast illisible (XML malformé) : {url}"
            raise PodcastUnavailable(message) from error
        if root.tag != "rss":
            message = f"la réponse n'est pas un flux RSS (racine « {root.tag} ») : {url}"
            raise PodcastUnavailable(message)
        return root

    def _extraire(self, root: ElementTree.Element, url: str) -> Iterator[Episode]:
        for item in root.iterfind("./channel/item"):
            episode = self._episode(item, url)
            if episode is not None:
                yield episode

    def _episode(self, item: ElementTree.Element, url: str) -> Episode | None:
        """Un épisode incomplet est écarté, jamais deviné.

        `episodeType` absent vaut `full` : c'est une extension iTunes, et un
        flux qui ne la porte pas n'expose que des épisodes ordinaires. Le
        contraire viderait un tel flux de tous ses épisodes.
        """
        type_episode = _texte(item, f"{{{ITUNES}}}episodeType")
        if type_episode is not None and type_episode.lower() != AIRABLE_KIND:
            return None

        enclosure = item.find("enclosure")
        audio = enclosure.get("url") if enclosure is not None else None
        if not audio:
            logger.info("épisode sans enclosure écarté dans %s", url)
            return None

        published_at = _publie_le(_texte(item, "pubDate"))
        if published_at is None:
            logger.info("épisode sans date exploitable écarté dans %s", url)
            return None

        # Le `guid` est facultatif en RSS. L'URL de l'enclosure est le
        # moins mauvais substitut : c'est elle que le flux publie, et c'est ce
        # que la base retiendra comme « déjà diffusé » (SPECS.md §4.11.1).
        identifier = _texte(item, "guid") or audio

        return Episode(
            identifier=identifier,
            title=_texte(item, "title") or identifier,
            published_at=published_at,
            audio=audio,
            duration=_duree(_texte(item, f"{{{ITUNES}}}duration")),
        )
