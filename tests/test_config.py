"""La configuration se lit, ou le démarrage n'a pas lieu.

Toutes les valeurs de ces tests sont **fictives** : aucun secret ne figure dans
un test, pas plus que dans le TOML (AGENTS.md §2).
"""

import tomllib
from datetime import time
from pathlib import Path

import pytest

from webradio.adapters.config import (
    Settings,
    SettingsError,
    SubsonicCredentials,
    credentials_from,
    load,
    read_env,
    validate,
)
from webradio.adapters.config.loading import load_toml
from webradio.adapters.config.schema import (
    DAYS,
    DEFAULT_ARTIST_RESULTS,
)

TOML_MINIMAL = """
[draw]
artist_gap = 5

[jingles]
folder = "/chemin/vers/jingles"

[state]
database = "/var/lib/local-webradio/etat.sqlite3"
"""

ENV_FICTIF = """
# Un modèle, avec des valeurs inventées.
SUBSONIC_URL=http://exemple.local/
SUBSONIC_UTILISATEUR=auditeur-fictif
SUBSONIC_MOT_DE_PASSE="passe-fictif"
"""


def _ecrire(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _valider(content: str) -> Settings:
    return validate(tomllib.loads(content))


def test_une_configuration_complete_est_lue(tmp_path: Path) -> None:
    content = (
        TOML_MINIMAL
        + """
[draw.votes]
floor = 0.5
ceiling = 3.0
half_life_days = 30

[[bands]]
start = "08:00"
end = "10:00"
genres = ["Chanson française"]

[[shows]]
name = "Une émission"
feed = "https://exemple.local/flux.xml"
days = ["Friday"]
time = "20:00"
"""
    )
    config = load_toml(_ecrire(tmp_path / "webradio.toml", content))

    assert config.draw.artist_gap == 5
    assert config.draw.votes.floor == 0.5
    assert config.bands[0].start == time(8, 0)
    assert config.bands[0].genres == ("Chanson française",)
    assert config.shows[0].days == ("friday",)
    assert config.shows[0].hour == time(20, 0)
    assert config.jingles.folder == "/chemin/vers/jingles"
    assert config.state.database.endswith("etat.sqlite3")


def test_les_reglages_subsonic_ont_des_defauts_declares() -> None:
    config = _valider(TOML_MINIMAL)

    assert config.subsonic.artist_results == DEFAULT_ARTIST_RESULTS


def test_l_ancienne_taille_d_echantillon_est_refusee_en_la_nommant() -> None:
    # La clé a disparu avec l'échantillonnage (GOAL-039) : une configuration
    # qui la porte encore doit le dire, pas l'ignorer en silence.
    content = TOML_MINIMAL + "\n[subsonic]\nsample_size = 500\n"

    with pytest.raises(SettingsError) as refus:
        validate(tomllib.loads(content))

    assert "sample_size" in str(refus.value)


def test_un_mot_de_passe_dans_le_toml_fait_echouer_le_demarrage() -> None:
    content = TOML_MINIMAL + '\n[subsonic]\nmot_de_passe = "peu importe"\n'

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "subsonic.mot_de_passe" in str(refus.value)
    assert "SUBSONIC_MOT_DE_PASSE" in str(refus.value)


def test_un_utilisateur_dans_le_toml_fait_echouer_le_demarrage() -> None:
    content = TOML_MINIMAL + '\n[subsonic]\nutilisateur = "peu importe"\n'

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "SUBSONIC_UTILISATEUR" in str(refus.value)


def test_un_secret_cache_dans_une_liste_de_sections_est_refuse() -> None:
    content = (
        TOML_MINIMAL
        + """
[[shows]]
name = "Une émission"
feed = "https://exemple.local/flux.xml"
days = ["tuesday"]
time = "20:00"
token = "peu importe"
"""
    )

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "shows[0].token" in str(refus.value)


def test_une_cle_inconnue_est_nommee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace("artist_gap = 5", "artist_gap = 5\nartist_gab = 6"))

    assert "draw.artist_gab" in str(refus.value)


def test_une_section_obligatoire_absente_est_nommee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace("[jingles]", "[jinglez]"))

    assert "jinglez" in str(refus.value) or "jingles" in str(refus.value)


def test_une_cle_obligatoire_absente_est_nommee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace('folder = "/chemin/vers/jingles"\n', ""))

    assert "jingles.folder" in str(refus.value)


def test_un_type_incorrect_est_nomme() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace("artist_gap = 5", 'artist_gap = "cinq"'))

    assert "draw.artist_gap" in str(refus.value)
    assert "entier" in str(refus.value)


def test_un_booleen_ne_passe_pas_pour_un_entier() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace("artist_gap = 5", "artist_gap = true"))

    assert "draw.artist_gap" in str(refus.value)


