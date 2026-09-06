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

**GOAL-056 à GOAL-058 sont clos le 2026-09-02**, ouverts le jour même après
l'écoute de 16 h : le jingle horaire arrivé une chanson trop tard, suivi du
générique « mystère » puis d'un morceau de la plage d'avant — corrigé par une
règle, l'avance datée par son moment (n°33) ; le thème d'une plage « au
hasard » se retire depuis l'interface (n°28 amendée) ; les prochains titres
se voient dans un tiroir, tirés pour leur heure, et se retirent avant de
passer (n°34). **GOAL-059** étend « Retirer » aux suites tirées au sort —
« année aléatoire » désignait le mode `era_fan`. **GOAL-060** met un lecteur
dans la page. **Aucun Goal ouvert.** Décisions
restantes de SPECS.md §7 : la **n°9** est une
conséquence consignée, non une question ; la **n°12** (combiner plusieurs
sources actives) est délibérément différée jusqu'à la deuxième source de
musique.

**Toutes les écoutes en attente ont été validées par l'auteur le 2026-09-02**
(AGENTS.md §4.1) : la prise d'antenne en fondu (GOAL-050), la jonction avec
le direct et la reprise à sa coupure (GOAL-051), la reprise après une longue
pause (GOAL-055), le jingle à la jonction qui suit l'heure (GOAL-056), les
retirages (GOAL-057, GOAL-059), les titres d'avance et leur liste (GOAL-058),
le lecteur puis la pilule depuis un téléphone (GOAL-060, GOAL-062).

