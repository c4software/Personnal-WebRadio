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

---

## 7. Cinquième relevé — ce qu'`annotate:` porte sur une requête

> Deux origines. Les fondus : GOAL-022, constatés **à l'écoute** sur la vraie
> radio (cette section manquait, le code y renvoyait déjà). La coupe :
> GOAL-047-T01, le 2026-09-01 — même image (`v2.3.3`), maquette
> `request.dynamic` + `normalize` + `crossfade(duration=2., fade_in=1.,
> fade_out=1.)`, deux MP3 de 8 s (440 et 880 Hz), sortie mesurée au `ffprobe`
> et à l'enveloppe RMS.

Le préfixe `annotate:cle=valeur,…:<uri>` ajoute des métadonnées que les
opérateurs lisent. Ce qui a été constaté :

| Question | Constat |
|---|---|
| `liq_fade_in`, `liq_fade_out`, `liq_cross_duration` | **Honorés par `crossfade`**, par requête : c'est ce qui donne aux jingles leurs fondus courts (GOAL-022, validé à l'oreille) |
| `liq_cue_out=<s>` sur un **fichier** | **Coupe au point dit.** `liq_cue_out=4.` sur un MP3 de 8 s : la sortie mesure 10,08 s au lieu de 14,08 s pour le témoin (8 + 8 − 2 s de fondu) — soit 4 + 8 − 2 |
| `liq_cue_out` sur une **URL HTTP** avec chaîne de requête (`?jeton=…&…`) | **Identique** : 10,08 s, la résolution télécharge puis coupe. La forme des URL Subsonic passe telle quelle |
| La jonction à la coupe | **Fondue, pas brutale** : le RMS du morceau coupé décroît régulièrement (−22 → −31 dB sur ~0,6 s) et le suivant démarre 2 s avant la coupe — le `crossfade` traite la coupe comme une fin de piste ordinaire |
| `initial_uri` à l'annonce | **Garde le préfixe `annotate:` entier** — la charnière peut donc l'utiliser comme clé de son registre, ce que `LiquidsoapPlayout` fait déjà pour les jingles |
| Un direct (flux infini) en `annotate:` + `liq_cue_out` | **Non** — relevé §5 : la résolution expire. Rien de neuf |

---

## 8. Sixième relevé — le fondu à la prise d'antenne (GOAL-050-T01, le 2026-09-01)

> Même image (`v2.3.3`). Maquette : `sine(440.)` derrière le `switch`
> `blank()` → programme de radio.liq, bascule à t=3 s, sortie MP3 mesurée à
> l'enveloppe RMS (`ffmpeg astats`, fenêtres de ~0,26 s).

La question : un auditeur qui déclenche la prise d'antenne (0 → 1 auditeur)
prend le son en pleine face — le `switch` bascule au milieu du morceau, plein
volume (témoin : −inf → −3,6 dB en une fenêtre). Comment fondre cette bascule ?

| Question | Constat |
|---|---|
| Un fondu **par auditeur** | **Impossible** : `output.harbor` encode une fois et sert le même flux à tous. Tout fondu est global — il ne peut porter que sur la prise d'antenne, pas sur chaque branchement |
| `transitions=[…]` sur le `switch` à `track_sensitive=false` | **S'exécute à la bascule** (`Switch to sine with transition`). La liste est complétée par `fun (x, y) -> y` ; `transition_length` plafonne à 5 s par défaut |
| Le typage de la liste `transitions` | **Homogène ou refus** : `fade.in(…)` rend une source enrichie de méthodes, la mélanger avec `fun (_, b) -> b` est une erreur de type |
| `fade.in` dans la transition | **Ne fond rien** : il agit sur les débuts de piste, et une source déjà entamée n'en présente aucun à la bascule — enveloppe mesurée **identique** au témoin, alors que la transition s'est bien exécutée |
| `amplify` piloté par l'horloge, armé par la transition | **Fond.** La transition pose `t0 := time()`, un `amplify({…})` en aval monte le gain de 0 à 1 en 2 s : RMS mesuré −24 → −3,5 dB, rampe régulière sur 2 s, indépendante des débuts de piste |
| `amplify` autour du `switch` contenant `input.http` | **Accepté à l'exécution** — contrairement à `normalize`/`crossfade` (relevé §3) : la structure complète de radio.liq, `input.http` compris, tourne et la rampe se mesure à l'identique |

### Points incertains

- [ ] La courbe : la rampe est linéaire en amplitude. À l'oreille, un fondu
      logarithmique peut sembler plus régulier — seule l'écoute le dira.

---

## 9. Septième relevé — le direct, le saut et l'antenne (GOAL-051-T01, le 2026-09-02)

> Même image (`v2.3.3`), en Docker sur la machine de développement. Maquette
> **fidèle** : le vrai `radio.liq` lancé contre une fausse API qui horodate à la
> milliseconde, quatre MP3 de 30 s, un auditeur `curl`, et le **vrai**
> `icecast.radiofrance.fr/franceinfo-midfi.mp3` comme direct. Motif : quatre
> défauts entendus à l'antenne le 2026-09-02 au matin, retrouvés dans les
> journaux de production.

