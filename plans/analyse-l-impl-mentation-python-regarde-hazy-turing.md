# Analyse de l'implémentation Python — constats et plan de correction

## Contexte

L'auteur demande une relecture de correction de `webradio/`, confrontée à
SPECS.md, ARCHITECTURE.md et AGENTS.md. État de base constaté avant analyse :
`ruff format`, `ruff check`, `mypy` propres, 782 tests verts.

Méthode (mémoire `analyse-sous-agent-avant-realisation`) : lecture directe du
noyau et des charnières, puis trois relectures Fable en lecture seule (noyau,
`app/`, adaptateurs). **Chaque constat ci-dessous a été reproduit par un script
`python -c` sur le code du dépôt**, par moi ou par le relecteur. Rien n'a été
modifié.

Verdict global : l'architecture tient (aucune horloge, aucun hasard, aucune
entrée-sortie hors de leur place ; refus des votes, pagination Subsonic,
décroissance des votes, arbitrage des plages, minuit : tout vérifié conforme).
Les défauts sont concentrés sur **trois zones** : le relâchement de la fenêtre
dans la file, le cycle de vie de l'avance du diffuseur (purges, verrou, mémoire
des émissions), et la traduction des pannes réseau dans les adaptateurs.

## Constats

### BLOQUANT (audible, ou une émission perdue)

**B1 — La fenêtre de non-répétition est contournée dès qu'un artiste hors
fenêtre attend déjà.** `webradio/core/queue.py:263-271`. Quand `hors_fenetre`
n'est pas vide mais que tous ses artistes sont dans l'avance, le code prend
`allowed = candidates` (fenêtre comprise) au lieu de `allowed = hors_fenetre`.
Reproduit : A vient de passer, B attend → la file retire **A**, avec le journal
« un artiste déjà en attente repasse » (faux coupable). Sur une plage étroite
avec `lookahead = 8`, le titre qui vient de passer peut revenir. SPECS §4.2,
§4.8. Introduit par GOAL-082-T02 (commit 9f479c9 et précédent). Le test
`test_queue.py:431` n'affirme qu'une longueur et ne le voit pas.

**B2 — Un épisode est inscrit « diffusé » à la demande du diffuseur, pas à sa
diffusion.** `webradio/app/show_scheduler.py:435` (`record_airing` dans
`_episode_de`), `:171` (YouTube), `:128` (`_cases_rendues` pour un direct).
L'entrée rendue par `/playout/next` n'est que l'**avance** ; trois purges la
jettent sans la rejouer : la reprise à neuf (`liquidsoap_playout.py:419-438`),
« Autre thème » sur une suite (`drop_advance`, `:335`), la fin d'un direct
(`radio.liq`). Reproduit : émission 20:00, épisode 60 min, jonction 20:01 →
épisode rendu et inscrit ; auditeur parti, revenu 20:21 → purge → musique, et
`due()` répond « rien de neuf ». L'épisode hebdomadaire ne passera jamais.
Même chose si Liquidsoap n'arrive pas à résoudre l'URL. SPECS §4.11 (rattrapage,
n°13, n°14).

### À CORRIGER (faux, mais borné)

**C1 — Rompre une suite d'artiste écarte toutes les pistes sans année.**
`queue.py:237-241` : `era_of(t) != directive.avoid_era` avec `avoid_era = None`
exclut les pistes sans année. Reproduit : « Autre thème » sur `artist_fan`
retire le **même** artiste et journalise « rien d'autre que « X » » alors que
Y et Z existent. SPECS §4.4 (GOAL-059).

**C2 — Plage au hasard dont le tirage échoue : la file et la grille ne parlent
plus la même clé.** `core/bands.py:261-264` rend `None` (clé `None` pour la
file) tandis que `moment_at` rend `(band, occurrence, None)`. Conséquence :
`revalidate` jette toute l'avance à chaque `prepare` (jusqu'à 8 tirages par
cycle) et « À suivre » est vide tant que dure l'occurrence. Cas réel :
`random = "genre"` sur une bibliothèque sans genre, ou source indisponible.

**C3 — `Runs` n'a qu'un état : préparer un titre sous l'occurrence suivante
efface la suite en cours, sans journal.** `core/runs.py:130-140`. L'avance
(n°34) est tirée sous des moments différents ; la suite d'artiste promise
(3 à 6) est coupée dès que l'avance chevauche la plage suivante et qu'un
retrait ou un `stop` fait retirer. Même famille que GOAL-076 (mémoire de
`mystery.py` indexée par occurrence).

