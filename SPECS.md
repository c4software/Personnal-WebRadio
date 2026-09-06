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
servie en [Subsonic](https://www.subsonic.org/pages/api.jsp) — Navidrome
chez l'auteur —, ponctué de jingles horaires,
d'interruptions d'information et d'**émissions** programmées.

Elle n'existe **que lorsqu'on l'écoute** : rien n'est décodé ni demandé tant que
personne n'est branché ; la musique démarre à la première connexion et s'arrête
à la dernière. Depuis le 2026-08-30 (§7 n°23), un processus de diffusion reste
debout entre deux écoutes — il encode du silence à moins d'un pour cent d'un
cœur — mais il ne tire aucun morceau, n'interroge pas la bibliothèque et ne fait
avancer ni la file ni la non-répétition.

L'expérience recherchée :

```
un auditeur se branche
        ↓
la chaîne démarre — la bibliothèque est interrogée, un morceau est tiré
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
| **Gérer la bibliothèque** | Le projet **lit** la bibliothèque. Il ne classe pas, ne renomme pas, ne modifie aucune étiquette, n'écrit jamais rien côté bibliothèque. Le serveur de musique reste la seule autorité sur les fichiers. |
| **Enregistrer, rejouer, podcaster** | Pas d'archivage du flux, pas de retour en arrière, pas de podcast des flashs. Une radio est un présent continu : ce qui est passé est perdu, et c'est assumé. |

L'**interface web**, laissée indécise à l'initialisation, est désormais **dans le
périmètre** (§4.8). Elle ne rouvre aucune des trois exclusions ci-dessus : elle
montre ce qui passe et porte deux boutons, elle ne gère ni la bibliothèque, ni la
configuration.

## 2.1 Comment elle tourne

La station est livrée en **conteneur Docker**, démarrée par un
`docker-compose.yml` (ARCHITECTURE.md §8.5). C'est ce qui fige la version de
ffmpeg avec le code qui l'a relevée.

Le serveur de musique — Navidrome chez l'auteur — n'en fait pas partie : il
existe déjà et lui appartient.

## 3. Qui s'en sert

Un auditeur — l'auteur — sur son **réseau local**, jamais exposé sur Internet.

Conséquences, et elles sont larges :

- **Pas d'authentification** sur le flux ni sur le pilotage. Quiconque est sur le
  réseau peut écouter et commander.
- **Pas de gestion de charge**, pas de limite de connexions. La diffusion doit
  néanmoins supporter proprement plusieurs lecteurs simultanés — un téléphone,
  un navigateur et une enceinte peuvent coexister.
- **Les seuls secrets** sont les identifiants Subsonic. Ils vivent dans le TOML
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

- Si **personne n'écoutait**, la chaîne démarre : la bibliothèque est interrogée, un
  premier morceau est tiré selon la grille de l'heure, l'encodage commence.
  Un délai d'amorçage est acceptable ; il doit rester **court et silencieux**,
  jamais un blanc de plusieurs secondes suivi d'un démarrage brutal. La **prise
  d'antenne se fond** : le volume monte de zéro au niveau nominal en deux
  secondes, l'auditeur ne prend jamais le son en pleine face — même quand
  l'antenne reprend au milieu d'un morceau resté en attente.
- Si **quelqu'un écoutait déjà**, le nouvel auditeur rejoint le flux **en
  cours** : il tombe au milieu du morceau, exactement comme sur une vraie radio,
  au volume du flux — le fondu ne vaut que pour la prise d'antenne, le flux
  étant encodé une seule fois pour tous.

**Quand cela se passe mal** :

| Situation | Comportement attendu |
|---|---|
| Source Subsonic injoignable | La chaîne ne démarre pas silencieusement. L'erreur est journalisée, et l'auditeur reçoit une réponse HTTP explicite plutôt qu'un flux vide. |
| Source joignable, bibliothèque vide | Même traitement : une radio sans musique est une erreur, pas un silence. |
| Liquidsoap ne joint pas l'API | Il s'arrête en le journalisant, et le superviseur le relance ; il ne sert jamais un flux qui ne contient rien (§7 n°23). |

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

Un **plafond de durée** borne la lecture, pas le choix (§7 n°32) : au-delà de
`draw.max_track_minutes` (20 min par défaut, la limite exacte passe, `0` =
sans limite), une piste se choisit comme les autres mais sa lecture **se coupe
au plafond**, fondue vers ce qui suit comme n'importe quelle jonction. Les
émissions, elles, ont leur propre durée (§4.11) et ne sont pas concernées.

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
- **Un jingle en retard passe quand même — dans la limite de sa péremption**
  (`jingles.expiry_seconds`, quinze minutes par défaut, `0` = jamais périmé).
  `14h.mp3` peut donc s'entendre à 14 h 10 si le morceau en cours est long :
  c'est un cas nominal, personne ne règle sa montre sur l'habillage. Mais à
  plus d'un quart d'heure de son heure pleine, il est **abandonné** : un
  `19h.mp3` entendu à 22 h 28, au retour d'une longue pause sans auditeur,
  sonne comme une horloge cassée (constaté le 2026-08-31, §7 n°29 — qui amende
  la n°4). La péremption s'évalue heure par heure : de deux heures enjambées,
  seule la plus récente peut encore passer. Le jingle d'« encore » (§4.6), lui,
  ne périme jamais : il répond à un vote, pas à l'horloge.
  → **L'autre exception n'a rien à voir avec le retard** : les jingles dus
  **pendant une émission** sont abandonnés, parce qu'une émission remplace la
  programmation, habillage compris (§4.11).
- **Si plusieurs jingles sont dus** à la même jonction — un morceau très long a
  enjambé deux heures — ils sont **tous diffusés, dans l'ordre chronologique**.
  Le jingle de vote `encore.mp3` (§4.6) passe toujours **en dernier**, parce
  qu'il annonce le morceau qui suit immédiatement.
- Pendant un jingle, `stop` et `encore` ne s'appliquent pas (§4.6).
- **La jonction suivante est bien la jonction qui suit l'heure** — pas celle
  d'après. Le diffuseur décide l'entrée de chaque jonction à la précédente
  (un morceau d'avance, §7 n°23) ; une heure pleine tombée entre les deux
  n'était donc vue qu'un morceau plus tard : `16h.mp3` à 16 h 07 pour un
  morceau fini à 16 h 03, constaté le 2026-09-02. **Depuis ce jour**, l'heure
  pleine remet l'avance en question (§7 n°33) : l'entrée déjà demandée se
  replace derrière le jingle, dans les quinze secondes qui suivent l'heure.
  Le résidu assumé : une jonction tombée dans ces quinze secondes-là garde le
  retard d'un morceau.

### 4.4 Les moments thématiques

Le tirage est **aléatoire par défaut**. Sur des plages horaires déclarées dans le
TOML, il est restreint à un genre ou à un ensemble de genres.

```
par défaut          → tirage libre dans toute la bibliothèque
08h00–10h00         → un genre déclaré
20h00–23h00         → un autre
21h00–23h00         → « un genre, choisis-le toi-même »
```

**Deux plages qui se recouvrent ne sont pas refusées : la plus courte
l'emporte** (révisé le 2026-09-02, GOAL-068). Dans l'exemple ci-dessus, la
plage de 21 h interrompt celle de 20 h, qui reprend à sa fin — c'est ce qui
permet de déclarer un fond de soirée large et d'y planter un rendez-vous, sans
avoir à découper le fond à la main. À durée égale, la **première déclarée**
tranche : le résultat reste déterministe. Une émission (§4.11) et un programme
(§4.13) passent avant, quelle que soit leur durée. La règle vaut à
l'identique entre deux programmes.

Une plage peut aussi **déléguer le choix** : plutôt que d'énumérer ses valeurs,
elle déclare la *sorte* de thème voulue — un genre, ou un artiste. La radio tire
alors dans toute la bibliothèque **au début de l'occurrence**, et s'y tient
jusqu'à la fin de la plage ; l'occurrence suivante retire (§7 n°28).

- Le tirage est **figé sur l'occurrence** : c'est ce qui en fait une soirée
  d'artiste, et non un tirage libre déguisé. Rien n'est persisté — une radio qui
  redémarre au milieu d'une plage retire.
- L'antenne nomme le thème sorti et **dit qu'il a été tiré** — « Moment · Air
  (au hasard) ». Le planning, lui, ne peut annoncer d'avance que la sorte : « Au
  hasard · un artiste ».
- **Le moment courant se nomme toujours** (GOAL-066), puisque l'interface
  l'affiche à côté du bouton « Autre thème » (§4.8) : une plage à mode seul
  (§7 n°31) n'a ni genre ni artiste à citer et s'annonce « Moment · tirage
  libre (passionné d'époque) » — jusqu'au 2026-09-02 elle n'affichait qu'un
  « Moment · » orphelin. Toute plage à mode suffixe son enchaînement, avec les
  mêmes mots que le planning (§4.8).
- Un tirage qui n'aboutit pas — source injoignable, bibliothèque vide — laisse
  la plage en tirage libre et sera **retenté à la jonction suivante** ; il est
  journalisé une fois par occurrence.
- Une plage sans musique disponible **ne fait pas taire la radio** : elle se
  replie sur le tirage libre, et le repli est journalisé.
- **Le thème se retire** (§7 n°28 amendée, GOAL-057). Une heure de Ragga qui
  ne plaît pas ne se subit pas jusqu'à l'heure suivante : un bouton — donc une
  route de l'API (§4.8) — fait retirer un **autre** thème pour le reste de
  l'occurrence ; l'ancien est écarté du tirage, sauf si la bibliothèque n'en
  offre pas d'autre, et c'est alors dit. Le morceau en cours finit (§7 n°5) ;
  dès la jonction suivante, la plage joue le nouveau thème — ce qui avait été
  tiré d'avance sous l'ancien est rassis et ne passe pas (§7 n°33). Le
  générique de la plage ne repasse pas : il annonce la plage, pas le thème.
  **Vaut aussi pour une suite tirée au sort** (GOAL-059) : sur une plage
  `era_fan` ou `artist_fan`, retirer rompt la suite en cours et en ouvre une
  autre, d'une autre décennie ou d'un autre artiste — sauf si la bibliothèque
  n'offre rien d'autre, et c'est dit ; l'avance tirée sous l'ancienne suite
  est jetée sans être replacée. Une double dose ne se retire pas : son artiste
  n'est pas une ancre tirée pour durer. Hors de ces plages, retirer est
  **refusé en le disant**.

#### Les modes d'enchaînement

Une plage peut enfin demander que ses tirages s'**enchaînent** (`mode`, §7
n°31) — combinable avec son thème, ou seul (un tirage libre enchaîné) :

| Mode | Ce qui s'entend |
|---|---|
| `double_dose` | Chaque artiste tiré passe **deux titres à la suite** — jamais deux fois le même titre |
| `era_fan` | **2 à 6 titres d'une même décennie**, tirés dans le thème de la plage |
| `artist_fan` | **3 à 6 titres du même artiste**, à la suite |

- Le premier morceau tiré pose l'**ancre** — son artiste, ou sa décennie — et
  la longueur de la suite est tirée au hasard injecté : une soirée se rejoue.
- Une suite d'artiste **outrepasse la fenêtre de non-répétition**, comme
  l'encore (§4.6) — répéter est le but — et la règle reprend dès la fin de la
  suite. Une suite d'époque, elle, varie les artistes : la fenêtre s'applique.
- Le **même titre ne repasse jamais** dans une même suite. Une suite qui
  s'épuise — plus rien de cet artiste, plus rien de cette décennie dans la
  plage — se **rompt en le journalisant**, et le morceau tiré à la place
  devient l'ancre de la suite suivante.
- Une piste **sans année** ne pose pas d'ancre d'époque : le tirage reste
  simple (6,7 % de la bibliothèque, docs/subsonic.md §4.1).
- Une plage peut **borner les décennies** où elle tire (`eras`, §6). Le filtre
  s'applique avant l'ancre : une décennie non déclarée ne peut donc pas ouvrir
  de vague. Les pistes sans année en sont écartées, faute d'appartenir à une
  décennie. Sans rien dans les décennies déclarées, la plage les **ignore en le
  journalisant** plutôt que de se taire (§4.4).
- La suite est **remise à zéro** au changement d'occurrence de plage, et ne
  vaut ni pour les programmes (§4.13) ni pour le tirage libre hors plage.

**La grille n'est consultée qu'au moment du tirage**, jamais après. Un morceau
tiré dans la plage « jazz » finit dans la plage « jazz », même s'il déborde de
quatre minutes sur la suivante. La transition entre deux plages tombe donc à la
jonction suivante, pas à l'heure pile — et c'est très bien ainsi : aucune
coupure, aucune durée à connaître d'avance, aucun cas limite à tester.

**Mais la plage d'avant ne déborde pas derrière son générique.** Ce qui a été
tiré **d'avance** — pas ce qui joue — sous une plage qui a fini est rassis, et
ne passe pas (§7 n°33) : le générique de la plage suivante est suivi d'un
morceau de cette plage, jamais d'un reliquat de la précédente. Le 2026-09-02 à
16 h 07, « une heure d'un genre tiré au sort » avait été suivie d'un cinquième
Bob Marley du contretemps de 15 h.

### 4.5 Les interruptions d'information

À certaines heures déclarées dans le TOML, un **flash France Info** est diffusé.

- Comme le jingle, il **ne coupe pas** un morceau en cours.
- **Il n'est jamais abandonné pour cause de retard** (§7 n°4) — la péremption
  des jingles horaires (§4.3, n°29) ne le concerne pas. Un flash peut donc
  s'entendre avec un décalage, borné par la durée du morceau en cours.
- **L'indisponibilité du flash est un cas nominal, pas une panne** : si le flux
  France Info ne répond pas, ou renvoie un contenu tronqué, la radio **se replie
  sur la musique** et journalise. Elle ne diffuse jamais un flash incomplet.

**Ce que le flash est réellement, depuis le 2026-08-30 : un extrait du direct
de franceinfo**, diffusé comme une **émission** (§4.11) — le podcast des flashs
n'existe plus ([docs/franceinfo.md](./docs/franceinfo.md) §1.bis). Il n'y a
donc pas de mécanisme « flash » distinct : une émission dont la source est un
direct, déclarée à `HH:00` avec une durée, est un flash. Le mot reste dans ce
document pour ce qu'il désigne à l'antenne.

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

**`encore` vise la chanson que l'auditeur entendait en votant** — pas celle
que le diffuseur avait prise d'avance, ni le jingle qui passe à la jonction.
**Depuis le 2026-09-02** (GOAL-067), cette ancre est retenue avec le vote, et
le morceau forcé est tiré aussitôt : la liste des prochains titres (§4.8) le
montre, et il se retire comme un autre — un autre du même artiste le
remplace. Constaté le jour même : un encore voté sur La Rue Kétanou avait
forcé le genre de THK, le morceau d'avance.

`encore` s'applique au morceau **suivant**, pas à toute la suite : il n'installe
pas un mode. Il peut en revanche être **enchaîné sans limite** — aucun compteur,
aucun plafond. Ce qui le borne est la bibliothèque elle-même : quand il ne reste
plus de morceau non joué de l'artiste, la radio se replie sur le genre, puis sur
le tirage libre.

**« Non joué » vaut « non passé à l'antenne récemment (borne), ni servi par un
encore »** — décision de l'auteur du 2026-09-06. L'encore ne connaissait que ce
qu'il avait servi lui-même : la file passait deux morceaux du même artiste, et
un encore sur le second rendait le premier, qui venait de s'entendre. La mémoire
des titres passés est **bornée** ; au-delà, un vieux titre redevient éligible,
sans quoi quelques mois de diffusion videraient l'artiste et le repli sur le
genre deviendrait la règle.

**`encore` outrepasse la règle de non-répétition (§4.2).** Les deux se
contrediraient sinon : l'une réclame le même artiste, l'autre le lui interdit.
C'est `encore` qui gagne, puisque c'est une demande explicite de l'auditeur — et
les morceaux servis par `encore` **n'entrent pas** dans la fenêtre de
non-répétition, sans quoi un long enchaînement condamnerait l'artiste pour
longtemps après.

### 4.7 Se débrancher

Quand le **dernier** auditeur se débranche, la musique s'arrête : plus rien
n'est décodé, la bibliothèque n'est plus interrogée, la file n'avance plus. Le
diffuseur reste debout et encode du silence (§1, §7 n°23).

Un auditeur qui se rebranche **vite** entend la radio reprendre là où le
diffuseur en était : le reliquat du morceau interrompu, puis le morceau demandé
d'avance. (La première version de ce paragraphe promettait « jamais le milieu
de celui qui passait » ; le relevé l'a démentie — le reliquat passe,
docs/liquidsoap.md §5.bis.)

Mais une avance rassit. Au-delà de `playout.resume_fresh_seconds` de pause
(900 s par défaut, `0` = jamais — §7 n°30), le retour jette tout : l'avance du
diffuseur, le reliquat du morceau interrompu, l'habillage en attente de
jonction, **et le morceau que la file avait déjà tiré** — et la radio repart
sur un **tirage neuf**, comme à un démarrage. (Ce dernier manquait à l'appel
jusqu'au 2026-09-02 : la file sert son avance sans regarder la contrainte, et
un morceau tiré à 19 h serait passé au réveil du lendemain. Et le reliquat
l'était à deux secondes près : le fondu enchaîné du diffuseur les avait déjà
lues, et les servait au premier auditeur — un micro-flash entendu le même
jour à 13 h 20, docs/liquidsoap.md §10.)

**Ce retour est silencieux jusqu'au premier morceau frais.** Jeter le reliquat
ne suffisait pas : le diffuseur ne peut le faire qu'au moment où il enchaîne,
donc une fois le morceau frais prêt, et l'attente peut durer plusieurs
secondes. Pendant ce temps, il servait ce qu'il avait sous la main — la veille.
L'antenne reste donc muette du retour jusqu'à l'entrée du morceau frais, qui
entre en fondu ; ce que l'auditeur perd est une attente, ce qu'il gagne est de
ne plus entendre une chanson qui n'a plus lieu d'être (micro-flash entendu le
2026-09-06 au matin, docs/liquidsoap.md §11). Un direct qui prendrait l'antenne
dans cet intervalle s'entend normalement : il n'a rien de rassis. Mais le
silence l'attend de l'autre côté — quand il rend l'antenne, la radio reste
muette jusqu'à son premier morceau frais, puisque c'est l'entrée de ce
morceau, et elle seule, qui lève le muet.
Seul un « encore » voté avant la pause survit : c'est une demande explicite
(§4.6). En deçà du seuil, rien ne change : la reprise se fait sur l'avance,
telle quelle. C'est cohérent avec « ce qui est passé est perdu » (§2).

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

#### L'antenne poussée, plutôt que redemandée

**Depuis le 2026-09-03** (GOAL-073), `GET /api/events` **pousse** ce que rend
`GET /api/on-air` : un flux `text/event-stream` qui envoie un événement
`antenne` à la connexion, puis à **chaque changement** — et rien d'autre qu'un
commentaire de maintien entre deux. Un changement de chanson se voit dans la
page au moment où il arrive, au lieu d'attendre le prochain sondage.

Le serveur regarde l'antenne à `web.refresh_seconds` (§6) ; c'est ce que
cette clé règle désormais, à la place de l'intervalle auquel la page
redemandait.

`GET /api/on-air` **reste** : l'API doit dire ce qui passe à qui le demande, et
la page n'a aucun chemin privilégié. Le flux s'ajoute à cette surface, il ne la
remplace pas.

Le sens inverse — voter, retirer un titre, retirer un thème — n'a pas de canal
permanent : ce sont des appels REST, comme avant (décision de l'auteur).

**Une coupure ne s'écrit pas.** Réseau perdu, serveur arrêté : la page affichait
« L'API ne répond pas : TypeError: Failed to fetch » jusqu'au prochain succès.
Elle montre désormais un **témoin** discret à côté du nom de la radio, et rien
d'autre — `EventSource` se rebranche de lui-même, et le témoin s'efface quand il
y parvient. Aucune exception n'est plus rendue telle quelle à l'auditeur : une
action qui échoue dit « Le serveur ne répond pas. » et s'efface au bout de
quelques secondes, comme un refus.

**Un onglet en fond ne suit plus l'antenne.** Page repliée, écran verrouillé,
application passée à l'arrière-plan : la page **ferme** son flux — elle n'a rien
à montrer, et le serveur n'a personne à qui pousser. Elle le rouvre au retour,
et le flux lui renvoie l'antenne dès la connexion : elle se remet à l'heure sans
rien redemander. C'est aussi ce qui évite qu'un téléphone laissé sur la page
toute une nuit tienne une connexion pour rien.

#### « À suivre »

L'interface annonce aussi **ce qui vient**. Le diffuseur a toujours un morceau
d'avance (§7 n°23), et c'est lui qu'on annonce — jamais l'habillage : dix
secondes de jingle ne sont pas « à suivre ».

Mais le diffuseur ne garde **qu'une** entrée d'avance. Quand cette unique
entrée est un jingle, il n'y a plus rien à annoncer, et le panneau restait vide
le temps de toute la chanson en cours — une quarantaine de fois par jour.
**Depuis le 2026-09-02**, on regarde alors derrière l'habillage : la file a déjà
tiré le morceau suivant, et c'est lui qu'on annonce. Une émission ou un
« encore » peuvent encore s'intercaler devant — l'annonce reste plus juste que
le silence. Pendant un **programme**, rien n'est annoncé : la musique vient
d'une liste et non de la file (§4.13), et l'avance préparée ne passera pas.

#### Les prochains titres

**Depuis le 2026-09-02** (§7 n°34, GOAL-058), « À suivre » est la tête d'une
**liste** : la radio tire `draw.lookahead` titres d'avance (§6, huit par
défaut), et l'API la rend dans l'ordre de passage (`GET /api/up-next`) — ce
que le diffuseur a déjà demandé, puis l'avance de la file — avec, pour chaque
entrée, sa nature, son titre, son artiste, l'**heure estimée** de son début, et
l'habillage **prévu** entre deux titres : le jingle horaire dont l'heure
tombera avant le suivant, le générique du moment qui changera. L'estimation
part du morceau en cours — son début, sa durée coupée au plafond — et compte
l'habillage pour zéro ; elle est absente quand rien ne permet d'estimer (un
direct, une entrée inconnue). Rien n'y est décidé : la liste dit ce que la
jonction rendrait si les durées tenaient.

**Chaque titre d'avance est tiré sous le moment qu'il trouvera en
commençant** — idée de l'auteur : c'est ce qui fait qu'une liste de trois
titres à 15 h 55 annonce un dernier titre de 15 h, puis deux de 16 h, et non
trois de 15 h dont deux rassis. L'avance datée (n°33) tranche à la jonction si
l'estimation tenait ; un créneau qui a glissé sous une autre plage — un `stop`,
un encore — est retiré avec ce qui le suit, et retiré au sort.

**Depuis le 2026-09-02** (GOAL-068), l'estimation regarde aussi ce qui
**remplacera la file** — les émissions et les programmes, et non plus les
seules plages :

- elle **nomme l'émission qui va couper** : à 19 h 58, elle annonçait un titre
  pour 20 h alors que l'émission de 20 h allait passer. Après un **direct**,
  dont la fin est déclarée, elle **reprend** à l'heure sûre : le flash de
  11 h 57 s'y lit entre le titre de 11 h 54 et celui de 12 h 10. Les **titres**
  s'arrêtent, en revanche, à ce qu'elle ne sait ni nommer ni dater — un podcast
  ou une chaîne YouTube, dont la durée ne se lit qu'une fois le flux ouvert ;
  un programme, qui ne s'annonce pas (voir « À suivre » ci-dessus) — et c'est
  la couture ci-dessous qui prend le relais.
  Elle ne s'arrête **jamais en silence** : le 2026-09-02, l'auteur n'a vu que
  quatre titres au lieu de huit — la liste jugeait rassis ce qui avait été
  tiré pour l'heure d'après un direct, et se coupait sans rien dire
  (GOAL-070) ;
- un créneau qui tomberait pendant un **programme** ou un **direct** est tiré
  pour l'heure de leur **fin** : la file n'y est pas servie, et un titre tiré
  pour cette heure-là aurait été jeté à la jonction — laissant la file vide au
  moment même de reprendre.

**Depuis le 2026-09-06** (§7 n°34 amendée, GOAL-078), la liste **coud** derrière
son dernier titre les périodes de la **grille effective**, jusqu'à l'horizon de
`web.upcoming_horizon_minutes` (§6, trois heures par défaut, `0` pour ne rien
coudre). La période **en cours** y
figure la première, sans heure de début — c'est sa fin qui compte, « en cours
→ 21:00 » — puis les suivantes avec la leur. La liste ne s'arrête donc plus net
après une émission sans fin déclarée : elle nomme ce que la grille annonce
derrière, sans heure quand la grille elle-même n'en connaît pas. Une période de
programme s'annonce comme **période**, au même titre qu'une plage ; seule sa
**musique** reste hors de la liste. Les trous de la grille restent des trous
(§4.4), et une émission déjà nommée par la liste ne l'est pas deux fois.
**Rien n'est tiré de plus** : la profondeur de l'avance ne bouge pas, la couture
lit la grille et ne décide rien.

Sur la forme : l'API rend chaque période cousue avec **les mêmes données que le
Planning**, sous la clé `period` de `GET /api/up-next` (`null` sur une ligne de
titre), et la page les met en mots avec **les mêmes fonctions**. Une période se
lit donc sur une ligne à part des titres, sans ✕ — rien ne s'y retire — et une
période en cours se lit « → fin ».

Un titre de la liste **se retire** (`DELETE /api/up-next/<identifiant>`) : il
ne passera pas, un autre est tiré à sa place sous le même moment, et le retrait
est journalisé. Le morceau qu'un encore force (§4.6) y figure après le jingle,
et se retire aussi : un autre du même artiste le remplace. Retirer compte comme passé pour la non-répétition : sur une
petite bibliothèque, le remplacement ne le rendrait pas aussitôt. Un titre qui
a commencé entre-temps n'attend plus : 404, et la page le dit. L'habillage ne
se retire pas. La non-répétition **voit ce qui attend** : un artiste tiré
d'avance ne revient pas dans la même avance, sauf suite d'artiste (§4.4) ou
bibliothèque trop petite — et alors c'est dit.

L'interface ouvre cette liste depuis « À suivre », ou depuis le bouton de
liste du lecteur ; **depuis le 2026-09-02** (GOAL-062) elle se déploie dans
le lecteur lui-même, au lieu d'un tiroir à part : une ligne par entrée,
l'habillage prévu en italique, et un ✕ « Ne passera pas » sur les titres. Ni
réordonner, ni forcer un titre : rien de plus n'a été demandé.

#### Le Planning

**Depuis le 2026-09-02** (GOAL-068), `GET /api/planning` rend la **grille
effective** de la semaine — sept journées, chacune déjà fusionnée — et non plus
les trois listes déclarées au TOML. Jusque-là, la page affichait côte à côte
« Hardisk, 20:00 » et « 20:00–22:00, Rock » : deux créneaux à la même heure,
dont l'un mange l'autre, et rien ne le disait.

Les périodes y sont arbitrées **comme à l'antenne** : une émission passe devant
la plage qu'elle occupe, un direct rogne celle qu'il recouvre, un programme
remplace celle qu'il couvre (§4.13), et entre deux plages c'est la plus courte
qui l'emporte (§4.4). Une plage coupée en son milieu se lit donc en deux
morceaux. Celle qui reprend après une émission **sans durée déclarée** —
podcast, chaîne YouTube — n'annonce que sa fin, « → 22:00 » : son début dépend
de la longueur d'un épisode que personne ne connaît d'avance, et l'inventer
serait mentir.

Une période appartient au jour où elle **commence** : une fin de soirée qui
court jusqu'à 02 h se lit tout entière la veille, et le lendemain n'en montre
pas la queue. La page ne recolle plus rien — elle met en mots ce qu'elle reçoit.

#### « Retirer »

Quand le moment en cours a tiré son thème au sort (§4.4), l'API le dit
(`moment_random`) et accepte de le **retirer** (`POST /api/moment/redraw`) : la
réponse porte le nouveau moment, pour que la page l'affiche sans attendre son
rafraîchissement. Hors d'une plage au hasard, la demande est refusée avec son
motif, exactement comme un vote pendant un jingle. L'interface montre le bouton
seulement quand l'API dit qu'il a un sens — elle ne le devine pas sur le
libellé. **Depuis le 2026-09-02**, le bouton s'appelle « Autre thème » :
« Retirer » se lisait aussi comme le retrait d'un titre de la liste.

Pendant une émission (§4.11) ou un flash (§4.5), l'antenne **n'annonce aucun
moment** : ils remplacent la plage (§4.4), et l'annoncer quand même ferait dire
à la page deux choses contradictoires. Le bouton « Autre thème » n'y a donc pas
de sens, et la demande est refusée avec son motif. La plage reprend son libellé
dès que la musique revient.

#### Écouter depuis la page

**Depuis le 2026-09-02** (GOAL-060), la page porte un lecteur, si le TOML
déclare l'adresse du flux (`web.stream_url`, §6) : un bouton « Écouter »,
qui vaut le geste que les navigateurs exigent avant tout son, et « Couper ».
La page ouverte **n'écoute pas** tant qu'on n'a pas appuyé — elle ne branche
aucun auditeur à l'insu de tous, et la radio continue de ne tourner que si
quelqu'un écoute (§1). Écouter depuis la page, c'est être un auditeur comme
un autre : la prise d'antenne se fond, couper rendort la radio si personne
d'autre n'écoute. Couper **décharge** le flux plutôt que de le mettre en
pause : un direct ne se reprend pas, et une connexion gardée compterait un
auditeur. Quand le navigateur le sait, titre, artiste et moment s'affichent
sur l'écran de verrouillage, et ses commandes de lecture passent par le même
bouton que la page. Ce que fait un téléphone au rebranchement, en
arrière-plan, écran verrouillé, ne se constate qu'en écoutant
(docs/flux-icy.md).

**Depuis le 2026-09-02** (GOAL-062), le lecteur est une **barre fixe en bas
de page**, présente sur tous les onglets : ce qui passe, le témoin d'antenne
(en direct, en veille, prise d'antenne en cours), le bouton de lecture, le
volume sur un écran large, et le bouton qui déploie les prochains titres. La
barre existe même sans flux déclaré — elle dit alors ce qui passe et ouvre la
liste — seul le bouton de lecture dépend de `web.stream_url`. L'onglet
« Antenne » met ce qui passe dans une carte, « Passer » et « Encore » juste
dessous ; sans auditeur, la carte dit que la radio dort et comment la
réveiller. Le style est celui des surfaces de verre : translucides, floutées,
sur un fond en dégradé — sans bibliothèque, ni de composants ni de lecteur.

**Depuis le 2026-09-02** (GOAL-063), la page **s'installe comme une
application** : un manifeste, des icônes pour l'écran d'accueil, un
affichage autonome sans barre d'adresse, et les balises que Safari iOS lit à
la place du manifeste. Rien n'est mis en cache : la page reste ce qu'elle
est, une vue sur l'API, et une radio hors ligne n'aurait rien à montrer.
L'onglet du navigateur — ou le nom de la fenêtre installée — dit ce qui
passe : titre et artiste, le nom de la radio quand personne n'écoute. Sans
auditeur, la carte de veille dit « Rien à l'antenne » et comment démarrer la
radio — le texte « La radio dort » a été retiré le même jour (l'auteur).
Ce qu'un téléphone fait de l'installation ne se constate qu'en essayant.

**Depuis le 2026-09-02** (GOAL-064), la page bouge un peu : les lignes d'une
liste entrent l'une après l'autre, un onglet glisse vers le suivant, une
chanson qui change fond l'ancienne dans la nouvelle — dans la scène comme
dans la barre. Tout s'éteint quand le système demande moins de mouvement.

**Depuis le 2026-09-02** (GOAL-065), le lecteur propose de **renvoyer le son
vers une enceinte** — Chromecast, AirPlay — par l'API Remote Playback du
navigateur, sans SDK tiers (docs/flux-icy.md §8). Le bouton n'apparaît qu'en
écoute, et seulement si le navigateur voit une cible : la page ne promet
rien qu'elle ne sache tenir. C'est l'enceinte qui ouvre le flux, donc
`web.stream_url` doit être joignable depuis elle. Ce qu'une enceinte fait
du flux ne se constate qu'en essayant.

L'interface web n'est rien de plus que la mise en page de cela : ce qui passe,
ce qui vient, un lecteur, trois boutons. Elle **ne configure pas** la radio — le TOML reste le seul point
d'entrée des réglages (§6) — et ne touche pas à la bibliothèque (§2).

### 4.13 Les programmes

Un **programme** est une plage de temps — **des jours et des heures** — pendant
laquelle la musique est tirée au hasard dans une **liste de lecture** que
l'auteur a constituée dans sa bibliothèque.

```toml
[[programmes]]
name      = "Le vendredi de Chloé"
playlist = "Chloé"
days    = ["vendredi"]
start    = "18:00"
end      = "20:00"
```

C'est la différence avec une plage thématique (§4.4) : une plage contraint le
**genre** dans toute la bibliothèque, un programme puise dans une **sélection
faite à la main**. « Du rock le soir » et « ma sélection du vendredi » ne sont
pas la même intention.

#### Ce qu'un programme ne change pas

Un programme reste de la musique. Tout ce qui vaut ailleurs vaut ici :

- la **non-répétition** s'applique, et sa fenêtre rétrécit si la liste est
  courte (§4.2) — une liste de dix titres ne bloque pas la radio ;
- les **jingles horaires** passent normalement ;
- **`stop` et `encore` sont acceptés** — un programme n'est pas un habillage.

#### `encore` reste dans la liste

Un `encore` pendant un programme cherche l'artiste **dans la liste**, pas dans
la bibliothèque. S'il n'a pas d'autre titre dans la liste, on retombe sur un
tirage **dans la liste**, jamais au-dehors.

> **Un programme est une intention.** Vous avez choisi ces morceaux-là, à cette
> heure-là ; en sortir sur un `encore` trahirait ce choix. C'est le seul endroit
> où `encore` a une portée plus étroite qu'ailleurs, et c'est délibéré.

#### Quand la liste manque

Une liste introuvable, vidée ou renommée **ne fait pas taire la radio** : elle
se replie sur le tirage libre, et le repli est journalisé — exactement comme une
plage thématique sans musique (§4.4) ou un flash absent (§4.5).

Aucune règle nouvelle à retenir : c'est la même que partout.

#### Ce qui reste à trancher

Programmes et plages thématiques sont **deux mécanismes qui répondent à la même
question** — que jouer à telle heure. Faut-il les garder tous les deux ? Voir
§7 n°19. En attendant, **le programme l'emporte** là où les deux se recouvrent,
parce qu'il est le plus précis.

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

La musique vient de **sources** déclarées dans le TOML. Subsonic en est une ;
d'autres pourront être ajoutées sans rien reprendre du cœur.

Une source sait faire trois choses, et seulement trois : chercher, tirer au
hasard sous contrainte de genre ou d'artiste, et résoudre une piste en un flux
audio lisible. Tout le reste — la grille, le tirage, la non-répétition — est
décidé au-dessus d'elles et ne dépend d'aucune.

**Une seule source est écrite aujourd'hui** : Subsonic. Le mécanisme est
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
- Elle vient d'un **flux de podcast**, dont on diffuse **l'épisode `full` le
  plus récent qui n'a pas déjà été diffusé** — ou d'un **direct** (ci-dessous).

#### Une émission peut être un direct

Une émission peut avoir pour source **un flux de webradio** plutôt qu'un
podcast : franceinfo pour un flash d'information, ou n'importe quelle autre
station, pendant une case donnée (§7 n°22). Elle obéit à tout ce qui précède,
avec trois différences qui tiennent à la nature d'un direct :

- **Elle a une durée déclarée, obligatoire.** Un podcast se termine de lui-même ;
  un direct jamais. La radio se rebranche sur la musique à la fin de la case —
  à la seconde, sans attendre une jonction, puisqu'il n'y en a pas. **Et sur
  un morceau frais** : celui qui attendait avait été tiré à l'ouverture de la
  case, pour une plage qui n'est peut-être plus ouverte (§7 n°22, révision du
  2026-09-02).
- **Elle n'a pas de rattrapage** (§7 n°13 ne s'applique pas) : ce qui compte est
  ce qui passe *maintenant* sur la station captée. Si la case est déjà
  entamée quand la jonction arrive, on capte pour **le temps qui reste** ; si la
  case est finie, elle est sautée et journalisée.
- **Elle ne s'enregistre pas comme diffusée** : il n'y a pas d'épisode. Elle se
  produit à chaque occurrence de sa case.

Un direct **injoignable, qui se tarit ou qui coupe en cours de case** n'est pas
une panne : la radio revient sur la musique et journalise (§4.5). Elle ne
retente pas dans la même case.
  - **`full` seulement.** Les `bonus` et les `trailer` sont écartés : un podcast
    qui publie une bande-annonce d'une minute trente ne doit pas la voir passer à
    l'heure de son émission.
  - **Jamais deux fois le même.** Si le plus récent a déjà été diffusé, la case
    est **sautée** : la radio reste sur la musique et le journalise, exactement
    comme pour un flash absent. Une émission qui n'a rien de neuf est une
    émission qui n'a pas lieu.

> **C'est la seule chose que ce projet retient entre deux démarrages** — voir
> §4.11.1. Tout le reste est perdu à l'arrêt, comme annoncé en §2.

#### 4.11.1 La seule mémoire du projet

Pour ne pas rediffuser, il faut se souvenir. Ce projet **n'avait aucune
persistance** (§2, ARCHITECTURE.md §5) ; il en acquiert **une, et une seule** :

> Pour chaque émission, **l'identifiant du dernier épisode diffusé**.

Rien d'autre. Ni historique, ni statistiques, ni position de lecture, ni ce qui
est passé à l'antenne. Un identifiant par émission, et c'est tout.

Ce que cela implique, et qui est assumé :

- **Perdre ce fichier n'est pas une panne** : la radio rediffusera une fois
  l'épisode le plus récent, puis reprendra son comportement normal. Il n'y a
  donc rien à sauvegarder.
- **Le fichier n'est pas de la configuration** : il est écrit par la radio, pas
  par l'auteur. Il ne va ni dans le TOML ni dans `.env` — seul **son chemin** y
  est déclaré.
- Le stockage est une base **SQLite** (ARCHITECTURE.md §5.1), partagée avec les
  votes (§4.12) et le journal des titres (§7 n°27).
- **Un épisode retiré du flux** ne pose pas de problème : l'identifiant retenu
  ne correspond plus à rien, donc le plus récent est forcément différent, donc
  il est diffusé.

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
[[shows]]
name   = "A la French"
feed  = "https://feeds.acast.com/public/shows/a-la-french"
days = ["vendredi"]
time = "20:00"

[[shows]]
name   = "LEGEND"
feed  = "https://feeds.acast.com/public/shows/legend-1"
days = ["mardi", "jeudi"]
time = "21:00"
```

Une **plage de podcasts** (§7 n°35) se déclare de la même façon, avec deux
clés de plus : `feeds` à la place de `feed`, et `end` :

```toml
[[shows]]
name  = "Podcasts - longs formats"
feeds = [
  "https://feeds.acast.com/public/shows/legend-1",
  "https://feeds.audiomeans.fr/feed/f57a29ac-....xml",
]
days = ["saturday", "sunday"]
time = "21:00"
end  = "23:00"
```

Entre `time` et `end`, la radio tire un flux au hasard parmi ceux qui ont un
épisode non diffusé, joue son épisode, puis recommence. La pioche est uniforme
**entre les flux**, jamais entre les épisodes. L'épisode entamé avant `end`
finit (§7 n°5) : une plage déborde donc d'autant plus que ses flux sont longs.
`end` est réservée aux podcasts — un direct et une chaîne YouTube n'enchaînent
rien — et une émission dont l'heure tombe **pendant** une plage du même jour
fait échouer le démarrage, comme deux émissions à la même heure.

**Les flux se lisent hors du chemin de la diffusion**, podcasts comme chaînes
YouTube — celles-ci enchaînent un flux Atom et une résolution `yt-dlp`, deux
appels que le diffuseur n'attend pas. Le diffuseur
attend la réponse pour jouer et abandonne au bout de son propre délai ; trois
flux lus
l'un après l'autre le dépassaient, et un hébergeur qui n'accuse rien suffisait
à couper l'antenne. La radio ne sert donc que ce qu'elle a déjà lu, et lance
la lecture en fond : les flux d'une case sont lus **avant** son ouverture, et
une case dont les flux ne sont pas encore là attend la jonction suivante — la
musique continue, comme pour tout ce qui manque à une émission (§4.11). Un
catalogue dont la garde a expiré sert quand même, le temps de le relire : sans
cela l'expiration tombait au milieu d'un épisode long et intercalait un
morceau de musique entre chaque épisode d'une plage.

**Une plage peut n'avoir presque rien à jouer**, et c'est voulu : un flux ne
sert qu'un épisode par publication (§7 n°14), donc une plage de trois heures
peut n'en tenir que vingt minutes si ses podcasts sont hebdomadaires. La
musique reprend pour le reste, sans que cela se signale comme une panne.

Un flux lu est gardé `podcast.cache_seconds` (900 s par défaut, `0` = jamais) :
une plage relit tous ses flux à chaque jonction, et six d'entre eux pèsent
21,6 Mo (docs/podcast.md §4.bis). Un épisode publié n'apparaît qu'à
l'expiration, ce qui est sans conséquence — la case ne se rouvre pas plus vite.

`days` vaut `"all"` ou une liste de jours de la semaine ; `time` est un moment
de la journée. **Rien de plus.** Ce choix est délibéré : des champs déclaratifs
n'exigent aucun analyseur syntaxique, se testent directement, et couvrent les
deux cas demandés — « tous les jours à 20 h » et « chaque mardi à 12 h ».

**Ce que cette forme ne sait pas exprimer**, et qui devra ouvrir une décision le
jour où le besoin apparaîtra : « le premier lundi du mois », « une semaine sur
deux », « du lundi au vendredi sauf jours fériés ». Une grammaire de récurrence
complète — de type `cron`, ou un langage à écrire — serait un analyseur, ses cas
limites et sa documentation. Elle n'arrivera pas avant son deuxième cas d'usage
(AGENTS.md §2).

### 4.12 Ce que la radio retient de vos votes

`stop` et `encore` ne valent pas que pour le morceau en cours : ils sont
**enregistrés**, et ils **pondèrent les tirages suivants**.

- Un artiste souvent passé revient **moins souvent**.
- Un artiste souvent redemandé revient **plus souvent**.

**Le vote porte sur l'artiste, et sur lui seul** (§7 n°16, révisée) : la
double portée piste + artiste surpondérait — chaque geste comptait deux fois,
et un artiste très présent finissait par écraser le tirage.

**Rien n'est jamais supprimé.** Un morceau passé cent fois reste dans la
bibliothèque et peut toujours sortir : sa chance diminue, elle ne s'annule pas.
C'est la différence entre une radio qui apprend et une radio qui se rétrécit —
et c'est la seconde qui finit par ne plus rien passer d'inattendu.

#### Ce que cela n'est pas

Ce n'est **pas** une note, ni un système de favoris, ni une liste noire. Il n'y a
rien à consulter, rien à corriger, rien à remettre à zéro depuis l'interface. La
radio écoute ce que vous faites, et elle en tient compte. C'est tout.

Ce n'est pas non plus une **recommandation** : aucun modèle, aucune similarité
calculée, aucun profil. Un compteur par artiste, et une pondération du tirage.

#### Un biais à connaître

Un `stop` ne dit pas « je n'aime pas ». Il dit souvent « pas maintenant », ou
« encore celui-là ». **Une radio qui pénalise durablement ce qu'on passe finit
par pénaliser ce qu'on aime le plus** — puisque c'est ce qu'elle joue le plus, et
donc ce qu'on passe le plus.

C'est la raison d'être de la décision ouverte §7 n°18 : sans oubli, la
pondération dérive dans le sens contraire de son intention.

#### Ce que chaque geste pèse

Un vote porte **sur l'artiste, et sur lui seul** (§7 n°16). Le barème ne dépend
pas du geste : `stop` et `encore` pèsent pareil, dans des sens opposés.

| Geste | Sur la piste | Sur l'artiste |
|---|---|---|
| `stop` | 0 | **1** |
| `encore` | 0 | **1** |

Un poids nul ne s'enregistre pas : rien n'est écrit au nom de la piste. Un
signal répété porte donc par l'artiste — dix `stop` sur des titres différents
d'un même artiste se voient, sans que le titre passé soit puni deux fois. La
première mouture — 1 sur ce que le geste désigne, 0,25 sur l'autre — a été
révisée le jour même de sa mise à l'écoute, parce qu'elle comptait chaque vote
deux fois (n°16).

#### Les votes s'oublient

Un vote pèse plein son poids, puis **s'estompe**. La demi-vie est déclarée au
TOML, et vaut **trois mois** par défaut :

```
stop d'hier        → compte 100 %
stop d'il y a 3 mois →  50 %
stop d'il y a 1 an   →   6 %
```

**C'est ce qui empêche la pondération de se retourner contre elle-même.** Sans
oubli, la radio se figerait sur ce qu'on a cliqué le premier mois — et
pénaliserait durablement ce qu'on aime le plus, puisque c'est ce qu'elle joue le
plus, donc ce qu'on passe le plus.

#### De combien

Le poids d'une piste ou d'un artiste est un multiplicateur de sa chance d'être
tiré, **borné des deux côtés** :

| | |
|---|---|
| Plancher | **×0,25** — quatre fois moins souvent, **jamais zéro** |
| Neutre | ×1 |
| Plafond | **×4** — quatre fois plus souvent |

Ordres de grandeur attendus : un `stop` récent ≈ ×0,7, trois ≈ ×0,4 ; un
`encore` récent ≈ ×1,5, trois ≈ ×2,5.

Assez pour s'entendre en quelques semaines, assez peu pour que la radio garde des
surprises : sur une grande bibliothèque, un titre à ×0,25 sort encore
régulièrement.

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
| Source injoignable **au démarrage** | refuse de démarrer, erreur HTTP explicite (§4.1) |
| Source injoignable **en cours** | continue avec ce qui est en file, réessaie en arrière-plan (§5.1) |
| La file s'épuise, la source toujours injoignable | **coupe proprement** plutôt que de servir du silence (§5.1) |
| Liquidsoap qui meurt en cours | le superviseur le relance ; les auditeurs se rebranchent sur une radio neuve (§4.7) |

La distinction est nette : **au démarrage**, une erreur est fatale et se dit ;
**en cours de diffusion**, elle se contourne et se journalise.

### 5.1 Jusqu'où « une radio ne se tait pas »

Le principe a une limite, et elle est nette : **la radio tient, puis elle coupe
en le disant.** Elle ne boucle jamais sur ce qu'elle a déjà joué pour donner le
change.

| Panne | Ce que fait la radio |
|---|---|
| Source injoignable | continue avec ce qui est en file, réessaie en arrière-plan |
| … et la file s'épuise sans retour | **coupe**, en journalisant pourquoi |
| l'API ne répond plus à Liquidsoap | il réessaie **une fois**, puis **coupe** en journalisant pourquoi |
| Liquidsoap meurt | le superviseur le relance, neuf |

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
identifiants Subsonic aujourd'hui, ce qui s'y ajoutera demain.

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
pour tout ce qui n'est pas secret.

Ce qu'il décrit, section par section. Le schéma qui fait foi est
`adapters/config/schema.py` : une clé qui n'y est pas est refusée au
démarrage, et toute clé ajoutée est documentée ici dans le même incrément
(AGENTS.md §6).

- **Le tirage** (`[draw]`) : `artist_gap`, le nombre d'artistes distincts qui
  doivent passer avant qu'un artiste puisse revenir (§4.2, 5 par défaut) ;
  `max_track_minutes`, le plafond de durée de lecture d'une piste (§4.2, 20 par
  défaut, `0` = sans limite) ; `lookahead`, le nombre de titres tirés d'avance
  — la liste des prochains titres (§4.8, 8 par défaut, au moins 1) ;
  `min_theme_tracks`, les titres qu'un artiste ou un genre doit avoir pour
  qu'une plage « carte blanche » le tire (§7 n°36, 15 par défaut, `0` = ne rien
  exiger) ;
