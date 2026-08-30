"""La configuration se lit, ou le démarrage n'a pas lieu.

Toutes les valeurs de ces tests sont **fictives** : aucun secret ne figure dans
un test, pas plus que dans le TOML (AGENTS.md §2).
"""

import tomllib
from datetime import time
from pathlib import Path

import pytest

from webradio.adapters.config import (
    Configuration,
    ErreurConfiguration,
    IdentifiantsNavidrome,
    charger,
    identifiants_depuis,
    lire_env,
    valider,
)
from webradio.adapters.config.loading import charger_toml
from webradio.adapters.config.schema import (
    JOURS,
    RESULTATS_ARTISTE_DEFAUT,
    TAILLE_ECHANTILLON_DEFAUT,
)

TOML_MINIMAL = """
[flux]
adresse = "0.0.0.0"
port = 8000
format = "mp3"
debit_kbps = 128
frequence_hz = 44100
canaux = 2

[tirage]
non_repetition_artistes = 5

[jingles]
dossier = "/chemin/vers/jingles"

[etat]
base = "/var/lib/local-webradio/etat.sqlite3"
"""

ENV_FICTIF = """
# Un modèle, avec des valeurs inventées.
NAVIDROME_URL=http://exemple.local/
NAVIDROME_UTILISATEUR=auditeur-fictif
NAVIDROME_MOT_DE_PASSE="passe-fictif"
"""


def _ecrire(chemin: Path, contenu: str) -> Path:
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def _valider(contenu: str) -> Configuration:
    return valider(tomllib.loads(contenu))


def test_une_configuration_complete_est_lue(tmp_path: Path) -> None:
    contenu = (
        TOML_MINIMAL
        + """
[tirage.votes]
plancher = 0.5
plafond = 3.0
demi_vie_jours = 30
poids_croise = 0.1

[[plages]]
debut = "08:00"
fin = "10:00"
genres = ["Chanson française"]

[[emissions]]
nom = "Une émission"
flux = "https://exemple.local/flux.xml"
jours = ["Vendredi"]
heure = "20:00"
"""
    )
    reglages = charger_toml(_ecrire(tmp_path / "webradio.toml", contenu))

    assert reglages.flux.port == 8000
    assert reglages.tirage.non_repetition_artistes == 5
    assert reglages.tirage.votes.plancher == 0.5
    assert reglages.plages[0].debut == time(8, 0)
    assert reglages.plages[0].genres == ("Chanson française",)
    assert reglages.emissions[0].jours == ("vendredi",)
    assert reglages.emissions[0].heure == time(20, 0)
    assert reglages.jingles.dossier == "/chemin/vers/jingles"
    assert reglages.etat.base.endswith("etat.sqlite3")


def test_les_reglages_navidrome_ont_des_defauts_declares() -> None:
    reglages = _valider(TOML_MINIMAL)

    assert reglages.navidrome.taille_echantillon == TAILLE_ECHANTILLON_DEFAUT
    assert reglages.navidrome.resultats_artiste == RESULTATS_ARTISTE_DEFAUT


def test_un_mot_de_passe_dans_le_toml_fait_echouer_le_demarrage() -> None:
    contenu = TOML_MINIMAL + '\n[navidrome]\nmot_de_passe = "peu importe"\n'

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "navidrome.mot_de_passe" in str(refus.value)
    assert "NAVIDROME_MOT_DE_PASSE" in str(refus.value)


def test_un_utilisateur_dans_le_toml_fait_echouer_le_demarrage() -> None:
    contenu = TOML_MINIMAL + '\n[navidrome]\nutilisateur = "peu importe"\n'

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "NAVIDROME_UTILISATEUR" in str(refus.value)


