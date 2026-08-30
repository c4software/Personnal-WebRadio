# docs/ffmpeg.md — Relevé des options réellement acceptées

> **Relevé établi le 2026-08-30** (`GOAL-002-T01` à `T04`). Les sections 1 à
> 2.ter portent des constats ; les sections 3 et 4 restent des questions.
> `GOAL-002` devra répondre **contre la version installée sur cette machine** —
> pas contre la documentation d'une version quelconque.
>
> Règle applicable (AGENTS.md §3). Ici elle est particulièrement concrète : les
> options de ffmpeg changent de version en version, et une option acceptée
> silencieusement mais ignorée produit un défaut **audible** que rien ne
> signalera.

**Version constatée le 2026-08-30** (`GOAL-001-T01`) :

```
ffmpeg version n9.0.1 — Copyright (c) 2000-2026 the FFmpeg developers
```

Tout ce qui suit doit être vérifié **contre cette version**, et le constat
réétabli si elle change.

---

## 1. Enchaîner deux morceaux sans blanc — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T01`), contre ffmpeg n9.0.1, avec trois
> MP3 volontairement hétérogènes — 44100/2/192k, 44100/2/128k et 48000/1/128k —
> parce que c'est le cas réel d'une bibliothèque, pas l'exception.

### 1.1 Le démultiplexeur `concat` avec `-c copy`

**Sur des fichiers homogènes** (même fréquence, mêmes canaux) : fonctionne.
Durée obtenue 6,030 s pour 6 s attendues, et un avertissement à chaque jonction :

```
Application provided invalid, non monotonically increasing dts to muxer in stream 0
```

**Sur des fichiers hétérogènes** (44100/2 puis 48000/1) : produit un fichier
lisible, mais **dont les métadonnées sont fausses**.

| | Copie (`-c copy`) | Réencodage |
|---|---|---|
| Durée annoncée | **6,295 s** | 6,000 s |
| Format annoncé | 44100 / 2 pour tout | 44100 / 2, exact |
| Durée réelle attendue | 6,000 s | 6,000 s |

Le conteneur déclare le format de la **première** image pour l'ensemble du
fichier, et la durée dérive de 5 %.

### 1.2 Ce qui contredit l'intuition, et qu'il ne faut pas généraliser

**Le décodeur de ffmpeg s'adapte image par image, et la hauteur reste juste.**
Mesuré par Goertzel sur la seconde moitié, entre les deux fréquences candidates —
660 Hz si le rééchantillonnage est honoré, 606 Hz s'il est ignoré :

| Fichier | Énergie à 606 Hz | Énergie à 660 Hz | Verdict |
|---|---|---|---|
| `c_48000` (référence) | 24 | **1835** | correct |
| Copie hétérogène | 12 | **1776** | **correct** |
| Réencodage | 7 | **1181** | correct |

L'hypothèse de départ — « la seconde moitié sera relue à 44100 et sonnera 8 %
trop bas » — est **fausse pour ffmpeg** : le format MP3 porte la fréquence dans
l'en-tête de chaque image, et un décodeur qui les lit s'adapte.

> **Ce constat ne s'étend à aucun autre lecteur.** Il dit que *ffmpeg* s'adapte,
> pas que VLC, un navigateur ou une enceinte le feront — d'autant que la durée
> annoncée, elle, reste fausse. C'est exactement la question de
> [flux-icy.md](./flux-icy.md) §3, et elle ne se répond qu'avec de vrais
> lecteurs.

### 1.3 La concaténation brute d'octets ne marche pas

`cat a.mp3 b.mp3 > flux.mp3` produit un fichier **cassé** :

```
[mp3float] Header missing
Error submitting packet to decoder: Invalid data found when processing input
```

Durée obtenue 5,07 s pour 6 s. Les étiquettes ID3 présentes à la jonction
rompent le flux d'images. **Écarter cette voie** : elle paraissait la plus
économe, elle ne fonctionne pas.

## 2. Alimenter un encodage continu — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T02`).

