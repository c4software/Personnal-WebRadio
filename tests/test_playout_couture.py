"""La couture de la grille derrière les prochains titres (GOAL-078)."""

from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from tests.fakes import FakeSource, track
from tests.test_playout import _programme
from webradio.core.bands import Band
from webradio.core.clock import FrozenClock
from webradio.core.control import Kind
from webradio.core.shows import Show as ShowCase

# Le 2026-09-06 est un dimanche : la grille de podcasts de l'auteur.
DIMANCHE_20H = datetime(2026, 9, 6, 20, 5, tzinfo=UTC)
ACTUS = ShowCase(name="Podcasts - actus", days=("sunday",), hour=time(20), end=time(21))
LONGS = ShowCase(name="Podcasts - longs formats", days=("sunday",), hour=time(21), end=time(23))
SOIREE = Band(start=time(20), end=time(22), genres=("rock",))
NUIT = Band(start=time(22), end=time(23, 30), genres=("ambient",))


def test_la_liste_coud_l_emission_en_cours_puis_la_suite_de_la_grille(tmp_path: Path) -> None:
    """Pendant un épisode de podcast, rien ne se date : la couture part de
    maintenant, dit jusqu'à quand l'émission tient, nomme celle qui suit, puis
    la musique qui reprend. Aucune période n'y figure deux fois."""
    montre = FrozenClock(DIMANCHE_20H)
    programme, _ = _programme(tmp_path, bands=[SOIREE, NUIT], clock=montre, shows=[ACTUS, LONGS])

    liste = programme.upcoming(None)

    assert [(i.kind, i.label, i.at) for i in liste] == [
        (Kind.SHOW, "Podcasts - actus", None),
        (Kind.SHOW, "Podcasts - longs formats", DIMANCHE_20H.replace(hour=21, minute=0)),
        (Kind.MUSIC, None, DIMANCHE_20H.replace(hour=23, minute=0)),
    ]
    fins = [i.period.end for i in liste if i.period is not None]
    assert fins == [
        DIMANCHE_20H.replace(hour=21, minute=0),
        DIMANCHE_20H.replace(hour=23, minute=0),
        DIMANCHE_20H.replace(hour=23, minute=30),
    ]
    assert len({i.period for i in liste}) == len(liste)


def test_la_couture_reprend_la_grille_apres_le_dernier_titre_date(tmp_path: Path) -> None:
    """Deux titres datés jusqu'à 16 h 05 dans la plage de 15 h : la plage de
    17 h est cousue avec son heure, et le trou de 16 h ne s'annonce pas
    (SPECS.md §4.4)."""
    montre = FrozenClock(datetime(2026, 9, 6, 15, 55, tzinfo=UTC))
    plages = [
        Band(start=time(15), end=time(16), genres=("rock",)),
        Band(start=time(17), end=time(18), genres=("électro",)),
    ]
    programme, _ = _programme(tmp_path, bands=plages, clock=montre, lookahead=2)
    depart = montre.now()

    programme.prepare(from_instant=depart)
    liste = programme.upcoming(depart)

    assert [(i.kind, i.at) for i in liste] == [
        (Kind.MUSIC, depart),
        (Kind.MUSIC, depart + timedelta(minutes=3)),
        (Kind.MUSIC, datetime(2026, 9, 6, 17, 0, tzinfo=UTC)),
    ]
    assert liste[-1].period is not None
    assert liste[-1].period.start == datetime(2026, 9, 6, 17, 0, tzinfo=UTC)


def test_rien_n_est_cousu_au_dela_de_l_horizon(tmp_path: Path) -> None:
    """Une plage qui commence après l'horizon n'est pas annoncée."""
    montre = FrozenClock(datetime(2026, 9, 6, 15, 55, tzinfo=UTC))
    plages = [Band(start=time(19), end=time(20), genres=("rock",))]
    programme, _ = _programme(tmp_path, bands=plages, clock=montre, horizon=timedelta(hours=3))

    assert programme.upcoming(None) == []


def test_sans_grille_effective_la_liste_ne_coud_rien(tmp_path: Path) -> None:
    """La grille effective est facultative : sans elle, la liste s'arrête à ce
    qu'elle a tiré."""
    montre = FrozenClock(DIMANCHE_20H)
    programme, _ = _programme(
        tmp_path, bands=[SOIREE, NUIT], clock=montre, shows=[ACTUS], effective=False
    )

    assert programme.upcoming(None) == []


def test_la_couture_ne_consomme_aucun_tirage(tmp_path: Path) -> None:
    """La couture lit la grille, elle n'interroge pas la source : deux lectures
    de suite rendent la même liste et n'appellent personne."""
    source = FakeSource([track("1", "Air", genre="rock")])
    montre = FrozenClock(DIMANCHE_20H)
    programme, _ = _programme(
        tmp_path, source=source, bands=[SOIREE, NUIT], clock=montre, shows=[ACTUS, LONGS]
    )

    premiere = programme.upcoming(None)
    appels = source.appels
    seconde = programme.upcoming(None)

    assert premiere == seconde
    assert source.appels == appels
