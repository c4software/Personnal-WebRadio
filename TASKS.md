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

**GOAL-076, GOAL-077 et GOAL-080 sont clos le 2026-09-06.** Le thème d'une plage « au
hasard » ne se retire plus tout seul — défaut trouvé en relisant, constaté par
un test, jamais entendu. Et une émission peut tenir plusieurs flux et déclarer
sa fin : les six podcasts demandés par l'auteur tiennent en deux plages le
week-end, groupées par longueur. **GOAL-080** a fermé ce que la revue de
GOAL-077 avait trouvé — dont une coupure d'antenne : trois flux lus l'un après
l'autre dans la requête dépassaient le délai du diffuseur. **GOAL-081** a
fermé la régression que GOAL-080 avait ouverte, un morceau de musique
intercalé entre chaque épisode d'une plage.

**GOAL-083 est clos le 2026-09-06** : ce qu'une relecture de correction de
tout `webradio/` a trouvé, chaque constat reproduit par script avant d'être
retenu. Deux bloquants, trouvés en lisant et jamais entendus — la fenêtre de
non-répétition contournée dès qu'un artiste hors fenêtre attendait, et
l'épisode inscrit « diffusé » quand le diffuseur le demande plutôt qu'à la
prise d'antenne, ce qui perdait une émission hebdomadaire pour de bon. Douze
tâches, douze commits. **Reste à écouter** (AGENTS.md §4.1) : une reprise après
pause avec une émission en avance, la jonction qui suit une émission, la
reprise de la musique à la fin d'un direct, et un morceau qui commence pendant
un battement d'heure pleine. **Au déploiement** : la configuration de
production doit déclarer `liquidsoap.url = "http://liquidsoap:8000"`, la
variable d'environnement ayant disparu du Compose.

**GOAL-084 est clos le 2026-09-06** : l'antenne annonçait la plage de la grille
pendant une émission, alors que l'émission la remplace.

**GOAL-078 est clos le 2026-09-06** : la liste des prochains titres coud
derrière elle les périodes de la grille effective, jusqu'à
`web.upcoming_horizon_minutes` (180 par défaut). **Reste à écouter** la liste
pendant l'émission de dimanche prochain.

**GOAL-085 est clos le 2026-09-06** : l'antenne dit la durée de ce qui passe et
ce qui en est écoulé quand elle les connaît, et la page en fait une barre qu'elle
avance elle-même entre deux messages. **Reste à écouter** le décalage entre la
barre et l'oreille, et l'écran de verrouillage sur téléphone.

**GOAL-086 est ouvert le 2026-09-06**, sur constat de l'auteur à 21 h 12 :
« Passer » accepté pendant un épisode de plage de podcasts, et l'antenne partie
sur la musique que le diffuseur avait d'avance. Deux défauts distincts, le
redémarrage aveugle (T02, close) et l'avance qui ne connaît pas les cases de
podcasts (T04, T05).

