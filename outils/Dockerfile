# syntax=docker/dockerfile:1

# ── L'atelier à jingles ────────────────────────────────────────────────────
# Rien à voir avec l'image de la radio : cette image-ci ne diffuse pas, elle
# FABRIQUE des fichiers, puis meurt (outils/README.md). Elle est construite à
# la demande par `outils/generer-jingles.sh`, jamais par docker-compose.
#
# Elle existe pour que la machine de l'auteur reste propre : ni venv, ni pistes
# intermédiaires, ni ffmpeg à jour à maintenir — seuls les mp3 finis sortent.
FROM python:3.13-slim

# ffmpeg synthétise le lit musical et fait le mixage ; edge-tts dit le texte.
# edge-tts est épinglé : il parle à une API non officielle, et une dérive
# silencieuse ne doit pas passer inaperçue le jour où elle casse.
RUN apt-get update \
 && apt-get install --no-install-recommends -y ffmpeg \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir edge-tts==7.2.3

# Le montage vit dans le conteneur, et disparaît avec lui.
ENV JINGLES_WORK=/tmp/montage \
    JINGLES_OUTPUT=/sortie

WORKDIR /atelier
COPY generer_jingles.py ./

# `-u` : la sortie du script arrive au fur et à mesure, pas à la fin.
ENTRYPOINT ["python", "-u", "generer_jingles.py"]
