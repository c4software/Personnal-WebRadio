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

from tests.test_ffmpeg import FakeProgramme, fabriquer, processus_du_groupe
from webradio.adapters.ffmpeg.encodeur import Chaine, ChaineIndisponible, FormatFlux
from webradio.adapters.http.diffusion import Diffusion
from webradio.adapters.http.serveur import Alimentation, ServeurFlux, Station

FORMAT = FormatFlux(conteneur="mp3", debit_kbps=128, frequence_hz=44100, canaux=2)
CHEMIN = "/flux"
NOM = "radio d'essai"
DELAI = 30.0
BLOC = b"x" * 8192


class FakeChaine:
    """Une chaîne qui ne lance aucun processus : elle émet ce qu'on lui dit.

    Elle suffit à tout ce que le serveur doit garantir — le démarrage à la
    première connexion, l'arrêt à la dernière — et laisse à `test_ffmpeg.py` ce
    qui demande de vrais processus.
    """

    def __init__(self, diffusion: Diffusion, refus: str | None = None) -> None:
        self._diffusion = diffusion
        self._refus = refus
        self.demarrages = 0
        self.arrete = threading.Event()

    def demarrer(self) -> None:
        if self._refus is not None:
            raise ChaineIndisponible(self._refus)
        self.demarrages += 1

    def arreter(self) -> None:
        self.arrete.set()

    def emettre(self, bloc: bytes = BLOC) -> None:
        self._diffusion.publier(bloc)


class ChaineObservee:
    """Une vraie chaîne, qui prévient quand on l'arrête.

    Attendre cet événement vaut mieux que sonder l'état : un test qui sonde
    conclut au bout d'un délai, et c'est ainsi qu'on rend vert un défaut lent.
    """

    def __init__(self, chaine: Chaine) -> None:
        self._chaine = chaine
        self.arrete = threading.Event()

    @property
    def groupe(self) -> int:
        return self._chaine.groupe

    def demarrer(self) -> None:
        self._chaine.demarrer()

    def arreter(self) -> None:
        self._chaine.arreter()
        self.arrete.set()


class Fabrique:
    """Fabrique une chaîne par session, et garde la dernière sous la main."""

    def __init__(self, refus: str | None = None) -> None:
        self._refus = refus
        self.chaines: list[FakeChaine] = []

    def __call__(self, diffusion: Diffusion) -> Alimentation:
        chaine = FakeChaine(diffusion, self._refus)
        self.chaines.append(chaine)
        return chaine

    @property
    def derniere(self) -> FakeChaine:
        return self.chaines[-1]


@contextmanager
def servir(station: Station) -> Iterator[ServeurFlux]:
    """Ouvre le serveur sur un port libre choisi par le système."""
    serveur = ServeurFlux(
        station, FORMAT, adresse="127.0.0.1", port=0, chemin=CHEMIN, nom=NOM, delai_attente=DELAI
    )
    serveur.demarrer()
    try:
        yield serveur
    finally:
        serveur.arreter()


def brancher(serveur: ServeurFlux, chemin: str = CHEMIN) -> http.client.HTTPResponse:
    connexion = http.client.HTTPConnection("127.0.0.1", serveur.port, timeout=DELAI)
    connexion.request("GET", chemin)
    return connexion.getresponse()


def brancher_par_socket(serveur: ServeurFlux) -> socket.socket:
    """Une connexion tenue à la main, pour pouvoir la couper vraiment.

    `http.client` referme ce qu'il veut quand il veut : pour éprouver une
    déconnexion, il faut être seul maître de la socket.
    """
    prise = socket.create_connection(("127.0.0.1", serveur.port), timeout=DELAI)
    prise.sendall(f"GET {CHEMIN} HTTP/1.0\r\nHost: local-webradio\r\n\r\n".encode())
    assert prise.recv(4096), "le serveur n'a rien répondu"
    return prise


def arracher(prise: socket.socket) -> None:
    """Coupe la connexion comme un câble arraché : une remise à zéro, sans adieu."""
    prise.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
    prise.close()


@contextmanager
def emission(chaine: FakeChaine, cadence: float = 0.01) -> Iterator[None]:
    """Fait émettre la chaîne en continu, le temps de l'observation.

    Sans émission, le serveur n'apprendrait jamais qu'un auditeur est parti : une
    socket ne l'annonce pas, elle refuse la prochaine écriture. La cadence imite
    ce que fait un encodeur cadencé au temps réel — un déversement à pleine
    vitesse remplirait les tampons plus vite que le serveur ne les vide, et
    l'auditeur serait abandonné pour lenteur au lieu d'être vu parti.
    """
    fin = threading.Event()

    def emettre() -> None:
        while not fin.wait(cadence):
            chaine.emettre()

    fil = threading.Thread(target=emettre, name="émission d'essai", daemon=True)
    fil.start()
    try:
        yield
    finally:
        fin.set()
        fil.join(DELAI)


@pytest.fixture
def fabrique() -> Fabrique:
    return Fabrique()


@pytest.fixture
def station(fabrique: Fabrique) -> Station:
    return Station(fabrique, capacite_par_auditeur=4096)


