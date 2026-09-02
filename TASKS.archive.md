# TASKS.archive.md — L'histoire des Goals terminés

Le détail des Goals entièrement `[x]`, déplacé ici à leur clôture pour que
[TASKS.md](./TASKS.md) reste court : c'est lui que chaque session lit, et une
mémoire qui grossit à chaque Goal finit par coûter plus qu'elle ne sert.

Ce fichier ne se lit que pour l'histoire — pourquoi une décision a été prise,
ce qu'un incident a appris. Les commandes du Harness ne le chargent jamais.
On y **ajoute** en fin de clôture ; on n'y retouche rien.

---

## Ce que la « Phase courante » a traversé

Les mises à jour successives, telles qu'elles ont été écrites — les plus
récentes d'abord.

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
- [x] `GOAL-001-T14` **Neuf décisions restent ouvertes** dans SPECS.md §7 — deux
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
- [x] `GOAL-001-T17` **L'écart d'anticipation sur les sources doit rester
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

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

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
- [x] `GOAL-004-T10` **Écoute réelle** : brancher VLC, un navigateur, une enceinte — et la matrice de `docs/flux-icy.md` §6
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
> [docs/subsonic.md](./docs/subsonic.md) : chacune correspond à un piège
> constaté, et à lui seul.

---

## GOAL-006 — Jingles horaires

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

- [x] `GOAL-006-T01` `core/jingles.py` : quel jingle est dû, d'après l'horloge injectée
- [x] `GOAL-006-T02` Résoudre `HHh.mp3` depuis l'heure — aucune table de correspondance
- [x] `GOAL-006-T03` **Un jingle absent ne signale rien** ; un jingle illisible journalise
- [x] `GOAL-006-T04` L'empilement : tous les jingles dus, dans l'ordre chronologique
- [x] `GOAL-006-T05` L'insertion à la jonction, par **le** chemin unique de `GOAL-004`
- [x] `GOAL-006-T06` **Écoute réelle** : le niveau d'un vrai jingle contre la musique
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

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

- [x] `GOAL-009-T01` Le serveur Flask, monté à côté du flux, sans le perturber
- [x] `GOAL-009-T02` Un gabarit Jinja2 : ce qui passe, et deux boutons
- [x] `GOAL-009-T03` Les boutons appellent **l'API**, jamais le noyau — l'interdit est contrôlé
- [x] `GOAL-009-T04` L'affichage d'un refus, quand un vote tombe pendant un jingle ou une émission
- [x] `GOAL-009-T05` Utilisable à une main, sur un téléphone posé à côté de l'enceinte
- [x] `GOAL-009-T06` **Regarder la page sur un vrai téléphone** — aucun test ne le fera
- [x] `GOAL-009-T07` Carte du dépôt

---

## GOAL-010 — Les émissions : podcasts programmés

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

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
- [x] `GOAL-010-T11` **Écoute réelle** : le niveau d'un épisode contre la musique, et la jonction
- [x] `GOAL-010-T12` Carte du dépôt

> **`T08` est la seule tâche du projet où le démarrage dépend d'un appel réseau
> qui peut ne servir à rien** (ARCHITECTURE.md §5.2). Elle porte aussi le chiffre
> qui a surpris : la fenêtre de rattrapage peut atteindre **2 h 50** sur LEGEND
> ([docs/podcast.md](./docs/podcast.md) §3.1).

---

## GOAL-012 — Les votes pondèrent les tirages suivants

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

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
- [x] `GOAL-012-T11` **Écoute sur plusieurs semaines** — le seul moyen de savoir si la radio s'est resserrée
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

`docs/subsonic.md` §2.6 a été établi pour ce Goal, et il change deux choses :

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

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30
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
- [x] `GOAL-015-T08` **Écoute réelle** : le niveau de la parole (−16,2 LUFS mesurés) contre la musique, et la coupure « en cours de phrase » à la fin de la case
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

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30

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
- [x] `GOAL-016-T12` **Écoute réelle** : fondus, niveau, VLC / navigateur / enceinte — la matrice de `docs/flux-icy.md` §6
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
- [x] `GOAL-018-T06` **Regarder sur le vrai téléphone** — la seule chose qu'aucun test ne fera

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
- [x] `GOAL-022-T03` **Écoute réelle** du fondu court, avec un vrai jingle dans `jingles/`

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
- [x] `GOAL-024-T04` **Écoute réelle** : encore → `encore.mp3` → un morceau du même artiste

---

## GOAL-025 — Une chaîne YouTube comme émission

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30
dernière vidéo de @hardisk ») ; tout est fait et constaté sauf l'écoute

Relevé [docs/youtube.md](./docs/youtube.md) : handle → `channel_id` par le lien
canonique ; flux Atom sans clé d'API (15 vidéos, sans durée) ; `yt-dlp` rend la
durée et l'URL audio directe, que ffmpeg décode exactement ; cette URL expire —
on résout **au moment de diffuser**, et seulement la candidate.

- [x] `GOAL-025-T01` `adapters/youtube/` : la chaîne comme un flux d'épisodes — même contrat que le podcast, le planificateur ne fait pas la différence (modulaire, comme demandé)
- [x] `GOAL-025-T02` La dernière vidéo **non encore diffusée**, la case bornée par sa durée réelle, la trace par `videoId` — les règles n°13/n°14, réutilisées telles quelles
- [x] `GOAL-025-T03` `youtube = "https://…/@chaine"` au TOML, exclusif de `feed` et `stream` ; `[youtube] timeout_seconds` ; chaîne injoignable ou `yt-dlp` en échec = musique, journalisé
- [x] `GOAL-025-T04` `yt-dlp` épinglé (2026.8.19) dans l'image `radio` ; **résolution réelle constatée depuis le conteneur**
- [x] `GOAL-025-T05` **Écoute réelle** : mercredi 20 h — la jonction, le niveau d'une vidéo contre la musique, et le ffmpeg de Liquidsoap sur googlevideo (constaté seulement avec celui de l'hôte)

---

## GOAL-026 — Les votes ne portent que sur l'artiste (n°16 révisée)

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, à l'écoute : « éviter
les surpondérations »

- [x] `GOAL-026-T01` `vote_weight` : 1 sur l'artiste, 0 sur la piste, `stop` comme `encore` — et un poids nul ne s'écrit pas en base (plus de lignes à zéro)
- [x] `GOAL-026-T02` La clé `cross_weight` disparaît du schéma et des TOML — une clé sans effet serait un mensonge
- [x] `GOAL-026-T03` SPECS §4.12 et n°16 révisés ; les anciennes lignes « piste » en base s'éteignent par la demi-vie, ou d'un ✕ sur la page

---

## GOAL-027 — Le journal des titres, visible dans l'interface

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30 (SPECS §7 n°27)

- [x] `GOAL-027-T01` La table `historique`, écrite quand un titre **commence** (jamais les jingles), bornée à **24 heures** (révisé par l'auteur) — un journal, pas une archive (§2 tient) ; la page le pagine heure par heure
- [x] `GOAL-027-T02` `GET /api/history` et l'onglet Historique, du plus récent au plus ancien

> **Constaté pendant ce Goal, à la première diffusion YouTube réelle**
> (docs/youtube.md §4) : mime `audio/webm` inconnu du diffuseur et résolution
> bornée à 29 s pour un fichier qu'elle télécharge — corrigés (m4a préféré,
> table complétée, délai à 120 s). Et une faiblesse consignée : la trace
> « diffusé » s'écrit à la décision, pas au démarrage du son — deux essais
> perdus ainsi.

---

## GOAL-028 — YouTube sans blanc : téléchargé en fond, servi en local

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30 : « il ne faudrait pas
de blanc, 30/60 s sans rien ça ne va pas »

- [x] `GOAL-028-T01` `radio` télécharge la vidéo en tâche de fond (`.part` puis renommage) pendant que la musique continue ; la case ne rend l'émission que **fichier prêt** — résolution instantanée, zéro blanc
- [x] `GOAL-028-T02` Le cache dans le volume d'état, partagé **en lecture seule** avec le diffuseur ; la vidéo lue **s'efface dès que la suite commence**, et le fichier porte un **nom stable par émission** (+ témoin `.id`) — le téléchargement suivant écrase, jamais d'accumulation, jamais un reste servi à la place de la candidate
- [x] `GOAL-028-T03` Un téléchargement en échec ou trop tard : musique, journalisé — la case borne tout

---

## GOAL-029 — Génériques d'ouverture et de fermeture des moments

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30 (« comme une radio classique »)

- [x] `GOAL-029-T01` `intro`/`outro` sur les plages **et** les programmes — des noms de fichiers dans le dossier des jingles, optionnels : absents, rien ne se passe et rien ne se signale (le régime de tous les jingles, SPECS.md §4.3)
- [x] `GOAL-029-T02` À la jonction où le moment **effectif** change (programme d'abord, comme pour la musique) : générique de fin de l'ancien, jingles horaires dus, générique d'ouverture du nouveau — dans cet ordre
- [x] `GOAL-029-T03` Une chaîne qui démarre **au milieu** d'un moment ne rejoue pas son générique
- [x] `GOAL-029-T04` **Écoute réelle**, avec de vrais génériques dans `jingles/`

---

## GOAL-030 — Les jours de la configuration passent à l'anglais

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30, pour la cohérence :
les clés du TOML sont en anglais depuis cf5c1e5, `days = "all"` l'était déjà,
seuls les noms de jours restaient en français.

- [x] `GOAL-030-T01` `monday` … `sunday` partout — noyau, schéma, configs, exemples, tests ; un jour français est désormais **refusé** en nommant les jours attendus
- [x] `GOAL-030-T02` L'interface, elle, **continue d'afficher en français** — la langue de la configuration n'est pas celle de la page

---

## GOAL-031 — Le jingle d'« encore » se configure, les exemples ont leurs génériques

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30

- [x] `GOAL-031-T01` `[jingles] encore = "…"` — `encore.mp3` n'est plus qu'un défaut ; les jingles horaires restent nommés par leur heure, c'est leur programmation
- [x] `GOAL-031-T02` Chaque plage et programme de `webradio.exemple.toml` montre ses `intro`/`outro`

---

## GOAL-032 — Les jingles horaires rangés dans `hours/`

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30 : « trop de fichiers »

- [x] `GOAL-032-T01` `jingle_name` rend `hours/14h.mp3` — l'« encore » et les génériques restent à la racine, et leurs noms libres acceptent des sous-chemins
- [x] `GOAL-032-T02` Le dossier local de l'auteur migré (46 fichiers, variantes `-b`/`-c` comprises — inutilisées par l'app, rangées avec), structure versionnée

---

