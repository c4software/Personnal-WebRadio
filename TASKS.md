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

**Prochaine tâche** : `GOAL-004-T01` — décoder une entrée vers le PCM du flux.

**Les sept lots restants sont découpés** (2026-08-30), soit 71 tâches.
`GOAL-012` s'ajoute en fin de parcours, découpé lui aussi : les trois décisions
qui le bloquaient (n°16 à n°18) ont été tranchées le 2026-08-30.

**Neuf lots, 83 tâches ouvertes.** Décisions : **19 tranchées sur 21**. Restent
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
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[ ]` |
| GOAL-005 | La grille horaire et les moments thématiques | `[ ]` |
| GOAL-006 | Jingles horaires et flashs France Info | `[ ]` |
| GOAL-007 | Le pilotage : `stop` et `encore` dans le noyau | `[ ]` |
| GOAL-008 | L'API de pilotage | `[ ]` |
| GOAL-009 | L'interface web — Flask et Jinja2 | `[ ]` |
| GOAL-010 | Les émissions : podcasts programmés | `[ ]` |
| GOAL-011 | Conteneurisation : Docker et Compose | `[ ]` — après GOAL-004 |
| GOAL-012 | Les votes pondèrent les tirages suivants | `[ ]` |

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
- [ ] `GOAL-002-T03` ffmpeg : insérer un fichier d'une autre origine (jingle) sans interrompre
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

## GOAL-004 — Le flux : ffmpeg, fan-out, démarrage à la demande

**État : TODO**

Le cœur exécutable. `GOAL-002` l'a largement pré-décidé : réencodage
systématique, voie PCM, un seul chemin d'insertion, `-re` pour cadencer.

- [ ] `GOAL-004-T01` `adapters/ffmpeg/` : décoder une entrée vers le PCM du flux
- [ ] `GOAL-004-T02` L'encodeur unique, cadencé — sans lui la bibliothèque part en minutes
- [ ] `GOAL-004-T03` Le fan-out : un flux, N connexions, un auditeur lent n'en ralentit aucun
- [ ] `GOAL-004-T04` `adapters/http/` : servir le flux, en-têtes `icy-*` compris
- [ ] `GOAL-004-T05` Démarrage à la première connexion
- [ ] `GOAL-004-T06` **Arrêt à la dernière — tout l'arbre de processus**, déconnexion brutale comprise
- [ ] `GOAL-004-T07` La file prend de l'avance : résoudre pendant que le courant joue
- [ ] `GOAL-004-T08` Les erreurs au démarrage sont fatales et se disent (SPECS.md §4.1)
- [ ] `GOAL-004-T09` Les pannes en cours : tenir, réessayer, puis couper en le disant (SPECS.md §5.1)
- [ ] `GOAL-004-T10` **Écoute réelle** : brancher VLC, un navigateur, une enceinte — et la matrice de `docs/flux-icy.md` §6
- [ ] `GOAL-004-T11` Carte du dépôt

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

**État : TODO**

À faire **juste après `GOAL-004`** : c'est le premier moment où il y a quelque
chose à faire tourner. Le faire avant serait emballer du vide ; beaucoup plus
tard, ce serait découvrir tard les surprises de réseau et de volumes.

- [ ] `GOAL-011-T01` `Dockerfile` : image Python fine, **ffmpeg épinglé à la version relevée**
- [ ] `GOAL-011-T02` `docker-compose.yml` : un service, `env_file`, ports
- [ ] `GOAL-011-T03` Volumes : configuration et jingles en **lecture seule**, état SQLite en écriture
- [ ] `GOAL-011-T04` **Le conteneur joint-il Navidrome ?** `http://music` est résolu par l'hôte, pas forcément par le conteneur
- [ ] `GOAL-011-T05` Arrêt propre : `SIGTERM` doit arrêter tout l'arbre, pas seulement le processus 1
- [ ] `GOAL-011-T06` Le conteneur ne tourne pas en `root`, et n'écrit que dans le volume d'état
- [ ] `GOAL-011-T07` `CONTRIBUTING.md` et `README.md` : lancer en conteneur, et vérifier **hors** conteneur

> **`T05` est le piège classique** : un processus 1 qui ignore `SIGTERM` laisse
> Docker tuer brutalement au bout de dix secondes — et l'on retrouve les
> orphelins de `GOAL-004-T06`, cette fois invisibles.

---

## GOAL-005 — La grille horaire et les moments thématiques

**État : TODO**