**Prochaine tâche** : GOAL-086-T06, la documentation finale et l'**écoute
réelle** de la manœuvre pendant une vraie plage de podcasts (T01 à T05 sont
faites). Puis GOAL-082-T04, le seuil de vivier appliqué ou non à l'ancre
d'`artist_fan`.

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
      La relecture du 2026-09-06 y rattache un second point à mesurer : le
      verrou de la charnière couvre **toute** la préparation, donc `/playing`
      et le `/playout/next` de préfetch attendent jusqu'à `draw.lookahead`
      tirages. Ce second point est traité par GOAL-075-T04, qui sort le
      parcours de bibliothèque du verrou ; ce qui reste sous le verrou est le
      tirage lui-même, et c'est ce que la mesure à l'antenne doit chiffrer.
      **Mesure partielle du 2026-09-06**, faite hors antenne depuis la machine
      de développement, contre le Navidrome de l'auteur (5 704 pistes) et une
      base SQLite locale :
      parcours complet à froid 0,93 s, à chaud 0,00 s, un genre 0,03 à 0,04 s ;
      **pondération** d'un tirage libre (`learning.weigh` sur 5 704 candidats)
      **1,34 s**, rien ne la met en cache. Le premier tirage d'une reprise vaut
      donc ~2,3 s ici (parcours + pondération) et chaque tirage libre suivant
      ~1,3 s ; avec `draw.lookahead = 8`, une préparation en tirage libre
      approche les dix secondes sous le verrou, et `frontal` est probablement
      plus lent. GOAL-075-T05 s'attaque à la pondération, qui devrait tomber
      sous 0,1 s. **Mesuré après T05, même machine, même bibliothèque** :
      **0,02 s** pour les 5 704 pistes, base de cinquante lignes de votes,
      soit soixante fois moins. Un tirage libre vaut donc ~0,02 s de
      pondération, et le premier tirage d'une reprise ~1 s, le parcours seul —
      hors du verrou depuis T04. Reste à confirmer à l'antenne : la mesure du
      délai réel du diffuseur n'est toujours pas faite.
