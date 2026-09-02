"""Tests de la grille effective, une fois plages, programmes et émissions fusionnés.

L'horloge est figée : deux exécutions donnent le même résultat (AGENTS.md §4).
"""

from datetime import UTC, datetime, time, timedelta

from webradio.core.bands import Band, Schedule
from webradio.core.clock import FrozenClock
from webradio.core.planning import EffectiveSchedule, Segment
from webradio.core.programmes import EVERY_DAY, Programme, Programming
from webradio.core.shows import Show, ShowSchedule

# Les journées d'essai partent de minuit.
MERCREDI = datetime(2026, 9, 2, tzinfo=UTC)
SAMEDI = datetime(2026, 9, 5, tzinfo=UTC)
DIMANCHE = datetime(2026, 9, 6, tzinfo=UTC)

GUITARES = Band(start=time(20), end=time(22), genres=("Rock",))
ELECTRIQUE = Band(start=time(22), end=time(23, 30), genres=("Électronique",))
TABLE = Band(start=time(12), end=time(13, 30), genres=("Pop",))

HARDISK = Show(name="Hardisk", days=("wednesday",), hour=time(20))
FLASH = Show(
    name="Flash franceinfo",
    days=("all",),
    hour=time(11, 57),
    duration=timedelta(minutes=13),
)


def _grille(
    bands: list[Band] | None = None,
    programmes: list[Programme] | None = None,
    shows: list[Show] | None = None,
) -> EffectiveSchedule:
    horloge = FrozenClock(MERCREDI)
    return EffectiveSchedule(
        Schedule(bands or [], horloge),
        Programming(programmes or [], horloge),
        ShowSchedule(shows or []),
    )


def _lu(segments: list[Segment]) -> list[tuple[str, str, str]]:
    """Résume chaque segment en (début, fin, occupant).

    Une fin inconnue se lit « ? » ; un segment qui reprend après une émission
    porte « → » devant sa fin, seule borne certaine.
    """
    lues = []
    for segment in segments:
        fin = "?" if segment.end is None else f"{segment.end:%H:%M}"
        lues.append(
            (f"{segment.start:%H:%M}", ("→" if segment.after_show else "") + fin, _nom(segment))
        )
    return lues


def _nom(segment: Segment) -> str:
    content = segment.content
    return content.genres[0] if isinstance(content, Band) else content.name


def test_une_journee_sans_rien_de_declare_est_vide() -> None:
    assert _grille().day(MERCREDI) == []


def test_hors_de_toute_plage_rien_n_est_annonce() -> None:
    """Hors plage, le tirage est libre et rien n'est listé (SPECS.md §4.4)."""
    jour = _grille(bands=[GUITARES]).day(MERCREDI)

    assert _lu(jour) == [("20:00", "22:00", "Rock")]


def test_une_emission_sans_duree_coupe_la_plage_qui_la_contient() -> None:
    """L'émission et la plage qu'elle coupe ne s'affichent pas comme deux
    créneaux indépendants : la plage reprend après elle."""
    jour = _grille(bands=[GUITARES], shows=[HARDISK]).day(MERCREDI)

    assert _lu(jour) == [("20:00", "?", "Hardisk"), ("20:00", "→22:00", "Rock")]


def test_une_emission_sans_duree_coupe_une_plage_en_deux() -> None:
    tardive = Show(name="Tardive", days=("wednesday",), hour=time(21))
    jour = _grille(bands=[GUITARES], shows=[tardive]).day(MERCREDI)

    assert _lu(jour) == [
        ("20:00", "21:00", "Rock"),
        ("21:00", "?", "Tardive"),
        ("21:00", "→22:00", "Rock"),
    ]


def test_un_direct_rogne_le_debut_de_la_plage_qu_il_recouvre() -> None:
    """Un direct connaît sa durée : la plage qu'il recouvre commence à sa fin,
    et cette heure est certaine."""
    jour = _grille(bands=[TABLE], shows=[FLASH]).day(MERCREDI)

    assert _lu(jour) == [("11:57", "12:10", "Flash franceinfo"), ("12:10", "13:30", "Pop")]


def test_un_direct_au_milieu_d_une_plage_la_laisse_de_part_et_d_autre() -> None:
    interlude = Show(name="Interlude", days=("all",), hour=time(21), duration=timedelta(minutes=30))
    jour = _grille(bands=[GUITARES], shows=[interlude]).day(MERCREDI)

    assert _lu(jour) == [
        ("20:00", "21:00", "Rock"),
        ("21:00", "21:30", "Interlude"),
        ("21:30", "22:00", "Rock"),
    ]


def test_une_plage_entierement_recouverte_par_un_direct_disparait() -> None:
    long_direct = Show(name="Le direct", days=("all",), hour=time(12), duration=timedelta(hours=2))
    jour = _grille(bands=[TABLE], shows=[long_direct]).day(MERCREDI)

    assert _lu(jour) == [("12:00", "14:00", "Le direct")]


def test_une_emission_hors_de_son_jour_ne_coupe_rien() -> None:
    jour = _grille(bands=[GUITARES], shows=[HARDISK]).day(SAMEDI)

    assert _lu(jour) == [("20:00", "22:00", "Rock")]


def test_un_programme_l_emporte_sur_les_plages_qu_il_recouvre() -> None:
    """Même priorité qu'à la diffusion : un programme l'emporte sur une plage
    (SPECS.md §4.13)."""
    chloe = Programme(
        name="Le vendredi de Chloé",
        playlist="Chloé",
        days=(EVERY_DAY,),
        start=time(21),
        end=time(23),
    )
    jour = _grille(bands=[GUITARES, ELECTRIQUE], programmes=[chloe]).day(MERCREDI)

    assert _lu(jour) == [
        ("20:00", "21:00", "Rock"),
        ("21:00", "23:00", "Le vendredi de Chloé"),
        ("23:00", "23:30", "Électronique"),
    ]