- [ ] `GOAL-005-T01` `adapters/config/` : lire le TOML, et **refuser** un secret qui s'y trouverait
- [ ] `GOAL-005-T02` Le schéma de configuration, validé au démarrage, erreurs nommant la clé fautive
- [ ] `GOAL-005-T03` `core/grille.py` : quelle plage à quelle heure — l'horloge est injectée
- [ ] `GOAL-005-T04` La grille n'est consultée **qu'au tirage** (SPECS.md §7 n°5) : un morceau finit dans sa plage
- [ ] `GOAL-005-T05` Le repli d'une plage sans musique sur le tirage libre, journalisé
- [ ] `GOAL-005-T06` `adapters/sources/navidrome/` : authentification par jeton dérivé
- [ ] `GOAL-005-T07` **Lire `status` dans le corps à chaque appel** — un mot de passe faux rend HTTP 200
- [ ] `GOAL-005-T08` Le tirage et le filtre par genre, avec la troncature à 500 **connue et respectée**
- [ ] `GOAL-005-T09` `pistes_de(artiste)` : `search3` filtré sur l'égalité exacte du nom
- [ ] `GOAL-005-T10` Traduire les erreurs Subsonic en `SourceIndisponible` — les deux régimes, HTTP 200 et 404
- [ ] `GOAL-005-T11` Tests de l'adaptateur contre des réponses **littérales**, HTML en 200 compris
- [ ] `GOAL-005-T12` Carte du dépôt

> Les tâches `T06` à `T11` sont entièrement pré-écrites par
> [docs/navidrome.md](./docs/navidrome.md) : chacune correspond à un piège
> constaté, et à lui seul.

---

## GOAL-006 — Jingles horaires

**État : TODO**

- [ ] `GOAL-006-T01` `core/jingles.py` : quel jingle est dû, d'après l'horloge injectée
- [ ] `GOAL-006-T02` Résoudre `HHh.mp3` depuis l'heure — aucune table de correspondance
- [ ] `GOAL-006-T03` **Un jingle absent ne signale rien** ; un jingle illisible journalise
- [ ] `GOAL-006-T04` L'empilement : tous les jingles dus, dans l'ordre chronologique
- [ ] `GOAL-006-T05` L'insertion à la jonction, par **le** chemin unique de `GOAL-004`
- [ ] `GOAL-006-T06` **Écoute réelle** : le niveau d'un vrai jingle contre la musique
- [ ] `GOAL-006-T07` Carte du dépôt

> **Le flash France Info ne figure plus dans ce Goal.** Aucune source n'a pu
> être confirmée ([docs/franceinfo.md](./docs/franceinfo.md) §1.5), et trois
> questions attendent l'auteur. Si la réponse est « franceinfo en 3 minutes »,
> les flashs deviennent une **émission** et rejoignent `GOAL-010` sans une ligne
> de code supplémentaire.

> **`T06` est le seul moyen de savoir** si un jingle écrase la musique. Le relevé
> ne pouvait pas le dire : ses fichiers d'essai étaient des sinus de même
> amplitude ([docs/ffmpeg.md](./docs/ffmpeg.md) §2.ter).

---

## GOAL-007 — Le pilotage : `stop` et `encore` dans le noyau

**État : TODO**

- [ ] `GOAL-007-T01` `core/controle.py` : l'effet de `stop` sur ce que la file rendra
- [ ] `GOAL-007-T02` L'effet d'`encore` : même artiste, puis même genre, puis tirage libre
- [ ] `GOAL-007-T03` `encore` **outrepasse** la non-répétition, et ses morceaux n'entrent pas dans la fenêtre
- [ ] `GOAL-007-T04` L'enchaînement illimité, borné par l'épuisement de l'artiste
- [ ] `GOAL-007-T05` Le **refus motivé** pendant un jingle, un flash ou une émission
- [ ] `GOAL-007-T06` Le jingle de vote `encore.mp3`, marqué dû, diffusé **en dernier** à la jonction

---

## GOAL-008 — L'API de pilotage

**État : TODO**

- [ ] `GOAL-008-T01` `adapters/web/api/` : la surface publique, sans Flask dans le noyau
- [ ] `GOAL-008-T02` Dire ce qui passe : titre, artiste, et **de quelle nature** — musique, jingle, flash, émission
- [ ] `GOAL-008-T03` Dire si la chaîne tourne
- [ ] `GOAL-008-T04` Accepter un vote `stop` et un vote `encore` — une voix suffit
- [ ] `GOAL-008-T05` Traduire le refus du noyau en réponse HTTP **motivée** — un refus muet ressemble à une panne
- [ ] `GOAL-008-T06` Tests : l'API n'appelle jamais le noyau autrement que par les décisions de `GOAL-007`

