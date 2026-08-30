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
    sources/     d'où vient la musique — Navidrome aujourd'hui
    podcast/     les émissions programmées
    ffmpeg/      l'encodage
    http/        le flux servi aux auditeurs
    web/         Flask, l'API et les gabarits Jinja2
    config/      la lecture du TOML
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
un auditeur se branche sur GET /flux — chez Liquidsoap
        ↓
Liquidsoap   POST /playout/listeners → « quelqu'un écoute » ; POST /playout/next → « quoi jouer ? »
        ↓
app/         traduit : app/liquidsoap_playout → app/playout.next_entry()
        ↓
core/queue   « il me faut une piste » → interroge la grille et le tirage
        ↓
core/schedule  quelle heure ? jingle dû ? flash dû ? plage thématique ?
core/rng       tirage contraint par le genre et la non-répétition
        ↓
adapters/sources     résout la piste choisie → une URL de flux audio
        ↓
adapters/web/playout_api   rend le chemin ou l'URL, en texte brut
        ↓
Liquidsoap   décode, normalise, enchaîne en fondu, encode, sert à N connexions
             POST /playout/playing → « je commence celui-ci » → l'API l'affiche
        ↓
    tous les auditeurs entendent la même chose au même instant
        ↓
dernière déconnexion → POST /playout/listeners « 0 » → plus rien n'est demandé
```

Le point important : **la file ne pousse pas, elle est tirée**. C'est Liquidsoap
qui réclame la piste suivante quand il en a besoin — toujours une d'avance
(docs/liquidsoap.md §3) ; le noyau ne connaît ni le temps réel, ni les tampons.

### 2.1 Ce qui doit rester confiné

Les laisser remonter, c'est répandre dans tout le code une dépendance qu'un seul
fichier devrait porter.

| Détail | Confiné dans |
|---|---|
| L'API Subsonic : `salt`, `token`, `u`, `p`, `v`, `c`, la forme des réponses | `adapters/sources/navidrome/` |
| Le langage de Liquidsoap, l'encodage, les fondus, les en-têtes du flux, les connexions | `adapters/liquidsoap/radio.liq` |
| Les deux routes que Liquidsoap appelle, et leur contrat en texte brut | `adapters/web/playout_api.py` |
| L'adresse du direct France Info | Le TOML (`adapters/config/`) — et c'est tout : un direct est une entrée ffmpeg comme une autre (`docs/franceinfo.md` §1.bis, `GOAL-015`) |
| Le format RSS d'un podcast, ses `enclosure`, ses redirections | `adapters/podcast/` |
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

## 4. Le flux : Liquidsoap, piloté morceau par morceau par le noyau

> **Décision du 2026-08-30** (SPECS.md §7 n°23, relevé
> [docs/liquidsoap.md](./docs/liquidsoap.md)). Le premier choix — notre serveur
> HTTP et ffmpeg en sous-processus — a été construit (`GOAL-004`) puis relu :
> six de ses sept défauts étaient dans le cycle de vie des processus et des
> connexions. Ce sont précisément les choses qu'un outil de diffusion fait à
> notre place. La migration (`GOAL-016`) a supprimé `adapters/ffmpeg/` et
> `adapters/http/` ; [docs/ffmpeg.md](./docs/ffmpeg.md) reste un relevé
> historique, et vaut encore pour ce que Liquidsoap fait avec ffmpeg en dessous.

**Le partage est net** : le noyau décide de *quoi* jouer, Liquidsoap fait
*tout le reste*.

```
Liquidsoap  ──« morceau suivant ? »──▶  adapters/liquidsoap  ──▶  app/playout.next_entry()
            ◀──── un chemin ou une URL ──                       (noyau, grille, jingles, émissions)
            ──« un auditeur arrive / part »──▶  compteur d'auditeurs (app/radio)
