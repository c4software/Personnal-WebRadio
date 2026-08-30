"""Les routes de Liquidsoap : quoi jouer, et combien écoutent (GOAL-016-T02, T03)."""

from datetime import timedelta

from flask.testing import FlaskClient

from tests.test_api import FakeRadio
from webradio.adapters.web import create_app


class FakePlayout:
    def __init__(self, entries: list[str | None]) -> None:
        self._entries = entries
        self.listeners: list[int] = []

    def next_entry(self) -> str | None:
        return self._entries.pop(0)

    def declare_listeners(self, count: int) -> None:
        self.listeners.append(count)


def _client(playout: FakePlayout | None) -> FlaskClient:
    app = create_app(FakeRadio(), refresh=timedelta(seconds=5), playout=playout)
    app.config.update(TESTING=True)
    return app.test_client()


def test_le_morceau_suivant_est_rendu_en_texte_brut() -> None:
    answer = _client(FakePlayout(["/jingles/20h.mp3"])).post("/playout/next")
    assert answer.status_code == 200
    assert answer.mimetype == "text/plain"
    assert answer.get_data(as_text=True) == "/jingles/20h.mp3"


def test_chaque_appel_consomme_un_morceau() -> None:
    client = _client(FakePlayout(["a", "b"]))
    assert client.post("/playout/next").get_data(as_text=True) == "a"
    assert client.post("/playout/next").get_data(as_text=True) == "b"


def test_plus_rien_a_jouer_se_dit_par_un_204_et_non_par_du_silence() -> None:
    answer = _client(FakePlayout([None])).post("/playout/next")
    assert answer.status_code == 204
    assert answer.get_data() == b""


def test_le_nombre_d_auditeurs_est_transmis() -> None:
    playout = FakePlayout([])
    client = _client(playout)
    assert client.post("/playout/listeners", data="1").status_code == 204
    assert client.post("/playout/listeners", data="0\n").status_code == 204
    assert playout.listeners == [1, 0]


def test_un_nombre_d_auditeurs_invalide_est_refuse_en_le_disant() -> None:
    playout = FakePlayout([])
    answer = _client(playout).post("/playout/listeners", data="beaucoup")
    assert answer.status_code == 400
    assert "beaucoup" in answer.get_data(as_text=True)
    assert playout.listeners == []


def test_sans_playout_les_routes_n_existent_pas() -> None:
    assert _client(None).post("/playout/next").status_code == 404
