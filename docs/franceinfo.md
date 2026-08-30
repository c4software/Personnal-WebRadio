# docs/franceinfo.md — Relevé du flash d'information

> **Relevé mené le 2026-08-30** (`GOAL-002-T07`), et **son résultat est
> négatif** : aucune source de flash horaire n'a pu être confirmée. La §1 dit ce
> qui a été établi, ce qui reste inconnu, et les trois questions qui remontent à
> l'auteur.
>
> **Décidé le 2026-08-30** : c'est `GOAL-002` qui cherche. Point de départ — les
> flux publics de Radio France : podcast, RSS, fichier à URL stable. On constate
> ce qui répond réellement, on documente. **Si rien de fiable n'existe, la
> question remonte à l'auteur** plutôt que de bricoler autour d'une source
> instable (AGENTS.md §1.2).
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'une
> dépendance externe.**

---

## 1. Trouver la source — **relevé : aucune source confirmée**

> **Constaté le 2026-08-30** (`GOAL-002-T07`). Recherche menée depuis le web,
> sans URL fournie par l'auteur.

**Aucun flux de flash horaire n'a pu être confirmé.** Voici ce qui a été établi,
et pourquoi cela ne suffit pas.

### 1.1 Radio France a retiré la découvrabilité de ses flux RSS

En **mars 2026**, Radio France a supprimé les liens RSS visibles des pages
d'émission. Les flux historiques de `radiofrance-podcast.net` répondaient encore
en **avril 2026** — mais ils ne sont plus annoncés nulle part, ce qui est le
statut le plus fragile qui soit : ils fonctionnent sans être promis.

### 1.2 Les flux officiels sont volontairement courts

Quand ils existent, les flux RSS de Radio France **se limitent aux cinq derniers
épisodes** plus ceux du mois précédent.

> **Ce n'est pas un problème pour nous, et c'est un point positif du relevé.**
> SPECS.md §7 n°14 a tranché « l'épisode le plus récent » : cinq épisodes
> suffisent largement. Une décision prise pour d'autres raisons se trouve être
> celle qui résiste à cette contrainte.

### 1.3 Trois voies, aucune sans risque

| Voie | Ce qu'elle vaut |
|---|---|
| Un flux `radiofrance-podcast.net` direct | Fonctionne, mais n'est plus documenté ni annoncé. Peut disparaître sans préavis, et rien ne préviendra |
| `rss-rf.aerion.me` (tiers, source ouverte, MIT) | Utilise les **mêmes API que l'application Radio France**. Actif. Mais c'est un service tiers : sa disponibilité ne dépend ni de nous ni de Radio France |
| Auto-héberger ce pont | Supprime la dépendance au tiers, ajoute un service à faire tourner — et déplace le problème plutôt que de le résoudre |

### 1.4 Ce qui reste réellement inconnu

Ce relevé n'a **pas** établi le plus important :

- [ ] **Aucune URL de flux de flash horaire n'a été confirmée.** Les émissions
      trouvées (« franceinfo en 3 minutes », « 8h30 franceinfo », « Les
      informés ») sont des **émissions**, pas des flashs. Elles relèveraient de
      `GOAL-010`, pas de `GOAL-006`.
- [ ] Un flash d'information — le bulletin bref diffusé à l'heure ronde — est-il
      seulement publié en podcast, ou n'existe-t-il qu'au fil de l'antenne ?
- [ ] Si seul le direct le porte, la question change de nature : il faudrait
      capter un flux continu et en extraire un segment, ce qui n'a rien à voir
      avec lire un podcast.

### 1.5 Conclusion : la question remonte à l'auteur

C'est la conduite qu'`AGENTS.md §1.2` prescrit, et que
[TASKS.md](../TASKS.md) avait inscrite : *si rien de fiable n'existe, remonter
plutôt que bricoler autour d'une source instable.*

**Trois questions, dans l'ordre :**

