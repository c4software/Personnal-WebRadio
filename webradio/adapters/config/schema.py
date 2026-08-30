"""Le schéma de configuration, et sa validation au démarrage.

Deux règles commandent tout ce fichier (SPECS.md §6.2) :

1. **Une configuration invalide empêche le démarrage et nomme la clé fautive.**
   Une radio qui démarre en ignorant la moitié de sa configuration est pire
   qu'une radio qui refuse de démarrer : elle diffuse quelque chose qui n'est
   pas ce qu'on lui a demandé, et personne ne s'en aperçoit.
2. **Un secret trouvé dans le TOML est une erreur, pas une commodité.** Le refus
   nomme la variable d'environnement dont la valeur aurait dû venir.

Une clé inconnue est refusée elle aussi : une clé mal orthographiée
silencieusement ignorée est exactement le cas que la règle 1 veut empêcher.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import time
from typing import Any, NoReturn

# Les trois variables du `.env`. Elles ne portent aucune valeur ici : seulement
# leur nom, qui sert à dire d'où un secret aurait dû venir.
VARIABLE_URL = "NAVIDROME_URL"
VARIABLE_UTILISATEUR = "NAVIDROME_UTILISATEUR"
VARIABLE_MOT_DE_PASSE = "NAVIDROME_MOT_DE_PASSE"

# Un fragment de nom de clé qui trahit un secret, et l'origine attendue de sa
# valeur. La recherche porte sur le nom, jamais sur la valeur : une valeur qui
# « ressemble » à un mot de passe n'est pas un critère, un nom de clé l'est.
SECRETS_INTERDITS: Mapping[str, str] = {
    "mot_de_passe": VARIABLE_MOT_DE_PASSE,
    "motdepasse": VARIABLE_MOT_DE_PASSE,
    "password": VARIABLE_MOT_DE_PASSE,
    "passwd": VARIABLE_MOT_DE_PASSE,
    "utilisateur": VARIABLE_UTILISATEUR,
    "username": VARIABLE_UTILISATEUR,
    "jeton": "",
    "token": "",
    "secret": "",
    "cle_api": "",
    "api_key": "",
    "apikey": "",
}

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
# SPECS.md §4.11 autorise `jours = "tous"` comme raccourci des sept jours.
TOUS_LES_JOURS = "tous"

# Défauts déclarés au même endroit que la clé qu'ils concernent, faute de quoi
# ils seraient « en dur » quelque part dans le code (AGENTS.md §2).
NON_REPETITION_DEFAUT = 5
VOTES_PLANCHER_DEFAUT = 0.25
VOTES_PLAFOND_DEFAUT = 4.0
VOTES_DEMI_VIE_DEFAUT = 90
VOTES_POIDS_CROISE_DEFAUT = 0.25
TAILLE_ECHANTILLON_DEFAUT = 500
RESULTATS_ARTISTE_DEFAUT = 50
DELAI_SECONDES_DEFAUT = 10.0

PORT_MAXIMUM = 65535

# Le temps qu'une écriture accepte d'attendre un verrou SQLite. Deux processus
# touchent la base : la chaîne et le serveur web (ARCHITECTURE.md §5.1).
DELAI_ETAT_DEFAUT = 5.0
# Un flux de podcast qui ne répond pas ne bloque pas la radio : l'émission est
# perdue et la musique continue (SPECS.md §4.11). Le délai reste donc court.
DELAI_PODCAST_DEFAUT = 15.0
# L'interface et l'API partagent le port du flux : une seule chose à ouvrir.
# Écoute sur toutes les interfaces : la radio est faite pour être jointe depuis
# le réseau local, et elle n'est jamais exposée sur Internet (SPECS.md §3).
ADRESSE_WEB_DEFAUT = "0.0.0.0"
PORT_WEB_DEFAUT = 8000
# L'intervalle auquel la page redemande ce qui passe. Trop court, elle
# interroge pour rien ; trop long, un « encore » semble sans effet.
RAFRAICHISSEMENT_DEFAUT = 5.0


class ErreurConfiguration(Exception):
    """Le démarrage est refusé, et la clé fautive est nommée.

    Elle est levée avant que quoi que ce soit ne soit diffusé : c'est le régime
    « au démarrage, une erreur est fatale et se dit » (SPECS.md §5).
    """


@dataclass(frozen=True, slots=True)
class ConfigurationFlux:
    """Ce qui est servi aux auditeurs, et sous quelle forme."""

    adresse: str
    port: int
    format: str
    debit_kbps: int
    frequence_hz: int
    canaux: int


@dataclass(frozen=True, slots=True)
class ConfigurationVotes:
    """La pondération d'un morceau par les votes (SPECS.md §4.12)."""

    plancher: float
    plafond: float
    demi_vie_jours: int
    poids_croise: float