@pytest.fixture
def serveur(station: Station) -> Iterator[ServeurFlux]:
    with servir(station) as ouvert:
        yield ouvert


def test_le_flux_annonce_de_l_audio_sans_en_annoncer_la_longueur(
    serveur: ServeurFlux, fabrique: Fabrique
) -> None:
    """Les en-têtes constatés acceptés par les lecteurs (`docs/flux-icy.md` §1)."""
    reponse = brancher(serveur)
    fabrique.derniere.emettre()

    assert reponse.status == 200
    assert reponse.getheader("Content-Type") == "audio/mpeg"
    assert reponse.getheader("icy-name") == NOM
    assert reponse.getheader("icy-br") == "128"
    assert reponse.getheader("Content-Length") is None
    assert reponse.getheader("Transfer-Encoding") is None
    assert reponse.read(len(BLOC)) == BLOC


def test_rien_ne_tourne_tant_que_personne_n_ecoute(
    serveur: ServeurFlux, station: Station, fabrique: Fabrique
) -> None:
    avant = station.en_antenne

    brancher(serveur)

    assert not avant, "une chaîne tournait avant le premier auditeur"
    assert station.en_antenne
    assert fabrique.derniere.demarrages == 1


def test_le_deuxieme_auditeur_rejoint_le_flux_en_cours(
    serveur: ServeurFlux, station: Station, fabrique: Fabrique
) -> None:
    """Un seul encodage alimente tout le monde (SPECS.md §4.1)."""
    premier = brancher(serveur)
    second = brancher(serveur)
    fabrique.derniere.emettre()

    assert len(fabrique.chaines) == 1
    assert fabrique.derniere.demarrages == 1
    assert station.auditeurs == 2
    assert premier.read(len(BLOC)) == second.read(len(BLOC)) == BLOC


def test_la_chaine_s_arrete_a_la_derniere_deconnexion(
    serveur: ServeurFlux, station: Station, fabrique: Fabrique
) -> None:
    premier = brancher_par_socket(serveur)
    second = brancher_par_socket(serveur)
    chaine = fabrique.derniere

    with emission(chaine):
        premier.close()
        assert not chaine.arrete.wait(1.0), "la chaîne s'est arrêtée alors qu'on écoutait encore"
        assert station.auditeurs == 1

        second.close()
        assert chaine.arrete.wait(DELAI), "le dernier auditeur parti, rien ne s'est arrêté"

    assert station.auditeurs == 0
    assert not station.en_antenne


def test_une_deconnexion_brutale_vaut_une_deconnexion(
    serveur: ServeurFlux, station: Station, fabrique: Fabrique
) -> None:
    """Câble arraché : la socket ne prévient pas, elle refuse la prochaine écriture."""
    prise = brancher_par_socket(serveur)
    chaine = fabrique.derniere

    arracher(prise)

    with emission(chaine):
        assert chaine.arrete.wait(DELAI), "une déconnexion brutale n'a rien arrêté"
    assert station.auditeurs == 0


def test_un_chemin_inconnu_ne_branche_personne(serveur: ServeurFlux, station: Station) -> None:
    reponse = brancher(serveur, "/pas-le-flux")

    assert reponse.status == 404
    assert not station.en_antenne


def test_une_chaine_qui_refuse_de_demarrer_le_dit_plutot_que_de_servir_du_vide() -> None:
    """SPECS.md §4.1 : jamais un flux vide, toujours une réponse explicite."""
    station = Station(Fabrique(refus="Navidrome est injoignable"))
    with servir(station) as serveur:
        reponse = brancher(serveur)

        assert reponse.status == 503
        assert reponse.getheader("Content-Type") != "audio/mpeg"
        assert "Navidrome est injoignable" in reponse.read().decode()
        assert not station.en_antenne


def test_un_auditeur_recoit_un_flux_decodable_et_rien_ne_survit_a_son_depart(
    tmp_path: Path,
) -> None:
    """Bout en bout, avec de vrais ffmpeg : c'est le seul test qui prouve les deux.

    Et il compte les processus **avant** que le serveur ne ferme : ce qui les
    arrête doit être le départ de l'auditeur, pas l'arrêt du programme.
    """
    musique = fabriquer(tmp_path, "musique.mp3", 10, 44100, 2)
    observees: list[ChaineObservee] = []

    def fabrique(diffusion: Diffusion) -> Alimentation:
        observee = ChaineObservee(
            Chaine(
                FakeProgramme([musique], boucler=True),
                FORMAT,
                diffusion.publier,
                diffusion.fermer,
            )
        )
        observees.append(observee)
        return observee

    station = Station(fabrique)
    with servir(station) as serveur:
        reponse = brancher(serveur)
        recu = reponse.read(16 * 1024)
        groupe = observees[0].groupe
        assert len(recu) == 16 * 1024
        assert processus_du_groupe(groupe), "la chaîne devrait tourner pendant l'écoute"

        reponse.close()

        assert observees[0].arrete.wait(DELAI), "le départ de l'auditeur n'a rien arrêté"
        assert processus_du_groupe(groupe) == []
        assert station.auditeurs == 0
