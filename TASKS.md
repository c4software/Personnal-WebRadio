# TASKS.md — Feuille de route et avancement réel

La mémoire persistante du projet. Un agent qui arrive doit pouvoir lire ce seul
fichier et comprendre **où le travail s'est arrêté**.

Documents liés : [AGENTS.md](./AGENTS.md) (les règles) ·
[SPECS.md](./SPECS.md) (le quoi) · [ARCHITECTURE.md](./ARCHITECTURE.md) (le
comment) · [TASKS.archive.md](./TASKS.archive.md) (l'histoire des Goals
terminés).

---

## Conventions

| Marque | État |
|---|---|
| `[ ]` | TODO — pas commencé |
| `[-]` | EN COURS — commencé, **jamais supposé terminé** |
| `[x]` | TERMINÉ — code **et** tests **et** vérification constatée |
| `[!]` | BLOQUÉ — la raison est écrite juste en dessous |

Identifiants : `GOAL-00X` pour un Goal, `GOAL-00X-TYY` pour une tâche. Ils sont
**stables** : une tâche abandonnée est barrée, jamais renumérotée. Les messages
de commit les référencent (AGENTS.md §7).

Rappel (AGENTS.md §1.1) : `code écrit ≠ tâche terminée`.

**L'archivage fait partie de la clôture.** Quand un Goal passe entièrement à
`[x]`, son détail — tâches, décisions, dettes — part en fin de
[TASKS.archive.md](./TASKS.archive.md), et seule sa ligne de la table de vue
d'ensemble reste ici. Les incidents consignés suivent le même chemin une fois
leur leçon inscrite dans [AGENTS.md](./AGENTS.md). C'est ce qui garde ce
fichier assez court pour être lu à chaque session.

---

## Phase courante

**Phase 2 — Le produit** `[x]` **terminée le 2026-08-30.**

Les quarante-trois Goals sont terminés et la table ci-dessous en est le bilan.
Le code est écrit, testé et vérifié, et ce que les tests n'entendent pas a été
**validé à l'écoute par l'auteur** — le 2026-08-30 pour le produit (votes,
saut, encore, flash France Info, YouTube, jingles, interface), puis le
**2026-08-31** pour la vague suivante : le tirage sur la bibliothèque entière
et son cache (GOAL-039/040), la plage au thème tiré au sort (GOAL-037), la
reprise à neuf après une longue pause (GOAL-041), la grille de journée et ses
quinze génériques (GOAL-043).

**GOAL-051 à GOAL-054 sont clos le 2026-09-02** : cinq défauts
entendus à l'antenne le matin même, à la rencontre du direct (GOAL-015) et de
la reprise à neuf (GOAL-041) ; le journal qui empilait deux journées sous la
même heure ; et le déploiement en deux moitiés dont une silencieuse — le script
du diffuseur voyage désormais dans une image ; et « À suivre » ne se vide
plus à chaque jingle. **GOAL-055 est clos le même jour** : le micro-flash
du morceau interrompu qu'entendait le premier auditeur après une longue
pause.

**Trois Goals ouverts le 2026-09-02, après l'écoute de 16 h** : le jingle
horaire arrivé une chanson trop tard, suivi du générique « mystère » puis d'un
morceau de la plage d'avant (GOAL-056, un défaut) ; retirer au sort le thème
d'une plage « au hasard » depuis l'interface (GOAL-057) ; voir les prochains
titres et agir dessus avant qu'ils passent (GOAL-058). Le diagnostic complet
est sous GOAL-056. Décisions
restantes de SPECS.md §7 : la **n°9** est une
conséquence consignée, non une question ; la **n°12** (combiner plusieurs
sources actives) est délibérément différée jusqu'à la deuxième source de
musique.

**Reste à écouter** (AGENTS.md §4.1) :

- **GOAL-050** — la montée du volume en deux secondes au branchement du premier
  auditeur, y compris quand l'antenne reprend au milieu d'un morceau.
- **GOAL-051** — la jonction musique → direct, dont les ~2 s de fondu de sortie
  écourtées (T04/T06) ; et la reprise à la coupure du direct, sur un morceau
  frais (T05). Les mesures disent qu'il n'y a ni silence ni retard ; elles ne
  disent pas si la coupure du fondu s'entend.
- **GOAL-055** — la reprise après une longue pause : le morceau frais entre
  sans fondu propre, sous la seule rampe de prise d'antenne. Les mesures disent
  que le reliquat ne passe plus ; elles ne disent pas si l'entrée à froid
  s'entend.

