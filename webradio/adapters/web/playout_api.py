"""Les deux routes que Liquidsoap appelle, et rien d'autre (ARCHITECTURE.md §4).

Liquidsoap encode, enchaîne et sert ; il ne décide de rien. À chaque jonction
il demande ici **quoi jouer**, et à chaque branchement ou débranchement il dit
**combien écoutent**. C'est le même régime que l'interface web : aucun chemin
privilégié, tout passe par une route, et la route se teste contre un Fake.

Le contrat est volontairement pauvre — du texte brut, pas du JSON — parce que
c'est ce qu'un script `.liq` lit sans effort, et qu'un contrat riche serait une
décision prise ici.
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
    """Ce que Liquidsoap a le droit de demander à la radio."""

    def next_entry(self) -> str | None:
        """Le chemin ou l'URL à jouer ensuite, ou `None` : la radio n'a plus rien.

        `None` n'est pas « réessaie » mais « c'est fini » (SPECS.md §5.1) : le
        script qui le reçoit doit arrêter de servir, pas encoder du silence.
        """
        ...

    def declare_listeners(self, count: int) -> None:
        """Combien écoutent, d'après celui qui tient les connexions."""
        ...

    def playing(self, entry: str) -> None:
        """Ce que Liquidsoap vient de **commencer** — pas ce qu'il a demandé.

        Un morceau est toujours demandé d'avance (docs/liquidsoap.md §3) :
        « à l'antenne » ne se déduit pas de `next_entry`, il se constate ici.
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
        """Le nombre d'auditeurs, en texte brut dans le corps : `0`, `1`, `2`…"""
        body = request.get_data(as_text=True).strip()
        if not body.isdigit():
            reason = f"nombre d'auditeurs invalide : « {body} »"
            logger.info("annonce refusée — %s", reason)
            return reason, BAD_REQUEST
        playout.declare_listeners(int(body))
        return "", NOTHING_MORE

    @api.post(PLAYING_PATH)
    def playing() -> ResponseReturnValue:
        """Le morceau que Liquidsoap commence, tel qu'il l'a reçu de `/next`."""
        entry = request.get_data(as_text=True).strip()
        if not entry:
            return "entrée vide", BAD_REQUEST
        playout.playing(entry)
        return "", NOTHING_MORE

    return api
