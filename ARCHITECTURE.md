# ARCHITECTURE.md — Architecture technique

La source de vérité **technique** : comment la radio est conçue. Le **quoi** est
dans [SPECS.md](./SPECS.md), les **règles** dans [AGENTS.md](./AGENTS.md).

Ce document décrit des **décisions et leurs raisons**, pas un inventaire de
fichiers. La §9 fait exception : elle décrit des dossiers et leur rôle, et c'est
elle qu'un agent lit pour savoir **ce qui existe vraiment**.

---

## 1. Découpage

Deux zones, et une frontière qui ne se franchit que dans un sens :

```
webradio/
  core/        les décisions — ne parle à personne
  adapters/    le monde extérieur — ne décide de rien
  app/         l'assemblage — câble les deux, une seule fois
```

**Le noyau décide, les adaptateurs exécutent.** Le noyau reçoit des données
(une liste de pistes, une heure, une graine) et rend des décisions (quelle piste
ensuite, faut-il un jingle maintenant). Il n'ouvre aucune connexion, ne lit aucun
fichier, ne lance aucun processus.

### 1.1 Ce qui ne franchit pas la frontière du noyau

Aucun `import` de `httpx`, `requests`, `aiohttp`, `subprocess`, `socket`,
`asyncio` ni d'ouverture de fichier dans `webradio/core/` — c'est un interdit
contrôlé par `/verify` (AGENTS.md §2).

La raison n'est pas esthétique. **Une radio est une machine à décider dans le
temps** : quelle piste, à quelle heure, après quoi. Si ces décisions sont
enchevêtrées avec des appels réseau, on ne peut plus les rejouer — et une
émission qu'on ne peut pas rejouer ne peut pas être testée.

## 2. Le trajet d'une donnée

De la connexion d'un auditeur jusqu'au son :

```
un auditeur se branche sur GET /flux
        ↓
app/         personne n'écoutait ? → démarre la chaîne
        ↓
core/queue   « il me faut une piste » → interroge la grille et le tirage
        ↓
core/schedule  quelle heure ? jingle dû ? flash dû ? plage thématique ?
core/rng       tirage contraint par le genre et la non-répétition
        ↓
adapters/navidrome   résout la piste choisie → une URL de flux audio
        ↓
adapters/ffmpeg      décode, normalise, encode en un flux unique
        ↓
adapters/http        fan-out : le même flux vers N connexions
        ↓
    tous les auditeurs entendent la même chose au même instant
        ↓
dernière déconnexion → la chaîne s'arrête
```

Le point important : **la file ne pousse pas, elle est tirée**. C'est l'encodeur
qui réclame la piste suivante quand il en a besoin ; le noyau ne connaît ni le
temps réel, ni les tampons.

### 2.1 Ce qui doit rester confiné

Les laisser remonter, c'est répandre dans tout le code une dépendance qu'un seul
fichier devrait porter.

| Détail | Confiné dans |
|---|---|
| L'API Subsonic : `salt`, `token`, `u`, `p`, `v`, `c`, la forme des réponses | `adapters/navidrome/` |
| Les options de ligne de commande ffmpeg, ses codes de sortie, sa sortie d'erreur | `adapters/ffmpeg/` |
| Les en-têtes HTTP du flux, le `Content-Type`, la gestion des connexions | `adapters/http/` |
| L'adresse et le format du flash France Info | `adapters/news/` |
| La syntaxe TOML et le nom des clés | `adapters/config/` |
| Flask, ses routes, ses requêtes et ses réponses | `adapters/web/` |
| Jinja2 et ses gabarits | `adapters/web/templates/` |

Au-dessus de ces dossiers, plus personne ne connaît de code HTTP, de nom de
codec, ni de clé de configuration : le noyau manipule des `Piste`, des `Genre`,
des `Instant` et des `Decision`.

## 3. Injection des dépendances

Pas de conteneur, pas de framework : **l'assemblage se fait à la main dans
`app/`**, une seule fois au démarrage. Le noyau reçoit ses dépendances par
constructeur, sous forme de `Protocol` (typage structurel), ce qui rend les
Fakes de test triviaux et ne coûte aucune bibliothèque.

### 3.1 Une seule horloge, un seul hasard

**C'est la décision structurante de ce projet.** Une radio *est* une grille
horaire et un tirage : si l'heure et le hasard sont lus n'importe où, la moitié
du produit devient intestable.

- `core/clock.py` — la **seule** source de temps. Un test fixe l'heure et fait
  avancer la journée à volonté.
- `core/rng.py` — la **seule** source de hasard, initialisée par une graine. Un
  test fixe la graine et **rejoue exactement la même émission**.

L'interdit correspondant est contrôlé par `/verify` : aucun `datetime.now()`,
`time.time()`, `random.` ni `secrets.` ailleurs (AGENTS.md §2).

Un exemple de ce que cela permet et qui serait autrement impossible : *« faire
tourner une journée entière de programmation en quelques millisecondes, et
vérifier que chaque jingle est tombé dans sa fenêtre. »*