- [x] **GOAL-075-T04** — Réchauffer le cache de la source hors du verrou, et ne
      tirer que dessous. La préparation de fond tient le verrou de la charnière
      pendant tous ses tirages ; un tirage sous une plage dont le genre n'est
      pas au cache coûte un parcours complet de Navidrome (une dizaine d'appels
      HTTP), et pendant ce temps `/playout/next` et `/playing` attendent.
      Choix technique : `RadioProgramme.constraints_to_prepare()` rend, sans
      rien tirer, les contraintes que la préparation imposera, et
      `RadioProgramme.warm()` appelle la source pour chacune. `_preparer_l_avance`
      calcule les contraintes sous le verrou (c'est immédiat), réchauffe hors
      du verrou, puis prépare sous le verrou : les tirages trouvent le cache
      chaud. Le réchauffage ne lève jamais — une source injoignable est
      journalisée en debug et la préparation fait comme avant.
      Deux arbitrages : `Schedule.constraint_to_draw` consomme le hasard sur une
      plage multi-genres, donc le réchauffage rend **tous** les genres de la
      plage plutôt que d'en tirer un, sinon l'avance ne serait plus rejouable ;
      et une plage au hasard ne voit pas son thème résolu pour réchauffer (le
      résoudre en avance déplacerait ses tirages dans la séquence du hasard) —
      on réchauffe le parcours complet, qui est justement ce que le tirage du
      thème consulte. Un `tracks_by(artiste)` n'est pas réchauffé : la source ne
      le met pas en cache.
      Ce que ça vaut : le premier `/playout/next` d'une reprise paie toujours
      **un** parcours (T01), mais le suivant n'attend plus la préparation
      derrière un parcours froid, et `/playing` non plus. Reste le premier
      tirage lui-même, et la mesure de T03.
- [x] **GOAL-075-T05** — Lire les scores de votes une fois par tirage, pas deux
      fois par candidat. Mesuré le 2026-09-06 (T03) : peser les 5 704 pistes
      d'un tirage libre coûtait 1,34 s, deux `SELECT` par piste, et rien ne les
      mettait en cache — le cache de bibliothèque chaud n'y changeait rien.
      C'est le coût dominant du tirage, devant le parcours d'une seconde que
      T04 vient de sortir du verrou.
      Choix technique : les poids sont fournis **par tirage** et non par piste.
      `Weigh` devient `Callable[[Sequence[Track]], list[float]]`, `Queue._tirer`
      appelle le peseur une fois, et `Learning.weigh` lit `all_scores()` une
      fois — la table ne contient que les cibles votées, quelques dizaines de
      lignes — puis pèse en mémoire. `all_scores` applique la même décroissance
      à la lecture que `scores` (ARCHITECTURE.md §5.2), les poids sont donc
      inchangés, et un test le vérifie cible par cible.
      Pourquoi pas un instantané gardé entre deux tirages : il faudrait une
      durée de vie, donc une clé TOML et une horloge dans `Learning`, et un vote
      supprimé depuis la page des votes ne passe pas par `remember()` — il
      resterait dans l'instantané. Un relevé par tirage n'a aucun de ces deux
      défauts et coûte une requête.
      Mesuré après coup sur la même machine et la même bibliothèque :
      **0,02 s** pour peser 5 704 pistes, contre 1,34 s avant, avec cinquante
      lignes de votes en base.

---

## GOAL-081 — Ce que la lecture de fond a cassé, et deux fenêtres fausses

Ouvert et clos le 2026-09-06, sur revue de clôture. GOAL-080 fermait une
coupure d'antenne ; il en a ouvert une régression audible.

- [x] **GOAL-081-T01** — Une plage n'intercale plus de musique entre deux
      épisodes. Le cache dure 900 s, un épisode long en dure 4 600 : la garde
      expirait **au milieu**, la jonction suivante ne trouvait rien et rendait
      la main à la musique. Motif mesuré sur trois flux de soixante-dix
      minutes : `épisode, musique, épisode, musique, épisode`. Le catalogue
      périmé sert désormais pendant qu'on le relit, et la relecture part au
      même instant — sans quoi un épisode publié n'apparaîtrait jamais.
      Le Fake des tests ne pouvait pas voir ce défaut : son cache n'expirait
      jamais. Il expire maintenant, comme le vrai.
- [x] **GOAL-081-T02** — `podcast.cache_seconds = 0` ne diffusait plus jamais
      un podcast : sans cache, il n'y a rien à servir en attendant, et la
      lecture différée rendait `None` à chaque jonction. L'option documentée
      était silencieusement morte. Sans cache, on lit donc sur place.
- [x] **GOAL-081-T03** — Deux fenêtres fausses autour de minuit. La
      préparation d'une case (`opens_within`) regardait le lendemain — qui ne
      peut pas porter une case déjà passée — et manquait le jour de l'instant :
      une case de 23 h 55 n'était pas vue depuis 23 h 50. Et la règle de
      recouvrement appariait un jour et une tranche qui ne se rencontrent pas,
      refusant une émission du samedi 1 h sous une plage du samedi 22 h à 2 h.
- [x] **GOAL-081-T04** — Une chaîne YouTube se lisait dans la requête que
      le diffuseur attend, et `yt-dlp` s'y résout : deux appels bornés par
      `youtube.timeout_seconds` (60 s en production) contre les 10 s du
      diffuseur, sans cache, à chaque jonction pendant deux jours. C'est la
      classe de défaut que GOAL-080 avait fermée pour les podcasts, avec un
      budget pire. Corrigée de la même façon : un cache sur `YoutubeChannel`,
      la lecture dans le fil de fond, et le préchauffage avant l'ouverture de
      la case.

---

## GOAL-082 — Une carte blanche ne rejoue plus le même titre toute l'heure

Ouvert le 2026-09-06 sur constat de l'auteur à l'antenne, deux captures à
l'appui. La plage `random = "artist"` de 14 h est tombée sur un artiste
n'ayant qu'un seul titre dans la bibliothèque, et l'a rejoué huit fois pour
remplir l'heure.

Mesuré en production : 5 704 pistes, 1 818 artistes, dont 1 277 (70 %) n'ont
qu'un titre. Le tirage se fait par une piste, donc pondéré : une carte blanche
sur cinq tombait sur un artiste à titre unique.

- [x] **GOAL-082-T01** — Une carte blanche n'a le droit de tirer qu'un artiste
      ayant au moins `draw.min_theme_tracks` titres (SPECS.md §7 n°36, 15 par
      défaut). Le seuil vient de la mesure : 3,6 minutes de médiane, donc une
      heure demande une quinzaine de titres, et 15 laisse encore 61 artistes
      éligibles. Aucun artiste au-dessus du seuil : il est relâché plutôt que
      la plage abandonnée, comme le fait la non-répétition.
- [x] **GOAL-082-T02** — La fenêtre de non-répétition était vidée quand une
      plage impose un vivier étroit, et rien ne la remplit. `Queue._choisir`
      appelle `shrink()` en boucle jusqu'à ce que la fenêtre soit vide, alors
      que l'exclusion venait de `en_attente`, sur lequel elle n'a aucune prise.
      Conséquence à la sortie de la plage : les artistes passés juste avant
      redeviennent éligibles immédiatement, alors que §4.2 devait les tenir
      cinq artistes. Trouvé en analysant, jamais entendu. Elle ne rétrécit
      plus que si c'est bien elle qui bloque ; le test échoue sans le
      correctif, vérifié en le retirant.
- [x] **GOAL-082-T03** — Le même trou pour `random = "genre"`, latent : aucune
      plage ne l'utilise aujourd'hui. Il serait **pire** — le tirage d'un genre
      est uniforme, pas pondéré par les titres, et 110 des 227 genres de la
      bibliothèque n'ont qu'un ou deux titres : près d'une occurrence sur deux
      tomberait dans le vide. Le seuil de T01 s'y applique donc aussi, et la
      clé devient `draw.min_theme_tracks` : elle ne dépend pas de la nature du
      vivier mais de ce qu'une occurrence consomme. Le décompte se fait sur le
      parcours, pas sur `genres()`, qui peut annoncer un genre sans piste.
- [ ] **GOAL-082-T04** — Dire si le seuil doit valoir aussi pour l'ancre
      d'`artist_fan` (n°31). L'analyse dit que le cas y est **borné** : une
      ancre à un seul titre rompt la suite au lieu de la répéter, et la vague
      n'a simplement pas lieu — même classe que GOAL-071, moins grave.

---

## GOAL-084 — L'antenne n'annonce plus la plage pendant une émission

Ouvert le 2026-09-06 sur constat de l'auteur à l'antenne, à 20 h 04. L'émission
« Podcasts - actus » (20:00→21:00 le dimanche) passait, la carte « Antenne »
disait bien EMISSION avec le titre de l'épisode, et le sous-titre annonçait
« Moment · Rock, Rock français, Alternatif & indé, Rock classique, Folk Rock
(double dose) » — la plage de 20 h, que l'émission remplace (SPECS.md §4.4). La
barre du lecteur affichait la même chose, et l'écran de verrouillage recevait ce
libellé comme album.

- [x] **GOAL-084-T01** — `LiveRadio` relayait le rappel `moment` sans regarder
      ce qui passe, alors qu'elle retient déjà la nature déclarée. Tant qu'elle
      vaut `SHOW` ou `NEWS`, `moment()` rend `None`, `moment_random()` rend faux
      et `redraw_moment()` refuse avec son motif ; un jingle garde le moment,
      l'habillage appartient à la plage. La correction vit dans la façade, pas
      dans le câblage. Vérifié : le test « pendant une émission, aucun moment »
      échoue sans le correctif, constaté en retirant la garde de `moment()`.

**Reste à écouter** (AGENTS.md §4.1) : la barre du lecteur et l'écran de
verrouillage pendant l'émission de dimanche prochain.

---

## GOAL-086 — Passer un épisode pioche un autre épisode

Ouvert le 2026-09-06 sur constat de l'auteur à l'antenne, à 21 h 12. Pendant un
épisode d'une plage de podcasts, « Passer » a été **accepté**, et le diffuseur a
joué la musique qu'il avait d'avance — alors que `Control` refuse tout `stop`
pendant une émission.

L'analyse, rejouée sur la pile réelle avec `FrozenClock`, sépare **deux défauts** :

1. **Le redémarrage aveugle.** Le service `radio` avait été redéployé pendant
   l'épisode. Le diffuseur n'annonce qu'au **début** d'une entrée (`radio.liq`,
   `on_track`) : le processus neuf ne reçoit aucun `POST /playout/playing` avant
   la fin de l'entrée en cours. `Control` et `LiveRadio` démarraient en nature
   `MUSIC`, l'API rendait `kind="musique"`, la page activait « Passer », le vote
   passait, et l'avance (une musique) prenait l'antenne. Le vote n'a même rien
   pesé : sans piste, `LiveRadio.vote` ne retient rien.
2. **L'avance qui ne connaît pas les cases de podcasts.** Ce que le diffuseur
   tenait d'avance était une musique tirée sans voir la case ouverte : même sans
   redémarrage, un `stop` pendant un épisode aurait à choisir un autre épisode,
   pas ce morceau.

- [x] **GOAL-086-T01** — Relevé Liquidsoap sur maquette (docs/liquidsoap.md
      §12) : `programme.fetch()` en 2.3.3, une route combinée remplacer-puis-
      sauter et le blanc pendant la résolution d'un épisode lourd, requeue+skip
      côté API, ordre `on_track`/recomplètement, ré-annonce de la piste en
      cours. Aucun mécanisme n'est écrit avant ce relevé (AGENTS.md §3).
      **Ce qui a été mesuré** : `fetch()` existe et est synchrone (il bloque le
      gestionnaire harbor toute la résolution, pas la diffusion) ; la route
      combinée `set_queue([])` + `fetch()` + `skip()` ne laisse aucun blanc mais
      coûte **deux tirages**, et c'est le plus rapide qui prend l'antenne ;
      `/requeue` puis `/skip` laisse **5,75 s de blanc** pour un épisode de 8 s
      de résolution, et attendre entre les deux ne fait qu'échanger du silence
      contre de l'épisode en cours ; `/playing` et le `/next` de recomplètement
      sont **concurrents**, à la milliseconde, et l'ordre n'est pas garanti ; la
      ré-annonce de la piste en cours marche depuis un `ref` (8,7 ms) comme
      depuis `source.last_metadata`.
- [x] **GOAL-086-T02** — Un processus qui redémarre ne sait pas ce qui passe :
      il le dit et refuse les votes. Nature `Kind.UNKNOWN` (`"inconnu"`) dans le
      noyau et dans l'API ; `Control` et `LiveRadio` y démarrent ; une entrée
      demandée avant ce démarrage s'affiche par ses étiquettes mais reste de
      nature inconnue, et s'inscrit au journal des titres avec cette nature
      plutôt que d'être perdue. Motif de refus : « la radio vient de redémarrer :
      elle ne sait pas encore ce qui passe ». La page n'a rien demandé :
      `voteImpossible` désactive déjà tout ce qui n'est pas `musique`, et le
      libellé de la carte affiche la nature telle quelle. Décision n°42
      (SPECS.md §7), avec son coût : après un déploiement en plein épisode, les
      deux boutons sont morts jusqu'à la jonction suivante.
- [x] **GOAL-086-T03** — Le diffuseur redit ce qu'il joue après un redémarrage
      de `radio`, et l'avance est redécidée par le processus neuf.
      **Les entrées se décrivent** : `next_entry` préfixe chaque entrée d'un
      `annotate:` portant `radio_kind`, `radio_label` et `radio_duration`,
      valeurs citées et échappées — un direct est exclu, le script reconnaît son
      entrée à `live:`. Une entrée déjà annotée (avance replacée) ne l'est pas
      deux fois, ce qui contourne le point incertain de docs/liquidsoap.md §7
      sur l'`annotate:` imbriqué, jingles compris.
      **Le script redit** : `derniere_annonce` garde le corps du dernier
      `on_track`, daté par `time()` en quatrième ligne, et `POST /announce` le
      re-poste tel quel (rien à redire s'il n'y a rien eu).
      **L'API l'ordonne** : au premier battement d'auditeurs d'un processus dont
      `_entree_en_cours` est nul, `/announce` puis `/requeue`, **une seule
      fois** ; hors verrou, et seulement si les deux ordres sont câblés.
      **`playing()` restaure** la nature, le libellé et la longueur lus dans
      l'entrée, datés du vrai début ; une ré-annonce de l'entrée déjà en cours
      ne redéclare rien.
      **Mesuré sur la maquette** (docs/liquidsoap.md §13) : des clés `annotate:`
      arbitraires traversent jusqu'à `on_track` et au POST ; une valeur non
      citée fait **perdre l'entrée entière** (un tiret ou un pourcent suffit) ;
      une valeur citée porte virgule, deux-points, accents et `"` échappé ;
      `radio_duration` ne coupe rien ; `/announce` redit le même corps en moins
      de 10 ms.
      **Résidus** : une entrée demandée par un script d'avant ce déploiement ne
      porte aucune nature et reste `inconnu` ; une musique se restaure sans
      `Track`, faute d'une recherche par identifiant dans `MusicSource` — le
      `stop` coupe, l'encore est accepté sans rien retenir. Décision n°42
      amendée (SPECS.md §7).
- [x] **GOAL-086-T04** — L'avance datée connaît les cases de podcasts.
      `RadioProgramme.current_moment()` rend `(période, case)`, où la case vient
      de `Shows.open_band_slot()` : `PodcastSlot(show, start, awaited)`, lue sans
      réseau — une plage déclare sa fin. `awaited` dit qu'un épisode est demandé
      sans avoir commencé, ce qui fait changer la clé à son `/playing`. Le
      rejugement du battement s'élargit aux `Kind.SHOW` qui portent une case de
      plage ; un direct et un podcast seul n'en portent pas.
      **Vérifié par rejeu** sur la pile réelle (`RadioProgramme` +
      `LiquidsoapPlayout` + `Shows`, `FrozenClock`) : la soirée du dimanche
      (19 h 57 musique, 20 h 00 épisode A, 20 h 01 musique faute de neuf,
      21 h 00 `/requeue` et épisode « longs formats ») **échoue sans le
      correctif** — la clé réduite à sa période ne rassit rien, et trois des six
      tests tombent. Le garde-fou est testé : quatre battements sous une case
      inchangée n'ordonnent aucun `/requeue`.
      **Ce qu'on retient de `core/shows.py`** : `open_slot` n'a pas bougé. Elle
      ne connaît pas les durées d'une plage, et refuser à `end` un épisode qui
      commencerait après demanderait une durée que la case n'a pas ; c'est le
      rejugement qui jette l'épisode demandé mais pas commencé. Décision n°43
      (SPECS.md §7), qui amende la n°33 et la n°35.
- [x] **GOAL-086-T05** — `stop` pendant un épisode de plage pioche un autre
      épisode. `Control.declare(kind, skippable=…)` : `stop` accepté sur un
      épisode de plage, `encore` refusé sur toute émission avec son propre
      motif, et refus motivé — « aucun autre épisode à piocher : l'épisode
      finit » — quand aucun flux n'a plus de neuf. La question se lit au
      **moment du vote**, par un rappel injecté (`Shows.has_another_episode`)
      qui compte les flux **en cache** ayant du neuf : ni hasard ni réseau
      consommés, et un test le constate.
      **Le drapeau voyage** : `Shows.due()` le rend, `RadioProgramme.on_kind`
      et `Pending` le portent, l'annotation `radio_skippable` s'ajoute aux clés
      de T03 pour qu'un processus neuf retrouve un épisode passable, et
      `OnAir.skippable` le rend à l'API — la page en tire deux règles
      distinctes, Passer sur `musique` ou `skippable`, Encore sur `musique`
      seul.
      **Le diffuseur remplace avant de sauter** : route `POST /skip-fresh`
      (`set_queue([])`, `fetch()`, `skip()`), refusée à vide comme `/skip`,
      journalisée à chaque étape ; `LiveRadio` l'ordonne au lieu de `/skip` et
      jette son avance sans `/requeue` supplémentaire ; l'ordre part d'un fil
      détaché, sans attendre une réponse que `fetch()` retient toute la
      résolution. Décisions n°44 et n°45 (SPECS.md §7).
      **Mesuré sur la maquette de §12** (docs/liquidsoap.md §14) : la variante
      qui devait éviter le double tirage — `fetch()` d'abord, puis
      `set_queue([la fraîche])` — **ne marche pas**. `set_queue` détruit les
      requêtes de la file, y compris celle qu'on lui repasse : `set_queue
      (queue())` fait tomber la file de 1 à 0, et la variante perd l'entrée
      fraîche après avoir bloqué le gestionnaire 8,04 s pour la télécharger.
      À l'antenne : pas de blanc (ton `a` de 0,50 à 16,50 s sans
      discontinuité), mais ni `b` ni `c` ne passent et c'est `d`, tiré par le
      `/next` d'après, qui prend l'antenne à 17,00 s — **deux tirages quand
      même**, dont un jeté. C'est donc la route de §12 qui est retenue, son
      double tirage assumé : ses deux entrées sont toutes deux consommées.
      **Résidus** : sans `podcast.cache_seconds`, rien n'est gardé et le vote
      est refusé comme s'il n'y avait plus rien à piocher ; l'API ne sait pas
      laquelle des deux entrées tirées prend l'antenne, c'est le `/playing` qui
      le lui dit ; deux « Passer » coup sur coup ne sont toujours pas mesurés
      (docs/liquidsoap.md §12).
- [ ] **GOAL-086-T06** — Documentation (SPECS.md §4.6, §4.8, §4.11 ;
      ARCHITECTURE.md ; README) et **écoute réelle** de la manœuvre pendant une
      vraie plage de podcasts (AGENTS.md §4.1).

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
| GOAL-076 | Le thème d'une plage « au hasard » ne se retire plus tout seul | `[x]` — clos le 2026-09-06 ; défaut constaté par un test avant correction, jamais entendu à l'antenne |
| GOAL-077 | Une plage « podcasts » : plusieurs flux, tirés au hasard | `[x]` — clos le 2026-09-06 ; **reste à écouter** l'enchaînement et le débordement |
| GOAL-081 | Ce que la lecture de fond a cassé, et deux fenêtres fausses | `[-]` — ouvert le 2026-09-06 ; T04 (YouTube) reste |
| GOAL-078 | La liste des prochains titres coud la grille derrière elle | `[x]` — clos le 2026-09-06 ; **reste à écouter** la liste pendant l'émission de dimanche |
| GOAL-080 | Ce qu'une plage podcasts expose, et que la revue a trouvé | `[x]` — clos le 2026-09-06 ; **reste à écouter** le début d'une plage |
| GOAL-082 | Une carte blanche ne rejoue plus le même titre toute l'heure | `[-]` — ouvert le 2026-09-06, sur constat à l'antenne |
| GOAL-079 | Les commentaires du code reviennent au ton d'un développeur | `[x]` — clos le 2026-09-06 ; `radio.liq` et cinq fichiers Python |
| GOAL-083 | Ce que la relecture du 2026-09-06 a trouvé | `[x]` — clos le 2026-09-06 ; la configuration de production doit déclarer `liquidsoap.url` |
| GOAL-084 | L'antenne n'annonce plus la plage pendant une émission | `[x]` — clos le 2026-09-06 ; **reste à écouter** la barre et l'écran de verrouillage pendant une émission |
| GOAL-085 | L'antenne dit où en est ce qui passe | `[x]` — clos le 2026-09-06 ; **reste à écouter** le décalage entre la barre et l'oreille, et l'écran de verrouillage |
| GOAL-086 | Passer un épisode pioche un autre épisode | `[-]` — ouvert le 2026-09-06 sur constat à l'antenne ; T02 close, T01 en cours |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).
