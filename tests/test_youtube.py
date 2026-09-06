"""Une chaîne YouTube vue comme un flux d'épisodes (GOAL-025, docs/youtube.md)."""

import http.client
import urllib.request
from datetime import UTC, datetime, timedelta
from types import TracebackType

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

ATOM_DATE_ILLISIBLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>datee</yt:videoId>
    <title>Datée</title>
    <published>2026-08-29T09:00:45+00:00</published>
  </entry>
  <entry>
    <yt:videoId>illisible</yt:videoId>
    <title>Sans date exploitable</title>
    <published>pas-une-date</published>
  </entry>
</feed>
"""

# Un flux dont la connexion a lâché en cours de corps.
FLUX_TRONQUE = b'<?xml version="1.0" encoding="UTF-8"?><feed><entry>'


class FakeReseau:
    """Pages et flux fixés par le test, avec le journal des lectures et des résolutions."""

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


def test_l_identifiant_se_lit_apres_channel_et_non_au_dernier_segment() -> None:
    """L'onglet des vidéos d'une chaîne finit par `/videos` : c'est le segment
    qui suit `/channel/` qui identifie la chaîne (docs/youtube.md §1)."""
    reseau = FakeReseau()
    _chaine(reseau).episodes("https://www.youtube.com/channel/UCexemple123/videos")

    assert reseau.lus == ["https://www.youtube.com/feeds/videos.xml?channel_id=UCexemple123"]


def test_une_adresse_channel_a_query_string_ou_barre_finale_donne_le_meme_identifiant() -> None:
    reseau = FakeReseau()
    chaine = _chaine(reseau)
    chaine.episodes("https://www.youtube.com/channel/UCexemple123/?view=0")
    chaine.episodes("https://www.youtube.com/channel/UCexemple123/videos?view=0")

    assert reseau.lus == [
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCexemple123",
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCexemple123",
    ]


def test_une_video_a_la_date_illisible_est_ecartee_sans_perdre_les_autres() -> None:
    """Même règle que les podcasts : sans date, l'entrée ne se classe pas, elle
    est écartée en le journalisant plutôt que de lever une `ValueError`."""
    reseau = FakeReseau(flux=ATOM_DATE_ILLISIBLE)
    episodes = _chaine(reseau).episodes("https://www.youtube.com/channel/UCx")

    assert [e.identifier for e in episodes] == ["datee"]


class _ReponseTronquee:
    """Ce que `urlopen` rend quand la connexion lâche en cours de corps."""

    def __enter__(self) -> "_ReponseTronquee":
        return self

    def __exit__(
        self,
        genre: type[BaseException] | None,
        value: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        raise http.client.IncompleteRead(FLUX_TRONQUE)


def test_un_flux_atom_tronque_se_dit(monkeypatch: pytest.MonkeyPatch) -> None:
    """`http.client.IncompleteRead` n'est pas une `OSError` : sans traduction,
    elle traverserait le planificateur au lieu de sauter la case."""

    def ouvrir(requete: object, timeout: float) -> _ReponseTronquee:  # noqa: ARG001
        return _ReponseTronquee()

    monkeypatch.setattr(urllib.request, "urlopen", ouvrir)
    chaine = YoutubeChannel(timeout=timedelta(seconds=5))

    with pytest.raises(YoutubeUnavailable, match="ne répond pas"):
        chaine.episodes("https://www.youtube.com/channel/UCx")


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