---

## GOAL-009 — L'interface web — Flask et Jinja2

**État : TODO**

- [ ] `GOAL-009-T01` Le serveur Flask, monté à côté du flux, sans le perturber
- [ ] `GOAL-009-T02` Un gabarit Jinja2 : ce qui passe, et deux boutons
- [ ] `GOAL-009-T03` Les boutons appellent **l'API**, jamais le noyau — l'interdit est contrôlé
- [ ] `GOAL-009-T04` L'affichage d'un refus, quand un vote tombe pendant un jingle ou une émission
- [ ] `GOAL-009-T05` Utilisable à une main, sur un téléphone posé à côté de l'enceinte
- [ ] `GOAL-009-T06` **Regarder la page sur un vrai téléphone** — aucun test ne le fera
- [ ] `GOAL-009-T07` Carte du dépôt

---

## GOAL-010 — Les émissions : podcasts programmés

**État : TODO**

- [ ] `GOAL-010-T01` `adapters/podcast/` : lire un flux RSS, en extraire les épisodes
- [ ] `GOAL-010-T02` Ne retenir que les `full` — écarter `bonus` et `trailer`
- [ ] `GOAL-010-T03` **Ne pas se fier à `enclosure/length`** : Acast insère de la publicité, le fichier servi diffère
- [ ] `GOAL-010-T04` `adapters/etat/` : la base SQLite, une table, écriture atomique
- [ ] `GOAL-010-T05` `core/emissions.py` : quelle émission est due, d'après la grille déclarée
- [ ] `GOAL-010-T06` **Deux émissions à la même heure refusent le démarrage**, en les nommant
- [ ] `GOAL-010-T07` L'épisode le plus récent **non encore diffusé** ; sinon la case est sautée
- [ ] `GOAL-010-T08` Le rattrapage borné à la durée de l'épisode — la durée se lit **avant** de décider
- [ ] `GOAL-010-T09` Une émission **suspend** la grille, la non-répétition et les jingles
- [ ] `GOAL-010-T10` Un épisode indisponible ou tronqué : rester sur la musique, journaliser
- [ ] `GOAL-010-T11` **Écoute réelle** : le niveau d'un épisode contre la musique, et la jonction
- [ ] `GOAL-010-T12` Carte du dépôt

> **`T08` est la seule tâche du projet où le démarrage dépend d'un appel réseau
> qui peut ne servir à rien** (ARCHITECTURE.md §5.2). Elle porte aussi le chiffre
> qui a surpris : la fenêtre de rattrapage peut atteindre **2 h 50** sur LEGEND
> ([docs/podcast.md](./docs/podcast.md) §3.1).

---

## GOAL-012 — Les votes pondèrent les tirages suivants

**État : TODO**

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

- [ ] `GOAL-012-T01` `adapters/etat/` : la table `votes`, et la décroissance à l'écriture
- [ ] `GOAL-012-T02` La décroissance **à la lecture** aussi, entre `vu_le` et maintenant
- [ ] `GOAL-012-T03` `core/ponderation.py` : des scores au multiplicateur, borné à `[0,25 ; 4]`
- [ ] `GOAL-012-T04` La portée croisée : `stop` = 1 sur la piste, 0,25 sur l'artiste ; `encore` l'inverse
- [ ] `GOAL-012-T05` `core/rng.py` gagne `choisir_pondere()` — une capacité **nouvelle**, pas un réglage
- [ ] `GOAL-012-T06` **Le tirage pondéré reste rejouable** à graine et poids fixés
- [ ] `GOAL-012-T07` La file reçoit les poids, elle ne va pas les chercher — la frontière du noyau tient
- [ ] `GOAL-012-T08` Enregistrer le vote au moment où il est **accepté**, jamais quand il est refusé
- [ ] `GOAL-012-T09` Les clés de configuration : plancher, plafond, demi-vie, poids croisé
- [ ] `GOAL-012-T10` Une base absente ou vide se comporte comme des poids neutres
- [ ] `GOAL-012-T11` **Écoute sur plusieurs semaines** — le seul moyen de savoir si la radio s'est resserrée
- [ ] `GOAL-012-T12` Carte du dépôt

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
