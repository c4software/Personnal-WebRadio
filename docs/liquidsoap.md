# docs/liquidsoap.md — Relevé de Liquidsoap, et ce qui a décidé la migration

> **Relevé établi le 2026-08-30**, contre `savonet/liquidsoap:v2.3.3` (Docker),
> avec deux MP3 hétérogènes (44100/2/192k et 48000/1/128k) et `curl`. Rien
> n'est installé sur la machine hôte : `pacman` ne connaît pas le paquet.
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'une
> dépendance externe.** Ce fichier distingue ce qui a été constaté de ce qui
> reste à constater.

**Version constatée** : `Liquidsoap 2.3.3`. Image : **967 Mo**.

---

## 1. Ce qui a été constaté

### 1.1 `request.dynamic` : c'est notre Python qui décide

```liquidsoap
def next_uri() =
  uri = list.hd(default="", process.read.lines("/work/next.sh"))
  request.create(uri)
end
s = request.dynamic(id="prog", next_uri, retry_delay=1., prefetch=1)
```

Le script externe est appelé **à chaque morceau**, et ce qu'il rend est joué.
C'est exactement la forme de `app/playout.py::next_entry()` : le noyau, la
grille, les jingles et les émissions restent à nous ; Liquidsoap ne décide
rien. `http.get` et `http.post` existent : le script peut être remplacé par un
appel à notre API.

Avec `prefetch=1`, **un morceau est demandé d'avance** dès le démarrage, avant
tout auditeur.

### 1.2 Sans auditeur, la version naïve joue dans le vide

Sans rien de spécial, `output.harbor` tire sur la source en permanence :
**deux morceaux décodés en 12 s sans aucun auditeur, 4 % de CPU**. C'est le
modèle radio classique que SPECS.md §1 refuse.

### 1.3 L'idiome « à la demande » existe, et il tient

```liquidsoap
listeners = ref(0)
s = switch(track_sensitive=false,
           [({listeners() > 0}, prog), ({true}, blank())])
output.harbor(%mp3(bitrate=128), mount="radio", port=8005,
  on_connect=fun (~headers, ~uri, ~protocol, _) -> listeners := listeners()+1,
  on_disconnect=fun (_) -> listeners := listeners()-1, s)
```

| Mesure | Résultat |
|---|---|
| Sans auditeur, 12 s | **1 appel** au script (le `prefetch`), **0,82 % de CPU** — l'encodeur encode du silence |
| Un auditeur, 8 s | 3 appels, le flux joue, `CONNECT n=1` puis `DISCONNECT n=0` à la coupure de `curl` |
| Reçu | 128 731 octets en 8 s = temps réel ; MP3 44100 / 2 ; 8,04 s de son |

**Ce que cela veut dire** : « rien ne tourne quand personne n'écoute » devient
« rien n'est **décodé ni demandé** quand personne n'écoute ». Un processus
reste debout et encode du silence à moins d'un pour cent d'un cœur — c'est le
même ordre de grandeur que notre encodage permanent (`docs/ffmpeg.md` §2.bis),
et notre Flask est de toute façon debout en permanence.

### 1.4 `crossfade` et `normalize` : natifs

Le script de 1.1 y ajoute `normalize(s)` puis `crossfade(duration=2.,
fade_in=1., fade_out=1., s)` — deux lignes. Le flux reçu ne contient aucun
silence détectable (`silencedetect`, −50 dB, 0,5 s). C'est tout ce que
`GOAL-004` avait dû écrire à la main, et ce que la première écoute aurait
réclamé.

### 1.5 Les en-têtes

`output.harbor` répond `HTTP/1.1 200 OK` et `Content-type: audio/mpeg`, **sans
`icy-name` ni `icy-br`**, même avec `Icy-MetaData: 1`. Sa signature offre
`headers : [string * string]` et `metaint : int` : les en-têtes de
`docs/flux-icy.md` §1 s'ajoutent à la main. **Non essayé.**

### 1.6 Le direct

