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

**Goal ouvert : GOAL-051** — quatre défauts constatés à l'antenne le
2026-09-02 au matin, à la rencontre du direct (GOAL-015) et de la reprise à
neuf (GOAL-041). Décisions restantes de SPECS.md §7 : la **n°9** est une
conséquence consignée, non une question ; la **n°12** (combiner plusieurs
sources actives) est délibérément différée jusqu'à la deuxième source de
musique.

**Reste à écouter** (AGENTS.md §4.1) : GOAL-050 — la montée du volume en deux
secondes au branchement du premier auditeur, y compris quand l'antenne reprend
au milieu d'un morceau. Les écoutes de GOAL-044 (modes d'enchaînement) et
GOAL-047 (coupe au plafond) ont été validées par l'auteur le 2026-09-01.

**Prochaine tâche** : GOAL-051-T06 — elle porte un arbitrage audible et
attend l'auteur (AGENTS.md §1.2, cas 2). T04 en dépend.

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
| GOAL-051 | Le direct ne ment plus à l'antenne, et la reprise coupe vraiment le reliquat | `[ ]` |
| GOAL-052 | L'historique dit quel jour, et ne mélange plus deux 8 h | `[ ]` — signalé par l'auteur le 2026-09-02, capture à l'appui |

Le détail de chacun — tâches, décisions prises, dettes, incidents — est dans
[TASKS.archive.md](./TASKS.archive.md).

---

## GOAL-051 — Le direct ne ment plus à l'antenne, et la reprise coupe vraiment le reliquat

Quatre défauts constatés **à l'antenne** le 2026-09-02 au matin, puis retrouvés
un à un dans les journaux de production (`local-webradio` et
`local-webradio-liquidsoap` sur `frontal`). Ils naissent de la rencontre de
GOAL-015 (le direct) et de GOAL-041 (la reprise à neuf) : chacun tient seul,
ensemble ils mentent.

```
23:47:22  le conteneur « radio » redémarre seul ; liquidsoap reste debout,
          figé au milieu d'un morceau depuis 19:11
07:49:45  premier auditeur — « pause de 8:02:23 : la radio repart à neuf »
07:49:46  « avance jetée sur ordre de l'API »  … et AUCUN « saut demandé »   ← 1
07:49:50  /next → live:…franceinfo  « direct demandé pour 609 s »
07:49:53  /next → le bouche-trou, tiré à 7 h 49 dans un créneau sans plage    ← 3
07:49:53.371  /playing  ← reconnu : « Matinale franceinfo » s'affiche
07:49:53.374  /playing  ← MÊME entrée, déjà consommée : « None — None »       ← 2
07:51:13  le bouche-trou est annoncé et démarre (préchargement du crossfade)
07:51:15  « Switch to live » — le direct prend l'antenne, rien ne le redit     ← 2
08:00:00  « le direct se termine » → le bouche-trou GELÉ reprend, 2 min hors
          de la plage « Chanson française »                                    ← 4
08:03:05  premier morceau réellement tiré à 8 h
```

- [x] **GOAL-051-T01** — Relever dans `docs/liquidsoap.md` §9, contre
      `savonet/liquidsoap:v2.3.3` en Docker : combien de fois `input.http`
      déclenche `on_track` à son démarrage ; ce que fait `skip()` sur un
      `request.dynamic` sans piste en cours, et quel témoin le script peut lire
      pour le savoir ; si l'annonce du direct peut partir d'une **transition**
      du `switch` qui le met à l'antenne ; ce que devient la source `programme`
      pendant qu'un direct la recouvre, et l'effet d'un `set_queue([])` +
      `skip()` à la fin du direct.
      **Fait le 2026-09-02** — maquette fidèle (le vrai `radio.liq` contre une
      fausse API, le vrai flux franceinfo), `docs/liquidsoap.md` §9. Le double
      `on_track` est reproduit sur deux manches, le témoin du saut est validé à
      froid et à chaud, la transition du `switch` et la purge de fin de direct
      fonctionnent. **Le relevé a trouvé un cinquième défaut** : un
      `switch(track_sensitive=true)` derrière `crossfade` cesse d'évaluer ses
      prédicats — d'où T06.
