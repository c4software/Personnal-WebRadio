"""Une chaîne YouTube vue comme un flux d'épisodes (GOAL-025, docs/youtube.md)."""

from datetime import UTC, datetime, timedelta

import pytest

from webradio.adapters.youtube.channel import Resolved, YoutubeChannel, YoutubeUnavailable

ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <title>Hardisk</title>
  <entry>
    <yt:videoId>ancienne</yt:videoId>
    <title>La plus vieille</title>
    <published>2026-08-01T09:00:00+00:00</published>
  </entry>
  <entry>
    <yt:videoId>recente</yt:videoId>
    <title>La plus fraîche</title>
    <published>2026-08-29T09:00:45+00:00</published>
  </entry>
</feed>
"""

PAGE = '<html><link rel="canonical" href="https://www.youtube.com/channel/UCexemple123"></html>'


class FakeReseau:
    """Les pages et flux que le test décide, et le journal des résolutions."""

    def __init__(self, *, page: str = PAGE, flux: str = ATOM) -> None:
        self._page = page
        self._flux = flux
        self.lus: list[str] = []
        self.resolues: list[str] = []

    def lire(self, url: str, _timeout: float) -> str:
        self.lus.append(url)
        return self._flux if "feeds/videos.xml" in url else self._page

    def resoudre(self, video_url: str, _timeout: float) -> Resolved:
        self.resolues.append(video_url)
        return Resolved(duration=timedelta(seconds=1742), audio="https://exemple.test/audio")


def _chaine(reseau: FakeReseau) -> YoutubeChannel:
    return YoutubeChannel(timeout=timedelta(seconds=5), fetch=reseau.lire, resolve=reseau.resoudre)


def test_la_plus_recente_arrive_en_tete_resolue_par_yt_dlp() -> None:
    reseau = FakeReseau()
    episodes = _chaine(reseau).episodes("https://www.youtube.com/@hardisk")

    assert [e.identifier for e in episodes] == ["recente", "ancienne"]
    assert episodes[0].duration == timedelta(seconds=1742)
    assert episodes[0].audio == "https://exemple.test/audio"
    assert episodes[0].published_at == datetime(2026, 8, 29, 9, 0, 45, tzinfo=UTC)


def test_seule_la_candidate_est_resolue() -> None:
    """Chaque résolution coûte un appel réseau : les autres vidéos ne servent
    qu'à dater (docs/youtube.md §2)."""
    reseau = FakeReseau()
    episodes = _chaine(reseau).episodes("https://www.youtube.com/@hardisk")
    assert reseau.resolues == ["https://www.youtube.com/watch?v=recente"]
    assert episodes[1].duration is None
    assert episodes[1].audio == ""


def test_le_handle_se_resout_par_le_lien_canonique_une_seule_fois() -> None:
    reseau = FakeReseau()
    chaine = _chaine(reseau)
    chaine.episodes("https://www.youtube.com/@hardisk")
    chaine.episodes("https://www.youtube.com/@hardisk")

    pages = [u for u in reseau.lus if "feeds" not in u]
    assert pages == ["https://www.youtube.com/@hardisk"]
    assert all("UCexemple123" in u for u in reseau.lus if "feeds" in u)


def test_une_adresse_channel_ne_demande_aucune_page() -> None:
    reseau = FakeReseau()
    _chaine(reseau).episodes("https://www.youtube.com/channel/UCdirect")
    assert all("feeds" in u for u in reseau.lus)


def test_une_page_sans_lien_canonique_se_dit() -> None:
    reseau = FakeReseau(page="<html>rien</html>")
    with pytest.raises(YoutubeUnavailable, match="canonique"):
        _chaine(reseau).episodes("https://www.youtube.com/@fantome")


def test_un_flux_illisible_se_dit() -> None:
    reseau = FakeReseau(flux="pas du xml")
    with pytest.raises(YoutubeUnavailable, match="illisible"):
        _chaine(reseau).episodes("https://www.youtube.com/channel/UCx")


def test_un_yt_dlp_en_echec_se_dit() -> None:
    reseau = FakeReseau()

    def refus(_video: str, _timeout: float) -> Resolved:
        message = "yt-dlp a refusé"
        raise YoutubeUnavailable(message)

    chaine = YoutubeChannel(timeout=timedelta(seconds=5), fetch=reseau.lire, resolve=refus)
    with pytest.raises(YoutubeUnavailable):
        chaine.episodes("https://www.youtube.com/channel/UCx")