| Question | Constat |
|---|---|
| Combien de fois `input.http` déclenche-t-il `on_track` au démarrage d'un direct ? | **Deux**, à ~3 ms d'intervalle. Maquette : `37.300`/`37.304` puis `38.949`/`38.951` sur deux manches. Production : `05:49:53.371`/`05:49:53.374`. Les deux annonces portent la même entrée — la charnière l'a consommée à la première, et la seconde lui arrive comme une entrée **inconnue et sans étiquettes** |
| `skip()` sur un `request.dynamic` où rien n'a jamais joué | **Mange l'entrée fraîche sur-le-champ** : `PLAYING a.mp3` à `8.617`, `PLAYING b.mp3` à `8.624` — 7 ms. Pire que ce que §5.bis mesurait : la cascade a avalé dans le même instant l'instruction `live:` **et** le morceau d'après. Le garde-fou de §5.bis est confirmé, et il ne suffit pas de le poser côté API |
| Un témoin fiable de « une piste passe », lisible **dans le script** | Un `ref` posé par le `on_track` du `request.dynamic`. Manche à froid : `piste_commencee=false`, aucun saut, `a.mp3` joue entier. Manche à chaud (une piste jouée, une pause, puis la purge) : `piste_commencee=true`, saut effectué, l'entrée fraîche démarre **140 ms** après la purge — les 137 ms de §5.bis. C'est le seul témoin qui vaille : `radio` redémarré seul croit qu'aucun morceau ne passe, alors que Liquidsoap en tient un depuis la veille |
| **`switch(track_sensitive=true)` derrière `crossfade`** | **Cesse d'évaluer ses prédicats.** Compteur posé dans le prédicat : **201 évaluations** tant que `blank()` est à l'antenne, puis **zéro** pendant deux minutes et quatre jonctions. Le direct n'obtient **jamais** l'antenne. `crossfade` ne présente aucune fin de piste au `switch`, et un `switch` sensible aux pistes ne reconsidère rien sans elle |
| Le même `switch` à `track_sensitive=false` | Le prédicat est évalué **en continu** (`n=1701`, `n=1801`…), `Switch to live with transition` tombe **2 s** après l'instruction — le temps que `input.http` soit prêt, cohérent avec §5 — et la transition s'exécute. Mais la bascule tombe alors **au milieu du morceau**, ce que SPECS.md §4.11 refuse |
| `transitions=[…]` sur le `switch` **du direct** | **Accepté à l'exécution**, `input.http` compris — contrairement à `normalize`/`crossfade` (§5). La transition du premier enfant s'exécute à la prise d'antenne, et un `thread.run({…})` y poste l'annonce à l'API sans bloquer le fil de diffusion |
| `set_queue([])` + `skip()` à la **fin** du direct | **Jette l'avance gelée sous le direct** : un `/next` frais part immédiatement et le morceau suivant démarre 140 ms après la coupure. Sans cela, le morceau gelé reprend là où il avait été suspendu — 2 min de musique hors plage constatées en production à 8 h |
| Un `ref` de fonction pour purger depuis `stop_live` | **Accepté.** `stop_live` est défini avant `programme` ; un `vider_l_avance = ref(fun () -> ())` déclaré tôt et affecté après la définition de `programme` lève la circularité |
| Un `def f(_, b) = b` sans `end` | **Erreur d'analyse à position fausse** : « At line 2, char 22-22: Parse error », quelle que soit la ligne fautive. Ne pas chercher à la ligne 2 |

### Ce que cela change

- Le témoin du saut **descend dans `radio.liq`** : c'est le seul endroit qui
  sait si une piste passe. `radio` l'ordonne toujours ; le script refuse à vide.
- L'annonce d'un direct ne peut pas venir de `live.on_track` : elle sort deux
  fois, et un morceau d'avance trop tôt. Elle vient de la **transition** du
  `switch` qui met le direct à l'antenne.
- La fin d'un direct est une **purge**, au même titre que le retour après une
  longue pause (SPECS.md §7 n°30) : l'avance qui dormait sous le direct est
  rassise de toute la durée de la case.

### Points incertains

- [ ] **Ce qui fait qu'une jonction traverse `crossfade` jusqu'au `switch`.**
      En maquette : jamais, sur quatre jonctions. En production le 2026-09-02 :
      **une fois**, 85 s après l'instruction, à la première jonction suivant une
      purge (`set_queue([])`). Tant que ce n'est pas établi, l'heure à laquelle
      un direct prend l'antenne n'est pas garantie — et c'est la cause du
      retard entendu à 7 h 51.
