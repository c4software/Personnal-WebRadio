# docs/flux-icy.md — Relevé de ce qu'attendent les lecteurs de webradio

> **Relevé partiel, établi le 2026-08-30** (`GOAL-002-T05`, `T06`). Les
> sections 1 à 3.bis portent des constats obtenus avec `curl` et ffmpeg. **La
> matrice des vrais lecteurs — VLC, navigateur, enceinte — reste entière** : elle
> demande l'auteur.
> `GOAL-002` devra répondre **en branchant de vrais lecteurs**, pas en lisant une
> spécification.
>
> Règle applicable (AGENTS.md §3). Elle est ici particulièrement mal outillée :
> il n'existe **aucune norme** du « flux de webradio ». Ce que les lecteurs
> acceptent est une convention de fait, héritée de Shoutcast et d'Icecast, et
> chacun l'interprète à sa façon. **Rien ne se déduit ; tout se constate.**

SPECS.md §4.9 exige un flux lisible par n'importe quel lecteur, sans coupure. Ce
relevé établit ce que « n'importe quel lecteur » veut réellement dire.

---

## 1. Le branchement — **relevé partiel**

> **Constaté le 2026-08-30** (`GOAL-002-T05`), avec une maquette de station :
> serveur HTTP, encodage unique, diffusion vers N connexions, démarrage à la
> première et arrêt à la dernière.
>
> **Les clients d'essai sont `curl` et ffmpeg.** Ce qui suit vaut pour eux, et
> **pour eux seuls** : VLC, un navigateur et une enceinte connectée n'ont pas été
> essayés — voir §6, ils demandent l'auteur.

En-têtes servis par la maquette, et acceptés :

```
Content-Type: audio/mpeg
icy-name: local-webradio
icy-br: 128
```

Ni `Content-Length` ni `Transfer-Encoding` — le flux est infini, et aucun client
d'essai ne s'en est plaint.

**Rien ne tourne tant que personne n'écoute** : zéro processus ffmpeg avant le
premier branchement. Le démarrage à la demande de SPECS.md §1 fonctionne.

## 2. Entrer en cours de route — **relevé**

**C'est le cas nominal de cette radio** (SPECS.md §4.1), et il fonctionne.

Un second auditeur branché **cinq secondes après** le premier, en plein morceau :

| Mesure | Auditeur A (dès le début) | Auditeur B (en cours) |
|---|---|---|
| Octets reçus | 196 608 | 94 208 |
| Durée décodable | 12,285 s | **5,880 s** |
| Format reconnu | mp3 44100 / 2 | **mp3 44100 / 2** |
| Erreurs au décodage | aucune | **aucune** |

**Un auditeur tardif n'a besoin d'aucun en-tête initial.** Le format MP3 porte
tout ce qu'il faut dans l'en-tête de **chaque image** : celui qui arrive au
milieu trouve la prochaine image et décode. C'est le même mécanisme que celui
constaté dans [ffmpeg.md](./ffmpeg.md) §1.2.

Seul avertissement observé, cosmétique : `Estimating duration from bitrate, this
may be inaccurate` — un flux infini n'a pas de durée.

**Un seul encodage alimente tout le monde** : deux processus ffmpeg avec un
auditeur, **toujours deux** avec deux auditeurs. Le fan-out se fait dans notre
code, comme prévu par ARCHITECTURE.md §4.1.

## 3. Ce qui fait décrocher — **sans objet, par construction**

La question était : que fait un lecteur si le débit, la fréquence, le nombre de
canaux ou le codec changent en cours de flux ?

**Elle ne se pose plus.** [ffmpeg.md](./ffmpeg.md) §2.bis a montré qu'un
réencodage permanent coûte 1 % d'un cœur, et SPECS.md §7 n°11 a tranché en sa
faveur : le flux est encodé **une fois, à un format fixe**, quoi que contienne la
bibliothèque. Rien ne change jamais en cours de route.

> **Ce n'est pas une réponse, c'est une suppression du problème.** Elle tient
> tant que la décision n°11 tient. Si un chemin de copie sans réencodage était
> réintroduit un jour, cette question redeviendrait ouverte — et elle exigerait
> alors la matrice de lecteurs de §6.

## 3.bis Un défaut trouvé en exécutant, qu'aucun test n'aurait vu

**À la dernière déconnexion, deux processus ffmpeg ont survécu.**

C'est exactement ce dont ARCHITECTURE.md §4 prévenait : *« un ffmpeg orphelin qui
survit à la dernière déconnexion annule tout le bénéfice du démarrage à la
demande. »* La maquette l'a produit du premier coup.

```
PID     ELAPSED  COMMAND
943786  00:58    [ffmpeg] <defunct>
944122  00:47    ffmpeg -i b_44100_128k_stereo.mp3 -f s16le -ar 44100 -ac 2 -
```

