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

**GOAL-074 est ouvert le 2026-09-06** : l'auteur a de nouveau entendu, en se
branchant le matin, un micro-flash de la chanson de la veille avant que la
radio ne bascule. Le garde-fou de GOAL-055 avait pourtant fonctionné — le
journal le dit. Ce qu'il ne couvre pas : le temps que met `cross` à
transitionner. Relevé en maquette à **160 ms** (docs/liquidsoap.md §10),
mesuré à **7 s** en production le 2026-09-06 ; pendant ces 7 s l'antenne est
déjà rendue et sert le reliquat de la veille.

**Prochaine tâche** : GOAL-074-T03 attend un arbitrage de l'auteur (trois
voies, aucune gratuite), puis GOAL-075-T01.

---

## GOAL-074 — La reprise ne laisse plus rien entendre de la veille, et l'annonce ne troue plus l'antenne

Deux défauts constatés dans les journaux de production du 2026-09-06, tous
deux dans `radio.liq`, tous deux invisibles aux tests (AGENTS.md §4.1).

**Le flash.** À 07:28:21 UTC, la purge de reprise à neuf (SPECS.md §7 n°30)
s'ordonne correctement et arme `reliquat_a_taire` ; l'antenne est rendue dans
la même seconde ; la transition de `cross` qui doit jeter le reliquat ne
s'exécute qu'à 07:28:28. Elle ne trouve alors plus que **0,04 s** à jeter
(`cross: Analysis … 0.04s / 2.00s`), contre **1,99 s** les 2026-09-02 et
2026-09-05. Les ~1,95 s manquantes sont sorties vers l'encodeur pendant
l'attente : c'est le flash. Le morceau frais, lui, entre après la rampe de
prise d'antenne, donc **à plein gain**.

**Le trou.** `on_track` poste l'annonce à l'API dans le fil de diffusion,
alors qu'`annoncer_le_direct` est enveloppé dans `thread.run` pour cette
raison exacte. Les deux `catchup` de 2,79 s et 2,94 s du 2026-09-06 suivent
exactement les deux annonces lentes ; aucune des six transitions rapides du
matin n'en produit.

- [x] **GOAL-074-T01** — Relever ce que la chaîne sert entre le saut et la
      transition de `cross`, quand l'entrée fraîche tarde. docs/liquidsoap.md
      §11. Trois constats : le délai de la transition ne dépend que de la
      latence de l'entrée fraîche ; pendant l'attente le tampon `before` part
      **à l'antenne** — 2,00 s du ton d'avant la pause, jusqu'à −16,7 dB, soit
      ~87 % du volume — puis l'antenne retombe sur `blank()` ; et
      `output.harbor` ne sert **aucune** rafale d'octets déjà encodés, ce qui
      était l'autre hypothèse. Le garde-fou de §10 est donc nécessaire mais
      pas suffisant : une transition s'exécute trop tard, seul le gain
      protège.
- [x] **GOAL-074-T02** — L'antenne reste muette du saut à antenne vide
      jusqu'à l'entrée du morceau frais, et le morceau frais entre sous la
      rampe de prise d'antenne. Le témoin `reliquat_a_taire` existe déjà et
      dit exactement cela ; `prise_direct` doit le lever, sinon un direct pris
      entre le saut et la transition resterait silencieux toute la case.
      SPECS.md §4.7 et §7 n°30 disent le comportement obtenu.
      Mesuré sur la maquette de §11, API retardée de 4 s : le ton d'avant la
      pause passe de −16,7 dB à **−99 dB** (silence absolu), et le morceau
      frais entre sous la rampe (−45 → −19 dB) au lieu d'entrer à froid.
      Aucune régression sur le régime rapide. Le garde-fou du direct est
      **raisonné, pas mesuré** : la maquette n'a pas su créer la course — la
      transition a jeté le reliquat une seconde avant que le direct ne prenne
      l'antenne. Il reste parce que rien d'autre ne lève le muet quand
      `programme` ne reprend jamais l'antenne.
      **À écouter** (AGENTS.md §4.1) : la reprise du matin après une nuit
      sans auditeur — que rien de la veille ne s'entende, que le silence
      d'attente ne dure pas au point d'inquiéter, et que le morceau frais
      entre en fondu et non à froid.