def test_un_port_hors_borne_est_refuse() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + "\n[web]\nport = 70000\n")

    assert "web.port" in str(refus.value)


def test_une_heure_mal_formee_est_nommee() -> None:
    content = (
        TOML_MINIMAL
        + """
[[bands]]
start = "8h"
end = "10:00"
genres = ["Rock"]
"""
    )

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "bands[0].start" in str(refus.value)


def test_une_liste_de_genres_vide_est_refusee() -> None:
    content = (
        TOML_MINIMAL
        + """
[[bands]]
start = "08:00"
end = "10:00"
genres = []
"""
    )

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "bands[0].genres" in str(refus.value)


def test_un_jour_inconnu_est_nomme() -> None:
    content = (
        TOML_MINIMAL
        + """
[[shows]]
name = "Une émission"
feed = "https://exemple.local/flux.xml"
days = ["lundredi"]
time = "20:00"
"""
    )

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "shows[0].days[0]" in str(refus.value)
    assert "lundredi" in str(refus.value)


def test_deux_emissions_au_meme_creneau_font_echouer_le_demarrage_en_les_nommant() -> None:
    content = (
        TOML_MINIMAL
        + """
[[shows]]
name = "Première"
feed = "https://exemple.local/un.xml"
days = ["tuesday", "friday"]
time = "20:00"

[[shows]]
name = "Seconde"
feed = "https://exemple.local/deux.xml"
days = ["friday"]
time = "20:00"
"""
    )

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "Première" in str(refus.value)
    assert "Seconde" in str(refus.value)
    assert "friday" in str(refus.value)


def test_deux_emissions_a_la_meme_heure_des_jours_differents_sont_acceptees() -> None:
    content = (
        TOML_MINIMAL
        + """
[[shows]]
name = "Première"
feed = "https://exemple.local/un.xml"
days = ["tuesday"]
time = "20:00"

[[shows]]
name = "Seconde"
feed = "https://exemple.local/deux.xml"
days = ["friday"]
time = "20:00"
"""
    )

    config = _valider(content)

    assert len(config.shows) == 2


def test_un_plancher_au_dessus_du_plafond_est_refuse() -> None:
    content = TOML_MINIMAL + "\n[draw.votes]\nfloor = 5.0\nceiling = 2.0\n"

    with pytest.raises(SettingsError) as refus:
        _valider(content)

    assert "draw.votes.floor" in str(refus.value)


def test_une_section_qui_n_en_est_pas_une_est_refusee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL.replace("[jingles]\nfolder", "jingles = 3\n[jinglez]\nfolder"))

    assert "jingles" in str(refus.value)


def test_une_suite_de_sections_attendue_ailleurs_est_refusee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider('bands = "aucune"\n' + TOML_MINIMAL)

    assert "bands" in str(refus.value)
    assert "sections" in str(refus.value)


def test_une_section_de_plage_qui_n_en_est_pas_une_est_refusee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider("bands = [1]\n" + TOML_MINIMAL)

    assert "bands[0]" in str(refus.value)


def test_un_toml_mal_forme_est_signale(tmp_path: Path) -> None:
    path = _ecrire(tmp_path / "webradio.toml", "[flux\n")

    with pytest.raises(SettingsError) as refus:
        load_toml(path)

    assert "TOML" in str(refus.value)


def test_un_toml_absent_est_signale(tmp_path: Path) -> None:
    with pytest.raises(SettingsError) as refus:
        load_toml(tmp_path / "absent.toml")

    assert "absent.toml" in str(refus.value)


def test_le_env_fournit_les_identifiants(tmp_path: Path) -> None:
    variables = read_env(_ecrire(tmp_path / ".env", ENV_FICTIF))
    credentials = credentials_from(variables)

    assert credentials.url == "http://exemple.local"
    assert credentials.username == "auditeur-fictif"
    assert credentials.password == "passe-fictif"


def test_une_ligne_env_exportee_est_acceptee(tmp_path: Path) -> None:
    variables = read_env(_ecrire(tmp_path / ".env", "export SUBSONIC_URL=http://exemple.local\n"))

    assert variables["SUBSONIC_URL"] == "http://exemple.local"


def test_un_env_absent_ne_fait_pas_echouer_la_lecture(tmp_path: Path) -> None:
    assert read_env(tmp_path / "absent.env") == {}


def test_une_ligne_env_sans_egal_est_signalee_avec_son_numero(tmp_path: Path) -> None:
    path = _ecrire(tmp_path / ".env", "# un commentaire\nSUBSONIC_URL\n")

    with pytest.raises(SettingsError) as refus:
        read_env(path)

    assert "ligne 2" in str(refus.value)