```

| Conséquence | Détail |
|---|---|
| Ce qu'on gagne | Enchaînement, fondus, niveau, fan-out, auditeur lent, déconnexion brutale, direct borné dans le temps — éprouvés ailleurs, pas écrits ici |
| Ce qu'on paie | Un processus debout en permanence (rien de décodé sans auditeur, ~0,8 % d'un cœur) ; une image de 967 Mo ; un script `.liq` dont la syntaxe dépend de la version |
| Ce qu'il faut surveiller | **Que Liquidsoap ne décide jamais.** Une `playlist()` dans le script, un `random` de Liquidsoap, un jingle inséré par le script : c'est le noyau contourné, et ce qu'aucun test ne verra |

**Le script n'a pas de raccourci**, comme l'interface web (§6) : il demande le
morceau suivant à l'API, il annonce ses auditeurs à l'API. Il ne lit ni le TOML,
ni la base, ni Navidrome.

### 4.0 Un format unique, réencodé en permanence

SPECS.md §4.9 exige **lisible par tout lecteur** et **sans coupure**, et §7 n°11
place l'économie de la machine en troisième. Liquidsoap réencode tout vers un
seul format (`%mp3(bitrate=…)` dans `radio.liq`) : un lecteur ne voit jamais le
format changer, quelle que soit l'hétérogénéité de la bibliothèque
(docs/navidrome.md §3.1). Le coût mesuré est de l'ordre d'un pour cent d'un
cœur (docs/ffmpeg.md §2.bis, docs/liquidsoap.md §1.3) : il n'y a rien à
optimiser.

### 4.1 Un flux, N auditeurs, un morceau d'avance

Un seul encodage alimente toutes les connexions ; l'auditeur lent, la
déconnexion brutale et le fan-out sont l'affaire de `output.harbor`, pas la
nôtre. Ce qui reste à nous, et que `app/liquidsoap_playout.py` tient :
Liquidsoap **demande toujours un morceau d'avance** (`prefetch=1` est le
minimum, docs/liquidsoap.md §3). *Demandé* n'est donc pas *à l'antenne* — l'API
n'affiche un morceau que lorsque Liquidsoap dit l'avoir commencé.

### 4.2 Couper en le disant

Laissé à lui-même, Liquidsoap réessaie sans fin et sert du silence
(docs/liquidsoap.md §3). Le script s'arrête donc de lui-même — `shutdown()` —
quand l'API répond « fini » (204) ou ne répond pas deux fois de suite ; le
superviseur (Compose, `restart`) relance un processus neuf, et un auditeur qui
se rebranche entend une radio neuve (SPECS.md §4.7).

## 5. Persistance

**Presque aucune, et l'exception est nommée.**

En mémoire, et perdu avec la chaîne : la fenêtre de non-répétition, l'effet en
cours d'un `encore`, la file. Pas de base, pas de cache sur disque, pas
d'historique de ce qui est passé à l'antenne.

**Sur disque, une seule chose** (SPECS.md §4.11.1) :

> Pour chaque émission, **l'identifiant du dernier épisode diffusé**.

### 5.0 Pourquoi cette exception existe, et comment la garder petite

Elle n'était pas prévue. SPECS.md §7 n°14 avait d'abord choisi « l'épisode le
plus récent », **précisément parce que cela ne demandait aucun état**. Le relevé
a montré qu'un podcast entre deux saisons rejouerait alors le même épisode
pendant des mois ([docs/podcast.md](./docs/podcast.md) §3.3.3), et l'auteur a
tranché pour « ne pas rediffuser » en sachant ce que cela coûtait.

**La conduite à tenir maintenant est celle d'un écart assumé** (§9.1) : cet état
est une exception, pas une porte ouverte.

- Il contient **un identifiant par émission**. Rien d'autre n'a le droit d'y
  entrer — ni l'historique des morceaux, ni des statistiques, ni une position de
  lecture. La première chose qu'on y ajoutera « puisqu'il existe déjà » sera
  celle qui aura transformé une exception en base de données.
- **Le perdre n'est pas une panne** : la radio rediffusera une fois l'épisode le
  plus récent, puis reprendra son cours. Il n'y a donc rien à sauvegarder, rien
  à migrer, aucun schéma à faire évoluer.
- Il est **écrit par la radio**, jamais par l'auteur : il ne va ni dans le TOML
  ni dans `.env`, et il n'est pas versionné.

### 5.1 SQLite, et pourquoi ce n'est pas démesuré

**Décidé le 2026-08-30** : le stockage est **SQLite**, via `sqlite3` de la
bibliothèque standard. Pas d'ORM, pas de migrations, pas de dépendance.

L'objection évidente — *une base de données pour un identifiant par émission ?* —
tombe devant un fait d'architecture : **il y aura deux processus vivants**. La
chaîne de diffusion écrit l'identifiant quand une émission démarre ; le serveur
Flask (`GOAL-008`, `GOAL-009`) lit l'état pour dire ce qui passe. Un fichier JSON
demanderait alors d'écrire soi-même ce que SQLite fait déjà correctement :
écriture atomique, lecture concurrente cohérente, et pas de fichier tronqué si
la machine s'éteint pendant l'écriture.

Le schéma tient en une table :

```sql
CREATE TABLE IF NOT EXISTS emissions_diffusees (
    emission   TEXT PRIMARY KEY,   -- le `nom` déclaré au TOML
    episode    TEXT NOT NULL,      -- le guid de l'épisode diffusé
    diffuse_le TEXT NOT NULL       -- ISO 8601, pour le journal et le diagnostic
);
```

**La garde de §5.0 disait** : *rien d'autre n'a le droit d'entrer, et surtout pas
« puisqu'on a une base ». Une seconde table n'arrive qu'avec une décision
écrite.*

### 5.2 La seconde table, et sa décision écrite

**Décidée le 2026-08-30** : les votes `stop` et `encore` sont enregistrés et
pondèrent les tirages suivants (SPECS.md §4.12, `GOAL-012`).

```sql
CREATE TABLE IF NOT EXISTS votes (
    portee       TEXT NOT NULL,    -- 'piste' ou 'artiste'  (SPECS.md §7 n°16)
    cible        TEXT NOT NULL,    -- l'identifiant de piste, ou le nom d'artiste
    score_stop   REAL NOT NULL DEFAULT 0,
    score_encore REAL NOT NULL DEFAULT 0,
    vu_le        TEXT NOT NULL,    -- ISO 8601 du dernier écrit
    PRIMARY KEY (portee, cible)
);
```

**Des scores décimaux, pas des compteurs entiers** — et ce n'est pas un détail.
Avec `stops INTEGER` et une seule date, douze `stop` dont le dernier date d'hier
compteraient tous comme frais : la décroissance de SPECS.md §7 n°18 serait
fausse, et personne ne s'en apercevrait.

Le score porte donc **la décroissance déjà appliquée**. À chaque écriture :

```
score ← score × 2^(−Δt / demi_vie) + increment
vu_le ← maintenant
```

où `Δt` est le temps écoulé depuis `vu_le`, et `increment` vaut 1 ou 0,25 selon
la portée (SPECS.md §4.12). La même décroissance s'applique **à la lecture**,
entre `vu_le` et l'instant courant.

C'est exact, incrémental, et cela ne demande de retenir que deux nombres et une
date par cible. Conserver chaque vote individuellement aurait été la solution
naïve : une table qui grossit indéfiniment pour une information qu'on peut
résumer.

**La garde n'a pas sauté, elle a fonctionné** : c'est parce qu'elle exigeait une
décision écrite que cet ajout est spécifié, borné et daté, au lieu d'être glissé
dans un commit d'implémentation. Elle reste en vigueur pour la **troisième**
table.

### 5.3 Ce que la pondération impose au noyau

`core/rng.py` ne sait aujourd'hui que **choisir uniformément**
(`Hasard.choisir(parmi)`). Un tirage pondéré est une capacité **différente**, pas
un réglage de la première.

Deux conséquences à ne pas manquer :

- **Le noyau reste pur.** Les poids lui sont **fournis**, comme les pistes : il
  ne va pas les chercher dans SQLite. C'est un adaptateur qui les charge, et la
  frontière du §1.1 tient sans exception.
- **Un tirage pondéré reste rejouable.** À graine et poids fixés, la même
  émission doit se rejouer à l'identique — sans quoi on perd ce que
  `GOAL-003-T02` avait acheté, et les tests de la file avec.

### 5.4 Ce que la base ne contiendra toujours pas

Ni l'historique de ce qui est passé à l'antenne, ni de statistiques d'écoute, ni
de position de lecture, ni de profil. Deux tables : le dernier épisode diffusé de
chaque émission, et les compteurs de votes.

Le fichier vit à un chemin déclaré au TOML, hors du dépôt. Il n'est pas
versionné, il n'a pas de sauvegarde, et le perdre n'est pas une panne (§5.0).

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

### 5.2 Les émissions, et l'absence de persistance

Une émission **remplace** la programmation au lieu de s'y insérer
(SPECS.md §4.11). Pour le noyau, cela veut dire que la file n'a rien à tirer
pendant sa durée : ni grille, ni non-répétition, ni tirage.

**L'absence de persistance est préservée.** C'est l'**épisode le plus récent**
qui est diffusé (SPECS.md §7 n°14), donc rien n'est retenu d'une fois sur
l'autre. L'option écartée — « le suivant non encore diffusé » — aurait imposé le
premier état durable du projet, et donc une décision d'architecture, pour un gain
d'usage mince.

**Le rattrapage se décide avant de servir.** Une émission manquée est rattrapée
dans la limite de sa durée (SPECS.md §7 n°13) — or la durée n'est connue
qu'**après avoir lu le flux du podcast**. Au démarrage de la chaîne, il faut donc
interroger le podcast pour savoir s'il y a lieu de rattraper, avant même de
savoir si l'on s'en servira.

C'est le seul endroit où le démarrage de la chaîne dépend d'un appel réseau qui
peut ne servir à rien. Si le flux est injoignable, il n'y a pas de rattrapage :
la radio démarre sur la musique et journalise (SPECS.md §5).

**Les jingles dus pendant une émission sont abandonnés** (SPECS.md §7 n°15).
Conséquence pour le noyau : la programmation d'une émission n'est pas une
insertion dans la file, c'est une **suspension** de tout ce qui l'alimente —
grille, non-répétition, tirage et habillage compris.

### 5.3 Les sources

Le noyau ne connaît qu'un `Protocol` : **chercher, tirer sous contrainte,
résoudre une piste en flux audio**. Rien d'autre ne le traverse — ni la grille,
ni la non-répétition, ni le tirage, qui sont décidés au-dessus et ne dépendent
d'aucune source.

Le mécanisme est **complet** : les sources sont déclarées au TOML et plusieurs
peuvent être activées (SPECS.md §4.10). **Une seule est écrite** — Navidrome.

C'est un **écart assumé** à l'interdit d'anticipation, consigné en §9.1. Ce qui
suit en découle et doit rester vrai : le registre ne contient qu'une entrée, et
tant qu'il n'en contient qu'une, **aucun code ne doit supposer qu'il y en a
plusieurs**. La façon de combiner plusieurs sources actives est explicitement non
spécifiée (SPECS.md §7 n°12) : la première tentative de la deviner serait la
seconde anticipation, celle-là non consignée.

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
au même titre qu'un jingle horaire.

**Quand plusieurs jingles sont dus à la même jonction, ils passent tous, à la
suite** : les jingles horaires d'abord, dans l'ordre chronologique, puis
`encore.mp3` en dernier — il annonce le morceau qui suit immédiatement et perdrait
son sens s'il en était séparé (SPECS.md §4.3).

Puisque aucun jingle n'est jamais abandonné pour retard (SPECS.md §7 n°4), un
morceau très long peut faire s'accumuler deux jingles horaires. C'est un cas
nominal, pas une anomalie.

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

### 7.1 La limite du second régime

« Ne pas se taire » n'est pas « ne jamais s'arrêter ». La radio **tient, puis
coupe en le disant** (SPECS.md §5.1) : elle continue sur ce qu'elle a, réessaie
en arrière-plan, relance ffmpeg une fois — et si rien ne revient, elle coupe.

Elle ne boucle **jamais** sur ce qu'elle a déjà joué pour donner le change. Ce
serait la seule façon de ne jamais couper, et ce serait la pire : une panne
masquée n'est jamais réparée, ce qui contredit frontalement « les erreurs se
voient » (AGENTS.md §2).

La coupure a un coût faible et connu : l'auditeur se rebranche, ce qui redémarre
une chaîne neuve — le mécanisme du démarrage à la demande existe déjà (§4).

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

## 8.5 Déploiement — Docker et Compose

**Décidé le 2026-08-30** : la station tourne en conteneur, orchestrée par un
`docker-compose.yml`.

### 8.5.1 Ce que le conteneur résout ici

Ce projet a une dépendance lourde et versionnée : **Liquidsoap**, dont la
syntaxe change de version en version (docs/liquidsoap.md §1.7). Le Compose
épingle l'image contre laquelle le relevé a été établi — `v2.3.3` — et
`verifier.sh` valide le script **dans cette image**. La même chose valait pour
ffmpeg avant la migration, et pour la même raison.

### 8.5.2 Deux services

```
services:
  radio:       Python — le noyau, l'API, l'interface, les routes de Liquidsoap
  liquidsoap:  l'image épinglée, le script monté en lecture seule, le port du flux