## GOAL-033 — Les variantes de jingles, tirées au hasard

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30
portait déjà `06h-b.mp3` et `06h-c.mp3` ; reste l'écoute réelle

- [x] `GOAL-033-T01` Tout jingle — horaire, « encore », générique — accepte des variantes `nom-a.mp3`, `nom-b.mp3`… : l'une est tirée **au hasard injecté** (rejouable), et le fichier de base devient optionnel dès qu'une variante existe
- [x] `GOAL-033-T02` **Écoute réelle** : la rotation s'entend-elle, sur plusieurs heures ?

---

## GOAL-034 — L'encore agit sur la chanson suivante, pas celle d'après

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30
étrange ») ; codé et vérifié, le déploiement attend une fenêtre hors écoute

Le diffuseur a toujours un morceau d'avance : l'effet d'un encore — jingle
puis même artiste — arrivait donc après la chanson déjà demandée.

- [x] `GOAL-034-T01` Un encore **accepté** ordonne `POST /requeue` au diffuseur, qui jette son avance (`set_queue([])`) : à la fin de la chanson en cours viennent le jingle puis le même artiste
- [x] `GOAL-034-T02` ~~jeté~~ **Rien n'est jeté** : la charnière met l'avance de côté et le programme la ressert **après** le jingle et le titre forcé — Yamê → encore.mp3 → Yamê-2 → Tryo, le schéma de l'auteur
- [x] `GOAL-034-T03` Déployé sur le feu vert de l'auteur, pile arrêtée puis relancée ; **reste l'écoute réelle** : encore → jingle → même artiste → la chanson prévue

---

## GOAL-035 — « À suivre » : la file s'affiche à l'antenne

**État : TERMINÉ** — validé à l'écoute par l'auteur le 2026-08-30
queue ? ») ; codé et vérifié, déploiement dans la même fenêtre que GOAL-034

- [x] `GOAL-035-T01` La charnière expose le morceau **demandé, pas encore à l'antenne** ; `/api/on-air` le rend (`up_next`), la page l'affiche sous le moment
- [x] `GOAL-035-T02` Déployer puis regarder : l'« à suivre » colle-t-il à ce qui sort réellement, jonction après jonction ?

---

## GOAL-036 — La CI : vérification puis image publiée sur GHCR

**État : TERMINÉ** — demandé par l'auteur le 2026-08-30

- [x] `GOAL-036-T01` GitHub Actions rejoue **la** commande de vérification du dépôt (`./verifier.sh`, `liquidsoap --check` compris — Docker est sur le runner), jamais une variante allégée
- [x] `GOAL-036-T02` L'image `radio` se construit sur du vérifié et se publie sur `ghcr.io/c4software/personnal-webradio` (`latest` + sha) depuis `master` seulement ; une PR construit sans publier. Le service `liquidsoap` n'a rien à construire : image amont épinglée, script monté

---

## GOAL-037 — Une plage dont le genre ou l'artiste est tiré au sort

**État : TERMINÉ** — demandé par l'auteur le 2026-08-31, plan validé le même
jour. Code écrit, testé, vérification complète constatée (`radio.liq` compris).
**Reste l'écoute réelle** : qu'une heure d'un artiste tiré au sort tienne,
fenêtre de non-répétition rétrécie comprise (AGENTS.md §4.1, §1.2).

Une plage `[[bands]]` peut déclarer `random = "genre"` ou `random = "artist"`
au lieu d'énumérer ses valeurs : la radio tire elle-même un genre (ou un
artiste) de la bibliothèque **au début de l'occurrence**, et s'y tient jusqu'à
la fin de la plage. L'occurrence suivante retire.

Choix validés par l'auteur : greffé sur `[[bands]]` (pas un 4ᵉ mécanisme, pas
une émission) ; tirage **figé sur l'occurrence** ; réservoir = **toute la
bibliothèque** (genre : `source.genres()` ; artiste : l'artiste d'une piste
tirée librement — aucune capacité nouvelle au `Protocol`) ; la configuration
**déclare** si c'est un genre ou un artiste. Aucune persistance : le tirage vit
en mémoire, une occurrence à la fois. Consigné en SPECS.md §7 n°28.

- [x] `GOAL-037-T01` `Band.random_theme` + invariant révisé (exactement un de `genres`/`artists`/`random_theme`), et `Band.occurrence_start(instant)` — le début de l'occurrence courante, minuit enjambé compris
- [x] `GOAL-037-T02` `core/mystery.py` : `RandomTheme(source, random)` tire la contrainte de l'occurrence, la mémorise (une seule entrée), rend `None` sans mémoriser sur `SourceUnavailable` ou réservoir vide — retentera à la jonction suivante, journalisé une fois
- [x] `GOAL-037-T03` `Schedule.constraint_to_draw` délègue les plages `random_theme` au `ThemeResolver` injecté — type déclaré dans `bands.py` pour éviter le cycle avec `mystery.py` ; l'horloge n'est plus lue qu'une fois ; câblage dans `app/main.py`
- [x] `GOAL-037-T04` Le TOML : clé `random` sur `[[bands]]`, exactement une des trois clés, sorte inconnue nommée dans le refus. Les valeurs acceptées sont **importées du noyau**, pas recopiées
- [x] `GOAL-037-T05` `_libelle_du_moment` et `_libelle_de_plage`, deux fonctions pures : « Moment · Air (au hasard) » à l'antenne, « Au hasard · un artiste » au planning. Le gabarit joint déjà la liste : rien à y changer
- [x] `GOAL-037-T06` SPECS.md §4.4 + §6 + décision n°28, `webradio.exemple.toml`, README, carte du dépôt pour `core/mystery.py`

### Dette laissée

