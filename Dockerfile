# syntax=docker/dockerfile:1

# ── L'application ──────────────────────────────────────────────────────────
# Plus de ffmpeg ici : Liquidsoap décode et encode dans son propre conteneur,
# épinglé dans docker-compose.yml (docs/liquidsoap.md).
FROM python:3.13-slim AS runtime

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

# 8080 : l'interface, l'API, et les deux routes que Liquidsoap appelle. Le flux
# n'est PAS servi par ce conteneur : c'est le service `liquidsoap` de
# docker-compose.yml (ARCHITECTURE.md §4). Le port réellement écouté vient du
# TOML — celui-ci est une déclaration, pas une configuration (SPECS.md §6).
EXPOSE 8080

# exec form, donc PID 1 est Python et reçoit SIGTERM directement. Sans cela,
# un shell intermédiaire l'avalerait et Docker tuerait brutalement au bout de
# dix secondes (ARCHITECTURE.md §8.5, GOAL-011-T05).
ENTRYPOINT ["local-webradio"]
CMD ["--config", "/etc/local-webradio/webradio.toml"]
