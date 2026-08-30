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

**Phase 0 — Harness** `[x]` **terminée le 2026-08-30.**

Le squelette se lance, l'outillage est posé, et la chaîne de vérification a été
**prouvée** — onze violations refusées une par une, puis un état propre qui
passe. Sortie constatée : 4 tests, 100 % de couverture, code de sortie 0.

**Phase 1 — Relevés et noyau** `[x]` terminée (`GOAL-002`, `GOAL-003`).

**Phase 2 — Le produit** `[-]` : tout le code des Goals 004 à 013 est écrit,
testé et vérifié (376 tests, 95 % de couverture, constaté le 2026-08-30). Ce
qui reste ouvert ne se teste pas : cinq tâches d'**écoute réelle** et un
**vrai téléphone** — `GOAL-004-T10`, `GOAL-006-T06`, `GOAL-009-T06`,
`GOAL-010-T11`, `GOAL-012-T11`. Elles demandent l'auteur devant la machine —
**mais pas avant `GOAL-014`** : la relecture du 2026-08-30 a trouvé quatre
défauts qui rendraient l'écoute trompeuse (les jingles ne passent jamais).

> **Mise à jour du 2026-08-30 (5)** — l'auteur ajoute les **émissions** : un
> épisode de podcast diffusé à heure dite, une seule à la fois, programmée au
> TOML par `jours` et `heure`. Objet d'un genre nouveau — long, et qui
> **remplace** la programmation au lieu de s'y insérer.
> Ajoute `GOAL-010` et un cinquième relevé `docs/podcast.md`. Ouvre puis tranche
> trois décisions le même jour : **n°13** rattrapage borné à la durée de
> l'épisode, **n°14** l'épisode le plus récent, **n°15** les jingles dus pendant
> une émission sont abandonnés — **seule exception** à « rien n'est jamais
> abandonné ».
>
> **Mise à jour du 2026-08-30 (4)** — les trois dernières décisions bloquantes
> tombent : **n°5** (la grille n'est lue qu'au tirage), **n°8** (tenir puis
> couper en le disant, jamais boucler) et **n°11** (sans coupure > lisible
> partout > économie ; le réencodage permanent est assumé). La recherche de la
> source France Info devient une tâche prioritaire de `GOAL-002`.
> **Plus aucune décision ne bloque un découpage** : les neuf Goals sont
> découpables.
>
> **Mise à jour du 2026-08-30 (3)** — quatre décisions tranchées d'un coup :
> **n°3** (non-répétition : 5 artistes distincts, fenêtre qui rétrécit),
> **n°4** (aucune péremption, rien n'est abandonné pour retard),
> **n°7** (`encore` illimité, outrepasse la n°3),
> **n°2** (abstraction complète des sources — **écart assumé** à l'interdit
> d'anticipation, consigné dans ARCHITECTURE.md §9.1).
> `GOAL-002`, `GOAL-003`, `GOAL-006` et `GOAL-007` sont débloqués. Ouvre la
> **n°12** : comment le tirage combine plusieurs sources actives.
>
> **Mise à jour du 2026-08-30 (2)** — l'auteur tranche la n°10 : **une voix
> suffit**, et l'accusé de réception d'un « encore » n'est plus une note mêlée à
> la musique mais un **jingle `encore.mp3` posé à la jonction**, par le même
> chemin que les jingles horaires. `GOAL-007` est débloqué ; une seule mécanique
> d'insertion reste à écrire, dans `GOAL-006`.
>
> **Mise à jour du 2026-08-30 (1)** — l'auteur a ajouté huit exigences après
> l'initialisation : interface web Flask/Jinja2, actions par API, `stop`/`encore`
> disponibles en permanence sauf pendant un jingle ou un flash, jingles nommés
> `HHh.mp3` en local et sans erreur si absents, note audible sur un vote
> « encore », flux compatible avec tout lecteur de webradio et sans coupure,
> transcodage minimal.
> Elles tranchent les décisions **n°1** et **n°6**, en ouvrent deux —
> **n°10** (que veut dire « vote » ?, tranchée depuis) et **n°11** (transcoder le
> moins contre ne jamais couper, **toujours ouverte**) — et ajoutent `GOAL-008`,
> `GOAL-009` et un quatrième relevé, `docs/flux-icy.md`.

La documentation structurante et les commandes de pilotage sont posées.
**Le code n'existe pas encore** : `GOAL-001-T01` à `T04` et `T11` restent à
faire, et la commande de vérification n'a donc jamais été exécutée avec succès —
elle n'a rien à vérifier.

**Prochaine tâche** : `GOAL-004-T01` — décoder une entrée vers le PCM du flux.

**Les sept lots restants sont découpés** (2026-08-30), soit 71 tâches.
`GOAL-012` s'ajoute en fin de parcours, découpé lui aussi : les trois décisions
qui le bloquaient (n°16 à n°18) ont été tranchées le 2026-08-30.

**Dix lots, 94 tâches ouvertes.** Décisions : **21 tranchées sur 24**. Restent
la n°9 — une conséquence consignée, non une question — et la n°12, différée
jusqu'à la deuxième source de musique.
`GOAL-011` (conteneurisation) s'insère **après `GOAL-004`** : c'est le premier
moment où il y a quelque chose à faire tourner.

**`GOAL-002` est terminé**, les cinq relevés établis. Deux questions restent à
l'auteur : la source du flash France Info (`docs/franceinfo.md` §1.5) et
l'ampleur de la fenêtre de rattrapage des émissions
(`docs/podcast.md` §3.1).

Sur quinze décisions, **treize sont tranchées**. La n°9 est une conséquence
consignée, non une question ; la n°12 est délibérément différée jusqu'à la
deuxième source de musique. **Aucune ne bloque plus un découpage** : les dix
Goals sont découpables.

---

## Vue d'ensemble

| Goal | Titre | État |
|---|---|---|
| GOAL-001 | Harness et initialisation | `[x]` |
| GOAL-002 | Relever les cinq dépendances externes | `[x]` |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture | `[x]` |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[-]` — seule l'écoute réelle reste |
| GOAL-005 | La grille horaire et les moments thématiques | `[x]` |
| GOAL-006 | Jingles horaires | `[-]` — seule l'écoute réelle reste |
| GOAL-007 | Le pilotage : `stop` et `encore` dans le noyau | `[x]` |
| GOAL-008 | L'API de pilotage | `[x]` |
| GOAL-009 | L'interface web — Flask et Jinja2 | `[-]` — seul le vrai téléphone reste |
| GOAL-010 | Les émissions : podcasts programmés | `[-]` — seule l'écoute réelle reste |
| GOAL-011 | Conteneurisation : Docker et Compose | `[x]` |
| GOAL-012 | Les votes pondèrent les tirages suivants | `[-]` — seule l'écoute réelle reste |
| GOAL-013 | Les programmes : une playlist, des jours, des heures | `[x]` |
| GOAL-014 | Correctifs de la relecture du 2026-08-30 | `[x]` — T01 corrigée ; T02–T07 supprimés avec leur code par GOAL-016 |
| GOAL-015 | Un direct comme émission — dont le flash France Info | `[-]` — seule l'écoute réelle reste |
| GOAL-017 | `stop` ne passe pas le morceau en cours | `[x]` — fondu validé à l'oreille |
| GOAL-018 | L'interface en Vue, et la page des votes | `[x]` |
| GOAL-019 | Les plages thématiques par jour | `[x]` |
| GOAL-020 | Les votes portent un libellé lisible | `[x]` |
| GOAL-021 | Effacer un vote, l'onglet Planning, et le bouton qui ne cliquait pas | `[x]` |
| GOAL-022 | Fondu court des jingles, et le moment présent à l'antenne | `[x]` |
| GOAL-023 | Une plage peut imposer un artiste | `[x]` |
| GOAL-024 | `encore` force réellement le même artiste | `[x]` |
| GOAL-025 | Une chaîne YouTube comme émission | `[-]` — seule l'écoute réelle reste |
| GOAL-026 | Les votes ne portent que sur l'artiste (n°16 révisée) | `[x]` |
| GOAL-016 | Migration vers Liquidsoap : le noyau décide, Liquidsoap diffuse | `[-]` — seule l'écoute réelle reste |

---

## GOAL-001 — Harness et initialisation

**État : TERMINÉ**

Mise en place du dépôt, de sa documentation et des commandes de pilotage. Aucune
fonctionnalité de la radio — hormis le squelette exécutable de `T02`, sans lequel
`/verify` n'aurait rien à vérifier.

- [x] `GOAL-001-T01` Constater l'existant et arrêter la stack (Python, version, gestionnaire de dépendances)
- [x] `GOAL-001-T02` Squelette exécutable : `pyproject.toml`, `webradio/{core,adapters,app}/`, `tests/`, un point d'entrée qui démarre et s'arrête proprement
- [x] `GOAL-001-T03` Outillage qualité : `ruff` (format + analyse), `mypy` strict, `pytest` + `pytest-cov` à 80 %
- [x] `GOAL-001-T04` **Prouver la chaîne de vérification** : écrire un test qui échoue, une violation de style et une erreur de type ; constater que la commande sort en erreur sur chacune ; puis les corriger et constater qu'elle passe
- [x] `GOAL-001-T05` Rédiger `SPECS.md`
- [x] `GOAL-001-T06` Rédiger `ARCHITECTURE.md`
- [x] `GOAL-001-T07` Rédiger `AGENTS.md`
- [x] `GOAL-001-T08` Rédiger `TASKS.md`, `CONTRIBUTING.md`, `README.md`, `CLAUDE.md`
- [x] `GOAL-001-T09` Installer `/goal`, `/task`, `/status`, `/verify` et `.claude/settings.json`
- [x] `GOAL-001-T10` Ouvrir les relevés `docs/{navidrome,franceinfo,ffmpeg,flux-icy}.md` avec **les questions auxquelles GOAL-002 devra répondre**
- [x] `GOAL-001-T11` Vérification complète passée et **sa sortie constatée**, carte du dépôt (ARCHITECTURE.md §9) mise à jour

> `T05` à `T10` ont été produites par `/init-project-harness`. Elles sont cochées
> parce que les fichiers existent et sont complets — **pas** parce qu'une
> vérification l'a confirmé : il n'y a rien à vérifier tant que `T02` et `T03`
> n'ont pas eu lieu. C'est précisément ce que `T11` constatera.

### Décisions prises

| Décision | Raison |
|---|---|
| Serveur HTTP propre + ffmpeg, plutôt qu'Icecast ou Liquidsoap | Seul choix qui donne littéralement le démarrage à la demande exigé par SPECS.md §1. Le prix — transitions et jingles à écrire — est assumé (ARCHITECTURE.md §4) |
| Python 3.11+ | `tomllib` dans la bibliothèque standard, et l'écosystème audio le plus fourni. Le flux temps réel partagé demandera du soin (ARCHITECTURE.md §4.1). **Constaté sur cette machine : 3.14.7** |
| `venv` + `pip` de la bibliothèque standard | `uv` était le premier choix, mais il n'est présent que comme **shim mise sans version fixée** : s'en servir aurait exigé de modifier la configuration mise **globale** de la machine. Le Harness ne touche pas à ce qui déborde du dépôt. `venv` + `pip` ne demandent rien et suffisent |
| `ruff` + `mypy` strict + `pytest --cov-fail-under=80` | Une seule commande, qui échoue bruyamment, tenant dans une règle de permission |
| La commande de vérification devient **`./verifier.sh`** | Une forme unique et stable, donc une seule règle de permission. Et surtout, elle porte les **contrôles textuels des interdits d'AGENTS.md §2** que ruff ne sait pas exprimer — ce qui lève `GOAL-001-T13` |
| Horloge et hasard injectés, chacun dans un module unique | Une radio *est* une grille horaire et un tirage : les lire n'importe où rendrait la moitié du produit intestable (ARCHITECTURE.md §3.1) |
| Aucune persistance | « Ce qui est passé est perdu » (SPECS.md §2). Pas de base, pas de cache, pas d'historique |
| Tout le projet en français | Choix de l'auteur à l'initialisation : code, docstrings, documentation et commits |
| Quatre cas d'arrêt, sans cinquième pour l'écoute | Autonomie maximale, choisie à l'initialisation. Conséquence consignée : SPECS.md §7 n°9 |
| Interface web en **Flask**, gabarits en **Jinja2** | Choix de l'auteur, 2026-08-30. Tranche SPECS.md §7 n°1 |
| **Toute action de l'interface passe par l'API** | Tranche SPECS.md §7 n°6. Un second chemin entre la vue et le noyau divergerait de l'API, et c'est celui qu'on ne teste pas qui casse (ARCHITECTURE.md §6) |
| Les jingles nommés `00h.mp3` … `23h.mp3` | Le nom du fichier *est* la programmation : aucune table de correspondance à tenir à jour. Seule exception à « rien en dur » (AGENTS.md §2) |
| Un jingle absent ne signale rien | C'est le mode d'emploi : on ajoute un jingle en déposant un fichier. Distinct d'un fichier corrompu, qui est un incident (SPECS.md §4.3) |
| `stop` et `encore` refusés pendant un jingle ou un flash, **explicitement** | Un refus muet est indistinguable d'une panne et pousse à réessayer (SPECS.md §4.6) |
| **Une voix suffit** pour `encore` : ni quorum, ni fenêtre | SPECS.md §3 ne prévoit qu'un auditeur : un quorum n'aurait rien à compter. Tranche SPECS.md §7 n°10 |
| L'accusé de réception est un **jingle `encore.mp3` à la jonction**, pas une note mêlée | Une seule mécanique d'insertion pour tous les jingles vaut mieux que deux. Le prix — un accusé différé jusqu'à la fin du morceau — est assumé (ARCHITECTURE.md §6.2) |
| `encore.mp3` absent ne signale rien, comme un jingle horaire | Même règle pour tous les jingles : on en ajoute un en déposant un fichier (SPECS.md §4.3, §4.6) |
| Non-répétition : **N artistes distincts**, 5 par défaut, fenêtre qui rétrécit plutôt que de bloquer | Indépendant de la durée des morceaux, donc prévisible et trivial à tester. Tranche SPECS.md §7 n°3 |
| **Aucune péremption** : ni jingle ni flash n'est abandonné pour retard | Un jingle est de l'habillage. Renoncer aurait coûté un seuil, un réglage et des cas limites pour un gain nul. Tranche SPECS.md §7 n°4 |
| Plusieurs jingles dus à la même jonction : **tous, à la suite** — horaires d'abord, `encore.mp3` en dernier | `encore.mp3` annonce le morceau qui suit immédiatement. Lève `GOAL-001-T16` |
| `encore` **illimité**, borné par la bibliothèque, et **outrepasse** la non-répétition | La borne vient des données, pas d'un réglage. Sans cette priorité, les deux règles se contrediraient. Tranche SPECS.md §7 n°7 |
| Sources : **abstraction complète** dès maintenant, une seule écrite | Choix de l'auteur. **Écart assumé** à l'interdit d'anticipation, consigné dans ARCHITECTURE.md §9.1. Tranche SPECS.md §7 n°2, ouvre la n°12 |
| Une plage thématique : **la grille n'est lue qu'au tirage** | Seule option qui n'ajoute aucune règle — ni durées à connaître, ni coupure, ni cas d'échec. Tranche SPECS.md §7 n°5 |
| Pannes en cours : **tenir, puis couper en le disant** | Couper tout de suite rend fragile aux micro-coupures ; boucler rend la panne invisible, contre AGENTS.md §2. Tranche SPECS.md §7 n°8 |
| Flux : **sans coupure > lisible partout > économie** | Une radio économe qui fait décrocher les lecteurs ne remplit pas sa fonction. Tranche SPECS.md §7 n°11 : le réencodage permanent est la voie par défaut, assumée |
| Le flash France Info est **cherché par `GOAL-002`** | Aucune adresse fournie. Point de départ : les flux publics de Radio France. Si rien de fiable, la question remonte (AGENTS.md §1.2) |
| Émission manquée : **rattrapée dans la limite de sa durée** | La durée de l'épisode est une borne naturelle, qui ne se règle pas. Tranche SPECS.md §7 n°13. Coûte un appel au podcast **au branchement**, avant de savoir s'il servira |
| Épisode diffusé : **le plus récent** | Seul choix qui ne rouvre pas l'absence de persistance. Tranche SPECS.md §7 n°14 |
| Jingles dus pendant une émission : **abandonnés** | Une émission remplace la programmation, habillage compris. **Seule exception à « rien n'est jamais abandonné »** — écrite dans SPECS.md §4.3 et §4.11. Tranche SPECS.md §7 n°15 |
| Les émissions déclarées par `jours` + `heure`, sans grammaire de récurrence | Des champs déclaratifs n'exigent aucun analyseur, se testent directement, et couvrent les deux cas demandés. Une grammaire complète n'arrivera pas avant son deuxième cas d'usage (AGENTS.md §2) |
| Cinquième relevé : `docs/podcast.md` | « RSS avec des `enclosure` » est une convention, pas une norme respectée : un flux qui marche ne dit rien du suivant |
| Quatrième relevé : `docs/flux-icy.md` | « Compatible avec tout lecteur de webradio » n'a aucune norme derrière : c'est une convention de fait, à constater lecteur par lecteur |

### Ce que `GOAL-001-T04` a prouvé

Onze violations introduites une par une, chacune **refusée**, puis retirée. Le
tableau dit surtout **quel** mécanisme a refusé — un refus obtenu par le mauvais
mécanisme est un refus qu'on croit avoir.

| Violation | Refusée par |
|---|---|
| Mise en forme qui s'écarte | `ruff format --check` |
| `print()` | `ruff` T20 |
| `except Exception: pass` | `ruff` BLE |
| Fonction sans annotations | `mypy` strict |
| `import httpx` dans le noyau | `mypy` (paquet absent) |
| `datetime.now()` sans fuseau | `ruff` DTZ |
| **`import socket` dans le noyau** | **la garde `verifier.sh`** — ruff et mypy l'acceptent |
| **`datetime.now(tz=UTC)` hors de `clock.py`** | **la garde `verifier.sh`** — ruff et mypy l'acceptent |
| `import random` hors de `rng.py` | la garde `verifier.sh` |
| `flask`/`jinja2` hors de `adapters/web/` | la garde, exercée isolément |
| `TODO` sans tâche | la garde `verifier.sh` |
| Couverture à 64 % | `pytest --cov-fail-under=80` |

**Les deux lignes en gras sont la raison d'être de cette tâche.** `import socket`
et `datetime.now(tz=UTC)` passent sans un mot devant ruff et mypy : sans les
gardes textuelles, le noyau aurait pu ouvrir une connexion et lire l'horloge
système sans que rien ne le signale — et les deux interdits les plus importants
du projet (ARCHITECTURE.md §1.1 et §3.1) n'auraient été que des phrases.

Deux essais ont par ailleurs échoué **avant** d'atteindre leur garde : `httpx` et
`flask` ne sont pas installés, donc mypy s'arrête sur l'import. Ces gardes-là ont
donc été exercées à part, contre des fixtures, pour ne pas se contenter d'un code
de sortie non nul obtenu pour une autre raison.

### Dettes ouvertes par ce Goal

- [x] `GOAL-001-T12` ~~La commande de vérification n'a jamais été exécutée.~~
      **Levée le 2026-08-30** par `T04` (elle refuse onze violations) puis `T11`
      (elle passe sur l'état propre, sortie constatée : 4 tests, 100 % de
      couverture, code de sortie 0).
- [x] `GOAL-001-T13` ~~Les interdits d'AGENTS.md §2 n'ont aucun contrôle
      exécutable.~~ **Levée par `GOAL-001-T03`** : `verifier.sh` les exécute à
      chaque appel — entrée-sortie dans le noyau, horloge, hasard, Flask hors de
      `adapters/web/`, `TODO` sans tâche. `print()`, `except` nu et argument
      ignoré sont attrapés par ruff.
- [ ] `GOAL-001-T14` **Neuf décisions restent ouvertes** dans SPECS.md §7 — deux
      ont été tranchées le 2026-08-30 (n°1 et n°6), deux ont été ouvertes le même
      jour (n°10 et n°11). Trois bloquent un Goal précis :
      la **n°2** (modularité des sources) avant `GOAL-002`,
      Dix ont été tranchées le 2026-08-30 : n°1 à n°8, n°10, n°11. La **n°9**
      n'est pas une question mais une conséquence consignée ; la **n°12** est
      délibérément différée jusqu'à la deuxième source.
      Les **n°13, n°14 et n°15**, ouvertes par les émissions, ont été tranchées
      le même jour. **Aucune décision ne bloque plus un découpage.**
- [x] `GOAL-001-T15` ~~La n°10 est une ambiguïté de spécification.~~ **Levée le
      2026-08-30** : l'auteur a tranché — une voix suffit, et l'accusé de
      réception devient un jingle `encore.mp3` inséré à la jonction plutôt
      qu'une note mêlée à la musique. `GOAL-007` n'est plus bloqué.
- [x] `GOAL-001-T16` ~~Deux jingles dus à la même jonction.~~ **Levée le
      2026-08-30** : tous diffusés à la suite, jingles horaires dans l'ordre
      chronologique puis `encore.mp3` en dernier (SPECS.md §4.3).
- [ ] `GOAL-001-T17` **L'écart d'anticipation sur les sources doit rester
      surveillé.** L'abstraction est écrite sans son deuxième cas d'usage
      (ARCHITECTURE.md §9.1). Trois questions restent délibérément sans réponse
      (SPECS.md §7 n°12) ; **la première réponse devinée en implémentant serait
      une seconde anticipation, celle-là non consignée.** À vérifier à chaque
      Goal touchant `adapters/sources/`.

---

## GOAL-002 — Relever les cinq dépendances externes

**État : TERMINÉ**

Cinq relevés à établir **par observation**, avant toute implémentation
(AGENTS.md §3). Les fichiers `docs/*.md` portent déjà les questions ; ce Goal y
répond.

**Trois sont faisables sur cette machine**, deux dépendent d'accès que le dépôt
n'a pas : un serveur Navidrome avec ses identifiants, et les URL des podcasts.
Le découpage sépare les deux, pour que ce qui peut avancer avance.

### Ce qui ne dépend que de la machine

- [x] `GOAL-002-T01` ffmpeg : copie sans réencodage, et comportement exact en fin de fichier
- [x] `GOAL-002-T02` ffmpeg : alimenter un encodage continu depuis une file inconnue d'avance
- [x] `GOAL-002-T03` ffmpeg : insérer un fichier d'une autre origine (jingle) sans interrompre
- [x] `GOAL-002-T04` ffmpeg : chiffrer le coût d'un réencodage permanent, pour un auditeur et pour cinq
- [x] `GOAL-002-T05` Flux : ce qu'un lecteur reçoit en se branchant **en cours** de diffusion
- [x] `GOAL-002-T06` Flux : ce qui fait décrocher — changement de débit, de fréquence, de canaux, de codec

### Ce qui dépend du réseau

- [x] `GOAL-002-T07` France Info : trouver la source du flash, son format, sa durée, sa fraîcheur

### Ce qui dépend de l'auteur

- [x] `GOAL-002-T08` Navidrome : authentification, tirage, genres, artiste, récupération du son

- [x] `GOAL-002-T09` Podcast : format des flux, fiabilité de la date de publication et de la durée
      > **Bloqué le 2026-08-30 — il manque les flux.** Aucune URL de podcast n'a
      > été fournie. Le relevé ne porte pas sur « les podcasts en général » mais
      > sur **ceux que la radio diffusera**, dont les écarts au format sont
      > précisément ce qu'il faut constater ([docs/podcast.md](./docs/podcast.md)).
      > **Ce qu'il faut pour débloquer** : les URL des émissions voulues.
      > **Ce que ce blocage bloque** : `GOAL-010` entièrement.

### Ce que GOAL-002 a établi

| Constat | Conséquence |
|---|---|
| La voie PCM enchaîne sans blanc, y compris entre formats différents | `concat` et la copie sans réencodage sont écartés |
| Un réencodage permanent coûte **1 % d'un cœur** | **Réencoder systématiquement.** L'optimisation que le relevé cherchait n'existe pas, et le chemin le plus simple est le bon |
| Un jingle est un morceau de plus dans la file | **Un seul chemin d'insertion** pour jingles horaires, jingle de vote et flashs |
| Un tuyau qui se tarit n'insère pas de silence — il fait un trou dans le **temps réel** | Résoudre le morceau suivant **pendant** que le courant joue, jamais à la jonction |
| Sans `-re`, ffmpeg encode ×95 trop vite | Cadencer, ou la radio consomme la bibliothèque en minutes |
| Un auditeur tardif décode sans en-tête initial | L'entrée en cours de route ne demande aucun mécanisme particulier |
| **Deux ffmpeg ont survécu à la dernière déconnexion** | Arrêter la chaîne = arrêter **tout l'arbre**. Un test sur un booléen serait passé au vert |
| Aucune source de flash France Info confirmée | Trois questions remontent à l'auteur |
| Navidrome : un mot de passe faux renvoie **HTTP 200** | Lire `status` dans le corps **à chaque appel** — le code HTTP ne dit rien |
| `getRandomSongs` **tronque à 500 en silence** | Ne jamais demander davantage en croyant l'obtenir |
| `search3` sur un artiste ramène **aussi d'autres artistes** | Filtrer sur l'égalité exacte, sinon `encore` sert un autre artiste |
| **La bibliothèque est hétérogène** : mp3 + m4a, six débits de 96 à 320 | La voie « transmettre tel quel » **n'existait pas**. La décision n°11 était la seule possible |
| `genre` manque sur **37 pistes sur 200** | `genre=None` était nécessaire, pas prudent : le refuser amputait 18 % de la bibliothèque |
| `duration` **toujours présent** | La programmation des jingles peut s'y fier |
| Podcast LEGEND : `pubDate` et `duration` fiables sur **725 épisodes** | Les décisions n°13 et n°14 sont implémentables |
| `itunes:episodeType` distingue `full` de `trailer` | **Ne retenir que `full`** — sinon « le plus récent » peut servir une bande-annonce d'une minute |
| Acast **insère de la publicité à la volée** (`livestitches`) | `enclosure/length` ment de 2 Mo ; `duration` est probablement optimiste de ~2 % |
| Épisodes : médiane **77 min**, maximum **170 min** | **Remonte à l'auteur** : la fenêtre de rattrapage de la n°13 peut atteindre 2 h 50 |

### Ce que GOAL-002 n'a pas pu établir

- **La matrice des vrais lecteurs** — VLC, navigateur, enceinte. Essais menés
  avec `curl` et ffmpeg seulement. C'est un angle mort (AGENTS.md §4.1) et il ne
  se comble pas depuis une session.
- **La matrice des vrais lecteurs** reste le seul manque : elle demande d'être
  devant la machine.

### Clôture

- [x] `GOAL-002-T10` Consolider les cinq relevés, et lister **ce qui reste incertain** — un point incertain n'est jamais remplacé par une supposition

---

## GOAL-003 — Le noyau : horloge, hasard, file de lecture

**État : TERMINÉ**

`core/clock.py`, `core/rng.py`, les modèles, la frontière des sources, la règle
de non-répétition et la file. **Aucune E/S** : c'est ici que se vérifie
l'interdit central d'AGENTS.md §2, et c'est pour cela que ce Goal peut être
écrit alors que `GOAL-002-T08` est bloqué — le noyau ne connaît qu'un `Protocol`,
jamais Navidrome.

- [x] `GOAL-003-T01` `core/clock.py` — l'horloge injectée, et une horloge de test qui avance à volonté
- [x] `GOAL-003-T02` `core/rng.py` — le hasard injecté, graine fixable, une émission qui se rejoue
- [x] `GOAL-003-T03` Les modèles : `Piste`, `Artiste`, `Genre`
- [x] `GOAL-003-T04` `SourceMusicale` — le `Protocol`, et un `FakeSource` versionné
- [x] `GOAL-003-T05` La fenêtre de non-répétition : N artistes distincts
- [x] `GOAL-003-T06` Le rétrécissement de la fenêtre quand elle ne laisse aucun artiste
- [x] `GOAL-003-T07` La file : tirer le morceau suivant, et prendre de l'avance
- [x] `GOAL-003-T08` Mettre à jour la carte du dépôt (ARCHITECTURE.md §9)

**Ce que `GOAL-002` impose à ce Goal** : la file doit **prendre de l'avance** —
résoudre le morceau suivant pendant que le courant joue, jamais à la jonction.
Un tuyau qui se tarit ne fait pas un blanc dans l'audio, il fait un trou dans le
temps réel ([docs/ffmpeg.md](./docs/ffmpeg.md) §2.2).

---

## Incident 2026-08-30 — `git add -A` pendant un travail parallèle

**Ce qui s'est passé.** Quatre agents écrivaient en parallèle dans des
répertoires disjoints, avec pour consigne de ne jamais committer. L'agent
principal, lui, a committé son propre travail (Docker, README) avec
`git add -A` — qui a **emporté au passage** les fichiers que les agents étaient
en train d'écrire.

| Commit | A emporté, sans le dire |
|---|---|
| `72bf772` *build(docker)* | `adapters/config/{__init__,schema}.py`, `adapters/etat/*`, `adapters/podcast/__init__.py`, `core/{controle,grille,jingles}.py` |
| `d2cbfef` *docs(readme)* | `adapters/config/chargement.py`, `adapters/ffmpeg/__init__.py`, `adapters/podcast/flux.py`, `adapters/sources/__init__.py`, `adapters/web/__init__.py`, `core/emissions.py` |

**Deux règles enfreintes**, et ce sont les deux qui comptent :

1. **Un commit dont le message ment sur son contenu.** « Conteneuriser » a
   embarqué 1 300 lignes de noyau et d'adaptateurs. L'historique cesse d'être
   relisible — exactement ce que « un commit = une tâche cohérente »
   (AGENTS.md §7) protège.
2. **Du code committé sans vérification.** `./verifier.sh` n'a pas tourné sur ces
   fichiers avant leur entrée dans l'historique : `code écrit ≠ tâche terminée`
   (AGENTS.md §1.1) a été violé à l'endroit précis où il coûte le plus.

**Ce que je n'ai pas fait, et pourquoi.** Pas de `rebase`, pas d'`amend` : la
réécriture d'historique est un cas d'arrêt (AGENTS.md §1.2), et masquer une
erreur en la faisant disparaître est le contraire de ce que §8 demande —
*repérer, ne pas masquer, corriger, rapporter*.

**Ce qui est fait à la place** : l'incident est écrit ici, et l'intégration
vérifie **l'ensemble** du dépôt avant de déclarer quoi que ce soit terminé. Les
fichiers emportés sont de toute façon du travail voulu ; c'est leur *entrée dans
l'historique* qui était prématurée, pas leur existence.

**La règle qui en sort**, à appliquer désormais :

> **Jamais `git add -A` quand un autre agent écrit.** On nomme les fichiers, ou
> l'on attend. Un dépôt partagé n'a pas d'index par agent : `-A` prend tout ce
> qui traîne, y compris ce que quelqu'un est en train d'écrire.

Ajoutée à AGENTS.md §7.

---

## Note 2026-08-30 — un message de commit amputé par le shell

Le commit *refactor(nommage) : les identifiants passent à l'anglais* porte un
paragraphe vide de ses mots :

> « Une collision réelle a été corrigée à la main :  et tombaient tous deux
> sur , et  réassignait un paramètre avec un autre type. La variable locale
> s'appelle . »

**Cause** : le message contenait des accents graves, et il a été passé à
`git commit -m` depuis un shell qui les a pris pour des substitutions de
commande. Cinq mots ont disparu à l'écriture.

**Ce que le paragraphe disait**, et qui compte pour qui relira ce commit :

> `reglages` et `config` tombaient tous deux sur `config` dans le glossaire de
> renommage, si bien que `config = config.settings` réassignait un paramètre
> avec un type différent. La variable locale a été renommée `settings`, à la
> main — c'est la seule correction manuelle du renommage.

**Pas d'`--amend`.** La réécriture d'historique est un cas d'arrêt
(AGENTS.md §1.2), et elle a déjà été refusée une fois ce jour-là. Être constant
sur une règle vaut mieux qu'un historique propre : la correction vit donc ici.

**La règle qui en sort** : un message de commit se passe par
`git commit -F` ou par un `heredoc` cité, jamais par `-m` avec du texte qui
contient des accents graves. Ajoutée à AGENTS.md §7.

---

## Constaté en conteneur, le 2026-08-30 (`GOAL-011`)

| Question | Réponse |
|---|---|
| Le conteneur joint-il Navidrome ? | **Oui.** `http://music` répond HTTP 200 depuis le conteneur — le nom est résolu par le réseau de l'hôte. `extra_hosts` reste en commentaire, pour une autre machine |
| `SIGTERM` arrête-t-il proprement ? | **Oui.** `docker stop` rend la main en **5 s** — bien avant les 10 s de grâce — et le code de sortie est **0** |
| ffmpeg orphelin dans le conteneur ? | **Non vérifié** : `ps` n'est pas dans l'image `slim`. Le code de sortie 0 et l'arrêt en 5 s prouvent que l'application a traité le signal, pas qu'aucun processus n'a survécu |

### Le défaut que le conteneur a révélé

Premier démarrage : **`Address already in use`**.

Le flux et l'interface sont **deux serveurs distincts**, et le commentaire de
`schema.py` affirmait pourtant qu'ils *« partagent le port du flux : une seule
chose à ouvrir »*. C'était faux, et rien hors du conteneur ne l'avait montré —
en développement, on ne lance jamais les deux ensemble.

Corrigé : le web prend **8080** par défaut, le flux garde **8000**. Le
`Dockerfile`, le Compose, le TOML d'exemple et le README suivent.

> **Ce n'est pas le conteneur qui a créé le défaut, c'est lui qui l'a rendu
> visible.** Le même bogue attendait quiconque aurait lancé la radio pour de
> bon.

---

## GOAL-004 — Le flux : ffmpeg, fan-out, démarrage à la demande

**État : EN COURS** — le code, les tests et la vérification sont passés ; seule l'écoute réelle (angle mort, AGENTS.md §4.1) reste à faire par l'auteur

Le cœur exécutable. `GOAL-002` l'a largement pré-décidé : réencodage
systématique, voie PCM, un seul chemin d'insertion, `-re` pour cadencer.

- [x] `GOAL-004-T01` `adapters/ffmpeg/` : décoder une entrée vers le PCM du flux
- [x] `GOAL-004-T02` L'encodeur unique, cadencé — sans lui la bibliothèque part en minutes
- [x] `GOAL-004-T03` Le fan-out : un flux, N connexions, un auditeur lent n'en ralentit aucun
- [x] `GOAL-004-T04` `adapters/http/` : servir le flux, en-têtes `icy-*` compris
- [x] `GOAL-004-T05` Démarrage à la première connexion
- [x] `GOAL-004-T06` **Arrêt à la dernière — tout l'arbre de processus**, déconnexion brutale comprise
- [x] `GOAL-004-T07` La file prend de l'avance : résoudre pendant que le courant joue
- [x] `GOAL-004-T08` Les erreurs au démarrage sont fatales et se disent (SPECS.md §4.1)
- [x] `GOAL-004-T09` Les pannes en cours : tenir, réessayer, puis couper en le disant (SPECS.md §5.1)
- [ ] `GOAL-004-T10` **Écoute réelle** : brancher VLC, un navigateur, une enceinte — et la matrice de `docs/flux-icy.md` §6
- [x] `GOAL-004-T11` Carte du dépôt

> **`T06` porte un défaut déjà constaté.** La maquette de `GOAL-002-T05` a laissé
> **deux ffmpeg orphelins** à la dernière déconnexion
> ([docs/flux-icy.md](./docs/flux-icy.md) §3.bis) : le décodeur source n'était
> pas tué, et la boucle déréférençait un processus disparu. Un test sur un
> booléen serait passé au vert. **Ce test doit compter les processus.**

> **`T10` est le premier rendez-vous avec les angles morts.** Aucun cas d'arrêt
> ne l'impose (SPECS.md §7 n°9) : c'est à l'auteur de le réclamer, ou il
> n'arrivera pas.

---

## GOAL-011 — Conteneurisation : Docker et Compose

**État : TERMINÉ**

À faire **juste après `GOAL-004`** : c'est le premier moment où il y a quelque
chose à faire tourner. Le faire avant serait emballer du vide ; beaucoup plus
tard, ce serait découvrir tard les surprises de réseau et de volumes.

- [x] `GOAL-011-T01` `Dockerfile` : image Python fine, **ffmpeg épinglé à la version relevée**
- [x] `GOAL-011-T02` `docker-compose.yml` : un service, `env_file`, ports
- [x] `GOAL-011-T03` Volumes : configuration et jingles en **lecture seule**, état SQLite en écriture
- [x] `GOAL-011-T04` **Le conteneur joint-il Navidrome ?** `http://music` est résolu par l'hôte, pas forcément par le conteneur
- [x] `GOAL-011-T05` Arrêt propre : `SIGTERM` doit arrêter tout l'arbre, pas seulement le processus 1
- [x] `GOAL-011-T06` Le conteneur ne tourne pas en `root`, et n'écrit que dans le volume d'état
- [x] `GOAL-011-T07` `CONTRIBUTING.md` et `README.md` : lancer en conteneur, et vérifier **hors** conteneur

> **`T05` est le piège classique** : un processus 1 qui ignore `SIGTERM` laisse
> Docker tuer brutalement au bout de dix secondes — et l'on retrouve les
> orphelins de `GOAL-004-T06`, cette fois invisibles.

---

## GOAL-005 — La grille horaire et les moments thématiques

**État : TERMINÉ**

- [x] `GOAL-005-T01` `adapters/config/` : lire le TOML, et **refuser** un secret qui s'y trouverait
- [x] `GOAL-005-T02` Le schéma de configuration, validé au démarrage, erreurs nommant la clé fautive
- [x] `GOAL-005-T03` `core/grille.py` : quelle plage à quelle heure — l'horloge est injectée
- [x] `GOAL-005-T04` La grille n'est consultée **qu'au tirage** (SPECS.md §7 n°5) : un morceau finit dans sa plage
- [x] `GOAL-005-T05` Le repli d'une plage sans musique sur le tirage libre, journalisé
- [x] `GOAL-005-T06` `adapters/sources/navidrome/` : authentification par jeton dérivé
- [x] `GOAL-005-T07` **Lire `status` dans le corps à chaque appel** — un mot de passe faux rend HTTP 200
- [x] `GOAL-005-T08` Le tirage et le filtre par genre, avec la troncature à 500 **connue et respectée**
- [x] `GOAL-005-T09` `pistes_de(artiste)` : `search3` filtré sur l'égalité exacte du nom
- [x] `GOAL-005-T10` Traduire les erreurs Subsonic en `SourceIndisponible` — les deux régimes, HTTP 200 et 404
- [x] `GOAL-005-T11` Tests de l'adaptateur contre des réponses **littérales**, HTML en 200 compris
- [x] `GOAL-005-T12` Carte du dépôt

> Les tâches `T06` à `T11` sont entièrement pré-écrites par
> [docs/navidrome.md](./docs/navidrome.md) : chacune correspond à un piège
> constaté, et à lui seul.

---

## GOAL-006 — Jingles horaires

**État : EN COURS** — le code, les tests et la vérification sont passés ; seule l'écoute réelle (angle mort, AGENTS.md §4.1) reste à faire par l'auteur

- [x] `GOAL-006-T01` `core/jingles.py` : quel jingle est dû, d'après l'horloge injectée
- [x] `GOAL-006-T02` Résoudre `HHh.mp3` depuis l'heure — aucune table de correspondance
- [x] `GOAL-006-T03` **Un jingle absent ne signale rien** ; un jingle illisible journalise
- [x] `GOAL-006-T04` L'empilement : tous les jingles dus, dans l'ordre chronologique
- [x] `GOAL-006-T05` L'insertion à la jonction, par **le** chemin unique de `GOAL-004`
- [ ] `GOAL-006-T06` **Écoute réelle** : le niveau d'un vrai jingle contre la musique
- [x] `GOAL-006-T07` Carte du dépôt

> **Le flash France Info ne figure plus dans ce Goal.** Aucune source n'a pu
> être confirmée ([docs/franceinfo.md](./docs/franceinfo.md) §1.5), et trois
> questions attendaient l'auteur. **Réponse le 2026-08-30** : le podcast est
> vide, le direct répond — le flash devient une **émission qui capte un direct**,
> `GOAL-015`.

> **`T06` est le seul moyen de savoir** si un jingle écrase la musique. Le relevé
> ne pouvait pas le dire : ses fichiers d'essai étaient des sinus de même
> amplitude ([docs/ffmpeg.md](./docs/ffmpeg.md) §2.ter).

---

## GOAL-007 — Le pilotage : `stop` et `encore` dans le noyau

**État : TERMINÉ**

- [x] `GOAL-007-T01` `core/controle.py` : l'effet de `stop` sur ce que la file rendra
- [x] `GOAL-007-T02` L'effet d'`encore` : même artiste, puis même genre, puis tirage libre
- [x] `GOAL-007-T03` `encore` **outrepasse** la non-répétition, et ses morceaux n'entrent pas dans la fenêtre
- [x] `GOAL-007-T04` L'enchaînement illimité, borné par l'épuisement de l'artiste
- [x] `GOAL-007-T05` Le **refus motivé** pendant un jingle, un flash ou une émission
- [x] `GOAL-007-T06` Le jingle de vote `encore.mp3`, marqué dû, diffusé **en dernier** à la jonction

---

## GOAL-008 — L'API de pilotage

**État : TERMINÉ**

- [x] `GOAL-008-T01` `adapters/web/api/` : la surface publique, sans Flask dans le noyau
- [x] `GOAL-008-T02` Dire ce qui passe : titre, artiste, et **de quelle nature** — musique, jingle, flash, émission
- [x] `GOAL-008-T03` Dire si la chaîne tourne
- [x] `GOAL-008-T04` Accepter un vote `stop` et un vote `encore` — une voix suffit
- [x] `GOAL-008-T05` Traduire le refus du noyau en réponse HTTP **motivée** — un refus muet ressemble à une panne
- [x] `GOAL-008-T06` Tests : l'API n'appelle jamais le noyau autrement que par les décisions de `GOAL-007`

---

## GOAL-009 — L'interface web — Flask et Jinja2

**État : EN COURS** — le code, les tests et la vérification sont passés ; seule l'écoute réelle (angle mort, AGENTS.md §4.1) reste à faire par l'auteur

- [x] `GOAL-009-T01` Le serveur Flask, monté à côté du flux, sans le perturber
- [x] `GOAL-009-T02` Un gabarit Jinja2 : ce qui passe, et deux boutons
- [x] `GOAL-009-T03` Les boutons appellent **l'API**, jamais le noyau — l'interdit est contrôlé
- [x] `GOAL-009-T04` L'affichage d'un refus, quand un vote tombe pendant un jingle ou une émission
- [x] `GOAL-009-T05` Utilisable à une main, sur un téléphone posé à côté de l'enceinte
- [ ] `GOAL-009-T06` **Regarder la page sur un vrai téléphone** — aucun test ne le fera
- [x] `GOAL-009-T07` Carte du dépôt

---

## GOAL-010 — Les émissions : podcasts programmés

**État : EN COURS** — le code, les tests et la vérification sont passés ; seule l'écoute réelle (angle mort, AGENTS.md §4.1) reste à faire par l'auteur

- [x] `GOAL-010-T01` `adapters/podcast/` : lire un flux RSS, en extraire les épisodes
- [x] `GOAL-010-T02` Ne retenir que les `full` — écarter `bonus` et `trailer`
- [x] `GOAL-010-T03` **Ne pas se fier à `enclosure/length`** : Acast insère de la publicité, le fichier servi diffère
- [x] `GOAL-010-T04` `adapters/etat/` : la base SQLite, une table, écriture atomique
- [x] `GOAL-010-T05` `core/emissions.py` : quelle émission est due, d'après la grille déclarée
- [x] `GOAL-010-T06` **Deux émissions à la même heure refusent le démarrage**, en les nommant
- [x] `GOAL-010-T07` L'épisode le plus récent **non encore diffusé** ; sinon la case est sautée
- [x] `GOAL-010-T08` Le rattrapage borné à la durée de l'épisode — la durée se lit **avant** de décider
- [x] `GOAL-010-T09` Une émission **suspend** la grille, la non-répétition et les jingles
- [x] `GOAL-010-T10` Un épisode indisponible ou tronqué : rester sur la musique, journaliser
- [ ] `GOAL-010-T11` **Écoute réelle** : le niveau d'un épisode contre la musique, et la jonction
- [x] `GOAL-010-T12` Carte du dépôt

> **`T08` est la seule tâche du projet où le démarrage dépend d'un appel réseau
> qui peut ne servir à rien** (ARCHITECTURE.md §5.2). Elle porte aussi le chiffre
> qui a surpris : la fenêtre de rattrapage peut atteindre **2 h 50** sur LEGEND
> ([docs/podcast.md](./docs/podcast.md) §3.1).

---

## GOAL-012 — Les votes pondèrent les tirages suivants

**État : EN COURS** — le code, les tests et la vérification sont passés ; seule l'écoute réelle (angle mort, AGENTS.md §4.1) reste à faire par l'auteur

`stop` et `encore` sont enregistrés dans la base et pondèrent les tirages
suivants : un morceau souvent passé revient moins souvent, un artiste souvent
redemandé revient plus souvent (SPECS.md §4.12).

**Rien n'est jamais supprimé** : le plancher est ×0,25, pas zéro. C'est la
différence entre une radio qui apprend et une radio qui se rétrécit.

### Pourquoi ce Goal existe sous cette forme

`ARCHITECTURE.md §5.0` posait une garde : *« une seconde table n'arrive qu'avec
une décision écrite »*. Ce Goal **est** cette décision. La garde n'a pas sauté,
elle a fonctionné — l'ajout est spécifié, borné et daté au lieu d'être glissé
dans un commit d'implémentation. Elle reste en vigueur pour la troisième table.

### Les tâches

- [x] `GOAL-012-T01` `adapters/etat/` : la table `votes`, et la décroissance à l'écriture
- [x] `GOAL-012-T02` La décroissance **à la lecture** aussi, entre `vu_le` et maintenant
- [x] `GOAL-012-T03` `core/ponderation.py` : des scores au multiplicateur, borné à `[0,25 ; 4]`
- [x] `GOAL-012-T04` La portée croisée : `stop` = 1 sur la piste, 0,25 sur l'artiste ; `encore` l'inverse
- [x] `GOAL-012-T05` `core/rng.py` gagne `choisir_pondere()` — une capacité **nouvelle**, pas un réglage
- [x] `GOAL-012-T06` **Le tirage pondéré reste rejouable** à graine et poids fixés
- [x] `GOAL-012-T07` La file reçoit les poids, elle ne va pas les chercher — la frontière du noyau tient
- [x] `GOAL-012-T08` Enregistrer le vote au moment où il est **accepté**, jamais quand il est refusé
- [x] `GOAL-012-T09` Les clés de configuration : plancher, plafond, demi-vie, poids croisé
- [x] `GOAL-012-T10` Une base absente ou vide se comporte comme des poids neutres
- [ ] `GOAL-012-T11` **Écoute sur plusieurs semaines** — le seul moyen de savoir si la radio s'est resserrée
- [x] `GOAL-012-T12` Carte du dépôt

### Ce que le découpage retient des décisions

| Décision | Ce qu'elle impose |
|---|---|
| **n°16** — portée croisée | `T04`. Un `stop` compte 1 sur la piste, 0,25 sur l'artiste ; dix `stop` sur des titres différents d'un même artiste finissent par se voir |
| **n°17** — de ×0,25 à ×4 | `T03`. Le plancher **non nul** est la garantie que rien ne disparaît |
| **n°18** — décroissance, demi-vie 3 mois | `T01` et `T02`. **Des scores décimaux, pas des compteurs** : douze `stop` dont le dernier date d'hier compteraient tous comme frais, et personne ne s'en apercevrait (ARCHITECTURE.md §5.2) |

### Trois pièges nommés d'avance

- **`T06`** — un tirage pondéré qui ne se rejoue pas fait perdre ce que
  `GOAL-003-T02` avait acheté, et emporte les tests de la file avec lui.
- **`T08`** — un vote refusé pendant un jingle ou une émission (SPECS.md §4.6) ne
  doit **rien** enregistrer. Sinon la radio apprend de gestes qui n'ont pas eu
  d'effet, et l'auditeur pondère sans le savoir.
- **`T11`** — c'est le **cinquième angle mort** (AGENTS.md §4.1), et le plus
  lent : un test vérifie la formule, aucun ne dit si la radio s'est resserrée.
  Cela ne se constate qu'après des semaines d'usage.

---

## GOAL-013 — Les programmes : une playlist, des jours, des heures

**État : TERMINÉ**

Une plage de temps — jours **et** heures — pendant laquelle la musique est tirée
au hasard dans une liste de lecture Navidrome (SPECS.md §4.13).

### Les tâches

- [x] `GOAL-013-T01` `adapters/sources/` : `getPlaylists` et `getPlaylist`, au format `Piste`
- [x] `GOAL-013-T02` **Ne jamais se fier à `songCount`** : une liste se juge sur ce qu'elle rend
- [x] `GOAL-013-T03` Résoudre une liste **par son nom** — c'est ce que le TOML déclare, pas un identifiant opaque
- [x] `GOAL-013-T04` `core/programmes.py` : quel programme est ouvert, d'après l'horloge injectée
- [x] `GOAL-013-T05` Le tirage **dans la liste**, avec la non-répétition et sa fenêtre qui rétrécit
- [x] `GOAL-013-T06` `encore` cherche **dans la liste**, et y retombe — jamais au-dehors
- [x] `GOAL-013-T07` Une liste introuvable, vidée ou renommée : repli sur le tirage libre, journalisé
- [x] `GOAL-013-T08` Le programme l'emporte sur une plage thématique qui le recouvre
- [x] `GOAL-013-T09` Une **émission** l'emporte sur un programme — elle remplace toute la programmation
- [x] `GOAL-013-T10` Les clés `[[programmes]]` au schéma, et le TOML d'exemple
- [x] `GOAL-013-T11` Carte du dépôt

### Ce que le relevé impose

`docs/navidrome.md` §2.6 a été établi pour ce Goal, et il change deux choses :

| Constat | Conséquence |
|---|---|
| **`getRandomSongs&playlistId` est ignoré en silence** — `status: ok`, et aucun des vingt morceaux rendus n'appartenait à la liste | Le tirage se fait **chez nous**, sur les entrées récupérées. `T05` ne délègue rien au serveur |
| **`songCount` et le nombre d'entrées divergent** — 67 annoncés, 32 rendus, tous distincts. Cause non établie | `T02`. Une liste « vide » se juge sur ses entrées, jamais sur son compteur |
| Une liste inexistante rend HTTP 200 / code 70 | `T07`. Même régime que le reste : lire `status`, jamais le code HTTP |

### Ce qui est encore ouvert

**SPECS.md §7 n°19** — faut-il garder *à la fois* les programmes et les plages
thématiques ? Ils répondent à la même question. La coexistence s'applique en
attendant, **provisoirement et écrit comme tel** : `T08` la met en œuvre, et
devra être rejouée si l'auteur tranche autrement.

---

## GOAL-014 — Correctifs de la relecture du 2026-08-30

**État : TERMINÉ** — `T01` corrigée et vérifiée ; `T02` à `T07` ont disparu avec leur code (`GOAL-016-T10`), et `T08` est sans objet

Une relecture de `adapters/ffmpeg/`, `adapters/http/` et `app/` a trouvé sept
défauts, dont quatre confirmés à la lecture du code. **376 tests passaient** :
chacun est un cas que les tests ne posaient pas, et chaque correctif commence
par le test qui l'aurait vu.

### Les tâches

- [x] `GOAL-014-T01` **Les jingles ne passent jamais.** `app/playout.py` : `_prochaine_emission()` appelle `jingles.due_now()` — qui **consomme** — et jette le résultat ; `_prochain_jingle()` rappelle et obtient `()`. Dès que `shows` est câblé (toujours, `main.py`), ni `20h.mp3` ni `encore.mp3` ne sortent. Un seul appel par jonction, et un test avec émissions câblées **et** un jingle dû
- [x] ~~`GOAL-014-T02`~~ **sans objet** — **Une chaîne qui coupe d'elle-même laisse les auditeurs pendus.** `app/main.py` : `end()` ne fait que baisser le compteur ; `Station` garde `_diffusion`, `Broadcast.close()` n'est jamais appelé, les lecteurs attendent sans EOF et tout nouvel auditeur s'abonne à une diffusion morte. Contredit SPECS.md §5.1 « couper en le disant ». Le test : file épuisée → les abonnés reçoivent la fin, le suivant redémarre une chaîne
- [x] ~~`GOAL-014-T03`~~ **sans objet** — **`on_air` ne redescend jamais à l'arrêt normal.** `Station.stop_all()` ne passe pas par `end()` : après le dernier auditeur, l'API affiche « à l'antenne » pour personne. Une seule source de vérité pour « la chaîne tourne »
- [x] ~~`GOAL-014-T04`~~ **sans objet** — **`next_entry()` appelé après l'arrêt.** `adapters/ffmpeg/encoder.py` : la pompe sort de `read()` sur `b""` quand le groupe est tué et entre dans `_enchainer` sans vérifier `_fini` — appel réseau, `declare(MUSIC)`, non-répétition et `record_airing` d'une chose jamais diffusée. Le test compte les appels à `next_entry` après `stop_all()` : zéro
- [x] ~~`GOAL-014-T05`~~ **sans objet** — Relance concurrente d'un arrêt (`encoder.py`, `_relancer` teste `_fini` hors verrou) : orphelins possibles — le défaut de `docs/flux-icy.md` §3.bis, par une autre porte. **Le test compte les processus**
- [x] ~~`GOAL-014-T06`~~ **sans objet** — Auditeur vivant qui ne lit plus (`server.py`, aucun `timeout` de socket) : `wfile.write` bloque sans borne, le compteur ne redescend pas, la chaîne tourne pour personne (SPECS.md §4.7). Un délai d'écriture, déclaré au TOML
- [x] ~~`GOAL-014-T07`~~ **sans objet** — La pompe n'a aucun garde-fou : `termine.wait()` peut lever `TimeoutExpired`, et toute exception de `next_entry` laisse une chaîne zombie muette. Attraper, journaliser, et **appeler `end()`** — jamais mourir en silence
- [x] ~~`GOAL-014-T08`~~ **sans objet** — Carte du dépôt, et les constats de ce Goal dans `docs/flux-icy.md` §3.bis

> **Recadré le 2026-08-30 par la décision n°23** : `T02` à `T07` vivent dans
> `adapters/ffmpeg/`, `adapters/http/` et le câblage de `main.py` — du code que
> `GOAL-016` supprime. **On ne les corrige pas**, on les consigne : ils sont la
> raison de la migration. Seule **`T01`** survit — elle est dans `app/playout.py`,
> qui reste — et elle se corrige **avant** de migrer, parce qu'un jingle qui ne
> passe jamais serait invisible dans la nouvelle chaîne aussi.

---

## GOAL-015 — Un direct comme émission — dont le flash France Info

**État : EN COURS** — tout est fait sauf `T08`, l'écoute réelle. Constaté sur
la pile complète : le direct franceinfo capté et affiché « émission » avec son
nom ; en maquette : la bascule à la jonction, la coupure à l'heure absolue, le
retour à la musique. Trois découvertes en chemin, consignées dans
docs/liquidsoap.md §5 — dont : une case plus courte que deux morceaux peut être
sautée (conforme au « pas de rattrapage »), et **l'heure des conteneurs était
UTC** — `/etc/localtime` traverse désormais la frontière du Compose et
`SystemClock` rend l'heure locale

Une émission peut capter **un flux de webradio** pendant une case déclarée
(SPECS.md §4.11 « Une émission peut être un direct », §7 n°22). C'est ce qui
rend le flash France Info possible — son podcast est vide, son direct répond
([docs/franceinfo.md](./docs/franceinfo.md) §1.bis) — et ce qui permet de glisser
n'importe quelle station entre deux créneaux de musique.

**Ce que le relevé a établi** : `https://icecast.radiofrance.fr/franceinfo-midfi.mp3`,
MP3 48 kHz stéréo 128 kb/s, décodé sans rien changer par `adapters/ffmpeg/decoder.py`
(5 s → 882 000 octets de PCM, exactement). Le direct n'est donc **pas un nouvel
adaptateur** : c'est une entrée ffmpeg qui ne se termine jamais. Tout ce Goal
tient dans *quand l'arrêter*.

### Les tâches

- [x] `GOAL-015-T01` Le TOML : une `[[shows]]` porte **soit** `feed`, **soit** `stream` + `duration` — jamais les deux, jamais ni l'un ni l'autre ; refus au démarrage, en nommant l'émission
- [x] `GOAL-015-T02` `core/shows.py` : une case de direct est due **tant qu'il reste du temps** dans sa case — pas de rattrapage (§7 n°22), et « le temps qui reste » se calcule à l'horloge injectée
- [x] `GOAL-015-T03` ~~un décodeur borné~~ **devenu** : `input.http` piloté par l'instruction `live:<fin absolue>:<url>` de l'API — relevé docs/liquidsoap.md §5 (un direct ne peut pas être une requête) — c'est le seul endroit qui coupe, et il coupe à la seconde déclarée, pas à une jonction. Vérifier contre ffmpeg n9.0.1 que l'option retenue (`-t` en entrée, ou arrêt du processus) rend **exactement** la durée demandée, et le consigner dans `docs/ffmpeg.md`
- [x] `GOAL-015-T04` `app/show_scheduler.py` : un direct ne passe ni par le podcast ni par `record_airing` — il n'y a pas d'épisode
- [x] `GOAL-015-T05` Injoignable, tari ou coupé en cours de case : retour à la musique, journalisé, **sans retenter dans la même case** (SPECS.md §4.5). **Tester avec une URL morte** et avec un serveur qui ferme après 2 s
- [x] `GOAL-015-T06` L'API et l'interface disent ce qui passe : nature `émission`, et le **nom déclaré** — le flux ne porte aucune métadonnée (docs/franceinfo.md §1.bis)
- [x] `GOAL-015-T07` Le TOML d'exemple : un flash franceinfo à `HH:00`, et une station tierce le dimanche entre deux créneaux
- [ ] `GOAL-015-T08` **Écoute réelle** : le niveau de la parole (−16,2 LUFS mesurés) contre la musique, et la coupure « en cours de phrase » à la fin de la case
- [x] `GOAL-015-T09` Carte du dépôt, `docs/franceinfo.md` §2 et §3 renseignés d'après ce qui a été observé

> **`T03` est le point dur**, et le seul qui touche ffmpeg. Un direct se coupe
> *pendant* qu'il joue : c'est la première fois que la radio arrête quelque
> chose autrement qu'à une jonction. Tout le reste de la spécification —
> « ne rien couper » — reste vrai pour la musique, et §4.11 dit pourquoi le
> direct est l'exception.

> **Ce qui attend l'auteur** (SPECS.md §7 n°22) : la durée d'un flash. La grille
> de franceinfo — journal à 00 et 30, environ neuf minutes — n'est connue que de
> seconde main et n'a pas été écoutée. Un premier réglage se prend, et `T08`
> le corrige.

---

## GOAL-016 — Migration vers Liquidsoap : le noyau décide, Liquidsoap diffuse

**État : EN COURS** — tout est fait et constaté de bout en bout contre le vrai Navidrome, **sauf `T12`**, l'écoute réelle, qui attend l'auteur

Décision SPECS.md §7 n°23, relevé [docs/liquidsoap.md](./docs/liquidsoap.md),
architecture ARCHITECTURE.md §4. Le noyau, les sources, les émissions, les
votes, l'API et l'interface **ne bougent pas**. Ce qui change : qui encode, qui
sert, qui compte les auditeurs.

**La règle de ce Goal** : le script `.liq` ne décide de rien. Pas de
`playlist()`, pas de hasard, pas de jingle dans le script. Il demande, il
annonce, il diffuse.

### Les tâches

- [x] `GOAL-016-T01` Le relevé complète ses incertitudes (`docs/liquidsoap.md` §3) : `prefetch=0` ou équivalent, en-têtes `icy-*` par `headers=`, comportement quand l'API ne répond pas, bascule réelle vers `input.http`. **Contre 2.3.3, dans le conteneur**
- [x] `GOAL-016-T02` `adapters/web/playout_api.py` : la route que Liquidsoap appelle pour **le morceau suivant** — rend un chemin ou une URL, et rien d'autre ; passe par `app/playout.next_entry()` comme tout le monde
- [x] `GOAL-016-T03` La route par laquelle Liquidsoap **annonce un auditeur qui arrive ou part** — **écrite et testée** (`POST /playout/listeners`) ; le câblage vers `ListenerCount` se fait avec `T06`, quand l'ancienne chaîne cesse d'être l'autre source
- [x] `GOAL-016-T04` `adapters/liquidsoap/radio.liq` : `request.dynamic` → l'API, `switch`/`blank()` sans auditeur, `normalize`, `crossfade`, `output.harbor` avec les en-têtes de `docs/flux-icy.md` §1. **Aucune décision dans le script** — un test le lit et refuse `playlist(`, `random`, `.mp3`
- [x] `GOAL-016-T05` `verifier.sh` : `liquidsoap --check radio.liq` **dans l'image épinglée** — la syntaxe change de version en version (docs/liquidsoap.md §1.7)
- [x] `GOAL-016-T06` Docker : un second service `liquidsoap` épinglé `v2.3.3`, le port du flux passe chez lui ; `webradio` ne publie plus que l'API. La version dans l'image se **vérifie** à la construction (comme pour ffmpeg, docs/ffmpeg.md)
- [x] `GOAL-016-T07` Les jingles : le chemin unique reste `next_entry()` — un jingle est un morceau suivant comme un autre. Test : émissions câblées **et** jingle dû → il sort (c'est `GOAL-014-T01` rejoué dans la nouvelle chaîne)
- [x] `GOAL-016-T08` **Un morceau est toujours demandé d'avance** (`prefetch=1` est le minimum, docs/liquidsoap.md §3) : distinguer *demandé* et *à l'antenne*, et l'API dit ce qui passe d'après le second
- [x] `GOAL-016-T09` Les pannes (SPECS.md §5.1) : **Liquidsoap boucle par défaut** (cinq tentatives en 8 s, silence servi). Quand `next_entry()` n'a plus rien, l'API répond « fini » et le script arrête de servir — `fallible`/`shutdown()` à relever. Test avec l'API arrêtée
- [x] `GOAL-016-T10` **Supprimer** `adapters/ffmpeg/`, `adapters/http/`, leurs tests, et le câblage de `main.py` ; `docs/ffmpeg.md` reste comme relevé historique et pour le décodage des podcasts
- [x] `GOAL-016-T11` `SPECS.md §1` et §4.7 reformulés : « rien n'est décodé ni demandé » ; `docs/flux-icy.md` rejoué contre `harbor`
- [ ] `GOAL-016-T12` **Écoute réelle** : fondus, niveau, VLC / navigateur / enceinte — la matrice de `docs/flux-icy.md` §6
- [x] `GOAL-016-T13` Carte du dépôt

> **Ce qui rend ce Goal sûr** : jusqu'à `T10`, l'ancienne chaîne existe encore
> et tous ses tests passent. On ne supprime qu'après avoir écouté (`T12` avant
> `T10` si l'auteur est disponible).

---

## GOAL-017 — `stop` ne passe pas le morceau en cours

**État : TERMINÉ** — câblé, constaté, et le fondu validé à l'oreille par l'auteur

SPECS.md §4.6 : *« `stop` : passer le morceau en cours. Le suivant démarre à la
jonction, sans blanc. »* Or `Control.take_skip()` n'est **consommé par
personne** — ni dans la chaîne actuelle, ni dans l'ancienne (vérifié dans
l'historique). Un `stop` est accepté, pèse sur les tirages suivants
(`GOAL-012`), mais le morceau joue jusqu'au bout. L'écart ne vient pas de la
migration : il n'a jamais été câblé, et aucun test ne le couvre.

### Les tâches

- [x] `GOAL-017-T01` Le chemin du saut : `harbor.http.register` (le `.simple` répond en HTTP/0.9 — `BadStatusLine` côté Python, constaté) expose `POST /skip` sur le port du flux ; `radio` l'appelle via `LIQUIDSOAP_URL`
- [x] `GOAL-017-T02` Câblé : un `stop` **accepté** ordonne le saut (jamais un `encore`, jamais un refus — testé) ; un diffuseur injoignable ne casse pas le vote, le morceau finit et pèse moins. **Constaté en réel** : saut en ~6 s, jonction propre
- [x] `GOAL-017-T03` **Écoute réelle** : fondu validé par l'auteur le 2026-08-30
- [x] `GOAL-017-T04` Carte du dépôt — rien de structurel : une route de plus dans radio.liq, un ordre de plus dans main.py

---

## GOAL-018 — L'interface en Vue, et la page des votes

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, pendant son écoute

- [x] `GOAL-018-T01` `GET /api/votes` : ce que les votes ont laissé, par cible, **décroissance appliquée à la lecture** (`SqliteState.all_scores()`), plus forts d'abord
- [x] `GOAL-018-T02` La façade traduit (`piste`/`artiste`, les mots de SPECS.md §4.12) — l'API ne connaît pas SQLite, et une base illisible rend une liste vide
- [x] `GOAL-018-T03` La page réécrite avec **Vue 3, vendu avec le paquet** (`static/vue.global.prod.js`) : la radio est un objet local, elle s'affiche sans internet — un test refuse tout CDN
- [x] `GOAL-018-T04` Deux onglets : l'antenne (nature, titre, boutons), et les votes (jauges stop/encore par cible)
- [x] `GOAL-018-T05` Les interdits tiennent : aucune donnée d'antenne dans le HTML servi, tout passe par l'API, délimiteurs `[[ ]]` pour laisser `{{ }}` à Jinja2
- [ ] `GOAL-018-T06` **Regarder sur le vrai téléphone** — la seule chose qu'aucun test ne fera

---

## GOAL-019 — Les plages thématiques par jour

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30

- [x] `GOAL-019-T01` `core/bands.py` : une plage porte des jours ; **aucun jour déclaré = tous les jours** — le comportement historique, aucune configuration existante ne change de sens
- [x] `GOAL-019-T02` Une plage qui enjambe minuit appartient au jour où elle **commence** : « samedi 22 h → 02 h » couvre dimanche 01 h, pas dimanche 23 h — même règle que les cases d'émission
- [x] `GOAL-019-T03` La clé `days` au schéma (optionnelle, mêmes jours que partout), un jour inconnu refusé en le nommant, le TOML d'exemple

---

## GOAL-020 — Les votes portent un libellé lisible

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, page des votes sous les yeux

- [x] `GOAL-020-T01` La colonne `libelle`, retenue **au moment du vote** (« titre — artiste ») — l'identifiant Subsonic est opaque et le reste
- [x] `GOAL-020-T02` **La seule migration du projet** : `ALTER TABLE` au démarrage, idempotente ; un vote d'avant garde sa cible brute plutôt que de disparaître
- [x] `GOAL-020-T03` La page groupe Morceaux / Artistes, et affiche le libellé

> **Points restés incertains, constatés en maquette** : `output.harbor` avec
> `metaint` (8192 par défaut, « Interval used to send ICY metadata ») n'émet
> **ni** `icy-metaint` **ni** `StreamTitle`, même quand le client envoie
> `Icy-MetaData: 1`. Le titre dans le flux attend donc un relevé plus profond ;
> la pochette n'a de toute façon **aucune place dans un flux ICY/MP3** — les
> lecteurs qui en montrent une la tirent d'ailleurs. Consigné dans
> docs/liquidsoap.md §6.

---

## GOAL-021 — Effacer un vote, l'onglet Planning, et le bouton qui ne cliquait pas

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, l'interface sous les yeux

- [x] `GOAL-021-T01` `DELETE /api/votes/<portée>/<cible>` : un vote donné par erreur s'efface (404 s'il n'existe pas, 400 pour une portée inconnue) ; la cible **brute** voyage dans `key`, le libellé reste pour les yeux
- [x] `GOAL-021-T02` `GET /api/planning` : la grille déclarée au TOML — plages, programmes, émissions — **figée à l'assemblage** ; rien ne se configure depuis le web (SPECS.md §6)
- [x] `GOAL-021-T03` L'onglet Planning, et le ✕ sur chaque vote
- [x] `GOAL-021-T04` **Le bouton Passer ne faisait rien depuis la page** : `@click="voter(URLS.stop)"` visait une constante de module, invisible d'une expression de gabarit Vue — l'erreur restait dans la console du téléphone. Les adresses vivent désormais dans `data`. Trouvé parce que l'auteur a cliqué et que le journal ne montrait **aucun** POST — mon essai `curl` court-circuitait la page
- [x] `GOAL-021-T05` Le fondu du saut : **validé à l'oreille par l'auteur** (clôt aussi GOAL-017-T03)

---

## GOAL-022 — Fondu court des jingles, et le moment présent à l'antenne

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, à l'écoute

- [x] `GOAL-022-T01` Un jingle porte ses propres fondus (0,2 s, enchaînement 0,5 s) par les métadonnées `liq_fade_*` que `crossfade` honore — relevé : `initial_uri` conserve l'`annotate:`, le registre demandé/à l'antenne tient
- [x] `GOAL-022-T02` `moment` sur `/api/on-air` : le programme ouvert (il l'emporte), sinon la plage thématique, sinon rien — affiché sous l'artiste
- [ ] `GOAL-022-T03` **Écoute réelle** du fondu court, avec un vrai jingle dans `jingles/`

---

## GOAL-023 — Une plage peut imposer un artiste

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30 (« pendant 1 h qu'un seul artiste »)

- [x] `GOAL-023-T01` `core/bands.py` : une plage déclare des `genres` **ou** des `artists` — jamais les deux, jamais aucun ; la contrainte (`Constraint`) traverse la grille et la file, le hasard injecté tranche entre plusieurs valeurs
- [x] `GOAL-023-T02` La file demande à `tracks_by(artist)` — qui existait depuis GOAL-007 — et une plage d'artiste sans musique se replie sur le tirage libre, en le disant
- [x] `GOAL-023-T03` La clé `artists` au schéma, le TOML d'exemple, le moment et le planning l'affichent

> **StreamTitle, verdict du soir** : cassé en 2.3.3 (les en-têtes clients sont
> passés en minuscules aux gestionnaires, la comparaison `"Icy-MetaData"`
> sensible à la casse ne réussit jamais — lu dans la source), **encore cassé en
> 2.4.5** (constaté en maquette), corrigé seulement sur `main`, non publié. La
> 2.4.5 casse par ailleurs notre script (`http.post` exige `synchronous`,
> `null()` déprécié) : l'épingle reste en 2.3.3, et le titre dans le flux
> attendra une version publiée portant le correctif (docs/liquidsoap.md §6).

---

## GOAL-024 — `encore` force réellement le même artiste

**État : TERMINÉ** — constaté par l'auteur le 2026-08-30 : le vote pondérait, le jingle s'annonçait, mais le morceau suivant ignorait la demande

Le trou jumeau de GOAL-017 : `Control.take_more()` et `track_after_more()` —
même artiste, puis même genre, puis libre, chaque repli dit — n'étaient
consommés par personne depuis GOAL-007.

- [x] `GOAL-024-T01` La charnière interroge le contrôle **avant** tout tirage ; l'ancre est le morceau **à l'antenne** (`LiveRadio.playing_track()`), pas celui demandé d'avance — à défaut, le dernier rendu
- [x] `GOAL-024-T02` Pendant un **programme**, l'encore cherche dans la **liste** et y retombe, jamais au-dehors (SPECS.md §7 n°20)
- [x] `GOAL-024-T03` Sans ancre (redémarrage) : le vote a pondéré et le jingle s'annonce, rien à forcer — journalisé
- [ ] `GOAL-024-T04` **Écoute réelle** : encore → `encore.mp3` → un morceau du même artiste

---

## GOAL-025 — Une chaîne YouTube comme émission

**État : EN COURS** — demandé par l'auteur le 2026-08-30 (« mercredi à 20 h, la
dernière vidéo de @hardisk ») ; tout est fait et constaté sauf l'écoute

Relevé [docs/youtube.md](./docs/youtube.md) : handle → `channel_id` par le lien
canonique ; flux Atom sans clé d'API (15 vidéos, sans durée) ; `yt-dlp` rend la
durée et l'URL audio directe, que ffmpeg décode exactement ; cette URL expire —
on résout **au moment de diffuser**, et seulement la candidate.

- [x] `GOAL-025-T01` `adapters/youtube/` : la chaîne comme un flux d'épisodes — même contrat que le podcast, le planificateur ne fait pas la différence (modulaire, comme demandé)
- [x] `GOAL-025-T02` La dernière vidéo **non encore diffusée**, la case bornée par sa durée réelle, la trace par `videoId` — les règles n°13/n°14, réutilisées telles quelles
- [x] `GOAL-025-T03` `youtube = "https://…/@chaine"` au TOML, exclusif de `feed` et `stream` ; `[youtube] timeout_seconds` ; chaîne injoignable ou `yt-dlp` en échec = musique, journalisé
- [x] `GOAL-025-T04` `yt-dlp` épinglé (2026.8.19) dans l'image `radio` ; **résolution réelle constatée depuis le conteneur**
- [ ] `GOAL-025-T05` **Écoute réelle** : mercredi 20 h — la jonction, le niveau d'une vidéo contre la musique, et le ffmpeg de Liquidsoap sur googlevideo (constaté seulement avec celui de l'hôte)

---

## GOAL-026 — Les votes ne portent que sur l'artiste (n°16 révisée)

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, à l'écoute : « éviter
les surpondérations »

- [x] `GOAL-026-T01` `vote_weight` : 1 sur l'artiste, 0 sur la piste, `stop` comme `encore` — et un poids nul ne s'écrit pas en base (plus de lignes à zéro)
- [x] `GOAL-026-T02` La clé `cross_weight` disparaît du schéma et des TOML — une clé sans effet serait un mensonge
- [x] `GOAL-026-T03` SPECS §4.12 et n°16 révisés ; les anciennes lignes « piste » en base s'éteignent par la demi-vie, ou d'un ✕ sur la page