```

**Deux, pas un**, parce que le second est un binaire tiers qui n'a rien à faire
dans l'image Python ; et **pas davantage**, parce que le protocole entre eux
tient en trois routes de texte brut. Les jingles sont montés **au même chemin**
dans les deux : `radio` rend des chemins, `liquidsoap` les ouvre.

Navidrome n'est **pas** dans le Compose : il existe déjà, il appartient à
l'auteur, et le projet n'a pas à le déployer (SPECS.md §2 — gérer la
bibliothèque est hors périmètre).

### 8.5.3 Ce qui doit traverser la frontière du conteneur

| Ce qui entre | Comment | Pourquoi |
|---|---|---|
| Les **secrets** | `env_file: .env` | Jamais dans l'image, jamais dans le Compose |
| La **configuration** | volume, en lecture seule | Elle change sans reconstruire l'image |
| Les **jingles** | volume, en lecture seule | Ce sont les fichiers de l'auteur ; le conteneur ne doit pas pouvoir les modifier |
| L'**état SQLite** | volume, en écriture | Il survit à une reconstruction (§5.1) |
| Le **port du flux** (`liquidsoap`) et **du web** (`radio`) | `ports:` | C'est par là qu'on écoute |
| Le **script** `radio.liq` | volume, en lecture seule | Il est versionné avec le code qui le pilote |

> **Le réseau est le point à ne pas manquer.** Navidrome répond à `http://music`
> — un nom résolu par le réseau **de l'hôte**. Un conteneur ne le résout pas
> forcément. C'est un cas de test au premier démarrage, pas une évidence.

