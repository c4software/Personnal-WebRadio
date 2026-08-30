"""Le fan-out : un flux, N connexions, et personne qui retient les autres.

Aucun processus ici : le partage est une décision de tampon, pas d'audio.
"""

import threading

import pytest

from webradio.adapters.http.broadcast import Broadcast, Subscriber

DELAI = 5.0


def test_tous_les_auditeurs_recoivent_le_meme_bloc() -> None:
    broadcast = Broadcast(capacity_per_listener=4)
    premier, second = broadcast.subscribe(), broadcast.subscribe()

    broadcast.publish(b"une image mp3")

    assert next(premier.blocks(DELAI)) == b"une image mp3"
    assert next(second.blocks(DELAI)) == b"une image mp3"


def test_un_auditeur_lent_est_abandonne_sans_ralentir_les_autres() -> None:
    """La contrainte d'ARCHITECTURE.md §4.1, constatée : publier ne bloque jamais."""
    broadcast = Broadcast(capacity_per_listener=2)
    lent, rapide = broadcast.subscribe(), broadcast.subscribe()

    blocs_recus = []
    for index in range(5):
        block = f"bloc {index}".encode()
        broadcast.publish(block)
        blocs_recus.append(next(rapide.blocks(DELAI)))

    assert blocs_recus == [f"bloc {index}".encode() for index in range(5)]
    assert lent.ferme
    assert broadcast.listeners == 1


def test_un_auditeur_abandonne_voit_son_flux_se_terminer() -> None:
    broadcast = Broadcast(capacity_per_listener=1)
    lent = broadcast.subscribe()
    broadcast.publish(b"premier")
    broadcast.publish(b"second")

    assert list(lent.blocks(DELAI)) == []


def test_la_fermeture_termine_toutes_les_connexions() -> None:
    broadcast = Broadcast(capacity_per_listener=4)
    subscriber = broadcast.subscribe()
    broadcast.publish(b"encore un peu de son")

    broadcast.close("la chaîne est arrêtée")

    assert list(subscriber.blocks(DELAI)) == [b"encore un peu de son"]
    assert broadcast.listeners == 0


def test_publier_sans_personne_a_l_ecoute_ne_leve_pas() -> None:
    broadcast = Broadcast()
    broadcast.publish(b"dans le vide")
    assert broadcast.listeners == 0


def test_le_desabonnement_supporte_d_etre_vu_deux_fois() -> None:
    """Une déconnexion peut être constatée par l'écriture *et* par la fin du flux."""
    broadcast = Broadcast()
    subscriber = broadcast.subscribe()

    broadcast.unsubscribe(subscriber)
    broadcast.unsubscribe(subscriber)

    assert broadcast.listeners == 0
    assert subscriber.ferme


def test_un_auditeur_attend_le_flux_sans_le_consommer_a_vide() -> None:
    """`blocs` attend ce qui vient, plutôt que de rendre la main sur un tampon vide."""
    broadcast = Broadcast()
    subscriber = broadcast.subscribe()
    recus: list[bytes] = []

    fil = threading.Thread(target=lambda: recus.extend(subscriber.blocks(DELAI)))
    fil.start()
    broadcast.publish(b"tardif")
    broadcast.close("fin de l'essai")
    fil.join(DELAI)

    assert recus == [b"tardif"]


def test_un_auditeur_ferme_ne_recoit_plus_rien() -> None:
    """Fermer deux fois, ou publier après la fermeture, ne réveille personne."""
    subscriber = Subscriber(capacity=2)
    subscriber.close()
    subscriber.close()

    assert not subscriber.deposer(b"trop tard")
    assert list(subscriber.blocks(DELAI)) == []


def test_un_auditeur_au_tampon_plein_est_reveille_quand_meme() -> None:
    """La sentinelle de fin doit passer même quand il ne reste plus de place."""
    subscriber = Subscriber(capacity=1)
    assert subscriber.deposer(b"le seul bloc qui tienne")

    subscriber.close()

    assert list(subscriber.blocks(DELAI)) == []


def test_un_tampon_sans_capacite_est_refuse() -> None:
    with pytest.raises(ValueError, match="capacité"):
        Subscriber(0)
