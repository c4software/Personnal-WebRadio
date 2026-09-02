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

# Les valeurs acceptées par `random` et `mode` viennent du noyau : les
# recopier ici en ferait deux listes à tenir d'accord, et c'est la
# configuration qui mentirait la première.
from webradio.core.bands import RANDOM_THEMES
from webradio.core.runs import Mode

MODES = tuple(m.value for m in Mode)

# Les trois variables du `.env`. Elles ne portent aucune valeur ici : seulement
# leur nom, qui sert à dire d'où un secret aurait dû venir.
VARIABLE_URL = "SUBSONIC_URL"
VARIABLE_UTILISATEUR = "SUBSONIC_UTILISATEUR"
VARIABLE_MOT_DE_PASSE = "SUBSONIC_MOT_DE_PASSE"

# Un fragment de nom de clé qui trahit un secret, et l'origine attendue de sa
# valeur. La recherche porte sur le nom, jamais sur la valeur : une valeur qui
# « ressemble » à un mot de passe n'est pas un critère, un nom de clé l'est.
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

# Défauts déclarés au même endroit que la clé qu'ils concernent, faute de quoi
# ils seraient « en dur » quelque part dans le code (AGENTS.md §2).
DEFAULT_ARTIST_GAP_KEY = 5
# Au-delà, la lecture se coupe au plafond (SPECS.md §7 n°32). 0 = sans limite.
DEFAULT_MAX_TRACK_MINUTES = 20
# Huit titres d'avance : assez pour voir venir une demi-heure (GOAL-061).
# Chaque titre est tiré pour son heure, la grille ne change pas sous l'avance ;
# le coût est un appel à la source par titre, que le cache absorbe.
DEFAULT_LOOKAHEAD = 8
DEFAULT_VOTE_FLOOR = 0.25
DEFAULT_VOTE_CEILING = 4.0
DEFAULT_VOTE_HALF_LIFE = 90
DEFAULT_ARTIST_RESULTS = 50
DEFAULT_TIMEOUT_SECONDS = 10.0
# La bibliothèque bouge rarement ; une heure borne le retard d'apparition
# d'un ajout sans refaire le parcours complet à chaque tirage (GOAL-040).
DEFAULT_CACHE_SECONDS = 3600.0
# À plus d'un quart d'heure de son heure pleine, un jingle horaire sonne comme
# une horloge cassée : il est abandonné (SPECS.md §7 n°29). 0 = jamais périmé.
DEFAULT_JINGLE_EXPIRY_SECONDS = 900.0
# Au-delà de cette pause sans auditeur, l'avance du diffuseur a rassi : le
# retour repart sur un tirage neuf (SPECS.md §7 n°30). 0 = jamais.
DEFAULT_RESUME_FRESH_SECONDS = 900.0

MAX_PORT = 65535

# Le temps qu'une écriture accepte d'attendre un verrou SQLite. Deux processus
# touchent la base : la chaîne et le serveur web (ARCHITECTURE.md §5.1).
DEFAULT_STATE_TIMEOUT = 5.0
# Un flux de podcast qui ne répond pas ne bloque pas la radio : l'émission est
# perdue et la musique continue (SPECS.md §4.11). Le délai reste donc court.
DEFAULT_PODCAST_TIMEOUT = 15.0
# L'interface et l'API sont servies par un serveur DISTINCT de celui du flux :
# ce sont deux serveurs, et ils ne peuvent pas écouter le même port. Le
# commentaire précédent affirmait le contraire ; le premier démarrage en
# conteneur l'a démenti par un « Address already in use » (GOAL-011-T04).
# Écoute sur toutes les interfaces : la radio est faite pour être jointe depuis
# le réseau local, et elle n'est jamais exposée sur Internet (SPECS.md §3).
DEFAULT_WEB_ADDRESS = "0.0.0.0"
DEFAULT_WEB_PORT = 8080
# L'intervalle auquel la page redemande ce qui passe. Trop court, elle
# interroge pour rien ; trop long, un « encore » semble sans effet.
DEFAULT_REFRESH = 5.0


class SettingsError(Exception):
    """Le démarrage est refusé, et la clé fautive est nommée.

    Elle est levée avant que quoi que ce soit ne soit diffusé : c'est le régime
    « au démarrage, une erreur est fatale et se dit » (SPECS.md §5).
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
    """Le dossier, le nom du jingle d'« encore » (GOAL-031), la péremption.

    Les jingles HORAIRES restent nommés par leur heure — c'est leur
    programmation, pas un réglage. `expiry_seconds` est la distance à l'heure
    pleine au-delà de laquelle un jingle horaire est abandonné (SPECS.md §7
    n°29) ; `0` = jamais.
    """

    folder: str
    encore: str = "encore.mp3"
    expiry_seconds: float = DEFAULT_JINGLE_EXPIRY_SECONDS


@dataclass(frozen=True, slots=True)
class Band:
    """Un moment thématique : des genres, entre deux heures.

    `days` restreint la plage à certains jours ; sans elle, tous les jours —
    le comportement historique (GOAL-019).

    `random_theme` remplace les deux premiers : la plage ne dit plus *quoi*,
    elle dit *quelle sorte* — « un genre » ou « un artiste » —, et la radio
    tire dans la bibliothèque (GOAL-037).

    `mode` demande que les tirages s'enchaînent (SPECS.md §7 n°31) : il se
    combine au thème, ou se déclare seul — un tirage libre enchaîné.
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


@dataclass(frozen=True, slots=True)
class PlayoutSettings:
    """La reprise après une pause sans auditeur (SPECS.md §4.7).

    `resume_fresh_seconds` : au-delà de cette pause, le retour d'un auditeur
    jette l'avance et repart sur un tirage neuf ; `0` = jamais.
    """

    resume_fresh_seconds: float = DEFAULT_RESUME_FRESH_SECONDS