@dataclass(frozen=True, slots=True)
class ConfigurationTirage:
    """Ce que le tirage doit respecter."""

    non_repetition_artistes: int
    votes: ConfigurationVotes


@dataclass(frozen=True, slots=True)
class ConfigurationJingles:
    """Seul le dossier se configure : les noms des jingles sont fixes."""

    dossier: str


@dataclass(frozen=True, slots=True)
class Plage:
    """Un moment thématique : des genres, entre deux heures."""

    debut: time
    fin: time
    genres: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfigurationEtat:
    """La base qui retient le dernier épisode diffusé et les votes.

    `delai_secondes` est le temps qu'une écriture accepte d'attendre un verrou :
    deux processus vivants touchent cette base — la chaîne de diffusion et le
    serveur web (ARCHITECTURE.md §5.1).
    """

    base: str
    delai_secondes: float


@dataclass(frozen=True, slots=True)
class ConfigurationWeb:
    """L'interface et l'API.

    `rafraichissement_secondes` est l'intervalle auquel la page redemande à
    l'API ce qui passe. Trop court, elle interroge pour rien ; trop long, un
    « encore » semble sans effet.
    """

    adresse: str
    port: int
    rafraichissement_secondes: float


@dataclass(frozen=True, slots=True)
class ConfigurationPodcast:
    """Le délai au-delà duquel un flux de podcast est réputé injoignable.

    Il doit rester court : une émission qui ne répond pas ne bloque pas la
    radio, elle est perdue et la musique continue (SPECS.md §4.11).
    """

    delai_secondes: float


@dataclass(frozen=True, slots=True)
class ProgrammeDeclare:
    """Une plage de temps où la musique vient d'une liste de lecture.

    Elle porte des **jours** en plus des heures, et sa source est une liste
    choisie plutôt qu'un genre — c'est ce qui la distingue d'une `Plage`
    (SPECS.md §4.13).
    """

    nom: str
    playlist: str
    jours: tuple[str, ...]
    debut: time
    fin: time


@dataclass(frozen=True, slots=True)
class Emission:
    """Un podcast diffusé à jour et heure dits."""

    nom: str
    flux: str
    jours: tuple[str, ...]
    heure: time


@dataclass(frozen=True, slots=True)
class ConfigurationNavidrome:
    """Ce que la source Navidrome a besoin de savoir, hors identifiants.

    `taille_echantillon` est un nombre de pistes demandé au serveur, pas une
    borne du tirage : le serveur tronque au-delà de son propre plafond, ce que
    l'adaptateur sait et rappelle (docs/navidrome.md §2.1).
    """

    taille_echantillon: int
    resultats_artiste: int
    delai_secondes: float


@dataclass(frozen=True, slots=True)
class Configuration:
    """Tout ce que le TOML décrit, une fois validé. Aucun secret n'y figure."""

    flux: ConfigurationFlux
    tirage: ConfigurationTirage
    jingles: ConfigurationJingles
    plages: tuple[Plage, ...]
    etat: ConfigurationEtat
    emissions: tuple[Emission, ...]
    programmes: tuple[ProgrammeDeclare, ...]
    navidrome: ConfigurationNavidrome
    web: ConfigurationWeb
    podcast: ConfigurationPodcast


