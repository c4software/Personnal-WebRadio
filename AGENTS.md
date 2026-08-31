# AGENTS.md — Règles de développement

Le contrat de travail de tout agent (Claude Code, Codex, …) ou développeur
humain agissant sur ce dépôt. Il prime sur toute habitude personnelle.

Documents liés : [SPECS.md](./SPECS.md) (le quoi) ·
[ARCHITECTURE.md](./ARCHITECTURE.md) (le comment) · [TASKS.md](./TASKS.md)
(l'ordre) · [PROMPT.md](./PROMPT.md) (l'intention initiale, gelée) ·
[docs/](./docs/) (les dépendances externes).

---

## 1. Méthode de travail

Le travail s'organise en **Goals**, eux-mêmes découpés en **tâches**. Tout est
consigné dans [TASKS.md](./TASKS.md), qui est la mémoire persistante du projet.

**Un commit par tâche, dans l'ordre. Les tâches s'enchaînent sans demander
d'approbation.**

Pour chaque tâche :

1. Énoncer brièvement le choix technique retenu, et pourquoi.
2. Passer la tâche à `[-]` dans TASKS.md.
3. Implémenter **cette tâche uniquement**.
4. Écrire les tests dans le même incrément que le code.
5. Lancer la vérification complète (§5) et **rapporter la sortie réelle**.
6. Mettre à jour la documentation impactée (§6).
7. Passer la tâche à `[x]`, committer, puis passer à la suivante.

Si une tâche se révèle plus grosse que prévu, l'étaler sur plusieurs commits —
mais ne jamais fusionner deux tâches en une.

La granularité est **le commit, pas la conversation** : c'est le commit qui rend
le travail relisible et réversible pas à pas. C'est ce qui rend l'avancement
autonome sans danger.

### 1.1 La règle fondamentale

Ne jamais considérer que :

```
code écrit = tâche terminée
```

La règle est :

```
code écrit → tests → vérification → documentation → TASKS.md = [x]
```

Une tâche dont la vérification échoue n'est **pas** terminée. Une tâche déclarée
terminée sans que la sortie de la vérification ait été vue est un mensonge, et
c'est l'agent suivant qui le paiera.

### 1.2 Quand s'arrêter quand même

L'enchaînement automatique ne dispense pas de savoir s'interrompre. **Quatre
cas, et seulement ceux-là** :

- **La vérification (§5) échoue et la réparer demande un arbitrage** — baisser
  une version, relâcher une règle de qualité, renoncer à un test.
- **La spécification est ambiguë sur une règle métier.** Ne jamais trancher en
  silence un comportement audible par l'auditeur.
- **Une action sortante ou difficilement réversible** : `git push`, publication,
  réécriture d'historique, suppression de données. Écrire dans la bibliothèque
  Navidrome en fait partie — et c'est de toute façon hors périmètre
  (SPECS.md §2).
- **Un choix structurel s'impose** qui contredirait
  [ARCHITECTURE.md](./ARCHITECTURE.md) ou [SPECS.md](./SPECS.md).

Hors de ces cas : décider, documenter la décision dans le message de commit, et
continuer.

> **Une conséquence assumée.** Il n'existe volontairement **pas** de cinquième
> cas « demander une écoute avant de cocher ». Les tâches qui touchent au son
> seront donc cochées sur la foi de tests qui n'entendent rien (§4.1). C'est le
> prix d'une autonomie maximale, choisi à l'initialisation, et consigné comme
> décision ouverte dans SPECS.md §7 — pas comme un oubli.

### 1.3 Reprendre après une interruption

Un agent peut être arrêté à tout moment. Au redémarrage :

1. lire ce fichier ;
2. lire [TASKS.md](./TASKS.md) ;
3. repérer les tâches `[-]` (EN COURS) ;
4. **constater l'état réel du code**, ne jamais supposer qu'une tâche `[-]` est
   terminée ;
5. lancer la vérification (§5) pour voir où en est le dépôt ;
6. reprendre la tâche.

La commande `/status` produit cette lecture automatiquement.

---

## 2. Interdits

Chacun est **constatable**, la plupart par une simple recherche textuelle —
`/verify` §5 les contrôle. Un interdit sans contrôle n'est pas un interdit, c'est
un vœu.

### Le noyau ne parle à personne