def test_un_secret_cache_dans_une_liste_de_sections_est_refuse() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[emissions]]
nom = "Une émission"
flux = "https://exemple.local/flux.xml"
jours = ["mardi"]
heure = "20:00"
token = "peu importe"
"""
    )

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "emissions[0].token" in str(refus.value)


def test_une_cle_inconnue_est_nommee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("port = 8000", "port = 8000\nprot = 8001"))

    assert "flux.prot" in str(refus.value)


def test_une_section_obligatoire_absente_est_nommee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("[jingles]", "[jinglez]"))

    assert "jinglez" in str(refus.value) or "jingles" in str(refus.value)


def test_une_cle_obligatoire_absente_est_nommee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace('adresse = "0.0.0.0"\n', ""))

    assert "flux.adresse" in str(refus.value)


def test_un_type_incorrect_est_nomme() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("port = 8000", 'port = "huit-mille"'))

    assert "flux.port" in str(refus.value)
    assert "entier" in str(refus.value)


def test_un_booleen_ne_passe_pas_pour_un_entier() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("port = 8000", "port = true"))

    assert "flux.port" in str(refus.value)


def test_un_port_hors_borne_est_refuse() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("port = 8000", "port = 70000"))

    assert "flux.port" in str(refus.value)


def test_une_heure_mal_formee_est_nommee() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[plages]]
debut = "8h"
fin = "10:00"
genres = ["Rock"]
"""
    )

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "plages[0].debut" in str(refus.value)


def test_une_liste_de_genres_vide_est_refusee() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[plages]]
debut = "08:00"
fin = "10:00"
genres = []
"""
    )

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "plages[0].genres" in str(refus.value)


def test_un_jour_inconnu_est_nomme() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[emissions]]
nom = "Une émission"
flux = "https://exemple.local/flux.xml"
jours = ["lundredi"]
heure = "20:00"
"""
    )

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "emissions[0].jours[0]" in str(refus.value)
    assert "lundredi" in str(refus.value)


def test_deux_emissions_au_meme_creneau_font_echouer_le_demarrage_en_les_nommant() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[emissions]]
nom = "Première"
flux = "https://exemple.local/un.xml"
jours = ["mardi", "vendredi"]
heure = "20:00"

[[emissions]]
nom = "Seconde"
flux = "https://exemple.local/deux.xml"
jours = ["vendredi"]
heure = "20:00"
"""
    )

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "Première" in str(refus.value)
    assert "Seconde" in str(refus.value)
    assert "vendredi" in str(refus.value)


def test_deux_emissions_a_la_meme_heure_des_jours_differents_sont_acceptees() -> None:
    contenu = (
        TOML_MINIMAL
        + """
[[emissions]]
nom = "Première"
flux = "https://exemple.local/un.xml"
jours = ["mardi"]
heure = "20:00"

