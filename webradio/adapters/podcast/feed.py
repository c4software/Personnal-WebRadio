"""Lire un flux de podcast et n'en retenir que les épisodes diffusables.

Le comportement vient du relevé docs/podcast.md, établi contre les flux
réellement déclarés, pas d'une norme (AGENTS.md §3). Trois constats pilotent
ce module :

- Seuls les épisodes `itunes:episodeType` = `full` passent : les flux exposent
  aussi des `bonus` et des `trailer`, qu'on ne diffuse pas à l'heure de
  l'émission (SPECS.md §4.11, docs/podcast.md §3.4).
- `enclosure/length` est faux à cause de la publicité insérée à la volée. Il
  n'est lu nulle part ici, volontairement (docs/podcast.md §2.1).
- Le serveur accepte les `Range` : ffmpeg lit l'URL directement, ce module ne
  rapatrie que le XML (docs/podcast.md §2.2).

`xml.etree.ElementTree` suffit ; `feedparser` ajouterait une dépendance pour
lire quatre balises.
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
    """Le flux ne répond pas, ou répond quelque chose d'illisible.

    Ce n'est pas une panne de la radio (SPECS.md §5) : l'appelant saute la
    case, journalise, et la musique continue. La décision lui revient.
    """


@dataclass(frozen=True, slots=True)
class Episode:
    """Un épisode diffusable.

    `duration` est facultative : `itunes:duration` est une extension qu'un
    flux peut ne pas exposer. Sans elle, la fenêtre de rattrapage
    (SPECS.md §4.11) n'est pas calculable ; l'appelant décide.

    La durée annoncée est sous-estimée d'environ 2 % : elle ne compte pas la
    publicité insérée à la volée (docs/podcast.md §2.1).
    """

    identifier: str
    title: str
    published_at: datetime
    audio: str
    duration: timedelta | None = None


class HttpReader(Protocol):
    """L'accès réseau dont la lecture d'un flux a besoin.

    Un `Protocol` pour tester sans réseau les cas du relevé (flux injoignable,
    XML malformé, page HTML en 200) contre des réponses littérales
    (AGENTS.md §4).
    """

    def read(self, url: str) -> bytes: ...


class UrllibReader:
    """Le lecteur réel, sur `urllib`.

    Le flux se lit d'un bloc, une fois par branchement : pas besoin d'une
    dépendance HTTP supplémentaire.
    """

    def __init__(self, *, lock_timeout: timedelta) -> None:
        """`lock_timeout` vient du TOML : aucune durée n'est écrite dans le code."""
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
    """Lit `itunes:duration` en secondes, en `MM:SS` ou en `HH:MM:SS`.

    Une durée illisible rend `None` plutôt qu'une valeur fausse, car elle
    borne le rattrapage.
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
    """Lit `pubDate` (RFC 2822). `None` si la date est illisible.

    Sans date, l'épisode ne peut pas être classé du plus récent au plus ancien
    (SPECS.md §7 n°14) : l'appelant l'écarte.
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
        """Les épisodes `full` du flux, du plus récent au plus ancien.

        Un flux sans épisode diffusable rend une liste vide : l'émission n'a
        pas lieu (SPECS.md §4.11). Un flux injoignable ou illisible lève
        `PodcastUnavailable`.
        """
        root = self._analyser(self._lecteur.read(url), url)
        episodes = sorted(self._extraire(root, url), key=lambda e: e.published_at, reverse=True)
        logger.debug("flux %s : %d épisode(s) diffusable(s)", url, len(episodes))
        return episodes

    def _analyser(self, content: bytes, url: str) -> ElementTree.Element:
        """Analyse le XML et vérifie que la racine est `rss`.

        Un portail captif ou une page d'erreur répond 200 et se lit parfois
        comme du XML (docs/podcast.md §5) ; le contrôle de la racine l'écarte.
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
        """L'épisode d'un `<item>`, ou `None` s'il est incomplet.

        `episodeType` absent vaut `full` : c'est une extension iTunes, et un
        flux qui ne la porte pas serait sinon vidé de tous ses épisodes.
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

        # Le `guid` est facultatif en RSS. À défaut, l'URL de l'enclosure sert
        # d'identifiant, et c'est elle que la base retiendra comme déjà
        # diffusée (SPECS.md §4.11.1).
        identifier = _texte(item, "guid") or audio

        return Episode(
            identifier=identifier,
            title=_texte(item, "title") or identifier,
            published_at=published_at,
            audio=audio,
            duration=_duree(_texte(item, f"{{{ITUNES}}}duration")),
        )
