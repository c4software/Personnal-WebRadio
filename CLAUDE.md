# CLAUDE.md

## Delegation policy (read first)

The session model (Fable) is the orchestrator, not the worker. Fable is the most expensive tier; spend its tokens only on decomposition, judgment calls, synthesis, and talking to the user. Delegate everything else to subagents via the Agent tool, picking the cheapest model that can do the job well:

- `model: "opus"` — the default worker tier. Anything requiring real judgment: implementation, debugging, architecture-aware exploration, adversarial review.
- `model: "sonnet"` — cheap tier for mechanical or low-stakes work: running tests and reporting output, simple greps/lookups with a known target, rote refactors from an exact spec, formatting, screenshot capture, admin chores. If getting it slightly wrong is cheap to catch, use sonnet.

- **Exploration/research**: never read broadly yourself. Spawn `Explore` agents (model: opus) with tightly scoped questions; consume their synthesized reports, not raw files. Trivial "find the file that defines X" lookups can go to sonnet.
- **Implementation**: for any multi-file change, spawn `general-purpose` agents (model: opus) with exact file paths, the relevant doctrine from this file, and a definition of done (tests to run). Independent changes get parallel agents in one message.
- **Verification/review**: adversarial review and blast-radius checks go to opus agents. Plain test runs and lint passes go to sonnet agents.
- Fable itself only edits directly when the change is small (one or two files, already-known locations).
- **Tripwire (added after Fable did a 5-file change inline, 2026-08-26): before the first Edit/Write, count the files the change will touch. Three or more, or any screenshot/browser-proof chore: stop and spawn agents instead. Inline Fable work is only sequential diagnosis (each command depends on the previous answer) and 1-2 file edits.**

Token rules:
- Batch independent agent launches in a single message so they run concurrently.
- Give agents file paths and constraints up front so they don't rediscover this file's contents; paste the relevant doctrine into the prompt.
- Never re-read files an agent already summarized; trust the report, spot-check only what you'll edit.
- Don't echo file contents or long diffs back to the user; report conclusions.

## Introduction 

Les règles de développement de ce dépôt vivent dans un seul fichier, partagé par
tous les agents et par les contributeurs humains :

👉 **[AGENTS.md](./AGENTS.md)** — méthode de travail, interdits, tests, commande
de vérification, conventions de code et de commit.

À lire ensuite, dans cet ordre :

1. [SPECS.md](./SPECS.md) — la spécification fonctionnelle (le **quoi**)
2. [ARCHITECTURE.md](./ARCHITECTURE.md) — l'architecture technique (le **comment**)
3. [TASKS.md](./TASKS.md) — la feuille de route et l'avancement réel (l'**ordre**)

Si le travail touche à **Subsonic**, au **flash France Info**, à **Liquidsoap**, à **YouTube/yt-dlp**, à **ffmpeg**, à
**ce qu'attendent les lecteurs de webradio** ou aux **flux de podcast**, lire **aussi** le relevé
correspondant dans [docs/](./docs/), et sa section « points incertains » en
particulier : **ne jamais inventer le comportement d'une dépendance externe**
(AGENTS.md §3).

## Commandes du Harness

| Commande | Rôle |
|---|---|
| `/status` | Où en est le projet, et ce qui cloche |
| `/goal <objectif>` | Décomposer un objectif en tâches, puis les exécuter |
| `/task [GOAL-00X-TYY]` | Exécuter une tâche précise, ou la suivante |
| `/verify` | Compiler, tester, et confronter TASKS.md à la réalité |

En arrivant sur le dépôt, commencer par `/status`.

## Points de vigilance

**Une tâche de `TASKS.md` à la fois**, tests compris, vérification passée **et sa
sortie constatée**, puis commit — avant d'aller plus loin.

`code écrit ≠ tâche terminée` :

```
code écrit → tests → vérification → documentation → TASKS.md = [x]
```

Ne jamais annoncer un succès non observé. Ne jamais supposer qu'une tâche `[-]`
est terminée : aller le vérifier.

### Ce projet, en particulier

**L'horloge et le tirage aléatoire sont le cœur du produit.** Une grille horaire
et une sélection au hasard qui lisent directement `datetime.now()` ou
`random.choice()` ne sont pas testables : on ne peut ni rejouer une soirée, ni
vérifier qu'un jingle tombe à l'heure. Ils sont **injectés**, et un seul module
les fournit (AGENTS.md §2).

**Les tests n'entendent rien.** Le son lui-même, les transitions, la tenue dans
la durée, le comportement des vrais lecteurs, le jingle qui annonce un vote,
l'effet de la pondération : rien de cela ne se constate autrement qu'en
écoutant. La liste vit en AGENTS.md §4.1 — et personne ne le détecte
automatiquement.

**L'interface web n'a aucun raccourci.** Ses boutons passent par l'API, comme
n'importe quel autre client. Une route Flask ou un gabarit Jinja2 qui appellerait
le noyau directement créerait un second chemin — celui qu'on ne teste pas
(AGENTS.md §2).