**C4 — Le jingle d'une heure tombée pendant une émission passe à la jonction
qui suit l'émission.** `core/jingles.py:82-104` n'abandonne que si `due_now`
est appelé *pendant* l'émission ; `app/playout.py:356` ne l'appelle qu'aux
jonctions, et une émission n'en a pas. Reproduit : émission 20:01→21:10,
`21h.mp3` rendu à 21:10. Idem `12h.mp3` après un flash 11:57→12:02.
SPECS §4.11, n°15 (« ni différés »). `test_jingles.py:86` teste une séquence
qui n'existe pas en production.

**C5 — À la fin d'un direct, l'avance gelée reste dans `_en_attente`.** Le
script la jette (`set_queue([])`) mais l'API ne l'apprend pas
(`liquidsoap_playout.py:202-207`). Elle est annoncée dans « À suivre », compte
dans les heures estimées, et au premier battement après l'heure pleine elle est
**replacée et diffusée** (`stash_for_replay`, même moment). Contredit n°22
révisée et n°33.

**C6 — Course battement / `/playing`.** `_remettre_l_avance_en_question`
(`:391-417`) juge « en avance » tout ce qui n'est pas `_entree_en_cours` ;
si le battement passe avant `/playing T` (qui attend le verrou pendant une
préparation), T est replacé puis **rejoué**, et l'antenne affiche le titre
précédent.

**C7 — Quatre chemins Flask mutent la file hors du verrou** pendant que le fil
de fond lit `Queue._avance` : `withdraw → programme.withdraw`
(`liquidsoap_playout.py:298`), `stash_for_replay` `:320-327`, `drop_advance →
forget_advance` `:343`, `_repartir_a_neuf → forget_pending` `:434`.
Reproduit avec deux fils : `IndexError` sur `self._file.advance[-1]`
(`playout.py:191`), non attrapé, la préparation s'arrête.

**C8 — `radio` redémarré pendant une pause ne date pas la pause.**
`liquidsoap_playout.py:359-362` : `_pause_depuis` n'existe qu'après un
battement à zéro reçu par *ce* processus. Un déploiement matinal avant le
premier auditeur reproduit exactement le cas de la n°29 (jingle de la veille).

**C9 — Une réponse HTTP tronquée n'est pas traduite en erreur métier.**
`http.client.IncompleteRead`, `BadStatusLine` et toute `HTTPException` ne sont
pas des `OSError` ; `subsonic.py:96-102` et `:358`, `podcast/feed.py:95-100`,
`youtube/channel.py:180-184` n'attrapent que `OSError`/`URLError`. Une page
`search3` coupée en route → 500 sur `/playout/next`. ARCHITECTURE §7, AGENTS §4
(cas « tronqué » exigé, absent des tests).

**C10 — `timeout_seconds = 0` passe la validation puis plante ou tue en
silence.** `config/schema.py:873, 891, 899` acceptent 0 ; `database.py:138` et
`feed.py:86` lèvent une `ValueError` brute à l'assemblage ; `youtube` avec 0
fait échouer chaque `subprocess.run` par `TimeoutExpired`. `subsonic` a déjà
`minimum=0.1` (l.821). SPECS §6.

**C11 — Date `<published>` malformée dans le flux Atom YouTube** :
`channel.py:227` `fromisoformat` sans garde → `ValueError` brute. `feed.py:123`
fait la garde pour les podcasts.

**C12 — Identifiant de chaîne lu au mauvais segment** : `channel.py:192-193`,
`…/channel/UC123/videos` donne `videos`.

**C13 — Interdits AGENTS §2** : code mort `_dans_la_plage`
(`schema.py:808`), `Pending.nature` (`liquidsoap_playout.py:57`),
`MusicSource.genres()` sans appelant (`sources.py:55`, implémenté dans Subsonic
et le Fake) ; paramètre ignoré `now_playing` (`playout.py:78,93`,
`main.py:509`) et `command` dans `vote_weight` (`weighting.py:65`) ;
`timeout=3` et URL par défaut en dur (`main.py:259,268`).

**C14 — Tests qui n'affirment pas ce qu'ils nomment** : `test_queue.py:431`
(longueur seule, cf. B1) ; `test_control.py:136` tautologique (`Control` n'a
pas de `Window`) ; `test_weighting.py:28-36` nommés d'après le tableau périmé
de §4.12 ; `test_show_scheduler.py:200` (aucun flux configuré) ;
`test_jingles.py:86` (cf. C4).

