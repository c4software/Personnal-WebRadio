"""L'état durable du projet, dans SQLite.

SQLite plutôt qu'un fichier JSON parce que deux processus écrivent en même temps
(ARCHITECTURE.md §5.1) : la chaîne de diffusion enregistre l'épisode d'une
émission, le serveur Flask lit et écrit les votes. SQLite fournit l'écriture
atomique et la lecture concurrente, un JSON demanderait de les réécrire.

Perdre cette base n'est pas une panne (ARCHITECTURE.md §5.0) : absente ou vide,
elle vaut « rien n'a jamais été diffusé » et poids neutres. Elle se crée seule,
ne se sauvegarde pas et ne se migre pas (une exception, voir `_MIGRATION_LIBELLE`).

Trois tables : le dernier épisode diffusé par émission, le journal des titres
sur vingt-quatre heures (SPECS.md §7 n°27) et les votes. Rien d'autre n'entre
ici sans décision écrite (ARCHITECTURE.md §5.0) : ni statistiques, ni position
de lecture, ni profil.
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

CREATE TABLE IF NOT EXISTS historique (
    joue_le TEXT NOT NULL,
    nature  TEXT NOT NULL,
    titre   TEXT NOT NULL,
    artiste TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS votes (
    portee       TEXT NOT NULL,
    cible        TEXT NOT NULL,
    score_stop   REAL NOT NULL DEFAULT 0,
    score_encore REAL NOT NULL DEFAULT 0,
    vu_le        TEXT NOT NULL,
    libelle      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (portee, cible)
);
"""

# Une base d'avant GOAL-020 n'a pas la colonne `libelle` : on l'ajoute au
# démarrage. C'est la seule migration du projet.
_MIGRATION_LIBELLE = "ALTER TABLE votes ADD COLUMN libelle TEXT NOT NULL DEFAULT ''"


class StateUnavailable(Exception):
    """La base est inaccessible, illisible ou verrouillée.

    Levée à la place de toute erreur `sqlite3` : les couches au-dessus de cet
    adaptateur ne connaissent pas `sqlite3` (ARCHITECTURE.md §7).
    """


class Scope(StrEnum):
    """La portée d'un vote (SPECS.md §7 n°16).

    La valeur est écrite telle quelle dans la colonne `portee` ; un `StrEnum`
    évite qu'une faute de frappe y crée une portée que personne ne relira.
    """

    TRACK = "piste"
    ARTIST = "artiste"


@dataclass(frozen=True, slots=True)
class Broadcast:
    """Le dernier épisode diffusé d'une émission, et quand.

    `diffuse_le` sert au diagnostic seulement (ARCHITECTURE.md §5.1). Aucune
    règle ne doit s'appuyer dessus, sinon perdre la base ne serait plus anodin.
    """

    episode: str
    diffuse_le: datetime


@dataclass(frozen=True, slots=True)
class Scores:
    """Les deux scores d'une cible, décroissance déjà appliquée.

    Des réels et non des compteurs : la décroissance de SPECS.md §4.12 est
    portée par le score lui-même. Des entiers avec une seule date compteraient
    tous les anciens votes comme frais.
    """

    stop: float = 0.0
    encore: float = 0.0


def _decroitre(score: float, ecoule: timedelta, half_life: timedelta) -> float:
    """Applique `score * 2 ** (-ecoule / half_life)` (SPECS.md §4.12).

    Un `ecoule` négatif (horloge reculée, fichier copié d'une autre machine)
    rend le score inchangé plutôt que de le faire grossir.
    """
    if ecoule <= timedelta(0):
        return score
    return float(score * 2.0 ** (-(ecoule / half_life)))