## 4. Le flux, et pourquoi il n'y a ni Icecast ni Liquidsoap

SPECS.md §1 exige que **rien ne tourne tant que personne n'écoute**. Le modèle
radio classique — une source qui alimente Icecast en permanence — contredit cette
exigence par construction : la station diffuse dans le vide, auditeurs ou non.

D'où le choix : **notre propre serveur HTTP, et ffmpeg en sous-processus**.

| Conséquence | Détail |
|---|---|
| Ce qu'on gagne | Le démarrage à la demande, littéralement ; une seule dépendance externe ; tout le reste est à nous, et testable |
| Ce qu'on paie | Les transitions, les fondus et l'insertion des jingles sont à écrire — Liquidsoap les offrait |
| Ce qu'il faut surveiller | Le cycle de vie du sous-processus. Un ffmpeg orphelin qui survit à la dernière déconnexion annule tout le bénéfice du démarrage à la demande |

### 4.0 La contrainte qui commande tout le reste

SPECS.md §4.9 pose trois exigences qui ne sont pas spontanément compatibles :
**lisible par tout lecteur de webradio**, **sans coupure**, et **transcodant le
moins possible**.

Elles se heurtent sur un point précis : transmettre un fichier tel quel économise
la machine, mais un changement de codec, de fréquence d'échantillonnage ou de
nombre de canaux **en cours de flux** est exactement ce qui fait décrocher un
lecteur de webradio — lequel a lu les en-têtes une fois, au branchement, et ne
les relit pas.

S'y ajoute que jingles — horaires comme de vote — et flashs viennent
d'**origines différentes** de la musique : les insérer suppose de les ramener au
format du flux, ou de tout ramener à un format commun.

**Aucune voie n'est retenue à ce stade** : c'est la décision ouverte
SPECS.md §7 n°11, et elle ne se tranche pas avant les relevés
[docs/ffmpeg.md](./docs/ffmpeg.md), [docs/flux-icy.md](./docs/flux-icy.md) et
[docs/navidrome.md](./docs/navidrome.md).

Ce qui est **déjà acquis** : la contrainte de non-coupure prime sur l'économie de
ressources. Une radio économe qui fait décrocher les lecteurs ne remplit pas sa
fonction ; une radio qui encode en permanence la remplit, mal.

### 4.1 Un flux, N auditeurs

Un seul encodage alimente toutes les connexions : chaque auditeur reçoit une
copie du **même** flux, au même instant (SPECS.md §4.1). Un auditeur lent ne doit
ralentir ni l'encodage, ni les autres — sa connexion est abandonnée avant de
devenir un frein.

## 5. Persistance

**Aucune.** La radio ne garde rien entre deux démarrages : ce qui est passé est
perdu (SPECS.md §2). Pas de base, pas de cache sur disque, pas d'historique.

Le seul état qui survit à une piste est en mémoire, et disparaît avec la chaîne :
la fenêtre de non-répétition, et l'effet en cours d'un `encore`.

### 5.1 Les secrets

Les identifiants Navidrome vivent dans le TOML local, **jamais versionné**. Un
exemple commenté l'est, sans secret.

L'API Subsonic accepte un jeton dérivé plutôt qu'un mot de passe en clair : la
forme retenue relèvera de [docs/navidrome.md](./docs/navidrome.md), une fois
observée. Dans tous les cas, **aucun identifiant ne paraît dans un journal** —
c'est un interdit contrôlé (AGENTS.md §2).

## 6. Le pilotage, l'API et l'interface web

Trois couches, et la frontière entre elles est la même que partout ailleurs.

```
navigateur
    ↓  (formulaire ou fetch)
adapters/web/     Flask : routes, gabarits Jinja2, mise en page
    ↓  (appel d'API, jamais d'appel direct au noyau)
adapters/web/api  la surface publique : ce qui passe, voter, refuser
    ↓
core/control      l'effet de `stop` et `encore` sur ce que la file rendra
```

**`stop` et `encore` sont des décisions, donc du noyau.** Leur effet se spécifie
et se teste sans Flask, sans HTTP et sans navigateur.

**L'interface web n'a aucun chemin privilégié** : ses boutons passent par l'API,
comme le ferait n'importe quel autre client (SPECS.md §4.8). C'est un interdit,
pas une convention : un gabarit Jinja2 ou une route Flask qui appellerait le
noyau directement créerait un second chemin, qui divergerait du premier.

### 6.1 Ce que l'API doit refuser

Pendant un jingle ou un flash, un vote n'est pas applicable (SPECS.md §4.6). Le
refus est **explicite et motivé** : l'appelant apprend qu'il a été refusé et
pourquoi. Un refus muet est indistinguable d'une panne, et pousse à réessayer.

C'est le noyau qui sait s'il est dans un jingle, un flash ou de la musique — donc
c'est lui qui refuse. L'API traduit ce refus en réponse HTTP ; elle ne le décide
pas.