- ❌ Aucun `import` de `httpx`, `requests`, `aiohttp`, `subprocess`, `socket`,
  `asyncio` ni `pathlib.Path.open` dans `webradio/core/`. Le noyau reçoit des
  données et rend des décisions ; il n'en va chercher aucune.

### Le hasard et le temps sont injectés

Ce sont **les deux dépendances les plus importantes du projet**, parce que ce
sont elles que le produit met en scène : une radio est une grille horaire et un
tirage. Les lire directement rend la moitié du produit intestable — on ne peut
alors ni rejouer une soirée, ni vérifier qu'un jingle tombe à l'heure.

- ❌ Aucun `datetime.now()`, `datetime.today()`, `time.time()` ni
  `time.monotonic()` hors de `webradio/core/clock.py`.
- ❌ Aucun `random.` ni `secrets.` hors de `webradio/core/rng.py`.

### L'interface web n'a aucun chemin privilégié

- ❌ Aucun `import` de `flask` ni de `jinja2` hors de `webradio/adapters/web/`.
- ❌ Aucune route Flask, aucun gabarit Jinja2 n'appelle le noyau directement :
  **tout passe par l'API** (SPECS.md §4.8). Un second chemin divergerait du
  premier, et c'est toujours celui qu'on ne teste pas qui casse.
- ❌ Aucune décision dans un gabarit. Un gabarit affiche un état ; il ne calcule
  pas s'il faut refuser un vote, ni ce qui passe à l'antenne.
- ❌ Aucun `render_template` dans les réponses de l'API : l'API rend des données,
  la vue les met en page.

### La configuration est le seul point d'entrée des valeurs

- ❌ Aucune URL, aucun chemin de fichier, aucun port, aucune durée en dur dans
  le code. Tout vient du TOML (SPECS.md §6), avec un défaut déclaré au même
  endroit.
- ⚠️ **Une exception, et une seule** : les noms des jingles sont **fixes** —
  `00h.mp3` à `23h.mp3` pour les heures (SPECS.md §4.3), `encore.mp3` pour le
  vote (SPECS.md §4.6). Seul le dossier est configurable. Ne pas ajouter de table
  de correspondance : le nom du fichier *est* la configuration.

### Les erreurs se voient

- ❌ Aucun `except:` nu, aucun `except Exception: pass`. Une exception avalée
  dans une radio produit un silence, et un silence ne remonte nulle part.
- ❌ Aucun `print()` : la journalisation passe par `logging`.
- ❌ Aucun secret, jeton ni mot de passe dans un appel de journalisation.
- ❌ Aucun secret ailleurs que dans `.env` — ni dans le TOML, ni dans un test,
  ni dans un fichier d'exemple (SPECS.md §6.1).

### Les règles générales

- ❌ Livrer du code qui ne compile pas, ou une fonctionnalité sans ses tests.
- ❌ Déclarer une tâche terminée sans avoir vu la sortie de la vérification.
- ❌ Laisser du code mort, une fonction inutilisée, un paramètre ignoré.
- ❌ Écrire un `TODO` sans tâche correspondante dans [TASKS.md](./TASKS.md).
- ❌ Écrire un commentaire qui n'apporte rien : une paraphrase du code, la
  narration de la ligne suivante, une justification adressée à un relecteur. Un
  commentaire énonce une contrainte ou un **pourquoi** que le code ne peut pas
  montrer (§9).
- ❌ Introduire une dépendance sans justification écrite dans le message de
  commit.
- ❌ Anticiper : ne pas créer de structure « pour plus tard ». Une abstraction
  arrive avec son **deuxième** cas d'usage, pas avant.
  → **Une dérogation est en vigueur, et une seule** : l'abstraction des sources
  de musique, décidée le 2026-08-30 (SPECS.md §7 n°2) et consignée dans
  ARCHITECTURE.md §9.1. Elle couvre le mécanisme déjà écrit, **pas ce qu'on
  pourrait en déduire** : les questions que soulève une deuxième source
  (SPECS.md §7 n°12) ne se répondent pas en implémentant. Une dérogation ne
  s'étend pas d'elle-même.

Face à plusieurs solutions, l'ordre de préférence est :
**simplicité → lisibilité → testabilité → maintenabilité → bibliothèque
standard**.

---

## 3. Les dépendances externes

Une règle, et elle n'a pas d'exception :

> **Ne jamais inventer le comportement d'une dépendance externe.**

Les relevés vivent dans [docs/](./docs/) :

