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

from webradio.core.clock import Clock

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


class StateUnavailable(Exception):
    """La base existe mais ne se laisse ni lire ni écrire.

    Traduite au plus près de son origine : au-dessus de cet adaptateur, plus
    personne ne connaît `sqlite3` (ARCHITECTURE.md §7).
    """


class Scope(StrEnum):
    """Sur quoi porte un vote (SPECS.md §7 n°16).

    Un `StrEnum` plutôt qu'une chaîne libre : la valeur est écrite telle quelle
    dans la colonne `portee`, et une faute de frappe y créerait silencieusement
    une troisième portée que personne ne relirait jamais.
    """

    TRACK = "piste"
    ARTIST = "artiste"


@dataclass(frozen=True, slots=True)
class Broadcast:
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


def _decroitre(score: float, ecoule: timedelta, half_life: timedelta) -> float:
    """`score * 2 ** (-Δt / demi_vie)` — l'oubli de SPECS.md §4.12.

    Un `Δt` négatif — horloge reculée, fichier recopié d'une autre machine —
    ne fait pas grossir un score : on rend la valeur telle quelle.
    """
    if ecoule <= timedelta(0):
        return score
    return float(score * 2.0 ** (-(ecoule / half_life)))


class SqliteState:
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
        path: Path,
        clock: Clock,
        *,
        lock_timeout: timedelta,
        vote_half_life: timedelta,
    ) -> None:
        """`delai_attente` et `demi_vie_votes` viennent du TOML (SPECS.md §6.2).

        Aucun défaut n'est écrit ici : une durée en dur dans le code est un
        interdit (AGENTS.md §2), et le défaut se déclare là où la clé est
        documentée.
        """
        if lock_timeout <= timedelta(0):
            message = "un délai d'attente nul rendrait toute écriture concurrente perdante"
            raise ValueError(message)
        if vote_half_life <= timedelta(0):
            message = "une demi-vie nulle ou négative ne définit aucune décroissance"
            raise ValueError(message)
        self._chemin = path
        self._horloge = clock
        self._delai_attente = lock_timeout
        self._demi_vie = vote_half_life
        self._preparer()

    def _preparer(self) -> None:
        """Crée le fichier, son dossier et le schéma s'ils manquent.

        Il n'y a pas de migration : le schéma se crée ou existe déjà. Le perdre
        n'étant pas une panne, il n'y a rien à faire évoluer.
        """
        self._chemin.parent.mkdir(parents=True, exist_ok=True)
        with self._connexion() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA)

    @contextmanager
    def _connexion(self) -> Iterator[sqlite3.Connection]:
        """Une connexion en WAL, avec le délai d'attente déclaré.

        WAL parce qu'un lecteur ne doit pas attendre un écrivain : le serveur
        web lit pendant que la chaîne écrit, et l'inverse.
        """
        try:
            connection = sqlite3.connect(
                self._chemin,
                timeout=self._delai_attente.total_seconds(),
                isolation_level=None,
            )
        except sqlite3.Error as error:
            message = f"base d'état inaccessible : {self._chemin}"
            raise StateUnavailable(message) from error
        try:
            yield connection
        except sqlite3.Error as error:
            message = f"base d'état illisible ou verrouillée : {self._chemin}"
            raise StateUnavailable(message) from error
        finally:
            connection.close()

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
        with self._connexion() as connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")

    # ------------------------------------------------------------------
    # Les émissions diffusées (SPECS.md §4.11.1)
    # ------------------------------------------------------------------

    def last_airing(self, show: str) -> Broadcast | None:
        """Le dernier épisode diffusé d'une émission, ou rien.

        Rendre `None` pour une base vide **est** le comportement nominal : la
        radio diffusera une fois l'épisode le plus récent, puis reprendra son
        cours (ARCHITECTURE.md §5.0).
        """
        with self._connexion() as connection:
            row = connection.execute(
                "SELECT episode, diffuse_le FROM emissions_diffusees WHERE emission = ?",
                (show,),
            ).fetchone()
        if row is None:
            return None
        return Broadcast(episode=str(row[0]), diffuse_le=datetime.fromisoformat(str(row[1])))

    def record_airing(self, show: str, episode: str) -> None:
        """Retient qu'un épisode est passé — au singulier, jamais un historique.

        Une seule ligne par émission : c'est la borne que s'impose
        ARCHITECTURE.md §5.0. Conserver les précédents serait l'historique
        d'antenne que ce projet a décidé de ne pas avoir.
        """
        instant = self._horloge.now().isoformat()
        with self._transaction() as connection:
            connection.execute(
                """
                INSERT INTO emissions_diffusees (emission, episode, diffuse_le)
                VALUES (?, ?, ?)
                ON CONFLICT(emission) DO UPDATE
                SET episode = excluded.episode, diffuse_le = excluded.diffuse_le
                """,
                (show, episode, instant),
            )
        logger.info("émission « %s » : épisode %s retenu comme diffusé", show, episode)

    # ------------------------------------------------------------------
    # Les votes (SPECS.md §4.12)
    # ------------------------------------------------------------------

    def scores(self, scope: Scope, target: str) -> Scores:
        """Les scores d'une cible, décroissance appliquée jusqu'à maintenant.

        La décroissance vaut **aussi à la lecture** (ARCHITECTURE.md §5.2) :
        sans elle, un score écrit il y a un an pèserait encore son poids plein
        tant que personne ne revote.
        """
        now = self._horloge.now()
        with self._connexion() as connection:
            row = connection.execute(
                "SELECT score_stop, score_encore, vu_le FROM votes WHERE portee = ? AND cible = ?",
                (str(scope), target),
            ).fetchone()
        if row is None:
            return Scores()
        ecoule = now - datetime.fromisoformat(str(row[2]))
        return Scores(
            stop=_decroitre(float(row[0]), ecoule, self._demi_vie),
            encore=_decroitre(float(row[1]), ecoule, self._demi_vie),
        )

    def all_scores(self) -> list[tuple[Scope, str, Scores]]:
        """Toutes les cibles votées, décroissance appliquée, plus fortes d'abord.

        C'est la matière de la page des votes : elle montre ce que la radio a
        retenu **aujourd'hui**, pas ce qui a été écrit un jour — d'où la
        décroissance ici aussi (ARCHITECTURE.md §5.2).
        """
        now = self._horloge.now()
        with self._connexion() as connection:
            rows = connection.execute(
                "SELECT portee, cible, score_stop, score_encore, vu_le FROM votes"
            ).fetchall()
        entries = [
            (
                Scope(str(row[0])),
                str(row[1]),
                Scores(
                    stop=_decroitre(
                        float(row[2]), now - datetime.fromisoformat(str(row[4])), self._demi_vie
                    ),
                    encore=_decroitre(
                        float(row[3]), now - datetime.fromisoformat(str(row[4])), self._demi_vie
                    ),
                ),
            )
            for row in rows
        ]
        entries.sort(key=lambda e: e[2].stop + e[2].encore, reverse=True)
        return entries

    def record_vote(
        self,
        scope: Scope,
        target: str,
        *,
        stop: float = 0.0,
        encore: float = 0.0,
    ) -> Scores:
        """Applique la décroissance, ajoute l'incrément, et rend le résultat.

        L'adaptateur ne connaît pas le barème : combien pèse un `stop` sur une
        piste et combien sur son artiste est une décision, donc du noyau
        (SPECS.md §4.12). Ici, on additionne ce qu'on nous donne.
        """
        now = self._horloge.now()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT score_stop, score_encore, vu_le FROM votes WHERE portee = ? AND cible = ?",
                (str(scope), target),
            ).fetchone()
            if row is None:
                courant = Scores()
            else:
                ecoule = now - datetime.fromisoformat(str(row[2]))
                courant = Scores(
                    stop=_decroitre(float(row[0]), ecoule, self._demi_vie),
                    encore=_decroitre(float(row[1]), ecoule, self._demi_vie),
                )
            nouveaux = Scores(stop=courant.stop + stop, encore=courant.encore + encore)
            connection.execute(
                """
                INSERT INTO votes (portee, cible, score_stop, score_encore, vu_le)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(portee, cible) DO UPDATE
                SET score_stop = excluded.score_stop,
                    score_encore = excluded.score_encore,
                    vu_le = excluded.vu_le
                """,
                (
                    str(scope),
                    target,
                    nouveaux.stop,
                    nouveaux.encore,
                    now.isoformat(),
                ),
            )
        return nouveaux