@dataclass(frozen=True, slots=True, repr=False)
class IdentifiantsNavidrome:
    """Les trois valeurs qui viennent du `.env`, et d'aucun autre endroit.

    La représentation masque le mot de passe : un objet passé par mégarde à un
    appel de journalisation ne doit pas suffire à le divulguer (AGENTS.md §2).
    """

    url: str
    utilisateur: str
    mot_de_passe: str

    def __repr__(self) -> str:
        return (
            f"IdentifiantsNavidrome(url={self.url!r}, "
            f"utilisateur={self.utilisateur!r}, mot_de_passe=***)"
        )


@dataclass(frozen=True, slots=True)
class Reglages:
    """Les deux moitiés de la configuration, réunies pour l'assemblage."""

    configuration: Configuration
    identifiants: IdentifiantsNavidrome


def _refuser(chemin: str, raison: str) -> NoReturn:
    message = f"configuration invalide — clé « {chemin} » : {raison}"
    raise ErreurConfiguration(message)


def _chemin(prefixe: str, cle: str) -> str:
    return f"{prefixe}.{cle}" if prefixe else cle


def refuser_les_secrets(brut: Mapping[str, Any], prefixe: str = "") -> None:
    """Refuse toute clé dont le nom trahit un secret, à n'importe quelle profondeur.

    Le contrôle porte sur le nom de la clé et non sur sa valeur : une valeur qui
    ressemble à un mot de passe n'est pas un critère utilisable, alors qu'un nom
    l'est, et c'est le nom que l'auteur d'un TOML écrit en connaissance de cause.
    """
    for cle, valeur in brut.items():
        chemin = _chemin(prefixe, cle)
        minuscule = cle.lower()
        for fragment, origine in SECRETS_INTERDITS.items():
            if fragment in minuscule:
                ou = f"« {origine} » dans le fichier .env" if origine else "le fichier .env"
                _refuser(chemin, f"c'est un secret, sa valeur doit venir de {ou} (SPECS.md §6.1)")
        if isinstance(valeur, Mapping):
            refuser_les_secrets(valeur, chemin)
        elif isinstance(valeur, list):
            for rang, element in enumerate(valeur):
                if isinstance(element, Mapping):
                    refuser_les_secrets(element, f"{chemin}[{rang}]")


def _verifier_cles(table: Mapping[str, Any], connues: Sequence[str], prefixe: str) -> None:
    for cle in table:
        if cle not in connues:
            attendues = ", ".join(connues)
            _refuser(_chemin(prefixe, cle), f"clé inconnue ; attendu l'une de : {attendues}")


def _table(parent: Mapping[str, Any], cle: str, prefixe: str) -> Mapping[str, Any]:
    chemin = _chemin(prefixe, cle)
    if cle not in parent:
        _refuser(chemin, "section obligatoire absente")
    valeur = parent[cle]
    if not isinstance(valeur, Mapping):
        _refuser(chemin, f"une section est attendue, pas {type(valeur).__name__}")
    return valeur


def _table_optionnelle(parent: Mapping[str, Any], cle: str, prefixe: str) -> Mapping[str, Any]:
    if cle not in parent:
        return {}
    return _table(parent, cle, prefixe)


def _texte(table: Mapping[str, Any], cle: str, prefixe: str, *, defaut: str | None = None) -> str:
    chemin = _chemin(prefixe, cle)
    if cle not in table:
        if defaut is None:
            _refuser(chemin, "clé obligatoire absente")
        return defaut
    valeur = table[cle]
    if not isinstance(valeur, str):
        _refuser(chemin, f"un texte est attendu, pas {type(valeur).__name__}")
    if not valeur:
        _refuser(chemin, "un texte vide ne désigne rien")
    return valeur


