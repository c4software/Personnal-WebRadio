"""Le serveur du flux : ses en-têtes, et le cycle de vie qu'il commande.

Les auditeurs sont de vraies connexions HTTP. C'est nécessaire : la déconnexion
brutale ne s'observe pas autrement — une socket ne l'annonce pas, elle refuse la
prochaine écriture (`docs/flux-icy.md` §5).
"""

import http.client
import socket
import struct
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.test_ffmpeg import FakeProgramme, fabriquer, group_processes
from webradio.adapters.ffmpeg.encoder import Chain, ChainUnavailable, StreamFormat
from webradio.adapters.http.broadcast import Broadcast
from webradio.adapters.http.server import Feed, Station, StreamServer

FORMAT = StreamFormat(container="mp3", bitrate_kbps=128, sample_rate_hz=44100, channels=2)
CHEMIN = "/flux"
NAME = "radio d'essai"
DELAI = 30.0
BLOC = b"x" * 8192


class FakeChain:
    """Une chaîne qui ne lance aucun processus : elle émet ce qu'on lui dit.

    Elle suffit à tout ce que le serveur doit garantir — le démarrage à la
    première connexion, l'arrêt à la dernière — et laisse à `test_ffmpeg.py` ce
    qui demande de vrais processus.
    """

    def __init__(self, broadcast: Broadcast, refus: str | None = None) -> None:
        self._diffusion = broadcast
        self._refus = refus
        self.demarrages = 0
        self.arrete = threading.Event()

    def start(self) -> None:
        if self._refus is not None:
            raise ChainUnavailable(self._refus)
        self.demarrages += 1

    def stop_all(self) -> None:
        self.arrete.set()

    def emettre(self, block: bytes = BLOC) -> None:
        self._diffusion.publish(block)


class ObservedChain:
    """Une vraie chaîne, qui prévient quand on l'arrête.

    Attendre cet événement vaut mieux que sonder l'état : un test qui sonde
    conclut au bout d'un délai, et c'est ainsi qu'on rend vert un défaut lent.
    """

    def __init__(self, chaine: Chain) -> None:
        self._chaine = chaine
        self.arrete = threading.Event()

    @property
    def group(self) -> int:
        return self._chaine.group

    def start(self) -> None:
        self._chaine.start()

    def stop_all(self) -> None:
        self._chaine.stop_all()
        self.arrete.set()


class Factory:
    """Fabrique une chaîne par session, et garde la dernière sous la main."""

    def __init__(self, refus: str | None = None) -> None:
        self._refus = refus
        self.chaines: list[FakeChain] = []

    def __call__(self, broadcast: Broadcast) -> Feed:
        chaine = FakeChain(broadcast, self._refus)
        self.chaines.append(chaine)
        return chaine

    @property
    def derniere(self) -> FakeChain:
        return self.chaines[-1]


@contextmanager
def servir(station: Station) -> Iterator[StreamServer]:
    """Ouvre le serveur sur un port libre choisi par le système."""
    server = StreamServer(
        station, FORMAT, address="127.0.0.1", port=0, path=CHEMIN, name=NAME, lock_timeout=DELAI
    )
    server.start()
    try:
        yield server
    finally:
        server.stop_all()


def connect(server: StreamServer, path: str = CHEMIN) -> http.client.HTTPResponse:
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=DELAI)
    connection.request("GET", path)
    return connection.getresponse()


def brancher_par_socket(server: StreamServer) -> socket.socket:
    """Une connexion tenue à la main, pour pouvoir la couper vraiment.

    `http.client` referme ce qu'il veut quand il veut : pour éprouver une
    déconnexion, il faut être seul maître de la socket.
    """
    prise = socket.create_connection(("127.0.0.1", server.port), timeout=DELAI)
    prise.sendall(f"GET {CHEMIN} HTTP/1.0\r\nHost: local-webradio\r\n\r\n".encode())
    assert prise.recv(4096), "le serveur n'a rien répondu"
    return prise


def arracher(prise: socket.socket) -> None:
    """Coupe la connexion comme un câble arraché : une remise à zéro, sans adieu."""
    prise.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    prise.close()


@contextmanager
def show(chaine: FakeChain, cadence: float = 0.01) -> Iterator[None]:
    """Fait émettre la chaîne en continu, le temps de l'observation.

    Sans émission, le serveur n'apprendrait jamais qu'un auditeur est parti : une
    socket ne l'annonce pas, elle refuse la prochaine écriture. La cadence imite
    ce que fait un encodeur cadencé au temps réel — un déversement à pleine
    vitesse remplirait les tampons plus vite que le serveur ne les vide, et
    l'auditeur serait abandonné pour lenteur au lieu d'être vu parti.
    """
    end = threading.Event()

    def emettre() -> None:
        while not end.wait(cadence):
            chaine.emettre()

    fil = threading.Thread(target=emettre, name="émission d'essai", daemon=True)
    fil.start()
    try:
        yield
    finally:
        end.set()
        fil.join(DELAI)


