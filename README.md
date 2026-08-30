# local-webradio

Une station de radio personnelle qui **n'existe que lorsqu'on l'écoute**.

Elle diffuse un flux HTTP audio unique, tiré au hasard dans une bibliothèque
[Navidrome](https://www.navidrome.org/), ponctué de jingles horaires et de flashs
d'information. Rien ne tourne tant que personne n'est branché : la chaîne démarre
à la première connexion et s'arrête à la dernière.

Deux auditeurs entendent la même chose au même instant. On ne choisit pas ce
qu'on écoute — on se branche, et ça joue déjà.

## Ce qu'elle fait

- **Tirage aléatoire** dans la bibliothèque, avec une règle de non-répétition des
  artistes
- **Grille horaire** : tirage libre par défaut, genres imposés sur des plages
  déclarées
- **Jingles horaires** en MP3, insérés à la jonction sans couper un morceau
- **Flashs France Info** aux heures choisies, avec repli sur la musique s'ils
  manquent
- **Pilotage** : `stop` pour passer, `encore` pour rester sur l'artiste — ou à
  défaut sur le genre. Un « encore » enregistré **s'entend** : une brève note est
  diffusée dans le flux
- **Une page web** — ce qui passe, et deux boutons — servie par Flask, mise en
  page en Jinja2, faite pour un téléphone posé à côté de l'enceinte
- **Toute action passe par une API**, jamais par un chemin réservé à l'interface
- **Un flux lisible par n'importe quel lecteur de webradio**, sans coupure, et
  transcodant le moins possible
- **Tout en TOML** : aucune URL, aucun chemin, aucune durée dans le code. Seule
  exception, les jingles, dont le nom porte l'heure : `00h.mp3` … `23h.mp3`

## Ce qu'elle ne fait pas

Plusieurs flux ou qualités · gérer la bibliothèque (elle lit Navidrome, elle
n'y écrit jamais) · enregistrer, rejouer ou podcaster. Voir
[SPECS.md §2](./SPECS.md).

## Installation

> **Le code n'existe pas encore.** Le projet en est à la Phase 0 — voir
> [TASKS.md](./TASKS.md). Cette section sera remplie par `GOAL-001`.

Il faudra : Python 3.11+, **ffmpeg**, un serveur Navidrome joignable, et un
dossier de jingles MP3 nommés `00h.mp3` à `23h.mp3` — tous facultatifs, une
heure sans jingle passe sans rien signaler.

## Développement

Ce dépôt est développé sous **Harness** : la documentation est la mémoire du
projet, et le travail avance par **Goals** découpés en tâches traçables.

| Fichier | Rôle |
|---|---|
| [AGENTS.md](./AGENTS.md) | Les règles de travail |
| [SPECS.md](./SPECS.md) | Ce que la radio doit faire |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Comment elle est conçue |
| [TASKS.md](./TASKS.md) | Où en est le travail |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Comment contribuer |
| [docs/](./docs/) | Navidrome, France Info, ffmpeg, lecteurs de webradio — relevés par observation |

Commandes de pilotage : `/status`, `/goal <objectif>`, `/task [ID]`, `/verify`.

Vérification avant tout commit :

```bash
ruff format --check . && ruff check . && mypy . && pytest --cov --cov-fail-under=80
```

## Licence

Non déterminée. Projet personnel, non destiné à la publication en l'état.