### À DISCUTER (ambiguïté, ou choix)

- **D1** `encore` ignore ce que la **file** a joué (`control.py:139`, `_servis`
  ne retient que ses propres services) : la file joue b1 puis b2, encore sur
  b2 → b1. SPECS §4.6 dit « morceau **non joué** ».
- **D2** Le verrou couvre toute la préparation (`liquidsoap_playout.py:151`) :
  `/playing`, donc `on_track` de Liquidsoap, et le `/next` de préfetch
  attendent jusqu'à `lookahead` tirages (cache Subsonic **par genre**, donc un
  parcours entier à chaque plage nouvelle). GOAL-075 a sorti la préparation de
  `/next`, pas du chemin critique ; c'est aussi la fenêtre de C6. À mesurer
  (GOAL-075-T03) avant de trancher.
- **D3** Un jingle replacé après un encore reçoit un second `annotate:`
  (`liquidsoap_playout.py:118`) ; docs/liquidsoap.md ne dit pas si Liquidsoap
  résout un `annotate:` imbriqué. À relever, pas à supposer.
- **D4** Changement d'heure : `full_hours_between` sur des décalages fixes
  (jingle `02h` inexistant, `03h` sauté) ; purge du journal par comparaison
  texte ISO (`database.py:311-322`), fausse d'une heure deux nuits par an.
- **D5** « Autre thème » pendant une panne de source perd le thème en cours
  (`mystery.py:73-78`, `pop` avant `_draw`).
- **D6** Le sel Subsonic tire douze valeurs par appel dans le **même**
  `RealRandom` que la file (`main.py:185,206`) : la rejouabilité à graine fixée
  (ARCHITECTURE §5.3) dépend du nombre d'appels réseau.
- **D7** SPECS §6 a dérivé du schéma (clés `[[emissions]]`, `jours`, `heure`,
  « flux : format, débit », « informations » n'existent plus ; `jingles.encore`,
  `youtube.timeout_seconds`, `intro/outro`, `stream`, `duration_minutes`
  n'y sont pas) ; §4.12 « Ce que chaque geste pèse » contredit n°16 ;
  `jingles.encore` contredit AGENTS §2 (« ne pas ajouter de table »).
- **D8** `feed` unique + `end` est accepté (`schema.py:705`) : la plage ne peut
  enchaîner qu'un épisode.
- **D9** L'estimation des heures ne coupe au plafond que le morceau en cours,
  pas les durées de l'avance (`liquidsoap_playout.py:178,274`,
  `playout.py:191,270`).

## Plan de correction

Un Goal dans TASKS.md, **GOAL-083 — Ce que la relecture du 2026-09-06 a
trouvé**, une tâche par constat, **un commit par tâche**, `./verifier.sh`
constaté avant chaque commit (AGENTS §1). Ordre : bloquants, puis les
corrections par zone, puis les interdits. Les « à discuter » deviennent des
décisions écrites (SPECS §7) ou des tâches, selon les réponses de l'auteur.

### T01 — B1, la fenêtre (`core/queue.py`)
Remplacer `allowed = candidates` par `allowed = hors_fenetre` quand
`hors_fenetre` n'est pas vide ; ne retomber sur `candidates` que si la fenêtre
est déjà vide. Test : A vient de passer, B attend → B sort, jamais A.
Renforcer `test_queue.py:431` pour affirmer l'artiste tiré.

### T02 — B2, la mémoire des émissions (`app/show_scheduler.py`,
`app/liquidsoap_playout.py`)
Inscrire la diffusion **quand Liquidsoap dit avoir commencé** (`playing()`),
pas à la demande : `Shows` retient « demandé, pas encore inscrit » par entrée,
et `LiquidsoapPlayout.playing` déclenche `record_airing` ; une purge
(`_repartir_a_neuf`, `drop_advance`, C5) oublie ce qui n'a pas commencé.
Attention à la double demande : tant que l'épisode attend, `due()` doit le
rendre à nouveau ou rendre `None` sans l'inscrire — à trancher en écrivant,
avec un test « purge avant diffusion → l'épisode repasse ».

