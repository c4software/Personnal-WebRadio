"""Les routes que Liquidsoap appelle (ARCHITECTURE.md §4).

Liquidsoap encode, enchaîne et sert ; il ne décide de rien. À chaque jonction
il demande ici quoi jouer, à chaque branchement ou débranchement il dit combien
écoutent, et à chaque démarrage de morceau il dit ce qu'il joue. Comme pour
l'interface web, tout passe par une route, testée contre un Fake.

Le contrat est en texte brut, pas en JSON : c'est ce qu'un script `.liq` lit
sans effort.
"""

import logging
from typing import Protocol

from flask import Blueprint, request
from flask.typing import ResponseReturnValue

logger = logging.getLogger(__name__)

PLAYOUT_PATH = "/playout"
NEXT_PATH = "/next"
LISTENERS_PATH = "/listeners"
PLAYING_PATH = "/playing"

NOTHING_MORE = 204
BAD_REQUEST = 400


class Playout(Protocol):
    """Ce que Liquidsoap peut demander à la radio."""

    def next_entry(self) -> str | None:
        """Le chemin ou l'URL à jouer ensuite, ou `None` quand il n'y a plus rien.

        `None` signifie que la diffusion s'arrête, pas qu'il faut réessayer
        (SPECS.md §5.1).
        """
        ...

    def declare_listeners(self, count: int) -> None:
        """Le nombre d'auditeurs, d'après celui qui tient les connexions."""
        ...

    def playing(self, entry: str, artist: str | None, title: str | None) -> None:
        """Ce que Liquidsoap vient de commencer, pas ce qu'il a demandé.

        Un morceau est toujours demandé d'avance (docs/liquidsoap.md §3) : ce
        qui est à l'antenne se constate ici, pas dans `next_entry`. `artist`
        et `title` sont les étiquettes lues par le décodeur, utiles quand
        l'entrée n'est pas reconnue, après un redémarrage.
        """
        ...


def create_playout_api(playout: Playout) -> Blueprint:
    """Les routes de Liquidsoap, montées sous `/playout`."""
    api = Blueprint("playout", __name__, url_prefix=PLAYOUT_PATH)

    @api.post(NEXT_PATH)
    def next_entry() -> ResponseReturnValue:
        """Le morceau suivant, en texte brut. 204 quand il n'y en a plus."""
        entry = playout.next_entry()
        if entry is None:
            logger.warning("plus rien à jouer : la diffusion doit s'arrêter")
            return "", NOTHING_MORE
        return entry, {"Content-Type": "text/plain; charset=utf-8"}

    @api.post(LISTENERS_PATH)
    def listeners() -> ResponseReturnValue:
        """Le nombre d'auditeurs, en entier décimal dans le corps."""
        body = request.get_data(as_text=True).strip()
        if not body.isdigit():
            reason = f"nombre d'auditeurs invalide : « {body} »"
            logger.info("annonce refusée — %s", reason)
            return reason, BAD_REQUEST
        playout.declare_listeners(int(body))
        return "", NOTHING_MORE

    @api.post(PLAYING_PATH)
    def playing() -> ResponseReturnValue:
        """Le morceau que Liquidsoap commence : l'entrée reçue de `/next`, puis
        l'artiste et le titre lus du fichier, une ligne chacun."""
        lines = request.get_data(as_text=True).splitlines()
        entry = lines[0].strip() if lines else ""
        if not entry:
            return "entrée vide", BAD_REQUEST
        artist = lines[1].strip() if len(lines) > 1 else ""
        title = lines[2].strip() if len(lines) > 2 else ""
        playout.playing(entry, artist or None, title or None)
        return "", NOTHING_MORE

    return api