Deux causes, distinctes, et la seconde est la plus vicieuse :

1. **Seul l'encodeur était tué.** Le processus **source** — la chaîne de
   décodeurs qui l'alimente — n'était jamais arrêté. Il survit, tuyau bouché, et
   ne meurt pas de lui-même.
2. **Course entre l'arrêt et la lecture.** La référence du processus est mise à
   `None` pendant que la boucle de diffusion lit encore dessus :
   `AttributeError: 'NoneType' object has no attribute 'stdout'`.

**À retenir pour `GOAL-004`** : arrêter la chaîne, c'est arrêter **tout l'arbre
de processus**, et la boucle de diffusion doit l'apprendre autrement qu'en
déréférençant ce qui vient de disparaître.

> Un test qui aurait vérifié « la chaîne s'arrête » en regardant un booléen
> serait **passé au vert**. Le booléen était juste ; les processus étaient
> toujours là.

## 4. Les métadonnées

- [ ] Faut-il annoncer le titre en cours, et par quel mécanisme ? Est-ce attendu,
      ou seulement agréable ?
- [ ] Un changement de métadonnée peut-il, à lui seul, provoquer une coupure chez
      certains lecteurs ?
- [ ] Que faut-il annoncer pendant un jingle ou un flash, où il n'y a ni titre ni
      artiste ?

## 5. Plusieurs auditeurs

- [ ] Un auditeur lent ralentit-il les autres si le flux est écrit dans une seule
      boucle ? Où doit se situer le tampon pour que non ?
- [ ] Comment détecter une déconnexion **brutale** — câble arraché, lecteur tué —
      plutôt que d'attendre un délai d'expiration ? SPECS.md §4.7 en dépend :
      sans cela, la chaîne tourne pour un auditeur qui n'existe plus.

---

## 6. Points incertains

**Établis** : le branchement, l'entrée en cours de route, et la disparition par
construction de la question des changements de format (§1 à 3).

**Reste entier, et il demande l'auteur :**

- [ ] **La matrice des vrais lecteurs.** Les essais ont été menés avec `curl` et
      ffmpeg. **VLC, un navigateur, une enceinte connectée et une application de
      radios n'ont pas été essayés** — or c'est le plus intolérant d'entre eux
      qui fixera la contrainte (SPECS.md §4.9).
- [ ] Les **métadonnées de titre** (§4) : attendues ou seulement agréables, et
      un changement peut-il à lui seul faire décrocher un lecteur ?
- [ ] La détection d'une déconnexion **brutale** (§5) — SPECS.md §4.7 en dépend :
      sans elle, la chaîne tourne pour un auditeur qui n'existe plus.
- [ ] Le placement du tampon pour qu'un auditeur lent ne ralentisse pas les
      autres. La maquette ne l'a pas éprouvé : deux auditeurs, tous deux locaux.

> **Ce que le relevé ne peut pas faire tout seul.** Brancher une enceinte
> connectée et un téléphone demande d'être devant la machine. C'est un des quatre
> angles morts (AGENTS.md §4.1), et il ne se comblera pas depuis une session.

---

## 7. Rejoué contre `output.harbor` — **relevé du 2026-08-30** (`GOAL-016`)

La chaîne de §1 à §5 n'existe plus : Liquidsoap 2.3.3 sert le flux
(docs/liquidsoap.md). Ce qui a été constaté avec `curl` sur la pile Compose
complète, contre le vrai Navidrome :

```
HTTP/1.1 200 OK
Content-type: audio/mpeg
icy-name: local-webradio
icy-br: 128
```

- Les en-têtes de §1 sont **reproduits** par `headers=` dans `radio.liq` ;
  ni `Content-Length` ni `Transfer-Encoding`, comme avant.
- Sans auditeur : aucune requête à l'API, rien de décodé (§1 « rien ne tourne »
  devient « rien n'est décodé ni demandé », SPECS.md §1).
- Premier auditeur : `POST /playout/listeners 1`, puis deux `POST /playout/next`
  d'affilée — celui qui joue et celui d'avance.
- Dernier auditeur parti (`curl` coupé) : `POST /playout/listeners 0` dans la
  seconde, et l'API repasse à `on_air: false`. La **déconnexion brutale** (§5)
  n'a toujours pas été essayée.
- Entrer en cours de route (§2) et les changements de format (§3) restent sans
  objet : un seul encodeur, un seul format.
- Les métadonnées de titre (§4) ne sont pas envoyées dans le flux ; l'API les
  porte. Toujours ouvert : est-ce attendu par un lecteur ?

**La matrice des vrais lecteurs (§6) reste entière** : `GOAL-016-T12`.
