# docs/liquidsoap.md — Relevé de Liquidsoap, et ce qui a décidé la migration
> **Relevé établi le 2026-08-30**, contre `savonet/liquidsoap:v2.3.3` (Docker),
> avec deux MP3 hétérogènes (44100/2/192k et 48000/1/128k) et `curl`. Rien
> n'est installé sur la machine hôte : `pacman` ne connaît pas le paquet.
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'une
> dépendance externe.** Ce fichier distingue ce qui a été constaté de ce qui
> reste à constater.

**Version constatée** : `Liquidsoap 2.3.3`. Image : **967 Mo**.

> **Depuis le 2026-09-07, le relevé porte sur deux versions.** Les sections 1 à
> 14 ont été mesurées sur la 2.3.3. **§15 relève la branche 2.4**
> (`savonet/liquidsoap:v2.4.x-latest`, 2.4.6+git, image de **1,12 Go**), vers
> laquelle l'épingle s'est déplacée pour obtenir les métadonnées ICY — et il dit
> lesquelles des sections précédentes sont à rejouer. **§16 les rejoue sur la
> 2.4**, avec le vrai `radio.liq` migré : c'est lui qui dit, pour chacune, si le
> constat de la 2.3.3 tient encore. **§17 referme le seul défaut qu'il a
> trouvé**, `normalize` qui tire sa source sans auditeur.

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

## 6. Les métadonnées dans le flux (GOAL-020, réécrit le 2026-09-07)

- [x] ~~Le mécanisme qui active les métadonnées ICY reste à trouver.~~
      **Trouvé le 2026-08-30, et c'est un bug amont** : `harbor.ml` passe les
      en-têtes clients **en minuscules** aux gestionnaires, et `harbor_output.ml`
      cherche `"Icy-MetaData"` avec sa casse — l'assertion échoue toujours,
      `metaint` devient −1, rien n'est émis. Constaté cassé en 2.3.3 **et** en
      2.4.5.
      **Corrigé sur la branche 2.4 depuis le 2026-07-22** (commit « fix ICY
      metadata negotiation », `1110b719`), mais dans aucune version publiée : la
      dernière est la 2.4.5 du 2026-06-15. L'image de branche
      `v2.4.x-latest` émet bien `icy-metaint` et les `StreamTitle` — §15 le
      mesure, et c'est ce qui décide le déplacement de l'épingle (GOAL-088).
      La 2.4.5 cassait par ailleurs notre script ; §15 dit exactement ce qu'il
      faut y changer, et confirme que `http.post` n'était **pas** en cause.
- [ ] **Chaque bloc ICY n'est livré qu'à un seul auditeur** sur la branche 2.4
      (§15.7). Corrigé amont par la PR #5003, fusionnée sur `main` le
      2026-04-28 mais **pas** portée sur `v2.4.x` ; la mesure sur
      `rolling-release-v2.5.x` le confirme réparé. Le défaut est **accepté et
      consigné** — décision de l'auteur, SPECS.md §7 n°47 — et se rouvrira le
      jour où l'amont le porte sur la 2.4.
- [ ] La **pochette** : le protocole ICY ne transporte que `StreamTitle` et
      `StreamUrl`. Aucun flux MP3 n'embarque d'image ; les lecteurs qui en
      affichent une la récupèrent par un autre canal. La seule piste restait
      `StreamUrl` pointant vers notre API — **écartée par décision de l'auteur**
      (GOAL-088) : le flux ne portera pas de `StreamUrl`. La question de la
      pochette reste donc ouverte, et sans piste ouverte de ce côté.

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

### Points incertains

- [ ] **Un `annotate:` imbriqué est-il résolu ?** Non observé. Un jingle
      replacé après un encore repasse par la charnière et reçoit un **second**
      préfixe (`annotate:…:annotate:…:/chemin`) : les fondus des jingles sont
      posés sans regarder ce que l'entrée porte déjà, alors que la coupe au
      plafond, elle, laisse passer une entrée déjà annotée. Rien ici ne dit si
      Liquidsoap lit la seconde annotation, la première, ou refuse l'URI —
      aucune manche ne l'a essayé (AGENTS.md §3).

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

- [x] ~~**`request.dynamic` peut-il commencer une entrée demandée avant une
      autre déjà commencée ?**~~ **Oui, mesuré en §12** dès que deux
      résolutions sont en vol — ce qui n'arrive qu'avec un `fetch()`. Ce qui
      suit reste la description du doute. Non observé alors, et l'API en dépend depuis
      GOAL-083-T05 : elle tient qu'une entrée plus ancienne qui n'a pas
      commencé a été jetée, faute de route pour l'apprendre de la purge de
      fin de direct. Ce qui est observé ici est plus étroit : après
      `set_queue([])`, un `/next` frais part et c'est ce morceau-là qui
      démarre. Avec `prefetch=1`, une seule entrée attend à la fois.
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

- [x] ~~Le morceau frais entre alors **sans fondu propre**, sous la seule rampe
      de prise d'antenne (2 s, §8).~~ **Tranché par §11** : il n'entre même pas
      toujours sous cette rampe. Elle est armée quand le `switch` rend
      l'antenne, pas quand le morceau frais entre ; dès que l'attente dépasse
      2 s, il entre à plein gain.
- [ ] Les 160 ms mesurées ici valent pour une API qui répond sur-le-champ.
      Le régime lent, et ce qu'il fait entendre, sont en §11.

---

## 11. Neuvième relevé — ce que `cross` sert quand l'entrée fraîche tarde (GOAL-074-T01, le 2026-09-06)

> Même image (`v2.3.3`). Maquette **fidèle** : le vrai `radio.liq` en conteneur
> contre une fausse API qui reproduit `declare_listeners` — la purge part de
> l'intérieur du gestionnaire de `/playout/listeners`, avant la réponse, donc
> pendant que le compteur du diffuseur est encore à zéro. Quatre tons purs de
> 25 s (a = 440 Hz, b = 660 Hz, c = 880 Hz, d = 1100 Hz), un auditeur `curl`,
> le flux MP3 reçu mesuré par fenêtres de 0,25 s : RMS, et fréquence dominante
> par passages à zéro — c'est elle qui dit **quel** morceau passe. Un seul
> paramètre change d'une manche à l'autre : le retard de `/playout/next`.

Motif : le 2026-09-06 au matin, l'auteur entend encore un micro-flash de la
veille, alors que le garde-fou de §10 (GOAL-055) fonctionne — le journal de
production porte bien « saut à antenne vide : le reliquat est jeté ». Ce que
§10 avait mesuré à **160 ms**, la production l'a montré à **7 s**.

| Question | Constat |
|---|---|
| Qu'est-ce qui décide du délai de la transition de `cross` ? | **La latence de l'entrée fraîche, et elle seule.** La transition ne peut pas s'exécuter avant que `b` ait `duration` en tampon ; `b` n'existe qu'une fois `/next` répondu et le fichier résolu. Deux manches, même script, même scénario : `/next` instantané → `Analysis … (1.96s / 2.00s)`, transition dans la seconde ; `/next` retardé de 4 s → `Analysis … (0.00s / 2.00s)`, transition 4 s après le saut. La maquette de §10 répondait sur-le-champ : elle ne pouvait mesurer que le premier régime |
| Où passe le tampon `before` pendant cette attente ? | **À l'antenne.** C'est ce que dit le `0.00s` : la transition ne trouve plus rien à jeter parce que la sortie a tout consommé. Mesuré dans le flux reçu : **2,00 s du ton `a`** — celui d'avant la pause — de 0,25 s à 2,25 s, sous la rampe de prise d'antenne, de −32,9 à **−16,7 dB**. Ce dernier chiffre est le niveau du **même ton à plein gain**, mesuré séparément dans la manche « rafale » (plateau à −16,7 dB) : la rampe de 2 s est finie quand le reliquat l'est, il sort donc **à plein volume** sur sa dernière fenêtre. Le garde-fou de §10 s'exécute ensuite, sur un tampon vide : il ne protège que le régime rapide |
| Que se passe-t-il une fois le tampon vidé ? | **L'antenne retombe sur `blank()`**, avec l'auditeur toujours branché : `programme` n'est plus prêt, le `switch` des auditeurs prend son second enfant. Mesuré : 2 s de silence absolu (−99 dB) entre le reliquat et le morceau frais. C'est la même ligne `Switch to blank with transition` vue en production le 2026-09-05 à 14:31:52, dix-neuf secondes avant que l'auditeur ne parte |
| Le morceau frais entre-t-il en fondu ? | **Au hasard du calendrier.** `antenne_prise` est armé quand le `switch` rend l'antenne, pas quand le morceau frais entre. En maquette le repli sur `blank` a réarmé la rampe 2 s avant l'entrée du frais, qui a donc fondu (−44 → −19 dB). En production le 2026-09-06, l'antenne a été reprise à 07:28:25 et le frais est entré à 07:28:28 : la rampe de 2 s était épuisée, il est entré **à plein gain**. Le point incertain de §10 se règle donc dans le mauvais sens, et il n'est pas déterministe |
| `output.harbor` sert-il une rafale d'octets déjà encodés à un auditeur qui se branche ? | **Non**, aux réglages de `radio.liq`. Protocole : A écoute le ton `a` à −16,7 dB, se débranche, l'antenne encode 1 s de silence, B se branche. Le flux de B commence sur le ton frais sous sa rampe, **sans aucune trace de `a`**. Un auditeur qui se rebranche n'hérite donc de rien : tout ce qu'il entend a été encodé pour lui. Le mot `burst` n'apparaît dans aucun réglage du script |

### Le correctif, mesuré sur la même maquette

