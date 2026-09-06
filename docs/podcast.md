# docs/podcast.md — Relevé des flux de podcast

> **Relevé établi le 2026-08-30** (`GOAL-002-T09`) contre les **deux** flux
> réellement voulus :
>
> | Émission | Flux | Épisodes |
> |---|---|---|
> | **LEGEND** | `https://feeds.acast.com/public/shows/legend-1` | 725 |
> | **A la French** | `https://feeds.acast.com/public/shows/a-la-french` | 31 |
>
> Les deux sont hébergés chez **Acast**, donc les constats se recoupent. Ce que
> deux flux du même hébergeur **ne** disent **pas** : ce que fera un troisième
> chez quelqu'un d'autre (§5).
> `GOAL-002` devra répondre **contre les flux réellement déclarés** par l'auteur.
>
> Règle applicable (AGENTS.md §3). Elle mord ici : « RSS avec des `<enclosure>` »
> décrit une convention, pas une norme respectée. Chaque éditeur s'en écarte à sa
> façon, et un flux qui marche ne dit rien du suivant.

Il recoupe [docs/franceinfo.md](./franceinfo.md) : si le flash France Info se
révèle être lui-même un podcast, les deux partagent la même mécanique — et il
faudra le constater, pas l'espérer.

---

## 1. Lire le flux — **relevé**

| Mesure | Constat |
|---|---|
| Réponse | `HTTP 200`, `application/xml; charset=utf-8` |
| Redirections | **aucune** sur le flux lui-même |
| Taille | 3,5 Mo |
| Épisodes exposés | **725** — tout le catalogue, pas les cinq derniers |
| `pubDate` | **0 manquant sur 725** |
| `itunes:duration` | **0 manquant sur 725** |
| `enclosure/url` | **0 manquant sur 725** |
| `enclosure/length` | **0 manquant sur 725** |

Format : RSS 2.0 avec les extensions iTunes. L'URL audio est dans
`<enclosure url>`.

> **Les deux constats dont dépendaient des décisions sont acquis.** `pubDate` est
> fiable, donc « l'épisode le plus récent » (SPECS.md §7 n°14) est
> implémentable ; `itunes:duration` est lisible **sans télécharger le fichier**,
> donc la fenêtre de rattrapage (n°13) est calculable au branchement.

### 1.1 Un champ que le relevé n'attendait pas : `itunes:episodeType`

725 entrées : **724 `full`, 1 `trailer`**.

Le trailer est ancien, donc « le plus récent » ne tomberait pas dessus
aujourd'hui — mais rien ne le garantit demain. **Ne retenir que les `full`** :
c'est une ligne de filtre, et elle évite de diffuser une bande-annonce d'une
minute trente à l'heure de l'émission.

## 2. Récupérer l'audio — **relevé**

L'URL de l'enclosure redirige vers `stitcher2.acast.com/livestitches/…`.

| Mesure | Constat |
|---|---|
| Type | `audio/mpeg` |
| `Accept-Ranges` | **`bytes`** — requêtes partielles acceptées |
| Premiers octets | `ID3\x03` — étiquette ID3, puis les trames |
| **`length` annoncé dans le flux** | **112 645 851 o** |
| **`Content-Length` réellement servi** | **114 800 141 o** |

### 2.1 Le fichier servi n'est pas celui qu'annonce le flux

**Deux mégaoctets de plus que déclaré**, et le nom du chemin dit pourquoi :
`livestitches`. Acast **insère de la publicité à la volée**, au moment de la
requête.

Trois conséquences :

- **`enclosure/length` ne doit pas être utilisé** pour dimensionner quoi que ce
  soit. Il décrit un fichier qui n'est pas celui qu'on reçoit.
- **`itunes:duration` est probablement optimiste** pour la même raison : la durée
  réelle inclut les publicités insérées. La fenêtre de rattrapage (n°13) sera
  donc légèrement plus courte que la diffusion. L'écart est de l'ordre de 2 %
  ici — à surveiller, pas à corriger à l'aveugle.
