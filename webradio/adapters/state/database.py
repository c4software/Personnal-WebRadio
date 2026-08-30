"""L'état durable, dans SQLite — et rien d'autre.

Pourquoi une base pour si peu (ARCHITECTURE.md §5.1) : **deux processus vivent
en même temps**. La chaîne de diffusion écrit l'identifiant d'un épisode quand
une émission démarre ; le serveur Flask lit et écrit les votes. Un fichier JSON
demanderait d'écrire soi-même ce que SQLite fait déjà : écriture atomique,
lecture concurrente cohérente, et pas de fichier tronqué si la machine s'éteint
au mauvais moment.

**Perdre cette base n'est pas une panne** (ARCHITECTURE.md §5.0) : une base
absente ou vide se comporte comme « rien n'a jamais été diffusé » et « poids
neutres ». Elle se crée toute seule, elle ne se sauvegarde pas, elle ne se migre
pas.

Deux tables, et la garde d'ARCHITECTURE.md §5.0 s'applique à la troisième :
rien d'autre n'entre ici, et surtout pas « puisqu'on a une base ». Ni historique
d'antenne, ni statistiques, ni position de lecture, ni profil.
"""

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path

from webradio.core.clock import Horloge

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS emissions_diffusees (
    emission   TEXT PRIMARY KEY,
    episode    TEXT NOT NULL,
    diffuse_le TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
    portee       TEXT NOT NULL,
    cible        TEXT NOT NULL,
    score_stop   REAL NOT NULL DEFAULT 0,
    score_encore REAL NOT NULL DEFAULT 0,
    vu_le        TEXT NOT NULL,
    PRIMARY KEY (portee, cible)
);
"""


class EtatIndisponible(Exception):
    """La base existe mais ne se laisse ni lire ni écrire.

    Traduite au plus près de son origine : au-dessus de cet adaptateur, plus
    personne ne connaît `sqlite3` (ARCHITECTURE.md §7).
    """


class Portee(StrEnum):
    """Sur quoi porte un vote (SPECS.md §7 n°16).

    Un `StrEnum` plutôt qu'une chaîne libre : la valeur est écrite telle quelle
    dans la colonne `portee`, et une faute de frappe y créerait silencieusement
    une troisième portée que personne ne relirait jamais.
    """

    PISTE = "piste"
    ARTISTE = "artiste"


@dataclass(frozen=True, slots=True)
class Diffusion:
    """Ce que la base retient d'une émission : un épisode, et quand il est passé.

    `diffuse_le` ne sert à aucune décision — c'est du diagnostic
    (ARCHITECTURE.md §5.1). Aucune règle ne doit s'appuyer dessus, sans quoi
    perdre la base cesserait d'être anodin.
    """

    episode: str
    diffuse_le: datetime


@dataclass(frozen=True, slots=True)
class Scores:
    """Les deux scores d'une cible, **décroissance déjà appliquée**.

    Ce sont des réels, pas des compteurs : le score porte l'oubli de
    SPECS.md §4.12. Avec des entiers et une seule date, douze `stop` dont le
    dernier date d'hier compteraient tous comme frais, et personne ne s'en
    apercevrait.
    """

    stop: float = 0.0
    encore: float = 0.0


def _decroitre(score: float, ecoule: timedelta, demi_vie: timedelta) -> float:
    """`score * 2 ** (-Δt / demi_vie)` — l'oubli de SPECS.md §4.12.

    Un `Δt` négatif — horloge reculée, fichier recopié d'une autre machine —
    ne fait pas grossir un score : on rend la valeur telle quelle.
    """
    if ecoule <= timedelta(0):
        return score
    return float(score * 2.0 ** (-(ecoule / demi_vie)))


class EtatSQLite:
    """L'état durable, ouvert et refermé à chaque opération.

    Une connexion par opération plutôt qu'une connexion gardée : Flask sert
    plusieurs requêtes en parallèle et la chaîne de diffusion écrit depuis un
    autre processus. Une connexion partagée entre fils imposerait de désactiver
    la garde `check_same_thread` de `sqlite3` — donc de reprendre à la main la
    sérialisation que SQLite fait déjà. Le coût d'ouverture est négligeable
    devant une écriture par morceau diffusé.
    """

    def __init__(
        self,
        chemin: Path,
        horloge: Horloge,
        *,
        delai_attente: timedelta,
        demi_vie_votes: timedelta,
    ) -> None:
        """`delai_attente` et `demi_vie_votes` viennent du TOML (SPECS.md §6.2).

        Aucun défaut n'est écrit ici : une durée en dur dans le code est un
        interdit (AGENTS.md §2), et le défaut se déclare là où la clé est
        documentée.
        """
        if delai_attente <= timedelta(0):
            message = "un délai d'attente nul rendrait toute écriture concurrente perdante"
            raise ValueError(message)
        if demi_vie_votes <= timedelta(0):
            message = "une demi-vie nulle ou négative ne définit aucune décroissance"
            raise ValueError(message)
        self._chemin = chemin
        self._horloge = horloge
        self._delai_attente = delai_attente
        self._demi_vie = demi_vie_votes
        self._preparer()

    def _preparer(self) -> None:
        """Crée le fichier, son dossier et le schéma s'ils manquent.

        Il n'y a pas de migration : le schéma se crée ou existe déjà. Le perdre
        n'étant pas une panne, il n'y a rien à faire évoluer.
        """
        self._chemin.parent.mkdir(parents=True, exist_ok=True)
        with self._connexion() as connexion:
            connexion.execute("PRAGMA journal_mode = WAL")
            connexion.executescript(SCHEMA)

    @contextmanager
    def _connexion(self) -> Iterator[sqlite3.Connection]:
        """Une connexion en WAL, avec le délai d'attente déclaré.

        WAL parce qu'un lecteur ne doit pas attendre un écrivain : le serveur
        web lit pendant que la chaîne écrit, et l'inverse.
        """
        try:
            connexion = sqlite3.connect(
                self._chemin,
                timeout=self._delai_attente.total_seconds(),
                isolation_level=None,
            )
        except sqlite3.Error as erreur:
            message = f"base d'état inaccessible : {self._chemin}"
            raise EtatIndisponible(message) from erreur
        try:
            yield connexion
        except sqlite3.Error as erreur:
            message = f"base d'état illisible ou verrouillée : {self._chemin}"
            raise EtatIndisponible(message) from erreur
        finally:
            connexion.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        """Une écriture qui lit d'abord ce qu'elle va modifier.

        `BEGIN IMMEDIATE` prend le verrou d'écriture dès l'entrée : sans lui,
        deux votes simultanés liraient le même score et le dernier écraserait
        le premier — un vote perdu en silence.

        Aucun `ROLLBACK` explicite : une transaction non validée est annulée à
        la fermeture de la connexion, que `_connexion` garantit. L'écrire
        quand même serait du code qu'aucun test ne peut atteindre.
        """
        with self._connexion() as connexion:
            connexion.execute("BEGIN IMMEDIATE")
            yield connexion
            connexion.execute("COMMIT")

    # ------------------------------------------------------------------
    # Les émissions diffusées (SPECS.md §4.11.1)
    # ------------------------------------------------------------------

    def derniere_diffusion(self, emission: str) -> Diffusion | None:
        """Le dernier épisode diffusé d'une émission, ou rien.

        Rendre `None` pour une base vide **est** le comportement nominal : la
        radio diffusera une fois l'épisode le plus récent, puis reprendra son
        cours (ARCHITECTURE.md §5.0).
        """
        with self._connexion() as connexion:
            ligne = connexion.execute(
                "SELECT episode, diffuse_le FROM emissions_diffusees WHERE emission = ?",
                (emission,),
            ).fetchone()
        if ligne is None:
            return None
        return Diffusion(episode=str(ligne[0]), diffuse_le=datetime.fromisoformat(str(ligne[1])))

    def enregistrer_diffusion(self, emission: str, episode: str) -> None:
        """Retient qu'un épisode est passé — au singulier, jamais un historique.

        Une seule ligne par émission : c'est la borne que s'impose
        ARCHITECTURE.md §5.0. Conserver les précédents serait l'historique
        d'antenne que ce projet a décidé de ne pas avoir.
        """
        instant = self._horloge.maintenant().isoformat()
        with self._transaction() as connexion:
            connexion.execute(
                """
                INSERT INTO emissions_diffusees (emission, episode, diffuse_le)
                VALUES (?, ?, ?)
                ON CONFLICT(emission) DO UPDATE
                SET episode = excluded.episode, diffuse_le = excluded.diffuse_le
                """,
                (emission, episode, instant),
            )
        logger.info("émission « %s » : épisode %s retenu comme diffusé", emission, episode)

    # ------------------------------------------------------------------
    # Les votes (SPECS.md §4.12)
    # ------------------------------------------------------------------

    def scores(self, portee: Portee, cible: str) -> Scores:
        """Les scores d'une cible, décroissance appliquée jusqu'à maintenant.

        La décroissance vaut **aussi à la lecture** (ARCHITECTURE.md §5.2) :
        sans elle, un score écrit il y a un an pèserait encore son poids plein
        tant que personne ne revote.
        """
        maintenant = self._horloge.maintenant()
        with self._connexion() as connexion:
            ligne = connexion.execute(
                "SELECT score_stop, score_encore, vu_le FROM votes WHERE portee = ? AND cible = ?",
                (str(portee), cible),
            ).fetchone()
        if ligne is None:
            return Scores()
        ecoule = maintenant - datetime.fromisoformat(str(ligne[2]))
        return Scores(
            stop=_decroitre(float(ligne[0]), ecoule, self._demi_vie),
            encore=_decroitre(float(ligne[1]), ecoule, self._demi_vie),
        )

    def enregistrer_vote(
        self,
        portee: Portee,
        cible: str,
        *,
        stop: float = 0.0,
        encore: float = 0.0,
    ) -> Scores:
        """Applique la décroissance, ajoute l'incrément, et rend le résultat.

        L'adaptateur ne connaît pas le barème : combien pèse un `stop` sur une
        piste et combien sur son artiste est une décision, donc du noyau
        (SPECS.md §4.12). Ici, on additionne ce qu'on nous donne.
        """
        maintenant = self._horloge.maintenant()
        with self._transaction() as connexion:
            ligne = connexion.execute(
                "SELECT score_stop, score_encore, vu_le FROM votes WHERE portee = ? AND cible = ?",
                (str(portee), cible),
            ).fetchone()
            if ligne is None:
                courant = Scores()
            else:
                ecoule = maintenant - datetime.fromisoformat(str(ligne[2]))
                courant = Scores(
                    stop=_decroitre(float(ligne[0]), ecoule, self._demi_vie),
                    encore=_decroitre(float(ligne[1]), ecoule, self._demi_vie),
                )
            nouveaux = Scores(stop=courant.stop + stop, encore=courant.encore + encore)
            connexion.execute(
                """
                INSERT INTO votes (portee, cible, score_stop, score_encore, vu_le)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(portee, cible) DO UPDATE
                SET score_stop = excluded.score_stop,
                    score_encore = excluded.score_encore,
                    vu_le = excluded.vu_le
                """,
                (
                    str(portee),
                    cible,
                    nouveaux.stop,
                    nouveaux.encore,
                    maintenant.isoformat(),
                ),
            )
        return nouveaux
