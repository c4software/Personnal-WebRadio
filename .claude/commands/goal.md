---
description: Transformer un objectif de haut niveau en tâches, puis les exécuter
argument-hint: <objectif de haut niveau>
---

# /goal — point d'entrée du Harness

Objectif reçu : **$ARGUMENTS**

Si aucun objectif n'a été fourni, ne rien inventer : afficher les Goals `TODO`
de `TASKS.md` et demander lequel entreprendre.

```
Goal → Analyse → Décomposition → Plan → TASKS.md
     → Exécution → Validation → Documentation
```

---

## Étape 1 — Comprendre le contexte

Lire, dans cet ordre, **avant de toucher au code** :

1. `AGENTS.md` — les règles de travail
2. `SPECS.md` — ce que le produit doit faire
3. `ARCHITECTURE.md` — comment il est conçu, et **la carte du dépôt : ce qui
   existe vraiment**
4. `TASKS.md` — où le travail s'est arrêté

Si l'objectif touche à **Navidrome**, au **flash France Info**, à
**Liquidsoap**, à **YouTube/yt-dlp**, à **ffmpeg**, aux **lecteurs de webradio**
ou aux **flux de podcast**, lire **aussi** le relevé correspondant dans `docs/`,
et sa section « points incertains » en particulier (AGENTS.md §3).

Lire ensuite **uniquement** les fichiers de code nécessaires à l'objectif. Ne
pas parcourir le dépôt entier.

Ne modifier aucun fichier à cette étape.

---

## Étape 2 — Vérifier les dépendances

Établir, en s'appuyant sur ce qui vient d'être lu :

- ce qui **existe déjà** — la carte du dépôt le dit, le code le confirme ;
- ce qui **manque** ;
- quelles tâches de `TASKS.md` sont concernées ;
- quelles contraintes d'architecture s'appliquent ;
- quels tests existent déjà ;
- quelles décisions ouvertes de `SPECS.md §7` ce Goal doit trancher.

**Ne pas recréer une fonctionnalité existante.**

### Goal déjà présent ?

Comparer l'objectif aux Goals de `TASKS.md`.

- **Identique ou très proche d'un Goal existant** → ne pas créer de doublon.
  L'annoncer, et proposer de **reprendre** le Goal existant à sa première tâche
  non terminée.
- **Recouvrement partiel** → le dire, et proposer soit d'étendre le Goal
  existant, soit d'en créer un nouveau qui en dépend.
- **Nouveau** → lui attribuer le prochain identifiant `GOAL-0XX` libre.

Les identifiants sont **stables** : ne jamais renuméroter.

---

## Étape 3 — Décomposer

Transformer l'objectif en tâches **assez petites pour être exécutées et validées
indépendamment**. Chaque tâche doit correspondre à un changement réel et
vérifiable.

Une bonne tâche nomme ce qu'elle produit :

```
[ ] Traduire les codes HTTP en erreurs métier (401, 503, corps non-JSON)
[ ] Tester la pagination par curseur, curseur invalide compris
```

Une mauvaise tâche est un domaine, pas un changement :

```
[ ] Faire l'API
[ ] Faire l'interface
[ ] Finir l'authentification
```

Règles de découpage :

- **l'étude précède l'implémentation** : une tâche qui touche à Navidrome, au
  flash France Info ou à ffmpeg commence par un relevé qui met à jour `docs/`
  (AGENTS.md §3) ;
- **le noyau précède ses consommateurs** : `core/` avant `adapters/`, et une
  décision se teste sans réseau avant d'être câblée ;
- **les tests ne sont pas des tâches séparées** du code qu'ils couvrent — sauf
  campagne de cas limites, qui en est une à part entière ;
- **toute tâche qui touche au son, aux transitions, à la durée ou aux lecteurs**
  (AGENTS.md §4.1) porte dans son intitulé ce qu'il faudra **écouter** : aucun
  test ne le fera ;
- la dernière tâche d'un Goal **met à jour la carte du dépôt**
  (ARCHITECTURE.md §9).

Numéroter `GOAL-0XX-T01`, `T02`, …

---

## Étape 4 — Présenter le plan

Avant toute modification de code, afficher :

```
Goal:
GOAL-0XX — <titre>

Plan:
1. ...
2. ...

Fichiers principaux concernés:
- ...

Décisions à trancher:
- ... (SPECS.md §7 n°X)

Validation:
- ./verifier.sh
```

Puis **inscrire le Goal et ses tâches dans `TASKS.md`** — table de vue
d'ensemble comprise — et commencer l'exécution.

### Autonomie

Le Harness privilégie l'autonomie. Ne poser une question que si la réponse ne
peut raisonnablement pas être déduite de `SPECS.md`, `ARCHITECTURE.md`,
`AGENTS.md`, de l'état du code ou des conventions du projet.

Les cas d'arrêt sont ceux d'`AGENTS.md §1.2`, et seulement ceux-là.

---

## Étape 5 — Exécuter

Pour chaque tâche, dans l'ordre :

1. prendre la première tâche non terminée ;
2. la passer à `[-]` dans `TASKS.md` ;
3. l'implémenter — **elle seule** ;
4. écrire ses tests dans le même incrément ;
5. lancer `/verify` et **constater la sortie réelle** ;
6. corriger jusqu'à ce qu'elle passe ;
7. mettre à jour la documentation impactée (AGENTS.md §6) ;
8. passer la tâche à `[x]`, committer (AGENTS.md §7) ;
9. tâche suivante.

Ne jamais modifier massivement le dépôt sans validation intermédiaire.

**Rappel** : `code écrit ≠ tâche terminée`. Une tâche dont la vérification
échoue reste `[-]`, ou passe à `[!]` avec sa raison écrite.

---

## Étape 6 — Clore

Quand toutes les tâches sont `[x]` :

- passer le Goal à `[x]` dans la table de vue d'ensemble ;
- mettre à jour la « Phase courante » et la « Prochaine tâche » de `TASKS.md` ;
- inscrire les dettes ouvertes par le Goal comme **tâches**, pas comme remarques ;
- produire un rapport : ce qui a été fait, les décisions prises et leur raison,
  ce qui reste ouvert.

**Ne pas enchaîner sur le Goal suivant sans y être invité.**
