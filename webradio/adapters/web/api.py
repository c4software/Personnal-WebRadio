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

API_PATH = "/api"
ON_AIR_PATH = "/on-air"
VOTE_PATH = "/votes/<name>"
VOTES_PATH = "/votes"
MOMENT_REDRAW_PATH = "/moment/redraw"
UP_NEXT_PATH = "/up-next"
UP_NEXT_ENTRY_PATH = "/up-next/<identifier>"

REFUS = 409
DEMANDE_INVALIDE = 400


class Kind(StrEnum):
    """De quelle nature est ce qui passe (SPECS.md §4.8).

    L'auditeur doit pouvoir distinguer un morceau d'un habillage : c'est aussi
    ce qui rend un refus de vote compréhensible plutôt que surprenant.
    """

    MUSIC = "musique"
    JINGLE = "jingle"
    NEWS = "flash"
    SHOW = "emission"


class Vote(StrEnum):
    """Les deux commandes de SPECS.md §4.6. « Vote » est un mot pour « bouton »."""

    SKIP = "stop"
    MORE = "encore"


@dataclass(frozen=True, slots=True)
class OnAir:
    """Ce qui passe à cet instant.

    `titre` et `artiste` sont facultatifs : un jingle horaire ou un flash n'ont
    ni l'un ni l'autre, et inventer un libellé ici serait une décision prise
    dans un adaptateur.
    """

    kind: Kind
    title: str | None = None
    artist: str | None = None


@dataclass(frozen=True, slots=True)
class VoteScore:
    """Ce qu'une cible a accumulé, décroissance déjà appliquée.

    `scope` vaut `piste` ou `artiste` — les mots de SPECS.md §4.12, pas ceux
    de la base : l'API ne connaît pas SQLite. `key` est la cible brute — ce
    qu'il faut rendre pour l'effacer — quand `target` est le libellé lisible.
    """

    scope: str
    target: str
    stop: float
    encore: float
    key: str = ""


@dataclass(frozen=True, slots=True)
class PlayedEntry:
    """Une ligne du journal : quand, quoi, par qui.

    `on` porte le **jour** (`AAAA-MM-JJ`) et `at` l'heure. Le journal couvre
    vingt-quatre heures : sans le jour, la page rangeait sous « 08 h » celui
    d'aujourd'hui et celui d'hier, et l'ordre paraissait faux alors qu'il ne
    l'était pas (signalé par l'auteur le 2026-09-02).
    """

    on: str
    at: str
    kind: str
    title: str
    artist: str


@dataclass(frozen=True, slots=True)
class UpcomingEntry:
    """Une ligne de la liste des prochains titres (GOAL-058).

    `identifier` est ce qu'il faut rendre pour retirer le titre — vide pour
    l'habillage, qui ne se retire pas. `at` est l'heure **estimée** du début,
    `HH:MM`, ou `None` quand rien ne permet d'estimer ; `expected` distingue
    l'habillage prévu de ce qui est déjà tiré.
    """

    kind: Kind
    title: str | None
    artist: str | None
    identifier: str = ""
    at: str | None = None
    expected: bool = False


@dataclass(frozen=True, slots=True)
class Verdict:
    """La réponse du noyau à un vote.

    `motif` est obligatoire quand le vote est refusé : un refus muet est
    indistinguable d'une panne et pousse à réessayer (ARCHITECTURE.md §6.1).
    """

    accepted: bool
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.accepted and not self.reason:
            message = "un refus sans motif est indistinguable d'une panne"
            raise ValueError(message)