`input.http("https://icecast.radiofrance.fr/franceinfo-midfi.mp3")` démarre
(`Source input.http gets up … pcm(stereo)`) et `switch` accepte un prédicat
horaire natif (`{ 0h-24h and live.is_ready() }`). **L'essai n'a pas montré la
bascule vers le direct** : dans les quinze secondes observées, le `switch` est
resté sur la musique. Cause non établie — probablement le temps de
remplissage du tampon de `input.http`. **À relever dans `GOAL-016`**, avec une
fenêtre d'observation plus longue.

### 1.7 Ce qui ne s'invente pas

`settings.harbor.icy` n'existe pas en 2.3.3 (`this value has no method icy`),
et `playlist()` prend un chemin de fichier, pas une liste. Deux erreurs faites
en dix minutes : **la syntaxe de Liquidsoap change de version en version**, et
tout script doit être validé par `liquidsoap --check` contre la version
épinglée — dans la vérification, pas à la main.

---

## 2. Ce qui a décidé (SPECS.md §7 n°23)

| | ffmpeg en sous-processus (GOAL-004) | Liquidsoap |
|---|---|---|
| Qui décide | notre Python | **notre Python** — `request.dynamic` |
| Cycle de vie des processus, auditeur lent, relance | **à nous** — 6 des 7 défauts de GOAL-014 sont là | Liquidsoap, éprouvé en production depuis quinze ans |
| Fondus, niveau | à écrire | deux lignes |
| Direct borné dans le temps (GOAL-015) | un décodeur à couper à la seconde, première coupure hors jonction | `input.http` + `switch` horaire, natif — à confirmer (1.6) |
| Rien ne tourne sans auditeur | **littéral** : zéro processus | un processus debout, 0,8 % de CPU, rien de décodé |
| Dépendance | ffmpeg, 9.0.1 | image de 967 Mo, un langage de script de plus, syntaxe mouvante |
| Testabilité du noyau | inchangée | **inchangée** |

**Ce qu'on garde** : `core/` entier, `adapters/{config,sources,podcast,state,web}`,
`app/{playout,radio,learning,show_scheduler}`. **Ce qui disparaît** :
`adapters/ffmpeg/`, `adapters/http/`, et la moitié de `app/main.py`. **Ce qui
apparaît** : `adapters/liquidsoap/` — le script `.liq`, et la route par laquelle
Liquidsoap demande la piste suivante et annonce ses auditeurs.

---

## 3. Second relevé — `GOAL-016-T01`, le 2026-08-30

> Même image, même méthode. Chaque ligne ci-dessous a été observée.