[[emissions]]
nom = "Seconde"
flux = "https://exemple.local/deux.xml"
jours = ["vendredi"]
heure = "20:00"
"""
    )

    reglages = _valider(contenu)

    assert len(reglages.emissions) == 2


def test_un_plancher_au_dessus_du_plafond_est_refuse() -> None:
    contenu = TOML_MINIMAL + "\n[tirage.votes]\nplancher = 5.0\nplafond = 2.0\n"

    with pytest.raises(ErreurConfiguration) as refus:
        _valider(contenu)

    assert "tirage.votes.plancher" in str(refus.value)


def test_une_section_qui_n_en_est_pas_une_est_refusee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider(TOML_MINIMAL.replace("[jingles]\ndossier", "jingles = 3\n[jinglez]\ndossier"))

    assert "jingles" in str(refus.value)


def test_une_suite_de_sections_attendue_ailleurs_est_refusee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider('plages = "aucune"\n' + TOML_MINIMAL)

    assert "plages" in str(refus.value)
    assert "sections" in str(refus.value)


def test_une_section_de_plage_qui_n_en_est_pas_une_est_refusee() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        _valider("plages = [1]\n" + TOML_MINIMAL)

    assert "plages[0]" in str(refus.value)


def test_un_toml_mal_forme_est_signale(tmp_path: Path) -> None:
    chemin = _ecrire(tmp_path / "webradio.toml", "[flux\n")

    with pytest.raises(ErreurConfiguration) as refus:
        charger_toml(chemin)

    assert "TOML" in str(refus.value)


def test_un_toml_absent_est_signale(tmp_path: Path) -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        charger_toml(tmp_path / "absent.toml")

    assert "absent.toml" in str(refus.value)


def test_le_env_fournit_les_identifiants(tmp_path: Path) -> None:
    variables = lire_env(_ecrire(tmp_path / ".env", ENV_FICTIF))
    identifiants = identifiants_depuis(variables)

    assert identifiants.url == "http://exemple.local"
    assert identifiants.utilisateur == "auditeur-fictif"
    assert identifiants.mot_de_passe == "passe-fictif"


def test_une_ligne_env_exportee_est_acceptee(tmp_path: Path) -> None:
    variables = lire_env(_ecrire(tmp_path / ".env", "export NAVIDROME_URL=http://exemple.local\n"))

    assert variables["NAVIDROME_URL"] == "http://exemple.local"


def test_un_env_absent_ne_fait_pas_echouer_la_lecture(tmp_path: Path) -> None:
    assert lire_env(tmp_path / "absent.env") == {}


def test_une_ligne_env_sans_egal_est_signalee_avec_son_numero(tmp_path: Path) -> None:
    chemin = _ecrire(tmp_path / ".env", "# un commentaire\nNAVIDROME_URL\n")

    with pytest.raises(ErreurConfiguration) as refus:
        lire_env(chemin)

    assert "ligne 2" in str(refus.value)


def test_une_ligne_env_sans_nom_est_signalee(tmp_path: Path) -> None:
    chemin = _ecrire(tmp_path / ".env", "=valeur\n")

    with pytest.raises(ErreurConfiguration) as refus:
        lire_env(chemin)

    assert "ligne 1" in str(refus.value)


def test_un_identifiant_manquant_est_nomme() -> None:
    with pytest.raises(ErreurConfiguration) as refus:
        identifiants_depuis({"NAVIDROME_URL": "http://exemple.local"})

    assert "NAVIDROME_UTILISATEUR" in str(refus.value)
    assert "NAVIDROME_MOT_DE_PASSE" in str(refus.value)


def test_le_mot_de_passe_n_apparait_pas_dans_la_representation_des_identifiants() -> None:
    identifiants = IdentifiantsNavidrome(
        url="http://exemple.local",
        utilisateur="auditeur-fictif",
        mot_de_passe="passe-fictif",
    )

    assert "passe-fictif" not in repr(identifiants)
    assert "***" in repr(identifiants)


def test_une_variable_du_processus_prime_sur_le_fichier_env(tmp_path: Path) -> None:
    toml = _ecrire(tmp_path / "webradio.toml", TOML_MINIMAL)
    env = _ecrire(tmp_path / ".env", ENV_FICTIF)

    reglages = charger(toml, env, {"NAVIDROME_UTILISATEUR": "autre-auditeur"})

    assert reglages.identifiants.utilisateur == "autre-auditeur"
    assert reglages.identifiants.mot_de_passe == "passe-fictif"
    assert reglages.configuration.flux.port == 8000


def test_le_raccourci_tous_les_jours_est_accepte() -> None:
    """SPECS.md §4.11 l'autorise depuis l'origine, mais rien ne l'acceptait :
    `jours = "tous"` échouait avec « une liste est attendue »."""
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[emissions]]\nnom = "E"\nflux = "https://x.test/f.xml"\n'
        'jours = "tous"\nheure = "20:00"\n'
    )
    config = valider(brut)
    assert config.emissions[0].jours == JOURS


def test_un_raccourci_inconnu_est_refuse() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[emissions]]\nnom = "E"\nflux = "https://x.test/f.xml"\n'
        'jours = "parfois"\nheure = "20:00"\n'
    )
    with pytest.raises(ErreurConfiguration, match="parfois"):
        valider(brut)


def test_un_programme_est_lu() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[programmes]]\nnom = "Vendredi"\nplaylist = "Chloé"\n'
        'jours = ["vendredi"]\ndebut = "18:00"\nfin = "20:00"\n'
    )
    config = valider(brut)
    assert config.programmes[0].nom == "Vendredi"
    assert config.programmes[0].playlist == "Chloé"
    assert config.programmes[0].jours == ("vendredi",)


def test_un_programme_a_clef_inconnue_est_refuse() -> None:
    brut = tomllib.loads(
        TOML_MINIMAL + '\n[[programmes]]\nnom = "V"\nplaylist = "C"\njours = ["lundi"]\n'
        'debut = "18:00"\nfin = "20:00"\ngenre = "rock"\n'
    )
    with pytest.raises(ErreurConfiguration, match="genre"):
        valider(brut)