def _entier(
    table: Mapping[str, Any],
    cle: str,
    prefixe: str,
    *,
    defaut: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    chemin = _chemin(prefixe, cle)
    if cle not in table:
        if defaut is None:
            _refuser(chemin, "clé obligatoire absente")
        return defaut
    valeur = table[cle]
    # `bool` est un `int` en Python : l'accepter ferait passer `true` pour 1.
    if not isinstance(valeur, int) or isinstance(valeur, bool):
        _refuser(chemin, f"un entier est attendu, pas {type(valeur).__name__}")
    if valeur < minimum:
        _refuser(chemin, f"{valeur} est inférieur au minimum {minimum}")
    if maximum is not None and valeur > maximum:
        _refuser(chemin, f"{valeur} dépasse le maximum {maximum}")
    return valeur


def _reel(
    table: Mapping[str, Any],
    cle: str,
    prefixe: str,
    *,
    defaut: float,
    minimum: float = 0.0,
) -> float:
    chemin = _chemin(prefixe, cle)
    if cle not in table:
        return defaut
    valeur = table[cle]
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)):
        _refuser(chemin, f"un nombre est attendu, pas {type(valeur).__name__}")
    if valeur < minimum:
        _refuser(chemin, f"{valeur} est inférieur au minimum {minimum}")
    return float(valeur)


def _liste_textes(table: Mapping[str, Any], cle: str, prefixe: str) -> tuple[str, ...]:
    chemin = _chemin(prefixe, cle)
    if cle not in table:
        _refuser(chemin, "clé obligatoire absente")
    valeur = table[cle]
    if not isinstance(valeur, list):
        _refuser(chemin, f"une liste est attendue, pas {type(valeur).__name__}")
    if not valeur:
        _refuser(chemin, "une liste vide ne restreint rien")
    for rang, element in enumerate(valeur):
        if not isinstance(element, str) or not element:
            _refuser(f"{chemin}[{rang}]", "un texte non vide est attendu")
    return tuple(valeur)


def _heure(table: Mapping[str, Any], cle: str, prefixe: str) -> time:
    texte = _texte(table, cle, prefixe)
    try:
        return time.fromisoformat(texte)
    except ValueError as erreur:
        _refuser(
            _chemin(prefixe, cle), f"« {texte} » n'est pas une heure au format HH:MM ({erreur})"
        )


def _liste_tables(parent: Mapping[str, Any], cle: str) -> list[Mapping[str, Any]]:
    if cle not in parent:
        return []
    valeur = parent[cle]
    if not isinstance(valeur, list):
        _refuser(cle, f"une suite de sections [[{cle}]] est attendue, pas {type(valeur).__name__}")
    for rang, element in enumerate(valeur):
        if not isinstance(element, Mapping):
            _refuser(f"{cle}[{rang}]", "une section est attendue")
    return list(valeur)


def _flux(brut: Mapping[str, Any]) -> ConfigurationFlux:
    table = _table(brut, "flux", "")
    _verifier_cles(
        table,
        ("adresse", "port", "format", "debit_kbps", "frequence_hz", "canaux"),
        "flux",
    )
    return ConfigurationFlux(
        adresse=_texte(table, "adresse", "flux"),
        port=_entier(table, "port", "flux", maximum=PORT_MAXIMUM),
        format=_texte(table, "format", "flux"),
        debit_kbps=_entier(table, "debit_kbps", "flux"),
        frequence_hz=_entier(table, "frequence_hz", "flux"),
        canaux=_entier(table, "canaux", "flux", maximum=2),
    )


def _tirage(brut: Mapping[str, Any]) -> ConfigurationTirage:
    table = _table(brut, "tirage", "")
    _verifier_cles(table, ("non_repetition_artistes", "votes"), "tirage")
    votes = _table_optionnelle(table, "votes", "tirage")
    _verifier_cles(
        votes,
        ("plancher", "plafond", "demi_vie_jours", "poids_croise"),
        "tirage.votes",
    )
    plancher = _reel(votes, "plancher", "tirage.votes", defaut=VOTES_PLANCHER_DEFAUT)
    plafond = _reel(votes, "plafond", "tirage.votes", defaut=VOTES_PLAFOND_DEFAUT)
    if plancher > plafond:
        _refuser("tirage.votes.plancher", f"{plancher} dépasse le plafond {plafond}")
    return ConfigurationTirage(
        non_repetition_artistes=_entier(
            table,
            "non_repetition_artistes",
            "tirage",
            defaut=NON_REPETITION_DEFAUT,
            minimum=0,
        ),
        votes=ConfigurationVotes(
            plancher=plancher,
            plafond=plafond,
            demi_vie_jours=_entier(
                votes, "demi_vie_jours", "tirage.votes", defaut=VOTES_DEMI_VIE_DEFAUT
            ),
            poids_croise=_reel(
                votes, "poids_croise", "tirage.votes", defaut=VOTES_POIDS_CROISE_DEFAUT
            ),
        ),
    )