@dataclass(frozen=True, slots=True)
class StateSettings:
    """La base qui retient le dernier épisode diffusé et les votes.

    `delai_secondes` est le temps qu'une écriture accepte d'attendre un verrou :
    deux processus vivants touchent cette base — la chaîne de diffusion et le
    serveur web (ARCHITECTURE.md §5.1).
    """

    database: str
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class WebSettings:
    """L'interface et l'API.

    `rafraichissement_secondes` est l'intervalle auquel la page redemande à
    l'API ce qui passe. Trop court, elle interroge pour rien ; trop long, un
    « encore » semble sans effet.
    """

    address: str
    port: int
    refresh_seconds: float
    # L'adresse du flux, pour le lecteur de la page (GOAL-060). Vide : pas de
    # lecteur. `:8000/flux` désigne l'hôte de la page.
    stream_url: str = ""


@dataclass(frozen=True, slots=True)
class YoutubeSettings:
    """`yt-dlp` peut être lent : son délai se déclare, comme tout délai."""

    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class PodcastSettings:
    """Le délai au-delà duquel un flux de podcast est réputé injoignable.

    Il doit rester court : une émission qui ne répond pas ne bloque pas la
    radio, elle est perdue et la musique continue (SPECS.md §4.11).
    """

    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class DeclaredProgramme:
    """Une plage de temps où la musique vient d'une liste de lecture.

    Elle porte des **jours** en plus des heures, et sa source est une liste
    choisie plutôt qu'un genre — c'est ce qui la distingue d'une `Plage`
    (SPECS.md §4.13).
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
    """Un podcast — ou un direct — diffusé à jour et heure dits.

    Soit `feed` (un podcast, dont l'épisode se termine de lui-même), soit
    `stream` **et** `duration_minutes` (un direct, qu'il faut couper). Jamais les
    deux, jamais ni l'un ni l'autre (SPECS.md §4.11).
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
    """Ce que la source Subsonic a besoin de savoir, hors identifiants.

    Aucune taille d'échantillon : la bibliothèque se parcourt entière, par
    pagination, et la taille de page est une propriété constatée du serveur,
    pas un réglage (docs/subsonic.md §2.7).

    `cache_seconds` est la durée pendant laquelle un parcours reste servi de
    mémoire ; `0` refait les appels à chaque tirage. Le prix du cache est
    assumé : de la musique ajoutée sur le serveur n'apparaît qu'à l'expiration.
    """

    artist_results: int
    timeout_seconds: float
    cache_seconds: float


@dataclass(frozen=True, slots=True)
class Settings:
    """Tout ce que le TOML décrit, une fois validé. Aucun secret n'y figure."""

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
    """Les trois valeurs qui viennent du `.env`, et d'aucun autre endroit.

    La représentation masque le mot de passe : un objet passé par mégarde à un
    appel de journalisation ne doit pas suffire à le divulguer (AGENTS.md §2).
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
    """Les deux moitiés de la configuration, réunies pour l'assemblage."""

    settings: Settings
    credentials: SubsonicCredentials


def _refuser(path: str, reason: str) -> NoReturn:
    message = f"configuration invalide — clé « {path} » : {reason}"
    raise SettingsError(message)


def _chemin(prefix: str, key: str) -> str:
    return f"{prefix}.{key}" if prefix else key


def reject_secrets(brut: Mapping[str, Any], prefix: str = "") -> None:
    """Refuse toute clé dont le nom trahit un secret, à n'importe quelle profondeur.

    Le contrôle porte sur le nom de la clé et non sur sa valeur : une valeur qui
    ressemble à un mot de passe n'est pas un critère utilisable, alors qu'un nom
    l'est, et c'est le nom que l'auteur d'un TOML écrit en connaissance de cause.
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
    # `bool` est un `int` en Python : l'accepter ferait passer `true` pour 1.
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
            ("start", "end", "genres", "artists", "random", "days", "intro", "outro", "mode"),
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
                # Pas de `days` = tous les jours : le comportement historique.
                days=_jours(table, prefix) if "days" in table else DAYS,
                intro=_texte(table, "intro", prefix) if "intro" in table else None,
                outro=_texte(table, "outro", prefix) if "outro" in table else None,
                mode=_texte(table, "mode", prefix) if "mode" in table else None,
            )
        )
    return tuple(bands)


def _jours(table: Mapping[str, Any], prefix: str) -> tuple[str, ...]:
    """Les jours d'une déclaration : une liste, ou le raccourci « tous ».

    Le raccourci est dans SPECS.md §4.11 depuis l'origine, mais il n'était
    accepté nulle part : `jours = "all"` faisait échouer le démarrage avec
    « une liste est attendue ». C'est la spécification qui avait raison.
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
    """Les programmes déclarés. Le recouvrement n'est pas refusé.

    Contrairement aux émissions, deux programmes qui se recouvrent ne font pas
    échouer le démarrage : le premier déclaré l'emporte, comme pour les plages.
    SPECS.md ne réserve le refus qu'aux émissions, et l'étendre ici serait
    inventer une règle.
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
    """Deux émissions au même créneau font échouer le démarrage, en les nommant.

    C'est exigé par SPECS.md §5 : la radio ne peut pas en diffuser deux à la
    fois, et choisir en silence laquelle sacrifier serait une décision prise
    sans personne.
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
    """Transforme un TOML déjà analysé en configuration, ou refuse le démarrage.

    Le refus des secrets passe **avant** tout le reste : une clé `mot_de_passe`
    doit s'entendre dire qu'elle est un secret, pas qu'elle est inconnue.
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