1. **Avez-vous une URL précise en tête ?** L'intention initiale disait
   « normalement il donne le flash accessible ». Si vous savez où, tout ce qui
   précède devient sans objet.
2. **Sinon, acceptez-vous une dépendance à un service tiers** (`rss-rf.aerion.me`)
   ou à un flux non documenté, en sachant qu'il peut disparaître sans préavis —
   auquel cas la radio se replie sur la musique et le journalise (SPECS.md §4.5) ?
3. **Ou bien : « franceinfo en 3 minutes » vous suffirait-il ?** C'est une
   émission courte et régulière. Elle ne serait plus un *flash* au sens de
   SPECS.md §4.5 mais une *émission* au sens de §4.11 — et le projet sait déjà
   faire, sans code supplémentaire.

> **La troisième piste est la plus intéressante.** Elle ferait disparaître
> `GOAL-006`'s dépendance externe entière : les flashs cesseraient d'être un
> mécanisme à part pour devenir un cas particulier des émissions.

## 1.bis Second relevé — **le podcast est mort, le direct répond**

> **Constaté le 2026-08-30**, depuis cette machine, avec `curl` et ffmpeg
> n9.0.1. Réponse aux trois questions de §1.5 : la n°3 (« franceinfo en
> 3 minutes ») **n'est plus possible** ; la n°2 a une réponse plus simple que
> prévu ; la n°1 reste posée à l'auteur.

### Le flux RSS « France Info en 3 minutes » répond, mais il est vide

```
GET https://radiofrance-podcast.net/podcast09/rss_13250.xml
HTTP 200  application/xml  3 197 octets
title  : France Info en 3 minutes
items  : 1
  Sun, 30 Aug 2026 00:45:36 +0200 | « Retrouvez tous les épisodes sur l'appli Radio France »
  durée 00:00:12 | enclosure audio/mpeg length=0
  https://media.radiofrance-podcast.net/podcast09/autopromo_replay_franceinfo.mp3
```

**Le seul épisode est une auto-promotion de douze secondes**, republiée chaque
jour. La voie « les flashs deviennent une émission » est fermée : notre lecteur
de podcast (GOAL-010) diffuserait ce message publicitaire tous les jours à
l'heure dite, avec un `guid` neuf à chaque fois. Le point 1.1 ci-dessus est
donc à relire : les flux ne sont pas seulement *dé-annoncés*, ils sont
**désactivés en gardant un code 200** — exactement le cas que la §3 redoutait.

### Le direct répond, et notre chaîne le décode

```
GET https://icecast.radiofrance.fr/franceinfo-midfi.mp3
HTTP/2 200   content-type: audio/mpeg   icy-br: 128   icy-name: franceinfo-midfi.mp3
(pas d'icy-metaint, même avec `Icy-MetaData: 1`)
ffprobe : mp3, 48000 Hz, 2 canaux, 128 kb/s
```

| Constat | Valeur |
|---|---|
| `http://direct.franceinfo.fr/live/franceinfo-midfi.mp3` | redirige en 301 vers l'URL ci-dessus |
| Variante `franceinfo-hifi.aac` | HTTP 200, `audio/aac`, 192 kb/s |
| Décodage par la voie du projet (`-f s16le -ar 44100 -ac 2`, 5 s) | **882 000 octets, exactement** ce qu'on attend |
| Niveau intégré sur 20 s de parole (`ebur128`) | **−16,2 LUFS** — c'est un niveau de radio parlée, à comparer à la musique **à l'oreille** |
| Débit reçu à l'ouverture | ~650 Ko dans les six premières secondes : le serveur envoie une avance, puis le temps réel |

Ce que cela change : un direct est une entrée ffmpeg **comme une autre** pour
`adapters/ffmpeg/decoder.py`. La différence n'est pas dans le format, elle est
dans le fait qu'**il ne se termine jamais** — c'est le programme qui doit
décider quand l'arrêter (voir SPECS.md §4.11 et `GOAL-015`).

### La grille de franceinfo — **source secondaire, à confirmer à l'oreille**