- **L'auteur doit savoir que les épisodes diffusés contiendront de la
  publicité.** Ce n'est pas un défaut du projet, c'est la nature de la source.

### 2.2 Un épisode ne se met pas en mémoire

114 Mo pour un épisode. `Accept-Ranges: bytes` permet de le lire au fil de
l'eau : **ffmpeg peut consommer l'URL directement**, comme n'importe quelle
autre entrée de la file ([ffmpeg.md](./ffmpeg.md) §2.1). Rien de particulier à
écrire.

## 3. Les durées, et ce qu'elles font aux décisions prises

| | |
|---|---|
| Minimum | **1 min** (le trailer) |
| Médiane | **77 min** |
| Maximum | **170 min** |
| Douze plus récents | de 36 min à **2 h 06** |

### 3.1 Ce que cela fait à la fenêtre de rattrapage (n°13)

SPECS.md §7 n°13 borne le rattrapage à **la durée de l'épisode**. Cette décision
a été prise **avant** de connaître ces chiffres.

Appliquée à LEGEND, elle donne :

```
émission déclarée à 20h00, épisode médian de 1 h 17

20h00  personne n'écoute       → l'émission n'a pas lieu
21h15  branchement             → DANS la fenêtre → l'émission démarre
                                  et se termine à 22h32

épisode long (2 h 50) :
22h45  branchement             → DANS la fenêtre → fin à 01h35
```

> **C'est peut-être exactement ce que veut l'auteur, et peut-être pas du tout.**
> Une fenêtre de rattrapage de deux heures cinquante n'est pas ce à quoi on pense
> en disant « rattrapée dans la limite de sa durée » — on l'imagine pour une
> émission d'une demi-heure.
>
> Le relevé ne tranche pas : la décision appartient à l'auteur, et il la prendra
> mieux avec ces chiffres qu'il ne l'a prise sans.

### 3.2 Ce que cela fait aux jingles (n°15)

Un épisode médian de 77 minutes fait **abandonner un à deux jingles horaires** ;
un épisode de 2 h 50 en fait abandonner trois. La décision n°15 tient — c'est ce
qu'elle prévoit — mais son ampleur est plus grande qu'un « de temps en temps ».

## 3.3 Le second flux : A la French, et ce qu'il révèle

| Mesure | LEGEND | A la French |
|---|---|---|
| Épisodes | 725 | **31** |
| `pubDate`, `duration`, `enclosure/url` | 0 manquant | **0 manquant** |
| `itunes:episodeType` | 724 `full`, 1 `trailer` | 30 `full`, **1 `bonus`** |
| Durées (min / médiane / max) | 1 / 77 / 170 min | 45 / **72** / 110 min |
| Écart annoncé ↔ servi | **+2 Mo** | **+350 octets** |

Trois enseignements que le premier flux ne pouvait pas donner :

### 3.3.1 L'insertion publicitaire varie énormément d'une émission à l'autre

+2 Mo chez LEGEND, +350 octets chez A la French. **Même hébergeur, même
mécanisme, deux ordres de grandeur d'écart.** On ne peut donc rien déduire d'un
flux pour un autre : `enclosure/length` reste inutilisable, mais la marge d'erreur
sur `duration` n'est pas une constante qu'on pourrait corriger.

### 3.3.2 `episodeType` n'a pas que `full` et `trailer`

A la French expose un **`bonus`** — et c'est **l'épisode le plus récent** :
*« Épisode BONUS : recap saison 1 et annonces »*, 45 min, 28 juillet 2026.

> Ma proposition de §1.1 — *ne retenir que les `full`* — écarterait donc
> aujourd'hui le dernier épisode publié au profit de celui du 7 juillet. Ce n'est
> plus une garde contre une bande-annonce d'une minute trente : c'est un choix
> éditorial. **Il remonte à l'auteur** (voir §3.4).

### 3.3.3 Un podcast entre deux saisons rejoue le même épisode

