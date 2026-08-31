# TASKS.md — Feuille de route et avancement réel

La mémoire persistante du projet. Un agent qui arrive doit pouvoir lire ce seul
fichier et comprendre **où le travail s'est arrêté**.

Documents liés : [AGENTS.md](./AGENTS.md) (les règles) ·
[SPECS.md](./SPECS.md) (le quoi) · [ARCHITECTURE.md](./ARCHITECTURE.md) (le
comment) · [TASKS.archive.md](./TASKS.archive.md) (l'histoire des Goals
terminés).

---

## Conventions

| Marque | État |
|---|---|
| `[ ]` | TODO — pas commencé |
| `[-]` | EN COURS — commencé, **jamais supposé terminé** |
| `[x]` | TERMINÉ — code **et** tests **et** vérification constatée |
| `[!]` | BLOQUÉ — la raison est écrite juste en dessous |

Identifiants : `GOAL-00X` pour un Goal, `GOAL-00X-TYY` pour une tâche. Ils sont
**stables** : une tâche abandonnée est barrée, jamais renumérotée. Les messages
de commit les référencent (AGENTS.md §7).

Rappel (AGENTS.md §1.1) : `code écrit ≠ tâche terminée`.

**L'archivage fait partie de la clôture.** Quand un Goal passe entièrement à
`[x]`, son détail — tâches, décisions, dettes — part en fin de
[TASKS.archive.md](./TASKS.archive.md), et seule sa ligne de la table de vue
d'ensemble reste ici. Les incidents consignés suivent le même chemin une fois
leur leçon inscrite dans [AGENTS.md](./AGENTS.md). C'est ce qui garde ce
fichier assez court pour être lu à chaque session.

---

## Phase courante

**Phase 2 — Le produit** `[x]` **terminée le 2026-08-30.**

Les trente-sept Goals sont terminés et la table ci-dessous en est le bilan. Le
code est écrit, testé et vérifié, et ce que les tests n'entendent pas —
votes, saut, encore, flash France Info, YouTube, jingles, interface — a été
**validé à l'écoute par l'auteur le 2026-08-30**, au terme d'une soirée en
conditions réelles.

**Goal ouvert** : GOAL-038 — le Compose de production tire l'image publiée,
un Compose de dev construit localement.

Décisions restantes de SPECS.md §7 : la **n°9** est une
conséquence consignée, non une question ; la **n°12** (combiner plusieurs
sources actives) est délibérément différée jusqu'à la deuxième source de
musique.

**Reste à écouter** : GOAL-037 a été codé et vérifié le 2026-08-31, mais
qu'une heure d'un artiste tiré au sort tienne — fenêtre de non-répétition
rétrécie comprise — ne se constate qu'à l'antenne (AGENTS.md §4.1).

**Prochaine tâche** : `GOAL-038-T01`.

---

## Vue d'ensemble

| Goal | Titre | État |
|---|---|---|
| GOAL-001 | Harness et initialisation | `[x]` |
| GOAL-002 | Relever les cinq dépendances externes | `[x]` |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture | `[x]` |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[x]` |
| GOAL-005 | La grille horaire et les moments thématiques | `[x]` |
| GOAL-006 | Jingles horaires | `[x]` |
| GOAL-007 | Le pilotage : `stop` et `encore` dans le noyau | `[x]` |
| GOAL-008 | L'API de pilotage | `[x]` |
| GOAL-009 | L'interface web — Flask et Jinja2 | `[x]` |
| GOAL-010 | Les émissions : podcasts programmés | `[x]` |
| GOAL-011 | Conteneurisation : Docker et Compose | `[x]` |
| GOAL-012 | Les votes pondèrent les tirages suivants | `[x]` |
| GOAL-013 | Les programmes : une playlist, des jours, des heures | `[x]` |
| GOAL-014 | Correctifs de la relecture du 2026-08-30 | `[x]` — T01 corrigée ; T02–T07 supprimés avec leur code par GOAL-016 |
| GOAL-015 | Un direct comme émission — dont le flash France Info | `[x]` |
| GOAL-016 | Migration vers Liquidsoap : le noyau décide, Liquidsoap diffuse | `[x]` |
| GOAL-017 | `stop` ne passe pas le morceau en cours | `[x]` — fondu validé à l'oreille |
| GOAL-018 | L'interface en Vue, et la page des votes | `[x]` |
| GOAL-019 | Les plages thématiques par jour | `[x]` |
| GOAL-020 | Les votes portent un libellé lisible | `[x]` |
| GOAL-021 | Effacer un vote, l'onglet Planning, et le bouton qui ne cliquait pas | `[x]` |
| GOAL-022 | Fondu court des jingles, et le moment présent à l'antenne | `[x]` |
| GOAL-023 | Une plage peut imposer un artiste | `[x]` |
| GOAL-024 | `encore` force réellement le même artiste | `[x]` |
| GOAL-025 | Une chaîne YouTube comme émission | `[x]` |
| GOAL-026 | Les votes ne portent que sur l'artiste (n°16 révisée) | `[x]` |
| GOAL-027 | Le journal des titres, visible dans l'interface | `[x]` |
| GOAL-028 | YouTube sans blanc : téléchargé en fond, servi en local | `[x]` |
| GOAL-029 | Génériques d'ouverture et de fermeture des moments | `[x]` |
| GOAL-030 | Les jours de la configuration passent à l'anglais | `[x]` |
| GOAL-031 | Le jingle d'« encore » se configure, les exemples ont leurs génériques | `[x]` |
| GOAL-032 | Les jingles horaires rangés dans `hours/` | `[x]` |
| GOAL-033 | Les variantes de jingles, tirées au hasard | `[x]` |
| GOAL-034 | L'encore agit sur la chanson suivante, l'avance est réinsérée | `[x]` |
| GOAL-035 | « À suivre » : la file s'affiche à l'antenne | `[x]` |
| GOAL-036 | La CI : vérification puis image publiée sur GHCR | `[x]` |
| GOAL-037 | Une plage dont le genre ou l'artiste est tiré au sort | `[x]` — reste l'écoute réelle |
| GOAL-038 | Le Compose de production tire l'image publiée ; un Compose de dev construit localement | `[ ]` |

Le détail de chacun — sauf les Goals encore ouverts, détaillés ci-dessous — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).

---

## GOAL-038 — Le Compose de production tire l'image publiée ; un Compose de dev construit localement

La CI publie déjà l'image du service `radio` sur GHCR à chaque poussée vérifiée
sur `master` (GOAL-036). Le `docker-compose.yml` continuait pourtant de
construire localement, la bascule n'étant qu'un commentaire. Ce Goal inverse le
défaut : la production tire l'image publiée, et le développement — qui a besoin
de construire le code en cours — passe par une surcharge explicite.

**Décision** : une surcharge `-f docker-compose.dev.yml` plutôt qu'un
`docker-compose.override.yml`, que Compose chargerait automatiquement — un
`docker compose up` chez un utilisateur reconstruirait alors en local, l'inverse
de l'objectif.

- [x] `GOAL-038-T01` `docker-compose.yml` référence `ghcr.io/c4software/personnal-webradio:latest` au lieu de `build: .` ; README (« Lancer », note `docker login ghcr.io`) ajusté ; validé par `docker compose config -q`
- [ ] `GOAL-038-T02` `docker-compose.dev.yml` : surcharge minimale (`build: .`, image `local-webradio:dev`) ; documentation dev (README, CONTRIBUTING), ARCHITECTURE §8.5 et carte du dépôt §9 ; validé par `docker compose -f docker-compose.yml -f docker-compose.dev.yml config -q`
