"""La dernière vidéo d'une chaîne, présentée comme un épisode de podcast.

Le planificateur d'émissions (`app/show_scheduler.py`) ne fait pas la
différence : il reçoit des épisodes — identifiant, date, durée, adresse
audio — et applique les mêmes règles qu'aux podcasts (le plus récent non
diffusé, la case bornée par la durée).

Trois choses viennent du relevé [docs/youtube.md](../../../docs/youtube.md),
et il ne faut pas les rediscuter ici :

- le `channel_id` se lit dans le lien **canonique** de la page de chaîne ;
- le flux Atom ne porte **pas** de durée : `yt-dlp` la donne, avec l'URL
  audio directe que ffmpeg sait ouvrir ;
- cette URL expire (~6 h) : on résout **au moment de diffuser**, et seule la
  vidéo candidate est résolue — pas les quinze du flux.
"""

import logging
import re
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from webradio.adapters.podcast.feed import Episode

logger = logging.getLogger(__name__)

FEED = "https://www.youtube.com/feeds/videos.xml?channel_id={channel}"
WATCH = "https://www.youtube.com/watch?v={video}"
ATOM = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
CANONIQUE = re.compile(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[^"]+)"')


class YoutubeUnavailable(Exception):
    """La chaîne, son flux ou `yt-dlp` ne répond pas. Cas nominal : musique."""


@dataclass(frozen=True, slots=True)
class Resolved:
    """Ce que `yt-dlp` sait d'une vidéo : sa durée, et où est l'audio."""

    duration: timedelta
    audio: str


def _resoudre_par_ytdlp(video_url: str, timeout: float) -> Resolved:
    """`yt-dlp -g` : la durée puis l'URL audio directe, une ligne chacune."""
    try:
        done = subprocess.run(
            [
                "yt-dlp",
                "-g",
                "-f",
                "bestaudio",
                "--print",
                "duration",
                "--print",
                "urls",
                "--no-warnings",
                video_url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except FileNotFoundError as absent:
        message = "yt-dlp introuvable : les émissions YouTube ont besoin de lui"
        raise YoutubeUnavailable(message) from absent
    except subprocess.TimeoutExpired as lent:
        message = f"yt-dlp n'a pas répondu en {timeout:g} s"
        raise YoutubeUnavailable(message) from lent
    except subprocess.CalledProcessError as refus:
        message = f"yt-dlp a refusé « {video_url} » : {refus.stderr.strip()[:200]}"
        raise YoutubeUnavailable(message) from refus
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].strip().isdigit():
        message = f"sortie de yt-dlp inattendue pour « {video_url} »"
        raise YoutubeUnavailable(message)
    return Resolved(duration=timedelta(seconds=int(lines[0])), audio=lines[1].strip())


class YoutubeChannel:
    """Le même contrat que `PodcastFeed` : des épisodes, du plus récent au reste.

    Seule la vidéo la plus récente est résolue par `yt-dlp` — c'est la seule
    candidate (SPECS.md §7 n°14), et chaque résolution coûte un appel réseau.
    """

    def __init__(
        self,
        timeout: timedelta,
        fetch: Callable[[str, float], str] | None = None,
        resolve: Callable[[str, float], Resolved] | None = None,
    ) -> None:
        self._delai = timeout.total_seconds()
        self._lire = fetch if fetch is not None else self._lire_par_urllib
        self._resoudre = resolve if resolve is not None else _resoudre_par_ytdlp
        self._chaines: dict[str, str] = {}

    def _lire_par_urllib(self, url: str, timeout: float) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "local-webradio"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as reponse:
                return str(reponse.read().decode("utf-8", errors="replace"))
        except (urllib.error.URLError, OSError, TimeoutError) as failure:
            message = f"« {url} » ne répond pas : {failure}"
            raise YoutubeUnavailable(message) from failure

    def _channel_id(self, channel_url: str) -> str:
        """Depuis n'importe quelle forme d'adresse — handle compris.

        Le lien canonique de la page fait foi (docs/youtube.md §1). Le
        résultat est retenu : une chaîne ne change pas d'identifiant.
        """
        if "/channel/" in channel_url:
            return channel_url.rstrip("/").rsplit("/", 1)[-1]
        connu = self._chaines.get(channel_url)
        if connu is not None:
            return connu
        page = self._lire(channel_url, self._delai)
        trouve = CANONIQUE.search(page)
        if trouve is None:
            message = f"aucun lien canonique de chaîne sur « {channel_url} »"
            raise YoutubeUnavailable(message)
        self._chaines[channel_url] = trouve.group(1)
        return trouve.group(1)

    def episodes(self, channel_url: str) -> list[Episode]:
        """Les vidéos du flux Atom, la plus récente résolue par `yt-dlp`.

        Les suivantes n'ont ni durée ni audio : elles ne servent qu'à dater —
        le planificateur ne diffuse jamais que la plus récente non diffusée.
        """
        flux = self._lire(FEED.format(channel=self._channel_id(channel_url)), self._delai)
        try:
            racine = ET.fromstring(flux)
        except ET.ParseError as illisible:
            message = f"flux Atom illisible pour « {channel_url} »"
            raise YoutubeUnavailable(message) from illisible
        episodes: list[Episode] = []
        for entry in racine.findall("a:entry", ATOM):
            video = entry.findtext("yt:videoId", namespaces=ATOM)
            published = entry.findtext("a:published", namespaces=ATOM)
            if not video or not published:
                continue
            episodes.append(
                Episode(
                    identifier=video,
                    title=entry.findtext("a:title", namespaces=ATOM) or video,
                    published_at=datetime.fromisoformat(published),
                    audio="",
                    duration=None,
                )
            )
        episodes.sort(key=lambda e: e.published_at, reverse=True)
        if episodes:
            recent = self._resoudre(WATCH.format(video=episodes[0].identifier), self._delai)
            episodes[0] = Episode(
                identifier=episodes[0].identifier,
                title=episodes[0].title,
                published_at=episodes[0].published_at,
                audio=recent.audio,
                duration=recent.duration,
            )
        return episodes
