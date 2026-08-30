"""Les jingles : ce qui est dû, dans quel ordre, et ce qui est abandonné."""

from datetime import UTC, datetime, timedelta

from webradio.core.clock import FrozenClock
from webradio.core.jingles import JINGLE_ENCORE, Jingles, jingle_name


def clock(hour: int, minute: int = 0) -> FrozenClock:
    return FrozenClock(datetime(2026, 8, 30, hour, minute, tzinfo=UTC))


def test_le_nom_du_jingle_se_deduit_de_l_heure() -> None:
    """Le nom du fichier *est* la programmation : aucune table à tenir à jour."""
    assert jingle_name(datetime(2026, 8, 30, 14, 37, tzinfo=UTC)) == "hours/14h.mp3"
    assert jingle_name(datetime(2026, 8, 30, 0, 0, tzinfo=UTC)) == "hours/00h.mp3"
    assert jingle_name(datetime(2026, 8, 30, 23, 59, tzinfo=UTC)) == "hours/23h.mp3"


def test_aucun_jingle_n_est_du_tant_qu_aucune_heure_n_est_franchie() -> None:
    h = clock(14, 5)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=50))
    assert jingles.due_now() == ()


def test_l_heure_pile_franchie_rend_le_jingle_de_cette_heure() -> None:
    h = clock(13, 55)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=10))
    assert jingles.due_now() == ("hours/14h.mp3",)


def test_un_jingle_en_retard_passe_quand_meme() -> None:
    """SPECS.md §7 n°4 : `14h.mp3` peut s'entendre à 14 h 25 si le morceau en
    cours est long. Renoncer aurait coûté un seuil pour un gain nul."""
    h = clock(13, 50)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=35))
    assert jingles.due_now() == ("hours/14h.mp3",)


def test_un_morceau_qui_enjambe_deux_heures_les_diffuse_toutes_dans_l_ordre() -> None:
    h = clock(13, 50)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=80))
    assert jingles.due_now() == ("hours/14h.mp3", "hours/15h.mp3")


def test_un_jingle_rendu_ne_l_est_pas_une_seconde_fois() -> None:
    h = clock(13, 55)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=10))
    assert jingles.due_now() == ("hours/14h.mp3",)
    assert jingles.due_now() == ()


def test_le_jingle_de_vote_passe_en_dernier() -> None:
    """`encore.mp3` annonce le morceau qui suit immédiatement : il perdrait son
    sens s'il en était séparé (SPECS.md §4.3)."""
    h = clock(13, 50)
    jingles = Jingles(h)
    jingles.mark_more()
    h.advance(timedelta(minutes=80))
    assert jingles.due_now() == ("hours/14h.mp3", "hours/15h.mp3", JINGLE_ENCORE)


def test_deux_votes_avant_la_meme_jonction_ne_font_qu_un_jingle() -> None:
    jingles = Jingles(clock(14, 10))
    jingles.mark_more()
    jingles.mark_more()
    assert jingles.encore_du
    assert jingles.due_now() == (JINGLE_ENCORE,)
    assert not jingles.encore_du


def test_les_jingles_dus_pendant_une_emission_sont_abandonnes() -> None:
    """La seule exception à « rien n'est jamais abandonné » (SPECS.md §7 n°15) :
    une émission remplace la programmation, habillage compris."""
    h = clock(19, 50)
    jingles = Jingles(h)
    h.advance(timedelta(hours=2))
    assert jingles.due_now(during_show=True) == ()


def test_une_emission_ne_differe_pas_les_jingles_qu_elle_a_abandonnes() -> None:
    """Les différer aurait produit un `21h.mp3` diffusé après trois heures
    d'émission — précisément ce que la décision n°15 refuse."""
    h = clock(19, 50)
    jingles = Jingles(h)
    h.advance(timedelta(hours=2))
    assert jingles.due_now(during_show=True) == ()
    h.advance(timedelta(minutes=5))
    assert jingles.due_now() == ()


def test_la_radio_ne_rattrape_pas_les_heures_d_avant_son_demarrage() -> None:
    """Elle n'existe que lorsqu'on l'écoute : se brancher à 22 h ne fait pas
    passer les jingles de la journée."""
    h = clock(22, 30)
    jingles = Jingles(h)
    h.advance(timedelta(minutes=5))
    assert jingles.due_now() == ()


def test_le_passage_de_minuit_rend_le_jingle_de_minuit() -> None:
    h = FrozenClock(datetime(2026, 8, 30, 23, 55, tzinfo=UTC))
    jingles = Jingles(h)
    h.advance(timedelta(minutes=10))
    assert jingles.due_now() == ("hours/00h.mp3",)


def test_une_journee_entiere_fait_tomber_les_vingt_quatre_jingles() -> None:
    """Une journée de programmation en une boucle : ce que l'injection de
    l'horloge achète (ARCHITECTURE.md §3.1)."""
    h = FrozenClock(datetime(2026, 8, 30, 0, 1, tzinfo=UTC))
    jingles = Jingles(h)
    entendus: list[str] = []
    for _ in range(24 * 12):
        h.advance(timedelta(minutes=5))
        entendus.extend(jingles.due_now())
    assert entendus == [f"hours/{hour:02d}h.mp3" for hour in [*range(1, 24), 0]]


def test_le_nom_du_jingle_d_encore_se_configure() -> None:
    """GOAL-031 : `encore.mp3` n'est qu'un défaut — le nom vient du TOML."""
    jingles = Jingles(clock(12), encore_name="bravo.mp3")
    jingles.mark_more()
    assert jingles.due_now() == ("bravo.mp3",)
