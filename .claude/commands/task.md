---
description: Travailler une tâche précise de TASKS.md, ou la prochaine pertinente
argument-hint: "[GOAL-00X-TYY]"
---

# /task — exécuter une tâche

Tâche demandée : **$ARGUMENTS**

```
Lire la tâche → Lire le contexte → Implémenter → Tester
             → Vérifier → Mettre à jour TASKS.md
```

---

## Étape 1 — Choisir la tâche

**Si un identifiant est fourni** (`GOAL-002-T03`) : c'est celle-là.

- Introuvable dans `TASKS.md` → le dire, montrer les tâches voisines du même
  Goal, et s'arrêter. **Ne pas inventer de tâche.**
- Déjà `[x]` → le signaler et **vérifier que c'est vrai** (le code existe, les
  tests passent). Si c'est faux, c'est une incohérence : AGENTS.md §8.
- `[!]` → relire la raison du blocage avant toute chose. Est-elle toujours
  valable ?

**Si aucun identifiant n'est fourni**, sélectionner :

1. une tâche `[-]` s'il en existe une — le travail en cours passe avant tout ;
2. sinon, la première tâche `[ ]` du Goal en cours ;
3. sinon, la première tâche du prochain Goal — mais si ce Goal n'est pas
   découpé, **ne pas improviser** : renvoyer vers `/goal`.

Annoncer la tâche retenue et pourquoi, avant de commencer.

---

## Étape 2 — Lire le contexte

- `AGENTS.md` — les règles s'appliquent à cette tâche aussi
- l'entrée du Goal dans `TASKS.md`, et les tâches qui la précèdent
- la section de `SPECS.md` que la tâche couvre
- la section de `ARCHITECTURE.md` concernée, **et sa carte du dépôt**
- le relevé de `docs/` si la tâche touche à Navidrome, au flash France Info
  ou à ffmpeg — sa section « points incertains » en particulier
- les fichiers de code que la tâche modifie, et leurs tests

Puis **constater l'état réel du code**. Ne jamais supposer qu'une tâche `[-]`
est à moitié faite, ni qu'elle ne l'est pas : regarder.

---

## Étape 3 — Implémenter

1. Passer la tâche à `[-]` dans `TASKS.md`.
2. Énoncer le choix technique retenu, et pourquoi.
3. Implémenter **cette tâche uniquement**. Ce qui déborde devient une nouvelle
   tâche dans `TASKS.md`, pas un ajout silencieux.
4. Écrire les tests **dans le même incrément** que le code.

Rappels qui coûtent cher à oublier (AGENTS.md §2) :

- rien de réseau, de `subprocess` ni de fichier dans `webradio/core/` ;
- `datetime.now()` et `time.time()` **seulement** dans `core/clock.py` ;
  `random.` et `secrets.` **seulement** dans `core/rng.py` ;
- aucune URL, aucun chemin, aucun port, aucune durée en dur : tout vient du TOML ;
- pas d'`except:` nu, pas d'`except Exception: pass`, pas de `print()` ;
- pas de `TODO` sans tâche correspondante ;
- aucun identifiant Navidrome dans un appel de journalisation.

---

## Étape 4 — Vérifier

```bash
./verifier.sh
```

**Si la tâche touche au son, aux transitions, à la tenue dans la durée ou aux
vrais lecteurs** (AGENTS.md §4.1) : **écouter réellement la radio**, et écrire
dans le commit ce qui a été entendu. Aucun test ne couvre ces quatre angles
morts, et aucun cas d'arrêt ne l'impose — c'est donc à cette étape, ou nulle
part.

**Constater la sortie réelle.** Ne jamais annoncer un succès non observé.

---

## Étape 5 — Clore

- Mettre à jour la documentation impactée (AGENTS.md §6), la carte du dépôt
  comprise si la structure a changé.
- Passer la tâche à `[x]`.
- Committer, en référençant l'identifiant (AGENTS.md §7).
- Annoncer la tâche suivante, **sans l'entreprendre**.

Si la tâche n'aboutit pas : la laisser `[-]`, ou la passer à `[!]` **avec la
raison écrite juste en dessous** dans `TASKS.md`. Un blocage non écrit est un
blocage perdu.