def _plages(brut: Mapping[str, Any]) -> tuple[Plage, ...]:
    plages: list[Plage] = []
    for rang, table in enumerate(_liste_tables(brut, "plages")):
        prefixe = f"plages[{rang}]"
        _verifier_cles(table, ("debut", "fin", "genres"), prefixe)
        plages.append(
            Plage(
                debut=_heure(table, "debut", prefixe),
                fin=_heure(table, "fin", prefixe),
                genres=_liste_textes(table, "genres", prefixe),
            )
        )
    return tuple(plages)


def _jours(table: Mapping[str, Any], prefixe: str) -> tuple[str, ...]:
    """Les jours d'une déclaration : une liste, ou le raccourci « tous ».

    Le raccourci est dans SPECS.md §4.11 depuis l'origine, mais il n'était
    accepté nulle part : `jours = "tous"` faisait échouer le démarrage avec
    « une liste est attendue ». C'est la spécification qui avait raison.
    """
    chemin = _chemin(prefixe, "jours")
    valeur = table.get("jours")
    if isinstance(valeur, str):
        if valeur.lower() != TOUS_LES_JOURS:
            _refuser(
                chemin,
                f"« {valeur} » n'est pas reconnu ; attendu « {TOUS_LES_JOURS} » ou une liste",
            )
        return JOURS
    jours = _liste_textes(table, "jours", prefixe)
    for position, jour in enumerate(jours):
        if jour.lower() not in JOURS:
            _refuser(
                f"{prefixe}.jours[{position}]",
                f"« {jour} » n'est pas un jour ; attendu l'un de : {', '.join(JOURS)}",
            )
    return tuple(jour.lower() for jour in jours)


def _programmes(brut: Mapping[str, Any]) -> tuple[ProgrammeDeclare, ...]:
    """Les programmes déclarés. Le recouvrement n'est pas refusé.

    Contrairement aux émissions, deux programmes qui se recouvrent ne font pas
    échouer le démarrage : le premier déclaré l'emporte, comme pour les plages.
    SPECS.md ne réserve le refus qu'aux émissions, et l'étendre ici serait
    inventer une règle.
    """
    programmes: list[ProgrammeDeclare] = []
    for rang, table in enumerate(_liste_tables(brut, "programmes")):
        prefixe = f"programmes[{rang}]"
        _verifier_cles(table, ("nom", "playlist", "jours", "debut", "fin"), prefixe)
        programmes.append(
            ProgrammeDeclare(
                nom=_texte(table, "nom", prefixe),
                playlist=_texte(table, "playlist", prefixe),
                jours=_jours(table, prefixe),
                debut=_heure(table, "debut", prefixe),
                fin=_heure(table, "fin", prefixe),
            )
        )
    return tuple(programmes)


def _emissions(brut: Mapping[str, Any]) -> tuple[Emission, ...]:
    emissions: list[Emission] = []
    for rang, table in enumerate(_liste_tables(brut, "emissions")):
        prefixe = f"emissions[{rang}]"
        _verifier_cles(table, ("nom", "flux", "jours", "heure"), prefixe)
        emissions.append(
            Emission(
                nom=_texte(table, "nom", prefixe),
                flux=_texte(table, "flux", prefixe),
                jours=_jours(table, prefixe),
                heure=_heure(table, "heure", prefixe),
            )
        )
    _refuser_les_collisions(emissions)
    return tuple(emissions)


