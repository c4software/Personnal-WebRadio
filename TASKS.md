# TASKS.md — Feuille de route et avancement réel

La mémoire persistante du projet. Un agent qui arrive doit pouvoir lire ce seul
fichier et comprendre **où le travail s'est arrêté**.

Documents liés : [AGENTS.md](./AGENTS.md) (les règles) ·
[SPECS.md](./SPECS.md) (le quoi) · [ARCHITECTURE.md](./ARCHITECTURE.md) (le
comment).

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

---

## Phase courante

**Phase 0 — Harness** `[-]` en cours.

La documentation structurante et les commandes de pilotage sont posées.
**Le code n'existe pas encore** : `GOAL-001-T01` à `T04` et `T11` restent à
faire, et la commande de vérification n'a donc jamais été exécutée avec succès —
elle n'a rien à vérifier.

**Prochaine tâche** : `GOAL-001-T01` — constater l'existant et arrêter la stack.

---

## Vue d'ensemble

| Goal | Titre | État |
|---|---|---|
| GOAL-001 | Harness et initialisation | `[-]` |
| GOAL-002 | Relever Navidrome, France Info et ffmpeg | `[ ]` |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture | `[ ]` |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[ ]` |
| GOAL-005 | La grille horaire et les moments thématiques | `[ ]` |
| GOAL-006 | Jingles horaires et flashs France Info | `[ ]` |
| GOAL-007 | Le pilotage : `stop` et `encore` | `[ ]` |

---

## GOAL-001 — Harness et initialisation

**État : EN COURS**

Mise en place du dépôt, de sa documentation et des commandes de pilotage. Aucune
fonctionnalité de la radio — hormis le squelette exécutable de `T02`, sans lequel
`/verify` n'aurait rien à vérifier.

- [ ] `GOAL-001-T01` Constater l'existant et arrêter la stack (Python, version, gestionnaire de dépendances)
- [ ] `GOAL-001-T02` Squelette exécutable : `pyproject.toml`, `webradio/{core,adapters,app}/`, `tests/`, un point d'entrée qui démarre et s'arrête proprement
- [ ] `GOAL-001-T03` Outillage qualité : `ruff` (format + analyse), `mypy` strict, `pytest` + `pytest-cov` à 80 %
- [ ] `GOAL-001-T04` **Prouver la chaîne de vérification** : écrire un test qui échoue, une violation de style et une erreur de type ; constater que la commande sort en erreur sur chacune ; puis les corriger et constater qu'elle passe
- [x] `GOAL-001-T05` Rédiger `SPECS.md`
- [x] `GOAL-001-T06` Rédiger `ARCHITECTURE.md`
- [x] `GOAL-001-T07` Rédiger `AGENTS.md`
- [x] `GOAL-001-T08` Rédiger `TASKS.md`, `CONTRIBUTING.md`, `README.md`, `CLAUDE.md`
- [x] `GOAL-001-T09` Installer `/goal`, `/task`, `/status`, `/verify` et `.claude/settings.json`
- [x] `GOAL-001-T10` Ouvrir les relevés `docs/{navidrome,franceinfo,ffmpeg}.md` avec **les questions auxquelles GOAL-002 devra répondre**
- [ ] `GOAL-001-T11` Vérification complète passée et **sa sortie constatée**, carte du dépôt (ARCHITECTURE.md §9) mise à jour

> `T05` à `T10` ont été produites par `/init-project-harness`. Elles sont cochées
> parce que les fichiers existent et sont complets — **pas** parce qu'une
> vérification l'a confirmé : il n'y a rien à vérifier tant que `T02` et `T03`
> n'ont pas eu lieu. C'est précisément ce que `T11` constatera.

### Décisions prises

| Décision | Raison |
|---|---|
| Serveur HTTP propre + ffmpeg, plutôt qu'Icecast ou Liquidsoap | Seul choix qui donne littéralement le démarrage à la demande exigé par SPECS.md §1. Le prix — transitions et jingles à écrire — est assumé (ARCHITECTURE.md §4) |
| Python 3.11+ | `tomllib` dans la bibliothèque standard, et l'écosystème audio le plus fourni. Le flux temps réel partagé demandera du soin (ARCHITECTURE.md §4.1) |
| `ruff` + `mypy` strict + `pytest --cov-fail-under=80` | Une seule commande, qui échoue bruyamment, tenant dans une règle de permission |
| Horloge et hasard injectés, chacun dans un module unique | Une radio *est* une grille horaire et un tirage : les lire n'importe où rendrait la moitié du produit intestable (ARCHITECTURE.md §3.1) |
| Aucune persistance | « Ce qui est passé est perdu » (SPECS.md §2). Pas de base, pas de cache, pas d'historique |
| Tout le projet en français | Choix de l'auteur à l'initialisation : code, docstrings, documentation et commits |
| Quatre cas d'arrêt, sans cinquième pour l'écoute | Autonomie maximale, choisie à l'initialisation. Conséquence consignée : SPECS.md §7 n°9 |

### Dettes ouvertes par ce Goal

- [ ] `GOAL-001-T12` **La commande de vérification n'a jamais été exécutée.**
      Le Harness a été livré avant le code qu'il doit vérifier — c'est l'ordre
      voulu, mais cela signifie que rien n'a encore prouvé que
      `ruff format --check . && ruff check . && mypy . && pytest --cov --cov-fail-under=80`
      fonctionne sur cette machine. Levée par `T04` puis `T11`.
- [ ] `GOAL-001-T13` **Les interdits d'AGENTS.md §2 n'ont aucun contrôle
      exécutable.** `/verify` §5 les décrit en `grep`, mais aucun script ne les
      lance. Tant que le code n'existe pas, ils ne coûtent rien ; dès `GOAL-003`,
      ils doivent être vérifiés à chaque passage.
- [ ] `GOAL-001-T14` **Neuf décisions restent ouvertes** dans SPECS.md §7. Deux
      bloquent un Goal précis et devront être tranchées avant lui : la n°2
      (modularité des sources) avant `GOAL-002`, la n°3 (règle de
      non-répétition) avant `GOAL-003`.

---

## GOAL-002 — Relever Navidrome, France Info et ffmpeg

**État : TODO** — non découpé.

Trois relevés à établir **par observation**, avant toute implémentation
(AGENTS.md §3). Les fichiers `docs/*.md` existent déjà et portent les questions ;
ce Goal y répond.

Il ouvre sur la décision **SPECS.md §7 n°2** — jusqu'où pousser la modularité des
sources — qui doit être tranchée avant d'écrire le client Navidrome.

---

## GOAL-003 — Le noyau : horloge, hasard, file de lecture

**État : TODO** — non découpé.

`core/clock.py`, `core/rng.py`, la file de lecture et la règle de
non-répétition. Aucune E/S : c'est ici que se vérifie l'interdit central
d'AGENTS.md §2.

Exige que **SPECS.md §7 n°3** (la règle de non-répétition exacte) soit tranchée.

---

## GOAL-004 — Le flux : ffmpeg, fan-out, démarrage à la demande

**État : TODO** — non découpé.

Le serveur HTTP, le sous-processus ffmpeg, le fan-out d'un flux unique vers N
connexions, et surtout le **cycle de vie** : démarrage à la première connexion,
arrêt à la dernière, y compris sur déconnexion brutale (SPECS.md §4.7).

Premier Goal dont le résultat ne peut être constaté qu'en **écoutant**
(AGENTS.md §4.1).

---

## GOAL-005 — La grille horaire et les moments thématiques

**État : TODO** — non découpé.

La lecture du TOML, les plages horaires, la contrainte de genre, et le repli sur
le tirage libre quand une plage n'a rien à offrir (SPECS.md §4.4).

---

## GOAL-006 — Jingles horaires et flashs France Info

**État : TODO** — non découpé.

L'insertion à la jonction sans couper un morceau, la péremption
(SPECS.md §7 n°4), et le repli sur la musique quand un jingle ou un flash manque.

---

## GOAL-007 — Le pilotage : `stop` et `encore`

**État : TODO** — non découpé.

L'effet de `stop` et `encore` dans le noyau, puis leur forme — qui dépend de
**SPECS.md §7 n°6**, elle-même liée à la n°1 (interface web ou non).