@pytest.fixture
def factory() -> Factory:
    return Factory()


@pytest.fixture
def station(factory: Factory) -> Station:
    return Station(factory, capacity_per_listener=4096)


@pytest.fixture
def server(station: Station) -> Iterator[StreamServer]:
    with servir(station) as ouvert:
        yield ouvert


def test_le_flux_annonce_de_l_audio_sans_en_annoncer_la_longueur(
    server: StreamServer, factory: Factory
) -> None:
    """Les en-têtes constatés acceptés par les lecteurs (`docs/flux-icy.md` §1)."""
    answer = connect(server)
    factory.derniere.emettre()

    assert answer.status == 200
    assert answer.getheader("Content-Type") == "audio/mpeg"
    assert answer.getheader("icy-name") == NAME
    assert answer.getheader("icy-br") == "128"
    assert answer.getheader("Content-Length") is None
    assert answer.getheader("Transfer-Encoding") is None
    assert answer.read(len(BLOC)) == BLOC


def test_rien_ne_tourne_tant_que_personne_n_ecoute(
    server: StreamServer, station: Station, factory: Factory
) -> None:
    avant = station.on_air

    connect(server)

    assert not avant, "une chaîne tournait avant le premier auditeur"
    assert station.on_air
    assert factory.derniere.demarrages == 1


def test_le_deuxieme_auditeur_rejoint_le_flux_en_cours(
    server: StreamServer, station: Station, factory: Factory
) -> None:
    """Un seul encodage alimente tout le monde (SPECS.md §4.1)."""
    premier = connect(server)
    second = connect(server)
    factory.derniere.emettre()

    assert len(factory.chaines) == 1
    assert factory.derniere.demarrages == 1
    assert station.listeners == 2
    assert premier.read(len(BLOC)) == second.read(len(BLOC)) == BLOC


def test_la_chaine_s_arrete_a_la_derniere_deconnexion(
    server: StreamServer, station: Station, factory: Factory
) -> None:
    premier = brancher_par_socket(server)
    second = brancher_par_socket(server)
    chaine = factory.derniere

    with show(chaine):
        premier.close()
        assert not chaine.arrete.wait(1.0), "la chaîne s'est arrêtée alors qu'on écoutait encore"
        assert station.listeners == 1

        second.close()
        assert chaine.arrete.wait(DELAI), "le dernier auditeur parti, rien ne s'est arrêté"

    assert station.listeners == 0
    assert not station.on_air


def test_une_deconnexion_brutale_vaut_une_deconnexion(
    server: StreamServer, station: Station, factory: Factory
) -> None:
    """Câble arraché : la socket ne prévient pas, elle refuse la prochaine écriture."""
    prise = brancher_par_socket(server)
    chaine = factory.derniere

    arracher(prise)

    with show(chaine):
        assert chaine.arrete.wait(DELAI), "une déconnexion brutale n'a rien arrêté"
    assert station.listeners == 0


def test_un_chemin_inconnu_ne_branche_personne(server: StreamServer, station: Station) -> None:
    answer = connect(server, "/pas-le-flux")

    assert answer.status == 404
    assert not station.on_air


def test_une_chaine_qui_refuse_de_demarrer_le_dit_plutot_que_de_servir_du_vide() -> None:
    """SPECS.md §4.1 : jamais un flux vide, toujours une réponse explicite."""
    station = Station(Factory(refus="Navidrome est injoignable"))
    with servir(station) as server:
        answer = connect(server)

        assert answer.status == 503
        assert answer.getheader("Content-Type") != "audio/mpeg"
        assert "Navidrome est injoignable" in answer.read().decode()
        assert not station.on_air


def test_un_auditeur_recoit_un_flux_decodable_et_rien_ne_survit_a_son_depart(
    tmp_path: Path,
) -> None:
    """Bout en bout, avec de vrais ffmpeg : c'est le seul test qui prouve les deux.

    Et il compte les processus **avant** que le serveur ne ferme : ce qui les
    arrête doit être le départ de l'auditeur, pas l'arrêt du programme.
    """
    musique = fabriquer(tmp_path, "musique.mp3", 10, 44100, 2)
    observees: list[ObservedChain] = []

    def factory(broadcast: Broadcast) -> Feed:
        observed = ObservedChain(
            Chain(
                FakeProgramme([musique], boucler=True),
                FORMAT,
                broadcast.publish,
                broadcast.close,
            )
        )
        observees.append(observed)
        return observed

    station = Station(factory)
    with servir(station) as server:
        answer = connect(server)
        recu = answer.read(16 * 1024)
        group = observees[0].group
        assert len(recu) == 16 * 1024
        assert group_processes(group), "la chaîne devrait tourner pendant l'écoute"

        answer.close()

        assert observees[0].arrete.wait(DELAI), "le départ de l'auditeur n'a rien arrêté"
        assert group_processes(group) == []
        assert station.listeners == 0