### 6.2 Le jingle de vote

Un vote « encore » enregistré fait diffuser `encore.mp3` **à la jonction**, entre
le morceau en cours et le suivant (SPECS.md §4.6).

Il emprunte **exactement le même chemin** que les jingles horaires : même
mécanique d'insertion, même contrainte de format (§4.0), même traitement d'un
fichier absent. Une seule différence, et elle est dans le noyau : il est
déclenché par un **événement** — un vote — là où les jingles horaires le sont par
l'**horloge**.

> **C'est une simplification obtenue en renonçant à quelque chose.** Une note
> mêlée par-dessus la musique aurait accusé réception immédiatement ; elle aurait
> imposé un second chemin d'insertion, capable de mixer deux sources en temps
> réel. Le jingle à la jonction ne demande rien de nouveau — au prix d'un accusé
> de réception différé jusqu'à la fin du morceau en cours. Le renoncement est
> délibéré (SPECS.md §7 n°10).

Conséquence pour le noyau : la file doit savoir qu'**un jingle de vote est dû**
au même titre qu'un jingle horaire, et les deux peuvent tomber sur la même
jonction. Ce qui se passe alors — les deux, un seul, dans quel ordre — n'est pas
spécifié : c'est une question à poser avant `GOAL-007`, pas à trancher en
implémentant.

## 7. Erreurs

Les erreurs techniques sont traduites en erreurs **métier** au plus près de leur
origine : un code HTTP 500 de Navidrome devient une `SourceIndisponible`, pas une
exception `httpx` qui traverse le programme. Au-dessus des adaptateurs, plus
personne ne connaît de code HTTP ni de nom de codec.

Deux régimes, nettement séparés (SPECS.md §5) :

- **au démarrage**, une erreur est **fatale** et se dit : la chaîne refuse de
  démarrer, l'auditeur reçoit une réponse explicite ;
- **en cours de diffusion**, elle se **contourne** et se journalise : la radio ne
  se tait pas.

`except:` nu et `except Exception: pass` sont interdits (AGENTS.md §2) : dans une
radio, une exception avalée produit un silence, et un silence ne remonte nulle
part.

## 8. Tests

- Le noyau se teste **sans rien** : ni réseau, ni ffmpeg, ni fichier. C'est ce
  que garantissent les interdits du §1.1.
- Horloge et graine fixées : une émission se **rejoue** à l'identique.
- Les adaptateurs se testent contre des réponses **littérales**, y compris
  malformées, tronquées, vides, ou d'un type inattendu.
- Les Fakes sont versionnés, jamais générés à la volée.
- Couverture : **80 % sur l'ensemble du dépôt**, imposée par
  `pytest --cov-fail-under=80`.

Et surtout : **les tests n'entendent rien**. Quatre angles morts sont recensés en
AGENTS.md §4.1, aucun n'est couvert automatiquement.

## 9. Carte du dépôt

**Ce que contient réellement le dépôt aujourd'hui.** C'est la section qu'un agent
lit avant de créer quoi que ce soit, pour ne pas recréer ce qui existe. Elle se
met à jour quand la **structure** change, pas à chaque fichier ajouté.

```
.
├── CLAUDE.md ............ aiguilleur : quoi lire, dans quel ordre
├── PROMPT.md ............ l'intention initiale, gelée
├── SPECS.md ............. le quoi
├── ARCHITECTURE.md ...... le comment (ce fichier)
├── AGENTS.md ............ les règles
├── TASKS.md ............. l'ordre — mémoire persistante
├── CONTRIBUTING.md ...... comment contribuer
├── README.md ............ documentation générale
├── docs/
│   ├── navidrome.md ..... relevé de l'API Subsonic telle que Navidrome l'implémente
│   ├── franceinfo.md .... relevé du flash d'information
│   ├── ffmpeg.md ........ relevé des options réellement acceptées
│   └── flux-icy.md ...... relevé de ce qu'attendent les lecteurs de webradio
└── .claude/
    ├── settings.json .... permissions partagées, versionnées
    └── commands/ ........ goal · task · status · verify
```

**Le code n'existe pas encore.** `GOAL-001` le posera :
`webradio/core/`, `webradio/adapters/`, `webradio/app/`, `tests/`,
`pyproject.toml`. `adapters/web/` (Flask) et ses gabarits Jinja2 arrivent avec
`GOAL-009`. Cette section est mise à jour par `GOAL-001-T02` puis par la
dernière tâche de chaque Goal (AGENTS.md §5.3).

### 9.1 Écarts assumés

Ce que le projet fait sciemment autrement que ce qu'on attendrait, et pourquoi.
Un écart écrit ici est visible ; un écart tu est une dette.

_(vide au démarrage — la décision ouverte SPECS.md §7 n°2, sur la modularité des
sources, atterrira ici si elle est tranchée en faveur d'une abstraction
anticipée.)_
