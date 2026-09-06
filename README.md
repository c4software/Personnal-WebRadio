# Personnal WebRadio 

Une station de radio personnelle qui **n'existe que lorsqu'on l'écoute**.

Elle diffuse un flux HTTP audio unique, tiré au hasard dans une bibliothèque
servie en [Subsonic](https://www.subsonic.org/pages/api.jsp) — Navidrome
chez l'auteur —, ponctué de jingles horaires et
d'émissions programmées. Rien ne tourne tant que personne n'est branché : la
chaîne démarre à la première connexion et s'arrête à la dernière.

Deux auditeurs entendent la même chose au même instant. On ne choisit pas ce
qu'on écoute — on se branche, et **ça joue déjà**.

```
un auditeur se branche
        ↓
la chaîne démarre — la bibliothèque est interrogée, un morceau est tiré
        ↓
la musique joue en continu, sans blanc entre les morceaux
        ↓
à l'heure pile : un jingle
à l'heure dite : une émission remplace la programmation
selon l'heure : un genre plutôt qu'un autre
        ↓
« stop » pour passer · « encore » pour rester sur cet artiste
        ↓
le dernier auditeur se débranche → la chaîne s'arrête
```

---

## Ce qu'elle fait

| | |
|---|---|
| **Tirage aléatoire** | Dans toute la bibliothèque, avec une règle de non-répétition des artistes |
| **Grille horaire** | Tirage libre par défaut ; des plages par **genres** ou par **artiste** (« une heure d'un seul artiste »), ou **au hasard** (`random = "genre"` / `"artist"` : la radio tire le thème au début de la plage et s'y tient), restreignables à des **jours**, avec **générique d'ouverture et de fermeture** optionnels |
| **Modes d'enchaînement** | `mode` sur une plage, combinable au thème — ou seul, pour un tirage libre enchaîné : `"double_dose"` (chaque artiste tiré passe **deux titres à la suite**), `"era_fan"` (**2 à 6 titres d'une même décennie**), `"artist_fan"` (**3 à 6 titres du même artiste**). Le premier morceau tiré pose l'ancre, la suite se rompt d'elle-même quand elle s'épuise |
| **Plafond de durée** | Au-delà de `max_track_minutes` (20 min par défaut), une piste se joue mais **se coupe au plafond**, fondue vers la suite — un DJ set étiqueté « piste » ne monopolise pas l'antenne |
| **Programmes** | Une liste de lecture de la bibliothèque sur un créneau — « le vendredi de Chloé, 18 h–20 h » |
| **Jingles horaires** | `00h.mp3` … `23h.mp3`, insérés à la jonction sans couper un morceau, fondu court |
| **Émissions** | À heure dite : un **podcast** (l'épisode le plus récent non diffusé), une **plage de podcasts** (`feeds` et `end` : elle enchaîne les épisodes de plusieurs flux jusqu'à son heure de fin), une **chaîne YouTube** (la dernière vidéo, téléchargée en fond puis servie en local — zéro blanc), ou un **direct** — le flash France Info, capté et coupé à l'heure |
| **Pilotage** | `stop` **passe le morceau** à l'instant, et **passe un épisode d'une plage de podcasts en piochant un autre épisode** ; `encore` force le prochain **chez le même artiste**, et s'annonce par un jingle |
| **Apprentissage** | Les votes pèsent sur **l'artiste** (jamais deux fois) : redemandé revient plus, passé revient moins — et tout s'oublie en trois mois |
| **Une page web** | Quatre onglets — antenne (ce qui passe, **où il en est**, le **moment** en cours et l'**« À suivre »**), votes (effaçables), **planning de la semaine**, **historique** (24 h, paginé heure par heure) — l'onglet vit dans l'URL. Un lecteur en bas de page, avec la **liste des prochains titres** : ce qui est tiré d'avance, retirable d'un ✕, puis **la grille cousue derrière** — l'émission en cours et sa fin, celle qui suit, la plage qui reprend |
| **Une API** | Toute action y passe — l'interface web n'a aucun chemin privilégié |

## Ce qu'elle ne fait pas

- **Plusieurs flux ou qualités.** Un seul flux, un seul débit, un seul format.
- **Gérer la bibliothèque.** Elle *lit* la bibliothèque ; elle n'y écrit jamais rien.
- **Enregistrer, rejouer, podcaster.** Une radio est un présent continu : ce qui
  est passé est perdu, et c'est assumé. (Un **journal des titres** existe —
  qui est passé, à quelle heure, borné à 24 h — jamais l'audio.)

Détail et raisons : [SPECS.md §2](./SPECS.md).

---

## Installation

### Ce qu'il faut

- **Docker** et **Docker Compose** — c'est la façon prévue de la faire tourner
- Un serveur **compatible Subsonic** (Navidrome, par exemple) joignable, et
  ses identifiants
- Un dossier de **jingles** MP3 — facultatif, et même vide

Pour développer, en plus : **Python 3.11+** — et Docker sert aussi à valider le
script Liquidsoap contre la version épinglée (`./verifier.sh`).

### Configuration

Deux fichiers, et la frontière entre eux est nette : **les secrets d'un côté,
tout le reste de l'autre.**

```bash
cp .env.exemple .env               # les secrets
cp webradio.exemple.toml webradio.toml   # tout le reste
chmod 600 .env
```

`.env` ne porte **que** des secrets :

```dotenv
SUBSONIC_URL=http://music
SUBSONIC_UTILISATEUR=votre-utilisateur
SUBSONIC_MOT_DE_PASSE=votre-mot-de-passe
```

`webradio.toml` porte le reste, et **aucun secret** — un secret trouvé dedans
fait échouer le démarrage, délibérément.

> **Pourquoi les séparer.** Un fichier de configuration se relit, se compare, se
> colle dans un rapport, se montre à quelqu'un pour demander de l'aide. Un
> fichier qui contient un mot de passe ne peut rien de tout cela — et c'est ainsi
> qu'un secret finit par voyager.

### Les jingles

Le **nom du fichier est la programmation**. Le jingle de 14 h s'appelle
`hours/14h.mp3`, et il n'y a aucune table de correspondance à tenir à jour :

```
jingles/
├── hours/           les jingles horaires, dans leur tiroir
│   ├── 08h.mp3      diffusé à 8 h
│   ├── 20h.mp3      diffusé à 20 h
│   └── 20h-b.mp3    une VARIANTE : l'une des deux est tirée au hasard
├── encore.mp3       diffusé quand un « encore » est enregistré — le nom
│                    se change : [jingles] encore = "bravo.mp3" dans le TOML
└── chloe-debut.mp3  un générique — nom libre, sous-dossiers permis
```

**Un jingle absent n'est pas une erreur.** Le dossier peut n'en contenir que
deux ; les vingt-deux autres heures passent sans jingle et sans rien signaler.
On ajoute un jingle en déposant un fichier, on le retire en le supprimant.

### Lancer

Le Compose tire l'image du service `radio` publiée par la CI sur GHCR — le
dépôt est privé, il faut s'y être connecté une fois (`docker login ghcr.io`,
avec un token) :

