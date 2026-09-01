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

Les quarante-trois Goals sont terminés et la table ci-dessous en est le bilan.
Le code est écrit, testé et vérifié, et ce que les tests n'entendent pas a été
**validé à l'écoute par l'auteur** — le 2026-08-30 pour le produit (votes,
saut, encore, flash France Info, YouTube, jingles, interface), puis le
**2026-08-31** pour la vague suivante : le tirage sur la bibliothèque entière
et son cache (GOAL-039/040), la plage au thème tiré au sort (GOAL-037), la
reprise à neuf après une longue pause (GOAL-041), la grille de journée et ses
quinze génériques (GOAL-043).

**Un Goal ouvert : GOAL-050** (le fondu à la prise d'antenne, ci-dessous).
Décisions restantes de SPECS.md §7 : la **n°9** est une
conséquence consignée, non une question ; la **n°12** (combiner plusieurs
sources actives) est délibérément différée jusqu'à la deuxième source de
musique.

**Plus rien à écouter.** Les deux dernières écoutes — GOAL-044, les trois
modes d'enchaînement et la fenêtre de non-répétition qui reprend après chaque
suite ; GOAL-047, la coupe d'une piste longue au plafond et son fondu — ont
été **validées par l'auteur le 2026-09-01**.

**Prochaine tâche** : `GOAL-050-T01`.

---

## GOAL-050 — Un fondu à la prise d'antenne `[-]`

**Ouvert le 2026-09-01.** Demandé par l'auteur : un auditeur qui se connecte ne
doit pas prendre le son en pleine face.

Le flux est encodé une seule fois et partagé (`output.harbor`) : un fondu par
auditeur n'existe pas. Le cas réel est la **prise d'antenne** — quand le
premier auditeur se branche, le `switch` bascule de `blank()` au programme au
milieu du morceau, plein volume. C'est cette bascule qu'on fond.

- [x] `GOAL-050-T01` Relevé : les `transitions` de `switch` et `fade.in` en
      v2.3.3 sur la bascule `blank()` → programme, constaté à l'exécution
      (enveloppe RMS, conteneur épinglé), consigné dans `docs/liquidsoap.md`
      §8 — `fade.in` ne fond pas une source entamée, `amplify` armé par la
      transition fond ; un fondu par auditeur est impossible
- [x] `GOAL-050-T02` `radio.liq` : le fondu à la prise d'antenne — transition
      qui arme, `amplify` qui monte en 2 s ; `amplify` constaté accepté sur la
      structure complète, `input.http` compris ; test du script à jour ;
      **reste l'écoute réelle** — la montée du volume au branchement du
      premier auditeur
- [-] `GOAL-050-T03` SPECS.md, clôture et archive — la carte du dépôt ne
      change pas

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
| GOAL-037 | Une plage dont le genre ou l'artiste est tiré au sort | `[x]` — écoute validée le 2026-08-31 |
| GOAL-038 | Le Compose de production tire l'image publiée ; un Compose de dev construit localement | `[x]` |
| GOAL-039 | Parler Subsonic plutôt que Navidrome, et tirer dans toute la bibliothèque | `[x]` — écoute validée le 2026-08-31 |
| GOAL-040 | Un cache de bibliothèque dans l'adaptateur Subsonic | `[x]` |
| GOAL-041 | Péremption des jingles horaires, et reprise à neuf après une longue pause | `[x]` — écoute validée le 2026-08-31 |
| GOAL-042 | Le Planning s'ouvre sur aujourd'hui, créneau en cours visible, jours repliés | `[x]` |
| GOAL-043 | Une grille de journée complète, et un atelier à jingles en conteneur | `[x]` — écoute validée le 2026-08-31 |
| GOAL-044 | Les modes d'enchaînement des plages : double dose, époque, artiste | `[x]` — écoute validée le 2026-09-01 |
| GOAL-045 | Une chanson trop longue n'est jamais diffusée | `[x]` — n°32 révisée par GOAL-047 |
| GOAL-046 | Le mode d'une plage se voit dans le Planning | `[x]` |
| GOAL-047 | Une chanson trop longue se joue, mais se coupe en fondu au plafond | `[x]` — écoute validée le 2026-09-01 |
| GOAL-048 | Un libellé trop long du Planning se tronque en ellipse | `[x]` |
| GOAL-049 | Tirage par genre fiable malgré les genres fantômes de Navidrome | `[x]` — clos le 2026-09-01 : diagnostic consigné (T01), le reste abandonné — la bibliothèque a été purgée, T03 annulée par revert |
| GOAL-050 | Un fondu à la prise d'antenne | `[-]` |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).