- [x] ~~Le compromis à trancher pour y remédier.~~ **Arbitré par l'auteur le
      2026-09-02** (GOAL-051-T06) : `track_sensitive=false` plus un témoin armé
      par le `on_track` du `request.dynamic`. Mesuré ensuite sur la même
      maquette : le direct prend l'antenne **1 s après le début de piste** qui
      l'arme — la jonction, donc — et la rend à l'heure dite. Le flux reçu ne
      porte **aucun silence** au retour à la musique (`silencedetect`, −50 dB,
      0,3 s : rien d'autre que les 5,4 s d'attente du tout premier morceau).
      Reste la question que seule l'oreille tranche : les ~2 s de fondu de
      sortie écourtées s'entendent-elles ?

---

## 10. Huitième relevé — le reliquat d'un saut à antenne vide (GOAL-055-T01, le 2026-09-02)

> Même image (`v2.3.3`). Maquette : la chaîne de radio.liq sans HTTP —
> `request.dynamic(prefetch=1)` → `normalize` → `crossfade(duration=2.)` →
> `switch` sur les auditeurs → `amplify` du fondu de prise d'antenne — sur
> trois tons purs de 20 s (a = 440 Hz, b = 660 Hz, c = 880 Hz). Un auditeur
> à t=1 (a joue, b est l'avance), parti à t=5, puis à t=9 la purge de
> reprise dans l'ordre de production : `set_queue([])`, `skip()`, compteur à 1.
> Sortie WAV mesurée par fenêtres de 0,25 s : RMS, et fréquence dominante par
> passages à zéro — c'est elle qui dit **quel** morceau passe.

Motif : à 13 h 20, l'auteur a entendu un micro-flash du morceau interrompu à
11 h 03. Le journal de production est sans ambiguïté — purge à 14.817, saut à
14.819, bascule à 14.863, puis `cross: Analysis: -12.9 dB / -nan (1.99 s /
0.00 s)` : deux secondes du morceau coupé, rien encore du suivant, et le
morceau frais annoncé 2,1 s après la bascule.

| Question | Constat |
|---|---|
| Que reste-t-il du morceau coupé après un `skip()` ordonné à antenne vide ? | **Ses deux dernières secondes lues.** `cross` tient `duration` de lecture d'avance ; le saut ne s'exécute qu'au premier tirage — donc après la bascule, quand l'auditeur écoute déjà — et ce tampon devient le `before` de la transition. Mesuré : 440 Hz de 9,0 à 9,75 s après la purge à 9,0, sous la rampe du fondu de prise d'antenne (−51 → −25 dB), puis 880 Hz. Le « reliquat coupé » de §5.bis et de SPECS.md §7 n°30 l'est donc à deux secondes près |
| `on_track` du morceau frais comme signal pour lever un silence | **Trop tôt.** Il tombe à 9,26 s, quand `cross` commence à lire le suivant d'avance — **avant** que le reliquat soit joué. Un `amplify` muet jusqu'à ce `on_track` laisse passer 440 Hz de 9,25 à 9,5 s : le flash est atténué, pas supprimé. En production, où l'entrée fraîche a mis 0,7 s à se préparer, il serait tombé après ; on ne peut pas s'appuyer sur cet ordre |
| La transition de `cross` | **Tient le reliquat en main.** `crossfade` est, dans `fades.liq` de la 2.3.3, un `cross(transition, s)` dont la transition appelle `cross.simple(fade_in, fade_out, initial_fade_in_metadata=b.metadata, initial_fade_out_metadata=a.metadata, a.source, b.source)`. Les deux sont publics. Une transition qui rend `b.source` seul quand un témoin le dit, et fait cet appel sinon, **jette le reliquat** : mesuré, aucune trace de 440 Hz après la purge, 880 Hz sous la rampe dès 9,25 s. La transition s'exécute 160 ms après la bascule ; ces 160 ms de reliquat passent sous un gain inférieur à 0,08 (−51 dB mesurés) |
| Une transition à deux branches — `b.source` ou `cross.simple(...)` | **Acceptée** au typage et à l'exécution, contrairement à `fade.in(...)` contre `fun (_, b) -> b` dans les transitions d'un `switch` (§8) |
| Des guillemets dans une interpolation `#{...}` | **Erreur d'analyse à position fausse** (« At line 2 »), comme le `def` sans `end` de §9. `"#{m["filename"]}"` refuse ; passer par une variable d'abord |

### Ce que cela change

- Le témoin du reliquat vit dans `radio.liq`, armé par le saut quand
  `listeners() == 0` — la purge de reprise comme la fin d'un direct sans
  auditeur — et consommé par la transition de `cross`.
- `crossfade` cède la place à `cross` avec cette transition : mêmes fondus,
  mêmes étiquettes `liq_fade_in`/`liq_fade_out` honorées, puisque c'est le
  même appel.

### Points incertains

- [ ] Le morceau frais entre alors **sans fondu propre**, sous la seule rampe
      de prise d'antenne (2 s, §8). Une entrée de morceau à froid s'entend
      différemment d'un fondu enchaîné ; seule l'oreille dira si la rampe
      suffit.
