"""L'interface : une page, ce qui passe, et deux boutons (SPECS.md §4.8).

Faite pour un téléphone utilisable à une main (SPECS.md §3).

Le gabarit ne reçoit aucune donnée d'antenne, seulement les adresses de l'API
et un intervalle ; il va tout chercher sur l'API. Une vue qui pré-remplirait la
page avec l'état de la radio créerait un second chemin vers le noyau
(AGENTS.md §2). Le gabarit ne décide rien non plus : il affiche `accepted` et
`reason` tels que l'API les rend.

Rien ne se configure depuis le web : le TOML est le seul point d'entrée des
réglages (SPECS.md §6).
"""

from datetime import timedelta

from flask import Blueprint, Flask, render_template, url_for
from flask.typing import ResponseReturnValue

from webradio.adapters.web.api import Radio, Vote, create_api
from webradio.adapters.web.playout_api import Playout, create_playout_api


def create_view(*, stream_url: str = "") -> Blueprint:
    """La page unique.

    `stream_url` est l'adresse que le lecteur de la page ouvre (GOAL-060) ;
    vide, la page n'a pas de lecteur.

    La page ne porte plus d'intervalle : elle s'abonne à `/api/events` et
    c'est le serveur qui décide quand elle apprend quelque chose (GOAL-073).
    """
    vue = Blueprint("vue", __name__, template_folder="templates")

    @vue.get("/")
    def page() -> ResponseReturnValue:
        return render_template(
            "index.html",
            url_evenements=url_for("api.events"),
            url_votes=url_for("api.votes_list"),
            url_planning=url_for("api.planning_view"),
            url_history=url_for("api.history_view"),
            url_stop=url_for("api.vote", name=str(Vote.SKIP)),
            url_encore=url_for("api.vote", name=str(Vote.MORE)),
            url_redraw=url_for("api.redraw_moment"),
            url_up_next=url_for("api.up_next_list"),
            url_flux=stream_url,
        )

    return vue


def create_app(
    radio: Radio,
    *,
    refresh: timedelta,
    playout: Playout | None = None,
    planning: dict[str, object] | None = None,
    stream_url: str = "",
) -> Flask:
    """L'application complète : l'API, la page qui s'en sert, et les routes de
    Liquidsoap si `playout` est fourni."""
    app = Flask(__name__)
    app.register_blueprint(create_api(radio, refresh=refresh, planning=planning))
    app.register_blueprint(create_view(stream_url=stream_url))
    if playout is not None:
        app.register_blueprint(create_playout_api(playout))
    return app