```bash
docker compose up -d
docker compose logs -f
```

Puis, dans n'importe quel lecteur — VLC, un navigateur, une enceinte :

```
http://<la-machine>:8000/flux
```

Le flux est servi par **Liquidsoap** (second service du Compose) ; le noyau lui
dit quoi jouer, morceau par morceau. L'interface, elle, est sur un téléphone du
même réseau — **un autre port**, parce que c'est l'autre service :

```
http://<la-machine>:8080/
```

> **Si les conteneurs ne joignent pas le serveur Subsonic** : `http://music` est un nom résolu
> par le réseau de *l'hôte*, qu'un conteneur ne résout pas forcément. Décommentez
> `extra_hosts` dans `docker-compose.yml` — pour les **deux** services, `liquidsoap`
> ouvre les mêmes URL que `radio`.
>
> **`webradio.toml` doit être lisible par le conteneur** (`chmod 644`) : il tourne
> sans privilège. Et `folder` des jingles y vaut `/var/lib/local-webradio/jingles`,
> le chemin où le Compose les monte dans les deux services.
>
> **En conteneur, déclarez `liquidsoap.url = "http://liquidsoap:8000"`** : le
> défaut est `http://127.0.0.1:8000`, qui ne désigne pas le service voisin, et
> les ordres au diffuseur — `/skip`, `/skip-fresh`, `/requeue`, `/announce` —
> seraient journalisés en échec.