D'après la presse spécialisée (pas d'après Radio France) : un **journal à 00 et
à 30 de chaque heure**, d'environ neuf minutes, et des rappels de titres entre
les deux. **Rien de cela n'a été observé ici** — le relevé n'a écouté que vingt
secondes. La durée à réserver est donc un réglage de l'auteur, pas un constat.

### Ce qui reste ouvert

- [ ] Le direct est publié sans engagement : une URL de flux peut changer. Le
      repli sur la musique (SPECS.md §4.5) est le seul filet, et il doit être
      **testé** avec une URL morte.
- [ ] Le flux ne porte pas de métadonnées en ligne : impossible de savoir *par
      le flux* si l'on est dans le journal ou dans une chronique.
- [ ] Un direct capté « en cours de phrase » et coupé « en cours de phrase » :
      c'est inévitable, et seule l'écoute dira si c'est acceptable.
- [ ] Le pont tiers `rss-rf.aerion.me` répond en 200 mais n'a pas été exploré
      plus loin : il n'est plus utile si le direct suffit.

## 2. Le contenu — **renseigné le 2026-08-30 par §1.bis et GOAL-015**

- **Durée** : celle qu'on déclare (`duration_minutes`). La grille de
  franceinfo — journal à :00 et :30, ~9 min — reste de seconde main : à
  ajuster à l'oreille (`GOAL-015-T08`).
- **Fraîcheur** : sans objet — on capte le **direct**, ce qui passe est ce qui
  passe à l'antenne.
- **Format** : MP3 48 kHz stéréo 128 kb/s, décodé et réencodé par le diffuseur
  comme tout le reste.
- **Niveau** : −16,2 LUFS mesurés, restitués à l'identique à travers la chaîne.
  Contre la musique normalisée : à l'oreille.
- **Métadonnées** : aucune dans le flux — l'interface affiche le **nom
  déclaré** au TOML.

### Les questions d'origine (historique)

- [ ] Quelle **durée** fait un flash, et cette durée est-elle stable ? Elle
      détermine la fenêtre qu'il faut réserver dans la programmation.
- [ ] À quelle **fréquence** est-il mis à jour ? Toutes les heures, aux
      demi-heures, irrégulièrement ?
- [ ] Comment savoir qu'un flash est **récent** plutôt que celui d'il y a trois
      heures ? Un flash périmé diffusé comme neuf est pire qu'un flash absent.
- [ ] Quel format et quel débit ? Faut-il un réencodage pour rejoindre le format
      du flux (ARCHITECTURE.md §4) ?
- [ ] Le niveau sonore est-il comparable à celui de la musique ? Un flash deux
      fois trop fort est l'un des quatre angles morts (AGENTS.md §4.1) — et ne se
      constatera qu'à l'oreille.

## 3. Quand ça se passe mal — **le mécanisme est celui des émissions**

Un direct injoignable ou qui se tarit : le diffuseur reste sur la musique — la
bascule exige que le direct soit **réellement prêt** — et la case n'est pas
retentée (SPECS.md §7 n°22). Restent à observer : une URL morte en production,
et une coupure du flux **en cours** de case.

### Les questions d'origine (historique)

SPECS.md §4.5 pose le principe : **l'indisponibilité est un cas nominal, pas une
panne.** Reste à établir ce qu'on observe réellement.

- [ ] Que se passe-t-il si la source ne répond pas ? Erreur franche, ou attente
      longue ? La radio ne peut pas se permettre d'attendre : un délai maximal
      devra être fixé et déclaré dans le TOML.
- [ ] Un fichier **tronqué** est-il détectable avant diffusion ? La radio ne doit
      jamais diffuser un flash incomplet.
- [ ] La source peut-elle renvoyer une page HTML d'erreur avec un code 200 ?

---

## 4. Points incertains

_L'adresse du direct est établie (§1.bis) ; la grille de franceinfo et le
niveau sonore contre la musique restent à constater à l'oreille._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