def test_la_plage_la_plus_courte_decoupe_celle_qui_la_contient() -> None:
    """La plage la plus courte l'emporte, et la longue reprend après (GOAL-068-T01)."""
    soiree = Band(start=time(20), end=time(23), genres=("Soirée",))
    heure = Band(start=time(21), end=time(22), genres=("Heure",))
    jour = _grille(bands=[soiree, heure]).day(MERCREDI)

    assert _lu(jour) == [
        ("20:00", "21:00", "Soirée"),
        ("21:00", "22:00", "Heure"),
        ("22:00", "23:00", "Soirée"),
    ]


def test_une_plage_qui_enjambe_minuit_se_lit_entiere_au_jour_ou_elle_commence() -> None:
    velours = Band(start=time(23, 30), end=time(1), genres=("Soul",))
    jour = _grille(bands=[velours]).day(MERCREDI)

    assert _lu(jour) == [("23:30", "01:00", "Soul")]


def test_le_lendemain_ne_reliste_pas_la_fin_de_la_veille() -> None:
    velours = Band(start=time(23, 30), end=time(1), genres=("Soul",))
    nuit = Band(start=time(1), end=time(3), genres=("Ambient",))
    jour = _grille(bands=[velours, nuit]).day(MERCREDI)

    assert _lu(jour) == [("01:00", "03:00", "Ambient"), ("23:30", "01:00", "Soul")]


def test_une_plage_du_seul_samedi_ne_deborde_pas_sur_le_dimanche() -> None:
    """Une plage du samedi qui passe minuit se lit entière au samedi ; le
    dimanche n'en montre pas la fin."""
    soiree = Band(start=time(21), end=time(2), days=("saturday",), genres=("House",))

    assert _lu(_grille(bands=[soiree]).day(SAMEDI)) == [("21:00", "02:00", "House")]
    assert _lu(_grille(bands=[soiree]).day(DIMANCHE)) == []


# ── Ce que la chaîne demande à la grille effective (GOAL-068) ──────────────


def test_la_prochaine_coupure_nomme_l_emission_qui_vient() -> None:
    """La grille annonce l'émission qui va couper la file, pour que « À suivre »
    n'annonce pas de la musique à cette heure-là."""
    grille = _grille(bands=[GUITARES], shows=[HARDISK])

    coupure = grille.next_replacement(
        MERCREDI.replace(hour=19, minute=58), MERCREDI.replace(hour=20, minute=1)
    )

    assert coupure is not None
    assert coupure.content is HARDISK
    assert coupure.start == MERCREDI.replace(hour=20)


def test_aucune_coupure_annoncee_quand_rien_ne_remplace_la_file() -> None:
    grille = _grille(bands=[GUITARES], shows=[HARDISK])

    assert grille.next_replacement(MERCREDI.replace(hour=15), MERCREDI.replace(hour=16)) is None


def test_un_programme_qui_s_ouvre_est_une_coupure() -> None:
    chloe = Programme(
        name="Chloé", playlist="Chloé", days=(EVERY_DAY,), start=time(18), end=time(20)
    )
    grille = _grille(programmes=[chloe])

    coupure = grille.next_replacement(MERCREDI.replace(hour=17), MERCREDI.replace(hour=19))

    assert coupure is not None and coupure.content is chloe


def test_la_file_n_est_servie_qu_a_la_fin_du_programme() -> None:
    """Pendant un programme, un titre tiré serait jeté et la file se
    retrouverait vide à la reprise : `served_from` reporte à la fin."""
    chloe = Programme(
        name="Chloé", playlist="Chloé", days=(EVERY_DAY,), start=time(18), end=time(20)
    )
    grille = _grille(programmes=[chloe])

    assert grille.served_from(MERCREDI.replace(hour=18, minute=30)) == MERCREDI.replace(hour=20)
    assert grille.served_from(MERCREDI.replace(hour=17)) == MERCREDI.replace(hour=17)


def test_la_file_n_est_servie_qu_a_la_fin_d_un_direct() -> None:
    grille = _grille(shows=[FLASH])

    assert grille.served_from(MERCREDI.replace(hour=12)) == MERCREDI.replace(hour=12, minute=10)


def test_une_emission_sans_duree_ne_se_saute_pas() -> None:
    """Sa fin est inconnue, on ne peut pas reporter le créneau après elle."""
    grille = _grille(shows=[HARDISK])

    assert grille.served_from(MERCREDI.replace(hour=20)) == MERCREDI.replace(hour=20)


def test_un_programme_puis_un_direct_se_sautent_l_un_apres_l_autre() -> None:
    chloe = Programme(
        name="Chloé", playlist="Chloé", days=(EVERY_DAY,), start=time(11), end=time(11, 57)
    )
    grille = _grille(programmes=[chloe], shows=[FLASH])

    assert grille.served_from(MERCREDI.replace(hour=11, minute=30)) == MERCREDI.replace(
        hour=12, minute=10
    )


def test_un_programme_recouvert_par_un_plus_court_ne_coupe_rien() -> None:
    """Le programme recouvert ne prendra pas l'antenne : l'annoncer ferait
    attendre une émission qui n'aura pas lieu."""
    longue = Programme(
        name="La soirée", playlist="A", days=(EVERY_DAY,), start=time(18), end=time(22)
    )
    courte = Programme(
        name="L'heure", playlist="B", days=(EVERY_DAY,), start=time(18), end=time(19)
    )
    grille = _grille(programmes=[longue, courte])

    coupure = grille.next_replacement(MERCREDI.replace(hour=17), MERCREDI.replace(hour=19))

    assert coupure is not None and coupure.content is courte