### 2.1 La voie qui marche : décoder au format commun, un seul encodeur

Un décodeur **par morceau**, choisi au dernier moment, ramenant chacun au même
PCM, tous versés dans le **même** encodeur :

```bash
for f in "$@"; do
  ffmpeg -i "$f" -f s16le -ar 44100 -ac 2 -
done | ffmpeg -re -f s16le -ar 44100 -ac 2 -i - -b:a 128k sortie.mp3
```

Trois morceaux de 3 s, **dont un en 48000 mono** :

| Mesure | Résultat |
|---|---|
| Durée | **9,000000 s** — exacte |
| Format | 44100 / 2, homogène |
| Fenêtres de 50 ms sous le seuil de silence | **0** |

**Aucun blanc, à aucune jonction**, y compris celle qui change de fréquence et de
nombre de canaux. C'est la réponse à la question ouverte de §1 : la file n'a pas
besoin d'être connue d'avance, et le démultiplexeur `concat` n'est pas nécessaire.

### 2.2 Un tuyau qui se tarit n'insère pas de silence

Une seconde d'attente injectée au milieu du tuyau : la durée obtenue reste
**6,000000 s**, pas 7. L'encodeur **attend**, il ne comble pas.

> **La conséquence est architecturale, et elle est importante.** Un morceau lent
> à résoudre ne crée pas de blanc *dans l'audio* — il crée un trou *dans le temps
> réel*. Pour l'auditeur branché, ce n'est pas un silence : c'est un flux qui
> cesse d'arriver, donc un tampon qui se vide, donc une déconnexion
> ([flux-icy.md](./flux-icy.md) §3).
>
> Il faut donc **prendre de l'avance** : résoudre le morceau suivant pendant que
> le courant joue, jamais à la jonction.

### 2.3 Le rythme n'est pas automatique

Sans `-re`, ffmpeg encode **aussi vite qu'il peut** : 0,26 s de machine pour 9 s
d'audio. Avec `-re`, il suit le temps réel : 8,48 s pour 9 s.

`-re` est donc indispensable — ou bien c'est notre code qui cadence. Sans l'un
des deux, la radio consommerait la bibliothèque entière en quelques minutes.

## 2.bis Transcoder le moins possible — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T04`), sur cette machine (24 cœurs).

| Mesure | Résultat |
|---|---|
| Réencodage de 60 s d'audio | **0,63 s de machine** |
| Facteur temps réel | **×95** |
| Coût d'un flux permanent | **1,05 % d'un cœur** |
| Coût pour cinq auditeurs | **le même** — un seul encodage les alimente tous (ARCHITECTURE.md §4.1) |

### Ce que ce chiffre décide

L'arbitrage de SPECS.md §7 n°11 plaçait l'économie en **troisième** priorité,
derrière « sans coupure » et « lisible partout ». Le chiffre montre qu'il n'y a
**presque rien à arbitrer** : un pour cent d'un cœur, sur une machine qui en a
vingt-quatre.

> **Conclusion pour `GOAL-004` : réencoder systématiquement.** Ne pas écrire de
> chemin de copie sans réencodage, ne pas détecter le format d'entrée, ne pas
> basculer d'un régime à l'autre. Ce chemin aurait apporté une complexité réelle
> — deux régimes, une bascule, ses cas limites — pour économiser un pour cent
> d'un cœur, en risquant précisément ce que la priorité n°1 interdit.
>
> C'est l'optimisation que le relevé était chargé de chercher. **Elle n'existe
> pas, et c'est une bonne nouvelle** : le chemin le plus simple est aussi le bon.

## 2.ter Insérer un jingle ou un flash — **relevé**

> **Constaté le 2026-08-30** (`GOAL-002-T03`), avec un jingle en **22050 mono**
> et un `encore.mp3` en **32000 stéréo** — c'est-à-dire des fichiers déposés à la
> main, sans rapport de format avec la bibliothèque.

