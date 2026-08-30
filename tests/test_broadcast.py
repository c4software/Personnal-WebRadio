"""Le fan-out : un flux, N connexions, et personne qui retient les autres.

Aucun processus ici : le partage est une décision de tampon, pas d'audio.
"""

import threading

import pytest

from webradio.adapters.http.broadcast import Abonne, Diffusion

DELAI = 5.0


def test_tous_les_auditeurs_recoivent_le_meme_bloc() -> None:
    diffusion = Diffusion(capacite_par_auditeur=4)
    premier, second = diffusion.abonner(), diffusion.abonner()

    diffusion.publier(b"une image mp3")

    assert next(premier.blocs(DELAI)) == b"une image mp3"
    assert next(second.blocs(DELAI)) == b"une image mp3"


def test_un_auditeur_lent_est_abandonne_sans_ralentir_les_autres() -> None:
    """La contrainte d'ARCHITECTURE.md §4.1, constatée : publier ne bloque jamais."""
    diffusion = Diffusion(capacite_par_auditeur=2)
    lent, rapide = diffusion.abonner(), diffusion.abonner()

    blocs_recus = []
    for rang in range(5):
        bloc = f"bloc {rang}".encode()
        diffusion.publier(bloc)
        blocs_recus.append(next(rapide.blocs(DELAI)))

    assert blocs_recus == [f"bloc {rang}".encode() for rang in range(5)]
    assert lent.ferme
    assert diffusion.auditeurs == 1


def test_un_auditeur_abandonne_voit_son_flux_se_terminer() -> None:
    diffusion = Diffusion(capacite_par_auditeur=1)
    lent = diffusion.abonner()
    diffusion.publier(b"premier")
    diffusion.publier(b"second")

    assert list(lent.blocs(DELAI)) == []


def test_la_fermeture_termine_toutes_les_connexions() -> None:
    diffusion = Diffusion(capacite_par_auditeur=4)
    abonne = diffusion.abonner()
    diffusion.publier(b"encore un peu de son")

    diffusion.fermer("la chaîne est arrêtée")

    assert list(abonne.blocs(DELAI)) == [b"encore un peu de son"]
    assert diffusion.auditeurs == 0


def test_publier_sans_personne_a_l_ecoute_ne_leve_pas() -> None:
    diffusion = Diffusion()
    diffusion.publier(b"dans le vide")
    assert diffusion.auditeurs == 0


def test_le_desabonnement_supporte_d_etre_vu_deux_fois() -> None:
    """Une déconnexion peut être constatée par l'écriture *et* par la fin du flux."""
    diffusion = Diffusion()
    abonne = diffusion.abonner()

    diffusion.desabonner(abonne)
    diffusion.desabonner(abonne)

    assert diffusion.auditeurs == 0
    assert abonne.ferme


def test_un_auditeur_attend_le_flux_sans_le_consommer_a_vide() -> None:
    """`blocs` attend ce qui vient, plutôt que de rendre la main sur un tampon vide."""
    diffusion = Diffusion()
    abonne = diffusion.abonner()
    recus: list[bytes] = []

    fil = threading.Thread(target=lambda: recus.extend(abonne.blocs(DELAI)))
    fil.start()
    diffusion.publier(b"tardif")
    diffusion.fermer("fin de l'essai")
    fil.join(DELAI)

    assert recus == [b"tardif"]


def test_un_auditeur_ferme_ne_recoit_plus_rien() -> None:
    """Fermer deux fois, ou publier après la fermeture, ne réveille personne."""
    abonne = Abonne(capacite=2)
    abonne.fermer()
    abonne.fermer()

    assert not abonne.deposer(b"trop tard")
    assert list(abonne.blocs(DELAI)) == []


def test_un_auditeur_au_tampon_plein_est_reveille_quand_meme() -> None:
    """La sentinelle de fin doit passer même quand il ne reste plus de place."""
    abonne = Abonne(capacite=1)
    assert abonne.deposer(b"le seul bloc qui tienne")

    abonne.fermer()

    assert list(abonne.blocs(DELAI)) == []


def test_un_tampon_sans_capacite_est_refuse() -> None:
    with pytest.raises(ValueError, match="capacité"):
        Abonne(0)