Les écoutes de GOAL-044 (modes d'enchaînement) et GOAL-047 (coupe au plafond)
ont été validées par l'auteur le 2026-09-01.

**Prochaine tâche** : GOAL-056-T01. Les trois Goals s'enchaînent dans
l'ordre : GOAL-057 et GOAL-058 s'appuient tous deux sur l'avance datée par
son moment que GOAL-056 met en place.

**Reste aussi** : l'écoute de GOAL-050 et GOAL-051, qui n'ont atteint la
production que le 2026-09-02 (GOAL-053).

---

## Vue d'ensemble

| Goal | Titre | État |
|---|---|---|
| GOAL-001 | Harness et initialisation | `[x]` |
| GOAL-002 | Relever les cinq dépendances externes | `[x]` |
| GOAL-003 | Le noyau : horloge, hasard, file de lecture | `[x]` |
| GOAL-004 | Le flux : ffmpeg, fan-out, démarrage à la demande | `[x]` |
| GOAL-005 | La grille horaire et les moments thématiques | `[x]` |
| GOAL-006 | Jingles horaires | `[x]` |
| GOAL-007 | Le pilotage : `stop` et `encore` dans le noyau | `[x]` |
| GOAL-008 | L'API de pilotage | `[x]` |
| GOAL-009 | L'interface web — Flask et Jinja2 | `[x]` |
| GOAL-010 | Les émissions : podcasts programmés | `[x]` |
| GOAL-011 | Conteneurisation : Docker et Compose | `[x]` |
| GOAL-012 | Les votes pondèrent les tirages suivants | `[x]` |
| GOAL-013 | Les programmes : une playlist, des jours, des heures | `[x]` |
| GOAL-014 | Correctifs de la relecture du 2026-08-30 | `[x]` — T01 corrigée ; T02–T07 supprimés avec leur code par GOAL-016 |
| GOAL-015 | Un direct comme émission — dont le flash France Info | `[x]` |
| GOAL-016 | Migration vers Liquidsoap : le noyau décide, Liquidsoap diffuse | `[x]` |
| GOAL-017 | `stop` ne passe pas le morceau en cours | `[x]` — fondu validé à l'oreille |
| GOAL-018 | L'interface en Vue, et la page des votes | `[x]` |
| GOAL-019 | Les plages thématiques par jour | `[x]` |
| GOAL-020 | Les votes portent un libellé lisible | `[x]` |
| GOAL-021 | Effacer un vote, l'onglet Planning, et le bouton qui ne cliquait pas | `[x]` |
| GOAL-022 | Fondu court des jingles, et le moment présent à l'antenne | `[x]` |
| GOAL-023 | Une plage peut imposer un artiste | `[x]` |
| GOAL-024 | `encore` force réellement le même artiste | `[x]` |
| GOAL-025 | Une chaîne YouTube comme émission | `[x]` |
| GOAL-026 | Les votes ne portent que sur l'artiste (n°16 révisée) | `[x]` |
| GOAL-027 | Le journal des titres, visible dans l'interface | `[x]` |
| GOAL-028 | YouTube sans blanc : téléchargé en fond, servi en local | `[x]` |
| GOAL-029 | Génériques d'ouverture et de fermeture des moments | `[x]` |
| GOAL-030 | Les jours de la configuration passent à l'anglais | `[x]` |
| GOAL-031 | Le jingle d'« encore » se configure, les exemples ont leurs génériques | `[x]` |
| GOAL-032 | Les jingles horaires rangés dans `hours/` | `[x]` |
| GOAL-033 | Les variantes de jingles, tirées au hasard | `[x]` |
| GOAL-034 | L'encore agit sur la chanson suivante, l'avance est réinsérée | `[x]` |
| GOAL-035 | « À suivre » : la file s'affiche à l'antenne | `[x]` |
| GOAL-036 | La CI : vérification puis image publiée sur GHCR | `[x]` |
| GOAL-037 | Une plage dont le genre ou l'artiste est tiré au sort | `[x]` — écoute validée le 2026-08-31 |
| GOAL-038 | Le Compose de production tire l'image publiée ; un Compose de dev construit localement | `[x]` |
| GOAL-039 | Parler Subsonic plutôt que Navidrome, et tirer dans toute la bibliothèque | `[x]` — écoute validée le 2026-08-31 |
| GOAL-040 | Un cache de bibliothèque dans l'adaptateur Subsonic | `[x]` |
| GOAL-041 | Péremption des jingles horaires, et reprise à neuf après une longue pause | `[x]` — écoute validée le 2026-08-31 |
| GOAL-042 | Le Planning s'ouvre sur aujourd'hui, créneau en cours visible, jours repliés | `[x]` |
| GOAL-043 | Une grille de journée complète, et un atelier à jingles en conteneur | `[x]` — écoute validée le 2026-08-31 |
| GOAL-044 | Les modes d'enchaînement des plages : double dose, époque, artiste | `[x]` — écoute validée le 2026-09-01 |
| GOAL-045 | Une chanson trop longue n'est jamais diffusée | `[x]` — n°32 révisée par GOAL-047 |
| GOAL-046 | Le mode d'une plage se voit dans le Planning | `[x]` |
| GOAL-047 | Une chanson trop longue se joue, mais se coupe en fondu au plafond | `[x]` — écoute validée le 2026-09-01 |
| GOAL-048 | Un libellé trop long du Planning se tronque en ellipse | `[x]` |
| GOAL-049 | Tirage par genre fiable malgré les genres fantômes de Navidrome | `[x]` — clos le 2026-09-01 : diagnostic consigné (T01), le reste abandonné — la bibliothèque a été purgée, T03 annulée par revert |
| GOAL-050 | Un fondu à la prise d'antenne | `[x]` — reste l'écoute réelle |
| GOAL-051 | Le direct ne ment plus à l'antenne, et la reprise coupe vraiment le reliquat | `[x]` — clos le 2026-09-02 ; **reste l'écoute** |
| GOAL-052 | L'historique dit quel jour, et ne mélange plus deux 8 h | `[x]` — clos le 2026-09-02 |
| GOAL-053 | Le script du diffuseur voyage dans une image, plus par un montage | `[x]` — clos le 2026-09-02 |
| GOAL-054 | « À suivre » regarde derrière l'habillage | `[x]` — clos le 2026-09-02 |
| GOAL-055 | Le premier auditeur n'entend plus le reliquat du morceau interrompu | `[x]` — clos le 2026-09-02 ; **reste l'écoute** |
| GOAL-056 | L'avance est datée par son moment : le jingle horaire tombe à la jonction qui suit l'heure, et la plage d'avant ne déborde plus derrière le générique | `[ ]` |
| GOAL-057 | Retirer au sort le thème d'une plage « au hasard », par l'API et l'interface | `[ ]` |
| GOAL-058 | Les prochains titres se voient, et se retirent avant de passer | `[ ]` |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).

