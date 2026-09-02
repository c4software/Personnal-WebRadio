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

**GOAL-071 est ouvert le 2026-09-02**, après un audit de la grille contre la
bibliothèque réelle : la plage de 12 h porte `era_fan`, mais son vivier ne
compte qu'**un** titre des années 1970 et sept des années 1990, quand une vague
en demande deux à six. La plage se rompt à peine ouverte, sans que rien ne le
dise. Une plage pourra déclarer les décennies dans lesquelles elle tire.

- [x] **GOAL-071-T01** — Une plage porte ses décennies et le tirage s'y tient :
      `Band.eras`, `Constraint.eras`, filtre dans `core/queue.py`, repli
      journalisé quand la plage n'a rien dans ces décennies ; SPECS.md §4.4.
      Les quatre tests ont été vus échouer filtre retiré.
- [-] **GOAL-071-T02** — La clé `eras` du TOML : schéma, chargeur, câblage
      `app/main.py`, SPECS.md §6

**Prochaine tâche** : GOAL-071-T02.

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
| GOAL-071 | Une plage `era_fan` choisit ses décennies | `[-]` — ouvert le 2026-09-02 |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).