### 8.5.4 Ce que le conteneur ne doit pas cacher

`docker compose up` ne remplace pas `./verifier.sh` : la vérification tourne
**hors conteneur**, sur le code, comme aujourd'hui. Un conteneur qui démarre ne
prouve rien sur la qualité de ce qu'il contient.

Et il ne comble aucun des angles morts d'AGENTS.md §4.1 : le son, les
transitions, la tenue dans la durée et les vrais lecteurs restent à écouter.

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
├── pyproject.toml ....... paquet, ruff, mypy, pytest, couverture
├── verifier.sh .......... LA commande de vérification (AGENTS.md §5.2)
├── Dockerfile, docker-compose.yml, .dockerignore
├── jingles/ ............. les jingles de l'auteur — versionné vide, contenu ignoré
├── webradio.exemple.toml  toutes les clés, commentées — webradio.toml n'est pas versionné
├── .env.exemple ......... les noms des secrets — .env n'est pas versionné
│
├── webradio/
│   ├── core/ ............ les décisions — ne parle à personne
│   │   ├── clock.py ..... la SEULE source de temps
│   │   ├── rng.py ....... la SEULE source de hasard — uniforme et pondéré
│   │   ├── models.py .... Track — ce qu'il faut pour décider
│   │   ├── sources.py ... MusicSource (Protocol) + SourceUnavailable
│   │   ├── rotation.py .. la fenêtre de non-répétition, et son rétrécissement
│   │   ├── queue.py ..... ce qui passe ensuite, et ce qui a été relâché
│   │   ├── bands.py ..... les plages thématiques de la grille
│   │   ├── programmes.py  les programmes : une playlist, des jours, des heures
│   │   ├── jingles.py ... quel jingle est dû, d'après l'heure
│   │   ├── shows.py ..... quelle émission est due, d'après la grille déclarée
│   │   ├── control.py ... l'effet de stop et encore, et le refus motivé
│   │   └── weighting.py . des votes aux poids du tirage
│   ├── adapters/ ........ le monde extérieur — ne décide de rien
│   │   ├── config/ ...... schema.py (les clés du TOML) · loading.py (fichier et .env)
│   │   ├── sources/ ..... navidrome.py — l'API Subsonic, et rien d'autre ne la connaît
│   │   ├── podcast/ ..... feed.py — RSS, enclosure, redirections
│   │   ├── liquidsoap/ .. radio.liq — demande, annonce, sert ; ne décide de rien
│   │   ├── state/ ....... database.py — SQLite : diffusions et votes
│   │   └── web/ ......... api.py (la surface publique) · playout_api.py (les routes de Liquidsoap) · views.py · templates/
│   └── app/ ............. l'assemblage, une fois au démarrage
│       ├── main.py ...... le point d'entrée : construit, branche, attend
│       ├── playout.py ... noyau → ffmpeg : la piste suivante, et les jingles à la jonction
│       ├── radio.py ..... noyau → API : la façade que l'interface interroge
│       ├── learning.py .. votes → poids : la base vue par le noyau
│       ├── show_scheduler.py  émission due → épisode à diffuser
│       └── liquidsoap_playout.py  demandé ≠ à l'antenne, et le compteur d'auditeurs
│
├── tests/ ............... un test_<module>.py par module, pytest
│   └── fakes.py ......... doubles versionnés — FakeSource, track()
│
├── docs/
│   ├── navidrome.md ..... relevé de l'API Subsonic telle que Navidrome l'implémente
│   ├── franceinfo.md .... relevé du flash d'information — source non confirmée
│   ├── podcast.md ....... relevé des flux de podcast des émissions
│   ├── liquidsoap.md .... relevé de Liquidsoap 2.3.3, et ce qui a décidé la migration
│   ├── ffmpeg.md ........ relevé historique — vaut pour ce que Liquidsoap fait en dessous
│   └── flux-icy.md ...... relevé de ce qu'attendent les lecteurs de webradio
│
└── .claude/
    ├── settings.json .... permissions partagées, versionnées
    └── commands/ ........ goal · task · status · verify