---

## GOAL-056 — L'avance est datée par son moment

Entendu par l'auteur le 2026-09-02 autour de 16 h : le jingle horaire n'était
pas à sa place. Le journal du diffuseur (en UTC, deux heures de moins) et
`/api/history` reconstituent la chronologie à la seconde :

| Heure | Ce qui commence | Ce que `radio` décide à cet instant pour la suite |
|---|---|---|
| 15:59:36 | *Ride Natty Ride* (Bob Marley, plage 15 h `artist_fan`) | *Could You Be Loved* — même suite d'artiste ; puis `prepare()` résout d'avance *Get Up, Stand Up*, toujours sous la plage de 15 h |
| **16:00:00** | — | rien : personne ne regarde l'horloge entre deux jonctions |
| 16:03:25 | *Could You Be Loved* | la plage a changé → générique `bands/mystere.mp3` mis en attente ; `16h-c.mp3` dû → rendu ; l'avance *Get Up, Stand Up* reste telle quelle |
| 16:07:19 | `hours/16h-c.mp3` — **7 min après l'heure** | `bands/mystere.mp3` |
| 16:07:43 | `bands/mystere.mp3` — « une heure d'un genre tiré au sort » | `next_pick()` sert l'avance **sans regarder la contrainte** : *Get Up, Stand Up* |
| 16:07:48 | *Get Up, Stand Up* — Bob Marley, **derrière le générique du mystère** | premier titre Ragga |
| 16:11:05 | *Natural* (Les R'tardataires) — la plage de 16 h commence enfin | … |

Deux défauts distincts, une même cause : **une entrée décidée d'avance ne sait
pas sous quel moment elle a été tirée, et personne ne la remet en question
quand ce moment finit.**

1. **Le jingle arrive une chanson trop tard.** Le diffuseur demande toujours un
   morceau d'avance (`prefetch=1`, docs/liquidsoap.md §3) : l'entrée qui
   commence à la jonction J est décidée à la jonction J−1. Une heure pleine
   qui tombe entre J−1 et J n'est vue qu'à J, pour l'entrée de J+1. SPECS.md
   §4.3 promet « la jonction suivante » ; la production livre **la jonction
   d'après**, systématiquement, depuis la migration Liquidsoap. Ici : 16 h 03
   promis, 16 h 07 servi. Le même retard frappe la transition de plage (§7
   n°5) et l'ouverture d'une émission-fichier — c'est ce que docs/liquidsoap.md
   §5 constatait déjà avec « une case plus courte que deux morceaux ».
   L'« encore » a déjà réglé ce problème pour lui-même (GOAL-034) : `/requeue`
   vide l'avance du diffuseur, et `stash_for_replay` la replace derrière le
   jingle. Il manque un **déclencheur à l'heure pleine**.
2. **La plage d'avant déborde derrière le générique.** `Queue.prepare()` avait
   résolu le cinquième titre de la suite Bob Marley à 15 h 59 ; `next_pick()`
   sert l'avance « sans regarder la contrainte — c'est tout son intérêt »
   (GOAL-054-T02 avait vu le même trou pour la longue pause, et l'avait bouché
   pour ce seul cas). À 16 h 07 le générique annonce un genre mystère, et
   l'auditeur entend un Bob Marley de plus. Le direct avait le même défaut, réglé
   pour lui seul le matin même (`stop_live` jette « l'avance rassie »,
   GOAL-051-T05). C'est le **troisième** cas particulier de la même règle
   absente.

**Choix retenu — une règle, pas un quatrième cas particulier** : toute entrée
décidée d'avance — l'avance de la file comme l'entrée déjà donnée au diffuseur —
est **datée par le moment qui l'a tirée** (l'occurrence de plage, le programme,
ou le tirage libre : la clé de `Constraint.run_key`, déjà là). Une entrée dont
le moment n'est plus le moment courant est **rassise** : elle ne passe pas,
elle se retire. Une heure pleine qui sonne pendant qu'une entrée musique attend
chez le diffuseur la fait remettre en question : rejouée derrière le jingle si
son moment tient encore, jetée sinon. Cela absorbe la purge de la longue pause
(§7 n°30), celle de la fin du direct, et les deux défauts de 16 h.