---

## Les émissions

Une émission est un épisode de podcast diffusé à heure dite. Elle **remplace** la
programmation pendant sa durée : ni grille, ni tirage, ni jingles.

Trois sources possibles — exactement une par émission :

```toml
# Un podcast : l'épisode « full » le plus récent non encore diffusé.
[[shows]]
name = "A la French"
feed = "https://feeds.acast.com/public/shows/a-la-french"
days = ["friday"]
time = "20:00"

# Une chaîne YouTube : la dernière vidéo non diffusée, téléchargée en tâche
# de fond (yt-dlp) pendant que la musique joue, servie en fichier local —
# jamais de blanc. Le cache s'écrase et s'efface tout seul.
[[shows]]
name    = "Hardisk"
youtube = "https://www.youtube.com/@hardisk"
days = ["wednesday"]
time = "20:00"

# Un DIRECT : capté pendant la case, coupé à l'heure de fin — c'est ainsi que
# passe le flash France Info. `duration_minutes` est obligatoire : un direct
# ne se termine pas seul, et il n'y a pas de rattrapage.
[[shows]]
name   = "Flash franceinfo"
stream = "https://icecast.radiofrance.fr/franceinfo-midfi.mp3"
duration_minutes = 9
days = "all"
time = "12:00"
```

Autant d'émissions que voulu, **mais jamais deux à la même heure le même jour** :
ce serait une erreur de configuration, et la radio refuserait de démarrer en les
nommant toutes les deux.

Ce qu'il faut savoir :

- On diffuse l'épisode **le plus récent qui n'a pas déjà été diffusé**. Si le
  podcast n'a rien publié de neuf, **la case est sautée** et la musique continue.
- Seuls les épisodes **réguliers** passent : les bonus et les bandes-annonces
  sont écartés.
- Une émission programmée **quand personne n'écoutait n'a pas eu lieu** — la
  radio n'existe que branchée. Elle est rattrapée si l'on se branche dans ce qui
  aurait été sa durée, et perdue au-delà.
- Une émission **ne coupe jamais** un morceau : elle commence à la jonction
  suivante.
- Une **plage de podcasts** se déclare avec `feeds` (plusieurs flux) et `end`
  (son heure de fin) : entre les deux, la radio tire un flux au hasard parmi
  ceux qui ont du neuf, joue son épisode, puis recommence. C'est la seule
  émission dont un `stop` passe l'épisode, faute de quoi il n'y a rien à mettre
  à la place (« Piloter »).

---

## Piloter

Deux gestes, depuis la page web ou directement par l'API.

| | |
|---|---|
| **`stop`** | **Passe le morceau en cours**, à l'instant, avec un fondu — et l'artiste pèsera un peu moins. Sur un **épisode d'une plage de podcasts**, il **pioche un autre épisode** : le diffuseur remplace son avance avant de sauter, la musique tenue d'avance ne passe donc pas |
| **`encore`** | Dès la fin de la chanson en cours : le jingle d'annonce, puis **un morceau du même artiste** — la chanson qui était prévue n'est pas perdue, elle passe juste après |

**Une voix suffit** : pas de quorum, l'effet est immédiat. Un `encore`
enregistré s'annonce par un jingle à la jonction suivante — `encore.mp3` par
défaut, personnalisable par `[jingles] encore = "…"` dans le TOML.

Ils sont disponibles en permanence, **sauf pendant un jingle, un flash ou une
émission** : on ne passe pas un flash, et on ne demande pas « encore » d'une
émission. La seule exception est l'épisode d'une plage de podcasts, que `stop`
passe — et là encore il est refusé quand aucun flux de la plage n'a plus
d'épisode neuf : « aucun autre épisode à piocher : l'épisode finit ». Un vote
refusé l'est **explicitement**, avec son motif : un refus muet ressemblerait à
une panne.

**Après un redémarrage du service `radio`**, l'antenne dit « inconnu » et refuse
les deux votes : le diffuseur n'annonce qu'au **début** d'une entrée, et le
processus neuf ne sait pas ce qui passe. Il le lui fait redire dès son premier
battement d'auditeurs, puis lui fait redemander son avance : les votes rouvrent,
avec la bonne nature, et l'avance décidée par le processus d'avant est
redécidée. Rien n'est coupé, et une plage de podcasts ne se retrouve pas avec de
la musique entre deux épisodes.

