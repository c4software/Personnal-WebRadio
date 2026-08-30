# docs/podcast.md — Relevé des flux de podcast

> **Relevé non commencé — bloqué** (`GOAL-002-T09`). Aucune URL de podcast n'a
> été fournie. Il ne porte pas sur « les podcasts en général » mais sur ceux que
> la radio diffusera.
> `GOAL-002` devra répondre **contre les flux réellement déclarés** par l'auteur.
>
> Règle applicable (AGENTS.md §3). Elle mord ici : « RSS avec des `<enclosure>` »
> décrit une convention, pas une norme respectée. Chaque éditeur s'en écarte à sa
> façon, et un flux qui marche ne dit rien du suivant.

Il recoupe [docs/franceinfo.md](./franceinfo.md) : si le flash France Info se
révèle être lui-même un podcast, les deux partagent la même mécanique — et il
faudra le constater, pas l'espérer.

---

## 1. Lire le flux

- [ ] Quel format exact : RSS 2.0 avec extensions iTunes, Atom, autre ? Les flux
      déclarés par l'auteur sont-ils homogènes entre eux ?
- [ ] Où se trouve l'URL du fichier audio : `<enclosure url>`, un lien
      `<media:content>`, ailleurs ?
- [ ] La **date de publication** est-elle toujours présente et fiable ? C'est ce
      dont dépend « le plus récent » (SPECS.md §7 n°14).
- [ ] La **durée** est-elle annoncée, et exacte ? La programmation en dépend :
      une émission qui dure le double de ce qu'elle annonce déborde sur la suite.
- [ ] Combien d'épisodes un flux expose-t-il, et faut-il paginer ?

## 2. Récupérer l'audio

- [ ] Quel format sortent réellement les fichiers, et à quel débit ? Il faudra
      les ramener au format du flux (ARCHITECTURE.md §4.0).
- [ ] Y a-t-il des **redirections** — services de mesure d'audience placés devant
      le fichier ? Combien de sauts, et vers quel domaine final ?
- [ ] Le fichier est-il servi d'un coup, ou faut-il le télécharger avant de
      pouvoir le diffuser ? Une émission d'une heure ne se met pas en mémoire à
      la légère.
- [ ] Le **niveau sonore** est-il comparable à celui de la musique ? Une émission
      deux fois trop forte est un angle mort (AGENTS.md §4.1).

## 3. Quand ça se passe mal

SPECS.md §4.11 pose le principe : un épisode indisponible ou tronqué **n'est pas
une panne**, la radio reste sur la musique. Reste à savoir ce qu'on observe.

- [ ] Que se passe-t-il si le flux ne répond pas ? Erreur franche ou attente
      longue ? Un délai maximal devra être fixé et déclaré au TOML.
- [ ] Un fichier **tronqué** est-il détectable avant diffusion ? La radio ne doit
      jamais diffuser une émission incomplète.
- [ ] Le flux peut-il renvoyer une page HTML d'erreur avec un code 200 ?
- [ ] Un épisode annoncé dans le flux mais dont le fichier a disparu : cas
      fréquent ou marginal ?

## 4. Deux constats dont dépendent des décisions déjà prises

Ces deux points ne sont pas de la curiosité : **deux décisions tranchées reposent
dessus**, et si le relevé les contredit, elles devront être rejouées.

- [ ] **La date de publication est-elle toujours présente et fiable ?**
      SPECS.md §7 n°14 a tranché « l'épisode le plus récent ». Sans date fiable,
      ce choix n'est pas implémentable.
- [ ] **La durée annoncée est-elle exacte ?**
      SPECS.md §7 n°13 borne le rattrapage d'une émission manquée à sa propre
      durée. Une durée fausse fait rattraper trop longtemps, ou pas assez.
      Vérifier aussi qu'elle est lisible **sans télécharger le fichier** — c'est
      ce qui rend la décision de rattraper possible au branchement.

---

## 5. Points incertains

_Tout ce qui précède._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