Ce que cela **ne** change pas : la grille n'est toujours consultée qu'au tirage
(§7 n°5), le morceau **en cours** finit toujours. Ce qui bouge est l'entrée
d'avance, que personne n'entend encore.

- [ ] **GOAL-056-T01** — La file date son avance : `Queue.prepare()` retient la
      clé du moment (`run_key`, ou `None` en tirage libre) avec le `Pick`, et
      `next_pick()` la sert seulement si la contrainte demandée porte la même
      clé — sinon il l'oublie et tire à neuf. Une plage multi-genres retire un
      genre à chaque jonction sans changer de clé : son avance survit, comme
      aujourd'hui. Tests : rejouer 15 h 59 → 16 h 03 à horloge injectée et
      constater que le premier titre servi après le changement de plage est
      tiré sous la nouvelle contrainte. `forget_prepared()` de GOAL-054-T02
      devient un cas de cette règle ou disparaît.
- [ ] **GOAL-056-T02** — La charnière date ce qu'elle donne au diffuseur :
      `LiquidsoapPlayout` retient, avec chaque entrée en attente, sa nature, le
      moment qui l'a tirée et l'instant de la décision. Pas encore de décision
      ici, seulement la mémoire — et `stash_for_replay` ne replace que ce dont
      le moment tient encore ; le reste est jeté en le journalisant.
- [ ] **GOAL-056-T03** — L'heure pleine remet l'avance en question. Le
      battement d'auditeurs (toutes les 15 s, `declare_listeners`) est
      l'horloge dont dispose la charnière : quand une heure pleine est passée
      depuis la décision de l'entrée musique en attente, et que quelqu'un
      écoute, la charnière la replace (T02) et ordonne `/requeue` — exactement
      le chemin de l'encore (GOAL-034). Le diffuseur redemande aussitôt : le
      programme rend le générique sortant, le jingle dû, le générique entrant,
      puis l'entrée replacée ou un tirage neuf. Rien pendant un direct — le
      direct purge lui-même à sa fin. Le résidu assumé : une jonction tombée
      dans les 15 s qui précèdent l'heure garde l'ancien comportement.
      **Écouter** avant de cocher (AGENTS.md §4.1) : un jingle à 17 h, à la
      jonction qui suit l'heure, sans blanc ni doublon.