```

**Les trois zones existent et sont peuplées.** Le noyau ne dépend de rien — ni
réseau, ni fichier, ni processus — et se teste sans infrastructure. Chaque
adaptateur confine une dépendance (§2.1). `app/` contient les cinq charnières
qui traduisent entre noyau et adaptateurs sans que l'un importe l'autre.

**Le flux n'est pas dans `webradio/`** : Liquidsoap le sert, depuis son propre
conteneur, en exécutant `adapters/liquidsoap/radio.liq`. Un test lit ce script
et refuse qu'il décide quoi que ce soit.

**Il n'y a pas d'`adapters/news/`, et il n'y en aura pas.** Le flash France
Info est un extrait du **direct** de franceinfo, diffusé comme une émission
(SPECS.md §4.11, `GOAL-015`) : une URL dans le TOML, rendue par
`/playout/next` comme n'importe quelle entrée, et bornée dans le temps par
Liquidsoap (`input.http`, docs/liquidsoap.md §3). Le podcast des flashs
n'existe plus (`docs/franceinfo.md` §1.bis).

**Les identifiants sont en anglais, la prose en français** — modules, classes
et fonctions d'un côté, docstrings, commentaires, journaux et documents de
l'autre.

### 9.1 Écarts assumés

Ce que le projet fait sciemment autrement que ce qu'on attendrait, et pourquoi.
Un écart écrit ici est visible ; un écart tu est une dette.

### L'abstraction des sources est anticipée

**Ce que la règle dit** : *une abstraction arrive avec son deuxième cas d'usage,
pas avant* (AGENTS.md §2).

**Ce que le projet fait** : le mécanisme de sources est complet — `Protocol`,
déclaration au TOML, plusieurs sources activables — alors qu'**une seule est
écrite**, Navidrome.

**Pourquoi** : décision de l'auteur, prise à l'initialisation (SPECS.md §7 n°2).
L'intention est de pouvoir brancher une autre source sans reprendre le cœur.

**Ce que cela coûte, et qu'il faut surveiller** : un mécanisme construit sans son
deuxième cas d'usage est construit contre des suppositions. Trois d'entre elles
ne sont **pas** spécifiées, et la décision ouverte SPECS.md §7 n°12 les recense :
comment le tirage combine plusieurs sources, si la non-répétition s'applique par
source ou globalement, ce qu'on fait d'une source injoignable parmi plusieurs.

**La conduite à tenir jusqu'à la deuxième source** : ne pas répondre à ces
questions en implémentant. Le registre ne contient qu'une entrée ; aucun code ne
doit supposer qu'il en contient plusieurs. La première réponse devinée serait une
seconde anticipation, celle-là non consignée — et c'est ainsi que les écarts
assumés deviennent des dettes tacites.
