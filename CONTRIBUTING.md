# CONTRIBUTING.md

## Avant de commencer

Lire [AGENTS.md](./AGENTS.md). C'est le contrat de travail, et il vaut pour les
contributeurs humains autant que pour les agents.

Puis, selon ce que vous touchez : [SPECS.md](./SPECS.md) pour un comportement
audible, [ARCHITECTURE.md](./ARCHITECTURE.md) pour une décision technique,
[TASKS.md](./TASKS.md) pour savoir où en est le travail, et le relevé
correspondant dans [docs/](./docs/) si vous touchez à Subsonic, au flash
France Info, à Liquidsoap, à ffmpeg ou à ce qu'attendent les lecteurs de webradio.

## Mettre en place l'environnement

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
```

Il faut par ailleurs **Docker** sur la machine (pour valider le script
Liquidsoap contre la version épinglée), et un serveur **compatible Subsonic**
joignable.

Pour faire tourner la station avec **le code en cours** — `docker-compose.yml`
tire l'image publiée, pas votre copie de travail — ajouter la surcharge de
développement :

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

```bash
cp .env.exemple .env      # puis y mettre vos identifiants
chmod 600 .env
```

`.env` porte **les secrets et rien d'autre**. Tout le reste — dossier des
jingles, grille horaire, émissions, seuils — va dans le TOML local, lui aussi
non versionné (SPECS.md §6).

## Le cycle d'une contribution

1. Prendre une tâche de [TASKS.md](./TASKS.md), ou en ouvrir une.
2. La passer à `[-]`.
3. Implémenter **cette tâche uniquement**, tests dans le même incrément.
4. Lancer la vérification, et **regarder sa sortie** :

   ```bash
   ./verifier.sh
   ```

   Pour corriger la mise en forme : `ruff format . && ruff check --fix .`

5. **Si la tâche touche au son, aux transitions, à la durée ou aux lecteurs**
   (AGENTS.md §4.1) : écouter réellement la radio, et écrire dans le commit ce
   qui a été entendu. Aucun test ne le fera à votre place.
6. Mettre à jour la documentation impactée (AGENTS.md §6).
7. Passer la tâche à `[x]`, committer au format
   [Conventional Commits](https://www.conventionalcommits.org/) en référençant
   l'identifiant de la tâche.

Une contribution dont la vérification échoue n'est pas terminée. Ne jamais
annoncer un succès non observé.

## Ce qui fait refuser une contribution

- Une fonctionnalité sans ses tests.
- Un appel réseau, un `subprocess` ou une ouverture de fichier dans
  `webradio/core/`.
- Un `import` de `flask` ou `jinja2` hors de `webradio/adapters/web/`.
- Une route Flask ou un gabarit Jinja2 qui appelle le noyau sans passer par
  l'API.
- Un `datetime.now()` ou un `random.` hors de `core/clock.py` et `core/rng.py`.
- Une URL, un chemin, un port ou une durée écrits en dur plutôt que lus du TOML.
- Un `except:` nu, un `except Exception: pass`, un `print()`.
- Un `TODO` sans tâche correspondante.
- Un comportement audible ajouté sans mise à jour de `SPECS.md`.
- Un secret hors de `.env` — dans le TOML, dans un test, dans un exemple.
- `.env`, le TOML local ou un fichier audio committé.
