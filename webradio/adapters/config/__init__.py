"""La lecture de la configuration : le TOML, et les secrets du `.env`.

Ce dossier confine **la syntaxe TOML et le nom des clés** (ARCHITECTURE.md §2.1).
Au-dessus de lui, plus personne ne sait qu'un fichier de configuration existe :
le reste du programme ne manipule que les objets de `schema.py`.

La frontière entre les deux fichiers est nette (SPECS.md §6) : le `.env` ne porte
**que** des secrets, le TOML **aucun**. Un secret trouvé dans le TOML fait
échouer le démarrage en disant d'où il aurait dû venir — sans ce refus, la
séparation ne tiendrait pas une semaine.
"""

from webradio.adapters.config.loading import charger, identifiants_depuis, lire_env
from webradio.adapters.config.schema import (
    Configuration,
    ConfigurationEtat,
    ConfigurationFlux,
    ConfigurationJingles,
    ConfigurationNavidrome,
    ConfigurationTirage,
    ConfigurationVotes,
    Emission,
    ErreurConfiguration,
    IdentifiantsNavidrome,
    Plage,
    Reglages,
    valider,
)

__all__ = [
    "Configuration",
    "ConfigurationEtat",
    "ConfigurationFlux",
    "ConfigurationJingles",
    "ConfigurationNavidrome",
    "ConfigurationTirage",
    "ConfigurationVotes",
    "Emission",
    "ErreurConfiguration",
    "IdentifiantsNavidrome",
    "Plage",
    "Reglages",
    "charger",
    "identifiants_depuis",
    "lire_env",
    "valider",
]