- [ ] **GOAL-056-T04** — Les deux purges existantes rejoignent la règle :
      `forget_pending()` (longue pause, §7 n°30) et le `/requeue` de fin de
      direct (`stop_live`) s'expriment comme « l'avance est rassise », sans
      code propre. Le script Liquidsoap ne change de comportement que si le
      relevé (docs/liquidsoap.md) le permet ; sinon la tâche se limite au
      Python et le dit.
- [ ] **GOAL-056-T05** — Documenter : SPECS.md §4.3 (le jingle tombe à la
      jonction qui suit l'heure, résidu de 15 s compris), §4.4 (la plage
      d'avant ne déborde pas derrière son générique), §7 — une décision
      n°33 « l'avance est datée par son moment » qui absorbe la purge de la
      n°30 ; ARCHITECTURE.md si la charnière change de rôle ;
      docs/liquidsoap.md §3 si le comportement de `set_queue([])` à
      auditeurs présents est observé de nouveau.

---

## GOAL-057 — Retirer au sort le thème d'une plage « au hasard »

Demandé par l'auteur le 2026-09-02. Une plage `random = "genre"` ou
`random = "artist"` tire son thème au début de l'occurrence et s'y tient
(SPECS.md §4.4, §7 n°28). Quand le genre sorti ne plaît pas — une heure de
Ragga un mercredi à 16 h —, il n'y a rien à faire d'autre que d'attendre 17 h.
L'auteur veut pouvoir **retirer** : un bouton dans l'interface, donc une route
d'API (SPECS.md §4.8 : aucun chemin privilégié).

> **Sur « année »** : il n'existe pas de thème « une année au hasard ».
> `RANDOM_THEMES` ne connaît que `genre` et `artist` ; les décennies ne vivent
> que dans le mode `era_fan`, qui pose son ancre par suite et non par
> occurrence. Retirer s'applique donc à ce qui est tiré aujourd'hui. Un thème
> `random = "era"` — une décennie tirée au sort pour l'occurrence — serait un
> Goal à part : `Track.year` est un entier relevé (docs/subsonic.md §4.1) et
> la bibliothèque est en mémoire (GOAL-039), donc filtrer par décennie est
> possible côté file ; mais c'est une nouvelle sorte de contrainte, avec ses
> replis, pas une case de plus dans `RANDOM_THEMES`.

Ce que retirer veut dire, à l'antenne : le morceau en cours finit (§7 n°5) ;
dès la jonction suivante, la plage joue le **nouveau** thème — donc l'avance
tirée sous l'ancien est rassise (GOAL-056), et le diffuseur doit la jeter par
`/requeue`. Le générique de la plage ne repasse pas : il annonce la plage, pas
le thème. Le nouveau thème est **différent** de l'ancien — retirer le même
serait un bouton qui ne fait rien —, sauf si la bibliothèque n'en offre qu'un.
Hors d'une plage au hasard, la demande est **refusée en le disant** (409 et
un motif, comme un vote pendant un jingle).

- [ ] **GOAL-057-T01** — Le noyau sait retirer : `RandomTheme.redraw()`
      oublie le thème de l'occurrence courante et retire en excluant l'ancien ;
      la clé de moment d'une plage au hasard inclut le thème sorti, pour que
      l'avance datée (GOAL-056) et la suite en cours (`Runs`) repartent. Tests
      à graine fixée : le nouveau thème diffère, l'occurrence suivante retire
      normalement, une bibliothèque à un seul genre rend le même en le disant.
- [ ] **GOAL-057-T02** — La route : `POST /api/moment/redraw`. Accepté →
      `{"accepted": true, "moment": "Moment · Jazz (au hasard)"}` après avoir
      préparé le tirage, pour que la réponse dise déjà ce qui vient ; refusé
      hors d'une plage au hasard → 409 et un motif. `/api/on-air` gagne un
      champ `moment_random: true|false` — l'interface ne doit pas deviner sur
      le libellé. Le `Protocol` `Radio` s'étend d'une question ; `LiveRadio`
      la traduit et ordonne le `/requeue`.
- [ ] **GOAL-057-T03** — L'interface : un bouton « Retirer » à côté du moment,
      visible seulement quand `moment_random` est vrai, grisé pendant l'appel,
      qui affiche le motif d'un refus comme le font « Passer » et « Encore ».
