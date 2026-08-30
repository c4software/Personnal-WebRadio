# CLAUDE.md

Les règles de développement de ce dépôt vivent dans un seul fichier, partagé par
tous les agents et par les contributeurs humains :

👉 **[AGENTS.md](./AGENTS.md)** — méthode de travail, interdits, tests, commande
de vérification, conventions de code et de commit.

À lire ensuite, dans cet ordre :

1. [SPECS.md](./SPECS.md) — la spécification fonctionnelle (le **quoi**)
2. [ARCHITECTURE.md](./ARCHITECTURE.md) — l'architecture technique (le **comment**)
3. [TASKS.md](./TASKS.md) — la feuille de route et l'avancement réel (l'**ordre**)

Si le travail touche à **Navidrome**, au **flash France Info**, à **Liquidsoap**, à **YouTube/yt-dlp**, à **ffmpeg**, à
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

**Les tests n'entendent rien.** Cinq choses ne se constatent qu'en écoutant : le
son lui-même, les transitions, la tenue dans la durée, le comportement des vrais
lecteurs, et le jingle qui annonce un vote. Elles sont listées en
AGENTS.md §4.1 — et personne ne les détecte automatiquement.

**L'interface web n'a aucun raccourci.** Ses boutons passent par l'API, comme
n'importe quel autre client. Une route Flask ou un gabarit Jinja2 qui appellerait
le noyau directement créerait un second chemin — celui qu'on ne teste pas
(AGENTS.md §2).
