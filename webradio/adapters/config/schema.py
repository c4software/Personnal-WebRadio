"""Le schéma de configuration et sa validation au démarrage.

Deux règles (SPECS.md §6.2) :

1. Une configuration invalide empêche le démarrage et nomme la clé fautive.
   Démarrer en ignorant une partie de la configuration diffuserait autre chose
   que ce qui a été demandé, sans que personne le voie.
2. Un secret trouvé dans le TOML est une erreur. Le refus nomme la variable
   d'environnement d'où la valeur aurait dû venir.

Une clé inconnue est refusée aussi : une clé mal orthographiée et ignorée
tomberait sous la règle 1.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import time
from typing import Any, NoReturn

# Les valeurs acceptées par `random` et `mode` viennent du noyau, pour ne pas
# tenir deux listes d'accord.
from webradio.core.bands import RANDOM_THEMES
from webradio.core.runs import Mode

MODES = tuple(m.value for m in Mode)

# Les noms des trois variables du `.env`, pour dire d'où un secret aurait dû
# venir. Leurs valeurs ne sont jamais lues ici.
VARIABLE_URL = "SUBSONIC_URL"
VARIABLE_UTILISATEUR = "SUBSONIC_UTILISATEUR"
VARIABLE_MOT_DE_PASSE = "SUBSONIC_MOT_DE_PASSE"

# Fragment de nom de clé qui désigne un secret, et la variable d'environnement
# attendue (vide si aucune). Le contrôle porte sur le nom de la clé, jamais sur
# la valeur : une valeur qui ressemble à un mot de passe n'est pas un critère.
FORBIDDEN_SECRET_KEYS: Mapping[str, str] = {
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

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
# SPECS.md §4.11 autorise `jours = "all"` comme raccourci des sept jours.
EVERY_DAY = "all"

# Les défauts sont déclarés ici, avec la clé qu'ils concernent, et nulle part
# ailleurs dans le code (AGENTS.md §2).
DEFAULT_ARTIST_GAP_KEY = 5
# Au-delà, la lecture est coupée au plafond (SPECS.md §7 n°32). 0 = sans limite.
DEFAULT_MAX_TRACK_MINUTES = 20
# Assez d'avance pour voir venir une demi-heure (GOAL-061). Chaque titre coûte
# un appel à la source, que le cache absorbe.
DEFAULT_LOOKAHEAD = 8
DEFAULT_VOTE_FLOOR = 0.25
DEFAULT_VOTE_CEILING = 4.0
DEFAULT_VOTE_HALF_LIFE = 90
DEFAULT_ARTIST_RESULTS = 50
DEFAULT_TIMEOUT_SECONDS = 10.0
# Un ajout dans la bibliothèque apparaît au plus tard une heure après, sans
# refaire le parcours complet à chaque tirage (GOAL-040).
DEFAULT_CACHE_SECONDS = 3600.0
# Distance à l'heure pleine au-delà de laquelle un jingle horaire est abandonné
# (SPECS.md §7 n°29). 0 = jamais périmé.
DEFAULT_JINGLE_EXPIRY_SECONDS = 900.0
# Pause sans auditeur au-delà de laquelle le retour jette l'avance et repart
# sur un tirage neuf (SPECS.md §7 n°30). 0 = jamais.
DEFAULT_RESUME_FRESH_SECONDS = 900.0

MAX_PORT = 65535

# Attente maximale d'un verrou SQLite : la chaîne et le serveur web écrivent
# dans la même base (ARCHITECTURE.md §5.1).
DEFAULT_STATE_TIMEOUT = 5.0
# Court : un flux de podcast qui ne répond pas fait perdre l'émission, la
# musique continue (SPECS.md §4.11).
DEFAULT_PODCAST_TIMEOUT = 15.0
# Toutes les interfaces : la radio est jointe depuis le réseau local et n'est
# jamais exposée sur Internet (SPECS.md §3).
DEFAULT_WEB_ADDRESS = "0.0.0.0"
# Le serveur web est distinct de celui du flux ; ils ne peuvent pas partager
# le port (GOAL-011-T04).
DEFAULT_WEB_PORT = 8080
# Intervalle auquel la page redemande ce qui passe. Trop court, elle interroge
# pour rien ; trop long, un « encore » semble sans effet.
DEFAULT_REFRESH = 5.0


class SettingsError(Exception):
    """Configuration invalide : le démarrage est refusé et la clé fautive nommée.

    Levée avant toute diffusion ; au démarrage, une erreur est fatale
    (SPECS.md §5).
    """


@dataclass(frozen=True, slots=True)
class VoteSettings:
    """La pondération d'un morceau par les votes (SPECS.md §4.12)."""

    floor: float
    ceiling: float
    half_life_days: int