def test_une_ligne_env_sans_nom_est_signalee(tmp_path: Path) -> None:
    path = _ecrire(tmp_path / ".env", "=valeur\n")

    with pytest.raises(SettingsError) as refus:
        read_env(path)

    assert "ligne 1" in str(refus.value)


def test_un_identifiant_manquant_est_nomme() -> None:
    with pytest.raises(SettingsError) as refus:
        credentials_from({"SUBSONIC_URL": "http://exemple.local"})

    assert "SUBSONIC_UTILISATEUR" in str(refus.value)
    assert "SUBSONIC_MOT_DE_PASSE" in str(refus.value)


def test_le_mot_de_passe_n_apparait_pas_dans_la_representation_des_identifiants() -> None:
    credentials = SubsonicCredentials(
        url="http://exemple.local",
        username="auditeur-fictif",
        password="passe-fictif",
    )

    assert "passe-fictif" not in repr(credentials)
    assert "***" in repr(credentials)


def test_une_variable_du_processus_prime_sur_le_fichier_env(tmp_path: Path) -> None:
    toml = _ecrire(tmp_path / "webradio.toml", TOML_MINIMAL)
    env = _ecrire(tmp_path / ".env", ENV_FICTIF)

    config = load(toml, env, {"SUBSONIC_UTILISATEUR": "autre-auditeur"})

    assert config.credentials.username == "autre-auditeur"
    assert config.credentials.password == "passe-fictif"
    assert config.settings.draw.artist_gap == 5


def test_le_raccourci_tous_les_jours_est_accepte() -> None:
    """SPECS.md §4.11 l'autorise depuis l'origine, mais rien ne l'acceptait :
    `jours = "all"` échouait avec « une liste est attendue »."""
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[shows]]\nname = "E"\nfeed = "https://x.test/f.xml"\n'
        'days = "all"\ntime = "20:00"\n'
    )
    config = validate(brut)
    assert config.shows[0].days == DAYS


def test_un_raccourci_inconnu_est_refuse() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[shows]]\nname = "E"\nfeed = "https://x.test/f.xml"\n'
        'days = "parfois"\ntime = "20:00"\n'
    )
    with pytest.raises(SettingsError, match="parfois"):
        validate(brut)


def test_un_programme_est_lu() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[programmes]]\nname = "Friday"\nplaylist = "Chloé"\n'
        'days = ["friday"]\nstart = "18:00"\nend = "20:00"\n'
    )
    config = validate(brut)
    assert config.programmes[0].name == "Friday"
    assert config.programmes[0].playlist == "Chloé"
    assert config.programmes[0].days == ("friday",)


def test_un_programme_a_clef_inconnue_est_refuse() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[programmes]]\nname = "V"\nplaylist = "C"\ndays = ["monday"]\n'
        'start = "18:00"\nend = "20:00"\ngenre = "rock"\n'
    )
    with pytest.raises(SettingsError, match="genre"):
        validate(brut)


# ── Un direct comme émission (GOAL-015) ─────────────────────────────────────

DIRECT = """
[[shows]]
name = "Flash"
stream = "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"
duration_minutes = 9
days = "all"
time = "12:00"
"""


def test_un_direct_se_declare_avec_son_flux_et_sa_duree() -> None:
    config = _valider(TOML_MINIMAL + DIRECT)
    flash = next(s for s in config.shows if s.name == "Flash")
    assert flash.stream == "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"
    assert flash.duration_minutes == 9
    assert flash.feed is None


def test_un_direct_sans_duree_est_refuse_en_le_disant() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + DIRECT.replace("duration_minutes = 9\n", ""))
    assert "Flash" in str(refus.value)
    assert "duration_minutes" in str(refus.value)


def test_feed_et_stream_ensemble_sont_refuses() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL
            + DIRECT.replace('name = "Flash"', 'name = "Flash"\nfeed = "https://x.test/rss"')
        )
    assert "Flash" in str(refus.value)


def test_une_emission_sans_source_est_refusee() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL
            + DIRECT.replace('stream = "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"\n', "")
        )
    assert "Flash" in str(refus.value)


def test_un_podcast_ne_declare_pas_de_duree() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL
            + DIRECT.replace(
                'stream = "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"',
                'feed = "https://x.test/rss"',
            )
        )
    assert "duration_minutes" in str(refus.value) or "durée" in str(refus.value)


# ── Les plages par jour (GOAL-019) ──────────────────────────────────────────

UNE_PLAGE = """
[[bands]]
start  = "08:00"
end    = "10:00"
genres = ["Chanson française"]
"""


def test_une_plage_sans_jours_vaut_tous_les_jours() -> None:
    config = _valider(TOML_MINIMAL + UNE_PLAGE)
    assert config.bands[0].days == DAYS