def _refuser_les_collisions(emissions: Sequence[Emission]) -> None:
    """Deux émissions au même créneau font échouer le démarrage, en les nommant.

    C'est exigé par SPECS.md §5 : la radio ne peut pas en diffuser deux à la
    fois, et choisir en silence laquelle sacrifier serait une décision prise
    sans personne.
    """
    occupes: dict[tuple[str, time], str] = {}
    for emission in emissions:
        for jour in emission.jours:
            creneau = (jour, emission.heure)
            precedente = occupes.get(creneau)
            if precedente is not None:
                _refuser(
                    "emissions",
                    f"« {precedente} » et « {emission.nom} » tombent toutes deux "
                    f"le {jour} à {emission.heure.isoformat('minutes')}",
                )
            occupes[creneau] = emission.nom


def _navidrome(brut: Mapping[str, Any]) -> ConfigurationNavidrome:
    table = _table_optionnelle(brut, "navidrome", "")
    _verifier_cles(
        table, ("taille_echantillon", "resultats_artiste", "delai_secondes"), "navidrome"
    )
    return ConfigurationNavidrome(
        taille_echantillon=_entier(
            table, "taille_echantillon", "navidrome", defaut=TAILLE_ECHANTILLON_DEFAUT
        ),
        resultats_artiste=_entier(
            table, "resultats_artiste", "navidrome", defaut=RESULTATS_ARTISTE_DEFAUT
        ),
        delai_secondes=_reel(
            table, "delai_secondes", "navidrome", defaut=DELAI_SECONDES_DEFAUT, minimum=0.1
        ),
    )


def valider(brut: Mapping[str, Any]) -> Configuration:
    """Transforme un TOML déjà analysé en configuration, ou refuse le démarrage.

    Le refus des secrets passe **avant** tout le reste : une clé `mot_de_passe`
    doit s'entendre dire qu'elle est un secret, pas qu'elle est inconnue.
    """
    refuser_les_secrets(brut)
    _verifier_cles(
        brut,
        (
            "flux",
            "tirage",
            "jingles",
            "plages",
            "etat",
            "emissions",
            "navidrome",
            "web",
            "podcast",
            "programmes",
        ),
        "",
    )
    jingles = _table(brut, "jingles", "")
    _verifier_cles(jingles, ("dossier",), "jingles")
    etat = _table(brut, "etat", "")
    _verifier_cles(etat, ("base", "delai_secondes"), "etat")
    web = _table_optionnelle(brut, "web", "")
    _verifier_cles(web, ("adresse", "port", "rafraichissement_secondes"), "web")
    podcast = _table_optionnelle(brut, "podcast", "")
    _verifier_cles(podcast, ("delai_secondes",), "podcast")
    return Configuration(
        flux=_flux(brut),
        tirage=_tirage(brut),
        jingles=ConfigurationJingles(dossier=_texte(jingles, "dossier", "jingles")),
        plages=_plages(brut),
        etat=ConfigurationEtat(
            base=_texte(etat, "base", "etat"),
            delai_secondes=_reel(etat, "delai_secondes", "etat", defaut=DELAI_ETAT_DEFAUT),
        ),
        emissions=_emissions(brut),
        programmes=_programmes(brut),
        navidrome=_navidrome(brut),
        web=ConfigurationWeb(
            adresse=_texte(web, "adresse", "web", defaut=ADRESSE_WEB_DEFAUT),
            port=_entier(web, "port", "web", defaut=PORT_WEB_DEFAUT, maximum=PORT_MAXIMUM),
            rafraichissement_secondes=_reel(
                web,
                "rafraichissement_secondes",
                "web",
                defaut=RAFRAICHISSEMENT_DEFAUT,
                minimum=0.5,
            ),
        ),
        podcast=ConfigurationPodcast(
            delai_secondes=_reel(podcast, "delai_secondes", "podcast", defaut=DELAI_PODCAST_DEFAUT),
        ),
    )
