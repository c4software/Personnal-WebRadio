# SPECS.md — Spécification fonctionnelle

La source de vérité **fonctionnelle** : ce que la radio doit faire, du point de
vue de celui qui l'écoute. Le **comment** est dans
[ARCHITECTURE.md](./ARCHITECTURE.md), l'**ordre** dans [TASKS.md](./TASKS.md).

Un comportement audible qui n'est pas décrit ici n'existe pas : il est soit à
écrire, soit à supprimer.

---

## 1. Intention

**local-webradio** est une station de radio personnelle. Elle diffuse un **flux
HTTP audio unique**, alimenté par un tirage dans une bibliothèque
[Navidrome](https://www.navidrome.org/), ponctué de jingles horaires,
d'interruptions d'information et d'**émissions** programmées.

Elle n'existe **que lorsqu'on l'écoute** : rien ne tourne tant que personne n'est
branché ; la chaîne démarre à la première connexion et s'arrête à la dernière.

L'expérience recherchée :

```
un auditeur se branche
        ↓
la chaîne démarre — Navidrome est interrogé, un morceau est tiré
        ↓
la musique joue en continu, sans blanc entre les morceaux
        ↓
à l'heure pile : un jingle
à certaines heures : un flash France Info
à l'heure dite : une émission remplace la programmation
selon l'heure : un genre plutôt qu'un autre
        ↓
l'auditeur peut dire « stop » (passer) ou « encore »
(rester sur cet artiste, ou à défaut sur ce genre)
        ↓
le dernier auditeur se débranche → la chaîne s'arrête
```

Ce n'est pas un lecteur de musique : on ne choisit pas ce qu'on écoute, on se
branche et **ça joue déjà**. Un auditeur qui arrive tombe au milieu du morceau en
cours ; deux auditeurs entendent la même chose au même instant.

## 2. Hors périmètre

Ce que ce projet ne fera **pas**. Cette section a autant de valeur que la
précédente : c'est elle qui empêche les Goals de déborder.

| Exclu | Pourquoi |
|---|---|
| **Plusieurs flux ou qualités** | Un seul flux, un seul débit, un seul format. C'est ce qui garde le cœur — une file partagée vers N auditeurs — aussi simple qu'il peut l'être. |
| **Gérer la bibliothèque** | Le projet **lit** Navidrome. Il ne classe pas, ne renomme pas, ne modifie aucune étiquette, n'écrit jamais rien côté bibliothèque. Navidrome reste la seule autorité sur les fichiers. |
| **Enregistrer, rejouer, podcaster** | Pas d'archivage du flux, pas de retour en arrière, pas de podcast des flashs. Une radio est un présent continu : ce qui est passé est perdu, et c'est assumé. |

L'**interface web**, laissée indécise à l'initialisation, est désormais **dans le
périmètre** (§4.8). Elle ne rouvre aucune des trois exclusions ci-dessus : elle
montre ce qui passe et porte deux boutons, elle ne gère ni la bibliothèque, ni la
configuration.

## 3. Qui s'en sert

Un auditeur — l'auteur — sur son **réseau local**, jamais exposé sur Internet.

Conséquences, et elles sont larges :

- **Pas d'authentification** sur le flux ni sur le pilotage. Quiconque est sur le
  réseau peut écouter et commander.
- **Pas de gestion de charge**, pas de limite de connexions. La diffusion doit
  néanmoins supporter proprement plusieurs lecteurs simultanés — un téléphone,
  un navigateur et une enceinte peuvent coexister.
- **Les seuls secrets** sont les identifiants Navidrome. Ils vivent dans le TOML
  local, jamais versionné, et n'apparaissent dans aucun journal (AGENTS.md §2).
- **L'interface web n'est pas protégée non plus** : quiconque est sur le réseau
  peut voir ce qui passe et voter. Elle est faite pour un téléphone posé à côté
  de l'enceinte, utilisable à une main — son ergonomie compte davantage que sa
  conformité formelle d'accessibilité.

---

## 4. Parcours

### 4.1 Se brancher

L'auditeur ouvre l'URL du flux dans un lecteur (VLC, un navigateur, une enceinte
connectée).

- Si **personne n'écoutait**, la chaîne démarre : Navidrome est interrogé, un
  premier morceau est tiré selon la grille de l'heure, l'encodage commence.
  Un délai d'amorçage est acceptable ; il doit rester **court et silencieux**,
  jamais un blanc de plusieurs secondes suivi d'un démarrage brutal.
- Si **quelqu'un écoutait déjà**, le nouvel auditeur rejoint le flux **en
  cours** : il tombe au milieu du morceau, exactement comme sur une vraie radio.

**Quand cela se passe mal** :

| Situation | Comportement attendu |
|---|---|
| Navidrome injoignable | La chaîne ne démarre pas silencieusement. L'erreur est journalisée, et l'auditeur reçoit une réponse HTTP explicite plutôt qu'un flux vide. |
| Navidrome joignable, bibliothèque vide | Même traitement : une radio sans musique est une erreur, pas un silence. |
| ffmpeg absent ou en échec | Erreur au démarrage, journalisée. Ne jamais servir un flux qui ne contient rien. |

### 4.2 Écouter

La musique joue **en continu**. Entre deux morceaux, **pas de blanc** : la
jonction est soit enchaînée, soit fondue — le choix relève de
[ARCHITECTURE.md](./ARCHITECTURE.md), la contrainte audible est ici.

La sélection est un **tirage** dans la bibliothèque, contraint par :

- **la grille horaire** (§4.4) : à certaines heures, un genre plutôt qu'un autre ;
- **une règle de non-répétition** : un artiste ne peut pas revenir avant que
  **N autres artistes** soient passés. `N` est configurable (§6), et vaut **5**
  par défaut. La règle compte des *artistes distincts*, pas des morceaux : trois
  titres d'affilée du même artiste ne comptent que pour un.

**Quand la règle bloque le tirage.** Sur une petite bibliothèque, ou dans une
plage thématique étroite, il peut ne pas rester d'artiste autorisé. La radio ne
se tait pas pour autant : la fenêtre **se rétrécit d'un cran à la fois** jusqu'à
ce qu'un tirage soit possible, et le rétrécissement est journalisé. Une
bibliothèque de trois artistes joue donc en alternant trois artistes, elle ne
s'arrête pas.

### 4.3 Les jingles horaires

À l'heure pile, un jingle — un fichier MP3 **local**, fourni par l'auteur — est
diffusé.

**Le nom du fichier est la programmation.** Les jingles s'appellent `00h.mp3`,
`01h.mp3`, … `23h.mp3`, dans un dossier déclaré au TOML. Le jingle de 14 h est
`14h.mp3`, et il n'existe aucune autre table de correspondance à tenir à jour :
on ajoute un jingle en déposant un fichier, on le retire en le supprimant.

- **Un jingle absent n'est pas une erreur.** Le dossier peut n'en contenir que
  trois ; les vingt-et-une autres heures passent sans jingle, **sans rien
  signaler** — ni journal, ni avertissement. C'est le mode d'emploi normal, pas
  une dégradation.
- Un fichier **présent mais illisible** est, lui, un incident : la radio continue
  et le journalise. La distinction compte — absent est nominal, corrompu ne l'est
  pas.
- Le jingle **ne coupe pas** un morceau en cours : il s'insère à la jonction
  suivante. Un jingle à cheval sur un refrain est un défaut.
- **Un jingle n'est jamais abandonné pour cause de retard**, quel qu'il soit.
  `14h.mp3` peut donc s'entendre à 14 h 25 si le morceau en cours est long. C'est
  assumé : un jingle est de l'habillage, personne ne règle sa montre dessus, et
  renoncer aurait demandé un seuil, un réglage et une famille de cas limites pour
  un gain nul.
  → **Une seule exception, et elle n'a rien à voir avec le retard** : les jingles
  dus **pendant une émission** sont abandonnés, parce qu'une émission remplace la
  programmation, habillage compris (§4.11).
- **Si plusieurs jingles sont dus** à la même jonction — un morceau très long a
  enjambé deux heures — ils sont **tous diffusés, dans l'ordre chronologique**.
  Le jingle de vote `encore.mp3` (§4.6) passe toujours **en dernier**, parce
  qu'il annonce le morceau qui suit immédiatement.
- Pendant un jingle, `stop` et `encore` ne s'appliquent pas (§4.6).

### 4.4 Les moments thématiques

Le tirage est **aléatoire par défaut**. Sur des plages horaires déclarées dans le
TOML, il est restreint à un genre ou à un ensemble de genres.

```
par défaut          → tirage libre dans toute la bibliothèque
08h00–10h00         → un genre déclaré
20h00–23h00         → un autre
```

- Une plage sans musique disponible **ne fait pas taire la radio** : elle se
  replie sur le tirage libre, et le repli est journalisé.
**La grille n'est consultée qu'au moment du tirage**, jamais après. Un morceau
tiré dans la plage « jazz » finit dans la plage « jazz », même s'il déborde de
quatre minutes sur la suivante. La transition entre deux plages tombe donc à la
jonction suivante, pas à l'heure pile — et c'est très bien ainsi : aucune
coupure, aucune durée à connaître d'avance, aucun cas limite à tester.

### 4.5 Les interruptions d'information

À certaines heures déclarées dans le TOML, un **flash France Info** est diffusé.

- Comme le jingle, il **ne coupe pas** un morceau en cours.
- Comme un jingle, **il n'est jamais abandonné pour cause de retard** (§4.3). Un
  flash peut donc s'entendre avec un décalage, borné par la durée du morceau en
  cours.
- **L'indisponibilité du flash est un cas nominal, pas une panne** : si le flux
  France Info ne répond pas, ou renvoie un contenu tronqué, la radio **se replie
  sur la musique** et journalise. Elle ne diffuse jamais un flash incomplet.

Ce que le flash est réellement — son adresse, son format, sa fréquence de mise à
jour — n'est pas connu à ce stade : voir [docs/franceinfo.md](./docs/franceinfo.md).

### 4.6 Piloter le flux

Deux commandes, adressées à la station en cours de diffusion :

| Commande | Effet |
|---|---|
| **`stop`** | Passer le morceau en cours. Le suivant démarre à la jonction, sans blanc. |
| **`encore`** | Rester sur cet artiste : le prochain morceau est du **même artiste**. S'il n'en reste aucun de disponible, du **même genre**. Si le genre non plus n'offre rien, tirage libre, et le repli est journalisé. |

**Elles sont disponibles en permanence**, à une exception près : **pendant un
jingle horaire ou un flash d'information**, elles ne s'appliquent pas. On ne
passe pas un flash, et on ne demande pas « encore » d'un jingle.

Une commande reçue pendant un jingle ou un flash n'est pas perdue en silence :
elle est **refusée explicitement**, et celui qui l'a envoyée l'apprend (§4.8).
Elle n'est ni mise en attente, ni appliquée au morceau suivant en douce — les
deux seraient des surprises.

**Une voix suffit** : le premier vote reçu s'applique, il n'y a ni quorum ni
fenêtre de dépouillement. « Vote » est ici un mot pour « bouton ».

**`encore` s'entend, à la jonction.** Un vote « encore » enregistré fait diffuser
un **jingle** — `encore.mp3`, dans le même dossier que les jingles horaires —
**entre le morceau en cours et le suivant**. Il emprunte exactement le même
chemin d'insertion que les jingles horaires : rien n'est mêlé par-dessus la
musique, rien ne coupe un morceau.

Comme eux, **son absence n'est pas une erreur** : sans `encore.mp3`, le vote
s'applique sans s'annoncer.

> **Ce que cela coûte, et qui est assumé** : l'accusé de réception n'est plus
> immédiat. Entre le vote et le jingle, il s'écoule la fin du morceau en cours —
> pendant laquelle rien ne confirme que le vote est passé. C'est le prix de la
> simplicité : une seule mécanique d'insertion pour tous les jingles.

`encore` s'applique au morceau **suivant**, pas à toute la suite : il n'installe
pas un mode. Il peut en revanche être **enchaîné sans limite** — aucun compteur,
aucun plafond. Ce qui le borne est la bibliothèque elle-même : quand il ne reste
plus de morceau non joué de l'artiste, la radio se replie sur le genre, puis sur
le tirage libre.

**`encore` outrepasse la règle de non-répétition (§4.2).** Les deux se
contrediraient sinon : l'une réclame le même artiste, l'autre le lui interdit.
C'est `encore` qui gagne, puisque c'est une demande explicite de l'auditeur — et
les morceaux servis par `encore` **n'entrent pas** dans la fenêtre de
non-répétition, sans quoi un long enchaînement condamnerait l'artiste pour
longtemps après.

### 4.7 Se débrancher

Quand le **dernier** auditeur se débranche, la chaîne s'arrête : ffmpeg est
arrêté, Navidrome n'est plus interrogé, plus rien ne tourne.

Un auditeur qui se rebranche redémarre une chaîne **neuve**. La radio ne
reprend pas où elle s'était arrêtée — c'est cohérent avec « ce qui est passé est
perdu » (§2).

Une déconnexion brutale (câble arraché, lecteur tué) doit être détectée comme une
déconnexion normale : sans quoi la chaîne tournerait indéfiniment pour un
auditeur qui n'existe plus.

### 4.8 L'interface web, et l'API qui la porte

Une interface web montre ce qui passe et permet d'agir sur la radio.

**Toute action passe par une API.** L'interface n'a aucun chemin privilégié : ses
boutons appellent la même API que n'importe quel autre client. C'est ce qui
permettra d'ajouter plus tard un autre point de commande — un bot, un raccourci
de téléphone — sans rien reprendre du cœur.

> **Aucun autre client n'est écrit pour autant.** L'API existe parce que
> l'interface web s'en sert **aujourd'hui**, pas parce qu'un bot pourrait s'en
> servir demain (AGENTS.md §2 : *une abstraction arrive avec son deuxième cas
> d'usage*). Ce qui est demandé, c'est que la porte existe — pas qu'on
> construise derrière.

L'API doit au minimum :

- dire **ce qui passe** : titre, artiste, et si l'on est dans de la musique, un
  jingle ou un flash ;
- accepter un vote **`stop`** et un vote **`encore`** ;
- **refuser explicitement** un vote pendant un jingle ou un flash (§4.6), en
  disant pourquoi — un refus muet est indistinguable d'une panne ;
- dire **si la chaîne tourne**, donc si quelqu'un écoute.

L'interface web n'est rien de plus que la mise en page de cela : ce qui passe, et
deux boutons. Elle **ne configure pas** la radio — le TOML reste le seul point
d'entrée des réglages (§6) — et ne touche pas à la bibliothèque (§2).

### 4.9 Ce que le flux doit être

Trois exigences, qui tirent en sens contraire et qu'il faut pourtant tenir
ensemble.

**Lisible par n'importe quel lecteur de webradio.** VLC, un navigateur, une
enceinte connectée, une application de radios : aucun ne doit demander de réglage
particulier. Un lecteur qui se branche reçoit un flux qu'il sait lire
immédiatement, sans rien connaître de ce qui l'a précédé.

**Sans coupure.** Le flux ne s'interrompt jamais : ni entre deux morceaux, ni à
l'insertion d'un jingle — horaire ou de vote — ni à celle d'un flash. Pour un
lecteur de webradio, une coupure n'est pas un blanc — c'est une déconnexion, et
il faut se rebrancher.

**Et transcodant le moins possible.** La machine qui diffuse n'a pas de
ressources à gaspiller : ce qui peut être transmis tel quel doit l'être.

Ces trois exigences ne sont pas spontanément compatibles : transmettre un fichier
tel quel interdit de le raccorder au précédent, et un changement de format en
cours de flux est précisément ce qui fait décrocher les lecteurs.

**L'ordre de priorité est tranché** (§7 n°11) :

```
1. sans coupure
2. lisible par tout lecteur
3. économie de la machine
```

Un réencodage permanent vers un format unique est donc la voie par défaut, et
elle est assumée. Chercher moins coûteux est une **optimisation**, jamais un
prétexte à violer cet ordre.

### 4.10 D'où vient la musique

La musique vient de **sources** déclarées dans le TOML. Navidrome en est une ;
d'autres pourront être ajoutées sans rien reprendre du cœur.

Une source sait faire trois choses, et seulement trois : chercher, tirer au
hasard sous contrainte de genre ou d'artiste, et résoudre une piste en un flux
audio lisible. Tout le reste — la grille, le tirage, la non-répétition — est
décidé au-dessus d'elles et ne dépend d'aucune.

**Une seule source est écrite aujourd'hui** : Navidrome. Le mécanisme est
néanmoins complet — plusieurs sources peuvent être déclarées et activées. Ce
choix est un **écart assumé** à la règle « une abstraction arrive avec son
deuxième cas d'usage » : il est consigné comme tel dans ARCHITECTURE.md §9.1,
pour rester visible plutôt que tacite.

Ce qui se passe quand **plusieurs sources sont actives à la fois** — comment le
tirage les combine, si elles se mélangent ou s'alternent, ce qui arrive quand
l'une devient injoignable — n'est pas spécifié : décision ouverte §7 n°12.

### 4.11 Les émissions

Une **émission** est un épisode de podcast diffusé à heure dite. Contrairement à
un jingle ou à un flash, qui ponctuent la musique, une émission **remplace la
programmation** pendant toute sa durée — trente minutes, une heure, davantage.

**Autant d'émissions que voulu, mais jamais deux en même temps.** Le TOML en
déclare autant qu'on veut, chacune avec son flux et sa case horaire — c'est le
sens de « une seule à la fois » : pas *un seul podcast*, mais *pas de
chevauchement*.

Deux émissions qui tomberaient à la même heure sont une **erreur de
configuration** : la radio refuse de démarrer en les nommant toutes les deux
(§6). Elle ne choisit pas à votre place, et elle ne joue pas la première venue.

Le chevauchement se juge sur la **case déclarée**, pas sur la durée réelle des
épisodes : deux émissions déclarées à des heures différentes ne se chevauchent
pas, même si la première déborde sur la seconde. Dans ce cas, **la première
finit** — c'est la même règle que pour les plages thématiques (§4.4), et pour la
même raison : ne rien couper.

#### Ce qu'une émission a en commun avec un jingle

- Elle **ne coupe pas** un morceau en cours : elle commence à la jonction
  suivante. Son démarrage est donc décalé au plus de la durée d'un morceau.
- Elle **n'est jamais abandonnée pour cause de retard** (§7 n°4).
- Un épisode **indisponible ou tronqué** n'est pas une panne : la radio reste sur
  la musique et journalise. Elle ne diffuse jamais une émission incomplète.
- **`stop` et `encore` n'y sont pas applicables** : ils sont refusés
  explicitement, comme pendant un jingle ou un flash (§4.6). On ne passe pas une
  émission.

#### Ce qu'une émission a de différent

- Elle **suspend la grille thématique et la règle de non-répétition** pour sa
  durée : il n'y a rien à tirer, il y a un épisode à diffuser.
- Elle est **longue**, donc elle enjambe presque toujours au moins une heure
  pleine. **Les jingles horaires dus pendant une émission sont abandonnés** —
  ils ne sont ni différés, ni mêlés au son. Une émission remplace la
  programmation, habillage compris, et personne n'attend un jingle au milieu
  d'une émission.
  → C'est la **seule exception** à « rien n'est jamais abandonné » (§4.3). Elle
  est écrite ici pour être vue, et sa raison n'est pas le retard mais la nature
  de l'émission. Il en va de même d'un flash d'information programmé pendant une
  émission.
- Elle vient d'un **flux de podcast**, dont on diffuse **l'épisode le plus
  récent**. Aucun état n'est retenu d'une fois sur l'autre : si le podcast n'a
  rien publié depuis, c'est le même épisode qui repasse — cela s'entend, et cela
  ne casse rien.

#### Quand la radio ne tournait pas

C'est la conséquence la plus contre-intuitive de ce projet, et elle est propre à
lui : **la radio n'existe que lorsqu'on l'écoute** (§1). Une émission programmée à
20 h alors que personne n'est branché **n'a tout simplement pas lieu** — rien ne
tourne pour la diffuser.

**Elle est rattrapée, dans la limite de sa propre durée.** Si l'on se branche
pendant ce qui aurait été sa durée de diffusion, elle démarre — **depuis le
début**. Passé ce délai, elle est perdue.

```
émission de 20h00, épisode d'1h

20h40  branchement  → dans la fenêtre → l'émission démarre, et finit à 21h40
21h10  branchement  → hors fenêtre    → musique, l'émission est perdue
```

Deux conséquences à assumer :

- **la durée n'est connue qu'après avoir lu le flux du podcast.** Décider s'il
  faut rattraper suppose donc d'interroger le flux au branchement, avant de
  savoir si l'on va s'en servir ;
- **une émission rattrapée décale sa propre fin.** Branché à 20 h 55, l'épisode
  d'une heure se termine à 21 h 55. C'est borné par la durée, jamais davantage.

Si le flux est injoignable au moment de décider, il n'y a pas de rattrapage : la
radio démarre sur la musique et journalise. Une émission perdue n'est pas une
panne.

#### La programmation

Déclarée au TOML, une entrée par émission :

```toml
[[emissions]]
nom   = "A la French"
flux  = "https://feeds.acast.com/public/shows/a-la-french"
jours = ["vendredi"]
heure = "20:00"

[[emissions]]
nom   = "LEGEND"
flux  = "https://feeds.acast.com/public/shows/legend-1"
jours = ["mardi", "jeudi"]
heure = "21:00"
```

`jours` vaut `"tous"` ou une liste de jours de la semaine ; `heure` est un moment
de la journée. **Rien de plus.** Ce choix est délibéré : des champs déclaratifs
n'exigent aucun analyseur syntaxique, se testent directement, et couvrent les
deux cas demandés — « tous les jours à 20 h » et « chaque mardi à 12 h ».

**Ce que cette forme ne sait pas exprimer**, et qui devra ouvrir une décision le
jour où le besoin apparaîtra : « le premier lundi du mois », « une semaine sur
deux », « du lundi au vendredi sauf jours fériés ». Une grammaire de récurrence
complète — de type `cron`, ou un langage à écrire — serait un analyseur, ses cas
limites et sa documentation. Elle n'arrivera pas avant son deuxième cas d'usage
(AGENTS.md §2).

---

## 5. Comportement en cas d'erreur

Le principe général : **une radio ne se tait pas**. Toute erreur qui peut être
contournée en continuant la musique l'est, et laisse une trace journalisée.

| Erreur | La radio |
|---|---|
| Un morceau illisible ou tronqué | passe au suivant, journalise |
| Un jingle absent (`14h.mp3` ou `encore.mp3`) | continue **sans rien signaler** — c'est nominal (§4.3, §4.6) |
| Un jingle présent mais illisible | passe outre, journalise |
| Un flash indisponible ou tronqué | continue sur la musique, journalise |
| Un épisode d'émission indisponible ou tronqué | continue sur la musique, journalise (§4.11) |
| Le flux de podcast injoignable au moment de décider d'un rattrapage | pas de rattrapage, démarre sur la musique, journalise |
| Deux émissions déclarées à la même heure | **refuse de démarrer**, en les nommant (§6) |
| Une plage thématique sans musique | se replie sur le tirage libre, journalise |
| La non-répétition ne laisse aucun artiste | rétrécit la fenêtre d'un cran, journalise (§4.2) |
| `encore` sans autre morceau de l'artiste | replie sur le genre, puis sur le tirage libre |
| Navidrome injoignable **au démarrage** | refuse de démarrer, erreur HTTP explicite (§4.1) |
| Navidrome injoignable **en cours** | continue avec ce qui est en file, réessaie en arrière-plan (§5.1) |
| La file s'épuise, Navidrome toujours injoignable | **coupe proprement** plutôt que de servir du silence (§5.1) |
| ffmpeg qui meurt en cours | relance la chaîne **une fois** ; si elle retombe, coupe proprement (§5.1) |

La distinction est nette : **au démarrage**, une erreur est fatale et se dit ;
**en cours de diffusion**, elle se contourne et se journalise.

### 5.1 Jusqu'où « une radio ne se tait pas »

Le principe a une limite, et elle est nette : **la radio tient, puis elle coupe
en le disant.** Elle ne boucle jamais sur ce qu'elle a déjà joué pour donner le
change.

| Panne | Ce que fait la radio |
|---|---|
| Navidrome injoignable | continue avec ce qui est en file, réessaie en arrière-plan |
| … et la file s'épuise sans retour | **coupe**, en journalisant pourquoi |
| ffmpeg meurt | relance la chaîne **une fois** |
| … et elle retombe | **coupe**, en journalisant pourquoi |

Une coupure n'est pas un échec du principe, c'en est l'application : une radio
qui boucle sur trois morceaux en répétant qu'elle va bien rend la panne
invisible, et une panne invisible n'est jamais réparée. L'auditeur qui se
rebranche redémarre une chaîne neuve (§4.7) — le mécanisme existe déjà.

## 6. Configuration

Deux fichiers, et la frontière entre eux est nette : **les secrets d'un côté, tout
le reste de l'autre.** Aucune URL, aucun chemin, aucun port, aucune durée n'est
écrite dans le code (AGENTS.md §2).

### 6.1 Les secrets : `.env`

Un fichier `.env`, **jamais versionné**, qui ne porte **que** des secrets :
identifiants Navidrome aujourd'hui, ce qui s'y ajoutera demain.

Un `.env.exemple` **est** versionné : il ne contient que des noms de variables et
leur rôle, jamais une valeur.

> **Pourquoi les séparer plutôt que tout mettre dans le TOML.** Un fichier de
> configuration se relit, se compare, se colle dans un rapport et se montre à
> quelqu'un pour demander de l'aide. Un fichier qui contient un mot de passe ne
> peut rien de tout cela — et c'est ainsi qu'un secret finit par voyager.
> Les séparer rend le TOML **partageable sans réfléchir**, ce qui est la seule
> protection qui tienne dans la durée.

### 6.2 Le reste : le TOML

Un unique fichier TOML, non versionné lui aussi (il décrit une installation),
pour tout ce qui n'est pas secret :

Ce que le TOML doit décrire, au minimum :

- **Le flux** : adresse d'écoute, port, format et débit ;
- **Les jingles** : le dossier seul — les noms sont fixes et ne se configurent
  pas : `00h.mp3` … `23h.mp3` pour les heures (§4.3), `encore.mp3` pour le vote
  (§4.6) ;

- **Le web** : adresse d'écoute et port de l'interface et de l'API ;
- **Les informations** : à quelles heures un flash est diffusé ;
- **Les moments thématiques** : plages horaires et genres associés ;
- **Le tirage** : `non_repetition_artistes`, le nombre d'artistes distincts qui
  doivent passer avant qu'un artiste puisse revenir (§4.2, défaut 5) ;
- **Les sources** : une section par source, avec son type et ses paramètres
  (§4.10) ;
- **Les émissions** : une entrée `[[emissions]]` par émission — nom, flux de
  podcast, jours et heure (§4.11). Il n'y a pas de limite au nombre
  d'émissions ;
- **Les seuils** : durée de fondu. **Aucun seuil de péremption** : ni les
  jingles ni les flashs ne sont abandonnés pour cause de retard (§4.3).

Le schéma exact se construit avec les Goals. Toute clé ajoutée est documentée
ici dans le même incrément (AGENTS.md §6).

**Un secret dans le TOML est une erreur de configuration**, pas une commodité :
si une clé d'identifiant y apparaît, le démarrage échoue en disant d'où elle
aurait dû venir. Sans ce refus, la séparation ne tiendrait pas une semaine.

Une configuration invalide **empêche le démarrage** et dit précisément quelle
clé pose problème. Une radio qui démarre en ignorant la moitié de sa
configuration est pire qu'une radio qui refuse de démarrer.

---

## 7. Ce qui reste à trancher

Les décisions ouvertes, **numérotées et stables**. Une décision prise migre vers
« Tranché » avec sa raison : c'est ce qui évite de la rejouer six mois plus tard.

### Tranché

**n°1 — Une interface web ? Oui.** Tranchée le 2026-08-30. Une interface web
existe (§4.8), servie par **Flask**, ses gabarits en **Jinja2**. Elle montre ce
qui passe et porte les deux boutons de vote. Elle ne configure rien : le TOML
reste le seul point d'entrée des réglages, et la bibliothèque reste hors
périmètre.
> *Raison* : le pilotage devait bien avoir une forme, et une page ouverte sur un
> téléphone posé à côté de l'enceinte est la plus directe. Le choix de Flask et
> Jinja2 est celui de l'auteur.

**n°10 — « Au vote » : une voix suffit.** Tranchée le 2026-08-30. Le premier vote
reçu s'applique : ni quorum, ni fenêtre de dépouillement, ni comptage des
auditeurs. **Et l'accusé de réception n'est pas une note mêlée à la musique**,
mais un jingle `encore.mp3` inséré à la jonction, par le même chemin que les
jingles horaires (§4.6).
> *Raison* : §3 ne prévoit qu'un auditeur, un quorum n'aurait rien à compter. Et
> une seule mécanique d'insertion pour tous les jingles vaut mieux que deux — le
> prix, un accusé de réception différé jusqu'à la fin du morceau en cours, est
> assumé.

**n°2 — La modularité des sources ? Abstraction complète.** Tranchée le
2026-08-30. Le mécanisme est complet dès maintenant : sources déclarées au TOML,
plusieurs activables (§4.10). Une seule est écrite — Navidrome.
> *Raison* : choix de l'auteur, contre l'interdit d'anticipation d'AGENTS.md §2.
> **C'est un écart, pas une exception tacite** : il est consigné dans
> ARCHITECTURE.md §9.1 pour rester visible. Il ouvre la décision n°12.

**n°3 — La non-répétition ? N artistes distincts.** Tranchée le 2026-08-30. Un
artiste ne revient pas avant que `non_repetition_artistes` autres artistes soient
passés — 5 par défaut, configurable. La fenêtre **se rétrécit** plutôt que de
bloquer le tirage (§4.2).
> *Raison* : indépendant de la durée des morceaux, donc prévisible et trivial à
> tester. Une fenêtre en minutes aurait fait varier le nombre de titres du simple
> au triple.

**n°4 — La péremption ? Aucune.** Tranchée le 2026-08-30. Ni les jingles ni les
flashs ne sont abandonnés **pour cause de retard**. `14h.mp3` peut s'entendre à
14 h 25 (§4.3). **Une exception a été ouverte depuis par la n°15** : ce qui est dû
pendant une émission est abandonné — pour une raison qui n'est pas le retard.
> *Raison* : un jingle est de l'habillage, personne ne règle sa montre dessus.
> Renoncer aurait coûté un seuil, un réglage et une famille de cas limites pour
> un gain nul. **Supprime aussi tout seuil de péremption du TOML.**

**n°7 — L'épuisement de `encore` ? Aucun compteur.** Tranchée le 2026-08-30.
`encore` s'enchaîne sans limite ; ce qui le borne est la bibliothèque, quand
l'artiste n'a plus de morceau non joué. Il **outrepasse** la règle n°3, et les
morceaux qu'il sert n'entrent pas dans la fenêtre de non-répétition (§4.6).
> *Raison* : la borne vient des données, pas d'un réglage. Et sans cette
> priorité, `encore` et la non-répétition se contrediraient frontalement.

**n°5 — Un morceau qui chevauche une fin de plage ? Il finit.** Tranchée le
2026-08-30. La grille n'est consultée **qu'au moment du tirage** : un morceau
tiré dans une plage y termine, quitte à déborder (§4.4).
> *Raison* : c'est la seule option qui n'ajoute **aucune** règle — ni durées à
> connaître, ni coupure, ni cas d'échec supplémentaire. La transition tombe à la
> jonction suivante plutôt qu'à l'heure pile, et cela ne s'entend pas comme un
> défaut.

**n°8 — Les pannes en cours ? Tenir, puis couper en le disant.** Tranchée le
2026-08-30. Navidrome injoignable : continuer sur la file, réessayer en
arrière-plan, couper si la file s'épuise. ffmpeg mort : relancer une fois, couper
si cela retombe (§5.1).
> *Raison* : couper tout de suite rendrait la radio fragile à une micro-coupure ;
> boucler indéfiniment rendrait la panne **invisible**, ce qui contredit
> frontalement « les erreurs se voient » (AGENTS.md §2). Tenir puis couper garde
> les deux qualités.

**n°11 — L'arbitrage du flux ? Ne jamais couper prime.** Tranchée le 2026-08-30.
L'ordre de priorité est fixé, et il ne dépend d'aucun relevé :

```
1. sans coupure
2. lisible par tout lecteur
3. économie de la machine
```

Un réencodage permanent vers un format unique est donc **assumé** s'il le faut.
> *Raison* : une radio économe qui fait décrocher les lecteurs ne remplit pas sa
> fonction ; une radio qui encode en permanence la remplit, mal.
>
> **Ce qui reste au relevé** n'est plus une décision mais une **optimisation** :
> `GOAL-002` dira si un chemin moins coûteux existe *sans violer cet ordre*
> — transmission telle quelle quand le format correspond, format homogène servi
> par Navidrome. S'il n'en existe pas, on réencode, et `GOAL-004` n'attend
> personne.

**n°13 — Une émission manquée ? Rattrapée, dans la limite de sa durée.**
Tranchée le 2026-08-30. Se brancher pendant ce qui aurait été la durée de
l'émission la fait démarrer, depuis le début ; au-delà, elle est perdue (§4.11).
> *Raison* : ne rien faire aurait donné l'impression que la programmation ne
> marche pas ; une fenêtre déclarée aurait ajouté une clé. La durée de l'épisode
> est une borne naturelle, qui ne se règle pas.
>
> **Ce qu'elle coûte** : la durée n'étant connue qu'après lecture du flux, il
> faut interroger le podcast au branchement **avant** de savoir si l'on
> rattrape. Et une émission rattrapée décale sa propre fin, d'au plus sa durée.

**n°14 — Quel épisode ? Le plus récent.** Tranchée le 2026-08-30. Aucun état n'est
retenu d'une fois sur l'autre. Si le podcast n'a rien publié depuis, le même
épisode repasse (§4.11).
> *Raison* : c'est le comportement d'une émission d'actualité, et surtout le seul
> qui **ne rouvre pas l'absence de persistance**. « Le suivant non encore
> diffusé » aurait imposé le premier état durable du projet
> (ARCHITECTURE.md §5.2) — une décision d'architecture, pour un gain d'usage
> mince.
>
> **Ce qu'elle exige du relevé** : que la date de publication soit toujours
> présente et fiable ([docs/podcast.md](./docs/podcast.md) §1). Si elle ne l'est
> pas, « le plus récent » n'est pas implémentable et la décision devra être
> rejouée.

**n°15 — Les jingles dus pendant une émission ? Abandonnés.** Tranchée le
2026-08-30. Ni différés, ni mêlés au son. Il en va de même d'un flash programmé
pendant une émission (§4.11).
> *Raison* : une émission remplace la programmation, habillage compris. Les
> différer aurait produit un `21h.mp3` diffusé après une émission de trois
> heures ; les mêler aurait **réintroduit le mixage de deux sources en temps
> réel**, précisément le chemin supprimé en remplaçant la note de vote par un
> jingle à la jonction (n°10).
>
> **C'est la seule exception à « rien n'est jamais abandonné » (n°4)**, et sa
> raison n'est pas le retard mais la nature de l'émission. Elle est écrite dans
> §4.3 **et** §4.11, pour qu'aucune des deux lectures ne la manque.

**n°6 — La forme des commandes ? Une API.** Tranchée le 2026-08-30. `stop` et
`encore` sont des appels d'API, et l'interface web n'a aucun chemin privilégié :
elle appelle la même API que tout autre client (§4.8).
> *Raison* : séparer l'effet de sa forme permet de spécifier et de tester `stop`
> et `encore` dans le noyau, et d'ajouter un autre point de commande plus tard
> sans rien reprendre. **Aucun autre client n'est écrit pour autant** — la porte
> existe, on ne construit pas derrière.

### Encore ouvert

**n°9 — L'écoute n'est pas un cas d'arrêt.**
Quatre angles morts sont recensés (AGENTS.md §4.1) et **aucun cas d'arrêt ne les
couvre** : les tâches qui touchent au son seront cochées sur la foi de tests qui
n'entendent rien. C'est un choix d'autonomie maximale, pris à l'initialisation et
assumé. Il est consigné ici pour être visible, et pour pouvoir être révisé à la
première fois où un défaut sonore traversera plusieurs Goals.

**n°12 — Plusieurs sources actives : comment le tirage les combine-t-il ?**
Ouverte par la décision n°2. Le mécanisme permet de déclarer plusieurs sources ;
rien ne dit ce qui se passe alors :

- se **mélangent-elles** en un seul réservoir, ou **s'alternent-elles** ?
- si elles se mélangent, avec quelle pondération — au prorata de leur taille, à
  parts égales, selon un poids déclaré ?
- la règle de non-répétition (§4.2) s'applique-t-elle **par source** ou sur
  l'ensemble ? Le même artiste peut exister dans deux sources.
- qu'advient-il quand **une seule** des sources actives devient injoignable ?
  Continuer avec les autres, ou traiter comme une panne (§7 n°8) ?

Sans réponse, la question ne se pose pas : une seule source est écrite. Elle se
posera **le jour de la deuxième** — c'est-à-dire exactement au moment où
l'abstraction anticipée cesse d'être gratuite.