- **Les votes** (`[draw.votes]`) : `floor` et `ceiling`, les bornes du
  multiplicateur de chance (§4.12, n°17 — 0,25 et 4 par défaut), et
  `half_life_days`, la demi-vie d'un vote (§4.12, n°18 — 90 par défaut) ;
- **Les jingles** (`[jingles]`) : `folder`, le dossier ; `encore`, le nom du
  jingle de vote (§4.6, `encore.mp3` par défaut) ; `expiry_seconds`, la
  péremption d'un jingle horaire (§4.3, n°29 — 900 par défaut, `0` = jamais).
  Les jingles horaires, eux, ne se nomment pas : `hours/00h.mp3` …
  `hours/23h.mp3`, le nom du fichier est la programmation (§4.3) ;
- **Les moments thématiques** (`[[bands]]`) : `start` et `end` ; `days`, une
  liste de jours ou `"all"` (tous les jours par défaut) ; le thème — `genres`,
  `artists`, ou `random` valant `"genre"` ou `"artist"` pour laisser la radio
  choisir (§4.4). Une plage déclare **exactement une** des trois clés — sauf à
  porter un `mode` seul. `mode` demande que les tirages s'**enchaînent** (§4.4,
  n°31) : `double_dose`, `era_fan` ou `artist_fan`, combinable au thème.
  `eras` borne les décennies où la plage tire — une liste d'entiers multiples
  de dix, comme `[2000, 2010, 2020]` ; absente, la plage tire dans toutes
  (§4.4). `intro` et `outro` nomment les génériques joués à son ouverture et à
  sa fermeture (§4.4) ;