| Relevé | Ce qu'il couvre |
|---|---|
| [docs/navidrome.md](./docs/navidrome.md) | L'API Subsonic telle que Navidrome l'implémente réellement |
| [docs/franceinfo.md](./docs/franceinfo.md) | Le flash d'information : accès, format, disponibilité |
| [docs/liquidsoap.md](./docs/liquidsoap.md) | Ce que Liquidsoap 2.3.3 fait réellement, et ce qui a décidé la migration |
| [docs/ffmpeg.md](./docs/ffmpeg.md) | Relevé historique — vaut pour ce que Liquidsoap fait avec ffmpeg en dessous |
| [docs/flux-icy.md](./docs/flux-icy.md) | Ce qu'attendent réellement les lecteurs de webradio |
| [docs/podcast.md](./docs/podcast.md) | Les flux de podcast des émissions, et ce qu'ils exposent vraiment |
| [docs/youtube.md](./docs/youtube.md) | Une chaîne YouTube comme émission : ce que yt-dlp et le flux Atom exposent vraiment |

> Le relevé des lecteurs ([docs/flux-icy.md](./docs/flux-icy.md)) est le plus
> mal outillé de tous : **il n'existe aucune norme du
> « flux de webradio »**. Ce que les lecteurs acceptent est une convention de
> fait, et chacun l'interprète à sa façon. Rien ne s'y déduit d'une
> spécification ; tout se constate en branchant de vrais lecteurs.

Avant toute décision les touchant :

1. lire le relevé ;
2. si le point n'y est pas, ou y figure comme incertain, **aller observer** — la
   documentation officielle établit l'usage, le comportement constaté fait foi
   sur les paramètres et les formats de réponse ;
3. **mettre à jour le relevé** avec ce qui a été observé.

**Ne jamais** inférer le comportement depuis une implémentation existante de ce
dépôt : ce serait couler une erreur dans le béton.

Un point resté incertain après observation est **signalé comme tel**, pas
supposé. Il rejoint la section « points incertains » du relevé **et** une tâche
dans TASKS.md.

---

## 4. Tests

- **Aucune fonctionnalité sans tests, dans le même commit.**
- Un test par comportement, nommé d'après le comportement observable :
  `test_un_jingle_tombe_a_l_heure_pile`, pas `test_jingle_2`.
  Le préfixe `test_` est imposé par la collecte de pytest ; ce qui le suit décrit
  le comportement, jamais un numéro ni le nom de la fonction testée.
- Le noyau se teste **sans infrastructure** : ni réseau, ni Liquidsoap, ni fichier.
  C'est ce que garantissent les interdits du §2.
- Les doubles sont des **Fakes versionnés**, pas des mocks générés à la volée.
- Le temps et le hasard sont injectés : un test fixe l'heure et la graine, et
  **rejoue** exactement la même émission. Jamais de `sleep` réel.
- La couche qui parle au monde extérieur se teste contre des réponses
  **littérales** — y compris malformées, tronquées, vides, ou d'un type
  inattendu. Un Navidrome qui renvoie du HTML d'erreur là où du JSON était
  promis est un cas de test, pas un imprévu.
- Cible de couverture : **80 % sur l'ensemble du dépôt**, imposée par
  `pytest --cov-fail-under=80`.

### 4.1 Ce que les tests ne verront jamais

Les tests vérifient **ce qui est décidé** ; ils n'entendent rien. Ce qui suit
ne se constate qu'en écoutant réellement la radio :

| Angle mort | Ce qui s'y cache |
|---|---|
| **Le son lui-même** | Niveau, saturation, un jingle qui écrase la musique, un flash deux fois trop fort |
| **Les transitions** | Un blanc entre deux morceaux, une coupure au milieu d'un flash, un jingle à cheval sur un refrain |
| **La tenue dans la durée** | Dérive d'horloge, tampon qui se vide, fuite mémoire après six heures, jingle horaire qui glisse |
| **Les vrais lecteurs** | Se brancher au vol, se rebrancher après coupure, VLC contre navigateur contre enceinte — chacun a ses exigences d'en-têtes et de tampon |
| **Le jingle de vote** | Qu'un « encore » s'annonce à la jonction sans détonner avec la musique qui l'entoure. Un test vérifie qu'il est déclenché ; aucun ne dit s'il sonne juste |
| **La pondération par les votes** | Qu'une radio « joue moins souvent » ce qu'on passe ne s'observe qu'à l'usage, sur des **semaines**. Un test vérifie la formule ; aucun ne dit si le résultat s'entend, ni si la radio s'est resserrée (SPECS.md §4.12) |