L'écoute réelle de T05 n'a pas eu lieu (AGENTS.md §1.2 : il n'existe pas de cas
d'arrêt « demander une écoute avant de cocher »). C'est la conséquence assumée
de la décision ouverte n°9 de SPECS.md.

---

## GOAL-038 — Le Compose de production tire l'image publiée ; un Compose de dev construit localement

**Terminé le 2026-08-31.**

La CI publie l'image du service `radio` sur GHCR depuis GOAL-036, mais le
Compose continuait de construire localement, la bascule n'étant qu'un
commentaire. Le défaut s'inverse : `docker compose up` tire du vérifié, et
construire le code en cours devient le geste explicite du développement.

**Décision** : une surcharge `-f docker-compose.dev.yml` plutôt qu'un
`docker-compose.override.yml`, que Compose chargerait automatiquement — un
`docker compose up` chez un utilisateur reconstruirait alors en local,
l'inverse de l'objectif. La surcharge ne redéfinit que la provenance de
l'image (`build: .`, `local-webradio:dev`) : volumes, réseau et santé restent
ceux de la production. Consigné en ARCHITECTURE.md §8.5.4.

- [x] `GOAL-038-T01` `docker-compose.yml` référence `ghcr.io/c4software/personnal-webradio:latest` au lieu de `build: .` ; README (« Lancer », note `docker login ghcr.io`) ajusté ; validé par `docker compose config -q`
- [x] `GOAL-038-T02` `docker-compose.dev.yml` : surcharge minimale (`build: .`, image `local-webradio:dev`) ; documentation dev (README, CONTRIBUTING), ARCHITECTURE §8.5.4 et carte du dépôt §9 ; validé par `docker compose -f docker-compose.yml -f docker-compose.dev.yml config -q`

---

## GOAL-039 — Parler Subsonic plutôt que Navidrome, et tirer dans toute la bibliothèque

**Terminé le 2026-08-31.**

Deux défauts d'un coup. Le vocabulaire : l'adaptateur parlait le protocole
Subsonic mais portait le nom d'un serveur, Navidrome — qui n'est que l'instance
contre laquelle le relevé a été établi. Et le tirage : il puisait dans
`getRandomSongs`, tronqué à 500 en silence — sur une bibliothèque de 5704
pistes, la radio tournait en rond dans un douzième de la musique.

- [x] `GOAL-039-T01` Renommage code : `SubsonicSource`, `SubsonicSettings`,
      `SubsonicCredentials`, `adapters/sources/subsonic.py`, `[subsonic]`,
      `SUBSONIC_*` (renommage sec, l'erreur au démarrage nomme les variables) ;
      `.env` et `webradio.toml` locaux mis à jour
- [x] `GOAL-039-T02` `docs/navidrome.md` → `docs/subsonic.md` ; SPECS,
      ARCHITECTURE, README, AGENTS, CLAUDE, CONTRIBUTING et le harness parlent
      du protocole ; Navidrome ne subsiste que là où il désigne ce serveur-là ;
      scope de commit `navidrome` → `subsonic` ; le littéral relevé
      `"type": "navidrome"` altéré par T01 restauré
- [x] `GOAL-039-T03` Relevé de la pagination contre l'instance réelle :
      `search3` à requête vide rend tout (5704, ordre stable, pas de plafond à
      500) ; `getSongsByGenre` pagine par `offset` mais tronque à 500 par
      appel ; les `songCount` de `getGenres` mentent (Rock : 357 annoncées,
      201 rendues par trois chemins concordants)
- [x] `GOAL-039-T04` `tracks()` réunit la bibliothèque entière page par page
      (fin = page courte, jamais un compteur) ; un serveur qui ignore l'offset
      est détecté (page sans piste nouvelle → arrêt journalisé) ;
      `sample_size` retiré de la configuration et refusé s'il traîne encore ;
      constaté contre l'instance : 5704 pistes, Rock 201, Chanson française
      1253
- [x] `GOAL-039-T05` SPECS §6 (plus de taille d'échantillon), clôture et
      archivage

### Décisions prises

- Variables d'environnement renommées sans repli sur les anciens noms : le
  démarrage échoue en nommant ce qui manque, c'est le régime voulu de la
  configuration (SPECS.md §6.2).
- La taille de page (500) est une constante de l'adaptateur, pas une clé de
  configuration : c'est le plafond constaté de `getSongsByGenre`, une
  propriété du serveur (docs/subsonic.md §2.7.2).
- Le filtre par genre reste côté serveur (`getSongsByGenre`, insensible à la
  casse) : le relevé montre qu'il coïncide exactement avec un filtre local
  sur le champ `genre` (1253 = 1253), et il évite de rapatrier la
  bibliothèque pour une plage thématique.

### Dette laissée

Ce que la variété retrouvée change à l'antenne — 5704 pistes tirables au lieu
de 500 — ne se constate qu'en écoutant sur la durée (AGENTS.md §4.1). Un
`tracks()` complet coûte désormais douze appels HTTP au lieu d'un, à chaque
tirage, et rien n'est mis en cache — le coût n'a pas été mesuré ; si un blanc
s'entendait un jour à la jonction, la mesure précéderait le remède.
*Soldée par GOAL-040 : la bibliothèque est servie de mémoire pendant
`cache_seconds` (une heure par défaut).*

---

## GOAL-040 — Un cache de bibliothèque dans l'adaptateur Subsonic

**Terminé le 2026-08-31.**

Depuis GOAL-039, chaque tirage parcourait la bibliothèque entière : ~12 appels
HTTP par changement de chanson, pour des données qui bougent rarement.

- [x] `GOAL-040-T01` La clé `cache_seconds` sur `[subsonic]` : `0` = sans
      cache, valeur négative refusée en nommant la clé ; exemples TOML
- [x] `GOAL-040-T02` Le cache dans l'adaptateur : horloge injectée
      (`core/clock.py`), une entrée par clé de tirage, expiration stricte à la
      lecture, copie rendue à chaque appel (personne ne mute l'entrée
      partagée) ; seul un parcours réussi entre au cache ; câblé dans
      `main.py` ; tests au `FrozenClock`, transport qui compte ses appels
- [x] `GOAL-040-T03` SPECS §6, dette de GOAL-039 soldée, clôture

### Décisions prises

- **Défaut de 3600 s** — demandé par l'auteur en cours de Goal (T01 était
  partie sur 600 s) : une heure de retard au pire sur un ajout, contre douze
  appels économisés par tirage.
- **Une panne ne sert jamais un cache périmé** : `SourceIndisponible` se
  propage comme avant, le régime de panne de SPECS.md §5 reste inchangé et
  visible. Servir du périmé en panne serait un autre choix, à décider s'il
  manque un jour.
- **`tracks_by` et les listes de lecture restent sans cache** : l'« encore »
  est rare, et une liste renommée ne doit pas rester résolue sur un
  identifiant périmé (docs/subsonic.md §2.6).

---

## GOAL-041 — Péremption des jingles horaires, et reprise à neuf après une longue pause

**Terminé le 2026-08-31.**

Constaté à l'antenne : le jingle de 19 h entendu à 22 h 28, après 3 h 30 sans
auditeur. L'avance du diffuseur (un morceau demandé d'avance) avait traversé la
pause intacte — angle mort entre la décision n°4 (« aucune péremption ») et
SPECS.md §4.7 (la pause au débranchement).

- [x] `GOAL-041-T01` Relevé Liquidsoap (docs/liquidsoap.md §5.bis) : l'avance
      survit à la pause ; le reliquat du morceau interrompu passe d'abord ;
      `set_queue([])` au repos ne recomplète pas ; annoncer avant de basculer
      le ref rend la purge sans course ; un skip sans morceau en cours mange
      le premier morceau frais
- [x] `GOAL-041-T02` Noyau : un jingle horaire à plus du délai de péremption
      de son heure pleine n'est plus dû — heure par heure, l'encore ne périme
      jamais, `None` = ancienne règle
- [x] `GOAL-041-T03` Config `jingles.expiry_seconds` (900 par défaut, 0 =
      jamais) ; SPECS §4.3, §6.2, n°4 amendée, n°29
- [x] `GOAL-041-T04` Charnière : pause datée à la première annonce à zéro ;
      au retour après plus de `playout.resume_fresh_seconds` (900 par défaut,
      0 = jamais), purge — `/requeue`, `/skip` si un morceau passait,
      `forget_pending()` côté programme ; SPECS §4.7 corrigé (le reliquat
      passe bel et bien), §6.2, n°30
- [x] `GOAL-041-T05` `radio.liq` : `on_connect` annonce AVANT de basculer le
      compteur — l'antenne reste muette pendant la purge ; test du script
- [x] `GOAL-041-T06` ARCHITECTURE §4.1 (l'avance a une durée de vie) et §6.2 ;
      carte du dépôt inchangée ; clôture

### Décisions prises

- **Deux seuils distincts, même défaut (15 min)** : la péremption d'un jingle
  se mesure à son heure pleine, la reprise à neuf à la durée de la pause. Les
  confondre aurait fait dépendre l'un de l'autre sans raison.
- **Un « encore » voté avant la pause survit** : c'est une demande explicite
  de l'auditeur, pas de l'habillage horaire.
- **Le `/skip` n'est ordonné que si un morceau passait** : à froid, le saut
  reste enregistré chez Liquidsoap et mangerait le premier tirage (relevé).
- **Flashs et émissions ne périment toujours pas** : la n°29 ne touche que
  les jingles horaires.

### Reste à écouter (AGENTS §4.1)

Se rebrancher après plus de quinze minutes de pause : ni jingle périmé, ni
avance rassise, ni reliquat du morceau interrompu — un départ propre sur un
tirage neuf. Et un rebranchement rapide inchangé : la reprise sur l'avance.

---

## GOAL-042 — Le Planning s'ouvre sur aujourd'hui, créneau en cours visible, jours repliés

**Terminé le 2026-08-31.**

Constat de l'auteur (capture) : sept cartes de ~15 lignes, la veille en
premier — la page était longue et le présent invisible. Présentation
seulement : `index.html`, l'API inchangée, rien ne se décide dans la page.

- [x] `GOAL-042-T01` Aujourd'hui en tête puis la suite de la semaine
      (renverse le « veille d'abord » volontaire de GOAL-021) ; badge et fond
      « en cours » sur le créneau du jour — minuit enjambé marqué sur son jour
      de départ seulement, direct via sa durée, podcast et YouTube jamais
      (fin inconnue) ; l'heure suit le rafraîchissement périodique
- [x] `GOAL-042-T02` Seul aujourd'hui déplié par défaut ; un jour replié
      tient en une ligne (chevron, nom, nombre de créneaux), dépliable au clic

### Décisions prises

- **L'état de dépli n'est pas persisté** : recharger la page revient à
  « aujourd'hui seul » — c'est le défaut voulu, pas une préférence à retenir.
- **Rendu constaté en chromium headless** avec un planning simulé : le
  surlignage tombe à l'heure juste ; le vrai navigateur de l'auteur reste le
  juge final (l'équivalent visuel d'AGENTS §4.1).

---

## GOAL-043 — Une grille de journée complète, et un atelier à jingles en conteneur

**Terminé le 2026-08-31.** Demande directe de l'auteur, hors `/goal`.

La grille de `webradio.toml` (non versionné) couvre désormais la journée :
quinze plages, dont trois propres au week-end, et **quatre trous volontaires**
de tirage libre (10 h 30–12 h, 13 h 30–14 h, 19 h–20 h, 03 h–05 h). Les genres
ont été relevés sur la bibliothèque réelle par `getGenres` plutôt qu'inventés :
une plage qui nomme un genre absent se replierait en silence sur le tirage
libre. Les plages de week-end sont déclarées **en tête** — deux plages qui se
recouvrent ne sont pas refusées, c'est la première qui l'emporte
(`core/bands.py`), et l'ordre du TOML est donc la réponse.

- [x] `GOAL-043-T01` La grille de journée, trous de tirage libre compris
- [x] `GOAL-043-T02` `outils/generer_jingles.py` : les quinze `intro` de plage
      — voix de synthèse sur un lit musical synthétisé, mixés en habillage
- [x] `GOAL-043-T03` L'atelier en conteneur (`outils/Dockerfile`,
      `outils/generer-jingles.sh`) et son `README`

### Décisions prises

- **Une voix de service en ligne, pas une voix locale** : `edge-tts` parle au
  service de lecture d'Edge — gratuit, sans compte ni clé, voix neuronales
  françaises. Les moteurs locaux essayés sonnent le robot ; Google Cloud TTS et
  ElevenLabs font aussi bien ou mieux mais réclament un compte facturable pour
  quinze phrases par an. **La contrepartie est assumée** : l'API n'est pas
  officielle, le jour où elle change l'outil casse — et la radio, non. C'est
  pourquoi les mp3 sont conservés plutôt que refaits à la demande.
- **Le lit musical est synthétisé note par note** (`aevalsrc`) : rien n'est
  téléchargé, aucune licence n'est en jeu. Il sonne « électronique » — c'est un
  habillage de station, pas de la musique.
- **L'atelier tourne en conteneur, et n'est pas un service** : ses deux
  dépendances (ffmpeg, edge-tts) ne doivent rien laisser sur la machine, et
  `docker-compose.yml` ne le connaît pas. Seuls les mp3 finis sortent, par un
  volume, avec l'`uid` de l'appelant.
- **`outils/` est hors de `webradio/`** : il fabrique des fichiers, le
  programme ne l'importe jamais. Il reste tenu par `./verifier.sh`, moins la
  règle « pas de `print` » — un outil hors ligne parle sur la sortie standard.
- **Les mp3 produits ne sont pas versionnés** : `jingles/*` est ignoré depuis
  l'origine, le dossier n'est versionné que vide. Le script est la recette.

### Reste à écouter (AGENTS §4.1)

Les quinze génériques à leur place dans la journée : la voix tombe-t-elle
juste, le lit ne couvre-t-il pas le premier mot, sept secondes ne sont-elles
pas trop longues à cinq heures du matin — et la grille elle-même, une journée
entière durant.


---

## GOAL-044 — Les modes d'enchaînement des plages : double dose, époque, artiste

**Terminé le 2026-08-31.** Demandé par l'auteur.

Une plage peut demander que ses tirages s'enchaînent (`mode`, SPECS.md §4.4,
n°31) : `double_dose` (deux titres par artiste tiré), `era_fan` (2 à 6 titres
d'une même décennie), `artist_fan` (3 à 6 titres du même artiste). Combinable
au thème, ou seul — un tirage libre enchaîné.

- [x] `GOAL-044-T01` Relevé : `year` est un entier, présent sur 93,3 % des
      5704 pistes réelles (docs/subsonic.md §4.1)
- [x] `GOAL-044-T02` `Track.year` optionnel, fakes à jour
- [x] `GOAL-044-T03` Mappage `year` chez Subsonic — absent, chaîne ou booléen
      valent « sans année »
- [x] `GOAL-044-T04` `core/runs.py` : ancre posée par le premier tirage,
      longueur par `pick` sur l'étendue, titres déjà servis exclus, remise à
      zéro au changement de clé, rupture qui ré-ancre
- [x] `GOAL-044-T05` Câblage : `Band.mode` → `Constraint.mode` + `run_key`
      (l'occurrence, hors égalité) → `Queue` — suites d'artiste par
      `tracks_by` et hors fenêtre, filtre d'époque, ruptures journalisées
- [x] `GOAL-044-T06` La clé `mode` au TOML, valeurs tirées du noyau, plage à
      mode seul acceptée ; « Tirage libre » au planning
- [x] `GOAL-044-T07` SPECS §4.4 + n°31, exemple TOML, grille locale (era_fan
      à midi, artist_fan à 15 h, double_dose à 20 h)
- [x] `GOAL-044-T08` Carte du dépôt (`runs.py`), archive, push

### Décisions prises

- **L'époque est la décennie** de l'année de la piste ; une piste sans année
  n'ancre pas de suite, sans consommer le hasard — la soirée se rejoue.
- **Les longueurs se tirent par `pick` sur l'étendue** : aucune capacité de
  plus au hasard injecté.
- **La clé de remise à zéro est l'occurrence de la plage**, pas sa
  contrainte : une plage multi-genres retire un genre à chaque jonction et la
  suite y survit — une suite d'artiste suit son artiste par `tracks_by`, même
  hors du genre du moment.
- **Le passe-droit de fenêtre est celui de l'encore** (SPECS.md §4.6) : les
  suites d'artiste l'empruntent, les suites d'époque laissent la fenêtre agir.
- **Le même titre ne repasse jamais dans une suite** ; une suite épuisée se
  rompt en le journalisant et le morceau tiré devient l'ancre suivante.
- **Hors périmètre** : programmes, émissions, encore et tirage libre hors
  plage ignorent les modes.

### Reste à écouter (AGENTS §4.1)

Les trois enchaînements sur la grille locale — double dose à 20 h, époque à
midi, artiste à 15 h — et la fenêtre de non-répétition qui reprend après
chaque suite. **Écoute validée par l'auteur le 2026-09-01.**

---

## GOAL-045 — Une chanson trop longue n'est jamais diffusée

**Terminé le 2026-09-01.** Demandé par l'auteur.

Au-delà de `draw.max_track_minutes` (20 min par défaut, la limite exacte
passe, `0` = sans limite), une piste est écartée partout où une piste se
choisit (SPECS.md §4.2, §7 n°32).

- [x] `GOAL-045-T01` Le filtre (`broadcastable`, core/models.py) dans la file
      — tirage libre, plages, suites, replis —, dans l'encore à chaque cran,
      et dans les listes des programmes ; bibliothèque entière trop longue =
      `EmptyQueue` qui nomme la durée
- [x] `GOAL-045-T02` `draw.max_track_minutes` (défaut 20, minimum 0), câblage
      des trois consommateurs dans `main.py`, SPECS §4.2/§6.2/n°32, les deux
      TOML

### Décisions prises

- **La limite exacte passe** : « au-delà » est strict.
- **Les émissions ne sont pas concernées** : leur durée est la leur (§4.11).
- **Le filtre est silencieux piste par piste** — seuls les replis qu'il
  provoque se journalisent, comme les autres.
- Au passage, le §6.2 nommait encore `non_repetition_artistes` : la clé réelle
  est `artist_gap` depuis toujours — corrigé (AGENTS §8).

---

## GOAL-046 — Le mode d'une plage se voit dans le Planning

**Terminé le 2026-09-01.** Constat de l'auteur : les modes de GOAL-044 ne
s'affichaient nulle part.

- [x] `GOAL-046-T01` L'API du planning porte `mode` brut sur chaque plage ;
      la page le traduit en détail — « double dose », « passionné d'époque »,
      « passionné d'artiste » — et une plage sans mode reste sobre. Rendu
      constaté en chromium headless.

---

## GOAL-047 — Une chanson trop longue se joue, mais se coupe en fondu au plafond

**Terminé le 2026-09-01.** Révision de la n°32 sur demande directe de
l'auteur : au lieu d'écarter du tirage toute piste au-dessus de
`draw.max_track_minutes`, la laisser se choisir et couper sa lecture au
plafond, fondue vers l'entrée suivante.

- [x] `GOAL-047-T01` Relevé contre la maquette v2.3.3 (docs/liquidsoap.md §7,
      nouveau) : `annotate:liq_cue_out` coupe un fichier comme une URL
      Subsonic au point dit, et le crossfade fond la coupe comme une fin de
      piste ordinaire ; le §7 que `JINGLE_FADES` référençait sans qu'il
      existe est écrit au passage
- [x] `GOAL-047-T02` Le plafond ne filtre plus : `broadcastable` supprimé
      avec les paramètres `max_duration` de queue/control/playout — une piste
      longue redevient éligible au tirage, aux suites, à l'encore et aux
      listes
- [x] `GOAL-047-T03` La charnière (`LiquidsoapPlayout`) annote l'entrée d'un
      `liq_cue_out` au plafond quand la piste musicale le dépasse, coupe
      journalisée ; SPECS §4.2/§6/§7 n°32, README, les deux TOML

### Décisions prises

- **La coupe vit dans la charnière, pas dans le noyau** : c'est une affaire
  de lecture, pas de choix — le noyau ne connaît plus le plafond.
- **Aucun fondu supplémentaire** : le relevé montre que le `crossfade` traite
  la coupe comme une fin de piste ordinaire (fondu mesuré à l'enveloppe RMS).
- **Une entrée replacée après un encore ne se double pas** : elle revient
  déjà annotée, la garde `startswith("annotate:")` suffit.
- **Émissions et jingles ne sont pas concernés** : durée propre pour les
  unes, brièveté par construction pour les autres.

### Reste à écouter (AGENTS.md §4.1)

La coupe réelle à 20 minutes et son fondu vers le morceau suivant, sur la
vraie radio. **Écoute validée par l'auteur le 2026-09-01.**

---

## GOAL-048 — Un libellé trop long du Planning se tronque en ellipse

**Terminé le 2026-09-01.** Constat de l'auteur (capture) : une longue liste de
genres repliait sur deux lignes et poussait le badge « en cours » à la ligne.

- [x] `GOAL-048-T01` `.evenement .nom` passe en flex avec un `.nom-texte`
      tronqué en ellipse (`min-width: 0` pour que l'enfant de grille rétrécisse) ;
      la liste complète reste lisible au survol (`title`) ; le badge « en
      cours » ne se comprime plus (`flex: none`, `white-space: nowrap`).
      Rendu constaté en Chrome headless : une ligne, ellipse, badge entier.

---

## GOAL-049 — Tirage par genre fiable malgré les genres fantômes de Navidrome

**Clos le 2026-09-01, sans changement de code.** Pendant le moment RAP du
2026-09-01, KISS est passé à l'antenne : le genre tiré (« Hip-Hop ») ne rendait
aucune piste, et `core/queue.py` s'est replié directement sur le tirage libre.

- [x] `GOAL-049-T01` Le diagnostic est consigné dans docs/subsonic.md et le
      point incertain §2.7.3 est résolu : Navidrome garde les fichiers disparus
      (`missing=1` — 1795 sur 7499) et les statistiques de `getGenres`
      (table `library_tag`) les comptent, alors que `getSongsByGenre`,
      `getRandomSongs`, `getAlbumList2` et `search3` les excluent. Les 142
      pistes « Hip-Hop » annoncées étaient toutes des disparues. Vérifié dans
      la base SQLite du serveur, Navidrome 0.63.2.
- ~~GOAL-049-T02 — Filtrer `tracks(genre)` localement~~ — abandonnée : le
  filtrage est le rôle de l'API (décision de l'auteur).
- ~~GOAL-049-T03 — Juger un genre tiré sur ses pistes rendues, plancher
  `genre_min_tracks` compris~~ — implémentée puis **annulée par revert** à la
  demande de l'auteur : la purge de la bibliothèque a fait disparaître les
  genres fantômes, le comportement d'avant convenait.
- ~~GOAL-049-T04 — Le repli en échelle (genre tiré → autres genres de la plage
  → réunion → tirage libre)~~ — abandonnée pour la même raison.
- ~~GOAL-049-T05 — Câbler `[draw] genre_min_tracks`~~ — abandonnée pour la
  même raison.

### Décision retenue

**La bibliothèque se soigne côté serveur, pas dans le code.** La purge des
fichiers disparus (interface Navidrome) a été faite le 2026-09-01 et constatée :
« Hip-Hop » a disparu de `getGenres` (262 → 246 genres). Si un genre maigre ou
fantôme réapparaît un jour, le relevé docs/subsonic.md §2.7.3 porte le
diagnostic complet, et l'historique Git porte l'implémentation annulée
(commit d30f77a, annulé par son revert).

---

## GOAL-050 — Un fondu à la prise d'antenne

**Terminé le 2026-09-01.** Demandé par l'auteur : un auditeur qui se connecte
ne doit pas prendre le son en pleine face.

Le flux est encodé une seule fois et partagé (`output.harbor`) : un fondu par
auditeur n'existe pas. Le cas réel est la **prise d'antenne** — quand le
premier auditeur se branche, le `switch` bascule de `blank()` au programme au
milieu du morceau, plein volume. C'est cette bascule qui se fond désormais
(SPECS.md §4.1).

- [x] `GOAL-050-T01` Relevé : les `transitions` de `switch` et `fade.in` en
      v2.3.3 sur la bascule `blank()` → programme, constaté à l'exécution
      (enveloppe RMS, conteneur épinglé), consigné dans `docs/liquidsoap.md`
      §8 — `fade.in` ne fond pas une source entamée, `amplify` armé par la
      transition fond ; un fondu par auditeur est impossible
- [x] `GOAL-050-T02` `radio.liq` : la transition arme un instant, un `amplify`
      monte le gain de 0 à 1 en deux secondes ; `amplify` constaté **accepté**
      autour du `switch` contenant `input.http`, là où `normalize`/`crossfade`
      sont refusés ; test du script à jour
- [x] `GOAL-050-T03` SPECS.md §4.1 (le fondu à la prise d'antenne, et sa
      limite : jamais par auditeur), clôture et archive — la carte du dépôt ne
      change pas

### Décisions prises

- **`amplify` piloté par l'horloge plutôt que `fade.in`** : la transition du
  `switch` s'exécute bien, mais `fade.in` n'agit qu'aux débuts de piste — une
  source entamée (retour d'antenne au milieu d'un morceau) ne fond pas. Mesuré
  au RMS, relevé docs/liquidsoap.md §8.
- **Deux secondes, rampe linéaire en amplitude** : la courbe (lin/log) reste
  un point incertain du relevé — seule l'écoute tranchera.

### Reste à écouter (AGENTS.md §4.1)

La montée du volume au branchement du premier auditeur — au démarrage à froid
et au retour au milieu d'un morceau resté en attente — et la régularité de la
rampe à l'oreille.

---

## GOAL-051 — Le direct ne ment plus à l'antenne, et la reprise coupe vraiment le reliquat

Quatre défauts constatés **à l'antenne** le 2026-09-02 au matin, puis retrouvés
un à un dans les journaux de production (`local-webradio` et
`local-webradio-liquidsoap` sur `frontal`). Ils naissent de la rencontre de
GOAL-015 (le direct) et de GOAL-041 (la reprise à neuf) : chacun tient seul,
ensemble ils mentent.

```
23:47:22  le conteneur « radio » redémarre seul ; liquidsoap reste debout,
          figé au milieu d'un morceau depuis 19:11
07:49:45  premier auditeur — « pause de 8:02:23 : la radio repart à neuf »
07:49:46  « avance jetée sur ordre de l'API »  … et AUCUN « saut demandé »   ← 1
07:49:50  /next → live:…franceinfo  « direct demandé pour 609 s »
07:49:53  /next → le bouche-trou, tiré à 7 h 49 dans un créneau sans plage    ← 3
07:49:53.371  /playing  ← reconnu : « Matinale franceinfo » s'affiche
07:49:53.374  /playing  ← MÊME entrée, déjà consommée : « None — None »       ← 2
07:51:13  le bouche-trou est annoncé et démarre (préchargement du crossfade)
07:51:15  « Switch to live » — le direct prend l'antenne, rien ne le redit     ← 2
08:00:00  « le direct se termine » → le bouche-trou GELÉ reprend, 2 min hors
          de la plage « Chanson française »                                    ← 4
08:03:05  premier morceau réellement tiré à 8 h
```

- [x] **GOAL-051-T01** — Relever dans `docs/liquidsoap.md` §9, contre
      `savonet/liquidsoap:v2.3.3` en Docker : combien de fois `input.http`
      déclenche `on_track` à son démarrage ; ce que fait `skip()` sur un
      `request.dynamic` sans piste en cours, et quel témoin le script peut lire
      pour le savoir ; si l'annonce du direct peut partir d'une **transition**
      du `switch` qui le met à l'antenne ; ce que devient la source `programme`
      pendant qu'un direct la recouvre, et l'effet d'un `set_queue([])` +
      `skip()` à la fin du direct.
      **Fait le 2026-09-02** — maquette fidèle (le vrai `radio.liq` contre une
      fausse API, le vrai flux franceinfo), `docs/liquidsoap.md` §9. Le double
      `on_track` est reproduit sur deux manches, le témoin du saut est validé à
      froid et à chaud, la transition du `switch` et la purge de fin de direct
      fonctionnent. **Le relevé a trouvé un cinquième défaut** : un
      `switch(track_sensitive=true)` derrière `crossfade` cesse d'évaluer ses
      prédicats — d'où T06.
- [x] **GOAL-051-T02** — Le témoin de « une piste passe » vit dans `radio.liq` :
      `on_skip` refuse un saut à vide, et la charnière ordonne toujours le
      `/skip` de la reprise à neuf. `radio` ne peut pas savoir ce que liquidsoap
      tient : redémarré seul, il croit qu'aucun morceau ne passe. **(défaut 1)**
- [x] **GOAL-051-T03** — Une entrée inconnue **et sans étiquettes** ne remplace
      plus ce qui est à l'antenne : déclarer « musique, sans titre ni artiste »
      efface l'affichage sans rien apporter. **(défaut 2, moitié Python)**
- [x] **GOAL-051-T04** — Le direct s'annonce quand il **prend** l'antenne, une
      seule fois par case, et non dès `live.start()` — un morceau d'avance plus
      tôt. **(défaut 2, moitié `.liq`)** — à écouter : la jonction musique → direct.
      **Dépend de T06** : sans prédicat réévalué, la transition ne s'exécute
      jamais.
- [x] **GOAL-051-T05** — À la fin du direct, l'avance rassie est jetée et le
      reliquat coupé : le premier morceau d'après est tiré à l'heure qu'il est,
      dans la plage qui est réellement ouverte. **(défauts 3 et 4)** — à
      écouter : la reprise à la coupure du direct.
- [x] **GOAL-051-T06** — Le direct prend l'antenne **à la première jonction**,
      et non au hasard. Constaté en maquette (T01) : derrière `crossfade`, un
      `switch(track_sensitive=true)` n'évalue plus ses prédicats — zéro
      évaluation sur quatre jonctions, le direct n'obtient jamais l'antenne. En
      production le 2026-09-02, une seule bascule, **85 s** après l'instruction.
      **(cinquième défaut, découvert par le relevé)**
      > **Arbitré par l'auteur le 2026-09-02** : `track_sensitive=false` plus un
      > témoin armé par le `on_track` du `request.dynamic`. Deux secondes de
      > fondu de sortie écourtées, deux fois par jour, valent mieux qu'un direct
      > qui entre à une heure non garantie. Mesuré : la bascule tombe 1 s après
      > le début de piste qui l'arme, et le retour à la musique ne porte aucun
      > silence.

**Décidé sans arbitrage** (AGENTS.md §1.2) : la purge de fin de direct est
ordonnée dans `radio.liq`, par un `ref` posé après la définition de `programme`
— `stop_live` est défini avant elle. Le script ne décide rien de plus : il
redemande à l'API. L'alternative — une route de plus, ou un réveil côté Python
à l'heure de fin — coûterait une surface publique pour un geste mécanique.

---

## GOAL-052 — L'historique dit quel jour, et ne mélange plus deux 8 h

Signalé par l'auteur le 2026-09-02, capture à l'appui : la page « 08 h » liste
`08:33 … 08:02` (aujourd'hui) **puis** `08:52 … 08:41` (la veille). L'ordre est
juste — `SELECT … ORDER BY joue_le DESC` (`adapters/state/database.py`) — mais
l'API n'expose que `%H:%M` (`app/main.py`, `lister_l_historique`) : privée de sa
date, la page groupe deux journées sous la même heure et l'ordre paraît faux.

- [x] **GOAL-052-T01** — L'entrée du journal porte sa date, pas seulement son
      heure : `PlayedEntry` gagne le jour, l'API le rend, et le contrat de
      SPECS.md §4.8 le dit.
- [x] **GOAL-052-T02** — La page sépare les journées : une heure d'aujourd'hui
      et la même heure d'hier ne se suivent plus sans le dire.

---

## GOAL-053 — Le script du diffuseur voyage dans une image, plus par un montage

Le déploiement du 2026-09-02 a mis à jour l'image de `radio` — qui **contient**
`radio.liq`, empreinte à l'appui — mais le service `liquidsoap` tourne sur
l'image amont `savonet/liquidsoap:v2.3.3` et lit le script par un montage
depuis l'hôte. Ce fichier-là est resté à `85c632d` : **six commits en
arrière**, dont les quatre correctifs du direct de GOAL-051 et le fondu de
prise d'antenne de GOAL-050, jamais déployé.

Rien ne le signalait, et rien ne pouvait le signaler : un montage n'a pas de
version. La décision d'ARCHITECTURE.md §8.5.2 — « le diffuseur n'a pas d'image
à construire » — économisait une image et coûtait un déploiement en deux
moitiés dont une silencieuse. **L'auteur la renverse le 2026-09-02.**

- [x] **GOAL-053-T01** — Le diffuseur a son image : `Dockerfile.liquidsoap`
      part de l'amont épinglée et y copie le script. Le Compose de production
      la tire, celui de développement la construit, et le montage disparaît.
      Un test refuse que l'épingle diverge entre le `FROM` et `verifier.sh` :
      deux endroits nomment la version, ils doivent dire la même chose.
- [x] **GOAL-053-T02** — La CI construit et publie l'image du diffuseur à côté
      de celle de `radio`, sur du vérifié et depuis `master` seulement.

---

## GOAL-054 — « À suivre » regarde derrière l'habillage

Signalé par l'auteur le 2026-09-02, capture à l'appui : « À suivre » est vide.
Le journal du diffuseur dit pourquoi, à la seconde — à 11:01:38, la seule
entrée demandée d'avance était `hours/11h-c.mp3`.

Le diffuseur ne garde **qu'une** entrée d'avance (`prefetch=1` est le minimum,
docs/liquidsoap.md §3), et `up_next()` saute les jingles : « dix secondes
d'habillage ne sont pas à suivre » (GOAL-035, demandé par l'auteur). Quand
cette unique entrée est de l'habillage, il n'y a plus rien à annoncer, et le
panneau reste vide **le temps de toute la chanson en cours** — une quarantaine
de fois par jour, à chaque jingle horaire et à chaque générique de plage.

La radio sait pourtant déjà ce qui vient : `core/queue.py` garde une `_avance`,
un `Pick` entièrement résolu que le tirage suivant servira. « À suivre » ne la
regarde simplement pas.

**Tranché par l'auteur le 2026-09-02** : regarder derrière l'habillage. La
règle de GOAL-035 tient — on n'annonce jamais un jingle — et le trou disparaît.

- [x] **GOAL-054-T01** — La file dit ce qu'elle a préparé : `Queue` expose son
      avance sans la consommer, et le programme ne la rend que lorsque c'est
      bien le tirage libre qui parlera — **pas** pendant un programme, dont la
      musique vient d'une liste et non de la file (SPECS.md §4.13). L'annoncer
      alors serait annoncer un morceau qui ne passera pas.
- [x] **GOAL-054-T02** — « À suivre » se replie sur cette avance quand la file
      du diffuseur n'a que de l'habillage.
      **Le câblage a révélé un trou dans SPECS.md §7 n°30** : la purge de
      reprise n'atteignait pas l'avance de la file, et `next_pick` la sert sans
      regarder la contrainte — un morceau tiré à 19 h serait passé au réveil du
      lendemain. Corrigé dans le même incrément : la purge l'oublie aussi.

---

## GOAL-055 — Le premier auditeur n'entend plus le reliquat du morceau interrompu

Signalé par l'auteur le 2026-09-02 : vers 13 h, un micro-flash de la chanson
d'avant à la connexion. Le journal du diffuseur le date à la milliseconde :
purge de reprise à 13:20:14.817, saut à .819, bascule à .863, puis
`cross: Analysis: -12.9 dB / -nan (1.99 s / 0.00 s)` — deux secondes du
morceau interrompu à 11 h 03, rien encore du suivant, et le morceau frais
annoncé 2,1 s après la bascule.

La purge de SPECS.md §7 n°30 fait ce qu'elle promet, à deux secondes près :
`crossfade` tient en permanence deux secondes déjà lues du morceau en cours,
et un saut ordonné sans auditeur ne s'exécute qu'au premier tirage — quand
le premier auditeur écoute déjà. Ces deux secondes deviennent alors le
`before` de la transition, et partent en fondu de sortie sous son nez.

Mesuré en maquette (docs/liquidsoap.md §10), puis corrigé au seul endroit qui
tient le reliquat : la transition de `cross`.

- [x] **GOAL-055-T01** — Un saut à antenne vide arme un témoin ; la
      transition qui remplace `crossfade` jette alors le reliquat et fait
      entrer le morceau frais seul, sous le fondu de prise d'antenne. Le reste
      est l'appel même de `crossfade` (`cross.simple`), fondus et étiquettes
      compris. Le témoin vaut aussi pour un direct qui finit sans auditeur.
      Un `on_track` comme signal a été essayé et mesuré trop tôt.


---


## GOAL-056 — L'avance est datée par son moment

Entendu par l'auteur le 2026-09-02 autour de 16 h : le jingle horaire n'était
pas à sa place. Le journal du diffuseur (en UTC, deux heures de moins) et
`/api/history` reconstituent la chronologie à la seconde :

| Heure | Ce qui commence | Ce que `radio` décide à cet instant pour la suite |
|---|---|---|
| 15:59:36 | *Ride Natty Ride* (Bob Marley, plage 15 h `artist_fan`) | *Could You Be Loved* — même suite d'artiste ; puis `prepare()` résout d'avance *Get Up, Stand Up*, toujours sous la plage de 15 h |
| **16:00:00** | — | rien : personne ne regarde l'horloge entre deux jonctions |
| 16:03:25 | *Could You Be Loved* | la plage a changé → générique `bands/mystere.mp3` mis en attente ; `16h-c.mp3` dû → rendu ; l'avance *Get Up, Stand Up* reste telle quelle |
| 16:07:19 | `hours/16h-c.mp3` — **7 min après l'heure** | `bands/mystere.mp3` |
| 16:07:43 | `bands/mystere.mp3` — « une heure d'un genre tiré au sort » | `next_pick()` sert l'avance **sans regarder la contrainte** : *Get Up, Stand Up* |
| 16:07:48 | *Get Up, Stand Up* — Bob Marley, **derrière le générique du mystère** | premier titre Ragga |
| 16:11:05 | *Natural* (Les R'tardataires) — la plage de 16 h commence enfin | … |

Deux défauts distincts, une même cause : **une entrée décidée d'avance ne sait
pas sous quel moment elle a été tirée, et personne ne la remet en question
quand ce moment finit.**

1. **Le jingle arrive une chanson trop tard.** Le diffuseur demande toujours un
   morceau d'avance (`prefetch=1`, docs/liquidsoap.md §3) : l'entrée qui
   commence à la jonction J est décidée à la jonction J−1. Une heure pleine
   qui tombe entre J−1 et J n'est vue qu'à J, pour l'entrée de J+1. SPECS.md
   §4.3 promet « la jonction suivante » ; la production livre **la jonction
   d'après**, systématiquement, depuis la migration Liquidsoap. Ici : 16 h 03
   promis, 16 h 07 servi. Le même retard frappe la transition de plage (§7
   n°5) et l'ouverture d'une émission-fichier — c'est ce que docs/liquidsoap.md
   §5 constatait déjà avec « une case plus courte que deux morceaux ».
   L'« encore » a déjà réglé ce problème pour lui-même (GOAL-034) : `/requeue`
   vide l'avance du diffuseur, et `stash_for_replay` la replace derrière le
   jingle. Il manque un **déclencheur à l'heure pleine**.
2. **La plage d'avant déborde derrière le générique.** `Queue.prepare()` avait
   résolu le cinquième titre de la suite Bob Marley à 15 h 59 ; `next_pick()`
   sert l'avance « sans regarder la contrainte — c'est tout son intérêt »
   (GOAL-054-T02 avait vu le même trou pour la longue pause, et l'avait bouché
   pour ce seul cas). À 16 h 07 le générique annonce un genre mystère, et
   l'auditeur entend un Bob Marley de plus. Le direct avait le même défaut, réglé
   pour lui seul le matin même (`stop_live` jette « l'avance rassie »,
   GOAL-051-T05). C'est le **troisième** cas particulier de la même règle
   absente.

**Choix retenu — une règle, pas un quatrième cas particulier** : toute entrée
décidée d'avance — l'avance de la file comme l'entrée déjà donnée au diffuseur —
est **datée par le moment qui l'a tirée** (l'occurrence de plage, le programme,
ou le tirage libre : la clé de `Constraint.run_key`, déjà là). Une entrée dont
le moment n'est plus le moment courant est **rassise** : elle ne passe pas,
elle se retire. Une heure pleine qui sonne pendant qu'une entrée musique attend
chez le diffuseur la fait remettre en question : rejouée derrière le jingle si
son moment tient encore, jetée sinon. Cela absorbe la purge de la longue pause
(§7 n°30), celle de la fin du direct, et les deux défauts de 16 h.

Ce que cela **ne** change pas : la grille n'est toujours consultée qu'au tirage
(§7 n°5), le morceau **en cours** finit toujours. Ce qui bouge est l'entrée
d'avance, que personne n'entend encore.

- [x] **GOAL-056-T01** — La file date son avance : `Queue.prepare()` retient la
      clé du moment (`run_key`, ou `None` en tirage libre) avec le `Pick`, et
      `next_pick()` la sert seulement si la contrainte demandée porte la même
      clé — sinon il l'oublie et tire à neuf. Une plage multi-genres retire un
      genre à chaque jonction sans changer de clé : son avance survit, comme
      aujourd'hui. Tests : rejouer 15 h 59 → 16 h 03 à horloge injectée et
      constater que le premier titre servi après le changement de plage est
      tiré sous la nouvelle contrainte. `forget_prepared()` de GOAL-054-T02
      devient un cas de cette règle ou disparaît.
- [x] **GOAL-056-T02** — La charnière date ce qu'elle donne au diffuseur :
      `LiquidsoapPlayout` retient, avec chaque entrée en attente, sa nature, le
      moment qui l'a tirée et l'instant de la décision. Pas encore de décision
      ici, seulement la mémoire — et `stash_for_replay` ne replace que ce dont
      le moment tient encore ; le reste est jeté en le journalisant.
- [x] **GOAL-056-T03** — L'heure pleine remet l'avance en question. Le
      battement d'auditeurs (toutes les 15 s, `declare_listeners`) est
      l'horloge dont dispose la charnière : quand une heure pleine est passée
      depuis la décision de l'entrée musique en attente, et que quelqu'un
      écoute, la charnière la replace (T02) et ordonne `/requeue` — exactement
      le chemin de l'encore (GOAL-034). Le diffuseur redemande aussitôt : le
      programme rend le générique sortant, le jingle dû, le générique entrant,
      puis l'entrée replacée ou un tirage neuf. Rien pendant un direct — le
      direct purge lui-même à sa fin. Le résidu assumé : une jonction tombée
      dans les 15 s qui précèdent l'heure garde l'ancien comportement.
      **Écouter** avant de cocher (AGENTS.md §4.1) : un jingle à 17 h, à la
      jonction qui suit l'heure, sans blanc ni doublon.
- [x] **GOAL-056-T04** — Les deux purges existantes **restent**, et la
      raison est consignée dans SPECS.md §7 n°33 : elles ne jugent pas au
      moment. La longue pause impose un tirage neuf même sous la même plage
      (n°30), donc `forget_prepared()` garde son sens ; et le script du
      diffuseur ne connaît aucun moment — sa purge de fin de direct est la
      ceinture d'un battement qui n'agit que toutes les quinze secondes. Aucun
      code retiré : il n'y avait pas de doublon, seulement une règle absente.
- [x] **GOAL-056-T05** — Documenter : SPECS.md §4.3 (le jingle tombe à la
      jonction qui suit l'heure, résidu de 15 s compris), §4.4 (la plage
      d'avant ne déborde pas derrière son générique), §7 — une décision
      n°33 « l'avance est datée par son moment » qui absorbe la purge de la
      n°30 ; ARCHITECTURE.md si la charnière change de rôle ;
      docs/liquidsoap.md §3 si le comportement de `set_queue([])` à
      auditeurs présents est observé de nouveau.

---

## GOAL-057 — Retirer au sort le thème d'une plage « au hasard »

Demandé par l'auteur le 2026-09-02. Une plage `random = "genre"` ou
`random = "artist"` tire son thème au début de l'occurrence et s'y tient
(SPECS.md §4.4, §7 n°28). Quand le genre sorti ne plaît pas — une heure de
Ragga un mercredi à 16 h —, il n'y a rien à faire d'autre que d'attendre 17 h.
L'auteur veut pouvoir **retirer** : un bouton dans l'interface, donc une route
d'API (SPECS.md §4.8 : aucun chemin privilégié).

> **Sur « année »** : il n'existe pas de thème « une année au hasard ».
> `RANDOM_THEMES` ne connaît que `genre` et `artist` ; les décennies ne vivent
> que dans le mode `era_fan`, qui pose son ancre par suite et non par
> occurrence. Retirer s'applique donc à ce qui est tiré aujourd'hui. Un thème
> `random = "era"` — une décennie tirée au sort pour l'occurrence — serait un
> Goal à part : `Track.year` est un entier relevé (docs/subsonic.md §4.1) et
> la bibliothèque est en mémoire (GOAL-039), donc filtrer par décennie est
> possible côté file ; mais c'est une nouvelle sorte de contrainte, avec ses
> replis, pas une case de plus dans `RANDOM_THEMES`.

Ce que retirer veut dire, à l'antenne : le morceau en cours finit (§7 n°5) ;
dès la jonction suivante, la plage joue le **nouveau** thème — donc l'avance
tirée sous l'ancien est rassise (GOAL-056), et le diffuseur doit la jeter par
`/requeue`. Le générique de la plage ne repasse pas : il annonce la plage, pas
le thème. Le nouveau thème est **différent** de l'ancien — retirer le même
serait un bouton qui ne fait rien —, sauf si la bibliothèque n'en offre qu'un.
Hors d'une plage au hasard, la demande est **refusée en le disant** (409 et
un motif, comme un vote pendant un jingle).

- [x] **GOAL-057-T01** — Le noyau sait retirer : `RandomTheme.redraw()`
      oublie le thème de l'occurrence courante et retire en excluant l'ancien ;
      la clé de moment d'une plage au hasard inclut le thème sorti, pour que
      l'avance datée (GOAL-056) et la suite en cours (`Runs`) repartent. Tests
      à graine fixée : le nouveau thème diffère, l'occurrence suivante retire
      normalement, une bibliothèque à un seul genre rend le même en le disant.
- [x] **GOAL-057-T02** — La route : `POST /api/moment/redraw`. Accepté →
      `{"accepted": true, "moment": "Moment · Jazz (au hasard)"}` après avoir
      préparé le tirage, pour que la réponse dise déjà ce qui vient ; refusé
      hors d'une plage au hasard → 409 et un motif. `/api/on-air` gagne un
      champ `moment_random: true|false` — l'interface ne doit pas deviner sur
      le libellé. Le `Protocol` `Radio` s'étend d'une question ; `LiveRadio`
      la traduit et ordonne le `/requeue`.
- [x] **GOAL-057-T03** — L'interface : un bouton « Retirer » à côté du moment,
      visible seulement quand `moment_random` est vrai, grisé pendant l'appel,
      qui affiche le motif d'un refus comme le font « Passer » et « Encore ».
- [x] **GOAL-057-T04** — Documenter : SPECS.md §4.4 (retirer), §4.8 (la route
      et le champ), §7 n°28 amendée ; **écouter** une fois : le retirage à la
      jonction, sans que le générique repasse.

---

**Amendement du 2026-09-02** : le bouton de l'interface s'appelle « Autre
thème », plus « Retirer » — à double sens depuis que GOAL-058 retire des
titres de la liste (l'auteur).

---

## GOAL-058 — Les prochains titres se voient, et se retirent avant de passer

Demandé par l'auteur le 2026-09-02 : « si elle existe, exposer la liste des
prochains titres pour agir dessus avant diffusion ».

**Elle n'existe pas encore comme liste.** Ce que la radio connaît d'avance
tient en deux entrées : celle déjà donnée au diffuseur (`prefetch=1`), et
l'avance de la file (`Queue._avance`, un seul `Pick`, GOAL-054). « À suivre »
en annonce la première qui soit de la musique. Pour agir sur plusieurs titres,
il faut d'abord qu'ils soient tirés.

Ce que tirer plusieurs titres d'avance engage, et qui décide du découpage :

- la **non-répétition** doit voir ce qui attend, pas seulement ce qui a joué —
  sinon la file tire deux fois le même artiste dans son avance ;
- les **suites** (`Runs`) s'observent au tirage : une avance de cinq titres
  contient donc une suite entière, c'est cohérent ;
- l'avance est **rassise** au changement de moment (GOAL-056) : plus elle est
  profonde, plus cette règle compte — c'est pourquoi GOAL-056 vient avant ;
- la **pondération** par les votes s'applique au tirage : un vote donné pendant
  qu'un titre attend ne le déplace pas, et c'est acceptable ;
- l'**encore** passe toujours devant la liste, et « À suivre » en devient la
  tête ;
- la source est appelée plusieurs fois d'affilée à la première préparation :
  le cache (`subsonic.cache_seconds`) l'absorbe, mais à vérifier au journal.

L'action demandée est **retirer** un titre : il ne passera pas, un autre est
tiré à sa place, et le retrait est journalisé. Rien de plus tant que l'auteur
ne l'a pas demandé — ni réordonner, ni forcer un titre (AGENTS.md §2 :
n'anticipe pas). Retirer la tête de liste — l'entrée déjà chez le diffuseur —
passe par le chemin de l'encore : `/requeue`, et le reste se replace.

**Redécoupé en cours de route, sur une remarque de l'auteur** : « les
problèmes d'horaire seront résolus si la planification des titres et des
jingles est anticipée dans cette liste ». Pas tout à fait — c'est l'avance
datée (GOAL-056) qui règle l'horaire, à la jonction — mais l'idée a décidé la
forme de la liste : chaque titre d'avance est **tiré sous le moment de son
heure estimée**, et l'habillage prévu y figure. Sans cela, une liste de trois
titres à 15 h 55 aurait montré trois titres de 15 h dont deux rassis.

- [x] **GOAL-058-T01** — La file tire N titres d'avance (`lookahead`, 1 par
      défaut dans le noyau), chacun daté par son moment ; `revalidate` coupe
      à la première entrée rassise ; `next_pick` ne sert la tête que si son
      moment tient et laisse le reste en place ; la fenêtre voit ce qui
      attend, l'attente s'efface en dernier ; `withdraw` retire un titre et
      le compte comme passé.
- [x] **GOAL-058-T02** — Le programme estime l'heure de chaque créneau
      (`prepare(from_instant)`) et tire chaque titre sous la plage de son
      heure, durée après durée, en revalidant à chaque préparation ; la
      charnière fournit l'estimation (début et durée du morceau en cours,
      jamais dans le passé, habillage pour zéro) et expose `upcoming()` — ce
      qui attend chez le diffuseur, puis l'avance, avec l'habillage prévu
      d'après les fichiers présents — et `withdraw()`, par `/requeue` pour
      l'entrée déjà demandée. « À suivre » devient la tête de la liste ;
      `prepared()` disparaît.
- [x] **GOAL-058-T03** — `GET /api/up-next` et `DELETE /api/up-next/<id>`
      (404 si le titre n'attend plus), la façade, l'assemblage, et
      `draw.lookahead` (défaut 3, au moins 1).
- [x] **GOAL-058-T04** — L'interface : « À suivre » ouvre un tiroir, une
      ligne par entrée avec l'heure estimée, l'habillage prévu en pointillé,
      un ✕ « Ne passera pas » sur les titres ; rechargé au rythme de
      l'antenne tant qu'il est ouvert.
- [x] **GOAL-058-T05** — SPECS.md §4.8, §6, §7 n°34 (et la n°5 précisée) ;
      ARCHITECTURE.md §4.1.

**Reste** : l'écoute d'une journée — la profondeur ne doit pas se remarquer à
l'antenne, ni artiste répété, ni titre hors plage après une transition — et
le tiroir n'a pas été vu dans un navigateur (pas de navigateur dans la
session qui l'a écrit).

---


## GOAL-059 — « Retirer » vaut aussi pour une suite tirée au sort

Précision de l'auteur le 2026-09-02, après GOAL-057 : « année aléatoire »
désignait le mode `era_fan` — la décennie d'une suite, tirée au sort par
l'ancre. Retirer doit donc valoir aussi pour une plage dont la **suite** est
au hasard : `era_fan` (une décennie) et `artist_fan` (un artiste). Retirer,
c'est **rompre la suite en cours** et en ouvrir une autre dont l'ancre diffère
de la précédente — sauf si la bibliothèque n'offre rien d'autre, et c'est
alors dit. L'avance tirée sous l'ancienne suite est jetée sans être replacée ;
le morceau en cours finit.

- [x] **GOAL-059-T01** — Le noyau : `Runs.break_run()` rompt la suite et
      retient l'ancre à éviter ; la `Directive` porte cet évitement, que la
      file applique au tirage suivant, avec repli dit ; `Queue.break_run()`.
- [x] **GOAL-059-T02** — L'assemblage : « Retirer » s'applique aux plages à
      suite au hasard — rompre, puis jeter l'avance sans la replacer
      (`drop_advance`) ; `moment_random` le dit à l'interface. SPECS.md §4.4
      et §7 n°28.

---


## GOAL-060 — Un lecteur dans la page

Demandé par l'auteur le 2026-09-02 : écouter la radio depuis l'interface,
sans ouvrir VLC. Un élément `<audio>` sur le flux de Liquidsoap suffit ; le
bouton vaut le geste que les navigateurs exigent avant tout son.

Ce que ça engage : l'adresse du flux vient du TOML (AGENTS.md §2 — rien en
dur), la page devient un auditeur (lancer la lecture réveille la radio, la
couper la rendort si personne d'autre n'écoute), et ce que fait le navigateur
d'un téléphone — rebranchement, arrière-plan, écran verrouillé — ne se
constate qu'en écoutant (docs/flux-icy.md).

- [x] **GOAL-060-T01** — `web.stream_url` : l'adresse du flux telle que la
      page doit l'ouvrir. Absente, pas de lecteur. Une valeur qui commence
      par `:` — `:8000/flux` — désigne l'hôte de la page : la même
      configuration vaut depuis tous les postes du réseau.
- [x] **GOAL-060-T02** — Le lecteur dans l'onglet « À l'antenne » : un bouton
      « Écouter » / « Couper », un `<audio preload="none">` qui ne charge rien
      tant qu'on n'écoute pas, et titre et artiste passés à l'écran de
      verrouillage par Media Session quand le navigateur le sait.
- [x] **GOAL-060-T03** — SPECS.md §4.8 et §6, l'exemple TOML ; **écouter**
      depuis un téléphone : la prise d'antenne, le rebranchement, l'arrière-plan.

---

## GOAL-061 — Retouches de l'interface

Demandées par l'auteur le 2026-09-02, après avoir vu le tiroir.

- [x] **GOAL-061-T01** — « Passer » et « Encore » sont grisés quand personne
      n'écoute : un vote sans antenne n'a rien sur quoi porter, et l'API
      l'aurait accepté sans effet visible.
- [x] **GOAL-061-T02** — Le tiroir montre plus de titres : `draw.lookahead`
      passe à 8 par défaut. La borne de la n°34 tenait à la grille qui
      changerait sous l'avance ; depuis que chaque titre est tiré pour son
      heure, elle ne tient plus qu'au coût des appels à la source, que le
      cache absorbe.
- [x] **GOAL-061-T03** — Le tiroir monte en glissant et le voile apparaît en
      fondu, à l'ouverture.

---

## GOAL-062 — L'interface repensée

Demandé par l'auteur le 2026-09-02, capture à l'appui : « c'est pas terrible ».
Le lecteur (GOAL-060) était un bouton posé sous le moment, les votes deux
pavés fixés en bas, et entre les deux un écran de vide. L'auteur propose un
lecteur « plus beau, toujours en bas », par une bibliothèque tierce peut-être.

**Décision : pas de bibliothèque de lecteur.** Un lecteur tiers (Plyr, et
consorts) est fait pour un fichier — barre de progression, durée, avance —
et rien de cela n'a de sens sur un direct. Il faudrait le vendre avec la page
(hors ligne, comme Vue), et « couper, c'est décharger » — la règle qui compte
un auditeur de moins — resterait à écrire à côté de lui. Vue est déjà là ; la
barre se dessine avec.

**Décision : le style « verre » d'Apple, pas Material.** L'auteur proposait
l'un ou l'autre. Material fidèle demande une bibliothèque de composants à
vendre hors ligne ; le verre — surfaces translucides floutées sur un fond en
dégradé — se fait en CSS seul, et convient à une radio qu'on regarde dans le
noir.

- [x] **GOAL-062-T01** — La barre de lecture, fixe en bas de page et présente
      sur tous les onglets : un bouton rond Écouter / Couper, titre, artiste et
      moment sur une ligne, un témoin « en direct » / « en veille », le volume
      quand l'écran est assez large. La règle de GOAL-060 ne change pas :
      rien n'est chargé avant le geste, couper décharge. **Écouter** depuis
      un téléphone : la barre reste sous le pouce quand on change d'onglet.
- [x] **GOAL-062-T02** — L'onglet « À l'antenne » en carte : nature, titre,
      artiste, moment et « Retirer », « À suivre » en ligne ouvrable, et
      « Passer » / « Encore » juste dessous — plus de vide entre le contenu et
      les boutons ; sans auditeur, la carte dit qu'il suffit d'écouter.
- [x] **GOAL-062-T03** — Un en-tête et des onglets segmentés communs, des
      cartes unifiées sur Votes, Planning, Historique et le tiroir ;
      SPECS.md §4.8 ; clôture.

---

## GOAL-063 — Installable en PWA, une icône, un titre qui dit ce qui passe

Demandé par l'auteur le 2026-09-02, en validant GOAL-062. Trois ajouts et
un retrait : la carte « La radio dort » — « c'est con » — disparaît ; la
barre dit déjà que personne n'écoute.

- [x] **GOAL-063-T01** — Retirer le texte « La radio dort » — la carte
      de veille reste, rectifiée par l'auteur après un premier retrait
      complet : elle dit « Rien à l'antenne » et comment démarrer la radio.
- [x] **GOAL-063-T02** — Une icône (favicon SVG) et un titre de page qui dit
      ce qui passe — titre et artiste dans l'onglet du navigateur, mis à jour
      à chaque rafraîchissement.
- [x] **GOAL-063-T03** — Installable en PWA : un manifeste, des icônes PNG
      pour l'écran d'accueil, les métadonnées qu'iOS exige, l'affichage
      autonome ; SPECS.md §4.8 ; la carte du dépôt (ARCHITECTURE.md §9) ;
      clôture. Ce qu'un téléphone en fait — l'installation, l'ouverture
      plein écran — ne se constate qu'en essayant.

---

## GOAL-064 — La feuille de style externalisée, et des animations

Demandé par l'auteur le 2026-09-02. Le gabarit portait 250 lignes de CSS en
tête ; elles partent dans `static/`, servies comme Vue. Et la page bouge :
les lignes d'une liste entrent l'une après l'autre, un onglet glisse vers
le suivant, une chanson qui change fond l'ancienne dans la nouvelle.

- [x] **GOAL-064-T01** — La CSS dans `static/style.css`, liée depuis le
      gabarit ; le gabarit n'a plus de `<style>`.
- [x] **GOAL-064-T02** — Les animations : entrée en cascade des lignes
      (prochains titres, votes, planning, historique), transition entre
      onglets, fondu au changement de chanson dans la scène et la barre —
      désactivées sous `prefers-reduced-motion`.
- [x] **GOAL-064-T03** — SPECS.md §4.8, la carte du dépôt ; clôture ; push.

**Retouche du 2026-09-02** : une barre de défilement apparaissait dans la
liste du lecteur le temps de l'animation — les lignes entraient par le bas
et dépassaient le conteneur défilant. Elles entrent par le haut.

**Incident du 2026-09-02** : l'image construite servait des 404 sur la
feuille de style — `pyproject.toml` n'empaquetait que les `.js` de
`static/`, et les tests lisent la source, pas le paquet. Corrigé en
empaquetant tout le dossier, avec un test qui confronte le dossier aux
motifs.

---

## GOAL-065 — Renvoyer le son vers une enceinte depuis le lecteur

Demandé par l'auteur le 2026-09-02 : « le support du cast, bouton dans le
player si lecture en cours ».

**Décision : l'API Remote Playback du navigateur, pas le SDK Google Cast.**
Le SDK se charge depuis `gstatic.com` — la page doit s'afficher sans
internet — et l'API standard couvre Chromecast (Chrome) comme AirPlay
(Safari), avec le repli Safari `webkitShowPlaybackTargetPicker`.

- [x] **GOAL-065-T01** — Le bouton de renvoi dans la barre, visible en
      écoute quand le navigateur voit une cible ; `docs/flux-icy.md` §8 ;
      SPECS.md §4.8. **Reste à essayer** avec une enceinte réelle.

---

## GOAL-066 — Le moment courant se nomme toujours, à côté du bouton

Demandé par l'auteur le 2026-09-02 : « dans une période moment, il faut que
l'UI web affiche le "moment" actuel à côté du bouton de changement ».

**Décision : c'est le libellé, pas la page, qui est en cause.** Le gabarit
affiche déjà le moment à côté du bouton (`<p class="moment">`), mais
`_libelle_du_moment` joignait des genres inexistants pour une plage à mode
seul (SPECS.md §7 n°31) — le « · » restait seul. Le libellé nomme désormais
le repli (« tirage libre ») et suffixe l'enchaînement, avec les mots du
Planning (GOAL-046).

- [x] **GOAL-066-T01** — Un libellé de moment jamais vide, et qui dit
      l'enchaînement de la plage ; SPECS.md §4.4.

---

## GOAL-067 — L'encore vise la chanson entendue au vote, et la liste le montre

Constaté à l'antenne le 2026-09-02 à 19 h 50 : un « encore » voté sur La Rue
Kétanou a forcé un morceau du genre de **THK** — le titre que le diffuseur
avait pris d'avance. Le journal le dit : `repli d'encore : artiste « THK »
épuisé`. Et la liste des prochains titres, raccourcie par le vote, ne
montrait pas le morceau forcé.

**Décision : l'ancre se prend au vote, et le morceau forcé se tire d'avance.**
`_piste_après_encore` lisait l'ancre à la jonction, quand c'est déjà le jingle
d'encore qui passe : la piste à l'antenne est alors `None`, et le repli sur
« le dernier morceau rendu » désignait le morceau **d'avance** — il y a
toujours un morceau d'écart (docs/liquidsoap.md §3). Le noyau retient
désormais, avec le vote, la chanson que l'auditeur entendait ; la charnière
résout le morceau forcé dès qu'elle se prépare, le sert après les jingles, le
montre dans la liste, et le retire comme un autre — en retirant un autre du
même artiste.

- [x] **GOAL-067-T01** — L'ancre au vote, le morceau forcé résolu d'avance et
      visible dans « prochains titres » ; le scénario de production en test.

---

## GOAL-068 — La grille effective : les périodes fusionnent, la plus courte l'emporte

Constaté par l'auteur le 2026-09-02, capture du Planning à l'appui : le
mercredi, `20:00 Hardisk` et `20:00–22:00 Rock` s'affichaient l'un sous
l'autre comme deux créneaux indépendants, alors que l'émission mange la plage.
Quatre autres cas de sa configuration étaient dans le même état — le flash de
11 h 57, le programme du vendredi, la soirée du samedi, le brunch du dimanche.
Le défaut valait aussi une couche plus bas : « À suivre » annonçait de la
musique pour 20 h.

**Décision de l'auteur, prise sur conséquences montrées** : entre deux
périodes de même nature, **la plus courte l'emporte** — en lieu et place de
« la première déclarée ». La priorité entre natures ne bouge pas (émission >
programme > moment), et la fusion vaut aussi pour ce que la radio prépare. Il
lui a été montré, avant qu'il choisisse, que sa plage « Enfants » du week-end
et sa « soirée du samedi » n'auraient dès lors plus une minute à elles ; les
raccourcir est une décision de configuration, et le TOML local n'est pas
versionné.

**Ce que la fusion ne réécrit pas.** La journée est balayée par frontières, et
l'occupant de chaque intervalle est demandé aux mêmes objets qu'à la jonction
— `Programming.programme_at`, `Schedule.band_at`, `ShowSchedule`. La grille
annoncée et la radio ne peuvent donc pas diverger : elles posent la même
question aux mêmes objets. Une émission sans durée déclarée — podcast, chaîne
YouTube — ne prend aucune durée annonçable : elle coupe la période, et ce qui
reprend après elle n'annonce que sa fin.

- [x] **GOAL-068-T01** — La plus courte période l'emporte (`core/bands.py`,
      `core/programmes.py`) ; SPECS.md §4.4.
- [x] **GOAL-068-T02** — `core/planning.py` : la grille effective d'une
      journée, émissions comprises.
- [x] **GOAL-068-T03** — `/api/planning` sert la grille effective, la page
      l'affiche telle quelle ; SPECS.md §4.8. Constaté radio démarrée sur la
      configuration de l'auteur.
- [x] **GOAL-068-T04** — « À suivre » s'arrête à l'émission qui va couper et
      la nomme ; l'avance n'est plus tirée pour les heures d'un programme ou
      d'un direct ; SPECS.md §4.8.

**Reste à écouter** (AGENTS.md §4.1) : la jonction de 20 h un mercredi, quand
Hardisk coupe la plage guitares ; et la reprise à la fin du programme du
vendredi, dont l'avance est désormais tirée pour 20 h et non plus pour 18 h.

---

## GOAL-069 — Le picto de volume est dessiné, comme les autres

Demandé par l'auteur le 2026-09-02 : « le picto volume est une emoji, c'est
pas top ». `🔈` était le seul caractère pictographique de la page, au milieu de
huit pictos dessinés en SVG de 16 × 16 qui prennent `currentColor`. Un emoji ne
suit ni la couleur ni la taille du reste, et change de dessin d'un système à
l'autre.

Un test refuse désormais tout pictogramme des plans supérieurs d'Unicode dans
la page servie : c'est la frontière qui sépare les emoji en couleur des flèches
et des croix typographiques que la page utilise (`✕`, `▾`, `‹`).

- [x] **GOAL-069-T01** — Un haut-parleur en SVG, et le test qui interdit le
      retour d'un emoji. Constaté sur la page rendue, radio démarrée.

---

## GOAL-070 — La liste des prochains titres ne se coupe plus en silence

Constaté par l'auteur le 2026-09-02, le jour même de GOAL-068 : « dans la
liste de lecture je ne vois que 4 prochaines chansons », alors que
`draw.lookahead = 8`.

**Ce que le diagnostic a montré**, en rejouant la journée entière sur la grille
de l'auteur : l'avance tient bien ses huit titres à toute heure. C'est la
**lecture** qui coupait. GOAL-068-T04, la veille, avait appris à la préparation
à reporter un créneau à la fin d'un direct ou d'un programme — la file n'y est
pas servie ; `upcoming`, lui, estimait sans ce report. Les deux heures
divergeaient, le moment ne correspondait plus à celui sous lequel le titre
avait été tiré, et la liste s'arrêtait comme devant une avance rassise, sans
rien dire.

**Décision : on ne continue qu'après ce qu'on sait nommer ET dater.** Un direct
déclare sa durée : la liste l'annonce et reprend à l'heure sûre. Un podcast ou
une chaîne YouTube ne connaissent leur durée qu'une fois le flux ouvert, et un
programme ne s'annonce pas (SPECS.md §4.8) : là, la liste s'arrête — mais
jamais en silence.

**La leçon** : un report appliqué d'un seul côté d'une paire
préparation/lecture se paie en truncation muette. Les deux marchent désormais
avec la même fonction, `_servi_a_partir_de`.

- [x] **GOAL-070-T01** — La liste estime avec le report de la préparation,
      nomme le direct qui coupe, reprend après lui ; SPECS.md §4.8. Le test
      a été vu échouer report retiré.
