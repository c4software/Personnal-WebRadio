# syntax=docker/dockerfile:1

# ── ffmpeg, épinglé ────────────────────────────────────────────────────────
# docs/ffmpeg.md s'ouvre sur « tout ce qui suit doit être vérifié contre cette
# version ». C'est la raison d'être de ce conteneur : figer ffmpeg avec le code
# qui l'a relevé, au lieu de dépendre de ce que la machine hôte a installé.
#
# 9.0.1 n'est pas un choix : c'est la version contre laquelle le relevé a été
# établi. Un premier essai en 7.1 a produit exactement ce que ce conteneur
# devait empêcher — figer la MAUVAISE version.
#
# On copie un binaire statique depuis une image versionnée plutôt que d'installer
# le paquet de la distribution : celui-ci change au gré des mises à jour de base,
# et ferait dériver la version sans prévenir.
FROM mwader/static-ffmpeg:9.0.1 AS ffmpeg

# ── L'application ──────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

COPY --from=ffmpeg /ffmpeg /ffprobe /usr/local/bin/

# Un utilisateur sans privilège : le conteneur ne doit écrire que dans le
# volume d'état (ARCHITECTURE.md §8.5.3).
RUN useradd --system --create-home --uid 10001 radio

WORKDIR /app

# Les dépendances d'abord, le code ensuite : une modification du code ne doit
# pas invalider le cache d'installation.
COPY pyproject.toml README.md ./
COPY webradio ./webradio
RUN pip install --no-cache-dir --no-compile .

# Le volume d'état appartient à l'utilisateur : c'est le seul endroit où
# l'application écrit.
RUN mkdir -p /var/lib/local-webradio && chown radio:radio /var/lib/local-webradio

USER radio

# 8000 : le flux. 8080 : l'interface et l'API. Ce sont DEUX serveurs, et ils ne
# peuvent pas écouter le même port. Les ports réellement écoutés viennent du
# TOML — ceux-ci sont une déclaration, pas une configuration (SPECS.md §6).
EXPOSE 8000 8080

# exec form, donc PID 1 est Python et reçoit SIGTERM directement. Sans cela,
# un shell intermédiaire l'avalerait, Docker tuerait brutalement au bout de dix
# secondes, et l'on retrouverait les orphelins de GOAL-004-T06 — cette fois
# invisibles (ARCHITECTURE.md §8.5, GOAL-011-T05).
ENTRYPOINT ["local-webradio"]
CMD ["--config", "/etc/local-webradio/webradio.toml"]