Les écoutes de GOAL-044 (modes d'enchaînement) et GOAL-047 (coupe au plafond)
ont été validées par l'auteur le 2026-09-01.

**GOAL-062 est clos le 2026-09-02** : l'auteur a trouvé l'interface
« pas terrible » — un lecteur perdu au milieu de la page, un grand vide
jusqu'aux votes collés en bas. Le lecteur est une pilule de verre fixe en
bas, présente sur tous les onglets, et les prochains titres s'y déploient ;
l'antenne est une carte, les votes juste dessous. **Aucun Goal ouvert.**

**GOAL-063 est clos le 2026-09-02** : la page s'installe comme une
application, porte une icône et dit dans son titre ce qui passe ; la carte
« La radio dort » reste, avec un texte sobre. **Aucun Goal ouvert.** Reste à essayer
l'installation depuis un téléphone — Android et iOS n'ont pas les mêmes
critères, et rien ne le constate sans un vrai appareil.

**GOAL-064 est clos le 2026-09-02** : la feuille de style est sortie du
gabarit, et la page s'anime — entrée des listes, changement d'onglet,
changement de chanson. **Aucun Goal ouvert.**

**GOAL-065 est clos le 2026-09-02** : le lecteur renvoie le son vers une
enceinte par l'API Remote Playback du navigateur, sans SDK ; **reste à
essayer** avec un Chromecast ou un AirPlay (docs/flux-icy.md §8).
**Aucun Goal ouvert.**

**GOAL-066 est clos le 2026-09-02** : à l'antenne, une plage à mode seul
— 19 h, `era_fan` sans genres — n'affichait qu'un « Moment · » vide à côté du
bouton « Autre thème ». Le moment courant se nomme désormais dans tous les
cas, et dit son enchaînement.

**GOAL-067 est clos le 2026-09-02** : un « encore » voté sur La Rue Kétanou
avait forcé le genre de THK, le morceau d'avance — l'ancre était lue à la
jonction, sous le jingle. Elle se prend désormais au vote, et le morceau forcé
se voit dans les prochains titres. **Aucun Goal ouvert.**

**GOAL-068 est clos le 2026-09-02** : le Planning affichait les périodes
**déclarées**, jamais celles qui passent — mercredi, « Hardisk » et la plage
guitares s'y lisaient comme deux créneaux côte à côte, alors que l'émission
mange la plage. La grille **effective** est calculée une fois, dans le noyau,
et sert au Planning comme à ce que la radio prépare. L'arbitrage d'un
recouvrement passe à **la plus courte période** (décision de l'auteur, prise
sur conséquences montrées). **Aucun Goal ouvert.** **Reste à écouter**
(AGENTS.md §4.1) : la jonction de 20 h un mercredi, quand Hardisk coupe les
guitares, et la reprise à la fin du programme du vendredi.

**GOAL-069 est clos le 2026-09-02** : le picto de volume de la barre était un
emoji — le seul de toute la page, au milieu de huit pictos dessinés en SVG. Il
est dessiné à son tour, et un test interdit le retour d'un emoji dans la page.

**GOAL-070 est clos le 2026-09-02** : l'auteur ne voyait que **quatre** titres
dans la liste de lecture au lieu des huit de `draw.lookahead`. Le report
introduit le jour même par GOAL-068-T04 s'appliquait à la préparation mais pas
à la lecture : la liste jugeait rassis ce qui avait été tiré pour l'heure
d'après un direct, et se coupait sans rien dire. Elle applique le même report,
nomme le direct qui coupe et reprend après lui. **Aucun Goal ouvert.**

**GOAL-071 est clos le 2026-09-02** : une plage déclare les décennies où elle
tire (`eras`), et le filtre s'applique avant que l'ancre d'une vague ne se
tire. Ouvert après un audit de la grille contre la bibliothèque réelle, qui
avait montré une plage `era_fan` dont le vivier ne compte qu'un titre d'une
décennie quand une vague en demande deux à six. **Aucun Goal ouvert.**
**Reste à écouter** (AGENTS.md §4.1) la plage de 12 h : qu'une vague bornée
s'entende comme une vague, et non comme un vivier rétréci.

**GOAL-072 est clos le 2026-09-03** : l'auteur trouvait le jeu de couleurs
« trop vibecoding » — trois halos bleu, violet et vert en fond, une pochette
en dégradé bleu→violet, des lueurs colorées, des capitales espacées de
0,2 em. La page passe au verre d'iOS : un fond graphite à une seule teinte,
des surfaces presque blanches et très transparentes, une arête spéculaire et
une lentille qui leur donnent une épaisseur, un grain fin, et la couleur
réservée à ce qui a un sens. L'en-tête flotte au lieu de déborder de la
colonne — sur un écran large, le bandeau s'arrêtait net au milieu de la page.
Rendu **validé à l'œil par l'auteur** le 2026-09-03, par retouches
successives depuis un aperçu servi sur le réseau. **Aucun Goal ouvert.**

**Nouvelle règle** (AGENTS.md §4 et §9, décision de l'auteur) : la feuille de
style ne porte **aucun commentaire**, et **aucun test n'affirme le contenu
d'une règle CSS** — un test qui fige `background: rgba(…)` se casse à chaque
réglage sans rien protéger. Les tests écrits pendant ce Goal ont été retirés,
et ceux de GOAL-064 allégés d'autant.

**Piste ouverte, non planifiée** : la pochette du morceau en cours, floutée,
en fond de page. C'est ce qui ferait vraiment vivre le verre, puisqu'il
change à chaque titre — mais cela demande la couverture depuis l'API
Subsonic, donc noyau, API et page : un Goal à part, pas une retouche.

**GOAL-073 est clos le 2026-09-03** : la page redemandait à l'API ce qui passe
toutes les cinq secondes, qu'elle soit visible ou non, et une coupure de réseau
s'affichait en toutes lettres — « L'API ne répond pas : TypeError: Failed to
fetch » — jusqu'au prochain succès. L'état d'antenne est désormais **poussé**
par `GET /api/events`, un flux SSE ; la page s'y abonne au lieu de sonder, ferme
sa connexion quand l'onglet passe en fond, et montre une coupure par un témoin
discret que `EventSource` efface en se rebranchant. Le sens interface → serveur
reste REST (décision de l'auteur). **Aucun Goal ouvert.**
**Reste à constater** (AGENTS.md §4.1, et rien ne le fera automatiquement) :
une vraie coupure réseau depuis un téléphone, et le retour d'un écran
verrouillé au bout de dix minutes.

**GOAL-074 est clos le 2026-09-06** : le micro-flash de la chanson de la
veille, entendu à la reconnexion du matin. Le garde-fou de GOAL-055 avait
pourtant fonctionné — il ne couvrait que le cas où l'API répond vite. La
transition de `cross` ne s'exécute qu'une fois le morceau frais bufférisé, et
la sortie servait le reliquat en attendant. Le témoin porte désormais sur le
gain. T03 est **abandonnée sur arbitrage** : `thread.run` ne sérialise pas et
la 2.3.3 n'a aucun verrou, donc le remède évident ferait mentir l'antenne.
**Reste à écouter** la reprise du matin.

**Quatre Goals ouverts**, dans cet ordre : **GOAL-075** (le premier tirage
d'une reprise, qui fixe la durée du silence et a déjà fait couper le
diffuseur), **GOAL-076** (petit, protège les deux suivants), **GOAL-077** (la
plage podcasts), **GOAL-078** (la couture de la grille — après GOAL-077, qui
lui donne le bon jeu de périodes).

**Prochaine tâche** : GOAL-076-T01. GOAL-075 attend sa mesure à l'antenne
(T03), qui demande le déploiement.

---

## GOAL-075 — Le premier tirage d'une reprise ne fait plus attendre l'antenne

Ouvert le 2026-09-06 par GOAL-074-T05, sur mesure. `next_entry` remplit toute
l'avance **dans la requête** (`app/liquidsoap_playout.py:128`) : le premier
`/playout/next` d'une reprise paie `draw.lookahead + 1` tirages — neuf en
production — contre un cache de bibliothèque expiré. D'où 4 s le 2026-09-06,
et plus de dix le 2026-09-05, où le diffuseur a coupé et laissé 21 s de
silence.

C'est ce délai qui rend la reprise silencieuse (GOAL-074-T02) : le muet dure
exactement le temps de ce tirage. Le raccourcir raccourcit l'attente.

- [x] **GOAL-075-T01** — Rendre l'entrée dès qu'elle est tirée, et préparer
      l'avance après avoir répondu. Le lanceur est **injecté** : sur place par
      défaut — ce qui garde tous les tests existants déterministes, sans fil ni
      attente — et, en production seulement, un fil unique monté dans
      `main.py`. Unique parce que deux préparations partageraient la file et la
      fenêtre de non-répétition ; démon, pour ne pas retenir l'arrêt.
      Établi avant d'écrire : différer ne peut pas produire un 204, car
      `Queue.next_pick` retombe sur un tirage neuf quand l'avance est vide
      (`core/queue.py:152-156`). Le premier tirage d'une reprise fait donc
      **un** tirage au lieu de `lookahead + 1` — neuf en production.
      **Reste à mesurer à l'antenne** : le gain en secondes ne se constate pas
      ici, la maquette ayant une fausse bibliothèque. C'est T03.
- [x] **GOAL-075-T02** — Que le cache de bibliothèque se réchauffe au réveil
      de l'antenne plutôt qu'au premier tirage. **Instruit, et écarté** : le
      réveil et le premier tirage sont le même instant. Le diffuseur annonce
      l'auditeur puis demande le morceau dans la foulée ; un réchauffage lancé
      à l'annonce serait encore en cours quand le tirage arrive, et celui-ci
      l'attendrait. On déplacerait l'attente sans la supprimer, exactement ce
      que la tâche soupçonnait. Le coût restant — une dizaine d'appels à
      Navidrome pour un parcours, par genre — est le prix de « rien n'est
      demandé sans auditeur » (SPECS.md §1).
      **Ce qui a été fait à la place**, trouvé en instruisant : les deux
      autres `prepare()` de la charnière étaient eux aussi dans une requête.
      Celui de `stash_for_replay` est le plus coûteux — `on_connect` attend
      cette requête **avant de rendre l'antenne**, et une avance rassise à
      replacer y valait `draw.lookahead` tirages pendant que l'auditeur
      attendait le son. Les trois passent maintenant par le même lanceur.
- [!] **GOAL-075-T03** — **En attente du déploiement.** Mesurer, une fois T01 et T02 faites, ce que met le
      premier tirage d'une reprise, et le comparer aux 10 s d'`api_timeout`.
      S'il reste au-dessus, le diffuseur continuera de couper une API
      seulement lente (SPECS.md §5.1) : la tâche ouvre alors une décision —
      « lente » et « morte » doivent-elles se distinguer ? — plutôt que de
      relever le délai en silence.
      Rien ne se mesure ici : la maquette a une fausse bibliothèque, et c'est
      le vrai Navidrome qui coûte — une dizaine d'appels par parcours, un par
      genre. La mesure demande l'image poussée sur `frontal` et une vraie
      reprise du matin. Ce qu'il faudra regarder : le délai entre
      « avance jetée sur ordre de l'API » et le « suivant : » qui suit, dans
      le journal du diffuseur.

---

## GOAL-076 — Le thème d'une plage « au hasard » ne se retire plus tout seul

Ouvert le 2026-09-06, sur analyse de code, **sans constat à l'antenne** — c'est
un chemin trouvé en lisant, pas un défaut entendu. Petit, indépendant, et il
protège GOAL-077 comme GOAL-078.

`core/mystery.py` ne retient qu'**une** occurrence : celle en cours. Or la
préparation tire chaque créneau sous le moment de son heure estimée
(`app/playout.py`, décision n°34) : si un créneau futur tombe dans une **autre**
occurrence d'une plage `random`, la mémoire est remplacée par l'occurrence
future, et le battement suivant — qui redemande le moment courant — n'y
retrouve plus rien et **retire** le thème en cours. Clé changée, avance
rassise, `requeue`.

Le chemin existe déjà à `lookahead = 8` dès qu'une plage `random` en suit une
autre à moins de trente minutes. Il devient nominal si l'avance s'allonge.

- [ ] **GOAL-076-T01** — Un test qui rejoue une soirée où l'avance franchit
      la frontière entre deux plages `random`, et affirme que le thème en
      cours ne bouge pas. Horloge et graine fixées, comme le reste : il doit
      échouer avant le correctif. `tests/test_mystery.py` ne couvre
      aujourd'hui que la succession, jamais l'alternance.
- [ ] **GOAL-076-T02** — La mémoire des thèmes tirés porte sur l'occurrence,
      pas sur « la dernière consultée ». Ce que « occurrence » veut dire
      exactement est à établir en lisant `core/bands.py` : la clé existe déjà
      pour dater l'avance (n°33), c'est probablement elle.

---

## GOAL-077 — Une plage « podcasts » : plusieurs flux, tirés au hasard

Ouvert le 2026-09-06, demande de l'auteur, forme tranchée le même jour
(SPECS.md §7 **n°35**) : c'est une **émission à plusieurs flux**, pas une
plage. Entre `time` et `end`, on tire un flux au hasard parmi ceux qui ont du
neuf, on joue son épisode, on recommence ; à `end`, l'épisode en cours **finit**
(n°5), quitte à déborder.

- [ ] **GOAL-077-T01** — Relever ce qu'exposent réellement les flux voulus par
      l'auteur (AGENTS.md §3). `docs/podcast.md` §5 le dit lui-même : le relevé
      ne porte que sur **un** hébergeur, Acast, et « un second podcast, chez un
      autre hébergeur, n'aura pas les mêmes garanties ». Relever aussi le coût
      de lecture : `_catalogues` relit **tous** les flux à chaque jonction,
      sans cache — 3,5 Mo pour LEGEND seul, donc ~17 Mo par jonction à cinq
      flux. Si le coût est réel, il devient une tâche.
- [ ] **GOAL-077-T02** — Le noyau : `core/shows.py` choisit parmi plusieurs
      catalogues, avec une mémoire **par flux** et une pioche uniforme entre
      flux, par le hasard injecté. Une case à fin déclarée est ouverte jusqu'à
      `end`, comme celle d'un direct, et non jusqu'à la durée d'un épisode
      (c'est un autre régime que le rattrapage de la n°13). Tests : deux flux
      dont un seul a du neuf ; plus rien nulle part, case sautée ; à graine
      fixe, la même soirée pioche le même flux ; l'épisode entamé finit après
      `end`.
- [ ] **GOAL-077-T03** — La charnière : `app/show_scheduler.py` tient
      plusieurs adresses par émission, enchaîne dans la case, et nomme le flux
      tiré dans son journal. La clé de mémoire passe à `<name>/<feed>` —
      changement de ce que garde la base, donc ARCHITECTURE.md §5.
- [ ] **GOAL-077-T04** — La configuration : `feeds` et `end` dans
      `adapters/config/schema.py`, exclusifs de `feed`/`stream`/`youtube`,
      refusés là où ils n'ont pas de sens. **Une règle à trancher en chemin** :
      la détection de collision juge aujourd'hui « la case déclarée » ; une
      plage de deux heures qui contient l'heure d'une autre émission n'est
      plus vue. `webradio.exemple.toml`, SPECS.md §6 et §4.11.
- [ ] **GOAL-077-T05** — La grille et la page : `core/planning.py` lit déjà
      `Show.duration` — une case à fin déclarée s'y insère sans règle
      nouvelle ; `app/main.py::_periode` doit nommer « podcasts » comme il
      nomme `live` et `youtube`.
      **À écouter** (AGENTS.md §4.1) : la jonction d'entrée, l'enchaînement de
      deux épisodes d'éditeurs différents — les niveaux ne se ressemblent
      pas — et le débordement à `end`.

---

## GOAL-078 — La liste des prochains titres coud la grille derrière elle

Ouvert le 2026-09-06, demande de l'auteur, forme tranchée le même jour
(SPECS.md §7 **n°34 amendée**). Après GOAL-077 : la plage podcasts ajoute à la
grille une émission **dont la fin est déclarée**, et c'est précisément ce que
la liste sait dater. Écrite avant, la couture le serait contre des émissions
sans fin, puis retouchée.

Aujourd'hui la liste s'arrête à ~30 min, et devant un programme ou un podcast
elle s'arrête net — on ne continue qu'après ce qu'on sait **nommer et dater**
(GOAL-070). Rien ne relie les titres tirés au Planning, qui sait pourtant tout.

**Rien n'est tiré de plus : zéro décision, zéro tirage jeté.** La profondeur de
l'avance ne bouge pas.

- [ ] **GOAL-078-T01** — Le noyau : `core/planning.py` rend les périodes
      effectives **entre deux instants**, celle en cours comprise. `day()` ne
      rend que celles qui commencent dans la journée : une période ouverte à
      l'instant demandé et commencée la veille n'y figure pas.
- [ ] **GOAL-078-T02** — `upcoming()` ajoute ces périodes après le dernier
      titre daté, et ne s'arrête plus net sur ce qu'il ne sait pas dater : il
      le nomme, puis reprend à la période suivante. Comment une période se
      représente à côté d'un titre — une nature de plus, ou une fin sur ce qui
      existe — est à trancher en écrivant.
- [ ] **GOAL-078-T03** — L'API les rend, et la page les met en mots avec les
      fonctions du Planning. Aucun calcul dans le gabarit, et surtout pas une
      reconstruction à partir de `/api/planning` : il est figé à l'assemblage,
      l'heure de couture dépend de l'antenne.
      **Une question à l'auteur en chemin** : SPECS.md §4.8 dit que pendant un
      programme, rien n'est annoncé. Cela visait sa musique — la **période**
      « Programme · Le vendredi de Chloé 18:00–20:00 » s'annonce-t-elle ?
- [ ] **GOAL-078-T04** — L'horizon de la couture vient du TOML, avec son
      défaut déclaré (SPECS.md §6). Aucune durée en dur.

---

## GOAL-079 — `radio.liq` reçoit la réécriture du ton que les autres ont eue

Ouvert le 2026-09-06, sur revue. `ea20e20` a réécrit les commentaires du dépôt
« en prose ordinaire » (AGENTS.md §9 : ni récit, ni citation, ni date, ni
anecdote) — et **n'a touché aucun fichier `.liq`**. Le script porte donc encore
des dates dans ses commentaires, des majuscules d'insistance et des citations
d'arbitrage, et tout ce qu'on y ajoute depuis suit cette convention-là par
mimétisme. §9 dit que cela « ne doit pas revenir ».

- [ ] **GOAL-079-T01** — Réécrire les commentaires de
      `webradio/adapters/liquidsoap/radio.liq` au ton d'AGENTS.md §9, dans un
      commit `style` à part. Chaque commentaire garde son **pourquoi** et perd
      sa date, son anecdote et ses majuscules ; ce que le relevé établit s'y
      renvoie au lieu de s'y recopier. Aucun changement de comportement : la
      vérification doit passer sans qu'un seul test change.

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
| GOAL-050 | Un fondu à la prise d'antenne | `[x]` — écoute validée le 2026-09-02 |
| GOAL-051 | Le direct ne ment plus à l'antenne, et la reprise coupe vraiment le reliquat | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-052 | L'historique dit quel jour, et ne mélange plus deux 8 h | `[x]` — clos le 2026-09-02 |
| GOAL-053 | Le script du diffuseur voyage dans une image, plus par un montage | `[x]` — clos le 2026-09-02 |
| GOAL-054 | « À suivre » regarde derrière l'habillage | `[x]` — clos le 2026-09-02 |
| GOAL-055 | Le premier auditeur n'entend plus le reliquat du morceau interrompu | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-056 | L'avance est datée par son moment : le jingle horaire tombe à la jonction qui suit l'heure, et la plage d'avant ne déborde plus derrière le générique | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-057 | Retirer au sort le thème d'une plage « au hasard », par l'API et l'interface | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-058 | Les prochains titres se voient, et se retirent avant de passer | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-059 | « Retirer » vaut aussi pour une suite tirée au sort : décennie ou artiste | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-060 | Un lecteur dans la page : écouter la radio depuis l'interface | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-061 | Retouches de l'interface : votes grisés sans auditeur, tiroir plus profond et animé | `[x]` — clos le 2026-09-02 |
| GOAL-062 | L'interface repensée : un lecteur en barre fixe, l'antenne en carte, les votes à portée de pouce | `[x]` — clos le 2026-09-02, écoute validée le même jour |
| GOAL-063 | Installable en PWA, une icône, un titre qui dit ce qui passe | `[x]` — clos le 2026-09-02 ; **reste à essayer** l'installation depuis un téléphone |
| GOAL-064 | La feuille de style externalisée, et des animations d'entrée, d'onglet et de chanson | `[x]` — clos le 2026-09-02 |
| GOAL-065 | Renvoyer le son vers une enceinte depuis le lecteur | `[x]` — clos le 2026-09-02 ; **reste à essayer** avec une enceinte |
| GOAL-066 | Le moment courant se nomme toujours, à côté du bouton | `[x]` — clos le 2026-09-02 |
| GOAL-067 | L'encore vise la chanson entendue au vote, et la liste le montre | `[x]` — clos le 2026-09-02 |
| GOAL-068 | La grille effective : les périodes fusionnent, la plus courte l'emporte | `[x]` — clos le 2026-09-02 ; **reste à écouter** la jonction de 20 h et la reprise après un programme |
| GOAL-069 | Le picto de volume est dessiné, comme les autres | `[x]` — clos le 2026-09-02 |
| GOAL-070 | La liste des prochains titres ne se coupe plus en silence | `[x]` — clos le 2026-09-02 |
| GOAL-071 | Une plage `era_fan` choisit ses décennies | `[x]` — clos le 2026-09-02 ; **reste à écouter** la plage de 12 h |
| GOAL-072 | Le verre d'iOS : la matière, la palette du système, un en-tête qui flotte | `[x]` — clos le 2026-09-03, rendu validé à l'œil le même jour |
| GOAL-073 | L'état d'antenne poussé par SSE, et une coupure qui ne s'écrit plus | `[x]` — clos le 2026-09-03 ; **reste à constater** une coupure réseau et un retour d'arrière-plan depuis un téléphone |
| GOAL-074 | La reprise ne laisse plus rien entendre de la veille, et l'annonce ne troue plus l'antenne | `[x]` — clos le 2026-09-06 ; T03 abandonnée sur arbitrage ; **reste à écouter** la reprise du matin |
| GOAL-075 | Le premier tirage d'une reprise ne fait plus attendre l'antenne | `[ ]` — ouvert le 2026-09-06 par GOAL-074-T05 |
| GOAL-076 | Le thème d'une plage « au hasard » ne se retire plus tout seul | `[ ]` — ouvert le 2026-09-06, sur analyse, sans constat à l'antenne |
| GOAL-077 | Une plage « podcasts » : plusieurs flux, tirés au hasard | `[ ]` — ouvert le 2026-09-06, forme tranchée (n°35) |
| GOAL-078 | La liste des prochains titres coud la grille derrière elle | `[ ]` — ouvert le 2026-09-06, forme tranchée (n°34 amendée) |
| GOAL-079 | `radio.liq` reçoit la réécriture du ton que les autres ont eue | `[ ]` — ouvert le 2026-09-06, sur revue : le fichier a échappé à `ea20e20` |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).