- [ ] **GOAL-057-T04** — Documenter : SPECS.md §4.4 (retirer), §4.8 (la route
      et le champ), §7 n°28 amendée ; **écouter** une fois : le retirage à la
      jonction, sans que le générique repasse.

---

## GOAL-058 — Les prochains titres se voient, et se retirent avant de passer

Demandé par l'auteur le 2026-09-02 : « si elle existe, exposer la liste des
prochains titres pour agir dessus avant diffusion ».

**Elle n'existe pas encore comme liste.** Ce que la radio connaît d'avance
tient en deux entrées : celle déjà donnée au diffuseur (`prefetch=1`), et
l'avance de la file (`Queue._avance`, un seul `Pick`, GOAL-054). « À suivre »
en annonce la première qui soit de la musique. Pour agir sur plusieurs titres,
il faut d'abord qu'ils soient tirés.

Ce que tirer plusieurs titres d'avance engage, et qui décide du découpage :

- la **non-répétition** doit voir ce qui attend, pas seulement ce qui a joué —
  sinon la file tire deux fois le même artiste dans son avance ;
- les **suites** (`Runs`) s'observent au tirage : une avance de cinq titres
  contient donc une suite entière, c'est cohérent ;
- l'avance est **rassise** au changement de moment (GOAL-056) : plus elle est
  profonde, plus cette règle compte — c'est pourquoi GOAL-056 vient avant ;
- la **pondération** par les votes s'applique au tirage : un vote donné pendant
  qu'un titre attend ne le déplace pas, et c'est acceptable ;
- l'**encore** passe toujours devant la liste, et « À suivre » en devient la
  tête ;
- la source est appelée plusieurs fois d'affilée à la première préparation :
  le cache (`subsonic.cache_seconds`) l'absorbe, mais à vérifier au journal.

L'action demandée est **retirer** un titre : il ne passera pas, un autre est
tiré à sa place, et le retrait est journalisé. Rien de plus tant que l'auteur
ne l'a pas demandé — ni réordonner, ni forcer un titre (AGENTS.md §2 :
n'anticipe pas). Retirer la tête de liste — l'entrée déjà chez le diffuseur —
passe par le chemin de l'encore : `/requeue`, et le reste se replace.

- [ ] **GOAL-058-T01** — La file tire N titres d'avance : `Queue` garde une
      avance de profondeur configurable (`[draw] lookahead`, défaut à choisir
      et à justifier dans le commit — 3 est un point de départ), chaque `Pick`
      daté par son moment (GOAL-056-T01) ; la fenêtre de non-répétition et
      l'écart d'artiste tiennent compte de ce qui attend. `prepared` rend la
      liste. Tests : cinq tirages d'avance ne répètent pas un artiste dans
      l'écart, une avance rassise se vide d'un coup, une source lente ne
      bloque pas la jonction (la préparation reste hors verrou).
- [ ] **GOAL-058-T02** — La route de lecture : `GET /api/up-next` rend la
      liste dans l'ordre de passage — l'entrée chez le diffuseur d'abord, puis
      l'avance de la file — avec, pour chacune, un identifiant stable (celui de
      la piste), titre, artiste, nature ; jamais l'habillage (règle de
      GOAL-035). `/api/on-air` garde `up_next` = la tête de cette liste.
- [ ] **GOAL-058-T03** — La route d'action : `DELETE /api/up-next/<identifier>`
      retire ce titre de l'avance — remplacé par un tirage neuf sous le même
      moment — et 404 s'il n'y attend plus (il a commencé entre-temps, ce
      qui arrivera). La tête de liste passe par `/requeue` + replacement du
      reste. Journalisé : « retiré avant diffusion : … ».
- [ ] **GOAL-058-T04** — L'interface : le panneau « À suivre » devient la
      liste, chaque ligne avec un ✕ « Ne passera pas » sur le modèle du ✕ des
      votes, rafraîchie au même rythme que l'antenne.
- [ ] **GOAL-058-T05** — Documenter : SPECS.md §4.8 (« À suivre » devient
      une liste, les deux routes), §6 (`lookahead`), §7 — décision n°34 « une
      avance de N titres, retirables » ; ARCHITECTURE.md §5 si la file change
      de forme. **Écouter** une journée : la profondeur ne doit pas se
      remarquer à l'antenne — ni artiste répété, ni titre hors plage après une
      transition.
