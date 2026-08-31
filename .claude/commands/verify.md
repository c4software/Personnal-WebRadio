---
description: Compiler, tester, analyser et confronter TASKS.md à l'état réel
---

# /verify — vérification du projet

Cette commande **constate**. Elle ne corrige rien de sa propre initiative et ne
coche aucune case.

| Niveau | Sens |
|---|---|
| **PASS** | Constaté conforme |
| **WARN** | Fonctionne, mais mérite attention |
| **FAIL** | Bloquant. Aucune tâche ne peut être déclarée terminée |

---

## 1 — Construction, tests, analyse statique

```bash
./verifier.sh
```

C'est **la** commande d'`AGENTS.md §5.2` : si elle change, elle change là-bas, et
ce fichier la recopie.

Reporter **la sortie réelle**. En cas d'échec, citer le message d'erreur, pas un
résumé — et ne jamais annoncer un succès non observé.

## 2 — Ce que la vérification n'entend pas

Rappel, à faire figurer dans le rapport comme **WARN** dès qu'une tâche audible a
été touchée depuis la dernière écoute :

> Le son, les transitions, la tenue dans la durée et le comportement des vrais
> lecteurs (AGENTS.md §4.1) ne sont couverts par **aucun** contrôle automatique.
> Une suite verte ne dit rien d'une radio qui grésille.

## 3 — Fichiers structurants

Présents et non vides : `SPECS.md`, `AGENTS.md`, `ARCHITECTURE.md`, `TASKS.md`,
`CONTRIBUTING.md`, `README.md`, `CLAUDE.md`,
`.claude/commands/{goal,task,status,verify}.md`, et les relevés de `docs/`
listés en `AGENTS.md §3`.

## 4 — État Git

- `git status` — travail non committé
- Aucun secret ni chemin machine indexé : `.claude/settings.local.json`,
  clés, jetons, fichiers d'environnement
- Les derniers messages de commit suivent `AGENTS.md §7` et référencent une tâche

## 5 — Erreurs évidentes

Contrôles par recherche textuelle. Chacun correspond à un interdit
d'`AGENTS.md §2` : un interdit sans contrôle ici est un vœu.

- `TODO` ou `FIXME` sans tâche correspondante dans `TASKS.md` → **FAIL**
- Un `import` de `httpx`, `requests`, `aiohttp`, `subprocess`, `socket` ou
  `asyncio` dans `webradio/core/` → **FAIL**
- `datetime.now()`, `datetime.today()`, `time.time()` ou `time.monotonic()` hors
  de `core/clock.py` → **FAIL**
- `random.` ou `secrets.` hors de `core/rng.py` → **FAIL**
- `except:` nu ou `except Exception: pass` → **FAIL**
- `print(` hors des tests → **FAIL**
- Une URL, un chemin absolu, un port ou une durée en dur dans le code → **WARN**
- Un secret, un mot de passe ou un jeton dans un appel de journalisation → **FAIL**

## 6 — Cohérence de TASKS.md

C'est le contrôle qui distingue cette commande d'un simple build.

Pour **chaque tâche `[x]`**, vérifier que ce qu'elle prétend avoir produit
existe réellement **et est testé**. Une tâche cochée dont le code est absent, ou
présent sans tests, est **FAIL** — et la case doit être décochée, pas ignorée.

Vérifier aussi :

- la carte du dépôt d'`ARCHITECTURE.md` décrit bien le dépôt actuel → sinon **WARN**
- aucune fonctionnalité implémentée n'est restée `[ ]` → sinon **WARN**
- chaque tâche `[!]` porte sa raison écrite → sinon **WARN**

---

## Rapport

```
/verify — local-webradio

[PASS] Construction, tests, analyse statique
[PASS] Fichiers structurants
[PASS] État Git
[FAIL] Erreurs évidentes — TODO sans tâche : src/player.ts:42
[PASS] Cohérence de TASKS.md

Résultat : FAIL

À corriger:
- src/player.ts:42 — ouvrir une tâche dans TASKS.md, ou retirer le TODO
```

Le résultat global est **FAIL** dès qu'un seul contrôle échoue.

Terminer par ce qu'il faut corriger, **sans le corriger** : la décision revient à
`/task` ou `/goal`.
