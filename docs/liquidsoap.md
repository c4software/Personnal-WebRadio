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
- [ ] Les deux entrées tirées par la route ne sont **pas** deux épisodes :
      `Shows.due()` rend `None` tant qu'un épisode demandé n'a pas pris
      l'antenne, donc la seconde est une musique. Ce que deux téléchargements
      simultanés feraient à la bande passante ne se pose donc pas ici ; ce qui
      passe après l'épisode fraîchement pioché n'est pas mesuré à l'antenne.
- [ ] **Le double tirage contredit le rang des demandes.** Avec `/skip-fresh`,
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
      repiochable, et peut donc repasser dans la même plage.
      **Résidu à écouter** (AGENTS.md §4.1) ; rien n'est corrigé ici.
