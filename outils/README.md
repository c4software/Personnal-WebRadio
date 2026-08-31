# `outils/` — ce qui fabrique des fichiers, pas ce qui les diffuse

Rien ici n'est importé par la radio. Ce sont des scripts qu'on lance **à la
main**, dont le résultat est un fichier posé sur le disque. La radio, elle, ne
connaît que le fichier.

C'est pourquoi ce dossier est hors de `webradio/` : il ne suit ni l'architecture
hexagonale (ARCHITECTURE.md §1), ni l'injection de l'horloge et du hasard, et il
a le droit d'appeler des programmes extérieurs comme bon lui semble. Il reste
tenu par la mise en forme et l'analyse statique de `./verifier.sh`, moins la
règle « pas de `print` » — un outil hors ligne parle sur la sortie standard,
c'est son interface.

**Tout s'exécute en conteneur.** Ces outils installent des dépendances que la
radio n'a pas, et il n'y a aucune raison qu'elles atterrissent sur la machine de
l'auteur. Chaque script s'occupe de construire son image et de la lancer : rien
à installer, rien à nettoyer, et rien qui traîne entre deux exécutions.

---

## `generer_jingles.py` — les génériques de plage

Fabrique les quinze `intro` déclarés par les plages thématiques de
`webradio.toml`, dans `jingles/bands/` : une voix de synthèse française sur un
lit musical synthétisé, mixés comme un habillage de station.

### Ce dont il a besoin

**Docker, et rien d'autre.** Les deux dépendances vivent dans l'image décrite par
`outils/Dockerfile`, construite à la demande :

| Outil | Pourquoi |
|---|---|
| `ffmpeg` | synthèse du lit musical, mixage, normalisation |
| `edge-tts` | la voix — service de lecture d'Edge, **gratuit, sans compte ni clé** |

L'image n'a rien à voir avec celle de la radio : elle ne diffuse pas, elle
fabrique. `docker-compose.yml` ne la connaît pas, et ne doit pas la connaître —
un atelier n'est pas un service.

> **Pourquoi pas une voix locale, ni un service payant.** `espeak` et consorts
> sonnent le robot, et personne ne veut ça toutes les deux heures sur sa radio.
> Google Cloud TTS et ElevenLabs font mieux, mais exigent un compte facturable
> pour quinze phrases par an. Edge donne des voix neuronales de même famille
> qu'Azure, sans clé. La contrepartie est qu'il s'appuie sur une **API non
> officielle** : le jour où elle change, ce script casse — et la radio, non.
> C'est aussi pourquoi les mp3 produits sont conservés plutôt que refaits.

### Utilisation

```bash
# Toute la série (une quinzaine de secondes, plus la construction la première fois)
./outils/generer-jingles.sh

# Un seul générique, après avoir changé son texte ou son habillage
./outils/generer-jingles.sh matinale

# Un nom inconnu rappelle la liste des noms connus, et sort en code 2
./outils/generer-jingles.sh liste
```

Le conteneur écrit dans `jingles/bands/`, monté sur son `/sortie`, et les
fichiers appartiennent à celui qui a lancé la commande — pas à root. **C'est le
seul endroit où quelque chose sort du conteneur** : les pistes intermédiaires
(voix seule, lit seul) restent dans son `/tmp` et disparaissent avec lui.

> Pour écouter ce qui a mal tourné dans un montage, ouvrir un conteneur qui
> reste : `docker run --rm -it --entrypoint bash local-webradio-jingles`, puis
> `python -u generer_jingles.py <nom>` — le `/tmp/montage` est alors sous la
> main jusqu'à la sortie.

### Comment c'est fait

1. **La voix.** `edge-tts`, voix `fr-FR-HenriNeural`, débit à −4 % : à l'antenne,
   on parle un rien plus lentement qu'en conversation.
2. **Le lit.** Une entrée `aevalsrc` par note — cinq timbres (`sine`, `bell`,
   `saw`, `square`, `pad`) et une grosse caisse, chacun une expression
   mathématique —, mixées par `amix`. Rien n'est téléchargé, aucune licence
   n'est en jeu. Une note tenue est ajoutée sous chaque générique pour que le lit
   ne meure pas avant la voix.
3. **Le mixage.** La voix entre 0,9 s après l'attaque du lit ; le lit **baisse
   sous elle** (`sidechaincompress`) et repart seul 1,4 s après la dernière
   syllabe. C'est le geste de base d'un habillage radio.
4. **Le niveau.** `loudnorm` à −16 LUFS, true peak −1,5 dBFS : le niveau
   habituel d'une webradio. Un jingle plus fort que la musique s'entend comme un
   défaut.

### Changer un texte ou un habillage

Tout est dans le dictionnaire `JINGLES`, en bas du script : un nom de fichier →
le texte dit, les notes du lit, la note tenue dessous, et la coupure du haut du
spectre si le lit est agressif. Une entrée modifiée se régénère seule en passant
son nom en argument.

**Les noms de fichiers sont un contrat avec `webradio.toml`** : ils y sont
déclarés en `intro = "bands/<nom>.mp3"`. En renommer un ici oblige à l'y
renommer. Un `intro` qui pointe vers un fichier absent ne fait rien et ne
signale rien (SPECS.md §4.3) — c'est silencieux, donc ça se vérifie à l'œil :

```bash
.venv/bin/python - <<'PY'
import tomllib, pathlib
bands = tomllib.loads(pathlib.Path("webradio.toml").read_text())["bands"]
manquants = [b["intro"] for b in bands if "intro" in b
             and not (pathlib.Path("jingles") / b["intro"]).exists()]
print("manquants :", manquants or "aucun")
PY
```

### Ce que ça ne dit pas

Les tests n'entendent rien (AGENTS.md §4.1). Que la voix tombe juste, que le lit
ne couvre pas le premier mot, qu'un générique de sept secondes ne soit pas trop
long à cinq heures du matin : **cela s'écoute**, et rien d'autre ne le dira.

```bash
mpv jingles/bands/*.mp3
```
