"""Lire les deux fichiers : le TOML, et le `.env` qui porte les secrets.

`tomllib` est dans la bibliothèque standard depuis Python 3.11, et le format du
`.env` — des lignes `CLÉ=valeur` — tient en vingt lignes : aucune dépendance
n'est justifiée ici, et une dépendance non justifiée est interdite
(AGENTS.md §2).

Les valeurs déjà présentes dans l'environnement du processus **priment** sur le
fichier : c'est ce qui permet de passer les identifiants à un conteneur sans y
copier de fichier (ARCHITECTURE.md §8.5.3).
"""

import logging
import os
import tomllib
from collections.abc import Mapping
from pathlib import Path

from webradio.adapters.config.schema import (
    VARIABLE_MOT_DE_PASSE,
    VARIABLE_URL,
    VARIABLE_UTILISATEUR,
    Config,
    NavidromeCredentials,
    Settings,
    SettingsError,
    validate,
)

journal = logging.getLogger(__name__)

_MARQUE_COMMENTAIRE = "#"
_PREFIXE_EXPORT = "export "


def read_env(path: Path) -> dict[str, str]:
    """Lit un fichier `clé=valeur`, sans rien journaliser de ce qu'il contient.

    Un fichier absent n'est pas une erreur : les variables peuvent venir de
    l'environnement du processus. Une ligne mal formée en est une, et elle est
    signalée avec son numéro — c'est la seule façon de la retrouver sans ouvrir
    le fichier, ce qu'on évite justement de faire avec un fichier de secrets.
    """
    if not path.is_file():
        journal.debug(
            "aucun fichier d'environnement à %s : les variables du processus feront foi", path
        )
        return {}
    values: dict[str, str] = {}
    content = path.read_text(encoding="utf-8")
    for numero, ligne_brute in enumerate(content.splitlines(), start=1):
        row = ligne_brute.strip()
        if not row or row.startswith(_MARQUE_COMMENTAIRE):
            continue
        if row.startswith(_PREFIXE_EXPORT):
            row = row[len(_PREFIXE_EXPORT) :].strip()
        if "=" not in row:
            message = (
                f"{path} ligne {numero} : une ligne « CLÉ=valeur » est attendue "
                "(le contenu n'est pas répété ici, c'est un fichier de secrets)"
            )
            raise SettingsError(message)
        key, _, value = row.partition("=")
        key = key.strip()
        if not key:
            message = f"{path} ligne {numero} : nom de variable vide"
            raise SettingsError(message)
        values[key] = _sans_guillemets(value.strip())
    return values


def _sans_guillemets(value: str) -> str:
    for guillemet in ('"', "'"):
        if len(value) >= 2 and value.startswith(guillemet) and value.endswith(guillemet):
            return value[1:-1]
    return value


def credentials_from(variables: Mapping[str, str]) -> NavidromeCredentials:
    """Extrait les trois identifiants, ou refuse le démarrage en nommant celui qui manque.

    Le message nomme la **variable**, jamais une valeur : dire ce qui manque
    n'oblige pas à dire ce qui est présent.
    """
    manquantes = [
        name
        for name in (VARIABLE_URL, VARIABLE_UTILISATEUR, VARIABLE_MOT_DE_PASSE)
        if not variables.get(name)
    ]
    if manquantes:
        message = (
            f"identifiants Navidrome absents : {', '.join(manquantes)} — "
            "ces valeurs viennent du fichier .env, jamais du TOML (SPECS.md §6.1)"
        )
        raise SettingsError(message)
    return NavidromeCredentials(
        url=variables[VARIABLE_URL].rstrip("/"),
        username=variables[VARIABLE_UTILISATEUR],
        password=variables[VARIABLE_MOT_DE_PASSE],
    )


def load_toml(path: Path) -> Settings:
    """Lit et valide le TOML. Un fichier absent ou mal formé empêche le démarrage."""
    if not path.is_file():
        message = f"configuration absente : {path} (voir webradio.exemple.toml)"
        raise SettingsError(message)
    try:
        brut = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        message = f"{path} n'est pas un TOML valable : {error}"
        raise SettingsError(message) from error
    return validate(brut)


def load(
    toml_path: Path,
    env_path: Path,
    environment: Mapping[str, str] | None = None,
) -> Config:
    """Réunit les deux moitiés de la configuration : le TOML et les secrets.

    `environnement` est injecté pour que les tests n'aient pas à toucher aux
    variables du processus — les toucher rendrait deux tests dépendants de leur
    ordre d'exécution.
    """
    processes = os.environ if environment is None else environment
    variables = read_env(env_path)
    variables.update({key: value for key, value in processes.items() if value})
    return Config(
        settings=load_toml(toml_path),
        credentials=credentials_from(variables),
    )
