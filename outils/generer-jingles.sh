#!/usr/bin/env bash
# Fabrique les génériques de plage dans un conteneur jetable.
#
# Rien ne s'installe sur la machine : ni venv, ni ffmpeg, ni pistes
# intermédiaires. Seuls les mp3 finis sortent, dans `jingles/bands/`, et ils
# appartiennent à l'utilisateur courant — pas à root.
#
#   ./outils/generer-jingles.sh              # toute la série
#   ./outils/generer-jingles.sh matinale     # un seul générique
set -euo pipefail

racine="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="local-webradio-jingles"
sortie="$racine/jingles/bands"

mkdir -p "$sortie"

echo "── construction de l'atelier ─────────────────────────────"
docker build -t "$image" "$racine/outils"

echo "── fabrication ───────────────────────────────────────────"
# --user : les fichiers produits appartiennent à celui qui a lancé la commande.
# --rm   : le conteneur, son venv et son montage disparaissent en sortant.
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "$sortie:/sortie" \
  "$image" "$@"