- [x] **GOAL-051-T02** — Le témoin de « une piste passe » vit dans `radio.liq` :
      `on_skip` refuse un saut à vide, et la charnière ordonne toujours le
      `/skip` de la reprise à neuf. `radio` ne peut pas savoir ce que liquidsoap
      tient : redémarré seul, il croit qu'aucun morceau ne passe. **(défaut 1)**
- [x] **GOAL-051-T03** — Une entrée inconnue **et sans étiquettes** ne remplace
      plus ce qui est à l'antenne : déclarer « musique, sans titre ni artiste »
      efface l'affichage sans rien apporter. **(défaut 2, moitié Python)**
- [ ] **GOAL-051-T04** — Le direct s'annonce quand il **prend** l'antenne, une
      seule fois par case, et non dès `live.start()` — un morceau d'avance plus
      tôt. **(défaut 2, moitié `.liq`)** — à écouter : la jonction musique → direct.
      **Dépend de T06** : sans prédicat réévalué, la transition ne s'exécute
      jamais.
- [x] **GOAL-051-T05** — À la fin du direct, l'avance rassie est jetée et le
      reliquat coupé : le premier morceau d'après est tiré à l'heure qu'il est,
      dans la plage qui est réellement ouverte. **(défauts 3 et 4)** — à
      écouter : la reprise à la coupure du direct.
- [ ] **GOAL-051-T06** — Le direct prend l'antenne **à la première jonction**,
      et non au hasard. Constaté en maquette (T01) : derrière `crossfade`, un
      `switch(track_sensitive=true)` n'évalue plus ses prédicats — zéro
      évaluation sur quatre jonctions, le direct n'obtient jamais l'antenne. En
      production le 2026-09-02, une seule bascule, **85 s** après l'instruction.
      **(cinquième défaut, découvert par le relevé)**
      > **Arbitrage à demander (AGENTS.md §1.2, cas 2)** : la seule bascule
      > fiable observée est `track_sensitive=false`, qui coupe **au milieu du
      > morceau** — ce que SPECS.md §4.11 refuse. L'armer au `on_track` du
      > `request.dynamic` la fait tomber ~2 s avant la fin audible, en plein
      > fondu de sortie. Le compromis est audible : il ne se tranche pas seul.

**Décidé sans arbitrage** (AGENTS.md §1.2) : la purge de fin de direct est
ordonnée dans `radio.liq`, par un `ref` posé après la définition de `programme`
— `stop_live` est défini avant elle. Le script ne décide rien de plus : il
redemande à l'API. L'alternative — une route de plus, ou un réveil côté Python
à l'heure de fin — coûterait une surface publique pour un geste mécanique.


---

## GOAL-052 — L'historique dit quel jour, et ne mélange plus deux 8 h

Signalé par l'auteur le 2026-09-02, capture à l'appui : la page « 08 h » liste
`08:33 … 08:02` (aujourd'hui) **puis** `08:52 … 08:41` (la veille). L'ordre est
juste — `SELECT … ORDER BY joue_le DESC` (`adapters/state/database.py`) — mais
l'API n'expose que `%H:%M` (`app/main.py`, `lister_l_historique`) : privée de sa
date, la page groupe deux journées sous la même heure et l'ordre paraît faux.

- [ ] **GOAL-052-T01** — L'entrée du journal porte sa date, pas seulement son
      heure : `PlayedEntry` gagne le jour, l'API le rend, et le contrat de
      SPECS.md §4.8 le dit.
- [ ] **GOAL-052-T02** — La page sépare les journées : une heure d'aujourd'hui
      et la même heure d'hier ne se suivent plus sans le dire.