def test_une_plage_se_restreint_a_des_jours() -> None:
    config = _valider(TOML_MINIMAL + UNE_PLAGE + 'days = ["saturday"]\n')
    assert config.bands[0].days == ("saturday",)


def test_un_jour_de_plage_inconnu_est_refuse() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + UNE_PLAGE + 'days = ["caturday"]\n')
    assert "bands[0]" in str(refus.value)


def test_une_plage_d_artistes_se_declare() -> None:
    config = _valider(
        TOML_MINIMAL + UNE_PLAGE.replace('genres = ["Chanson française"]', 'artists = ["Air"]')
    )
    assert config.bands[0].artists == ("Air",)
    assert config.bands[0].genres == ()


def test_genres_et_artistes_ensemble_sont_refuses_au_toml() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + UNE_PLAGE + 'artists = ["Air"]\n')
    assert "bands[0]" in str(refus.value)


# ── Une plage au thème tiré au sort (GOAL-037) ──────────────────────────────


def test_une_plage_peut_demander_un_genre_au_hasard() -> None:
    config = _valider(
        TOML_MINIMAL + UNE_PLAGE.replace('genres = ["Chanson française"]', 'random = "genre"')
    )
    assert config.bands[0].random_theme == "genre"
    assert config.bands[0].genres == ()
    assert config.bands[0].artists == ()


def test_une_plage_peut_demander_un_artiste_au_hasard() -> None:
    config = _valider(
        TOML_MINIMAL + UNE_PLAGE.replace('genres = ["Chanson française"]', 'random = "artist"')
    )
    assert config.bands[0].random_theme == "artist"


def test_sans_random_une_plage_ne_tire_rien_au_sort() -> None:
    assert _valider(TOML_MINIMAL + UNE_PLAGE).bands[0].random_theme is None


def test_random_et_genres_ensemble_sont_refuses_au_toml() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + UNE_PLAGE + 'random = "genre"\n')
    assert "exactement une des trois" in str(refus.value)


def test_une_plage_qui_ne_declare_rien_du_tout_est_refusee_au_toml() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(TOML_MINIMAL + UNE_PLAGE.replace('genres = ["Chanson française"]', ""))
    assert "exactement une des trois" in str(refus.value)


def test_une_sorte_de_theme_inconnue_est_refusee_en_la_nommant() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL + UNE_PLAGE.replace('genres = ["Chanson française"]', 'random = "album"')
        )
    assert "bands[0].random" in str(refus.value)
    assert "album" in str(refus.value)


# ── Une chaîne YouTube comme émission (GOAL-025) ────────────────────────────


def test_une_emission_youtube_se_declare_par_sa_chaine() -> None:
    config = _valider(
        TOML_MINIMAL
        + '\n[[shows]]\nname = "Hardisk"\nyoutube = "https://www.youtube.com/@hardisk"\n'
        + 'days = ["wednesday"]\ntime = "20:00"\n'
    )
    show = next(s for s in config.shows if s.name == "Hardisk")
    assert show.youtube == "https://www.youtube.com/@hardisk"
    assert show.feed is None and show.stream is None
    assert config.youtube.timeout_seconds == 60.0


def test_une_emission_a_exactement_une_source() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL
            + '\n[[shows]]\nname = "Double"\nyoutube = "https://youtube.com/@x"\n'
            + 'feed = "https://x.test/rss"\ndays = ["wednesday"]\ntime = "20:00"\n'
        )
    assert "Double" in str(refus.value)


def test_une_emission_youtube_ne_declare_pas_de_duree() -> None:
    with pytest.raises(SettingsError) as refus:
        _valider(
            TOML_MINIMAL
            + '\n[[shows]]\nname = "Hardisk"\nyoutube = "https://youtube.com/@x"\n'
            + 'duration_minutes = 30\ndays = ["wednesday"]\ntime = "20:00"\n'
        )
    assert "Hardisk" in str(refus.value)


# ── Les génériques (GOAL-029) ───────────────────────────────────────────────


def test_une_plage_declare_ses_generiques_optionnels() -> None:
    config = _valider(TOML_MINIMAL + UNE_PLAGE + 'intro = "debut.mp3"\noutro = "fin.mp3"\n')
    assert config.bands[0].intro == "debut.mp3"
    assert config.bands[0].outro == "fin.mp3"


def test_sans_generique_rien_ne_change() -> None:
    config = _valider(TOML_MINIMAL + UNE_PLAGE)
    assert config.bands[0].intro is None
    assert config.bands[0].outro is None


def test_le_jingle_d_encore_se_configure_et_a_un_defaut() -> None:
    assert _valider(TOML_MINIMAL).jingles.encore == "encore.mp3"
    config = _valider(TOML_MINIMAL.replace("[jingles]", '[jingles]\nencore = "bravo.mp3"'))
    assert config.jingles.encore == "bravo.mp3"
