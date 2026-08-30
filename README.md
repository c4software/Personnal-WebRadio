# Personnal WebRadio 

Une station de radio personnelle qui **n'existe que lorsqu'on l'écoute**.

Elle diffuse un flux HTTP audio unique, tiré au hasard dans une bibliothèque
[Navidrome](https://www.navidrome.org/), ponctué de jingles horaires et
d'émissions programmées. Rien ne tourne tant que personne n'est branché : la
chaîne démarre à la première connexion et s'arrête à la dernière.

Deux auditeurs entendent la même chose au même instant. On ne choisit pas ce
qu'on écoute — on se branche, et **ça joue déjà**.

```
un auditeur se branche
        ↓
la chaîne démarre — Navidrome est interrogé, un morceau est tiré
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
| **Grille horaire** | Tirage libre par défaut ; des plages par **genres** ou par **artiste** (« une heure d'un seul artiste »), restreignables à des **jours**, avec **générique d'ouverture et de fermeture** optionnels |
| **Programmes** | Une liste de lecture Navidrome sur un créneau — « le vendredi de Chloé, 18 h–20 h » |
| **Jingles horaires** | `00h.mp3` … `23h.mp3`, insérés à la jonction sans couper un morceau, fondu court |
| **Émissions** | À heure dite : un **podcast** (l'épisode le plus récent non diffusé), une **chaîne YouTube** (la dernière vidéo, téléchargée en fond puis servie en local — zéro blanc), ou un **direct** — le flash France Info, capté et coupé à l'heure |
| **Pilotage** | `stop` **passe le morceau** à l'instant ; `encore` force le prochain **chez le même artiste**, et s'annonce par un jingle |
| **Apprentissage** | Les votes pèsent sur **l'artiste** (jamais deux fois) : redemandé revient plus, passé revient moins — et tout s'oublie en trois mois |
| **Une page web** | Quatre onglets — antenne (avec le **moment** en cours), votes (effaçables), **planning de la semaine**, **historique** — l'onglet vit dans l'URL |
| **Une API** | Toute action y passe — l'interface web n'a aucun chemin privilégié |

## Ce qu'elle ne fait pas

- **Plusieurs flux ou qualités.** Un seul flux, un seul débit, un seul format.
- **Gérer la bibliothèque.** Elle *lit* Navidrome ; elle n'y écrit jamais rien.
- **Enregistrer, rejouer, podcaster.** Une radio est un présent continu : ce qui
  est passé est perdu, et c'est assumé. (Un **journal des titres** existe — qui
  est passé, à quelle heure — jamais l'audio.)

Détail et raisons : [SPECS.md §2](./SPECS.md).

---

## Installation

### Ce qu'il faut

- **Docker** et **Docker Compose** — c'est la façon prévue de la faire tourner
- Un serveur **Navidrome** joignable, et ses identifiants
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
NAVIDROME_URL=http://music
NAVIDROME_UTILISATEUR=votre-utilisateur
NAVIDROME_MOT_DE_PASSE=votre-mot-de-passe
```

`webradio.toml` porte le reste, et **aucun secret** — un secret trouvé dedans
fait échouer le démarrage, délibérément.

> **Pourquoi les séparer.** Un fichier de configuration se relit, se compare, se
> colle dans un rapport, se montre à quelqu'un pour demander de l'aide. Un
> fichier qui contient un mot de passe ne peut rien de tout cela — et c'est ainsi
> qu'un secret finit par voyager.

### Les jingles

Le **nom du fichier est la programmation**. Le jingle de 14 h s'appelle
`14h.mp3`, et il n'y a aucune table de correspondance à tenir à jour :

```
jingles/
├── 08h.mp3      diffusé à 8 h
├── 20h.mp3      diffusé à 20 h
└── encore.mp3   diffusé quand un « encore » est enregistré
```

**Un jingle absent n'est pas une erreur.** Le dossier peut n'en contenir que
deux ; les vingt-deux autres heures passent sans jingle et sans rien signaler.
On ajoute un jingle en déposant un fichier, on le retire en le supprimant.

### Lancer

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

> **Si les conteneurs ne joignent pas Navidrome** : `http://music` est un nom résolu
> par le réseau de *l'hôte*, qu'un conteneur ne résout pas forcément. Décommentez
> `extra_hosts` dans `docker-compose.yml` — pour les **deux** services, `liquidsoap`
> ouvre les mêmes URL que `radio`.
>
> **`webradio.toml` doit être lisible par le conteneur** (`chmod 644`) : il tourne
> sans privilège. Et `folder` des jingles y vaut `/var/lib/local-webradio/jingles`,
> le chemin où le Compose les monte dans les deux services.

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
days = ["vendredi"]
time = "20:00"

# Une chaîne YouTube : la dernière vidéo non diffusée, téléchargée en tâche
# de fond (yt-dlp) pendant que la musique joue, servie en fichier local —
# jamais de blanc. Le cache s'écrase et s'efface tout seul.
[[shows]]
name    = "Hardisk"
youtube = "https://www.youtube.com/@hardisk"
days = ["mercredi"]
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

---

## Piloter

Deux gestes, depuis la page web ou directement par l'API.

| | |
|---|---|
| **`stop`** | **Passe le morceau en cours**, à l'instant, avec un fondu — et l'artiste pèsera un peu moins |
| **`encore`** | Le prochain morceau est **du même artiste** (à défaut du même genre) — et l'artiste pèsera un peu plus |

**Une voix suffit** : pas de quorum, l'effet est immédiat. Un `encore`
enregistré s'annonce par le jingle `encore.mp3` à la jonction suivante.

Ils sont disponibles en permanence, **sauf pendant un jingle ou une émission** —
on ne passe pas une émission. Un vote reçu à ce moment-là est refusé
explicitement, avec son motif : un refus muet ressemblerait à une panne.

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
| [docs/](./docs/) | Navidrome, Liquidsoap, ffmpeg, podcasts, lecteurs — **relevés par observation** |

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

Cinq contrôles, du moins cher au plus cher, qui **s'arrêtent au premier échec** :
mise en forme, analyse statique, types, **les interdits d'AGENTS.md §2**, puis
tests et couverture.

Le quatrième est ce qui distingue ce script d'un `make check` : il transforme les
interdits en recherches exécutées. Un interdit que rien ne contrôle n'est pas un
interdit, c'est un vœu — et il finit toujours par être enfreint, de bonne foi.

> `./verifier.sh` tourne **hors conteneur**, sur le code. Un conteneur qui
> démarre ne prouve rien sur la qualité de ce qu'il contient.

### Les relevés

`docs/` ne contient pas de la documentation recopiée : ce sont des **constats**,
établis contre les vraies dépendances, avec leur date. La règle qui les
accompagne n'a pas d'exception :

> **Ne jamais inventer le comportement d'une dépendance externe**, et ne jamais
> l'inférer d'une implémentation existante de ce dépôt.

Ils ont déjà évité des erreurs coûteuses — que la bibliothèque soit hétérogène
rendait impossible la voie qui semblait la plus économe, et qu'un mot de passe
faux revienne en HTTP 200 aurait fait conclure « bibliothèque vide ».

### Ce qu'aucun test ne verra

Cinq choses ne se constatent **qu'en écoutant** : le son lui-même, les
transitions, la tenue dans la durée, le comportement des vrais lecteurs, et
l'effet de la pondération.

Personne ne les détecte automatiquement. Celui qui touche à ces zones **écoute
réellement la radio avant de committer** — c'est le seul filet, et il n'est pas
automatique. Voir [AGENTS.md §4.1](./AGENTS.md).

---

## Licence

Non déterminée — tous droits réservés par défaut. Projet personnel.