class Radio(Protocol):
    """Ce que l'API attend de la radio, et rien de plus.

    Trois questions : est-ce que ça tourne, qu'est-ce qui passe, et que
    répond-on à un vote. Tout le reste — la file, la grille, le tirage, l'effet
    d'un `encore` — est décidé derrière cette frontière.
    """

    def on_air(self) -> bool:
        """La chaîne tourne-t-elle ? Elle ne tourne que si quelqu'un écoute."""
        ...

    def on_air_now(self) -> OnAir | None:
        """Ce qui passe, ou `None` quand la chaîne est à l'arrêt."""
        ...

    def vote(self, vote: Vote) -> Verdict:
        """Applique un vote, ou le refuse en disant pourquoi.

        Une voix suffit : il n'y a ni quorum ni fenêtre de dépouillement
        (SPECS.md §4.6).
        """
        ...

    def vote_scores(self) -> list[VoteScore]:
        """Ce que la radio a retenu des votes, plus forts d'abord."""
        ...

    def forget_vote(self, scope: str, target: str) -> bool:
        """Efface une cible votée par erreur. Faux si elle n'existait pas."""
        ...

    def history(self) -> list[PlayedEntry]:
        """Ce qui est passé, du plus récent au plus ancien (§7 n°27)."""
        ...

    def up_next(self) -> "OnAir | None":
        """Le morceau déjà demandé qui suivra, ou rien (GOAL-035)."""
        ...

    def moment(self) -> str | None:
        """Le moment déclaré qui s'applique — programme ou plage — ou rien.

        C'est du contexte, pas de l'antenne : une émission se voit déjà par
        sa nature. `None` en tirage libre.
        """
        ...

    def moment_random(self) -> bool:
        """Le moment en cours a-t-il tiré son thème au sort (SPECS.md §4.4) ?

        C'est ce qui dit à l'interface si « Retirer » a un sens — elle ne
        doit pas le deviner sur le libellé.
        """
        ...

    def redraw_moment(self) -> Verdict:
        """Retire le thème du moment en cours, ou refuse en disant pourquoi
        (GOAL-057). Hors d'une plage au hasard, il n'y a rien à retirer."""
        ...

    def upcoming(self) -> list[UpcomingEntry]:
        """Les prochains titres dans l'ordre de passage, habillage prévu
        compris (GOAL-058). Vide quand la chaîne ne tourne pas."""
        ...

    def withdraw(self, identifier: str) -> bool:
        """Retire un titre qui attend : il ne passera pas, un autre le
        remplace. Faux s'il n'attend plus (GOAL-058)."""
        ...


def _antenne_en_donnees(on_air_now: OnAir | None) -> dict[str, str | None] | None:
    if on_air_now is None:
        return None
    return {
        "kind": str(on_air_now.kind),
        "title": on_air_now.title,
        "artist": on_air_now.artist,
    }


