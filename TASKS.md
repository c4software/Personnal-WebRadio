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

Les trente-six Goals sont terminés et la table ci-dessous en est le bilan. Le
code est écrit, testé et vérifié, et ce que les tests n'entendent pas —
votes, saut, encore, flash France Info, YouTube, jingles, interface — a été
**validé à l'écoute par l'auteur le 2026-08-30**, au terme d'une soirée en
conditions réelles.

**Un Goal ouvert : GOAL-037** (ci-dessous). Décisions restantes de SPECS.md §7 :
la **n°9** est une conséquence consignée, non une question ; la **n°12**
(combiner plusieurs sources actives) est délibérément différée jusqu'à la
deuxième source de musique.

**Prochaine tâche** : `GOAL-037-T01`.

---

## GOAL-037 — Une plage dont le genre ou l'artiste est tiré au sort

**État : EN COURS** — demandé par l'auteur le 2026-08-31, plan validé le même
jour.

Une plage `[[bands]]` peut déclarer `random = "genre"` ou `random = "artist"`
au lieu d'énumérer ses valeurs : la radio tire elle-même un genre (ou un
artiste) de la bibliothèque **au début de l'occurrence**, et s'y tient jusqu'à
la fin de la plage. L'occurrence suivante retire.

Choix validés par l'auteur : greffé sur `[[bands]]` (pas un 4ᵉ mécanisme, pas
une émission) ; tirage **figé sur l'occurrence** ; réservoir = **toute la
bibliothèque** (genre : `source.genres()` ; artiste : l'artiste d'une piste
tirée librement — aucune capacité nouvelle au `Protocol`) ; la configuration
**déclare** si c'est un genre ou un artiste. Aucune persistance : le tirage vit
en mémoire, une occurrence à la fois.

- [x] `GOAL-037-T01` `Band.random_theme` + invariant révisé (exactement un de
  `genres`/`artists`/`random_theme`), et `Band.occurrence_start(instant)` —
  le début de l'occurrence courante, minuit enjambé compris
- [x] `GOAL-037-T02` `core/mystery.py` : `RandomTheme(source, random)` tire la
  contrainte de l'occurrence, la mémorise (une seule entrée), rend `None` sans
  mémoriser sur `SourceUnavailable` ou réservoir vide — retentera à la
  jonction suivante, journalisé une fois
- [x] `GOAL-037-T03` Brancher : `Schedule.constraint_to_draw` délègue les
  plages `random_theme` au résolveur injecté ; câblage dans `app/main.py`
- [ ] `GOAL-037-T04` Le TOML : clé `random` sur `[[bands]]`, validation
  (`genres`/`artists`/`random` s'excluent), message de refus explicite
- [ ] `GOAL-037-T05` Ce qui se voit : `moment_courant()` nomme le thème tiré
  (« Moment · Air (au hasard) ») ; le planning statique affiche « Au hasard ·
  un artiste » — **à écouter** : qu'une heure d'un artiste tiré au sort tienne,
  fenêtre de non-répétition rétrécie comprise (AGENTS.md §4.1)
- [ ] `GOAL-037-T06` La doc, même incrément : SPECS.md §4.4 + §6 + décision
  n°28, `webradio.exemple.toml`, README ; carte du dépôt (ARCHITECTURE.md §9)
  pour `core/mystery.py`

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
| GOAL-037 | Une plage dont le genre ou l'artiste est tiré au sort | `[-]` |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).
