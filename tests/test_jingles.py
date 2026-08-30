"""Les jingles : ce qui est dû, dans quel ordre, et ce qui est abandonné."""

from datetime import UTC, datetime, timedelta

from webradio.core.clock import HorlogeFigee
from webradio.core.jingles import JINGLE_ENCORE, Jingles, nom_du_jingle


def horloge(heure: int, minute: int = 0) -> HorlogeFigee:
    return HorlogeFigee(datetime(2026, 8, 30, heure, minute, tzinfo=UTC))


def test_le_nom_du_jingle_se_deduit_de_l_heure() -> None:
    """Le nom du fichier *est* la programmation : aucune table à tenir à jour."""
    assert nom_du_jingle(datetime(2026, 8, 30, 14, 37, tzinfo=UTC)) == "14h.mp3"
    assert nom_du_jingle(datetime(2026, 8, 30, 0, 0, tzinfo=UTC)) == "00h.mp3"
    assert nom_du_jingle(datetime(2026, 8, 30, 23, 59, tzinfo=UTC)) == "23h.mp3"


def test_aucun_jingle_n_est_du_tant_qu_aucune_heure_n_est_franchie() -> None:
    h = horloge(14, 5)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=50))
    assert jingles.dus() == ()


def test_l_heure_pile_franchie_rend_le_jingle_de_cette_heure() -> None:
    h = horloge(13, 55)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=10))
    assert jingles.dus() == ("14h.mp3",)


def test_un_jingle_en_retard_passe_quand_meme() -> None:
    """SPECS.md §7 n°4 : `14h.mp3` peut s'entendre à 14 h 25 si le morceau en
    cours est long. Renoncer aurait coûté un seuil pour un gain nul."""
    h = horloge(13, 50)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=35))
    assert jingles.dus() == ("14h.mp3",)


def test_un_morceau_qui_enjambe_deux_heures_les_diffuse_toutes_dans_l_ordre() -> None:
    h = horloge(13, 50)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=80))
    assert jingles.dus() == ("14h.mp3", "15h.mp3")


def test_un_jingle_rendu_ne_l_est_pas_une_seconde_fois() -> None:
    h = horloge(13, 55)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=10))
    assert jingles.dus() == ("14h.mp3",)
    assert jingles.dus() == ()


def test_le_jingle_de_vote_passe_en_dernier() -> None:
    """`encore.mp3` annonce le morceau qui suit immédiatement : il perdrait son
    sens s'il en était séparé (SPECS.md §4.3)."""
    h = horloge(13, 50)
    jingles = Jingles(h)
    jingles.marquer_encore()
    h.avancer(timedelta(minutes=80))
    assert jingles.dus() == ("14h.mp3", "15h.mp3", JINGLE_ENCORE)


def test_deux_votes_avant_la_meme_jonction_ne_font_qu_un_jingle() -> None:
    jingles = Jingles(horloge(14, 10))
    jingles.marquer_encore()
    jingles.marquer_encore()
    assert jingles.encore_du
    assert jingles.dus() == (JINGLE_ENCORE,)
    assert not jingles.encore_du


def test_les_jingles_dus_pendant_une_emission_sont_abandonnes() -> None:
    """La seule exception à « rien n'est jamais abandonné » (SPECS.md §7 n°15) :
    une émission remplace la programmation, habillage compris."""
    h = horloge(19, 50)
    jingles = Jingles(h)
    h.avancer(timedelta(hours=2))
    assert jingles.dus(pendant_emission=True) == ()


def test_une_emission_ne_differe_pas_les_jingles_qu_elle_a_abandonnes() -> None:
    """Les différer aurait produit un `21h.mp3` diffusé après trois heures
    d'émission — précisément ce que la décision n°15 refuse."""
    h = horloge(19, 50)
    jingles = Jingles(h)
    h.avancer(timedelta(hours=2))
    assert jingles.dus(pendant_emission=True) == ()
    h.avancer(timedelta(minutes=5))
    assert jingles.dus() == ()


def test_la_radio_ne_rattrape_pas_les_heures_d_avant_son_demarrage() -> None:
    """Elle n'existe que lorsqu'on l'écoute : se brancher à 22 h ne fait pas
    passer les jingles de la journée."""
    h = horloge(22, 30)
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=5))
    assert jingles.dus() == ()


def test_le_passage_de_minuit_rend_le_jingle_de_minuit() -> None:
    h = HorlogeFigee(datetime(2026, 8, 30, 23, 55, tzinfo=UTC))
    jingles = Jingles(h)
    h.avancer(timedelta(minutes=10))
    assert jingles.dus() == ("00h.mp3",)


def test_une_journee_entiere_fait_tomber_les_vingt_quatre_jingles() -> None:
    """Une journée de programmation en une boucle : ce que l'injection de
    l'horloge achète (ARCHITECTURE.md §3.1)."""
    h = HorlogeFigee(datetime(2026, 8, 30, 0, 1, tzinfo=UTC))
    jingles = Jingles(h)
    entendus: list[str] = []
    for _ in range(24 * 12):
        h.avancer(timedelta(minutes=5))
        entendus.extend(jingles.dus())
    assert entendus == [f"{heure:02d}h.mp3" for heure in [*range(1, 24), 0]]