Le témoin de §10 porte désormais aussi sur le gain (`gain_antenne`), et la
branche « reliquat » de la transition réarme la rampe.

| Manche | Avant | Après |
|---|---|---|
| `/next` retardé de 4 s | ton `a` de −32,9 à −16,7 dB pendant 2,00 s, puis 2 s de silence, puis `c` | **silence à −99 dB** pendant 4,25 s, puis `c` de −45 à −19 dB |
| `/next` instantané | ton `c` dès 0,50 s, sous la rampe | **inchangé** : ton `c` dès 0,50 s, sous la rampe |
| Un direct pris pendant l'intervalle | — | le direct s'entend, plateau à −24,6 dB : le muet ne le touche pas |

Le morceau frais entre désormais **sous une rampe** dans les deux régimes, ce
qui referme le point incertain de §10 : sans le réarmement, l'attente épuisait
la rampe et il entrait à froid.

### Ce que cela change

- Le témoin de §10 est **nécessaire mais pas suffisant**. Il vide le tampon que
  la transition tient encore ; il ne dit rien de ce que la sortie a déjà tiré
  en attendant. Ce qui protège l'auditeur ne peut pas être une transition, qui
  s'exécute trop tard : c'est le gain.
- La reprise à neuf (SPECS.md §7 n°30) n'a pas de version « rapide » et de
  version « lente ». Elle a un régime, et il dépend d'un temps de réponse —
  donc de la bibliothèque, du réseau, de la charge. Ce qui s'est bien passé le
  2026-09-02 était une API rapide, pas une correction complète.
- Un auditeur ne reçoit que ce qui est encodé pendant qu'il écoute : couper le
  son à la source suffit, il n'y a pas de tampon à purger derrière. Mesuré à
  **une seconde** d'écart entre le départ de l'un et l'arrivée de l'autre ; un
  rebranchement dans la même seconde n'a pas été essayé.
- **Le muet doit épargner un direct, et cela se déduit** de §9 et §10 plutôt
  que de se mesurer : §10 dit que le `on_track` du morceau frais — celui qui
  arme le direct — tombe **avant** la transition de `cross` ; §9 dit que le
  direct prend l'antenne ~1 s après cet armement. En régime lent, où la
  transition attend plusieurs secondes, le direct gagne donc la course, et
  sans garde-fou sa case entière serait muette. La maquette n'a mesuré que le
  régime rapide, où la transition arrive en 160 ms et où le direct la perd.

| `thread.run` sérialise-t-il les tâches qu'on lui donne ? | **Non.** Deux annonces lancées à 2 s d'écart, la première répondant en 6 s et la seconde tout de suite : côté API, « second » est reçu et répondu à 7,669 s, « premier » ne l'est qu'à 11,669 s. La seconde **double** la première. Passer `on_track` en asynchrone tel quel inverserait donc l'antenne — un jingle de 5 s suivi d'un morceau, avec une API lente, laisserait le jingle affiché sur la musique |
| Un verrou pour les sérialiser ? | **Il n'y en a pas.** `liquidsoap --list-functions` de la 2.3.3 ne donne que `thread.run`, `thread.run.recurrent`, `thread.delay`, `thread.on_error`, `thread.pause`, `thread.when`. Aucun mutex, aucune file. `thread.run.recurrent` est le seul fil garanti unique — mais la file qu'il consommerait serait écrite sans protection par le fil de diffusion |
| Le premier appel HTTP d'un processus | **Échoue, en 523, sans atteindre le serveur.** Constaté trois fois en maquette, l'API en écoute depuis plusieurs secondes et n'ayant rien reçu dans son journal. La même ligne apparaît au démarrage de chaque manche (« l'API n'a pas pris l'annonce des auditeurs (523) ») |

### Points incertains

- [x] ~~**Pourquoi `/playout/next` met-il 4 s, et parfois davantage.**~~
      **Répondu par GOAL-074-T05, et la cause est chez nous** : `next_entry`
      remplit toute l'avance dans la requête, soit `draw.lookahead + 1`
      tirages — neuf en production — contre un cache de bibliothèque expiré
      après une longue pause. Le remède est GOAL-075. Mesures : 4 s le
      2026-09-06 (purge à 07:28:21, réponse à 07:28:25) ; le 2026-09-05, le
      diffuseur a abandonné deux fois à `api_timeout` (10 s) avant de couper —
      on sait donc que c'était **plus de 10 s**, pas combien.
- [ ] **Ce que le 523 du premier appel fait perdre en production.** Si la
      règle vaut hors maquette, la première annonce d'un processus neuf est
      perdue : après un redémarrage du diffuseur, l'antenne pourrait rester
      muette d'un morceau. Non constaté en production, non expliqué.
- [ ] Combien de temps de silence un auditeur accepte à la reprise avant de
      croire la radio en panne. Seule l'écoute le dira (AGENTS.md §4.1).

---

## 12. Dixième relevé — passer un épisode de plage (GOAL-086-T01, le 2026-09-06)

> Même image (`v2.3.3`), en Docker sur la machine de développement. Maquette de
> §11 adaptée : la chaîne de `radio.liq` sans le direct — `request.dynamic
> (prefetch=1)` → `normalize` → `cross(duration=2.)` → `switch` sur les
> auditeurs → `amplify` — devant une fausse API qui horodate à la milliseconde,
> quatre tons purs de 25 s (a = 440 Hz, b = 660 Hz, c = 880 Hz, d = 1100 Hz),
> un auditeur `curl`. Le poids d'un épisode est simulé par un petit serveur
> HTTP Python qui sert `c.mp3` (401 283 o) à 50 000 o/s, soit **8 s** de
> résolution. Le flux MP3 reçu est mesuré par fenêtres de 0,25 s : RMS, et
> fréquence dominante par passages à zéro — c'est elle qui dit **quel** morceau
> passe.

Motif : une plage de podcasts (SPECS.md §7 n°35) enchaîne des épisodes ; un
« Passer » doit mener à un autre épisode, pas à l'avance déjà en file. Le
diffuseur tient une entrée d'avance et n'expose que `/skip` et `/requeue`.

