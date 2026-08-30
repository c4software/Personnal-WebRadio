"""Le flux de podcast, contre des réponses **littérales**.

Y compris celles que le relevé annonce sans les avoir observées
(docs/podcast.md §5) : flux injoignable, XML malformé, page HTML servie en 200,
épisode sans enclosure. Aucun test ne touche au réseau.
"""

from datetime import UTC, datetime, timedelta

import pytest

from webradio.adapters.podcast import (
    Episode,
    FluxPodcast,
    LecteurUrllib,
    PodcastIndisponible,
)

URL = "https://feeds.acast.com/public/shows/a-la-french"

ENTETE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">'
    "<channel><title>A la French</title>"
)
PIED = "</channel></rss>"


def item(
    guid: str = "guid-1",
    titre: str = "Épisode 1",
    date: str = "Mon, 07 Jul 2026 05:00:00 GMT",
    duree: str = "01:12:00",
    type_episode: str | None = "full",
    audio: str | None = "https://sphinx.acast.com/a-la-french/episode-1.mp3",
    length: str = "112645851",
) -> str:
    balises = [f"<guid>{guid}</guid>", f"<title>{titre}</title>", f"<pubDate>{date}</pubDate>"]
    if audio is not None:
        balises.append(f'<enclosure url="{audio}" length="{length}" type="audio/mpeg"/>')
    if duree:
        balises.append(f"<itunes:duration>{duree}</itunes:duration>")
    if type_episode is not None:
        balises.append(f"<itunes:episodeType>{type_episode}</itunes:episodeType>")
    return "<item>" + "".join(balises) + "</item>"


def flux(*items: str) -> str:
    return ENTETE + "".join(items) + PIED


class FakeLecteur:
    """Rend une réponse littérale, ou tombe en panne sur commande."""

    def __init__(self, contenu: str | bytes = "", *, panne: str | None = None) -> None:
        self._contenu = contenu.encode() if isinstance(contenu, str) else contenu
        self._panne = panne
        self.appels: list[str] = []

    def lire(self, url: str) -> bytes:
        self.appels.append(url)
        if self._panne is not None:
            raise PodcastIndisponible(self._panne)
        return self._contenu


def episodes_de(contenu: str) -> list[Episode]:
    return FluxPodcast(FakeLecteur(contenu)).episodes(URL)


def test_seuls_les_episodes_full_sont_retenus() -> None:
    """Un bonus en tête de flux ne doit pas passer à l'heure de l'émission."""
    resultat = episodes_de(
        flux(
            item(guid="bonus", date="Tue, 28 Jul 2026 05:00:00 GMT", type_episode="bonus"),
            item(guid="trailer", date="Wed, 29 Jul 2026 05:00:00 GMT", type_episode="trailer"),
            item(guid="plein", date="Mon, 07 Jul 2026 05:00:00 GMT"),
        )
    )
    assert [e.identifiant for e in resultat] == ["plein"]


def test_les_episodes_sont_rendus_du_plus_recent_au_plus_ancien() -> None:
    resultat = episodes_de(
        flux(
            item(guid="ancien", date="Mon, 01 Jun 2026 05:00:00 GMT"),
            item(guid="recent", date="Mon, 07 Jul 2026 05:00:00 GMT"),
        )
    )
    assert [e.identifiant for e in resultat] == ["recent", "ancien"]


def test_un_episode_sans_type_declare_est_considere_comme_diffusable() -> None:
    """`itunes:episodeType` est une extension : un flux qui l'ignore n'est pas vide."""
    resultat = episodes_de(flux(item(type_episode=None)))
    assert len(resultat) == 1


def test_un_episode_sans_enclosure_est_ecarte() -> None:
    resultat = episodes_de(flux(item(guid="muet", audio=None), item(guid="jouable")))
    assert [e.identifiant for e in resultat] == ["jouable"]


def test_un_episode_sans_date_exploitable_est_ecarte() -> None:
    """Sans date, « le plus récent » n'a pas de sens."""
    resultat = episodes_de(flux(item(guid="sans-date", date="hier soir"), item(guid="date")))
    assert [e.identifiant for e in resultat] == ["date"]


def test_un_episode_sans_balise_de_date_est_ecarte() -> None:
    contenu = flux(item(guid="sans-date")).replace(
        "<pubDate>Mon, 07 Jul 2026 05:00:00 GMT</pubDate>", ""
    )
    assert episodes_de(contenu) == []


