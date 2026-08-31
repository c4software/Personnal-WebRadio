# docs/subsonic.md — Relevé de l'API Subsonic telle que Navidrome l'implémente

> **Relevé établi le 2026-08-30** (`GOAL-002-T08`), contre l'instance de
> l'auteur : **Navidrome 0.63.2**, API Subsonic 1.16.1.
>
> **Aucun identifiant ne figure dans ce fichier**, ni dans aucun commit : ils
> vivent dans le TOML local, non versionné.
> `GOAL-002` devra répondre **par observation**, contre un vrai serveur.
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'un
> endpoint**, et ne jamais l'inférer d'une implémentation existante de ce dépôt.
> La spécification Subsonic établit l'usage ; **ce que Navidrome renvoie
> réellement fait foi**.

Références de départ :

- API Subsonic : <https://www.subsonic.org/pages/api.jsp>
- Navidrome : <https://www.navidrome.org/docs/developers/subsonic-api/>

---

## 1. Authentification — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T08`) contre l'instance de l'auteur.
> **Navidrome 0.63.2**, API Subsonic annoncée **1.16.1**.
>
> Aucun identifiant ne figure ici ni dans aucun commit : ils vivent dans le TOML
> local, non versionné (AGENTS.md §7).

**Les trois formes d'authentification fonctionnent** — jeton dérivé `t`+`s`, mot
de passe en clair `p`, et `p=enc:<hex>`. Le projet retiendra **le jeton dérivé** :
c'est la seule qui ne fait pas circuler le mot de passe, et elle ne coûte rien.

Paramètres acceptés : `u`, `v=1.16.1`, `c=local-webradio`, `f=json`.

### 1.1 Le piège, et il est confirmé

**Une authentification refusée renvoie `HTTP 200`.**

```
mot de passe faux → HTTP 200
                    { "subsonic-response": { "status": "failed",
                                             "error": { "code": 40,
                                                        "message": "Wrong username or password" } } }
```

> **Conséquence pour l'adaptateur** : le code HTTP ne dit rien. Il faut lire
> `status` dans le corps, **à chaque appel**, avant de regarder les données. Un
> client qui se fierait au code HTTP prendrait un refus d'authentification pour
> une réponse valide et vide — et la radio conclurait « bibliothèque vide » au
> lieu de « mot de passe faux ».

## 2. Trouver de la musique — **relevé**

### 2.1 `getRandomSongs` existe, et il tronque en silence

| `size` demandé | Rendus |
|---|---|
| 1 | 1 |
| 10 | 10 |
| 500 | 500 |
| **501** | **500** — `status: ok`, aucune erreur |

**Le plafond est 500, et le dépassement est silencieux.** Demander davantage ne
lève rien : on croit avoir demandé 1000 pistes, on en a 500.

### 2.2 Le filtre par genre fonctionne

- `getRandomSongs&genre=<nom>` rend bien des pistes de ce genre, et d'aucun autre.
- **Un genre inexistant rend `status: ok` et zéro piste**, pas une erreur.

> C'est exactement ce que `SourceMusicale.pistes()` avait supposé
> (`webradio/core/sources.py`) : *« une source qui ne connaît pas le genre
> demandé rend une liste vide plutôt que de lever »*. La supposition est
> confirmée, et le repli sur le tirage libre reste décidé au-dessus
> (SPECS.md §4.4).

### 2.3 La bibliothèque réelle : 262 genres

Les plus fournis : *Chanson française* (1280 titres), *Rap français* (426),
*Rock* (357), *Reprise* (290), *Pop* (277), *French Music* (275).

> **262 genres est beaucoup**, et les noms se recouvrent (« Pop » et « French
> Music », « Chanson française » et « Reprise »). La grille thématique de
> SPECS.md §4.4 devra probablement viser des **ensembles** de genres plutôt
> qu'un genre unique — ce que la spécification prévoyait déjà.

### 2.4 Le tirage serveur suffit-il ?

**Non, et c'est décidé.** `getRandomSongs` ne sait rien de ce qui vient de
passer : il ne peut pas garantir la non-répétition de SPECS.md §4.2.

Le noyau tire donc lui-même (`core/rng.py`) parmi des pistes obtenues du serveur.
`getRandomSongs` reste utile pour **échantillonner** une grande bibliothèque sans
la rapatrier entière.

### 2.5 Les autres pistes d'un artiste — ce dont `encore` dépend

`search3&query=<artiste>&songCount=50` fonctionne, **mais ramène aussi d'autres
artistes** : sur 50 résultats pour un artiste, 49 étaient de lui, 1 non.

> **L'adaptateur doit filtrer sur l'égalité exacte du nom d'artiste.** Sans ce
> filtre, `encore` servirait parfois un autre artiste — précisément ce que
> l'auditeur n'a pas demandé.

## 2.6 Les listes de lecture — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T08`, complété pour `GOAL-013`).

`getPlaylists` rend les listes de l'utilisateur : identifiant, nom, `songCount`,
`duration`. `getPlaylist&id=<id>` rend les entrées, dans le même format qu'une
piste ordinaire — `id`, `title`, `artist`, `genre`, `duration`, `suffix`.

Sur l'instance de l'auteur, trois listes : 67, 26 et 19 morceaux annoncés.

### 2.6.1 `songCount` et le nombre d'entrées peuvent diverger

| Liste | `songCount` annoncé | Entrées rendues |
|---|---|---|
| A | **67** | **32** |
| B | 26 | 26 |
| C | 19 | 19 |

Trente-cinq morceaux manquent à l'appel sur la première, et les identifiants
rendus sont bien tous distincts — ce n'est pas un doublon compté deux fois.