@dataclass(frozen=True, slots=True)
class DrawSettings:
    """Ce que le tirage doit respecter."""

    artist_gap: int
    votes: VoteSettings
    max_track_minutes: int = DEFAULT_MAX_TRACK_MINUTES
    lookahead: int = DEFAULT_LOOKAHEAD


@dataclass(frozen=True, slots=True)
class JingleSettings:
    """Le dossier des jingles, le nom du jingle d'« encore » (GOAL-031), la péremption.

    Les jingles horaires ne se configurent pas : ils sont nommés par leur
    heure. `expiry_seconds` est la distance à l'heure pleine au-delà de
    laquelle un jingle horaire est abandonné (SPECS.md §7 n°29) ; `0` = jamais.
    """

    folder: str
    encore: str = "encore.mp3"
    expiry_seconds: float = DEFAULT_JINGLE_EXPIRY_SECONDS


@dataclass(frozen=True, slots=True)
class Band:
    """Une plage horaire thématique.

    Le thème est `genres`, `artists` ou `random_theme` (un genre ou un artiste
    tiré dans la bibliothèque, GOAL-037), un seul des trois. `days` restreint
    la plage à certains jours ; par défaut tous les jours (GOAL-019). `mode`
    enchaîne les tirages (SPECS.md §7 n°31) ; il se combine au thème ou se
    déclare seul. `eras` borne les décennies où la plage tire (GOAL-071) ;
    vide, elle tire dans toutes.
    """

    start: time
    end: time
    genres: tuple[str, ...] = ()
    artists: tuple[str, ...] = ()
    random_theme: str | None = None
    days: tuple[str, ...] = DAYS
    intro: str | None = None
    outro: str | None = None
    mode: str | None = None
    eras: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class PlayoutSettings:
    """La reprise après une pause sans auditeur (SPECS.md §4.7).

    Au-delà de `resume_fresh_seconds` de pause, le retour jette l'avance et
    repart sur un tirage neuf ; `0` = jamais.
    """

    resume_fresh_seconds: float = DEFAULT_RESUME_FRESH_SECONDS


@dataclass(frozen=True, slots=True)
class StateSettings:
    """La base d'état (ARCHITECTURE.md §5).

    `timeout_seconds` est l'attente maximale d'un verrou : la chaîne et le
    serveur web écrivent dans la même base (ARCHITECTURE.md §5.1).
    """

    database: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class WebSettings:
    """L'interface et l'API.

    `refresh_seconds` est l'intervalle auquel le flux d'événements regarde si
    l'antenne a changé (voir `DEFAULT_REFRESH`). La page ne sonde plus : elle
    s'abonne, et le serveur pousse (GOAL-073).
    """

    address: str
    port: int
    refresh_seconds: float
    # L'adresse du flux pour le lecteur de la page (GOAL-060). Vide : pas de
    # lecteur. Une valeur comme `:8000/flux` désigne l'hôte de la page.
    stream_url: str = ""