| Question (§3 d'avant) | Constat |
|---|---|
| `prefetch=0` ? | **Casse tout** : la source n'est jamais « prête », le `switch` ne la choisit jamais — zéro appel au script même avec un auditeur, et l'auditeur reçoit du silence (−70 LUFS). **`prefetch=1` est le minimum** : un morceau est demandé d'avance, **avant** le premier auditeur. La non-répétition doit donc apprendre qu'un morceau demandé n'est pas encore joué (`GOAL-016-T08`) |
| En-têtes `icy-*` | `headers=[("icy-name","local-webradio"),("icy-br","128")]` : **servis tels quels** — `docs/flux-icy.md` §1 est satisfait |
| API injoignable | Liquidsoap **boucle** : `Failed to execute … exit (1)` puis `Every possibility failed!`, **cinq tentatives en 8 s** (`retry_delay=1.`), et sert du silence pendant ce temps. C'est exactement ce que SPECS.md §5.1 interdit. **Couper en le disant est à notre charge** : `output.harbor` a `fallible`, `input.http` et les sources ont `start`/`on_start` — à essayer en `T09` |
| Bascule vers `input.http` | **Constatée** : `Switch to live with transition`, et le reçu mesure **−16,2 LUFS — identique à la source** franceinfo. Mais la source a mis **15 s** à devenir prête après le démarrage : un direct doit être branché **avant** sa case |
| `input.http` au repos | **Tire le flux en permanence** : ~18 Ko/s sans aucun auditeur (128 kb/s, 24 h/24). `input.http` accepte `start : bool` — à démarrer à l'approche de la case, à arrêter après (`GOAL-015`) |
| Déconnexion brutale | Non essayée — toujours `curl` coupé proprement |
| Mémoire | 80 Mo, 3 % de CPU avec un auditeur et le direct branché |

### Ce que cela change pour `GOAL-016`

- **Un morceau d'avance** est une propriété du système, pas un bug : `T08` doit
  distinguer *demandé* et *à l'antenne*, et l'API dit ce qui passe d'après le
  second.
- **La panne se gère chez nous** (`T09`) : quand `next_entry()` n'a rien à
  rendre, l'API ne répond pas « réessaie » mais « c'est fini », et le script
  doit alors **arrêter de servir** — pas encoder du silence.
- Le direct de `GOAL-015` se pilote par `start=false` puis démarrage anticipé ;
  ce n'est plus un décodeur à couper à la seconde.

## 4. Points incertains

- [ ] Comment un script **arrête de servir** proprement : `fallible=true` sur
      `harbor` sans repli, ou `shutdown()` — et ce que voit l'auditeur (EOF ?).
- [ ] La déconnexion brutale d'un lecteur : `on_disconnect` sur un câble arraché.
- [ ] `source.start()` / `source.stop()` sur `input.http` en 2.3.3 : nom exact,
      délai de mise en route (15 s constatées au démarrage du script).
- [ ] Le `crossfade` entre un morceau et un **jingle** : la spécification veut
      une jonction nette (SPECS.md §4.3) — le fondu doit-il s'appliquer partout ?

---

## 5. Troisième relevé — le direct (`GOAL-015`, le 2026-08-30)

> Même image. Chaque ligne a été observée, en maquette puis sur la pile
> Compose complète contre le vrai franceinfo.

| Question | Constat |
|---|---|
| Un direct comme *requête* (`annotate:` + `liq_cue_out`) ? | **Non.** La résolution d'un flux infini expire — `Time limit exceeded (timeout: 29.00)` — puis la file passe au suivant. Un direct n'est pas une requête |
| `input.http` alors ? | **Oui**, avec trois précautions ci-dessous |
| `self_sync` | **`false` obligatoire.** Sans lui, le serveur envoie sa rafale initiale (~650 Ko en 6 s), l'horloge de la sortie se cale dessus, et le morceau en cours est avalé — 8 s de musique jouées en 3 s |
| `normalize`/`crossfade` autour d'un `switch` contenant `input.http` | **Refusé à l'exécution** — `This source may control its own latency` — et `--check` **ne le voit pas** : le conteneur redémarrait en boucle. La bascule vers le direct se place **après** ces opérateurs |
| Mise en route | ~2 s entre `start()` et `is_ready()` sur cette machine — d'où le démarrage dès l'instruction, un morceau d'avance |
| Coupure | `stop()` à l'heure de fin **absolue** portée par l'instruction (`live:<epoch>:<url>`) ; le retour à la musique prend ~5 s de plus, le temps de vider le tampon |
| Jonction | `switch(track_sensitive=true)` **après** avoir gardé la file pleine : sur l'instruction `live:`, le script redemande aussitôt l'entrée réelle. Rendre `null()` à `request.dynamic` fait basculer au milieu du morceau — la source se déclare « pas prête » |
| Case courte | Une case **plus courte que deux morceaux** peut être sautée entièrement : le diffuseur a un morceau d'avance, et la jonction peut tomber après la fin de case. Conforme à « pas de rattrapage » (SPECS.md §7 n°22), et constaté avec une case de 2 min |
| Fuseau | `SystemClock` rend l'heure **locale** — mais un conteneur vit en UTC : sans `/etc/localtime` monté depuis l'hôte, un flash de 12:00 part à 14:00 en été. Constaté au premier essai, corrigé dans le Compose |

---

## 5.bis Quatrième relevé — la pause et le rebranchement (`GOAL-041`, le 2026-08-31)

> Même image (`v2.3.3`), maquette réduite : `request.dynamic(prefetch=1)` +
> `switch` sur `listeners()` + `output.harbor`, une fausse API qui horodate à
> la milliseconde, quatre MP3 de 8 s. Motif : le jingle de 19 h entendu à
> 22 h 28 — l'avance demandée avant la pause avait traversé 3 h 30 de silence.

| Question | Constat |
|---|---|
| L'avance survit-elle à la pause ? | **Oui.** L'entrée demandée d'avance pendant l'écoute reste dans la file de `request.dynamic` tant que personne n'écoute, et c'est **elle** qui part au rebranchement — c'est le bug constaté à l'antenne |
| Le morceau interrompu ? | Au rebranchement, Liquidsoap sert d'abord **le reliquat du morceau coupé** (~2 s constatées sur une coupure à 6 s d'un titre de 8 s), puis la file. SPECS.md §4.7 disait « jamais le milieu de celui qui passait » : c'est inexact tel quel |
| `set_queue([])` au repos | Vide la file **sans recomplètement** : aucun appel à l'API tant que personne ne tire. Le tirage suivant n'a lieu qu'à la demande — donc une purge au rebranchement produit bien un tirage **frais** |
| `prefetch` au démarrage à froid | Dans cette maquette (source non sélectionnée, `blank()` à l'antenne), **aucun** appel avant le premier auditeur — nuance par rapport à §1.3, où le script externe était appelé une fois au repos. L'avance ne se remplit que quand la source est tirée |
| Annoncer **avant** de rendre l'antenne | Dans `on_connect`, poster `listeners()+1` à l'API **puis** basculer le `ref` : l'API traite le branchement pendant que l'antenne est encore sur `blank()`. C'est ce qui rend la purge **sans course** : ordonnée depuis le gestionnaire de `/playout/listeners`, elle précède toujours la reprise du son |
| Le harbor pendant un `on_connect` bloqué | **Pas d'interblocage** : `/requeue` puis `/skip`, postés par l'API pendant que `on_connect` attend sa réponse, répondent 200 en ~5 ms chacun |
| La purge complète | `/requeue` (l'avance rassise ne jouera jamais) **puis** `/skip` (le reliquat du morceau interrompu est coupé) : l'entrée fraîche démarre **137 ms** après l'annonce. Sans le `/skip`, ~2 s de reliquat passent d'abord |
| `/skip` sans morceau en cours | **Pas inoffensif** : envoyé alors que rien n'a jamais joué, le saut reste enregistré et **mange le premier morceau** dès son départ (5 ms). Ne sauter que si un morceau passait quand la pause a commencé |

## 6. Points incertains — les métadonnées dans le flux (GOAL-020)

- [x] ~~Le mécanisme qui active les métadonnées ICY reste à trouver.~~
      **Trouvé le 2026-08-30, et c'est un bug amont** : `harbor.ml` passe les
      en-têtes clients **en minuscules** aux gestionnaires, et `harbor_output.ml`
      cherche `"Icy-MetaData"` avec sa casse — l'assertion échoue toujours,
      `metaint` devient −1, rien n'est émis. Constaté cassé en 2.3.3 **et** en
      2.4.5 ; corrigé sur `main` (`List.assoc_opt "icy-metadata"`), non publié.
      À réessayer au prochain déplacement d'épingle. La 2.4.5 casse par
      ailleurs notre script — `http.post` exige `synchronous`, `null()` est
      déprécié — ce qui reconfirme §1.7 : on ne bouge l'épingle qu'avec un
      relevé complet.
- [ ] La **pochette** : le protocole ICY ne transporte que `StreamTitle` et
      `StreamUrl`. Aucun flux MP3 n'embarque d'image ; les lecteurs qui en
      affichent une la récupèrent par un autre canal. Si l'envie reste, la
      piste sérieuse est `StreamUrl` pointant vers notre API — à relever
      contre de vrais lecteurs.
