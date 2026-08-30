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
    Configuration,
    ErreurConfiguration,
    IdentifiantsNavidrome,
    Reglages,
    valider,
)

journal = logging.getLogger(__name__)

_MARQUE_COMMENTAIRE = "#"
_PREFIXE_EXPORT = "export "


def lire_env(chemin: Path) -> dict[str, str]:
    """Lit un fichier `clé=valeur`, sans rien journaliser de ce qu'il contient.

    Un fichier absent n'est pas une erreur : les variables peuvent venir de
    l'environnement du processus. Une ligne mal formée en est une, et elle est
    signalée avec son numéro — c'est la seule façon de la retrouver sans ouvrir
    le fichier, ce qu'on évite justement de faire avec un fichier de secrets.
    """
    if not chemin.is_file():
        journal.debug("aucun fichier d'environnement à %s : les variables du processus feront foi", chemin)
        return {}
    valeurs: dict[str, str] = {}
    contenu = chemin.read_text(encoding="utf-8")
    for numero, ligne_brute in enumerate(contenu.splitlines(), start=1):
        ligne = ligne_brute.strip()
        if not ligne or ligne.startswith(_MARQUE_COMMENTAIRE):
            continue
        if ligne.startswith(_PREFIXE_EXPORT):
            ligne = ligne[len(_PREFIXE_EXPORT) :].strip()
        if "=" not in ligne:
            message = (
                f"{chemin} ligne {numero} : une ligne « CLÉ=valeur » est attendue "
                "(le contenu n'est pas répété ici, c'est un fichier de secrets)"
            )
            raise ErreurConfiguration(message)
        cle, _, valeur = ligne.partition("=")
        cle = cle.strip()
        if not cle:
            message = f"{chemin} ligne {numero} : nom de variable vide"
            raise ErreurConfiguration(message)
        valeurs[cle] = _sans_guillemets(valeur.strip())
    return valeurs


def _sans_guillemets(valeur: str) -> str:
    for guillemet in ('"', "'"):
        if len(valeur) >= 2 and valeur.startswith(guillemet) and valeur.endswith(guillemet):
            return valeur[1:-1]
    return valeur


def identifiants_depuis(variables: Mapping[str, str]) -> IdentifiantsNavidrome:
    """Extrait les trois identifiants, ou refuse le démarrage en nommant celui qui manque.

    Le message nomme la **variable**, jamais une valeur : dire ce qui manque
    n'oblige pas à dire ce qui est présent.
    """
    manquantes = [
        nom
        for nom in (VARIABLE_URL, VARIABLE_UTILISATEUR, VARIABLE_MOT_DE_PASSE)
        if not variables.get(nom)
    ]
    if manquantes:
        message = (
            f"identifiants Navidrome absents : {', '.join(manquantes)} — "
            "ces valeurs viennent du fichier .env, jamais du TOML (SPECS.md §6.1)"
        )
        raise ErreurConfiguration(message)
    return IdentifiantsNavidrome(
        url=variables[VARIABLE_URL].rstrip("/"),
        utilisateur=variables[VARIABLE_UTILISATEUR],
        mot_de_passe=variables[VARIABLE_MOT_DE_PASSE],
    )


def charger_toml(chemin: Path) -> Configuration:
    """Lit et valide le TOML. Un fichier absent ou mal formé empêche le démarrage."""
    if not chemin.is_file():
        message = f"configuration absente : {chemin} (voir webradio.exemple.toml)"
        raise ErreurConfiguration(message)
    try:
        brut = tomllib.loads(chemin.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as erreur:
        message = f"{chemin} n'est pas un TOML valable : {erreur}"
        raise ErreurConfiguration(message) from erreur
    return valider(brut)


def charger(
    chemin_toml: Path,
    chemin_env: Path,
    environnement: Mapping[str, str] | None = None,
) -> Reglages:
    """Réunit les deux moitiés de la configuration : le TOML et les secrets.

    `environnement` est injecté pour que les tests n'aient pas à toucher aux
    variables du processus — les toucher rendrait deux tests dépendants de leur
    ordre d'exécution.
    """
    processus = os.environ if environnement is None else environnement
    variables = lire_env(chemin_env)
    variables.update({cle: valeur for cle, valeur in processus.items() if valeur})
    return Reglages(
        configuration=charger_toml(chemin_toml),
        identifiants=identifiants_depuis(variables),
    )
