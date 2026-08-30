"""Le point d'entrée.

Squelette de GOAL-001-T02 : il se lance, annonce ce qu'il est, et s'arrête. Il
existe pour que la chaîne de vérification ait un objet — sans lui, /verify
n'aurait rien à vérifier et le Harness serait invérifiable.

Il ne diffuse rien : la radio est construite par les Goals suivants.
"""

import logging
import sys

logger = logging.getLogger(__name__)

NOM = "local-webradio"


def version() -> str:
    """La version déclarée du paquet.

    Lue depuis les métadonnées d'installation plutôt que recopiée ici : deux
    endroits qui portent le même numéro finissent toujours par diverger.
    """
    from importlib.metadata import PackageNotFoundError, version as _version

    try:
        return _version("local-webradio")
    except PackageNotFoundError:
        return "0.0.0+source"


def main() -> int:
    """Démarre, annonce, s'arrête.

    Rend un code de sortie plutôt que d'appeler sys.exit : une fonction qui
    rend une valeur se teste, une fonction qui quitte le processus non.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logger.info("%s %s — squelette, aucune diffusion", NOM, version())
    return 0


if __name__ == "__main__":
    sys.exit(main())
