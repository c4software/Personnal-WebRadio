"""La surface publique : ce qui passe, et voter (SPECS.md §4.8).

**Toute action passe par ici.** L'interface web n'a aucun chemin privilégié :
ses boutons appellent cette API comme le ferait n'importe quel autre client. Ce
n'est pas une convention mais un interdit (AGENTS.md §2) — un second chemin
divergerait du premier, et c'est celui qu'on ne teste pas qui casse.

Aucun `render_template` ici : l'API rend des données, la vue les met en page.

**La frontière avec le noyau est le `Protocol` `Radio`.** Le noyau n'est pas
encore câblé ; l'API ne connaît de lui que ces trois questions, et se teste
contre un Fake. C'est aussi la ligne de partage des responsabilités
d'ARCHITECTURE.md §6.1 : **c'est le noyau qui refuse un vote**, parce que lui
seul sait s'il est dans un jingle, un flash ou une émission. L'API traduit ce
refus en réponse HTTP, elle ne le décide pas.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

logger = logging.getLogger(__name__)

CHEMIN_API = "/api"
CHEMIN_ANTENNE = "/antenne"
CHEMIN_VOTE = "/votes/<nom>"

REFUS = 409
DEMANDE_INVALIDE = 400


class Nature(StrEnum):
    """De quelle nature est ce qui passe (SPECS.md §4.8).

    L'auditeur doit pouvoir distinguer un morceau d'un habillage : c'est aussi
    ce qui rend un refus de vote compréhensible plutôt que surprenant.
    """

    MUSIQUE = "musique"
    JINGLE = "jingle"
    FLASH = "flash"
    EMISSION = "emission"


class Vote(StrEnum):
    """Les deux commandes de SPECS.md §4.6. « Vote » est un mot pour « bouton »."""

    STOP = "stop"
    ENCORE = "encore"


@dataclass(frozen=True, slots=True)
class Antenne:
    """Ce qui passe à cet instant.

    `titre` et `artiste` sont facultatifs : un jingle horaire ou un flash n'ont
    ni l'un ni l'autre, et inventer un libellé ici serait une décision prise
    dans un adaptateur.
    """

    nature: Nature
    titre: str | None = None
    artiste: str | None = None


@dataclass(frozen=True, slots=True)
class Verdict:
    """La réponse du noyau à un vote.

    `motif` est obligatoire quand le vote est refusé : un refus muet est
    indistinguable d'une panne et pousse à réessayer (ARCHITECTURE.md §6.1).
    """

    accepte: bool
    motif: str | None = None

    def __post_init__(self) -> None:
        if not self.accepte and not self.motif:
            message = "un refus sans motif est indistinguable d'une panne"
            raise ValueError(message)


class Radio(Protocol):
    """Ce que l'API attend de la radio, et rien de plus.

    Trois questions : est-ce que ça tourne, qu'est-ce qui passe, et que
    répond-on à un vote. Tout le reste — la file, la grille, le tirage, l'effet
    d'un `encore` — est décidé derrière cette frontière.
    """

    def en_diffusion(self) -> bool:
        """La chaîne tourne-t-elle ? Elle ne tourne que si quelqu'un écoute."""
        ...

    def antenne(self) -> Antenne | None:
        """Ce qui passe, ou `None` quand la chaîne est à l'arrêt."""
        ...

    def voter(self, vote: Vote) -> Verdict:
        """Applique un vote, ou le refuse en disant pourquoi.

        Une voix suffit : il n'y a ni quorum ni fenêtre de dépouillement
        (SPECS.md §4.6).
        """
        ...


def _antenne_en_donnees(antenne: Antenne | None) -> dict[str, str | None] | None:
    if antenne is None:
        return None
    return {
        "nature": str(antenne.nature),
        "titre": antenne.titre,
        "artiste": antenne.artiste,
    }


def creer_api(radio: Radio) -> Blueprint:
    """L'API, montée sous `/api`.

    Rendue par une fabrique plutôt que par un module global : c'est ce qui
    permet de l'assembler à la main dans `app/` (ARCHITECTURE.md §3) et de la
    tester contre un Fake sans variable de module à remettre à zéro.
    """
    api = Blueprint("api", __name__, url_prefix=CHEMIN_API)

    @api.get(CHEMIN_ANTENNE)
    def antenne() -> ResponseReturnValue:
        """Ce qui passe, et si la chaîne tourne."""
        return jsonify(
            {
                "en_diffusion": radio.en_diffusion(),
                "antenne": _antenne_en_donnees(radio.antenne()),
            }
        )

    @api.post(CHEMIN_VOTE)
    def voter(nom: str) -> ResponseReturnValue:
        """Un vote `stop` ou `encore`, accepté ou refusé **avec son motif**."""
        try:
            vote = Vote(nom)
        except ValueError:
            motif = f"vote inconnu : « {nom} »"
            logger.info("vote refusé — %s", motif)
            return jsonify({"accepte": False, "vote": nom, "motif": motif}), DEMANDE_INVALIDE

        verdict = radio.voter(vote)
        corps = {"accepte": verdict.accepte, "vote": str(vote), "motif": verdict.motif}
        if verdict.accepte:
            logger.info("vote « %s » accepté", vote)
            return jsonify(corps)
        logger.info("vote « %s » refusé — %s", vote, verdict.motif)
        return jsonify(corps), REFUS

    return api