### T03 — C4, jingles pendant une émission (`app/playout.py`)
À la jonction qui suit une émission, abandonner les heures pleines tombées
**entre le début et la fin** de l'émission : `Jingles` reçoit l'intervalle à
oublier (ou `playing()` d'une émission avance le repère à sa fin). Réécrire
`test_jingles.py:86` sur la vraie séquence.

### T04 — C5 + C6, le registre du diffuseur (`app/liquidsoap_playout.py`)
Fin de direct : purger `_en_attente` quand `/playing` reçoit une entrée
inconnue après un direct, ou ajouter un signal explicite du script (préférer
le second : le script sait qu'il a jeté). Course : ne replacer que ce qui a été
**décidé avant** la dernière annonce, ou faire tolérer à `playing()` une entrée
déjà replacée (la retirer de `_a_rejouer`).

### T05 — C7, le verrou (`app/liquidsoap_playout.py`)
Prendre `_verrou` autour de `programme.withdraw`, `replay_later`/
`current_moment`, `forget_advance`, `forget_pending`. Test à deux fils, ou
un Fake qui vérifie le verrou tenu.

### T06 — C8, la pause inconnue au démarrage
Sans `_pause_depuis` et sans `_entree_en_cours`, un premier battement > 0
traite la reprise comme longue (purge), ce que docs/liquidsoap.md §9 justifie
déjà pour le saut.

### T07 — C1 + C2 + C3, le noyau des suites
`queue.py:240` : ne comparer l'époque (resp. l'artiste) que si `avoid_era`
(resp. `avoid_artist`) est défini. `bands.py:264` : rendre
`Constraint(run_key=key)` au lieu de `None`. `runs.py` : indexer l'état par
clé d'occurrence (`dict`, bornée comme `MEMOIRE_MAX` de `mystery.py`).

### T08 — C9 + C11 + C12, les lecteurs réseau
Attraper `http.client.HTTPException` dans les trois lecteurs ; garder la date
Atom ; prendre le segment qui suit `/channel/`. Tests littéraux : réponse
tronquée, `<published>` illisible, URL `/channel/UC…/videos` (AGENTS §4).

### T09 — C10, la configuration
`minimum=0.1` sur `state`, `podcast`, `youtube` `timeout_seconds`, avec tests.

### T10 — C13 + C14, interdits et tests
Supprimer `_dans_la_plage`, `Pending.nature`, `now_playing` ; décider pour
`MusicSource.genres()` (retirer du `Protocol`, de Subsonic et du Fake) et
`vote_weight(command)` ; sortir `timeout=3` et l'URL Liquidsoap vers le TOML
(SPECS §6 mis à jour). Renommer les tests de `test_weighting.py`, remplacer
`test_control.py:136` par un test dans `test_playout.py`, donner un flux au
direct de `test_show_scheduler.py:200`.

### T11 — D1, l'encore connaît ce que la file a joué (décision de l'auteur :
corriger)
`Control.track_after_more` reçoit les titres joués récemment : la charnière
(`app/playout.py`, qui voit passer chaque `Pick`) alimente une mémoire bornée
de `Control` (`played(track)`), fusionnée avec `_servis` dans `ecartes`.
Test : la file joue b1 puis b2, encore sur b2 → jamais b1 tant que b3 existe.

### Documentation
SPECS §6 réaligné sur le schéma (D7), §4.12 réconcilié avec n°16 ;
ARCHITECTURE §4.1 note la dépendance implicite « `prepare()` avant chaque
jonction » ; D2 reste rattachée à GOAL-075-T03 (mesure) ; D3 devient un
point incertain de docs/liquidsoap.md ; D4, D5, D6, D8, D9 consignés en SPECS
§7 comme décisions ouvertes, sans code.

## Décisions de l'auteur (2026-09-06)
- Périmètre : **tout ce qui est confirmé** — GOAL-083, T01 à T11.
- D1 : **corriger** (T11).

## Vérification

- `./verifier.sh` après chaque tâche, sortie constatée.
- Pour B1, C1, C2, C3, C4 : un test qui **échoue sans le correctif**, vérifié en
  le retirant (méthode de GOAL-082-T02).
- Pour B2, C5, C6 : scénarios rejoués avec `FrozenClock` et le Fake du
  diffuseur (`tests/test_liquidsoap_playout.py`).
- Pour C9 : réponses littérales tronquées dans les trois tests d'adaptateurs.
- **Reste à écouter** (AGENTS §4.1) : une reprise après pause avec une émission
  en avance, et la jonction qui suit une émission (jingle absent).