**Un jingle n'est rien d'autre qu'un morceau de plus dans la file.** Il traverse
le même tuyau, il est ramené au même PCM, et l'encodeur ne fait aucune
différence :

| Séquence | Durée attendue | Obtenue | Blancs |
|---|---|---|---|
| musique · `14h.mp3` · musique | 7,000 s | **7,000000 s** | 0 |
| musique · `14h.mp3` · `15h.mp3` · `encore.mp3` · musique | 8,500 s | **8,500000 s** | 0 |

La seconde ligne est le cas de SPECS.md §4.3 — plusieurs jingles dus à la même
jonction, `encore.mp3` en dernier. **Quatre jonctions, aucun blanc.**

> **Il n'y a donc qu'un seul chemin d'insertion à écrire**, et il est déjà décrit
> en §2.1. Les jingles horaires, le jingle de vote et les flashs l'empruntent
> tous. C'est la simplification qu'ARCHITECTURE.md §6.2 espérait en remplaçant la
> note mêlée par un jingle à la jonction : le relevé la confirme.

### Ce que ce relevé **ne** dit **pas**

Les niveaux mesurés sont uniformes (rms ≈ 1850 partout) — **mais les fichiers
d'essai sont des sinus synthétiques de même amplitude.** Cela ne dit rien du cas
réel, où un jingle enregistré trop fort écrasera la musique.

La normalisation du niveau reste donc entière, et c'est un **angle mort**
(AGENTS.md §4.1) : aucun test ne l'entendra. À traiter dans `GOAL-006`, avec de
vrais fichiers, à l'oreille.

## 3. Le flux de sortie

- [ ] Quel format et quel débit pour un flux HTTP lu indifféremment par VLC, un
      navigateur et une enceinte connectée ?
- [ ] Quels en-têtes ffmpeg produit-il en tête de flux, et un auditeur qui se
      branche **en cours** peut-il les manquer ? C'est exactement le cas nominal
      de SPECS.md §4.1 : il faut savoir ce qu'un auditeur tardif reçoit.
- [ ] Comment forcer un débit régulier, pour que l'encodage suive le temps réel
      plutôt que d'aller aussi vite qu'il peut ?

## 4. Le cycle de vie du processus

ARCHITECTURE.md §4 le signale comme le point à surveiller : **un ffmpeg orphelin
qui survit à la dernière déconnexion annule tout le bénéfice du démarrage à la
demande.**

- [ ] Comment l'arrêter proprement, et en combien de temps s'arrête-t-il ?
- [ ] Que fait-il si sa sortie n'est plus lue — le dernier auditeur vient de se
      débrancher ? Bloque-t-il, meurt-il, remplit-il un tampon ?
- [ ] Que renvoie-t-il comme code de sortie dans chacun de ces cas ?
- [ ] Sa sortie d'erreur doit-elle être lue en continu pour éviter qu'il ne se
      bloque sur un tuyau plein ?

---

## 5. Points incertains

**Établis, et clos** : l'enchaînement sans blanc, l'alimentation d'un encodage
continu, l'insertion d'un jingle, le coût d'un réencodage permanent (§1 à 2.ter).

**Restent ouverts :**

- [ ] Les en-têtes que ffmpeg produit en tête de flux, et ce qu'un auditeur
      tardif en reçoit — **partiellement répondu** par
      [flux-icy.md](./flux-icy.md) §2 : il décode sans en-tête initial. Ce qui
      reste à voir concerne les lecteurs autres que ffmpeg.
- [ ] Le cycle de vie du processus (§4) — **un défaut a déjà été trouvé**
      ([flux-icy.md](./flux-icy.md) §3.bis) : deux orphelins survivants. Les
      questions de §4 restent à reprendre à la lumière de ce constat.
- [ ] La **normalisation du niveau** entre musique, jingles et flashs. Les
      fichiers d'essai étaient des sinus de même amplitude ; le cas réel ne l'est
      pas. Angle mort (AGENTS.md §4.1) : à traiter à l'oreille dans `GOAL-006`.

Aucun point n'a été remplacé par une supposition.
