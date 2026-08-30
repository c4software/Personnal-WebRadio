# docs/ffmpeg.md — Relevé des options réellement acceptées

> **Ce relevé est vide de constats.** Il porte les questions auxquelles
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

## 2.bis Transcoder le moins possible

SPECS.md §4.9 demande d'économiser la machine ; SPECS.md §4.9 demande aussi de ne
jamais couper. Ce relevé doit établir ce qui est **réellement possible**, pas ce
qui serait souhaitable.

- [ ] ffmpeg sait-il **copier** un flux audio sans le réencoder (`-c copy`) tout
      en l'insérant dans une sortie continue ? À quelles conditions sur le format
      d'entrée ?
- [ ] Que produit exactement une copie lorsque deux fichiers successifs n'ont pas
      le même débit, la même fréquence d'échantillonnage ou le même nombre de
      canaux ? Un flux valide, ou un flux que les lecteurs refusent
      (→ [docs/flux-icy.md](./flux-icy.md) §3) ?
- [ ] Quel est le **coût réel** d'un réencodage permanent sur cette machine —
      pourcentage d'un cœur pour un auditeur, pour cinq ? Le chiffre décide :
      « économiser les ressources » n'a de sens qu'en regard de ce qu'on
      économise.
- [ ] Un réencodage **partiel** est-il possible : copier tant que le format
      correspond, ne réencoder que les fichiers qui s'en écartent ? Que se
      passe-t-il à la bascule entre les deux régimes ?

Ce relevé **ne décide de rien** : SPECS.md §7 n°11 est tranchée, et le
réencodage permanent est la voie par défaut, assumée. Ce qu'on cherche ici est
une **optimisation** — un chemin moins coûteux qui ne viole pas l'ordre
*sans coupure > lisible partout > économie*. S'il n'en existe pas, on réencode et
`GOAL-004` n'attend personne.

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

_Tout ce qui précède._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