Le dernier épisode `full` de A la French date du **7 juillet 2026**, le bonus du
**28 juillet**. Nous sommes le **30 août** : l'émission est en pause.

Une case **chaque vendredi à 20 h** servirait donc, avec la décision n°14
(« le plus récent »), **le même épisode toutes les semaines** jusqu'à la reprise.

> **Ce n'est pas un défaut, c'est le comportement spécifié** — SPECS.md §4.11 le
> dit déjà : *« si le podcast n'a rien publié depuis, c'est le même épisode qui
> repasse — cela s'entend, et cela ne casse rien. »*
>
> Mais « cela s'entend » avait été écrit pour un podcast quotidien, où le cas est
> rare. Sur une émission hebdomadaire en pause, c'est le cas **nominal**, et il
> peut durer des mois. L'auteur doit le savoir avant que ça n'arrive.

## 3.4 Ce que ce relevé a fait trancher

Les deux questions qu'il a soulevées ont été tranchées par l'auteur le
2026-08-30 :

| Question | Réponse |
|---|---|
| Retenir les `bonus` ? | **Non — `full` seulement.** Un bonus n'est pas l'émission. *A la French* diffusera donc l'épisode du 7 juillet, pas le bonus du 28 |
| Un podcast en pause ? | **Ne pas rediffuser.** La case est sautée, la radio reste sur la musique |

> **La seconde a rouvert un choix fondateur.** Ne pas rediffuser exige de se
> souvenir de ce qui a été diffusé, et le projet n'avait **aucune** persistance.
> Il en acquiert une, délibérément bornée à un identifiant par émission
> (SPECS.md §4.11.1, ARCHITECTURE.md §5.0).
>
> C'est le relevé qui a rendu cette décision possible : sans les dates réelles,
> « le même épisode repasse » restait une phrase abstraite.

## 4. Quand ça se passe mal

Non observé pendant ce relevé : le flux a répondu à chaque appel, aucun épisode
n'était tronqué, aucune page HTML n'est apparue. Ces cas restent **dus**
(§5).

## 4.bis Les six flux d'une plage podcasts, et ce qu'ils coûtent (GOAL-077-T01, le 2026-09-06)

> Les six flux nommés par l'auteur, résolus par l'API de recherche d'Apple
> (`itunes.apple.com/lookup`) plutôt que devinés, puis passés à **notre propre
> adaptateur** `PodcastFeed` — seul juge qui compte, puisque c'est lui qui
> devra les lire. Taille par `curl`, coût complet (téléchargement et analyse)
> au meilleur de trois, depuis la machine de développement. La ligne « les
> six » est la **somme** des mesures individuelles : les six n'ont pas été lus
> d'affilée. Ces coûts varient d'un essai à l'autre — LEGEND a été mesuré à
> 0,13 s puis à 0,67 s pour la même taille — donc l'ordre de grandeur vaut,
> pas le chiffre.

| Flux | Hébergeur | Épisodes | Taille | Coût | Durée médiane |
|---|---|---|---|---|---|
| Les Grosses Têtes | Audiomeans | 102 | 339 Ko | 0,06 s | **6 min 09** |
| Entrez dans l'Histoire | Audiomeans | 101 | 449 Ko | 0,12 s | 20 min 31 |
| Small Talk — Konbini | Audiomeans | 105 | 886 Ko | 0,15 s | 1 h 01 |
| C dans l'air | Saooti / Octopus | 200 | 613 Ko | 0,40 s | 12 min 33 |
| LEGEND | Acast | 729 | 3,59 Mo | 0,67 s | 1 h 17 |
| HugoDécrypte — Actus | Acast | 1 894 | **15,68 Mo** | 0,47 s | 10 min 48 |
| **Les six** | trois hébergeurs | 3 131 | **21,6 Mo** | **~1,9 s** (somme) | |

### Ce que cela établit