- **Les programmes** (`[[programmes]]`) : une entrée par programme — `name`,
  `playlist`, `days`, `start`, `end`, et `intro` / `outro` comme une plage
  (§4.13) ;
- **Les émissions** (`[[shows]]`) : une entrée par émission — `name`, `days` et
  `time`, l'heure de la case (§4.11). Exactement **une** source : `feed` (un
  podcast), `feeds` (plusieurs, c'est une **plage de podcasts**, §7 n°35),
  `stream` (un direct, dont le flash d'information de §4.5) ou `youtube` (une
  chaîne). `duration_minutes` est obligatoire pour un direct — il faut le
  couper — et interdit ailleurs, où la durée se lit à la source. `end` est
  l'heure jusqu'à laquelle une plage de podcasts enchaîne les épisodes. Il n'y
  a pas de limite au nombre d'émissions. Un même flux ne se déclare pas deux
  fois, ni dans une plage ni entre deux émissions : chacune tient sa propre
  mémoire, et le même épisode passerait deux fois ;
- **L'état** (`[state]`) : `database`, le chemin de la base SQLite (§4.11.1),
  et `timeout_seconds`, le délai qu'une écriture accepte d'attendre un verrou
  — deux processus y touchent (5 par défaut, au moins 0,1) ;
- **Le web** (`[web]`) : `address` et `port` de l'interface et de l'API
  (`0.0.0.0` et 8080 par défaut) ; `refresh_seconds`, l'intervalle auquel le
  serveur regarde si l'antenne a changé (5 par défaut, au moins 0,5) ;
  `upcoming_horizon_minutes`, jusqu'où la liste des prochains titres coud la
  grille derrière son dernier titre (§4.8 — 180 par défaut, `0` ne coud rien) ;
  `stream_url`, l'adresse du flux que le lecteur de la page ouvre (§4.8) —
  absente, pas de lecteur ; `:8000/flux` désigne l'hôte de la page ;
- **Le diffuseur** (`[liquidsoap]`) : `url`, où joindre Liquidsoap pour lui
  ordonner `/skip` et `/requeue` (§5.1, `http://127.0.0.1:8000` par défaut —
  en conteneur, `http://liquidsoap:8000`), et `order_timeout_seconds`,
  l'attente maximale de cet ordre (3 par défaut, au moins 0,1). Une adresse
  fausse ne fait pas taire la radio : l'ordre est journalisé en échec et le
  morceau finit ;
- **Les podcasts** (`[podcast]`) : `timeout_seconds`, le délai au-delà duquel
  un flux est réputé injoignable (15 par défaut, au moins 0,1) — il reste
  court, une émission qui ne répond pas ne bloque pas la radio, elle est perdue
  et la musique continue (§4.11) — et `cache_seconds`, la durée pendant
  laquelle un flux lu est gardé (900 par défaut, `0` = relire à chaque fois).
  Une plage relit tous ses flux à chaque jonction, et six d'entre eux pèsent
  une vingtaine de mégaoctets ;
- **YouTube** (`[youtube]`) : `timeout_seconds`, le délai accordé à `yt-dlp`,
  qui peut être lent (60 par défaut, au moins 0,1) ;
- **Subsonic** (`[subsonic]`) : `artist_results`, le nombre de résultats par
  artiste (50 par défaut) ; `timeout_seconds`, le délai réseau (10 par défaut,
  au moins 0,1) ; `cache_seconds`, la durée du cache de bibliothèque (une heure
  par défaut, `0` = sans cache — le prix est assumé : un morceau ajouté sur le
  serveur n'apparaît qu'à l'expiration). **Aucune taille d'échantillon** : le
  tirage voit la bibliothèque entière, récupérée par pagination
  (docs/subsonic.md §2.7). C'est la seule source de musique écrite à ce jour
  (§4.10, §7 n°12) ;
- **La reprise** (`[playout]`) : `resume_fresh_seconds`, la pause sans auditeur
  au-delà de laquelle le retour repart sur un tirage neuf (§4.7, n°30 — 900 par
  défaut, `0` = jamais).

**Ce que le TOML ne décrit pas.** Le flux lui-même — adresse d'écoute, port,
format, débit — et les durées de fondu sont l'affaire de Liquidsoap et vivent
dans `radio.liq` (ARCHITECTURE.md §4). Les heures des flashs d'information
n'ont pas de clé propre : un flash est un `[[shows]]` avec `stream` (§4.5).

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
plusieurs activables (§4.10). Une seule est écrite — Subsonic.
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

**n°4 — La péremption ? Aucune.** Tranchée le 2026-08-30, **amendée le
2026-08-31 par la n°29** : les jingles horaires périment désormais. Le reste
tient : ni les flashs ni les émissions ne sont abandonnés **pour cause de
retard**. **L'exception de la n°15** demeure : ce qui est dû pendant une
émission est abandonné — pour une raison qui n'est pas le retard.
> *Raison d'origine* : un jingle est de l'habillage, personne ne règle sa
> montre dessus. Renoncer aurait coûté un seuil, un réglage et une famille de
> cas limites pour un gain nul. La décision supprimait aussi tout seuil de
> péremption du TOML — la n°29 en rouvre un, et un seul, en sachant ce que
> cela coûte.

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
> **Précisée le 2026-09-02** (n°34) : ce qui joue finit toujours ; mais ce qui
> est tiré **d'avance** l'est sous le moment de son heure estimée, et non du
> présent — la grille est consultée pour le créneau, pas après le tirage.

**n°8 — Les pannes en cours ? Tenir, puis couper en le disant.** Tranchée le
2026-08-30. Source injoignable : continuer sur la file, réessayer en
arrière-plan, couper si la file s'épuise. API muette pour le diffuseur :
réessayer une fois, couper en le disant (§5.1, n°23).
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

**n°14 — Quel épisode ? Le plus récent `full` non encore diffusé.** Tranchée le
2026-08-30, **puis révisée le même jour** à la lumière du relevé (§4.11).

> **Ce qui a changé, et pourquoi c'est important.** La première version disait
> « le plus récent », sans mémoire — et sa raison principale était qu'elle **ne
> rouvrait pas l'absence de persistance**.
>
> Le relevé de [docs/podcast.md](./docs/podcast.md) §3.3.3 a montré ce que cela
> donnait en pratique : *A la French* est entre deux saisons depuis le
> 28 juillet, donc une case hebdomadaire aurait rejoué le même épisode pendant
> des mois. « Cela s'entend, et cela ne casse rien » avait été écrit en pensant à
> un podcast quotidien, où le cas est rare ; sur une hebdomadaire en pause, c'est
> le cas **nominal**.
>
> L'auteur a donc tranché pour « ne pas rediffuser », **en sachant que cela
> ouvrait le premier état persistant du projet**. C'est une décision
> d'architecture, prise sciemment : voir §4.11.1 pour son étendue exacte —
> un identifiant par émission, rien de plus — et ARCHITECTURE.md §5.
>
> **`full` seulement** : le relevé a montré qu'`itunes:episodeType` distingue
> aussi `bonus` et `trailer`, et que le plus récent d'*A la French* est
> justement un `bonus`. L'auteur l'écarte — un bonus n'est pas l'émission.

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

**n°16 — Le poids porte sur quoi ? Sur l'artiste seul.** Tranchée le
2026-08-30, puis **révisée le même jour par l'auteur, à l'écoute** : `stop`
comme `encore` comptent **1 sur l'artiste**, rien sur la piste (§4.12).
> *Raison de la révision* : la première mouture — 1 sur ce que le geste
> désigne, 0,25 sur l'autre — surpondérait : chaque vote comptait deux fois,
> et un artiste déjà très présent dans la bibliothèque finissait par écraser
> le tirage. La clé `cross_weight` disparaît du TOML avec elle.

**n°17 — De combien ? De ×0,25 à ×4.** Tranchée le 2026-08-30. Plancher **non
nul** — rien n'est jamais supprimé — et plafond, pour qu'un artiste redemandé dix
fois ne sature pas la radio (§4.12).
> *Raison* : assez pour s'entendre en quelques semaines, assez peu pour garder des
> surprises. Sur une grande bibliothèque, un titre à ×0,25 sort encore
> régulièrement.

**n°18 — Les poids s'oublient-ils ? Oui.** Tranchée le 2026-08-30. Décroissance
dans le temps, demi-vie déclarée au TOML, **trois mois** par défaut (§4.12).
> *Raison* : c'est la seule des trois qui **corrige** le biais de §4.12 au lieu de
> l'amplifier. Sans oubli, la radio se fige sur les premiers mois d'usage et
> pénalise durablement ce qu'on aime le plus.

**n°20 — `encore` pendant un programme ? Il reste dans la liste.** Tranchée le
2026-08-30. L'artiste est cherché dans la liste ; à défaut, on retire dans la
liste, jamais au-dehors (§4.13).
> *Raison* : un programme est une intention, et en sortir sur un `encore`
> trahirait le choix des morceaux. C'est le seul endroit où `encore` a une
> portée plus étroite qu'ailleurs.

**n°21 — Une liste de lecture manquante ? Repli sur la musique.** Tranchée le
2026-08-30. Introuvable, vidée ou renommée : tirage libre, et le repli est
journalisé (§4.13).
> *Raison* : c'est la règle de tout le reste de la spécification — une plage
> sans musique, un flash absent. Aucune règle nouvelle à retenir.

**n°22 — Un flux de webradio comme émission ? Oui, avec une durée.** Tranchée
le 2026-08-30 par l'auteur. Une émission peut capter un direct (§4.11) ; la case
a une durée obligatoire, pas de rattrapage, pas de trace en base.
> *Raison* : c'est ce qui rend le flash France Info possible — son podcast est
> désormais vide (docs/franceinfo.md §1.bis), et le direct répond. Et c'est le
> même mécanisme qui permet de glisser n'importe quelle station entre deux
> créneaux de musique. Le flash cesse d'être un mécanisme à part : c'est une
> émission courte dont la source est un direct.
>
> **Ce qui reste à l'auteur** : la durée à réserver pour un flash — la grille
> de franceinfo n'est connue que de seconde main — et si une coupure « en cours
> de phrase » à la fin de la case est acceptable. Seule l'écoute le dira.
>
> **Mise en œuvre, constatée le 2026-08-30** (GOAL-015) : l'API rend au
> diffuseur une instruction `live:<fin en secondes Unix>:<url>` ; la fin est
> **absolue**, quelle que soit l'heure où la jonction arrive. Deux conséquences
> mesurées, cohérentes avec « pas de rattrapage » : une case **plus courte que
> deux morceaux** peut être sautée entièrement — le diffuseur a toujours un
> morceau d'avance, et la jonction peut tomber après la case — et la coupure
> effective traîne de quelques secondes, le temps de vider le tampon du direct
> (docs/liquidsoap.md §5).
>
> **Révision du 2026-09-02** (GOAL-051) : **la fin d'un direct est une purge.**
> Le morceau demandé d'avance a été tiré à l'ouverture de la case et a dormi
> dessous toute sa durée ; le rendre à la coupure, c'est diffuser une heure
> plus tard un morceau choisi pour une plage qui n'est plus ouverte. Le
> diffuseur jette donc son avance et coupe le reliquat quand le direct rend
> l'antenne, et redemande — c'est la mécanique de la n°30, appliquée à une
> autre cause. Constaté à l'antenne : deux minutes de musique hors plage à 8 h
> le matin même.
>
> **Complément du 2026-09-06** (GOAL-083-T05) : le diffuseur jette cette avance
> sans avoir de route pour le dire, et l'API l'ignorait. Elle l'apprend de
> l'ordre des demandes — ce qui commence est plus récent que ce qui a été jeté.
> L'avance gelée cesse donc d'être annoncée dans « À suivre », et de revenir à
> l'antenne au premier battement après l'heure pleine (n°33).

**n°23 — ffmpeg à la main, ou Liquidsoap ? Liquidsoap.** Tranchée le 2026-08-30
par l'auteur, sur relevé ([docs/liquidsoap.md](./docs/liquidsoap.md)). Le
noyau continue de décider de chaque morceau ; Liquidsoap encode, enchaîne,
fond, sert, et gère les auditeurs.
> *Raison* : six des sept défauts trouvés à la relecture du 2026-08-30 sont dans
> le cycle de vie des processus et des connexions — ce que Liquidsoap fait
> depuis quinze ans. Les fondus et le niveau viennent avec ; le direct de la
> n°22 aussi. Et le point décisif : le tirage, la grille, les jingles et les
> émissions **ne bougent pas** — `request.dynamic` demande à notre code quoi
> jouer, morceau par morceau.
>
> **Ce que cela coûte, et qui est assumé** : « rien ne tourne tant que personne
> n'écoute » (§1) se lit désormais **« rien n'est décodé ni demandé »** — un
> processus reste debout et encode du silence, à moins d'un pour cent d'un
> cœur. Une image de 967 Mo, et un langage de script dont la syntaxe change
> d'une version à l'autre : le script est validé par `liquidsoap --check` dans
> la vérification, contre la version épinglée.

**n°27 — Un journal des titres ? Oui, borné.** Tranchée le 2026-08-30 par
l'auteur. Ce qui commence — musique et émissions, pas l'habillage — s'inscrit
dans un journal chronologique de deux cents lignes, visible dans l'interface.
> *Raison* : « c'était quoi, tout à l'heure ? » est une question légitime.
> §2 tient toujours : c'est un journal des **titres**, jamais l'audio — rien
> ne se rejoue, rien ne s'archive.
>
> **Précision du 2026-09-02** (GOAL-052) : chaque ligne porte son **jour** en
> plus de son heure. Le journal couvre vingt-quatre heures, donc deux fois la
> même heure : sans le jour, la page rangeait sous « 08 h » celui d'aujourd'hui
> **et** celui d'hier, et l'ordre paraissait faux alors qu'il ne l'était pas.

**n°28 — Une plage au thème tiré au sort ? Greffée sur les plages, figée sur
l'occurrence.** Tranchée le 2026-08-31 par l'auteur. Une plage déclare
`random = "genre"` ou `random = "artist"` au lieu d'énumérer ses valeurs ; la
radio tire dans **toute la bibliothèque** au début de l'occurrence et s'y tient
jusqu'à la fin. L'occurrence suivante retire, et rien n'est persisté.
**Amendée le 2026-09-02** (GOAL-057, GOAL-059) : figée, mais pas subie —
l'auteur peut faire **retirer** un autre thème pour le reste de l'occurrence,
par l'API et l'interface (§4.4) ; et de même rompre une suite au hasard
(n°31) pour en ouvrir une autre. Le thème sorti fait partie du moment : le retirer ouvre un
nouveau moment, et l'avance tirée sous l'ancien est rassise (n°33).
> *Raison* : ni un quatrième mécanisme, ni une émission — c'est la même question
> que les plages, *que jouer à telle heure*, avec une réponse que la
> configuration ne donne pas. Figer sur l'occurrence est ce qui en fait une
> soirée plutôt qu'un tirage libre déguisé : sans cela, chaque morceau
> changerait de thème et rien ne s'entendrait. La configuration **déclare** la
> sorte parce que la déduire d'un réservoir mêlant genres et artistes rendrait
> le résultat imprévisible à la lecture du TOML. L'artiste se tire par une
> piste tirée librement, et non par une capacité « lister les artistes »
> ajoutée au `Protocol` : une capacité de plus coûterait à toutes les sources à
> venir pour un seul appel.
> **Précisée le 2026-09-06** : « figé sur l'occurrence » veut dire sur *chaque*
> occurrence, pas sur la dernière consultée. La radio ne demande pas que le
> thème du moment : elle tire ses titres d'avance sous le moment de leur heure
> estimée (n°34), donc sous des occurrences qu'elle n'a pas encore atteintes.
> Une mémoire à une seule entrée les laissait s'effacer l'une l'autre, et la
> soirée changeait de thème en cours de route — trouvé en relisant, jamais
> entendu (GOAL-076).

**n°29 — Un jingle horaire loin de son heure ? Abandonné.** Tranchée le
2026-08-31 par l'auteur, sur constat : le jingle de 19 h entendu à 22 h 28,
après 3 h 30 sans auditeur — l'avance du diffuseur avait traversé la pause
(docs/liquidsoap.md §5.bis). À plus de `jingles.expiry_seconds` de son heure
pleine (900 s par défaut, `0` = jamais), un jingle horaire n'est plus dû. La
péremption s'évalue heure par heure, et ne touche ni l'« encore » — un vote,
pas une heure — ni les flashs ni les émissions (n°4).
> *Raison* : la n°4 visait le retard **en cours de diffusion** — un morceau
> long qui enjambe l'heure. Une avance congelée pendant une absence d'auditeur
> est un autre régime : là, le jingle n'habille plus, il ment sur l'heure.

**n°30 — Une longue pause sans auditeur ? Le retour repart à neuf.** Tranchée
le 2026-08-31 par l'auteur, même constat que la n°29. Au-delà de
`playout.resume_fresh_seconds` (900 s par défaut, `0` = jamais), le retour d'un
auditeur jette l'avance du diffuseur, coupe le reliquat du morceau interrompu
et oublie l'habillage en attente : tirage neuf (§4.7). En deçà, la reprise se
fait sur l'avance, telle quelle — la pause reste le mode nominal. Un « encore »
voté avant la pause survit.
> *Raison* : garder l'avance rend la reprise instantanée et sans surprise pour
> une pause courte ; après des heures, elle ne vaut plus rien — un morceau tiré
> pour 19 h n'annonce rien à 22 h 30. Le mécanisme s'appuie sur ce que le
> relevé a établi (docs/liquidsoap.md §5.bis) : l'annonce des auditeurs précède
> la remise à l'antenne, la purge est donc sans course ; et le saut n'a d'effet
> que si un morceau passait — à froid, il mangerait le premier tirage. **Qui
> tient ce dernier garde-fou a été revu le 2026-09-02** : c'est le diffuseur,
> seul à savoir ce qu'il joue. La radio, redémarrée seule dans la nuit, croyait
> l'antenne vide et laissait passer neuf minutes d'un morceau de la veille
> (docs/liquidsoap.md §9).
> **Et « couper le reliquat » a été précisé le 2026-09-06** : le diffuseur ne
> peut le jeter qu'au moment où il enchaîne, donc une fois le morceau frais
> prêt. Quand l'API tarde à le rendre, il n'a plus rien à jeter — il l'a déjà
> servi. Le retour est donc **muet** jusqu'au morceau frais, qui entre en
> fondu. Mesuré : deux secondes de la veille, à plein volume sur la fin,
> (docs/liquidsoap.md §11).
> **Et le redémarrage a été tranché le 2026-09-06** (GOAL-083) : un processus
> qui démarre ne sait pas depuis quand la pause dure, la pause est donc datée
> de son démarrage — sinon le premier auditeur du matin après un déploiement
> retrouvait l'avance de la veille, le cas de la n°29. Résidu assumé : un
> auditeur qui revient moins de `playout.resume_fresh_seconds` après un
> redémarrage retrouve l'avance que le diffuseur tenait, comme avant. Traiter
> l'absence de date comme une pause longue coûterait plus cher : un
> déploiement à chaud couperait le morceau en cours.

**n°31 — Des tirages qui s'enchaînent ? Trois modes, portés par la plage.**
Tranchée le 2026-08-31, demande directe de l'auteur. `mode` sur une plage :
`double_dose` (deux titres par artiste tiré), `era_fan` (2 à 6 titres d'une
même décennie), `artist_fan` (3 à 6 titres du même artiste). L'époque est la
**décennie** de l'année de la piste ; les longueurs se tirent par `pick` sur
l'étendue — aucune capacité de plus au hasard ; le même titre ne repasse
jamais dans une suite ; la clé de remise à zéro est l'**occurrence** de la
plage, pas sa contrainte — une plage multi-genres retire un genre à chaque
jonction et la suite y survit, une suite d'artiste suivant son artiste par
`tracks_by`, même hors du genre du moment.
**Précisée le 2026-09-06** (GOAL-083) : la suite est **retenue par
occurrence**, comme le thème au hasard (n°28), et non une seule à la fois.
L'avance est tirée créneau par créneau sous des occurrences différentes
(n°34) : un titre préparé pour la plage suivante coupait sinon la suite en
cours, sans rien dire — la double dose promise se réduisait à un titre.
Rompre une suite (§4.4) ne rompt que celle du moment courant. La mémoire est
bornée aux dernières occurrences vues ; au-delà, une occurrence oubliée
repart à zéro.
> *Raison* : c'est un geste d'antenne — « encore un peu de la même chose » —
> pas un nouveau mécanisme de grille : le mode se greffe sur la plage comme le
> thème au hasard (n°28), et tout le reste (émissions, programmes, encore,
> votes) l'ignore. Les suites d'artiste empruntent le passe-droit de fenêtre
> de l'encore (§4.6) plutôt qu'une règle nouvelle.

**n°32 — Une piste trop longue ? Coupée au plafond, pas écartée.** Tranchée le
2026-08-31 (« jamais diffusée »), **révisée le 2026-09-01** sur demande directe
de l'auteur. Au-delà de `draw.max_track_minutes` (20 min par défaut, la limite
exacte passe, `0` = sans limite), une piste se choisit comme les autres —
tirage, suites, encore, listes des programmes — mais sa lecture se coupe au
plafond, fondue vers l'entrée suivante par la jonction ordinaire. La coupe est
journalisée. Les émissions gardent leur propre durée.
> *Raison de la révision* : écarter un DJ set du tirage protégeait le rythme
> mais rendait une partie de la bibliothèque inaudible à l'antenne. Le couper
> au plafond garde les deux : tout se joue, rien ne monopolise l'antenne. La
> coupe vit dans la charnière de diffusion — le noyau ne connaît plus le
> plafond, c'est une affaire de lecture, pas de choix (docs/liquidsoap.md §7).

**n°33 — Ce qui a été tiré d'avance sous un moment fini ? Rassis, et jeté.**
Tranchée le 2026-09-02 par l'auteur, après l'écoute de 16 h : le jingle une
chanson trop tard, puis le générique du mystère suivi d'un morceau de la plage
d'avant. Toute entrée décidée d'avance — l'avance de la file comme l'entrée
déjà demandée par le diffuseur — est **datée** par le moment qui l'a tirée
(le programme, l'occurrence de plage, ou le tirage libre) et par l'instant de
sa décision. Une entrée dont le moment a fini est rassise : elle n'est ni
servie, ni annoncée, ni replacée — le tirage suivant la remplace sous le
moment courant. Une heure pleine passée depuis la décision d'une entrée
musique la fait replacer derrière le jingle dû ; le battement d'auditeurs du
diffuseur (quinze secondes) en est l'horloge, et seulement quand quelqu'un
écoute. Pendant une émission, l'heure ne compte pas — ses jingles sont
abandonnés (§4.11) — mais un moment fini compte toujours.
> *Raison* : le direct (`stop_live`), la longue pause (n°30) et « À suivre »
> (GOAL-054) avaient chacun reçu un correctif particulier pour le même trou —
> une avance servie sans regarder sous quoi elle avait été tirée. Une règle
> unique, constatable dans la file et dans la charnière, remplace le quatrième
> cas particulier. Les deux purges existantes restent, parce qu'elles ne
> jugent pas au moment : la longue pause impose un tirage neuf **même sous la
> même plage** (n°30), et le script du diffuseur ne connaît aucun moment — sa
> purge de fin de direct est la ceinture du battement, qui, lui, ne peut agir
> que toutes les quinze secondes. Ce qui joue n'est jamais touché : la n°5
> tient, seule l'avance — que personne n'entend encore — est remise en
> question.

**n°34 — Les prochains titres ? Une avance de N titres, tirés pour leur
heure, et retirables.** Tranchée le 2026-09-02 par l'auteur. La file tire
`draw.lookahead` titres d'avance (défaut 8, révisé le 2026-09-02 : l'auteur
voulait voir plus loin), chacun **sous le moment de son
heure estimée** — le morceau en cours, puis les durées, l'habillage pour zéro —
et daté par lui (n°33) ; l'estimation se revalide à chaque préparation, et un
créneau qui a glissé est retiré avec ce qui le suit. La liste se lit par l'API
avec les heures estimées et l'habillage prévu ; un titre s'en retire, remplacé
sous le même moment, et compte comme passé pour la non-répétition. La
non-répétition voit ce qui attend. Rien d'autre : ni réordonner, ni forcer.
> *Raison* : l'auteur voulait voir venir et agir avant diffusion ; une liste
> qui ne serait qu'une fenêtre sur l'avance existante aurait montré des titres
> rassis dès qu'une plage change — d'où le tirage pour l'heure du créneau, qui
> est aussi ce qui rend la liste juste sans rien décider avant la jonction. La
> profondeur est bornée pour que la grille ne change pas sous une avance
> entière, et parce que chaque titre d'avance est un appel à la source. La
> n°5 tient : ce qui joue n'est jamais coupé, seule l'avance — que personne
> n'entend encore — regarde devant elle.
> **Amendée le 2026-09-06** : la liste ne s'arrête plus au dernier titre tiré.
> Elle **coud** derrière lui les périodes de la grille effective — « 20:00
> Hardisk », « → 22:00 Rock » — sans rien tirer de plus. L'auteur voulait voir
> la suite ; allonger l'avance pour cela aurait été le mauvais remède : au-delà
> de la première frontière de plage, tout est re-tiré à chaque `stop`, et une
> avance de trente titres vide la non-répétition de son sens, puisqu'elle voit
> ce qui attend. La profondeur reste donc bornée ; c'est la **vue** qui va plus
> loin, et elle ne décide rien.

**n°35 — Une plage « podcasts » ? Une émission à plusieurs flux, pas une
plage.** Tranchée le 2026-09-06 par l'auteur, sur analyse du code. Une
`[[shows]]` gagne `feeds` — plusieurs adresses au lieu d'une — et `end`. Entre
`time` et `end`, la radio tire **un flux au hasard parmi ceux qui ont un
épisode non diffusé**, joue son épisode, puis recommence. À `end`, **l'épisode
en cours finit** : c'est la n°5, ce qui passe n'est jamais coupé. La pioche est
uniforme entre les flux, pas entre les épisodes — sans quoi le podcast le plus
prolifique écraserait les autres. Un flux sans rien de neuf est écarté de la
pioche ; tous épuisés, la case est sautée et journalisée. La n°14 tient dans
chaque flux : c'est le `full` le plus récent non diffusé, on ne redescend pas.
> *Raison* : tout ce qu'une plage fait est faux pour un épisode — elle tire des
> pistes par artiste, genre et décennie, les coupe au plafond et les soumet aux
> votes ; un épisode dure soixante-dix minutes, n'a ni artiste ni genre, et ne
> se vote pas. En faire une plage obligerait à trouer chaque règle du tirage
> d'une exception « sauf podcast ». À l'inverse, tout ce qu'une émission fait
> est déjà ce qu'on veut : remplacer la programmation, abandonner les jingles
> (n°15), refuser les votes, se souvenir de ce qui a été diffusé, apparaître
> dans la grille. Il ne manquait que deux traits, et le direct a déjà le
> second. Ce n'est donc pas un troisième mécanisme — la n°19 est assez lourde
> comme cela.
> *Conséquence assumée* : un épisode médian de soixante-dix-sept minutes lancé
> peu avant `end` déborde sur ce qui suit. C'est le prix de la n°5, et il
> s'entend — la plage suivante commence en retard.

**n°36 — Une carte blanche ne tire qu'un thème assez fourni.** Tranchée le
2026-09-06 par l'auteur, sur constat à l'antenne. Une plage `random` n'a le
droit de tirer qu'un artiste — ou qu'un genre — ayant au moins
`draw.min_theme_tracks` titres (15 par défaut, `0` = ne rien exiger). Si aucun
ne l'atteint, le seuil est relâché plutôt que la plage abandonnée, comme le
fait déjà la non-répétition (§4.2).
> *Raison* : la carte blanche de 14 h est tombée sur un artiste n'ayant qu'un
> seul titre dans la bibliothèque, et l'a rejoué huit fois d'affilée pour
> remplir l'heure. Rien ne l'interdisait : la §4.2 compte des artistes, pas des
> morceaux, et le thème est figé pour l'occurrence (n°28). Le seuil vient de la
> mesure : les titres durent 3,6 minutes de médiane, donc une heure en demande
> une quinzaine. Sur la bibliothèque de l'auteur — 5 704 pistes, 1 818 artistes,
> dont 70 % n'ont qu'un titre — le seuil de 15 laisse 61 artistes éligibles, de
> quoi tenir deux mois de cartes blanches quotidiennes sans répétition d'un
> jour à l'autre. Le descendre à 3 n'en donnerait que 190 mais ne réglerait
> rien : trois titres ne remplissent pas une heure.
> *Étendu aux genres le même jour* : le tirage d'un genre est **uniforme**, pas
> pondéré par les titres, et 110 des 227 genres de la bibliothèque de l'auteur
> n'en ont qu'un ou deux — près d'une occurrence sur deux tomberait dans le
> vide. Le décompte se fait sur le parcours, pas sur la liste des genres : un
> genre peut être déclaré sans piste (GOAL-049).
> *Ce que cela ne règle pas* : rien ne mémorise encore les morceaux, donc un
> thème fourni peut voir un de ses titres revenir dans la même heure.

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

**n°19 — Programmes et plages thématiques : faut-il les deux ?**
Ils répondent à la même question — *que jouer à telle heure* — et le programme
est strictement plus expressif : il a des **jours**, et sa source est une liste
choisie plutôt qu'un genre.

Trois issues, et elles ne coûtent pas la même chose :

| Voie | Ce qu'elle vaut |
|---|---|
| **Les deux coexistent** | Deux intentions distinctes, chacune son mot. Rien n'est jeté. Mais deux mécanismes à tenir, et une règle de priorité à retenir |
| **Les programmes remplacent les plages** | Un seul concept. Mais cela **jette `core/grille.py`**, testé à 100 %, pour le réécrire autrement |
| **Les plages gagnent des `jours` et une source « playlist »** | Le même résultat par extension plutôt que par remplacement. Rien n'est jeté, mais le mot « plage » recouvre alors deux choses |

**Rien n'est décidé.** En attendant, la coexistence s'applique — c'est la seule
des trois qui ne jette rien ni ne renomme quoi que ce soit — et **le programme
l'emporte** là où les deux se recouvrent, parce qu'il est le plus précis. Ce
choix est **provisoire et écrit comme tel** : il ne doit pas devenir la réponse
par prescription.

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

**n°37 — Le changement d'heure : la grille suit-elle l'heure locale ?**
Ouverte le 2026-09-06 par la relecture de GOAL-083. L'horloge rend une heure
locale à décalage **figé** au moment de l'appel : `full_hours_between` ajoute
des heures absolues, donc la nuit du passage à l'heure d'été un `02h.mp3`
inexistant est demandé et `03h` sauté ; et la purge du journal des titres
compare des chaînes ISO (n°27), fausse d'une heure ces deux nuits-là. Ce que
cela coûte : deux nuits par an, un jingle absent — cas nominal (§5) — et un
journal purgé une heure trop tôt ou trop tard. Ce qui le trancherait : décider
si la grille est en heure locale vraie (recalculer le fuseau à chaque heure
pleine) ou en décalage figé, et comparer les instants plutôt que leur texte.

**n°38 — « Autre thème » pendant une panne de source : le thème en cours est
perdu.** Ouverte le 2026-09-06 par la relecture de GOAL-083. Retirer un thème
oublie l'ancien **avant** de tirer le nouveau ; si la bibliothèque ne répond
pas, le tirage rend « rien » et la plage finit son occurrence sans thème, alors
qu'elle en avait un. Ce que cela coûte : une plage thématique qui devient une
carte blanche jusqu'à l'occurrence suivante, sur un geste de l'auditeur.
Ce qui le trancherait : dire si un retirage qui échoue **garde** l'ancien thème
— ce que ferait n'importe quelle transaction — ou si l'échec vaut abandon.

**n°39 — Le sel Subsonic partage le hasard du tirage.** Ouverte le 2026-09-06
par la relecture de GOAL-083. Le point d'assemblage passe le même `RealRandom`
à la source Subsonic, qui en tire douze caractères de sel par requête, et à la
file. La rejouabilité à graine fixée (ARCHITECTURE.md §5.3) dépend donc du
**nombre d'appels réseau** : deux exécutions qui ne touchent pas le cache aux
mêmes moments ne rejouent pas la même soirée. Ce que cela coûte : rien à
l'antenne, tout à la reproductibilité d'un incident. Ce qui le trancherait :
donner au sel son propre générateur — c'est un besoin cryptographique, pas un
tirage de programmation — ou assumer que seule la maquette rejoue.

**n°40 — Une émission à `feed` unique accepte `end`.** Ouverte le 2026-09-06
par la relecture de GOAL-083. Le schéma n'exige `feeds` que pour refuser `end`
à un direct et à une chaîne : un `feed` seul avec `end` est accepté, et
constitue une plage qui ne peut enchaîner qu'un épisode (§7 n°14, un épisode
par publication). Ce que cela coûte : une déclaration qui promet trois heures
et n'en tient que vingt minutes, sans que rien ne le dise. Ce qui le
trancherait : dire si c'est une erreur de configuration à refuser au démarrage,
ou une plage à un flux, légitime et à documenter comme telle.

**n°41 — Les durées de l'avance ne sont pas coupées au plafond dans
l'estimation des heures.** Ouverte le 2026-09-06 par la relecture de GOAL-083.
La charnière coupe le morceau **en cours** à `draw.max_track_minutes` pour
estimer la jonction suivante (n°32), mais additionne ensuite les durées
**pleines** de ce qui attend. Ce que cela coûte : sur une avance qui contient
une piste longue, l'heure estimée de chaque titre suivant part trop loin, donc
sous la mauvaise plage — le titre est tiré pour un moment qu'il n'atteindra
pas, et la revalidation le jette à la préparation d'après. Ce qui le
trancherait : appliquer le même plafond aux durées de l'avance, ou établir que
l'écart reste sous la minute et l'écrire.