def test_une_date_sans_fuseau_est_lue_en_temps_universel() -> None:
    """Deux dates comparées sans fuseau donnent un ordre faux, pas une erreur."""
    episode = episodes_de(flux(item(date="Mon, 07 Jul 2026 05:00:00")))[0]
    assert episode.publie_le == datetime(2026, 7, 7, 5, 0, tzinfo=UTC)


def test_une_duree_a_quatre_champs_vaut_absente() -> None:
    assert episodes_de(flux(item(duree="1:02:03:04")))[0].duree is None


def test_un_flux_vide_ne_rend_aucun_episode() -> None:
    """Une émission sans épisode n'a pas lieu : ce n'est pas une erreur."""
    assert episodes_de(flux()) == []


def test_l_audio_et_la_date_sont_ceux_du_flux() -> None:
    episode = episodes_de(flux(item()))[0]
    assert episode.audio == "https://sphinx.acast.com/a-la-french/episode-1.mp3"
    assert episode.publie_le == datetime(2026, 7, 7, 5, 0, tzinfo=UTC)
    assert episode.titre == "Épisode 1"


@pytest.mark.parametrize(
    ("texte", "attendue"),
    [
        ("4320", timedelta(seconds=4320)),
        ("72:00", timedelta(minutes=72)),
        ("01:12:00", timedelta(hours=1, minutes=12)),
    ],
)
def test_la_duree_se_lit_dans_ses_trois_formes(texte: str, attendue: timedelta) -> None:
    """`itunes:duration` est lisible sans télécharger : le rattrapage en dépend."""
    assert episodes_de(flux(item(duree=texte)))[0].duree == attendue


def test_une_duree_illisible_vaut_absente_plutot_que_fausse() -> None:
    """Une durée fausse bornerait le rattrapage au mauvais endroit."""
    assert episodes_de(flux(item(duree="une heure et quart")))[0].duree is None


def test_une_duree_absente_ne_fait_pas_disparaitre_l_episode() -> None:
    assert episodes_de(flux(item(duree="")))[0].duree is None


def test_une_taille_annoncee_absurde_ne_change_rien() -> None:
    """`enclosure/length` ment (docs/podcast.md §2.1) : rien ne s'en sert."""
    normal = episodes_de(flux(item(length="112645851")))[0]
    menteur = episodes_de(flux(item(length="0")))[0]
    assert normal == menteur


def test_un_guid_absent_se_replie_sur_l_url_de_l_enclosure() -> None:
    """Il faut un identifiant pour se souvenir d'avoir diffusé (SPECS.md §4.11.1)."""
    contenu = flux(item()).replace("<guid>guid-1</guid>", "")
    assert episodes_de(contenu)[0].identifiant.endswith("episode-1.mp3")


def test_un_xml_malforme_est_signale() -> None:
    with pytest.raises(PodcastIndisponible, match="XML malformé"):
        episodes_de(ENTETE + item())


def test_une_page_html_servie_en_200_est_signalee() -> None:
    """Le piège du relevé : un portail répond 200 avec du HTML bien formé."""
    page = "<html><head><title>Erreur</title></head><body><p>503</p></body></html>"
    with pytest.raises(PodcastIndisponible, match="n'est pas un flux RSS"):
        episodes_de(page)


def test_un_flux_injoignable_est_signale() -> None:
    lecteur = FakeLecteur(panne="réseau coupé")
    with pytest.raises(PodcastIndisponible, match="réseau coupé"):
        FluxPodcast(lecteur).episodes(URL)


def test_le_flux_demande_est_bien_celui_qu_on_lit() -> None:
    lecteur = FakeLecteur(flux(item()))
    FluxPodcast(lecteur).episodes(URL)
    assert lecteur.appels == [URL]


def test_un_schema_d_url_refuse_ne_part_pas_sur_le_reseau() -> None:
    lecteur = LecteurUrllib(delai_attente=timedelta(seconds=5))
    with pytest.raises(PodcastIndisponible, match="schéma d'URL refusé"):
        lecteur.lire("file:///etc/passwd")


def test_un_delai_d_attente_nul_est_refuse() -> None:
    with pytest.raises(ValueError, match="délai d'attente"):
        LecteurUrllib(delai_attente=timedelta(0))