### Ce que la page montre

**Ce qui passe, et où il en est.** La carte « Antenne » et la barre du lecteur
portent une progression : l'écoulé et la durée d'un morceau (coupée au plafond),
d'un épisode de podcast quand son flux la déclare, d'un direct jusqu'à sa fin.
Une vidéo YouTube, un jingle ou un épisode sans durée n'annoncent que l'écoulé,
sans barre : la radio ne montre pas une avancée dont elle ignore la fin. La
position est celle du diffuseur, en avance de quelques secondes sur l'oreille,
le temps du tampon. Quand le téléphone le permet, l'écran de verrouillage la
reçoit aussi.

**Le moment, sauf pendant une émission.** La plage en cours se nomme — « Moment ·
Jazz, Soul » — avec, quand son thème a été tiré au sort, le bouton « Autre
thème ». Pendant une émission ou un flash, la plage est remplacée : la page ne
l'annonce pas, et « Autre thème » disparaît.

**Les prochains titres.** Le lecteur déploie la liste : les titres tirés
d'avance avec leur heure estimée, l'habillage prévu en italique, un ✕ pour
qu'un titre ne passe pas. Derrière le dernier titre, la liste **coud la
grille** — « Podcasts → 21:00 », « 21:00 Longs formats → 23:00 », « 23:00
Électronique » — jusqu'à l'horizon de `web.upcoming_horizon_minutes` (trois
heures par défaut, `0` pour ne rien coudre). Rien n'y est tiré de plus : c'est
une vue, elle ne décide rien.

### Ce que la radio retient

`stop` et `encore` sont enregistrés, et **pondèrent les tirages suivants** — sur
**l'artiste seul**, pour ne jamais compter double : un artiste souvent passé
revient moins souvent, un artiste souvent redemandé revient plus souvent. La
page Votes montre ce qui a été retenu, et un vote donné par erreur s'y efface
d'un ✕.

**Rien n'est jamais supprimé.** Un artiste passé cent fois reste dans la
bibliothèque et peut toujours sortir : sa chance descend à un quart, elle ne
s'annule pas. C'est la différence entre une radio qui apprend et une radio qui se
rétrécit.

Les votes **s'oublient** avec le temps — demi-vie de trois mois par défaut. Sans
cet oubli, la radio se figerait sur ce qu'on a cliqué le premier mois, et
finirait par pénaliser ce qu'on aime le plus : c'est ce qu'elle joue le plus,
donc ce qu'on passe le plus.

Ce n'est ni une note, ni des favoris, ni une liste noire, ni de la
recommandation. Un compteur, et une pondération du tirage.

---

## Développer

Ce dépôt est développé sous **Harness** : la documentation est la mémoire du
projet, et le travail avance par **Goals** découpés en tâches traçables.

| Fichier | Rôle |
|---|---|
| [AGENTS.md](./AGENTS.md) | Les règles de travail — à lire en premier |
| [SPECS.md](./SPECS.md) | Ce que la radio doit faire, et les décisions prises |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Comment elle est conçue, et ce qui existe vraiment |
| [TASKS.md](./TASKS.md) | Où en est le travail |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Comment contribuer |
| [docs/](./docs/) | Subsonic, Liquidsoap, ffmpeg, podcasts, lecteurs — **relevés par observation** |

Commandes de pilotage : `/status`, `/goal <objectif>`, `/task [ID]`, `/verify`.

### Mise en place

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

### Vérifier

```bash
./verifier.sh
```

Des contrôles enchaînés du moins cher au plus cher, qui **s'arrêtent au premier
échec** : mise en forme, analyse statique, types, **les interdits
d'AGENTS.md §2**, la validation du script Liquidsoap contre l'image épinglée,
puis tests et couverture. Le détail est en [AGENTS.md §5.2](./AGENTS.md).

> `./verifier.sh` tourne **hors conteneur**, sur le code. Un conteneur qui
> démarre ne prouve rien sur la qualité de ce qu'il contient.

Ce que la vérification n'entendra jamais — le son, les transitions, la tenue
dans la durée, les vrais lecteurs — s'écoute avant de committer :
[AGENTS.md §4.1](./AGENTS.md).

---

## Licence

[MIT](./LICENSE).