| Question | Constat |
|---|---|
| `programme.fetch()` existe-t-il en 2.3.3 ? | **Oui**, et documenté. `liquidsoap -h request.dynamic` dans l'image le donne parmi les méthodes : « `fetch : () -> bool` — Try feeding the queue with a new request. Returns `true` if successful. This method can take long to return and should usually be run in a separate thread. » `liquidsoap --check` accepte un script qui l'appelle depuis un gestionnaire `harbor.http.register` |
| Est-il synchrone ? | **Oui, et il bloque le gestionnaire harbor.** Route `/fetch` appelée alors que `/playout/next` attend 6 s avant de répondre : `curl` mesure `code=200 temps=6.014s`, et le journal donne `[T] …077.9 /fetch : appel` puis `[T] …083.91 /fetch : rendu true` — 6,01 s. Il rend **`true`** quand la requête est résolue. Il **ne bloque pas la diffusion** : le ton à l'antenne continue sans accroc pendant l'attente (mesuré, aucune fenêtre sous −17 dB) |
| Que fait `fetch()` de la file ? | **Il ajoute une entrée par-dessus `prefetch`.** Après un `fetch()` seul, `programme.queue()` rend **2** au lieu de 1. Aucune entrée n'est perdue : la surnuméraire passe simplement au morceau suivant |
| Route combinée `/skip-fresh` (`set_queue([])` + `fetch()` + `skip()`), avec l'entrée fraîche lente | **L'épisode en cours continue jusqu'à la bascule, sans blanc.** Ordre à 8,05 s ; réponse HTTP à **8,048 s** (le gestionnaire est bloqué toute la résolution) ; le ton `a` tient de 0,50 à **16,50 s** sans discontinuité (−16,6 dB à l'ordre, −14,7 dB à la fin), le fondu de `cross` s'entend à 16,50 s, l'entrée fraîche à **17,00 s**. **Aucune trace de `b`** (660 Hz absent de toutes les fenêtres) : l'avance a bien été jetée, pas jouée |
| Mais quelle entrée fraîche ? | **Pas forcément celle que `fetch()` a résolue.** `set_queue([])` réveille aussitôt le fil d'avance de `request.dynamic`, qui tire lui aussi : deux `/next` partent dans la même milliseconde (journal : `suivant : http://…/c.mp3` puis `suivant : /liq/d.mp3`). `fetch()` tenait `c` (8 s de téléchargement), le fil d'avance a résolu `d` sur-le-champ — c'est **`d`** qui démarre au saut (1100 Hz à 17,00 s), et `c` joue ensuite. Un « Passer » coûte donc **deux tirages**, et l'ordre suit la fin de résolution, pas l'ordre des appels |
| `/requeue` puis `/skip` à ~50 ms, comme le ferait l'API | **Un blanc de 5,75 s.** `requeue` répond en 9,8 ms, `skip` en 4,6 ms. Ton `a` jusqu'à 10,25 s (les ~2 s que `cross` tient d'avance), puis **−99 dB de 10,50 à 16,00 s**, puis `c` à 16,25 s sous une rampe (−42 → −21 dB) — le `switch` était retombé sur `blank()` (`Switch to blank with transition`), comme en §11. Un seul tirage, et c'est bien l'entrée tirée qui joue |
| `/requeue`, 3 s d'attente, `/skip` | **Le blanc se réduit d'autant, sans rien avancer.** Ton `a` jusqu'à 13,00 s, silence de 13,25 à 16,00 s (**2,75 s**), `c` à 16,25 s. Les trois manches font entrer l'entrée fraîche à **16,25–17,00 s** : c'est le téléchargement qui commande, pas la méthode. Attendre ne fait qu'échanger du silence contre de l'épisode en cours |
| Au début d'une piste, qui part le premier : `/playing` ou le `/next` de recomplètement ? | **`/playing`, d'une milliseconde ou moins — et ce n'est pas garanti.** Trois jonctions d'une manche : `PLAYING` à 13.189 / `NEXT` à 13.190 ; 17.228 / 17.229 ; 21.230 / 21.231. Sur une autre manche, la **première** piste s'est annoncée dans l'autre sens (`NEXT` 9.170, `PLAYING` 9.171). Les deux appels sont **concurrents** : `on_track` poste depuis le fil de diffusion, le recomplètement depuis le fil d'avance |
| Le recomplètement attend-il la réponse de `/playing` ? | **Non.** Avec un `/playout/playing` qui met 3 s à répondre, le `/next` part quand même dans la milliseconde : `PLAYING` 13.067 / `NEXT` 13.067, puis `PLAYING repond apres 3.0s` à 16.067. Une API qui répondrait à `/next` en s'appuyant sur avoir déjà traité `/playing` n'a **aucune marge** |
| Ré-annoncer la piste en cours depuis un `ref` | **Oui.** Le corps du dernier `on_track` gardé dans un `ref`, re-posté par une route `/replay-playing` : le POST repart, avec **les mêmes métadonnées** (`/liq/s1.mp3 \| Episode \| Un`), en 8,7 ms. Après la jonction, c'est la nouvelle piste qui est re-postée (`… \| Deux`) |
| Une primitive qui rend les métadonnées de la piste en cours | **`source.last_metadata` existe** (`liquidsoap --list-functions` la donne ; `-h` : « Return the last metadata from the source », type `(source('a)) -> [string * string]?`), et `request.dynamic` la porte aussi comme méthode `last_metadata : () -> [string * string]?`. Mesuré sur la même manche : elle rend **exactement** ce que le `ref` gardait, `initial_uri` compris. Le `ref` n'est donc pas nécessaire — mais il ne coûte rien et ne dépend pas de l'endroit de la chaîne où on le lit |
| Le client qui abandonne pendant un `/skip-fresh` | **N'annule rien.** `curl --max-time 2` sur une route qui bloque 8 s : le client rend `000` à 2,00 s, le gestionnaire va jusqu'au bout (`fetch() = true` à +8,06 s) et le saut a lieu. L'API peut poster sans attendre |

### Ce que cela change

- Le choix n'est pas entre « avec » et « sans blanc », mais entre **un blanc** et
  **de l'épisode en trop**. L'entrée fraîche entre au même instant dans les
  trois manches (16,25–17,00 s pour 8 s de téléchargement) : ce que la route
  combinée gagne, elle le gagne en gardant l'antenne pleine pendant l'attente,
  pas en allant plus vite.
- `set_queue([])` **tire** dès qu'un auditeur écoute — nuance par rapport à
  §5.bis, qui l'avait mesuré au repos, source non tirée. Ajouter `fetch()`
  par-dessus fait donc **deux** tirages concurrents, et le plus rapide gagne
  l'antenne.
- Un gestionnaire harbor qui appelle `fetch()` est bloqué pour toute la
  résolution. Sur un épisode de 50 à 120 Mo, cela peut aller jusqu'à
  `settings.request.timeout` — **120 s** dans `radio.liq`. La route doit être
  postée sans attendre la réponse, et le journal du diffuseur reste le seul
  témoin de ce qu'elle a fait.

### Points incertains

- [x] ~~**`request.dynamic` peut-il commencer une entrée demandée avant une
      autre déjà commencée ?** (§9)~~ **Mesuré ici : oui, quand deux
      résolutions sont en vol.** L'entrée demandée en second (`d`, résolue en
      100 ms) a démarré avant celle demandée en premier (`c`, 8 s de
      téléchargement). Avec `prefetch=1` et le script tel qu'il est, une seule
      résolution est en vol à la fois et le cas ne se présente pas ; il
      n'apparaît **que** si l'on ajoute un `fetch()`. Ce que l'API tient depuis
      GOAL-083-T05 cesse donc de valoir le jour où la route combinée est
      adoptée.
- [ ] Ce que l'auditeur préfère entendre après un « Passer » : quelques
      secondes de plus de l'épisode qu'il vient de refuser, ou un blanc de la
      même durée. Aucune mesure ne le dira (AGENTS.md §4.1).
- [ ] Le temps réel de résolution d'un épisode de 50 à 120 Mo. Simulé ici à
      8 s ; **non mesuré** contre un vrai flux de podcast.
- [ ] Deux « Passer » coup sur coup, ou un `/skip-fresh` pendant qu'un autre
      bloque encore. **Non essayé.**

### Annexe — la route combinée de la maquette

```liquidsoap
def on_skip_fresh(request, response) =
  ignore(request)
  programme.set_queue([])
  ok = programme.fetch()
  log("fetch() = #{ok}")
  if piste_commencee() then sauter() end
  response.data("passe")
end
harbor.http.register(port=port, method="POST", "/skip-fresh", on_skip_fresh)
```

---

## 13. Onzième relevé — ce qu'`annotate:` accepte comme valeur (GOAL-086-T03, le 2026-09-06)

> Même image (`v2.3.3`), maquette de §12 réduite : `request.dynamic(prefetch=1)`
> → `normalize` → `crossfade(duration=2.)` → `switch` sur les auditeurs, fausse
> API horodatée, quatre tons purs de 25 s, un auditeur `curl`. Le `on_track` de
> la maquette journalise **toutes** les paires de métadonnées reçues.

Motif : pour qu'un processus `radio` neuf retrouve ce qui passe, l'entrée doit
se décrire elle-même (SPECS.md §7 n°42). §7 disait ce que Liquidsoap fait des
clés `liq_*` ; rien ne disait ce qu'il fait des autres.

| Question | Constat |
|---|---|
| Des clés `annotate:` **arbitraires** traversent-elles jusqu'à `on_track` ? | **Oui, telles quelles.** `kind`, `label`, `identifier`, `radio_kind`, `radio_label`, `radio_duration` : toutes apparaissent dans les métadonnées de `on_track`, à côté de `filename`, `initial_uri`, `rid`, `status`, `temporary` — et repartent donc dans le corps de `/playout/playing` |
| Une valeur **non citée** | **Un jeton simple seulement.** `label=Un%20episode` est refusé (`Error while parsing annotate URI … Char 18-21: Syntax error`), `identifier=ep-42` aussi (le tiret) ; `kind=show` et `kind=music` passent. Le refus porte sur **l'URI entière** : la requête n'est jamais résolue, l'entrée n'est **jamais jouée**, et la file passe à la suivante |
| Une valeur **citée** | **Tout passe.** `radio_label="A la French : \"n° 12\", dit-il"` est rendu à `on_track` comme `A la French : "n° 12", dit-il` : virgule, deux-points, accents, guillemets typographiques et `"` échappé traversent intacts |
| L'échappement de la contre-oblique | `\\` rend `\` ; une contre-oblique **brute** devant une lettre (`"Anti\Hero"`) est gardée telle quelle. Écrire `\\` pour `\` et `\"` pour `"` est donc correct dans les deux sens |
| `initial_uri` sur une entrée annotée | **Le préfixe entier**, confirmé §7 : l'API relit les annotations dans l'entrée qu'elle reçoit à l'annonce, sans lire les métadonnées |
| Une clé nommée `duration` | **Écartée par précaution, non mesurée.** Liquidsoap se réserve `duration` ; les clés du dépôt sont préfixées `radio_` pour n'entrer en collision avec aucune |
| `radio_duration="25"` sur un fichier de 25 s | **Ne coupe rien** : la piste tient ses 25 s (de 9,0 s à 32,0 s à l'antenne, fondu de 2 s compris) |
| Les fondus d'un jingle et la description dans **un seul** préfixe | `annotate:liq_fade_in=0.2,liq_fade_out=0.2,liq_cross_duration=0.5,radio_kind="jingle":/liq/b.mp3` : accepté, joué, et les six clés arrivent à `on_track` |
| `time()` posté en quatrième ligne de `/playout/playing` | **Les secondes Unix du diffuseur**, `1788725109.21`. C'est l'instant du vrai début, que la ré-annonce ne change pas |
| Une route `POST /announce` qui re-poste le dernier corps d'`on_track` | **Redit exactement le même corps**, `initial_uri` et horodatage compris, en moins de 10 ms. Sans annonce préalable, elle le dit et ne poste rien |

### Ce que cela change

- Toute valeur d'annotation écrite par le dépôt est **citée et échappée**. Une
  valeur mal citée ne dégrade pas l'annotation : elle fait perdre l'entrée.
- Le point incertain de §7 sur l'`annotate:` imbriqué reste entier, et il est
  désormais **contourné** : la charnière ne préfixe jamais une entrée qui porte
  déjà un `annotate:`, fondus des jingles compris.

### Points incertains

- [ ] Une clé qui porte le nom d'une métadonnée réservée (`duration`, `title`,
      `artist`) : ce que Liquidsoap en fait n'a **pas** été mesuré, le préfixe
      `radio_` évite la question.
- [ ] La longueur maximale d'un préfixe `annotate:`. Un titre d'épisode très
      long n'a pas été essayé.

---

## 14. Douzième relevé — remplacer l'avance sans la perdre (GOAL-086-T05, le 2026-09-06)

> Même image (`v2.3.3`), **maquette de §12 réutilisée telle quelle** : la chaîne
> de `radio.liq` sans le direct, fausse API horodatée à la milliseconde, quatre
> tons purs de 25 s (a = 440 Hz, b = 660 Hz, c = 880 Hz, d = 1100 Hz), l'épisode
> lourd simulé par `c.mp3` servi à 50 000 o/s (401 283 o, soit **8 s** de
> résolution), un auditeur `curl`, flux analysé par fenêtres de 0,25 s.