**La cause n'a pas été établie.** L'hypothèse la plus probable est que
`songCount` compte les entrées de la liste tandis que `getPlaylist` ne rend que
celles dont le fichier existe encore ; elle n'est **pas vérifiée**, et ce relevé
ne la présente pas comme un fait.

> **La conduite à tenir ne dépend pas de la cause** : **ne jamais se fier à
> `songCount`.** Ce qui compte est ce que `getPlaylist` rend réellement. Une
> liste « vide » se juge sur ses entrées, pas sur son compteur.

### 2.6.2 `getRandomSongs&playlistId` est **ignoré en silence**

Le paramètre n'existe pas dans la spécification Subsonic. L'essayer ne provoque
aucune erreur : `status: ok`, et vingt morceaux rendus.

**Aucun des vingt n'appartenait à la liste demandée.**

```
liste demandée : 32 morceaux connus
20 tirés avec playlistId → 0 appartiennent à la liste
```

> C'est le piège de cette API sous sa forme la plus pure : un paramètre inconnu
> est ignoré, la réponse reste `ok`, et l'on croit avoir filtré. **Le tirage
> dans une liste se fait donc chez nous**, sur les entrées récupérées — ce qui
> est de toute façon ce que le noyau sait faire (`core/rng.py`).

### 2.6.3 Une liste inexistante

`HTTP 200`, `status: failed`, code **70**, « playlist not found » — même régime
que pour une piste inexistante (§5).

## 3. Récupérer le son — **relevé**

`stream`, `stream&format=raw` et `download` rendent **tous les trois** le même
`Content-Type: audio/mpeg` et la même `Content-Length` sur cette instance : aucun
transcodage serveur n'est appliqué par défaut.

`Content-Length` est présent, donc la taille est connue d'avance.

### 3.1 Le constat qui valide la décision n°11

Sur un échantillon de **200 pistes** :

| | |
|---|---|
| Formats | `mp3` × 199, **`m4a` × 1** |
| Débits | 320 (94), 128 (79), 160 (6), 96 (2), 222 (2), 193 (1) |
| **Bibliothèque homogène ?** | **NON** |

> **La voie « transmettre tel quel » était impossible dès le départ.** Six débits
> différents et deux conteneurs : un chemin de copie sans réencodage aurait
> produit un flux dont le format change en cours de route, et la seule pièce à
> conviction de [flux-icy.md](./flux-icy.md) §3 dit qu'un lecteur lit ses
> en-têtes une fois.
>
> SPECS.md §7 n°11 avait tranché *sans coupure > lisible partout > économie*, et
> [ffmpeg.md](./ffmpeg.md) §2.bis avait montré que le réencodage permanent coûte
> 1 % d'un cœur. **Ce relevé-ci montre que l'alternative n'existait même pas.**

## 4. Les métadonnées — **relevé**

Sur les mêmes 200 pistes :

| Champ | Manquant |
|---|---|
| `id`, `title`, `artist`, `duration`, `suffix`, `bitRate` | **0 / 200** |
| **`genre`** | **37 / 200** — près d'une sur cinq |

> **`duration` est toujours présent** : la programmation des jingles peut s'y
> fier, et le refus d'une durée nulle posé dans `core/modeles.py` reste une
> garde, pas un cas courant.
>
> **`genre` manque une fois sur cinq.** SPECS.md §4.2 l'avait déjà autorisé —
> *« une bibliothèque réelle a des morceaux sans étiquette »* — et
> `core/modeles.py` accepte `genre=None`. La décision est confirmée par les
> chiffres : refuser ces pistes aurait amputé la radio de 18 % de la
> bibliothèque.

## 5. Quand ça se passe mal — **relevé**

| Situation | Réponse |
|---|---|
| Identifiant inexistant | **HTTP 200**, `status: failed`, code **70**, « Song not found » |
| Paramètre obligatoire absent | **HTTP 200**, `status: failed`, code **70** |
| Endpoint inconnu | **HTTP 404** — pas de corps Subsonic |
| `f=xml` demandé | XML rendu : le format demandé est honoré |

**Deux régimes distincts, et l'adaptateur doit gérer les deux** : une erreur
*applicative* arrive en HTTP 200 avec un code dans le corps ; une erreur *de
routage* arrive en HTTP 404 sans corps Subsonic. Un client qui ne parserait que
le JSON s'étoufferait sur le second.

**Non observé, donc non écarté** : une page HTML rendue à la place du JSON. Elle
n'est pas apparue ici, mais un proxy placé devant le serveur la produirait. Le
cas de test reste obligatoire (AGENTS.md §4).

## 6. Points incertains

**Établis** : authentification et son piège, tirage et sa troncature, filtre par
genre, pistes d'un artiste, récupération du son, complétude des métadonnées, et
les deux régimes d'erreur.

**Restent ouverts :**

- [ ] Le comportement **pendant une analyse de bibliothèque** en cours. Non
      observé : aucune analyse n'a eu lieu pendant le relevé.
- [ ] Une **page HTML** rendue à la place du JSON — non apparue ici, mais un
      proxy placé devant le serveur la produirait. Le cas de test reste dû.
- [ ] Une **limite de débit** côté serveur. Non observée sur quelques dizaines
      d'appels ; une radio en interroge davantage sur une soirée.
- [ ] La **stabilité des identifiants** entre deux analyses de bibliothèque.
      Non vérifiable en une session.
- [ ] Le comportement de `stream` sur les rares fichiers **`m4a`** : un seul est
      apparu dans l'échantillon, et il n'a pas été récupéré.

Aucun point n'a été remplacé par une supposition.