- [!] **GOAL-074-T03** — `on_track` annonce sans bloquer le fil de diffusion,
      comme `annoncer_le_direct`. Les deux témoins qu'il pose —
      `piste_commencee` et `direct_arme` — restent posés dans le fil : ce sont
      eux qui garantissent qu'un direct entre à la jonction
      (docs/liquidsoap.md §9), et les différer les décalerait.
      **BLOQUÉ le 2026-09-06 : le remède naïf ment sur l'antenne.** Mesuré
      (docs/liquidsoap.md §11) : `thread.run` **ne sérialise pas** — deux
      annonces lancées à 2 s d'écart, la lente est doublée par la rapide. Un
      jingle de 5 s suivi d'un morceau, avec l'API lente qu'on a, laisserait
      le jingle affiché à l'antenne pendant la musique. Et la 2.3.3 n'offre
      **aucun verrou** : `--list-functions` ne donne que `thread.run`,
      `thread.run.recurrent`, `thread.delay`, `thread.on_error`,
      `thread.pause`, `thread.when`.
      Trois voies, et le choix appartient à l'auteur :
      **(a)** ne rien changer — le trou de ~3 s reste, mais l'ordre est
      garanti par le blocage lui-même, et T05 s'attaque à la cause ;
      **(b)** une file consommée par un unique `thread.run.recurrent` —
      l'ordre est tenu, mais la file est écrite par le fil de diffusion sans
      protection : une annonce peut se perdre, donc un titre manquer au
      journal ;
      **(c)** un délai d'attente court propre à `/playout/playing` — le trou
      est borné, et l'annonce est perdue quand l'API dépasse ce délai.
      Aucune n'est gratuite. (a) est la seule qui ne perde jamais un titre.
      **À écouter** si elle est levée (AGENTS.md §4.1) : qu'aucune jonction
      ne laisse de blanc.
- [x] **GOAL-074-T04** — Le conteneur du diffuseur lit l'heure de l'hôte.
      `docker-compose.yml` ne monte `/etc/localtime` que pour `radio` : les
      deux journaux sont dans deux fuseaux, ce qui a failli faire lire de
      travers l'incident du 2026-09-06. Sans effet sur la grille — le script
      ne connaît aucun moment.
- [x] **GOAL-074-T05** — Mesurer ce que met `/playout/next` à répondre après
      une purge, et le dire. **Mesuré, et la cause est chez nous.**
      Le premier `/next` d'une reprise : **4 s** le 2026-09-06 (purge 07:28:21
      UTC, réponse 07:28:25) ; le 2026-09-05, **plus de 10 s** — au-delà
      d'`api_timeout` — deux échecs de suite, et le diffuseur a **coupé**
      (« l'API ne répond plus »), 21 s de silence et un redémarrage à froid.
      Les `/next` du régime établi, eux, répondent en 0 à 2 s.
      La cause : `next_entry` appelle `prepare()` **dans la requête**
      (`app/liquidsoap_playout.py:128`), qui remplit toute l'avance —
      `draw.lookahead = 8` en production. Le premier `/next` d'une reprise
      paie donc neuf tirages, contre un cache de bibliothèque
      (`subsonic.cache_seconds = 3600`) forcément expiré après une pause de
      17 h. Chaque tirage rouvre la bibliothèque chez Navidrome.
      Le remède — préparer hors de la requête — touche la concurrence de la
      chaîne : il ouvre **GOAL-075**, comme prévu, plutôt que de se corriger
      ici à l'aveugle.

Le correctif n'atteint l'antenne qu'après un `git push`, une image CI et un
`docker compose pull` sur `frontal` : trois actions sortantes, à l'auteur
(AGENTS.md §1.2).

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

- [ ] **GOAL-075-T01** — Rendre l'entrée dès qu'elle est tirée, et préparer
      l'avance après avoir répondu. La préparation est déjà décrite comme
      « une commodité, pas une cause d'arrêt » (`app/playout.py`) et se veut
      « hors verrou » : reste à établir qu'elle peut l'être hors requête sans
      course avec la jonction suivante.
- [ ] **GOAL-075-T02** — Que le cache de bibliothèque se réchauffe au réveil
      de l'antenne plutôt qu'au premier tirage. À instruire : `declare_listeners`
      s'exécute déjà avant que l'antenne ne soit rendue, mais dans la requête
      que le diffuseur attend — réchauffer là déplacerait l'attente sans la
      supprimer.
- [ ] **GOAL-075-T03** — Ce que le diffuseur fait d'une API lente. Deux
      échecs de suite le font couper (SPECS.md §5.1), et un tirage de reprise
      légitime a dépassé `api_timeout`. Décider si ce délai doit distinguer
      « lente » de « morte », ou si T01 suffit à ce que la question ne se pose
      plus.

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
| GOAL-074 | La reprise ne laisse plus rien entendre de la veille, et l'annonce ne troue plus l'antenne | `[-]` — ouvert le 2026-09-06 ; T01, T02, T04, T05 faites ; **T03 bloquée** sur un arbitrage |
| GOAL-075 | Le premier tirage d'une reprise ne fait plus attendre l'antenne | `[ ]` — ouvert le 2026-09-06 par GOAL-074-T05 |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).