**Conséquence à assumer** : aucun de ces défauts n'est détecté automatiquement
par qui que ce soit. Celui qui touche à ces zones **écoute réellement la radio
avant de committer** — c'est le seul filet, et il n'est pas automatique
(§1.2).

**Quand une écoute révèle un défaut, corriger le produit, jamais le harnais de
test.** Un harnais plus indulgent que la production transforme une suite de
tests en décor : les chiffres redeviennent verts, la radio continue de grésiller,
et le défaut ressort des semaines plus tard, plus cher.

---

## 5. Vérification

### 5.1 Écrire des commandes qui ne redemandent pas confirmation

Une commande ne peut entrer dans une règle de permission que si sa forme se
répète. Quatre habitudes suffisent à éviter l'essentiel des demandes :

| Faire | Plutôt que |
|---|---|
| Écrire les fichiers avec **Write** et **Edit** | `cat > f <<'EOF'`, `sed -i '…'` |
| `git commit -m "…"` (l'identité est dans `.git/config`) | `git -c user.email=… commit …` |
| Un motif `grep` stable, ou lire toute la sortie | un `grep -E "…"` différent à chaque appel |
| La commande de vérification unique (§5.2) | des variantes ponctuelles |

Les règles partagées vivent dans `.claude/settings.json`, versionné et sans
chemin machine. Ce qui dépend de la machine — chemin de la bibliothèque, jeton
Navidrome, adresse du serveur — va dans `.claude/settings.local.json` et dans le
TOML local, **jamais versionnés**. `git push` est **délibérément absent** de
l'allowlist : une action sortante se confirme.

### 5.2 La commande

À lancer **avant tout commit** :

```bash
./verifier.sh
```

C'est exactement ce que fait `/verify`. **Si elle change, elle change ici**, et
les autres fichiers la recopient.

Le script enchaîne les contrôles du moins cher au plus cher, et **s'arrête au
premier échec** (`set -euo pipefail`) :

| Contrôle | Ce qu'il refuse |
|---|---|
| `ruff format --check` | Une mise en forme qui s'écarte |
| `ruff check` | Import ou variable inutilisés, `print()`, `except` nu, argument ignoré, `import random`/`secrets` hors de `core/rng.py` |
| `mypy` (strict) | Une fonction sans annotations, un type incohérent, du code inatteignable |
| **Les interdits d'AGENTS.md §2** | Entrée-sortie dans le noyau, horloge hors de `core/clock.py`, hasard hors de `core/rng.py`, Flask hors de `adapters/web/`, `TODO` sans tâche |
| `liquidsoap --check` (image épinglée) | Un `radio.liq` que la version de production n'accepte pas |
| `pytest --cov --cov-fail-under=80` | Un test en échec, une couverture sous 80 % |

Le contrôle des interdits est ce qui distingue ce script d'un simple `make check` :
il transforme les interdits en **recherches textuelles exécutées**. Un interdit
que rien ne contrôle n'est pas un interdit, c'est un vœu — et il est toujours
enfreint, tôt ou tard, par quelqu'un de bonne foi.

Correction automatique de la mise en forme :

```bash
.venv/bin/ruff format . && .venv/bin/ruff check --fix .
```

Rien n'est déclaré terminé sans que la commande de vérification ait été lancée
**et sa sortie réellement constatée**. En cas d'échec, rapporter la sortie ; ne
jamais annoncer un succès non observé.

### 5.3 Définition de « terminé »

- [ ] `./verifier.sh` passe.
- [ ] Les tests couvrent le comportement ajouté, cas limites compris.
- [ ] Si la tâche touche au son, aux transitions, à la durée ou aux lecteurs
      (§4.1) : la radio a été **écoutée**, et ce qui a été entendu est écrit
      dans le commit.
- [ ] Aucun code mort, aucun `TODO` orphelin.
- [ ] La carte du dépôt d'[ARCHITECTURE.md](./ARCHITECTURE.md) §9 reste exacte —
      elle décrit **des dossiers et leur rôle**, elle ne se met donc à jour que
      si la structure change, pas à chaque fichier ajouté.
- [ ] La case correspondante de [TASKS.md](./TASKS.md) est cochée.
- [ ] Le commit suit §7.

---

## 6. Documentation

La documentation fait partie de la tâche, pas de son après-coup.

| Changement | Fichier à mettre à jour |
|---|---|
| Nouveau comportement audible par l'auditeur | [SPECS.md](./SPECS.md) |
| Nouvelle clé de configuration TOML | [SPECS.md](./SPECS.md) §6 |
| Décision d'architecture, dépendance, découpage | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| Nouveau dossier, ou dossier dont le rôle change | [ARCHITECTURE.md](./ARCHITECTURE.md) §9 |
| Une observation sur Navidrome, France Info, Liquidsoap, ffmpeg, YouTube/yt-dlp, un lecteur de webradio ou un flux de podcast | le relevé correspondant dans [docs/](./docs/) |
| Une route d'API ajoutée, changée ou retirée | [SPECS.md](./SPECS.md) §4.8 — c'est une surface publique |
| Nouvelle règle de développement | ce fichier |
| Procédure de contribution | [CONTRIBUTING.md](./CONTRIBUTING.md) |
| Avancement, nouvelle tâche, blocage | [TASKS.md](./TASKS.md) |

[PROMPT.md](./PROMPT.md) est **gelé** : il conserve l'intention initiale et ne se
met pas à jour. Là où une règle applicable l'a dépassé, c'est ce fichier qui fait
foi — et la divergence est consignée en fin de `PROMPT.md`.

---

## 7. Git

**Un commit = une tâche cohérente.** Format
[Conventional Commits](https://www.conventionalcommits.org/) :

```
<type>(<scope>): <description à l'impératif, en minuscules>

<corps optionnel : le pourquoi, pas le quoi>

Réf: GOAL-00X-TYY
```

Types : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `ci`.

Scopes usuels : `core`, `queue`, `schedule`, `rng`, `clock`, `navidrome`,
`source`, `jingle`, `news`, `stream`, `ffmpeg`, `http`, `config`, `control`,
`api`, `web`, `harness`.

Exemples :

```
feat(schedule): faire tomber les jingles à l'heure pile
test(navidrome): couvrir une réponse HTML là où du JSON était promis
docs(ffmpeg): relever le comportement en fin de fichier
```

Référencer l'identifiant de la tâche en pied de message : c'est ce qui relie
l'historique Git à TASKS.md.

**Un message de commit ne se passe jamais à `-m` avec des accents graves** : le
shell les prend pour des substitutions de commande et mange les mots. Utiliser
`git commit -F -` ou un heredoc cité. C'est arrivé le 2026-08-30, et la
correction est dans TASKS.md — pas dans un `--amend`.

**Jamais `git add -A` quand un autre agent écrit dans le dépôt.** On nomme les
fichiers, ou l'on attend. Un dépôt partagé n'a pas d'index par agent : `-A` prend
tout ce qui traîne, y compris ce que quelqu'un est en train d'écrire — et produit
un commit dont le message ment sur son contenu, avec du code que rien n'a
vérifié. C'est arrivé le 2026-08-30 ; l'incident est consigné dans TASKS.md.

Ne jamais committer : `.env`, un mot de passe, un jeton, le TOML local,
`.claude/settings.local.json`, un fichier audio, un artefact de build.

**Avant tout commit qui touche à la configuration**, vérifier que Git ignore bien
ce qu'il doit ignorer — c'est une commande, pas une intention :

```bash
git check-ignore -v .env webradio.toml
```

---

## 8. Détecter les incohérences

Le dépôt peut se retrouver dans un état contradictoire. Ce qui fait foi :

| Symptôme | Source de vérité |
|---|---|
| TASKS.md dit `[x]`, le code ne compile pas | **Le code.** Repasser la tâche à `[-]` et corriger |
| TASKS.md dit `[ ]`, la fonctionnalité existe | **Le code.** Cocher, après avoir vérifié qu'elle est testée |
| ARCHITECTURE.md décrit A, le code fait B | **ARCHITECTURE.md**, sauf si B est meilleur — alors mettre à jour le document et le dire |
| SPECS.md décrit un comportement absent | **SPECS.md.** C'est une tâche manquante |
| Un relevé de `docs/` contredit ce qu'on observe | **Ce qu'on observe.** Corriger le relevé |

Dans tous les cas : repérer l'incohérence, **ne pas la masquer**, corriger le
côté qui a tort, et rapporter la décision dans le rapport et dans le commit.

---

## 9. Conventions de code

Appliquées par `ruff` (mise en forme et analyse), `mypy` (types) et
`pyproject.toml`.

### Mise en forme

- Indentation : 4 espaces.
- 100 colonnes maximum par ligne.
- Imports explicites, jamais `from x import *`.
- Annotations de type **partout** : `mypy` est configuré en mode strict.

### Nommage

| Élément | Convention | Exemple |
|---|---|---|
| Module | `snake_case`, nom de ce qu'il contient | `schedule.py` |
| Classe, `Protocol` | `PascalCase` | `TrackSource` |
| Fonction, variable | `snake_case` | `next_track`, `is_news_time` |
| Constante de module | `SCREAMING_SNAKE_CASE` en tête de fichier | `DEFAULT_BITRATE` |
| Test | `test_` + le comportement observable, jamais un numéro | `test_un_jingle_tombe_a_l_heure_pile` |
| Fake | préfixe `Fake` | `FakeNavidromeSource` |
| Clé TOML | `snake_case`, en français | `duree_fondu`, `heures_thematiques` |

### Documentation du code

- Docstring **en français**, sur ce qui n'est pas évident : un choix, une
  contrainte, une raison. Pas de paraphrase de la signature.
- Un commentaire explique **pourquoi**, jamais **quoi**.

### La langue : identifiants en anglais, prose en français

**Révisé le 2026-08-30**, et c'est un renversement de la règle précédente
(« tout le projet est en français »). La frontière passe désormais entre ce que
l'outillage lit et ce qu'un humain lit :

| Ce que c'est | Langue |
|---|---|
| Classes, fonctions, variables, paramètres, membres d'énumération | **anglais** |
| Noms de modules et de fichiers de code | **anglais** |
| **Clés et sections du TOML** | **anglais** *(révisé le 2026-08-30)* |
| Docstrings, commentaires | **français** |
| SPECS, ARCHITECTURE, TASKS, AGENTS, README, relevés `docs/` | **français** |
| Messages de commit | **français** |
| Chaînes affichées à l'auditeur, messages de journal | **français** |

> **Pourquoi cette frontière et pas une autre.** Un identifiant est lu par
> l'outillage autant que par un humain : `mypy`, `ruff`, les traces d'erreur,
> la complétion et toutes les bibliothèques tierces sont anglophones, et un
> `Fenetre` au milieu d'un `TypeError` détonne. La prose, elle, sert à
> expliquer un **pourquoi** — et elle le fait mieux dans la langue de celui qui
> l'écrit.
>
> **Ce que ce renversement coûte** : 83 classes et 248 fonctions renommées d'un
> coup. L'historique porte donc un commit de renommage massif **sans aucun
> changement de comportement** — c'est délibéré, et c'est ce qui le rend
> relisible.

Un exemple du style attendu :

```python
def prochain_morceau(self) -> Piste:
    """Un artiste ne peut pas revenir avant que trois autres soient passés.

    Sans cette contrainte, un tirage uniforme sur une bibliothèque où un
    artiste pèse lourd le fait réapparaître toutes les deux ou trois pistes,
    ce qui s'entend immédiatement comme un défaut de la radio.
    """
```

---

## 10. Que faire quand on est bloqué

- **ffmpeg manque une option** → constater ce que la version installée accepte,
  le consigner dans [docs/ffmpeg.md](./docs/ffmpeg.md) ; ne pas contourner en
  dégradant silencieusement le format.
- **Navidrome répond autrement que la spécification Subsonic** → c'est Navidrome
  qui fait foi. Consigner l'écart dans
  [docs/navidrome.md](./docs/navidrome.md).
- **Le flash France Info est indisponible ou tronqué** → ce n'est pas une panne,
  c'est un cas nominal : la radio se replie sur la musique. Si SPECS.md ne dit
  pas comment, c'est une ambiguïté de spécification (§1.2).
- **Un lecteur de webradio décroche** → ce n'est presque jamais le lecteur.
  C'est un changement de format en cours de flux (SPECS.md §7 n°11). Consigner
  dans [docs/flux-icy.md](./docs/flux-icy.md) quel lecteur, à quel moment.
- **La spécification est ambiguë** → poser la question. Ne pas trancher en
  silence un comportement que l'auditeur entendra.
- **Une abstraction résiste** → le dire. Contourner une abstraction est une
  dette ; la réparer est une étape.
