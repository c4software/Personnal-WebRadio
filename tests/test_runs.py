"""Les suites : ancre, longueur tirée, rupture, remise à zéro (SPECS.md §7 n°31)."""

from tests.fakes import track
from webradio.core.rng import ScriptedRandom
from webradio.core.runs import Directive, Mode, Runs, era_of

PLAGE = "rock"  # la clé de remise à zéro est opaque : une chaîne suffit au test


def test_la_decennie_se_deduit_de_l_annee() -> None:
    assert era_of(track("1", "Air", year=1977)) == 1970
    assert era_of(track("2", "Air")) is None


def test_sans_mode_aucune_suite_ne_s_ouvre() -> None:
    runs = Runs(ScriptedRandom([]))
    runs.observe(PLAGE, None, track("1", "Air"))
    assert runs.directive(PLAGE, None) is None


def test_la_double_dose_impose_le_meme_artiste_une_fois_sans_le_meme_titre() -> None:
    """Longueur fixe : le hasard n'est pas consommé, le script vide le prouve."""
    runs = Runs(ScriptedRandom([]))
    runs.observe(PLAGE, Mode.DOUBLE_DOSE, track("a1", "Air"))
    assert runs.directive(PLAGE, Mode.DOUBLE_DOSE) == Directive(
        artist="Air", exclude=frozenset({"a1"}), bypass_window=True
    )
    runs.observe(PLAGE, Mode.DOUBLE_DOSE, track("a2", "Air"))
    assert runs.directive(PLAGE, Mode.DOUBLE_DOSE) is None  # la dose est servie


def test_le_passionne_d_artiste_tire_sa_longueur_entre_3_et_6() -> None:
    """`ScriptedRandom([1])` sur [3, 4, 5, 6] donne 4 titres : l'ancre puis trois."""
    runs = Runs(ScriptedRandom([1]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    for identifier in ("b2", "b3", "b4"):
        directive = runs.directive(PLAGE, Mode.ARTIST_FAN)
        assert directive is not None and directive.artist == "Bowie"
        runs.observe(PLAGE, Mode.ARTIST_FAN, track(identifier, "Bowie"))
    assert runs.directive(PLAGE, Mode.ARTIST_FAN) is None


def test_les_titres_deja_servis_sont_exclus_de_la_suite() -> None:
    runs = Runs(ScriptedRandom([3]))  # [3, 4, 5, 6] : 6 titres
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b2", "Bowie"))
    directive = runs.directive(PLAGE, Mode.ARTIST_FAN)
    assert directive is not None
    assert directive.exclude == frozenset({"b1", "b2"})


def test_le_passionne_d_epoque_ancre_la_decennie_et_laisse_la_fenetre_agir() -> None:
    """`ScriptedRandom([0])` sur [2, 3, 4, 5, 6] donne 2 titres d'une même décennie."""
    runs = Runs(ScriptedRandom([0]))
    runs.observe(PLAGE, Mode.ERA_FAN, track("c1", "Air", year=1977))
    directive = runs.directive(PLAGE, Mode.ERA_FAN)
    assert directive == Directive(era=1970, exclude=frozenset({"c1"}))
    assert not directive.bypass_window  # les artistes varient : la fenêtre s'applique
    runs.observe(PLAGE, Mode.ERA_FAN, track("c2", "Bowie", year=1975))
    assert runs.directive(PLAGE, Mode.ERA_FAN) is None


def test_une_ancre_sans_annee_n_ouvre_pas_de_suite_d_epoque() -> None:
    """Le hasard n'est pas consommé (script vide) : la soirée se rejoue à
    l'identique avec ou sans ce cas."""
    runs = Runs(ScriptedRandom([]))
    runs.observe(PLAGE, Mode.ERA_FAN, track("c1", "Air"))
    assert runs.directive(PLAGE, Mode.ERA_FAN) is None


def test_un_changement_de_contrainte_remet_la_suite_a_zero() -> None:
    runs = Runs(ScriptedRandom([1]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    assert runs.directive(PLAGE, Mode.ARTIST_FAN) is not None
    assert runs.directive("jazz", Mode.ARTIST_FAN) is None  # autre plage : rien ne suit


def test_le_tirage_libre_remet_la_suite_a_zero() -> None:
    runs = Runs(ScriptedRandom([1, 1]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    runs.directive(None, None)
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b2", "Bowie"))
    directive = runs.directive(PLAGE, Mode.ARTIST_FAN)
    assert directive is not None
    assert directive.exclude == frozenset({"b2"})  # une suite neuve, pas la reprise


def test_une_piste_qui_ne_colle_pas_ouvre_la_suite_suivante() -> None:
    """La rupture (plus de candidats, ancre relâchée) n'arrête pas le mode : le
    morceau tiré devient l'ancre d'une nouvelle suite."""
    runs = Runs(ScriptedRandom([1, 1]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("p1", "Portishead"))
    directive = runs.directive(PLAGE, Mode.ARTIST_FAN)
    assert directive is not None
    assert directive.artist == "Portishead"
    assert directive.exclude == frozenset({"p1"})


def test_rompre_une_suite_d_epoque_fait_eviter_sa_decennie() -> None:
    """Le retirage sur une plage `era_fan` rompt la suite et en ouvre une autre,
    d'une autre décennie (GOAL-059)."""
    runs = Runs(ScriptedRandom([0, 0]))
    runs.observe(PLAGE, Mode.ERA_FAN, track("1", "Air", year=1998))
    assert runs.break_run()
    assert runs.directive(PLAGE, Mode.ERA_FAN) == Directive(avoid_era=1990)
    runs.observe(PLAGE, Mode.ERA_FAN, track("2", "Bowie", year=1977))
    suite = runs.directive(PLAGE, Mode.ERA_FAN)
    assert suite is not None and suite.era == 1970 and suite.avoid_era is None


def test_rompre_une_suite_d_artiste_fait_eviter_son_artiste() -> None:
    runs = Runs(ScriptedRandom([0, 0]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    assert runs.break_run()
    assert runs.directive(PLAGE, Mode.ARTIST_FAN) == Directive(avoid_artist="Bowie")


def test_une_double_dose_ou_l_absence_de_mode_ne_se_rompt_pas() -> None:
    runs = Runs(ScriptedRandom([]))
    assert not runs.break_run()
    runs.observe(PLAGE, Mode.DOUBLE_DOSE, track("a1", "Air"))
    assert not runs.break_run()


def test_l_evitement_ne_survit_pas_a_un_changement_de_plage() -> None:
    runs = Runs(ScriptedRandom([0]))
    runs.observe(PLAGE, Mode.ARTIST_FAN, track("b1", "Bowie"))
    runs.break_run()
    assert runs.directive("jazz", Mode.ARTIST_FAN) is None