**Trois hébergeurs, et les trois tiennent.** Audiomeans et Saooti n'avaient
jamais été relevés ; sur 3 131 épisodes, **aucun** n'est sans `itunes:duration`
ni sans `enclosure`. Ce que §1 et §2 disaient d'Acast vaut donc aussi pour eux,
sur ce que nous lisons. La convention « RSS avec des enclosure » n'est toujours
pas une norme, mais elle tient chez trois hébergeurs sur trois.

**Le coût est en octets, et il n'est plus négligeable.** ~21,6 Mo par jonction
de case, contre 3,9 Mo pour les deux flux d'avant. Et cette lecture est dans
`next_entry`, la requête que le diffuseur attend pour jouer (GOAL-075).

**Ce qui bornait cette lecture n'était pas sa taille, c'était `api_timeout`.**
Le diffuseur abandonne une requête au bout de 10 s et coupe au deuxième échec
(§3, radio.liq). Les flux étaient lus **l'un après l'autre**, chacun avec
`podcast.timeout_seconds` : trois flux à 15 s font 45 s dans le pire cas, et un
hébergeur qui absorbe les paquets — sans refuser ni répondre — suffisait à
faire couper l'antenne.

**Corrigé le 2026-09-06** : la radio ne sert que ce qu'elle a déjà lu, et la
lecture part dans un fil de fond (SPECS.md §4.11). Le produit `nombre de flux
× délai d'attente` n'a donc plus à tenir sous `api_timeout` — pour les
**podcasts**. Une chaîne YouTube, elle, se lit toujours dans la requête, et
`yt-dlp` s'y ajoute : c'est GOAL-081-T04.

**Les durées sont extrêmement hétérogènes** : de 6 minutes à 1 h 17 de médiane,
et jusqu'à 2 h pour l'épisode le plus récent de LEGEND. Une pioche uniforme
entre flux (SPECS.md §7 n°35) donnera donc des épisodes de longueurs très
inégales, et la n°5 — l'épisode entamé finit — fera déborder une plage de deux
heures d'autant plus souvent que LEGEND ou Small Talk sortent au tirage.

**« Les Grosses Têtes » n'est pas l'émission**, c'est le flux d'extraits :
6 minutes de médiane, un épisode par jour à 9 h. À dire à l'auteur, qui
attendait probablement les deux heures d'antenne.

---

## 5. Points incertains

**Établis** : le format du flux, la fiabilité de `pubDate` et de
`itunes:duration`, la récupération de l'audio, l'insertion publicitaire, et les
durées réelles.

**Restent ouverts :**

- [ ] **L'écart réel entre la durée annoncée et la durée servie.** Le `length`
      diffère de 2 % ; la durée l'est probablement aussi. Non mesuré : il
      faudrait décoder un épisode entier.
- [ ] Le comportement quand le flux **ne répond pas**, ou répond une page HTML
      en 200. Non observé — mais SPECS.md §4.11 en fait un cas nominal, donc le
      cas de test est dû (AGENTS.md §4).
- [ ] Un épisode annoncé dont le fichier a **disparu**. Non rencontré sur 725.
- [ ] La **stabilité des URL d'enclosure** : `livestitches` suggère qu'elles sont
      calculées à la demande. Une URL mise de côté vaut-elle encore une heure
      plus tard ?
- [x] ~~Ce relevé porte sur un seul flux, chez Acast.~~ **Trois hébergeurs
      relevés le 2026-09-06** (§4.bis) : Acast, Audiomeans, Saooti. Aucun
      épisode sans durée ni sans audio sur 3 131. Reste vrai qu'un quatrième
      hébergeur ne s'invente pas.
- [ ] **Le comportement d'Audiomeans et de Saooti quand ça se passe mal.** §4
      ne décrit que les pannes vues chez Acast. Les deux nouveaux n'ont été
      observés qu'en marche.
- [ ] **L'insertion publicitaire chez Audiomeans et Saooti.** §2.1 l'a mesurée
      chez Acast (écart de 2 % entre durée annoncée et servie). Non mesurée
      ailleurs : il faudrait décoder un épisode entier.

Aucun point n'a été remplacé par une supposition.
