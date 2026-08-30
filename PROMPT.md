# PROMPT.md — Intention initiale (gelée)

> **Ce fichier ne se met pas à jour.** Il conserve l'intention du projet telle
> qu'elle a été formulée avant qu'une seule ligne ne soit écrite.
>
> Il a servi une fois, pour créer le Harness (Phase 0). Ensuite, les agents
> travaillent depuis [AGENTS.md](./AGENTS.md), [SPECS.md](./SPECS.md),
> [ARCHITECTURE.md](./ARCHITECTURE.md) et [TASKS.md](./TASKS.md).
>
> **Là où une règle applicable a dépassé ce texte, c'est
> [AGENTS.md](./AGENTS.md) qui fait foi.** Les divergences constatées sont
> listées en fin de fichier.

---

## L'objectif, tel que reçu

`/init-project-harness` a été lancée **sans objectif**. Le nom du dossier —
`local-webradio` — a servi d'indice, et trois intentions ont été proposées à
l'auteur. Aucune n'a été retenue telle quelle ; l'auteur a écrit la sienne, que
voici **mot pour mot** :

> L'idée est que ça soit effectivement une webradio dynamique active que si il y
> a des client, pioche en aléatoir dans ma bibliothéque navidrome (mais je veux
> que ça soit modulaire, pour l'instant navidrome mais plus tard d'autre
> source). Il y aura des jingles horaires (fourni en mp3) et des intéruption
> d'information via le flux de France Info (normalement il donne le flash
> accessible). Prévoir que ça soit paramétrable en toml, et également prévoir
> des moment téhmatique avec des moment de pioche aléatoire, mais parfois sur
> des heures données des type de musique spécifique. Prévoire également la
> possibilité d'intégrer du pilotage de flux avec une notion de stop ou encore,
> pour avoir si encore de la musique supplémentaire du même artiste ou du meême
> genre si pas d'autre musique de l'artiste.

## Ce que l'entretien d'initialisation a établi

| Question | Réponse retenue |
|---|---|
| Objectif reformulé, testable | Diffuser un flux HTTP audio unique, démarré à la première connexion et arrêté à la dernière, alimenté par un tirage dans une bibliothèque Navidrome selon une grille horaire thématique, ponctué de jingles horaires et de flashs France Info, configuré en TOML et pilotable par `stop`/`encore` |
| Hors périmètre | Plusieurs flux ou qualités · gérer la bibliothèque · enregistrer, rejouer, podcaster. **L'interface web de gestion n'a pas été exclue** → décision ouverte |
| Auditeurs et contexte | L'auteur seul, sur le réseau local, jamais exposé sur Internet |
| Moteur de diffusion | Serveur HTTP propre + ffmpeg, chaîne démarrée à la demande. Écarté : Liquidsoap + Icecast (diffuse en continu, contredit l'exigence) et l'hybride (latence d'amorçage, cycle de vie à trois processus) |
| Stack | Python 3.11+ · `ruff` · `mypy` · `pytest` |
| Dépendances externes à relever | Navidrome / API Subsonic · le flash France Info · ffmpeg. **Aucune URL de flash n'a été fournie** : à trouver et à confirmer |
| Ce qu'un test ne verra pas | Les quatre : le son lui-même · les transitions · la tenue dans la durée · les vrais lecteurs |
| Langues | Tout en français — code, docstrings, documentation, commits |
| Commande de vérification | `ruff format --check . && ruff check . && mypy . && pytest --cov --cov-fail-under=80` |
| Couverture visée | 80 % sur l'ensemble du dépôt |
| Cas d'arrêt supplémentaires | **Aucun.** Les quatre d'AGENTS.md §1.2 suffisent — y compris pour les tâches audibles |

## Goals définis au démarrage

| Goal | Titre |
|---|---|
| GOAL-001 | Harness et initialisation |
| GOAL-002 | Relever Navidrome, France Info et ffmpeg |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande |
| GOAL-005 | La grille horaire et les moments thématiques |
| GOAL-006 | Jingles horaires et flashs France Info |
| GOAL-007 | Le pilotage : `stop` et `encore` |

Seul `GOAL-001` a été découpé en tâches. Les autres restent des titres : ils
seront découpés par `/goal` le jour où on les entreprend, avec la connaissance du
code d'alors.

## Trois tensions signalées à l'initialisation, non tranchées

1. **L'interface web de gestion** — seule des quatre exclusions proposées à ne
   pas avoir été cochée. Ni dedans, ni dehors. → SPECS.md §7 n°1.
2. **La modularité des sources** — « pour l'instant Navidrome mais plus tard
   d'autres » contredit frontalement l'interdit *une abstraction arrive avec son
   deuxième cas d'usage*. → SPECS.md §7 n°2.
3. **Quatre angles morts, aucun cas d'arrêt pour l'écoute** — les tâches qui
   touchent au son seront cochées sur la foi de tests qui n'entendent rien.
   Choix d'autonomie maximale, assumé. → SPECS.md §7 n°9.

---

## Divergences acceptées

Ce que l'implémentation a fait différemment de ce texte, et pourquoi. La règle
applicable reste celle d'[AGENTS.md](./AGENTS.md).

| Point du prompt | Ce qui a été fait | Raison |
|---|---|---|
| _(vide au démarrage)_ | | |