@dataclass(frozen=True, slots=True)
class YoutubeSettings:
    """Le délai accordé à `yt-dlp`, qui peut être lent."""

    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class PodcastSettings:
    """Le délai au-delà duquel un flux de podcast est réputé injoignable.

    Il reste court : une émission qui ne répond pas est perdue et la musique
    continue (SPECS.md §4.11).
    """

    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class DeclaredProgramme:
    """Une plage horaire où la musique vient d'une liste de lecture.

    À la différence d'une `Band`, la source est une liste de lecture, pas un
    genre (SPECS.md §4.13).
    """

    name: str
    playlist: str
    days: tuple[str, ...]
    start: time
    end: time
    intro: str | None = None
    outro: str | None = None


@dataclass(frozen=True, slots=True)
class Show:
    """Une émission diffusée à jours et heure fixes (SPECS.md §4.11).

    Exactement une source : `feed` (podcast), `youtube` (chaîne) ou `stream`
    (direct). Un direct exige `duration_minutes`, puisqu'il faut le couper ;
    les autres sources l'interdisent.
    """

    name: str
    days: tuple[str, ...]
    hour: time
    feed: str | None = None
    stream: str | None = None
    youtube: str | None = None
    duration_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class SubsonicSettings:
    """Les réglages de la source Subsonic, hors identifiants.

    Pas de taille d'échantillon : la bibliothèque se parcourt entière par
    pagination, et la taille de page est une propriété du serveur
    (docs/subsonic.md §2.7).

    `cache_seconds` est la durée pendant laquelle un parcours est servi de
    mémoire ; `0` refait les appels à chaque tirage. De la musique ajoutée sur
    le serveur n'apparaît qu'à l'expiration du cache.
    """

    artist_results: int
    timeout_seconds: float
    cache_seconds: float


@dataclass(frozen=True, slots=True)
class Settings:
    """La configuration validée du TOML. Aucun secret n'y figure."""

    draw: DrawSettings
    jingles: JingleSettings
    bands: tuple[Band, ...]
    state: StateSettings
    shows: tuple[Show, ...]
    programmes: tuple[DeclaredProgramme, ...]
    subsonic: SubsonicSettings
    web: WebSettings
    podcast: PodcastSettings
    youtube: YoutubeSettings
    playout: PlayoutSettings


@dataclass(frozen=True, slots=True, repr=False)
class SubsonicCredentials:
    """Les identifiants Subsonic, lus dans le `.env` uniquement.

    Le `repr` masque le mot de passe pour qu'un passage par mégarde dans un
    journal ne le divulgue pas (AGENTS.md §2).
    """

    url: str
    username: str
    password: str

    def __repr__(self) -> str:
        return (
            f"SubsonicCredentials(url={self.url!r}, "
            f"utilisateur={self.username!r}, mot_de_passe=***)"
        )


@dataclass(frozen=True, slots=True)
class Config:
    """Les réglages du TOML et les identifiants du `.env`, réunis pour l'assemblage."""

    settings: Settings
    credentials: SubsonicCredentials


def _refuser(path: str, reason: str) -> NoReturn:
    message = f"configuration invalide — clé « {path} » : {reason}"
    raise SettingsError(message)


