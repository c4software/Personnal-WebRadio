"""L'interface : une page, ce qui passe, et deux boutons (SPECS.md §4.8).

Faite pour **un téléphone posé à côté de l'enceinte, utilisable à une main** :
son ergonomie compte davantage que sa conformité formelle (SPECS.md §3).

Le gabarit ne reçoit **aucune donnée d'antenne**. Il reçoit trois adresses et un
intervalle, et va tout chercher lui-même sur l'API. Ce n'est pas une coquetterie
technique : c'est ce qui rend l'interdit d'AGENTS.md §2 constatable plutôt que
promis. Une vue qui pré-remplirait la page avec l'état de la radio aurait un
second chemin d'accès au noyau, qui divergerait du premier.

Aucune décision dans le gabarit non plus : il affiche `accepte` et `motif` tels
que l'API les rend. Ce n'est pas lui qui calcule s'il faut refuser un vote.

**Rien ne se configure depuis le web** : le TOML reste le seul point d'entrée
des réglages (SPECS.md §6).
"""

from datetime import timedelta

from flask import Blueprint, Flask, render_template, url_for
from flask.typing import ResponseReturnValue

from webradio.adapters.web.api import Radio, Vote, creer_api

MILLISECONDES = 1000


def creer_vue(*, rafraichissement: timedelta) -> Blueprint:
    """La page unique.

    `rafraichissement` vient du TOML : c'est une durée, et aucune durée ne
    s'écrit dans le code (AGENTS.md §2).
    """
    if rafraichissement <= timedelta(0):
        message = "un rafraîchissement nul ferait boucler la page sans reprendre son souffle"
        raise ValueError(message)

    vue = Blueprint("vue", __name__, template_folder="templates")

    @vue.get("/")
    def page() -> ResponseReturnValue:
        return render_template(
            "index.html",
            url_antenne=url_for("api.antenne"),
            url_stop=url_for("api.voter", nom=str(Vote.STOP)),
            url_encore=url_for("api.voter", nom=str(Vote.ENCORE)),
            rafraichissement_ms=int(rafraichissement.total_seconds() * MILLISECONDES),
        )

    return vue


def creer_application(radio: Radio, *, rafraichissement: timedelta) -> Flask:
    """L'application complète : l'API, puis la page qui s'en sert.

    Les deux sont montées ensemble parce que la page ne sait rien faire sans
    l'API — c'est exactement ce qu'on veut vérifier.
    """
    application = Flask(__name__)
    application.register_blueprint(creer_api(radio))
    application.register_blueprint(creer_vue(rafraichissement=rafraichissement))
    return application
