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
[Navidrome](https://www.navidrome.org/), ponctué de jingles horaires et
d'interruptions d'information.

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
- **une règle de non-répétition** : un artiste ne revient pas immédiatement.
  La forme exacte de la règle est une décision ouverte (§7 n°3), mais l'exigence
  audible est ferme : un artiste qui réapparaît toutes les deux pistes s'entend
  comme un défaut.

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
- Le décalage entre l'heure pile et la diffusion effective est donc borné par la
  durée du morceau en cours. **Le seuil acceptable est une décision ouverte**
  (§7 n°4) : au-delà, mieux vaut renoncer au jingle de cette heure-là que de le
  diffuser à et quart.
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
- Le comportement d'un morceau qui chevauche la fin d'une plage — le laisser
  finir, ou couper — est une décision ouverte (§7 n°5).

### 4.5 Les interruptions d'information

À certaines heures déclarées dans le TOML, un **flash France Info** est diffusé.

- Comme le jingle, il **ne coupe pas** un morceau en cours.
- Il est plus long qu'un jingle et porte de l'information datée : un flash
  diffusé trop tard n'a plus de valeur. Le seuil de péremption est la même
  décision ouverte que §4.3 (§7 n°4).
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
pas un mode. Combien de fois il peut être enchaîné, et si l'effet s'épuise, est
une décision ouverte (§7 n°7).

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
cours de flux est précisément ce qui fait décrocher les lecteurs. **C'est la
décision ouverte n°11**, la plus structurante de celles qui restent.

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
| Une plage thématique sans musique | se replie sur le tirage libre, journalise |
| `encore` sans autre morceau de l'artiste | replie sur le genre, puis sur le tirage libre |
| Navidrome injoignable **en cours de diffusion** | comportement à définir — décision ouverte §7 n°8 |
| Navidrome injoignable **au démarrage** | refuse de démarrer, erreur HTTP explicite (§4.1) |
| ffmpeg qui meurt en cours | comportement à définir — décision ouverte §7 n°8 |

La distinction est nette : **au démarrage**, une erreur est fatale et se dit ;
**en cours de diffusion**, elle se contourne et se journalise.

## 6. Configuration

Un unique fichier **TOML**, seul point d'entrée de toutes les valeurs. Aucune URL,
aucun chemin, aucun port, aucune durée n'est écrite dans le code (AGENTS.md §2).

Le fichier local n'est **jamais versionné** — il contient les identifiants
Navidrome. Un exemple commenté l'est, sans secret.

Ce que le TOML doit décrire, au minimum :

- **Navidrome** : adresse, identifiants ;
- **Le flux** : adresse d'écoute, port, format et débit ;
- **Les jingles** : le dossier seul — les noms sont fixes et ne se configurent
  pas : `00h.mp3` … `23h.mp3` pour les heures (§4.3), `encore.mp3` pour le vote
  (§4.6) ;

- **Le web** : adresse d'écoute et port de l'interface et de l'API ;
- **Les informations** : à quelles heures un flash est diffusé ;
- **Les moments thématiques** : plages horaires et genres associés ;
- **Le tirage** : la règle de non-répétition, une fois §7 n°3 tranchée ;
- **Les seuils** : durée de fondu, péremption d'un jingle ou d'un flash.

Le schéma exact se construit avec les Goals. Toute clé ajoutée est documentée
ici dans le même incrément (AGENTS.md §6).

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

**n°6 — La forme des commandes ? Une API.** Tranchée le 2026-08-30. `stop` et
`encore` sont des appels d'API, et l'interface web n'a aucun chemin privilégié :
elle appelle la même API que tout autre client (§4.8).
> *Raison* : séparer l'effet de sa forme permet de spécifier et de tester `stop`
> et `encore` dans le noyau, et d'ajouter un autre point de commande plus tard
> sans rien reprendre. **Aucun autre client n'est écrit pour autant** — la porte
> existe, on ne construit pas derrière.

### Encore ouvert

**n°2 — Jusqu'où pousser la modularité des sources ?**
L'intention initiale demande une abstraction permettant d'ajouter d'autres
sources que Navidrome plus tard. Cela **contredit frontalement** l'interdit
d'AGENTS.md §2 : *une abstraction arrive avec son deuxième cas d'usage*.

Trois issues, à trancher avant le Goal qui écrit le client Navidrome :

- une frontière **nommée mais non abstraite** — le noyau ne parle jamais
  directement à Navidrome, mais il n'existe qu'une implémentation et aucun point
  d'extension ;
- une **abstraction complète** dès maintenant, en acceptant l'écart à la règle et
  en le consignant dans ARCHITECTURE.md §9.1 ;
- **rien du tout**, et on paiera l'extraction le jour de la deuxième source.

La première est la seule qui respecte les deux exigences ; elle n'est pas
retenue pour autant, elle est proposée.

**n°3 — La règle de non-répétition.**
« Un artiste ne revient pas immédiatement » doit devenir une règle exacte :
un nombre de pistes, une durée, une fenêtre glissante. Elle est audible, donc
elle est de la spécification, pas de l'implémentation.

**n°4 — La péremption d'un jingle ou d'un flash.**
Un jingle ne coupe pas un morceau, donc il glisse. Au-delà de quel décalage
vaut-il mieux **renoncer** que diffuser à contretemps ? La réponse peut différer
entre un jingle (habillage) et un flash (information datée).

**n°5 — Un morceau qui chevauche la fin d'une plage thématique.**
Le laisser finir, ou couper à l'heure ? Le laisser finir est plus musical ; il
décale l'entrée dans la plage suivante.

**n°7 — L'épuisement de `encore`.**
Combien de fois d'affilée peut-on demander « encore » avant que la radio reprenne
un tirage libre ? Sans limite, un `encore` répété transforme la radio en album.

**n°8 — Les pannes en cours de diffusion.**
Que fait la radio si Navidrome devient injoignable, ou si ffmpeg meurt, alors que
des auditeurs sont branchés ? Continuer avec ce qui est en mémoire, tenter de
redémarrer, couper proprement ? Le §5 pose le principe — *une radio ne se tait
pas* — mais pas sa limite.

**n°9 — L'écoute n'est pas un cas d'arrêt.**
Quatre angles morts sont recensés (AGENTS.md §4.1) et **aucun cas d'arrêt ne les
couvre** : les tâches qui touchent au son seront cochées sur la foi de tests qui
n'entendent rien. C'est un choix d'autonomie maximale, pris à l'initialisation et
assumé. Il est consigné ici pour être visible, et pour pouvoir être révisé à la
première fois où un défaut sonore traversera plusieurs Goals.

**n°11 — Transcoder le moins possible, sans jamais couper.**
C'est la décision la plus structurante restée ouverte, et elle oppose trois
exigences de §4.9 :

| Voie | Ce qu'on gagne | Ce qu'on paie |
|---|---|---|
| **Tout réencoder** vers un format unique | Un flux parfaitement continu, des fondus et des insertions possibles, un seul format pour tous les lecteurs | La machine encode en permanence dès qu'un auditeur écoute — exactement ce que « transcoder le minimum » cherche à éviter |
| **Transmettre tel quel** quand le format correspond, réencoder sinon | Presque aucun calcul sur une bibliothèque homogène | Un changement de format en cours de flux fait décrocher les lecteurs ; ni fondu ni insertion propre à la jonction |
| **Exiger une bibliothèque homogène** et transmettre tel quel | Le coût minimal, et un flux continu | Une contrainte reportée sur la bibliothèque, que le projet n'a pas le droit de modifier (§2). Un seul fichier au mauvais format casse la radio |

S'ajoute une question de fait : l'insertion d'un jingle, d'un flash ou de la note
d'accusé de réception impose de mêler des fichiers **d'origines différentes**.
Aucune des voies ci-dessus ne l'évite entièrement.

Rien ne se tranche avant le relevé de [docs/ffmpeg.md](./docs/ffmpeg.md) et de
[docs/flux-icy.md](./docs/flux-icy.md), et avant de savoir ce que la bibliothèque
contient réellement ([docs/navidrome.md](./docs/navidrome.md)).
