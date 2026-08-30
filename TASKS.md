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

**Phase 1 — Relevés et noyau** `[-]` en cours (`GOAL-002`, `GOAL-003`).

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

**Prochaine tâche** : `GOAL-002-T01` — ffmpeg, copie sans réencodage.

Sur quinze décisions, **treize sont tranchées**. La n°9 est une conséquence
consignée, non une question ; la n°12 est délibérément différée jusqu'à la
deuxième source de musique. **Aucune ne bloque plus un découpage** : les dix
Goals sont découpables.

---

## Vue d'ensemble

| Goal | Titre | État |
|---|---|---|
| GOAL-001 | Harness et initialisation | `[x]` |
| GOAL-002 | Relever les cinq dépendances externes | `[-]` |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture | `[ ]` |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[ ]` |
| GOAL-005 | La grille horaire et les moments thématiques | `[ ]` |
| GOAL-006 | Jingles horaires et flashs France Info | `[ ]` |
| GOAL-007 | Le pilotage : `stop` et `encore` dans le noyau | `[ ]` |
| GOAL-008 | L'API de pilotage | `[ ]` |
| GOAL-009 | L'interface web — Flask et Jinja2 | `[ ]` |
| GOAL-010 | Les émissions : podcasts programmés | `[ ]` |

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

**État : EN COURS**

Cinq relevés à établir **par observation**, avant toute implémentation
(AGENTS.md §3). Les fichiers `docs/*.md` portent déjà les questions ; ce Goal y
répond.

**Trois sont faisables sur cette machine**, deux dépendent d'accès que le dépôt
n'a pas : un serveur Navidrome avec ses identifiants, et les URL des podcasts.
Le découpage sépare les deux, pour que ce qui peut avancer avance.

### Ce qui ne dépend que de la machine

- [ ] `GOAL-002-T01` ffmpeg : copie sans réencodage, et comportement exact en fin de fichier
- [ ] `GOAL-002-T02` ffmpeg : alimenter un encodage continu depuis une file inconnue d'avance
- [ ] `GOAL-002-T03` ffmpeg : insérer un fichier d'une autre origine (jingle) sans interrompre
- [ ] `GOAL-002-T04` ffmpeg : chiffrer le coût d'un réencodage permanent, pour un auditeur et pour cinq
- [ ] `GOAL-002-T05` Flux : ce qu'un lecteur reçoit en se branchant **en cours** de diffusion
- [ ] `GOAL-002-T06` Flux : ce qui fait décrocher — changement de débit, de fréquence, de canaux, de codec

### Ce qui dépend du réseau

- [ ] `GOAL-002-T07` France Info : trouver la source du flash, son format, sa durée, sa fraîcheur

### Ce qui dépend de l'auteur

- [ ] `GOAL-002-T08` Navidrome : authentification, tirage, genres, artiste, récupération du son
- [ ] `GOAL-002-T09` Podcast : format des flux, fiabilité de la date de publication et de la durée

### Clôture

- [ ] `GOAL-002-T10` Consolider les cinq relevés, et lister **ce qui reste incertain** — un point incertain n'est jamais remplacé par une supposition

---

## GOAL-003 — Le noyau : horloge, hasard, file de lecture

**État : TODO** — non découpé.

`core/clock.py`, `core/rng.py`, la file de lecture et la règle de
non-répétition. Aucune E/S : c'est ici que se vérifie l'interdit central
d'AGENTS.md §2.

**Débloqué** : SPECS.md §7 n°3 est tranchée — `non_repetition_artistes` artistes
distincts, 5 par défaut, et une fenêtre qui **rétrécit** plutôt que de bloquer le
tirage. Ce rétrécissement est un comportement à part entière, avec ses tests.

---

## GOAL-004 — Le flux : ffmpeg, fan-out, démarrage à la demande

**État : TODO** — non découpé.

Le serveur HTTP, le sous-processus ffmpeg, le fan-out d'un flux unique vers N
connexions, et surtout le **cycle de vie** : démarrage à la première connexion,
arrêt à la dernière, y compris sur déconnexion brutale (SPECS.md §4.7).

Premier Goal dont le résultat ne peut être constaté qu'en **écoutant**
(AGENTS.md §4.1) — et premier à devoir tenir les trois exigences de SPECS.md
§4.9 : lisible par tout lecteur, sans coupure, transcodant le moins possible.

**Débloqué** : SPECS.md §7 n°11 est tranchée. L'ordre de priorité est fixé —
sans coupure, puis lisible partout, puis économie — et le **réencodage permanent
est la voie par défaut, assumée**. Ce que `GOAL-002` apportera n'est plus une
décision mais une optimisation : un chemin moins coûteux existe-t-il *sans violer
cet ordre* ?

Ce Goal porte aussi la limite de « une radio ne se tait pas » : tenir, réessayer,
puis **couper en le disant** — jamais boucler sur ce qui vient de passer
(SPECS.md §5.1).

---

## GOAL-005 — La grille horaire et les moments thématiques

**État : TODO** — non découpé.

La lecture du TOML, les plages horaires, la contrainte de genre, et le repli sur
le tirage libre quand une plage n'a rien à offrir (SPECS.md §4.4).

**Débloqué** : SPECS.md §7 n°5 est tranchée — la grille n'est consultée qu'au
moment du tirage. Un morceau déborde sur la plage suivante et personne ne s'en
formalise : ce Goal n'a donc **aucune** logique de fin de plage à écrire.

---

## GOAL-006 — Jingles horaires et flashs France Info

**État : TODO** — non découpé.

L'insertion à la jonction sans couper un morceau, la résolution du nom `HHh.mp3`
depuis l'heure, l'empilement de plusieurs jingles dus à la même jonction, et le
silence délibéré quand un jingle est absent — distinct de l'incident qu'est un
fichier corrompu (SPECS.md §4.3).

**Aucun seuil de péremption** : SPECS.md §7 n°4 est tranchée, rien n'est jamais
abandonné pour retard. Cela retire de ce Goal toute une famille de cas limites.

C'est ici qu'est écrite **l'unique mécanique d'insertion de jingle**, celle dont
`GOAL-007` se sert pour `encore.mp3` (ARCHITECTURE.md §6.2). Elle est donc
écrite une fois, pour deux déclencheurs : l'horloge et le vote.

---

## GOAL-007 — Le pilotage : `stop` et `encore` dans le noyau

**État : TODO** — non découpé.

L'effet des deux commandes sur ce que la file rendra ensuite, le **refus motivé**
pendant un jingle ou un flash (SPECS.md §4.6), et le déclenchement de la note
d'accusé de réception.

Sans Flask, sans HTTP, sans navigateur : c'est du noyau, et cela se teste seul.

**Débloqué le 2026-08-30** : SPECS.md §7 n°7 et n°10 sont tranchées. `encore`
s'enchaîne sans limite, **outrepasse la règle de non-répétition**, et les morceaux
qu'il sert n'entrent pas dans la fenêtre — sans quoi un long enchaînement
condamnerait l'artiste pour longtemps après.

SPECS.md §7 n°10 est tranchée — une voix suffit, et
l'accusé de réception est un jingle `encore.mp3` posé à la jonction, par le même
chemin que les jingles horaires. Le noyau n'a donc qu'à **marquer un jingle de
vote comme dû** ; toute la mécanique d'insertion appartient à `GOAL-006`.

Reste à poser avant de découper : ce qui se passe quand un jingle horaire et un
jingle de vote tombent sur la **même jonction** (`GOAL-001-T16`).

---

## GOAL-008 — L'API de pilotage

**État : TODO** — non découpé.

La surface publique (SPECS.md §4.8) : dire ce qui passe, accepter un vote `stop`
ou `encore`, refuser explicitement pendant un jingle ou un flash, dire si la
chaîne tourne.

Elle traduit en HTTP des décisions prises par le noyau ; elle n'en prend aucune.

**Aucun autre client n'est écrit** — pas de bot, pas de Telegram. L'API existe
parce que `GOAL-009` s'en sert, pas parce qu'un autre client pourrait s'en servir
un jour (AGENTS.md §2).

---

## GOAL-009 — L'interface web — Flask et Jinja2

**État : TODO** — non découpé.

Une page : ce qui passe, et deux boutons. Servie par Flask, mise en page par des
gabarits Jinja2, destinée à un téléphone posé à côté de l'enceinte.

Elle appelle **l'API de `GOAL-008`**, jamais le noyau. Aucune décision dans un
gabarit.

Elle ne configure rien : le TOML reste le seul point d'entrée des réglages
(SPECS.md §6).

---

## GOAL-010 — Les émissions : podcasts programmés

**État : TODO** — non découpé.

Un épisode de podcast diffusé à heure dite, déclaré au TOML par `jours` et
`heure` (SPECS.md §4.11). Une seule émission à la fois ; elle **remplace** la
programmation au lieu de s'y insérer, donc elle suspend la grille thématique et
la non-répétition pour sa durée.

Ce qui se déduit déjà des règles existantes, et n'a pas à être rediscuté : elle
ne coupe pas un morceau, elle n'est jamais abandonnée pour retard, `stop` et
`encore` y sont refusés, un épisode indisponible fait rester sur la musique.

**Débloqué le 2026-08-30** : les trois décisions sont tranchées.

- **n°13** — rattrapage borné à la durée de l'épisode. **Conséquence à ne pas
  manquer au découpage** : la durée n'étant connue qu'après lecture du flux, le
  démarrage de la chaîne doit interroger le podcast **avant** de savoir s'il s'en
  servira. C'est le seul endroit du projet où le démarrage dépend d'un appel
  réseau qui peut ne servir à rien.
- **n°14** — l'épisode le plus récent. Aucun état retenu : l'absence de
  persistance est préservée.
- **n°15** — les jingles dus pendant une émission sont abandonnés. Pour le noyau,
  une émission n'est donc pas une insertion dans la file mais une **suspension**
  de tout ce qui l'alimente.

Deux constats de `GOAL-002` conditionnent ces décisions
([docs/podcast.md](./docs/podcast.md) §4) : la **date de publication** doit être
fiable, et la **durée** lisible sans télécharger le fichier. Si l'un manque, la
décision correspondante est à rejouer.