Motif : la route de §12 (`set_queue([])` → `fetch()` → `skip()`) coûte **deux**
tirages, le fil d'avance étant réveillé par la purge. On cherchait à n'en payer
qu'un : `fetch()` **d'abord** (la file passe à deux), puis
`set_queue([la fraîche seule])` pour retirer l'ancienne avance, puis `skip()`.

| Question | Constat |
|---|---|
| `request.id` et `list.mem` existent-ils en 2.3.3 ? | **Oui.** `liquidsoap -h request.id` : « Identifier of a request », type `(request) -> int` ; `list.mem` : `('a, ['a]) -> bool` |
| Nommer `request` le paramètre d'un gestionnaire harbor | **Il masque le module `request`.** `def on_x(request, response)` puis `request.id(r)` ne compile pas (`Error 5: this value has type (_.{id : _}, ...) -> _`). Le paramètre doit être renommé |
| `fetch()` puis `set_queue([la fraîche])` | **La file retombe à 0.** Journal : `file avant = 1 [1]`, `fetch() = true, file apres = 2 [1, 2]`, `fraiches = 1 [2]`, puis `set_queue fait, file = 0`. La requête rendue par `queue()` ne survit pas au `set_queue` suivant |
| `set_queue(programme.queue())`, l'identité | **Vide la file, elle aussi** : `avant = 1`, `apres = 0`. **`set_queue` détruit les requêtes qu'il remplace, y compris celles qu'on lui repasse.** Une entrée lue dans `queue()` ne peut donc pas y être réinstallée |
| Ce que la variante donne à l'antenne | **Pas de blanc, mais l'entrée fraîche est perdue.** Ton `a` de 0,50 à 16,50 s sans discontinuité (−16,6 dB à l'ordre, −14,7 dB à la fin), fondu à 16,50 s, entrée fraîche à 17,00 s. **Ni `b` (660 Hz) ni `c` (880 Hz)** dans aucune fenêtre : l'ancienne avance a bien été jetée, et `c` — les 8 s de téléchargement de `fetch()` — l'a été aussi. C'est **`d`** qui joue (1100 Hz de 17,00 à 41,00 s), tiré par le `/next` qui suit la purge |
| Ce que ça coûte | **Deux tirages quand même**, et le gestionnaire bloqué 8,04 s pour rien (`skip-fresh2: code=200 temps=8.038071s`). La file finit à 0 au lieu de 1 |

### Ce que cela change

- **La variante est impossible**, et pour une raison de principe, pas de
  réglage : `set_queue` détruit les requêtes de la file. `fetch()` ne peut donc
  pas précéder la purge, et l'ordre de §12 est le seul qui marche.
- **La route retenue est celle de §12**, avec son double tirage assumé :
  `set_queue([])`, `fetch()`, `skip()`. Ses deux tirages sont tous les deux
  **consommés** — le plus vite résolu prend l'antenne, l'autre devient l'avance
  — alors que la variante en jette un après l'avoir téléchargé.
- Conséquence pour l'API : elle ne peut pas savoir laquelle des deux entrées
  passe. Elle poste l'ordre **sans attendre**, et c'est le `/playout/playing`
  du diffuseur qui lui dit ce qui a réellement commencé.

### Points incertains

- [ ] Un moyen de retirer **une** entrée de la file sans la détruire. Aucune
      primitive de 2.3.3 ne l'offre à notre connaissance ; `queue()` et
      `set_queue()` sont les seules trouvées.
- [x] ~~Les deux entrées tirées par la route ne sont **pas** deux épisodes :
      `Shows.due()` rend `None` tant qu'un épisode demandé n'a pas pris
      l'antenne, donc la seconde est une musique.~~ **Corrigé par GOAL-087-T01**
      (SPECS.md §7 n°45 précisée) : pendant une plage, une seconde demande sert
      un autre épisode, d'un autre flux, jamais le même. La mesure ci-dessus
      reste valable — elle porte sur la route, pas sur ce qu'elle tire.
      Reste ouvert : ce que **deux téléchargements simultanés** de 50 à 120 Mo
      font à la bande passante, et ce qui passe après l'épisode fraîchement
      pioché, non mesuré à l'antenne.
- [x] ~~**Le double tirage contredit le rang des demandes.** Avec `/skip-fresh`,
      deux entrées sont en vol, et §12 a mesuré que l'entrée demandée en second
      démarre la première quand la plus ancienne est lente à se résoudre.
      L'hypothèse d'`_oublier_les_demandes_anterieures`
      (`webradio/app/liquidsoap_playout.py`, GOAL-083 — « une demande plus
      ancienne qui n'a pas commencé a été jetée ») cesse alors d'être vraie :
      elle n'a pas été jetée, elle joue plus tard.
      Rejoué le 2026-09-06 sur la pile réelle (`RadioProgramme` +
      `LiquidsoapPlayout` + `Shows`, `FrozenClock`), la musique de rang
      supérieur prenant l'antenne la première : l'épisode de rang inférieur est
      **oublié du registre**, et `_signaler_l_emission` appelle
      `Shows.dropped()`. Quand cet épisode joue ensuite, `_restaurer` le
      déclare correctement d'après ses annotations — nature émission, libellé,
      passable —, mais **rien ne l'inscrit comme diffusé** : `started()` ne
      reconnaît plus sa demande, `dropped()` l'ayant déjà oubliée. Il reste
      repiochable, et peut donc repasser dans la même plage.~~
      **Corrigé par GOAL-087.** La mesure tient : l'ordre des demandes ne dit
      plus lequel commence. Ce qui change est ce qu'on en conclut. T01 fait des
      deux entrées en vol deux épisodes, donc `dropped()` ne s'applique plus à
      celle de rang inférieur ; T02 ajoute `Shows.started_unregistered`, que
      `_restaurer` appelle quand une entrée d'émission inconnue du registre
      prend l'antenne — elle se retrouve par son adresse dans les catalogues en
      cache et s'inscrit. `_oublier_les_demandes_anterieures` continue d'oublier
      la plus ancienne du registre local, ce qui reste juste (elle ne doit ni
      s'annoncer ni se replacer) ; c'est d'en conclure qu'elle a été jetée qui
      ne l'était pas.
      **Reste à écouter** (AGENTS.md §4.1) : un vrai « Passer » en plage,
      l'épisode qui prend l'antenne et celui qui suit.

---

## 15. Treizième relevé — la branche 2.4 et les métadonnées ICY (GOAL-088-T01, le 2026-09-07)

> **Changement d'image.** Toutes les sections qui précèdent portent sur
> `savonet/liquidsoap:v2.3.3`. Celle-ci relève la **branche 2.4** :
> `savonet/liquidsoap:v2.4.x-latest`, soit « Liquidsoap 2.4.6+git@284f9c903 »,
> condensat `sha256:b27b11cfccd466265f605cd3de143bc019f4e0ed58db464297f04ed6ebea3efc`
> (`docker inspect --format '{{index .RepoDigests 0}}'`). Image **1,12 Go** au
> lieu de 967 Mo.
>
> Deux méthodes. Pour le script : une copie de `radio.liq` passée à
> `liquidsoap --check` contre l'image 2.4, corrigée et repassée jusqu'à `rc=0`.
> Pour les métadonnées : une maquette réduite — `request.dynamic(prefetch=1)`
> → `mksafe` → `output.harbor(%mp3(bitrate=128))` — branchée par
> `curl -H "Icy-MetaData: 1"`, le flux enregistré tel quel et découpé par un
> analyseur Python qui suit `icy-metaint: 8192` (16 000 o/s à 128 kb/s, donc un
> bloc toutes les 0,512 s) et n'imprime que les blocs qui **changent**. Les tons
> purs et la mesure de fréquence par passages à zéro sont ceux de §11 et §12.
>
> Comparaison faite à chaque fois avec la 2.3.3, et avec
> `savonet/liquidsoap:rolling-release-v2.5.x` (2.5.0+git@4198c46, publié le
> 2026-09-06) là où la 2.4 se révèle défaillante.

Motif : GOAL-088 veut que le flux annonce le titre en cours (`StreamTitle`).
§6 avait constaté que la 2.3.3 ne négocie **jamais** `icy-metaint`, même avec
`Icy-MetaData: 1` — bug amont de casse : `harbor.ml` passe les en-têtes clients
en minuscules, `harbor_output.ml` cherche `"Icy-MetaData"`, et l'assertion
`assert (List.assoc "Icy-MetaData" headers = "1")` (ligne 454 du tag `v2.3.3`)
échoue toujours. Le correctif amont existe — commit « fix ICY metadata
negotiation » du 2026-07-22, `1110b719` sur la branche `v2.4.x-latest`, entrée
CHANGES.md du 2026-08-04 — mais **aucune version publiée ne le porte** : la
dernière est la 2.4.5 du 2026-06-15. Sur Docker Hub, le tag `v2.4.x-latest`
date du 2026-09-05 et `rolling-release-v2.5.x` du 2026-09-06.

### 15.1 Ce que la 2.4 refuse de notre `radio.liq`

Quatre changements, obtenus en itérant `liquidsoap --check` jusqu'à `rc=0`.

| Question | Constat |
|---|---|
| `programme.on_track(on_track)` | **Refusé** (`Error 15: Missing arguments in function application: synchronous : bool`). En 2.4, **tous** les rappels de source exigent `synchronous` : `on_track`, `on_metadata`, `on_connect`, `on_disconnect`, `on_frame`, `on_wake_up` (commit amont « Make synchronous argument required in callbacks », #4619, 2025-08-10). La forme qui compile est `programme.on_track(synchronous=true, on_track)` |
| `http.post` est-il en cause ? | **Non**, contrairement à ce que §6 avançait à partir de la 2.4.5. `liquidsoap -h http.post` dans l'image 2.4 rend `string` avec les méthodes `status_code`, `status_message`, `headers` : `answer.status_code` reste valide, et `http.post.full` n'existe pas |
| `null()` | **Déprécié** (`Warning 5: Deprecated: use null`), 2 occurrences dans `radio.liq`. Le `null` nu est **refusé en 2.3.3** (« this value has no method find ») : la double compatibilité 2.3.3/2.4 est impossible |
| `on_connect` / `on_disconnect` en **argument** d'`output.harbor` | **Type changé** (`Error 5`), et l'argument est déprécié (« Please use the on_connect source method »). Le rappel ne reçoit plus une liste d'en-têtes mais un enregistrement `{headers, ip, protocol, uri}`. Forme retenue : `radio = output.harbor(...)` puis `radio.on_connect(synchronous=true, fun (client) -> … client.ip …)`, idem pour `on_disconnect` |
| `output.harbor` lui-même | **Journalise un avertissement au niveau 3** : « output.harbor code has not been update in a long while. Please reach if you wish to contribute to it otherwise we suggest using icecast! ». Rien d'autre ne change |
| Ce qui reste | Des `Warning 6` de masquage (`url`, `metadata`, `on_track`, `request` ×4), cosmétiques — le même piège qu'en §14 |
| Signatures vérifiées **inchangées** pour notre usage | `thread.run` (toujours sans `synchronous`), `cross`, `cross.simple`, `input.http` (`start`, `self_sync`, `max_buffer`), `harbor.http.register`, `request.dynamic` (`prefetch`, `set_queue`, `queue`, `skip`, `last_metadata`). `switch` garde `track_sensitive` et `transitions` en 2.4 — **absents en 2.5** |

### 15.2 `fetch()` devient asynchrone, et `/skip-fresh` casse

| Question | Constat |
|---|---|
| Le type de `programme.fetch()` | **`unit` en 2.4**, `bool` en 2.3.3 (§12). `liquidsoap -h request.dynamic` : « returns immediately and a new request is fetched in the background » |
| Ce que la route de §12 donne alors | **3,75 s de silence.** `/skip-fresh` répond en **11 ms**, le journal dit « fetch rendu … file=0 », puis le `skip()` tombe sur une file vide : l'antenne se tait jusqu'à l'entrée fraîche |
| Le remède, mesuré | `r = request.create(url)` ; `request.resolve(r)` — **bloquant**, ~4 s sur l'épisode lourd simulé ; `programme.add(r)` (`add : (request) -> bool`, « Requests are resolved before being added ») ; puis `skip()`. **Aucun silence** : le ton en cours tient jusqu'au saut, l'entrée fraîche entre au saut |
| Ce que ce remède coûte | **Deux tirages, comme en §12** — la purge réveille le fil d'avance. L'ordre de la file suit l'ordre de **résolution** |
| Ce qu'il impose au script | Le gestionnaire appelle `ask_next()` lui-même et **construit la requête**, cas `live:` compris : c'est lui qui a l'URL, `fetch()` ne la lui donne plus |

### 15.3 `normalize` avant `cross` casse `cross` en 2.4

Six manches, mêmes fichiers de 8 s, un seul paramètre : l'ordre des deux
opérateurs.

| Question | Constat |
|---|---|
| `normalize` puis `cross` — l'ordre de `radio.liq` | **`cross` ne fonctionne plus** : aucun `on_metadata` après `cross`, **aucun bloc ICY**, et des jonctions toutes les **8 s** au lieu de 6 s — donc ni recouvrement, ni fondu enchaîné. Un `skip()` rétablit ensuite les métadonnées, **mais pas le recouvrement** |
| `cross` puis `normalize`, ou `amplify` puis `cross` | **Corrects** : métadonnées à chaque jonction, période de **6 s** (8 s moins les 2 s de recouvrement) |
| Pourquoi | En 2.4, `normalize` est bâti sur `rms` + `delay_line` + `track_audio_amplify` — visible dans le journal des horloges |
| État amont | **Zone mouvante** : issue #5382 du 2026-08-31, PR #5378 fusionnée puis annulée |

L'ordre doit donc s'inverser dans `radio.liq` : `cross` d'abord, `normalize`
ensuite, toujours avant le `switch` du direct.

### 15.4 Ce que `StreamTitle` porte

Maquette ICY décrite en tête, `icy-metaint: 8192` négocié.

| Question | Constat |
|---|---|
| Un fichier étiqueté `artist=Un, title=La` | `StreamTitle='Un - La';` — c'est Liquidsoap qui assemble « Artiste - Titre » |
| Une entrée `annotate:artist=Jingle,title=Top:` | `'Jingle - Top'` : `annotate:` alimente `StreamTitle` comme une étiquette de fichier |
| Les mêmes entrées en **2.3.3** | **Pas d'`icy-metaint` dans la réponse, aucun bloc.** Le bug de §6 est bien ce qui empêchait tout |
| Un fichier **sans étiquette** (`c.mp3`) | **Un bloc de longueur 0** : rien n'est émis, et le **titre précédent reste affiché** chez le lecteur. Idem avec `annotate:radio_label=Top horaire:` seul — nos clés `radio_*` ne produisent aucun `StreamTitle` |
| `annotate:title="Top horaire":/liq/c.mp3` (fichier nu) | `StreamTitle='Top horaire';` — **pas de tiret**, l'artiste absent ne laisse pas de trace |
| `annotate:title="Jingle top":/liq/a.mp3` (fichier **déjà** étiqueté) | `'Un - Jingle top'` : `title=` écrase le titre du fichier, mais **l'artiste du fichier subsiste** |
| `annotate:artist="",title="Sans artiste"` | `' - Sans artiste'` : une valeur **vide ne retire pas la clé**, elle la vide. Annoter ne suffit donc pas à obtenir un libellé propre |
| `metadata.map(strip=true, …)` | **C'est lui qui nettoie.** Avec `metadata.map(strip=true, fun (m) -> if m["radio_kind"] != "" and m["radio_kind"] != "musique" then [("title", m["radio_label"]), ("artist","")] else [] end, s)` : un jingle étiqueté donne `'Top horaire'`, un générique `'Moment · Jazz'`, une musique reste `'Un - La'`. `strip=true` retire bien l'artiste vidé |

### 15.5 Le direct

| Question | Constat |
|---|---|
| `input.http` vers un distant qui **envoie** de l'ICY | **Relayé.** `'Un - La'` apparaît à la prise d'antenne (9,22 s, l'audio du direct à 9,25 s) |
| Un distant qui n'en envoie **pas** — le cas de France Info (docs/franceinfo.md) | **Rien n'est émis**, et le titre d'avant reste affiché pendant toute la case |
| Titrer le direct depuis le script | `live = metadata.map(insert_missing=true, fun (_) -> [("title","Direct France Info")], live_raw)` donne `'Direct France Info'` à 9,22 s, **à travers** `switch(track_sensitive=false, transitions=…)` posé derrière `cross`. `update=false` si l'on ne veut rien retenir du distant |
| La variante par la transition | `live_raw.insert_metadata([...])` **dans** la transition donne le même résultat. Elle doit viser la **source brute**, pas le `b` de la transition, pour rester homogène en type |
| Le **retour** à la musique en milieu de piste | **Aucun bloc n'est rejoué** — `replay_metadata=true` n'y change rien. Sans objet pour `radio.liq` : la fin de direct y purge et saute, donc une piste neuve commence |

### 15.6 Quand le titre change, par rapport au son

Maquette avec `cross(duration=2.)` et `cross.simple(fade_in=1., fade_out=1.)`.

| Question | Constat |
|---|---|
| L'instant du `StreamTitle` face au fondu | **Au début du fondu**, soit 0,2 à 0,5 s avant que le ton entrant domine : 6,66 s contre 6,75 s ; 12,29 contre 12,75 ; 18,43 contre 18,75 |
| L'instant du `on_track` de `request.dynamic` | **2 s plus tôt encore** — c'est la lecture d'avance de `cross` (§11) |

L'auditeur voit donc le titre changer un peu avant de l'entendre changer, et
l'API l'apprend deux secondes avant lui.

### 15.7 Plusieurs auditeurs : chaque bloc n'est livré qu'à un seul

| Question | Constat |
|---|---|
| Trois auditeurs branchés ensemble sur la 2.4 | **Chaque bloc ICY est livré à UN SEUL client.** Deux manches : `x` reçoit les titres 1 à 3, `z` le 4e, `y` **aucun**. Quatre jonctions, quatre blocs, consommés une fois chacun |
| Un auditeur qui rejoint **en cours** de morceau | **Ne reçoit pas le titre courant** : il attend la jonction suivante, et encore faut-il qu'il gagne le tirage |
| La cause amont | PR **#5003** : « metadata was previously consumed by the first listener in the list per frame, leaving all others stale ». Fusionnée sur `main` le **2026-04-28**, **pas** sur `v2.4.x` |
| La même maquette sur `rolling-release-v2.5.x` | **Corrigée** : `x` et `y` reçoivent tous les titres, et `z`, branché en retard, reçoit le titre courant dès son premier bloc |
| Passer en 2.5 pour autant ? | **Non, mesuré impossible en l'état** : la 2.5 refuse notre script (`switch` sans `track_sensitive`, §15.1), et `normalize` → `cross` y donne des jonctions à 4 s, non expliquées |

### Ce que cela change

- **L'épingle bouge**, et par condensat : c'est la décision de l'auteur
  (GOAL-088-T02). Aucune version publiée ne porte le correctif ICY, donc rien
  d'autre qu'une image de branche ne peut annoncer un titre.
- **`radio.liq` migre d'un bloc** : `synchronous=true` sur `on_track`, `null`
  nu, `on_connect`/`on_disconnect` par méthode, `fetch()` remplacé par
  `request.resolve` + `add`, `cross` **avant** `normalize`, masquages renommés.
  Il n'existe pas de version qui satisfasse les deux images à la fois.
- **Le libellé hors chanson se construit dans le script**, pas dans
  l'annotation : `title=` seul laisse l'artiste du fichier, et une valeur vide
  ne retire pas la clé. Seul `metadata.map(strip=true, …)` d'après
  `radio_kind`/`radio_label` donne ce que l'interface affiche (GOAL-088-T04).
- **Le défaut multi-auditeurs est accepté et consigné** (SPECS.md §7 n°47,
  décision de l'auteur), à revoir quand l'amont porte #5003 sur 2.4. Tant qu'il
  dure, un titre affiché par un lecteur ne dit rien de ce que les autres voient.
- **Des relevés antérieurs cessent d'être garantis**, parce qu'ils ont tous été
  faits sur la 2.3.3. Rejoués sur 2.4 en GOAL-088-T03, et le résultat est en
  **§16** :
  - [x] §1.5, §3 et §6 — en-têtes, `icy-metaint` sur le vrai script ;
  - [x] §5.bis et §9 — `on_connect` par méthode, annoncer avant de rendre
        l'antenne, `on_track` synchrone, direct ;
  - [x] §10 et §11 — reliquat, muet de reprise, rampe, avec `cross` devant
        `normalize` ;
  - [x] §12 et §14 — `/skip-fresh` réécrit ;
  - [x] §11 — le premier appel HTTP en 523 (non reproduit) ;
  - [x] le coût en CPU et en mémoire, l'image passant de 967 Mo à 1,12 Go ;
  - [ ] §1.4 et §7 — les fondus `liq_fade_*`, qui ne se constatent qu'à
        l'écoute (AGENTS.md §4.1) ;
  - [ ] §5 — `input.http` contre le vrai France Info, sur la pile Compose ;
        §16 l'a simulé par un serveur local.

### Points incertains

- [ ] **Les rappels `synchronous=false`** : sérialisés ou non, non mesuré. Le
      script ne s'en sert nulle part, mais §11 a montré que `thread.run` ne
      sérialise rien — rien ne dit que ces rappels-là font mieux.
- [ ] **Le régime lent de §11 sur la 2.4** : ce que la sortie tire pendant que
      l'entrée fraîche se résout n'a pas été rejoué. C'est GOAL-088-T03.
- [ ] **Le comportement de `cross` en 2.5** : les jonctions à 4 s avec
      `normalize` → `cross` n'ont pas d'explication, et la 2.5 n'accepte pas
      le script tel quel. Sans objet tant que l'épingle reste sur la 2.4.
- [ ] **La pochette** reste hors d'atteinte : le protocole ne transporte que
      `StreamTitle` et `StreamUrl` (§6). L'auteur a écarté `StreamUrl`, la
      question ne se rouvre donc pas de ce côté.
- [ ] **Un changement de titre peut-il faire décrocher un lecteur ?** Aucune
      maquette ne le dira : `curl` ne décroche de rien. C'est GOAL-088-T06, à
      l'écoute, sur de vrais lecteurs (docs/flux-icy.md §4, AGENTS.md §4.1).

---

## 16. Quatorzième relevé — les relevés rejoués sur la 2.4 (GOAL-088-T03, le 2026-09-07)

> **Image épinglée** : `savonet/liquidsoap@sha256:b27b11cfccd466265f605cd3de143bc019f4e0ed58db464297f04ed6ebea3efc`
> (2.4.6+git@284f9c903). Maquette **fidèle** : le **vrai `radio.liq` du dépôt**
> monté en lecture seule dans le conteneur, `--network host`, devant une fausse
> API Python qui sert `/playout/next`, `/playout/playing` et
> `/playout/listeners` et horodate tout à la milliseconde. Quatre tons purs de
> 25 s étiquetés (a = 440 Hz « Un - La », b = 660, c = 880, d = 1100), un
> auditeur `curl`, le flux MP3 reçu mesuré par fenêtres de 0,25 s : RMS et
> fréquence dominante — c'est elle qui dit **quel** morceau passe. Le direct est
> simulé par une route `/live.mp3` qui débite un ton de 1500 Hz à 16 000 o/s ;
> l'épisode lourd et le 404 par deux autres routes de la même API. Onze manches.
>
> **Témoin** : les mêmes manches sur `savonet/liquidsoap:v2.3.3` avec le script
> d'**avant** la migration (`git show fb75f2d^:…/radio.liq`). Sans lui, on ne
> saurait pas distinguer ce que la version change de ce que le script change.

### 16.1 Un défaut trouvé : `normalize` tire la source sans auditeur

C'est le seul écart qui casse quelque chose, et il ne vient pas de là où on
l'attendait.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §5.bis : « au démarrage à froid, **aucun** appel avant le premier auditeur » | Le script lancé, personne branché, journal de l'API pendant 6 s | **Différent, et c'est un défaut.** `NEXT#0` part **1 s après le démarrage** (à 2,054 s de la manche), le morceau est préparé, `on_track` tombe et `PLAYING /liq/a.mp3` est posté à 2,172 s. L'auditeur ne se branche qu'à 4,979 s et prend le morceau **en cours** |
| Le même scénario sur la 2.3.3 | Script d'avant la migration, image `v2.3.3` | **Rien avant l'auditeur** : `LISTENERS 1` à 6,983 s, puis `NEXT#0` à 7,089 s — 106 ms après. C'est bien la 2.4 qui change |
| D'où cela vient | Six manches d'isolement, un opérateur à la fois | **`normalize`.** Ordre inversé (`normalize` devant `cross`) : tire quand même. Sans `cross` du tout : tire quand même. Maquette minimale `request.dynamic` → `switch(listeners)` → `output.harbor` : **ne tire pas** ; plus `on_track(synchronous=true)` : ne tire pas ; plus `input.http(start=false)` et son `switch` : ne tire pas ; **plus `normalize` : tire**, deux entrées en 122 ms |

En 2.4, `normalize` est bâti sur `rms` + `delay_line` + `track_audio_amplify`
(§15.3) et consomme sa source en continu, quelle que soit la sortie. Comme il
est **avant** le `switch` des auditeurs dans `radio.liq`, la chaîne décode et
tire pendant que `blank()` est à l'antenne.

Ce que cela casse, mesuré :

- SPECS.md §1 (« rien n'est décodé ni demandé sans auditeur ») n'est plus tenu :
  un morceau est tiré, décodé et **annoncé** à l'API sans personne à l'écoute.
- Le premier auditeur d'un processus neuf prend le morceau en cours de route :
  2,8 s manquées en manche A.
- `piste_commencee` est vrai dès le démarrage. Le garde-fou de §9 (« un saut à
  vide mange le premier morceau ») ne refuse donc plus rien sur un processus qui
  vient de démarrer.
- Le premier bloc ICY servi est vide : le titre a été émis avant le
  branchement (§15.7), et le lecteur n'affiche rien jusqu'à la jonction.

**Non corrigé ici** : c'est GOAL-088-T08. **Corrigé depuis, et mesuré en §17** :
une `source.available` posée **avant** `cross` fige la chaîne jusqu'au premier
auditeur, et le démarrage à vide ne tire plus rien.

### 16.2 Les en-têtes et l'ICY sur le vrai script (§1.5, §3, §6)

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §3 : `icy-name` et `icy-br` servis tels quels | `curl -sD` sur `/stream` | **Identique** : `icy-name: local-webradio`, `icy-br: 128`, `Content-type: audio/mpeg` |
| §1.5 / §6 : `icy-metaint` jamais négocié, même avec `Icy-MetaData: 1` | La même requête avec l'en-tête, sur le **vrai** script cette fois | **Différent** : `icy-metaint: 8192` dans la réponse. Le témoin 2.3.3, même requête : aucun `icy-metaint`. §15.4 ne valait que pour la maquette réduite ; il vaut pour le script du dépôt |
| §15.4 : les blocs `StreamTitle` | Flux découpé par `metaint`, 26,6 s d'audio | **52 blocs**, un `StreamTitle` à la jonction : `StreamTitle='Deux - Le';` au bloc 46 (23,55 s d'audio). Sans `Icy-MetaData: 1`, pas de `metaint` et pas un octet de plus dans le flux |
| Le premier bloc | — | **Vide**, l'auditeur ayant rejoint en cours de piste (§15.7, aggravé par §16.1) |

### 16.3 Le branchement (§5.bis, §9)

Manche : `/playout/listeners` qui dort **3 s** avant de répondre, et qui poste
`/requeue` puis `/skip` au diffuseur depuis son gestionnaire, avant de répondre
— exactement ce que fait `declare_listeners`.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §5.bis : annoncer **avant** de rendre l'antenne | `on_connect` par méthode (2.4) ; instants du POST, de la réponse et de la bascule | **Identique.** `LISTENERS 1` posté à 4,974 s, l'API répond à 7,983 s, et c'est **alors seulement** que « auditeur branché » et `Switch to switch with transition` tombent. L'ordre annonce-puis-bascule survit au passage par méthode |
| §5.bis : pas d'interblocage quand l'API tarde | `/requeue` puis `/skip` postés pendant que `on_connect` attend | **Identique** : `200` en **7 ms** et **1 ms** (2.3.3 : ~5 ms chacun). La purge s'exécute pendant l'attente (« avance jetée », « saut demandé » dans la même seconde), le tirage frais part et l'antenne est encore sur `blank()` |
| Le dernier auditeur parti | `curl` arrivé à son terme | **Identique** : `LISTENERS 0` **dans les 100 ms** |
| §4 : « la déconnexion brutale d'un lecteur, non essayée » | `kill -9` sur le `curl`, horodaté à la milliseconde | **Mesuré pour la première fois** : `SIGKILL` à `…173.856`, `LISTENERS 0` à `…174.082` — **226 ms**. Le point incertain de §4 se referme pour ce cas-là seulement (voir les points incertains) |

### 16.4 Le direct (§9)

Manche : un direct instruit au tirage d'avance, pris à la jonction suivante,
rendu à l'heure dite ; deux cases enchaînées.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §9 : `on_track` arme `piste_commencee` et `direct_arme` | `on_track(synchronous=true, …)`, forme imposée par la 2.4 (§15.1) | **Identique** : l'annonce part du fil de diffusion et le témoin est armé au même instant. Rien ne trahit le changement de signature |
| §9 : le direct prend l'antenne ~1 s après le début de piste qui l'arme | Instants de l'`on_track` et du `Switch to live with transition` | **Plus rapide, et l'écart s'explique** : **10 ms** (`on_track` à 25,126 s, bascule et annonce à 25,136 s). §9 mesurait le délai de remplissage d'un `input.http` démarré à l'instant ; ici il coulait depuis 20 s. La règle « à la jonction, jamais au milieu » tient dans les deux cas |
| §9 : l'annonce du direct vient de la **transition**, une seule fois | Corps reçu par `/playout/playing` | **Identique** : `PLAYING live:1788794282:http://…` — l'entrée telle que l'API l'a rendue, **une** fois par prise d'antenne, sur les deux cases |
| §9 : l'avance dort **sous** le direct | Journal pendant la case | **Identique** : `d` est préparé et annoncé pendant que le direct est à l'antenne |
| §9 : la fin du direct purge et saute | Fin de case, avec un auditeur branché | **Identique** : « l'avance rassie est jetée, le reliquat coupé », `Analysis … (2.00 s / 0.00 s)`, nouveau `on_track` **1,9 s** après. Les deux secondes que `cross` tient du morceau gelé **passent quand même** (1,25 s de `d` mesurées à l'antenne) : `reliquat_a_taire` n'est armé qu'à antenne vide, et la case s'est terminée devant un auditeur. C'est le comportement de §10, pas un écart de version |

### 16.5 Le reliquat, le muet et la rampe (§10, §11)

Manche de §11 rejouée : un auditeur écoute, part, et revient six secondes plus
tard ; la purge part de l'intérieur du gestionnaire de `/playout/listeners`. Un
seul paramètre change d'une manche à l'autre : le retard de `/playout/next`.
L'établissement du flux coûte 3,00 s dans cette maquette — c'est l'origine des
temps donnés ci-dessous.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §10 : `cross` tient deux secondes du morceau coupé, la transition les jette | Régime rapide, `/next` immédiat, avec `cross` **avant** `normalize` | **Identique** : `Analysis … (1.88 s / 2.00 s)`, « saut à antenne vide : le reliquat est jeté », l'entrée fraîche à 4,25 s du flux — 1,25 s après l'établissement. **Aucune fenêtre à 440 Hz** : rien du morceau d'avant la pause |
| §11 : en régime lent, la sortie a déjà servi le reliquat, puis 2 s de blanc | `/next` retardé de **4 s** | **Identique au correctif de §11** : `Analysis … (0.00 s / 2.00 s)`, silence numérique complet jusqu'à 8,00 s, **aucune trace de 440 Hz**, puis `c` |
| §11 : le morceau frais entre sous une rampe réarmée (`gain_antenne`) | Fenêtres de 0,25 s à l'entrée du morceau frais | **Identique** : −50,5 dB à 8,25 s, puis −39,8, −34,5, −30,9, −28,2, −26,0, −24,1, −22,5, −21,3 et le plateau à −21,0 dB à 10,50 s. La rampe fait bien ses **2 s** |
| §15.3 : `cross` derrière `normalize` ne fonctionne plus | L'ordre inversé du script migré, sur le vrai `radio.liq` | **Confirmé dans le bon sens** : `Analysis` à chaque jonction, recouvrement de 2 s, fondu enchaîné audible sur toutes les manches |
| §11 : « le premier appel HTTP d'un processus échoue en 523 » | Les journaux des **dix** démarrages de conteneur de ce relevé | **Non reproduit** : pas un seul `523`, et la première annonce (`LISTENERS 0` du battement) est répondue `204` à chaque fois. Le défaut de §11 ne se constate pas sur la 2.4 |

### 16.6 « Passer » quand l'entrée fraîche se dérobe (§12, §14)

`/skip-fresh` réécrit en `next_entry()` + `request.resolve` + `add` (§15.2)
avait déjà été mesuré sans blanc en T02. Deux cas de bord restaient.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| §12 : la route combinée garde l'antenne pleine | L'entrée fraîche répond **404** | **Le saut tombe quand même**, et **sans blanc** : `/skip-fresh` répond en 6,2 ms, le journal dit « l'entrée fraîche ne s'est pas résolue, le saut aura un blanc », mais le tirage d'avance que `set_queue([])` a réveillé avait déjà résolu `c` — `a` tient jusqu'à 11,50 s (−15,8 dB à l'ordre, −26,8 dB en fin de fondu), `c` entre à 11,75 s. **Le message du journal est pessimiste** : il décrit ce qui arriverait si le second tirage tardait |
| §12 : un « Passer » coûte deux tirages, et le plus vite résolu gagne | `next_entry()` rend un **direct** | **Le saut tombe quand même.** Le gestionnaire tire `live:…` (« direct demandé pour 39 s »), redemande, retombe sur un `live:` (« un direct est déjà en cours, instruction ignorée »), conclut « aucune entrée fraîche à mettre en file » et saute ; réponse en **4,6 ms**. Le tirage d'avance réveillé sert `c`, dont l'`on_track` **arme le direct** : `c` s'entend **0,5 s** puis le direct prend l'antenne. Deux manches identiques |

### 16.7 Le coût (ARCHITECTURE.md §4)

`docker stats --no-stream`, deux lectures à cinq secondes d'écart, même machine,
même manche, l'image de 1,12 Go contre celle de 967 Mo.

| Relevé d'origine | Ce qui a été rejoué | Constat 2.4 |
|---|---|---|
| ARCHITECTURE.md §4 : « rien de décodé sans auditeur, ~0,8 % d'un cœur » | Conteneur sans auditeur | **1,79 % puis 2,00 %** de CPU, **83,0** puis **82,3 MiB**. Témoin 2.3.3 : **1,03 %** et **0,97 %**, 322,3 puis 328,4 MiB. Le surcroît de CPU est celui de §16.1 — la 2.4 décode pendant ce temps |
| §3 : « 80 Mo, 3 % de CPU avec un auditeur » | Un auditeur `curl` | **3,84 % puis 3,57 %**, **87,4** puis **86,0 MiB**. Témoin 2.3.3 : 3,04 % et 3,14 %, 81,7 puis 81,0 MiB. Même ordre de grandeur, ~0,6 point de CPU et ~5 MiB de plus |

### Ce que cela change

- **GOAL-088-T08 est ouverte** : `normalize` doit cesser de tirer la source
  quand personne n'écoute (§16.1). C'est SPECS.md §1 qui est en jeu, pas un
  détail de journal.
- **ARCHITECTURE.md §4 est faux sur deux points** — « rien de décodé sans
  auditeur » et « ~0,8 % d'un cœur » — tant que T08 n'est pas faite. La
  correction du document appartient à GOAL-088-T07.
- **Rien d'autre n'a bougé.** Les huit comportements sur lesquels le script
  s'appuie — annoncer avant de rendre l'antenne, l'absence d'interblocage, le
  témoin de piste, la prise du direct à la jonction, l'annonce par la
  transition, la purge de fin de case, le reliquat jeté, la rampe réarmée —
  se rejouent à l'identique sur la 2.4, aux millisecondes près.
- **§1.5 et §6 sont périmés pour la 2.4** : le vrai script négocie
  `icy-metaint` et émet des `StreamTitle`. C'est ce que GOAL-088 cherchait.
- Le `523` du premier appel HTTP (§11) **ne se reproduit pas** sur la 2.4. Rien
  ne dit qu'il a été corrigé ; il n'est simplement plus observable ici.
- **Une nuance de §3** : « `prefetch=1` demande un morceau avant le premier
  auditeur » valait pour la maquette naïve de GOAL-016, pas pour le script du
  dépôt — le témoin 2.3.3 ne tire rien avant le branchement. C'est §5.bis qui
  était exact.

### Points incertains

- [ ] **Pourquoi `normalize` tire en 2.4.** L'opérateur est identifié, la cause
      amont ne l'est pas — §15.3 signalait déjà une zone mouvante (issue #5382,
      PR #5378 fusionnée puis annulée). Le remède est à instruire en T08 ; on ne
      sait pas encore si un placement différent suffit.
- [ ] **La déconnexion vraiment brutale.** Ce qui a été mesuré est un `curl`
      tué : le noyau ferme la socket proprement, et le diffuseur l'apprend en
      226 ms. Un câble arraché ou une machine éteinte ne ferment rien, et le
      délai serait celui du `keepalive` TCP — **non mesuré**, la maquette étant
      en `--network host`.
- [ ] **Le direct est simulé.** `input.http` a été branché sur un serveur local
      débitant un ton ; les 15 s de mise en route de §3 et les **deux**
      `on_track` de §9 au démarrage d'un `input.http` n'ont pas été rejoués
      contre le vrai France Info (§5, à faire sur la pile Compose).
- [ ] **La mémoire de la 2.3.3 au repos** (322 MiB, contre 83 MiB en 2.4) n'est
      pas expliquée et repose sur deux lectures d'une seule manche.
- [ ] **Le multi-auditeurs** n'a pas été rejoué ici : §15.7 tient, un bloc ICY
      n'est livré qu'à un seul auditeur.
- [ ] **Ce qui ne s'entend pas en maquette** (AGENTS.md §4.1) : la reprise du
      matin après une longue pause, les fondus `liq_fade_*` d'un jingle (§1.4,
      §7), et si les 0,5 s de musique avant un direct pioché par « Passer »
      (§16.6) s'entendent comme un accroc ou comme une jonction.

---

## 17. Quinzième relevé — `normalize` sans auditeur (GOAL-088-T08, le 2026-09-07)

> **Même image épinglée** que §16
> (`savonet/liquidsoap@sha256:b27b11cfccd466265f605cd3de143bc019f4e0ed58db464297f04ed6ebea3efc`,
> 2.4.6+git@284f9c903) et **même maquette fidèle** : le `radio.liq` du dépôt —
> ici une copie par piste, un opérateur de différence — monté dans le
> conteneur en `--network host`, devant la fausse API horodatée de §16, quatre
> tons purs de 25 s étiquetés (a = 440 Hz « Un - La », b = 660, c = 880,
> d = 1100), un auditeur `curl`, le flux mesuré par fenêtres de 0,25 s (RMS et
> fréquence dominante). Six pistes essayées, puis six manches sur la piste
> retenue.

Motif : §16.1. En 2.4, `normalize` consomme sa source en continu quelle que
soit la sortie ; placé avant le `switch` des auditeurs, il faisait tirer,
décoder et annoncer un morceau devant `blank()`.

### 17.1 Ce qui arrête le tirage, et ce qui ne l'arrête pas

Manche identique pour les six : le script démarré, **personne branché**,
30 secondes de journal d'API.

| Piste | Ce qu'elle change | Constat |
|---|---|---|
| Le script tel quel (témoin du défaut) | — | **Trois tirages, deux pistes décodées** : `NEXT#0` à 2,085 s (1 s après le démarrage), `PLAYING /liq/a.mp3` à 2,192 s, `NEXT#1` dans la milliseconde, puis `PLAYING /liq/b.mp3` et `NEXT#2` à 25,1 s. La chaîne joue dans le vide, morceau après morceau |
| `source.available` **après** `cross`, avant `normalize` | `programme = source.available(programme, {listeners() > 0})` posé ligne 329 | **Insuffisant** : `NEXT#0`, `PLAYING a` et `NEXT#1` tombent quand même, aux mêmes instants. Rendre la source indisponible **derrière** `cross` n'empêche pas `cross` de commencer une piste pour répondre à `normalize` ; seul l'enchaînement s'arrête ensuite |
| `normalize` **après** le `switch` des auditeurs | `on_air = normalize(on_air)` | **Un tirage** (`NEXT#0`), aucun `PLAYING`. Le morceau demandé n'est pas décodé, mais il est demandé — donc l'avance vieillit sans auditeur (SPECS.md §7 n°30) |
| Sans `normalize` du tout | ligne retirée | **Un tirage**, aucun `PLAYING`. Identique à la précédente : c'est bien `normalize` seul qui décodait |
| `normalize.old` à la place | l'implémentation d'avant la 2.0 | **Un tirage**, aucun `PLAYING`. `normalize.old` ne tire pas sa source ; le défaut appartient au `normalize` bâti sur `rms` + `delay_line` + `track_audio_amplify` (§15.3) |
| `normalize(enabled={listeners() > 0}, …)` | le seul paramètre de `-h normalize` qui parle d'activité | **Sans effet** : trois tirages, deux `PLAYING`, comme le témoin. `enabled` gouverne le gain, pas la consommation. Aucun autre paramètre (`target`, `up`, `down`, `window`, `lookahead`, `threshold`, `track_sensitive`) ne touche au tirage |
| **`source.available` avant `cross`** (piste retenue) | `programme = source.available(programme, {listeners() > 0})` posé juste avant `cross` | **Rien** : aucun `NEXT`, aucun `PLAYING`, aucun décodage en 30 s. C'est le comportement du témoin 2.3.3 de §16.1 |

Le reste du script n'a pas à changer : `sauter()`, `set_queue`, `add` et
`skip()` visent la liaison `programme` **d'avant** le masquage, donc toujours
le `request.dynamic` (§14).

### 17.2 La piste retenue, rejouée

Six manches sur `source.available` avant `cross`.

| Manche | Constat |
|---|---|
| Démarrage sans auditeur, 30 s | **Aucun `NEXT`, aucun `PLAYING`.** Le journal du script s'arrête à « Switch to blank » |
| `/skip` sans auditeur, puis un auditeur | « saut demandé à vide : rien ne passe, il mangerait le premier morceau », et `a` joue entier ensuite (440 Hz sous la rampe dès 4,25 s). Le garde-fou de §9 refuse de nouveau |
| Premier auditeur puis une jonction | `icy-metaint: 8192` négocié ; `NEXT#0` **75 ms** après `LISTENERS 1`, `PLAYING` 121 ms après ; rampe de prise d'antenne de **2 s** (440 Hz : −52,8 dB à 4,25 s, −40,0, −34,1, −30,3, −27,4, −25,2, −23,3, −21,7, −20,5 dB à 6,25 s) ; jonction avec `Analysis … (1,98 s / 2,00 s)`, recouvrement mesuré de 27,25 à 27,75 s ; blocs ICY `StreamTitle='Un - La'` puis `'Deux - Le'` |
| Prise et fin d'un direct (deux cases) | Pris **à la jonction** (`Analysis` puis « le direct prend l'antenne » dans la même seconde), annoncé **une** fois par la transition (`PLAYING live:…`), 1500 Hz de 26,25 à 65,00 s ; fin de case : purge, saut, `Analysis … (2,00 s / 0,00 s)`, 1 s de `d` puis la case suivante. Conforme à §16.4 |
| Reprise après une pause, `/next` immédiat | « saut à antenne vide : le reliquat est jeté », **aucune fenêtre à 440 Hz**, `c` à 4,25 s à −54,1 dB sous la rampe |
| Reprise, `/next` retardé de 4 s | Silence numérique jusqu'à 8,25 s, **aucune trace de 440 Hz**, puis `c` à −50,5 dB sous la rampe — les chiffres de §16.5 |
| « Passer » sur un épisode lourd (50 000 o/s) | `/skip-fresh` répond en **8,014 s** (8,013 s en T02), `a` tient jusqu'à 19,50 s **sans blanc**, puis `d` — le second tirage a gagné la course, comme en §16.6. `Analysis … (1,98 s / 2,00 s)` |

### 17.3 Deux constats de passage

| Question | Constat |
|---|---|
| §5 : « `normalize`/`crossfade` en aval d'un `switch` contenant `input.http` est refusé à l'exécution » | **Plus vrai en 2.4.** La piste « `normalize` après le `switch` des auditeurs » a joué une manche entière de direct — deux cases prises et rendues — sans « This source may control its own latency » et sans redémarrage du conteneur. Elle a été écartée pour son tirage à vide, pas pour ce refus |
| Le coût au repos (§16.7, ARCHITECTURE.md §4) | **1,45 % puis 1,17 %** d'un cœur sans auditeur (72,6 puis 82,2 MiB), contre 1,79 et 2,00 % avec le défaut ; **3,97 % puis 4,75 %** avec un auditeur (87,5 et 86,4 MiB). Le décodage à vide disparaît, le « ~0,8 % » d'ARCHITECTURE.md §4 reste inexact |

### Ce que cela change

- **`radio.liq` porte une garde de plus** : `source.available(programme,
  {listeners() > 0})` juste avant `cross`. Le `switch` des auditeurs ne suffit
  plus depuis la 2.4 — il dit ce qui sort, pas ce qui est tiré.
- **La place est imposée** : derrière `cross`, la garde laisse `cross`
  commencer une piste. C'est le seul écart mesuré entre les deux placements.
- **SPECS.md §1 est de nouveau tenu**, et la phrase « rien de décodé sans
  auditeur » d'ARCHITECTURE.md §4 redevient exacte ; le chiffre de CPU qui la
  suit, lui, reste faux (GOAL-088-T07).
- **§16.1 est refermé.**

### Points incertains

- [ ] **Pourquoi `normalize` tire en 2.4** reste sans explication amont
      (§16.1) : on sait seulement que `normalize.old` ne le fait pas, et que
      `enabled` n'y change rien. Si l'amont corrige `normalize`, la garde
      devient inutile mais reste sans effet.
- [ ] **Le niveau sonore n'a pas été écouté** (AGENTS.md §4.1). Les manches
      montrent la montée lente de `normalize` après la rampe (−19,9 dB à 6,75 s,
      −14,1 dB à 26,0 s sur un ton pur) ; ce que cela donne sur de la musique
      ne se mesure pas ici.
- [ ] **Le dernier auditeur qui part au milieu d'un morceau.** La garde n'est
      pas `track_sensitive`, la source devient indisponible sur-le-champ —
      comme le `switch` juste après. Aucune manche n'a mesuré ce que devient
      alors le tampon de `cross` au rebranchement suivant, hors de la purge de
      reprise déjà rejouée ici.