def _chemin(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def reject_secrets(brut: Mapping[str, Any], prefix: str = "") -> None:
    """Lève `SettingsError` pour toute clé dont le nom désigne un secret, à toute profondeur.

    Le contrôle porte sur le nom de la clé, pas sur la valeur (voir
    `FORBIDDEN_SECRET_KEYS`).
    """
    for key, value in brut.items():
        path = _chemin(prefix, key)
        minuscule = key.lower()
        for fragment, origine in FORBIDDEN_SECRET_KEYS.items():
            if fragment in minuscule:
                ou = f"« {origine} » dans le fichier .env" if origine else "le fichier .env"
                _refuser(path, f"c'est un secret, sa valeur doit venir de {ou} (SPECS.md §6.1)")
        if isinstance(value, Mapping):
            reject_secrets(value, path)
        elif isinstance(value, list):
            for index, element in enumerate(value):
                if isinstance(element, Mapping):
                    reject_secrets(element, f"{path}[{index}]")


def _verifier_cles(table: Mapping[str, Any], connues: Sequence[str], prefix: str) -> None:
    for key in table:
        if key not in connues:
            attendues = ", ".join(connues)
            _refuser(_chemin(prefix, key), f"clé inconnue ; attendu l'une de : {attendues}")


def _table(parent: Mapping[str, Any], key: str, prefix: str) -> Mapping[str, Any]:
    path = _chemin(prefix, key)
    if key not in parent:
        _refuser(path, "section obligatoire absente")
    value = parent[key]
    if not isinstance(value, Mapping):
        _refuser(path, f"une section est attendue, pas {type(value).__name__}")
    return value


def _table_optionnelle(parent: Mapping[str, Any], key: str, prefix: str) -> Mapping[str, Any]:
    if key not in parent:
        return {}
    return _table(parent, key, prefix)


def _texte(table: Mapping[str, Any], key: str, prefix: str, *, default: str | None = None) -> str:
    path = _chemin(prefix, key)
    if key not in table:
        if default is None:
            _refuser(path, "clé obligatoire absente")
        return default
    value = table[key]
    if not isinstance(value, str):
        _refuser(path, f"un texte est attendu, pas {type(value).__name__}")
    if not value:
        _refuser(path, "un texte vide ne désigne rien")
    return value


def _entier(
    table: Mapping[str, Any],
    key: str,
    prefix: str,
    *,
    default: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
) -> int:
    path = _chemin(prefix, key)
    if key not in table:
        if default is None:
            _refuser(path, "clé obligatoire absente")
        return default
    value = table[key]
    # `bool` est un sous-type de `int` : sans ce test, `true` passerait pour 1.
    if not isinstance(value, int) or isinstance(value, bool):
        _refuser(path, f"un entier est attendu, pas {type(value).__name__}")
    if value < minimum:
        _refuser(path, f"{value} est inférieur au minimum {minimum}")
    if maximum is not None and value > maximum:
        _refuser(path, f"{value} dépasse le maximum {maximum}")
    return value


def _reel(
    table: Mapping[str, Any],
    key: str,
    prefix: str,
    *,
    default: float,
    minimum: float = 0.0,
) -> float:
    path = _chemin(prefix, key)
    if key not in table:
        return default
    value = table[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _refuser(path, f"un nombre est attendu, pas {type(value).__name__}")
    if value < minimum:
        _refuser(path, f"{value} est inférieur au minimum {minimum}")
    return float(value)


def _liste_textes(table: Mapping[str, Any], key: str, prefix: str) -> tuple[str, ...]:
    path = _chemin(prefix, key)
    if key not in table:
        _refuser(path, "clé obligatoire absente")
    value = table[key]
    if not isinstance(value, list):
        _refuser(path, f"une liste est attendue, pas {type(value).__name__}")
    if not value:
        _refuser(path, "une liste vide ne restreint rien")
    for index, element in enumerate(value):
        if not isinstance(element, str) or not element:
            _refuser(f"{path}[{index}]", "un texte non vide est attendu")
    return tuple(value)


def _heure(table: Mapping[str, Any], key: str, prefix: str) -> time:
    texte = _texte(table, key, prefix)
    try:
        return time.fromisoformat(texte)
    except ValueError as error:
        _refuser(_chemin(prefix, key), f"« {texte} » n'est pas une heure au format HH:MM ({error})")


def _liste_tables(parent: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    if key not in parent:
        return []
    value = parent[key]
    if not isinstance(value, list):
        _refuser(key, f"une suite de sections [[{key}]] est attendue, pas {type(value).__name__}")
    for index, element in enumerate(value):
        if not isinstance(element, Mapping):
            _refuser(f"{key}[{index}]", "une section est attendue")
    return list(value)


def _tirage(brut: Mapping[str, Any]) -> DrawSettings:
    table = _table(brut, "draw", "")
    _verifier_cles(table, ("artist_gap", "votes", "max_track_minutes", "lookahead"), "draw")
    votes = _table_optionnelle(table, "votes", "draw")
    _verifier_cles(
        votes,
        ("floor", "ceiling", "half_life_days"),
        "draw.votes",
    )
    floor = _reel(votes, "floor", "draw.votes", default=DEFAULT_VOTE_FLOOR)
    ceiling = _reel(votes, "ceiling", "draw.votes", default=DEFAULT_VOTE_CEILING)
    if floor > ceiling:
        _refuser("draw.votes.floor", f"{floor} dépasse le plafond {ceiling}")
    return DrawSettings(
        artist_gap=_entier(
            table,
            "artist_gap",
            "draw",
            default=DEFAULT_ARTIST_GAP_KEY,
            minimum=0,
        ),
        max_track_minutes=_entier(
            table,
            "max_track_minutes",
            "draw",
            default=DEFAULT_MAX_TRACK_MINUTES,
            minimum=0,
        ),
        lookahead=_entier(table, "lookahead", "draw", default=DEFAULT_LOOKAHEAD, minimum=1),
        votes=VoteSettings(
            floor=floor,
            ceiling=ceiling,
            half_life_days=_entier(
                votes, "half_life_days", "draw.votes", default=DEFAULT_VOTE_HALF_LIFE
            ),
        ),
    )


def _plages(brut: Mapping[str, Any]) -> tuple[Band, ...]:
    bands: list[Band] = []
    for index, table in enumerate(_liste_tables(brut, "bands")):
        prefix = f"bands[{index}]"
        _verifier_cles(
            table,
            (
                "start",
                "end",
                "genres",
                "artists",
                "random",
                "days",
                "intro",
                "outro",
                "mode",
                "eras",
            ),
            prefix,
        )
        declarees = sum(cle in table for cle in ("genres", "artists", "random"))
        if declarees > 1 or (declarees == 0 and "mode" not in table):
            _refuser(
                prefix,
                "une plage déclare `genres`, `artists` OU `random` — exactement une des "
                "trois, sauf à porter un `mode` seul",
            )
        if "random" in table and table["random"] not in RANDOM_THEMES:
            _refuser(
                _chemin(prefix, "random"),
                f"attendu {' ou '.join(RANDOM_THEMES)}, pas {table['random']!r}",
            )
        if "mode" in table and table["mode"] not in MODES:
            _refuser(
                _chemin(prefix, "mode"),
                f"attendu {', '.join(MODES)}, pas {table['mode']!r}",
            )
        bands.append(
            Band(
                start=_heure(table, "start", prefix),
                end=_heure(table, "end", prefix),
                genres=_liste_textes(table, "genres", prefix) if "genres" in table else (),
                artists=_liste_textes(table, "artists", prefix) if "artists" in table else (),
                random_theme=_texte(table, "random", prefix) if "random" in table else None,
                # Sans `days`, la plage vaut tous les jours (GOAL-019).
                days=_jours(table, prefix) if "days" in table else DAYS,
                intro=_texte(table, "intro", prefix) if "intro" in table else None,
                outro=_texte(table, "outro", prefix) if "outro" in table else None,
                mode=_texte(table, "mode", prefix) if "mode" in table else None,
                eras=_liste_decennies(table, "eras", prefix) if "eras" in table else (),
            )
        )
    return tuple(bands)


def _liste_decennies(table: Mapping[str, Any], key: str, prefix: str) -> tuple[int, ...]:
    """Les décennies d'une plage : des entiers multiples de dix (GOAL-071)."""
    path = _chemin(prefix, key)
    value = table[key]
    if not isinstance(value, list):
        _refuser(path, f"une liste est attendue, pas {type(value).__name__}")
    if not value:
        _refuser(path, "une liste vide ne restreint rien")
    for index, element in enumerate(value):
        if not isinstance(element, int) or isinstance(element, bool):
            _refuser(f"{path}[{index}]", "une décennie est un entier, comme 1990")
        if element <= 0 or element % 10:
            _refuser(f"{path}[{index}]", f"décennie attendue, multiple de dix : {element}")
    return tuple(value)


def _jours(table: Mapping[str, Any], prefix: str) -> tuple[str, ...]:
    """Les jours d'une déclaration : une liste de noms, ou le raccourci `"all"`.

    Les noms sont rendus en minuscules. Le raccourci vient de SPECS.md §4.11.
    """
    path = _chemin(prefix, "days")
    value = table.get("days")
    if isinstance(value, str):
        if value.lower() != EVERY_DAY:
            _refuser(
                path,
                f"« {value} » n'est pas reconnu ; attendu « {EVERY_DAY} » ou une liste",
            )
        return DAYS
    days = _liste_textes(table, "days", prefix)
    for position, jour in enumerate(days):
        if jour.lower() not in DAYS:
            _refuser(
                f"{prefix}.days[{position}]",
                f"« {jour} » n'est pas un jour ; attendu l'un de : {', '.join(DAYS)}",
            )
    return tuple(jour.lower() for jour in days)


def _programmes(brut: Mapping[str, Any]) -> tuple[DeclaredProgramme, ...]:
    """Les programmes déclarés.

    Deux programmes qui se recouvrent ne sont pas refusés : le plus court
    l'emporte, comme pour les plages. SPECS.md ne réserve le refus des
    collisions qu'aux émissions.
    """
    programmes: list[DeclaredProgramme] = []
    for index, table in enumerate(_liste_tables(brut, "programmes")):
        prefix = f"programmes[{index}]"
        _verifier_cles(
            table, ("name", "playlist", "days", "start", "end", "intro", "outro"), prefix
        )
        programmes.append(
            DeclaredProgramme(
                name=_texte(table, "name", prefix),
                playlist=_texte(table, "playlist", prefix),
                days=_jours(table, prefix),
                intro=_texte(table, "intro", prefix) if "intro" in table else None,
                outro=_texte(table, "outro", prefix) if "outro" in table else None,
                start=_heure(table, "start", prefix),
                end=_heure(table, "end", prefix),
            )
        )
    return tuple(programmes)


def _emissions(brut: Mapping[str, Any]) -> tuple[Show, ...]:
    shows: list[Show] = []
    for index, table in enumerate(_liste_tables(brut, "shows")):
        prefix = f"shows[{index}]"
        _verifier_cles(
            table,
            ("name", "feed", "stream", "youtube", "duration_minutes", "days", "time"),
            prefix,
        )
        name = _texte(table, "name", prefix)
        sources = [key for key in ("feed", "stream", "youtube") if key in table]
        if len(sources) != 1:
            _refuser(
                prefix,
                f"« {name} » doit avoir exactement une source : "
                "`feed` (podcast), `stream` (direct) ou `youtube` (chaîne)",
            )
        if "stream" in table and "duration_minutes" not in table:
            _refuser(
                prefix,
                f"« {name} » est un direct : `duration_minutes` est obligatoire",
            )
        if "stream" not in table and "duration_minutes" in table:
            _refuser(prefix, f"« {name} » : sa durée se lit à la source, pas ici")
        shows.append(
            Show(
                name=name,
                days=_jours(table, prefix),
                hour=_heure(table, "time", prefix),
                feed=_texte(table, "feed", prefix) if "feed" in table else None,
                stream=_texte(table, "stream", prefix) if "stream" in table else None,
                youtube=_texte(table, "youtube", prefix) if "youtube" in table else None,
                duration_minutes=(
                    _entier(table, "duration_minutes", prefix, maximum=24 * 60)
                    if "duration_minutes" in table
                    else None
                ),
            )
        )
    _refuser_les_collisions(shows)
    return tuple(shows)


def _refuser_les_collisions(shows: Sequence[Show]) -> None:
    """Refuse deux émissions au même jour et à la même heure, en les nommant.

    La radio ne peut pas en diffuser deux à la fois et ne choisit pas à la
    place de l'auteur (SPECS.md §5).
    """
    occupes: dict[tuple[str, time], str] = {}
    for show in shows:
        for jour in show.days:
            creneau = (jour, show.hour)
            precedente = occupes.get(creneau)
            if precedente is not None:
                _refuser(
                    "shows",
                    f"« {precedente} » et « {show.name} » tombent toutes deux "
                    f"le {jour} à {show.hour.isoformat('minutes')}",
                )
            occupes[creneau] = show.name


def _subsonic(brut: Mapping[str, Any]) -> SubsonicSettings:
    table = _table_optionnelle(brut, "subsonic", "")
    _verifier_cles(table, ("artist_results", "timeout_seconds", "cache_seconds"), "subsonic")
    return SubsonicSettings(
        artist_results=_entier(table, "artist_results", "subsonic", default=DEFAULT_ARTIST_RESULTS),
        timeout_seconds=_reel(
            table, "timeout_seconds", "subsonic", default=DEFAULT_TIMEOUT_SECONDS, minimum=0.1
        ),
        cache_seconds=_reel(table, "cache_seconds", "subsonic", default=DEFAULT_CACHE_SECONDS),
    )


def validate(brut: Mapping[str, Any]) -> Settings:
    """Transforme un TOML déjà analysé en `Settings`, ou lève `SettingsError`.

    Les secrets sont contrôlés avant les clés inconnues : une clé
    `mot_de_passe` doit être signalée comme un secret, pas comme inconnue.
    """
    reject_secrets(brut)
    _verifier_cles(
        brut,
        (
            "draw",
            "jingles",
            "bands",
            "state",
            "shows",
            "subsonic",
            "web",
            "podcast",
            "youtube",
            "programmes",
            "playout",
        ),
        "",
    )
    jingles = _table(brut, "jingles", "")
    _verifier_cles(jingles, ("folder", "encore", "expiry_seconds"), "jingles")
    state = _table(brut, "state", "")
    _verifier_cles(state, ("database", "timeout_seconds"), "state")
    web = _table_optionnelle(brut, "web", "")
    _verifier_cles(web, ("address", "port", "refresh_seconds", "stream_url"), "web")
    podcast = _table_optionnelle(brut, "podcast", "")
    _verifier_cles(podcast, ("timeout_seconds",), "podcast")
    playout = _table_optionnelle(brut, "playout", "")
    _verifier_cles(playout, ("resume_fresh_seconds",), "playout")
    return Settings(
        draw=_tirage(brut),
        jingles=JingleSettings(
            folder=_texte(jingles, "folder", "jingles"),
            encore=_texte(jingles, "encore", "jingles", default="encore.mp3"),
            expiry_seconds=_reel(
                jingles, "expiry_seconds", "jingles", default=DEFAULT_JINGLE_EXPIRY_SECONDS
            ),
        ),
        bands=_plages(brut),
        state=StateSettings(
            database=_texte(state, "database", "state"),
            timeout_seconds=_reel(state, "timeout_seconds", "state", default=DEFAULT_STATE_TIMEOUT),
        ),
        shows=_emissions(brut),
        programmes=_programmes(brut),
        subsonic=_subsonic(brut),
        web=WebSettings(
            address=_texte(web, "address", "web", default=DEFAULT_WEB_ADDRESS),
            port=_entier(web, "port", "web", default=DEFAULT_WEB_PORT, maximum=MAX_PORT),
            refresh_seconds=_reel(
                web,
                "refresh_seconds",
                "web",
                default=DEFAULT_REFRESH,
                minimum=0.5,
            ),
            stream_url=_texte(web, "stream_url", "web", default=""),
        ),
        youtube=YoutubeSettings(
            timeout_seconds=_reel(
                _table_optionnelle(brut, "youtube", ""),
                "timeout_seconds",
                "youtube",
                default=60.0,
            )
        ),
        podcast=PodcastSettings(
            timeout_seconds=_reel(
                podcast, "timeout_seconds", "podcast", default=DEFAULT_PODCAST_TIMEOUT
            ),
        ),
        playout=PlayoutSettings(
            resume_fresh_seconds=_reel(
                playout, "resume_fresh_seconds", "playout", default=DEFAULT_RESUME_FRESH_SECONDS
            ),
        ),
    )