def create_api(radio: Radio, planning: dict[str, object] | None = None) -> Blueprint:
    """L'API, montée sous `/api`.

    Rendue par une fabrique plutôt que par un module global : c'est ce qui
    permet de l'assembler à la main dans `app/` (ARCHITECTURE.md §3) et de la
    tester contre un Fake sans variable de module à remettre à zéro.
    """
    api = Blueprint("api", __name__, url_prefix=API_PATH)

    @api.get("/planning")
    def planning_view() -> ResponseReturnValue:
        """La grille **effective** de la semaine, jour par jour (GOAL-068).

        Des données figées à l'assemblage : rien ne se configure depuis le
        web (SPECS.md §6). Les périodes y sont déjà fusionnées — une émission
        devant la plage qu'elle mange, un direct qui rogne celle qu'il
        recouvre — pour que la page montre ce qui passera, et non ce qui a été
        déclaré.
        """
        return jsonify(planning or {"days": {}})

    @api.get(ON_AIR_PATH)
    def on_air_now() -> ResponseReturnValue:
        """Ce qui passe, et si la chaîne tourne."""
        return jsonify(
            {
                "on_air": radio.on_air(),
                "on_air_now": _antenne_en_donnees(radio.on_air_now()),
                "moment": radio.moment(),
                "moment_random": radio.moment_random(),
                "up_next": _antenne_en_donnees(radio.up_next()),
            }
        )

    @api.get(VOTES_PATH)
    def votes_list() -> ResponseReturnValue:
        """Ce que les votes ont laissé : par cible, décroissance comprise."""
        return jsonify(
            {
                "votes": [
                    {
                        "scope": v.scope,
                        "target": v.target,
                        "key": v.key or v.target,
                        "stop": round(v.stop, 2),
                        "encore": round(v.encore, 2),
                    }
                    for v in radio.vote_scores()
                ]
            }
        )

    @api.delete("/votes/<scope>/<path:target>")
    def forget(scope: str, target: str) -> ResponseReturnValue:
        """Effacer un vote donné par erreur (GOAL-021). 404 s'il n'existe pas."""
        if scope not in ("piste", "artiste"):
            return jsonify({"deleted": False, "reason": f"portée inconnue : « {scope} »"}), 400
        if radio.forget_vote(scope, target):
            logger.info("vote effacé : %s « %s »", scope, target)
            return jsonify({"deleted": True})
        return jsonify({"deleted": False, "reason": "aucun vote pour cette cible"}), 404

    @api.get("/history")
    def history_view() -> ResponseReturnValue:
        """Le journal des titres — jamais l'audio (SPECS.md §2 tient toujours)."""
        return jsonify(
            {
                "history": [
                    {
                        "on": e.on,
                        "at": e.at,
                        "kind": e.kind,
                        "title": e.title,
                        "artist": e.artist,
                    }
                    for e in radio.history()
                ]
            }
        )

    @api.post(VOTE_PATH)
    def vote(name: str) -> ResponseReturnValue:
        """Un vote `stop` ou `encore`, accepté ou refusé **avec son motif**."""
        try:
            vote = Vote(name)
        except ValueError:
            reason = f"vote inconnu : « {name} »"
            logger.info("vote refusé — %s", reason)
            return jsonify({"accepted": False, "vote": name, "reason": reason}), DEMANDE_INVALIDE

        verdict = radio.vote(vote)
        body = {"accepted": verdict.accepted, "vote": str(vote), "reason": verdict.reason}
        if verdict.accepted:
            logger.info("vote « %s » accepté", vote)
            return jsonify(body)
        logger.info("vote « %s » refusé — %s", vote, verdict.reason)
        return jsonify(body), REFUS

    @api.get(UP_NEXT_PATH)
    def up_next_list() -> ResponseReturnValue:
        """La liste des prochains titres, dans l'ordre de passage (GOAL-058)."""
        return jsonify(
            {
                "up_next": [
                    {
                        "kind": str(e.kind),
                        "title": e.title,
                        "artist": e.artist,
                        "identifier": e.identifier,
                        "at": e.at,
                        "expected": e.expected,
                    }
                    for e in radio.upcoming()
                ]
            }
        )

    @api.delete(UP_NEXT_ENTRY_PATH)
    def withdraw(identifier: str) -> ResponseReturnValue:
        """Retirer un titre avant qu'il passe. 404 s'il n'attend plus — il a
        pu commencer entre-temps, et cela arrivera."""
        if radio.withdraw(identifier):
            logger.info("retiré avant diffusion : %s", identifier)
            return jsonify({"withdrawn": True})
        return jsonify({"withdrawn": False, "reason": "ce titre n'attend plus"}), 404

    @api.post(MOMENT_REDRAW_PATH)
    def redraw_moment() -> ResponseReturnValue:
        """Retirer le thème d'une plage au hasard — accepté avec le nouveau
        moment, ou refusé avec son motif (GOAL-057)."""
        verdict = radio.redraw_moment()
        body = {"accepted": verdict.accepted, "reason": verdict.reason, "moment": radio.moment()}
        if verdict.accepted:
            logger.info("thème retiré : %s", body["moment"])
            return jsonify(body)
        logger.info("retirage refusé — %s", verdict.reason)
        return jsonify(body), REFUS

    return api
