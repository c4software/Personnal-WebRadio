# docs/podcast.md — Relevé des flux de podcast

> **Relevé établi le 2026-08-30** (`GOAL-002-T09`) contre le flux réellement
> voulu : **LEGEND**, `https://feeds.acast.com/public/shows/legend-1`, 725
> épisodes.
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

## 4. Quand ça se passe mal

Non observé pendant ce relevé : le flux a répondu à chaque appel, aucun épisode
n'était tronqué, aucune page HTML n'est apparue. Ces cas restent **dus**
(§5).

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
- [ ] Ce relevé porte sur **un seul flux**. Un second podcast, chez un autre
      hébergeur, n'aura pas les mêmes garanties — et « RSS avec des enclosure »
      reste une convention, pas une norme.

Aucun point n'a été remplacé par une supposition.