class SqliteState:
    """L'état durable, avec une connexion ouverte et fermée par opération.

    Flask sert plusieurs requêtes en parallèle et la chaîne écrit depuis un
    autre processus. Une connexion partagée entre fils obligerait à désactiver
    `check_same_thread` et à sérialiser soi-même. Le coût d'ouverture est
    négligeable pour une écriture par titre diffusé.
    """

    def __init__(
        self,
        path: Path,
        clock: Clock,
        *,
        lock_timeout: timedelta,
        vote_half_life: timedelta,
    ) -> None:
        """`lock_timeout` et `vote_half_life` viennent du TOML (SPECS.md §6.2).

        Pas de défaut ici : une durée en dur est interdite (AGENTS.md §2), le
        défaut se déclare avec la clé dans `adapters/config/schema.py`.
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
        """Crée le dossier, le fichier et le schéma s'ils manquent.

        Ajoute la colonne `libelle` des votes à une base d'avant GOAL-020.
        Idempotent.
        """
        self._chemin.parent.mkdir(parents=True, exist_ok=True)
        with self._connexion() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(SCHEMA)
            colonnes = [row[1] for row in connection.execute("PRAGMA table_info(votes)")]
            if "libelle" not in colonnes:
                connection.execute(_MIGRATION_LIBELLE)

    @contextmanager
    def _connexion(self) -> Iterator[sqlite3.Connection]:
        """Ouvre une connexion avec le délai d'attente déclaré et la ferme à la sortie.

        Toute erreur `sqlite3` est traduite en `StateUnavailable`. Le mode WAL,
        activé dans `_preparer`, évite qu'un lecteur attende un écrivain.
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
        """Une transaction d'écriture, validée à la sortie.

        `BEGIN IMMEDIATE` prend le verrou d'écriture dès l'entrée. Sans lui,
        deux votes simultanés liraient le même score et le second écraserait
        le premier.

        Pas de `ROLLBACK` explicite : une transaction non validée est annulée
        quand `_connexion` ferme la connexion.
        """
        with self._connexion() as connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")

    # ------------------------------------------------------------------
    # Les émissions diffusées (SPECS.md §4.11.1)
    # ------------------------------------------------------------------

    def last_airing(self, show: str) -> Broadcast | None:
        """Le dernier épisode diffusé d'une émission, ou `None`.

        `None` pour une base vide est le cas nominal : la radio diffuse alors
        l'épisode le plus récent (ARCHITECTURE.md §5.0).
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
        """Retient l'épisode diffusé d'une émission, en remplaçant le précédent.

        Une seule ligne par émission : conserver les précédents serait un
        historique d'antenne, que ARCHITECTURE.md §5.0 exclut.
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

        La décroissance s'applique aussi à la lecture (ARCHITECTURE.md §5.2),
        sinon un vieux score garderait son poids tant que personne ne revote.
        Cible inconnue : scores nuls.
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

    def all_scores(self) -> list[tuple[Scope, str, str, Scores]]:
        """Toutes les cibles votées, décroissance appliquée, scores les plus forts d'abord.

        Sert la page des votes, qui montre les poids actuels et non ceux écrits
        (ARCHITECTURE.md §5.2). Chaque élément : la portée, la cible brute (la
        clé, pour `delete_vote`), le libellé retenu au vote (GOAL-020) ou la
        cible brute pour les votes d'avant la migration, puis les scores.
        """
        now = self._horloge.now()
        with self._connexion() as connection:
            rows = connection.execute(
                "SELECT portee, cible, score_stop, score_encore, vu_le, libelle FROM votes"
            ).fetchall()
        entries = [
            (
                Scope(str(row[0])),
                str(row[1]),
                str(row[5]) or str(row[1]),
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
        entries.sort(key=lambda e: e[3].stop + e[3].encore, reverse=True)
        return entries

    def record_play(self, kind: str, title: str, artist: str = "") -> None:
        """Ajoute un titre au journal et purge ce qui a plus de vingt-quatre heures.

        Ce journal des titres n'est pas l'archive du flux que SPECS.md §2 exclut ;
        il est borné à vingt-quatre heures (SPECS.md §7 n°27).
        """
        now = self._horloge.now()
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO historique (joue_le, nature, titre, artiste) VALUES (?, ?, ?, ?)",
                (now.isoformat(), kind, title, artist),
            )
            connection.execute(
                "DELETE FROM historique WHERE joue_le < ?",
                ((now - timedelta(days=1)).isoformat(),),
            )

    def history(self) -> list[tuple[datetime, str, str, str]]:
        """Le journal, du plus récent au plus ancien."""
        with self._connexion() as connection:
            rows = connection.execute(
                "SELECT joue_le, nature, titre, artiste FROM historique"
                " ORDER BY joue_le DESC, rowid DESC"
            ).fetchall()
        return [(datetime.fromisoformat(str(r[0])), str(r[1]), str(r[2]), str(r[3])) for r in rows]

    def delete_vote(self, scope: Scope, target: str) -> bool:
        """Efface les votes d'une cible. Vrai si une ligne a été supprimée.

        Action manuelle depuis l'interface (GOAL-021), jamais appelée par le
        tirage.
        """
        with self._transaction() as connection:
            cursor = connection.execute(
                "DELETE FROM votes WHERE portee = ? AND cible = ?", (str(scope), target)
            )
        return cursor.rowcount > 0

    def record_vote(
        self,
        scope: Scope,
        target: str,
        *,
        stop: float = 0.0,
        encore: float = 0.0,
        label: str = "",
    ) -> Scores:
        """Applique la décroissance, ajoute les incréments et rend les nouveaux scores.

        Le barème (le poids d'un `stop` sur une piste ou sur son artiste) est
        une décision du noyau (SPECS.md §4.12) ; ici on additionne seulement.
        Un `label` vide ne remplace pas le libellé déjà enregistré.
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
                INSERT INTO votes (portee, cible, score_stop, score_encore, vu_le, libelle)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(portee, cible) DO UPDATE
                SET score_stop = excluded.score_stop,
                    score_encore = excluded.score_encore,
                    vu_le = excluded.vu_le,
                    libelle = CASE WHEN excluded.libelle != '' THEN excluded.libelle
                                   ELSE votes.libelle END
                """,
                (
                    str(scope),
                    target,
                    nouveaux.stop,
                    nouveaux.encore,
                    now.isoformat(),
                    label,
                ),
            )
        return nouveaux
