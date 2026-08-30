# docs/franceinfo.md — Relevé du flash d'information

> **Ce relevé est vide de constats**, et il commence par une inconnue plus grande
> que les autres : **aucune adresse n'a été fournie à l'initialisation**.
> L'auteur a indiqué que France Info « donne le flash accessible », sans préciser
> par quel moyen.
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'une
> dépendance externe.**

---

## 1. Trouver la source — préalable à tout le reste

- [ ] Par quel moyen le flash est-il réellement accessible ? Un flux RSS de
      podcast, un fichier à URL stable, une API, autre chose ?
- [ ] Cette adresse est-elle **publique et stable**, ou dépend-elle d'une clé,
      d'une session, d'un identifiant de lecteur ?
- [ ] Quelles sont les **conditions d'utilisation** ? Le projet est privé et non
      exposé (SPECS.md §3), ce qui simplifie la question sans l'effacer.

> Tant que ce point n'est pas établi, `GOAL-006` ne peut pas être découpé.
> Si aucune source fiable n'existe, c'est une **ambiguïté de spécification**
> (AGENTS.md §1.2) : la question remonte à l'auteur, elle ne se contourne pas.

## 2. Le contenu

- [ ] Quelle **durée** fait un flash, et cette durée est-elle stable ? Elle
      détermine la fenêtre qu'il faut réserver dans la programmation.
- [ ] À quelle **fréquence** est-il mis à jour ? Toutes les heures, aux
      demi-heures, irrégulièrement ?
- [ ] Comment savoir qu'un flash est **récent** plutôt que celui d'il y a trois
      heures ? Un flash périmé diffusé comme neuf est pire qu'un flash absent.
- [ ] Quel format et quel débit ? Faut-il un réencodage pour rejoindre le format
      du flux (ARCHITECTURE.md §4) ?
- [ ] Le niveau sonore est-il comparable à celui de la musique ? Un flash deux
      fois trop fort est l'un des quatre angles morts (AGENTS.md §4.1) — et ne se
      constatera qu'à l'oreille.

## 3. Quand ça se passe mal

SPECS.md §4.5 pose le principe : **l'indisponibilité est un cas nominal, pas une
panne.** Reste à établir ce qu'on observe réellement.

- [ ] Que se passe-t-il si la source ne répond pas ? Erreur franche, ou attente
      longue ? La radio ne peut pas se permettre d'attendre : un délai maximal
      devra être fixé et déclaré dans le TOML.
- [ ] Un fichier **tronqué** est-il détectable avant diffusion ? La radio ne doit
      jamais diffuser un flash incomplet.
- [ ] La source peut-elle renvoyer une page HTML d'erreur avec un code 200 ?

---

## 4. Points incertains

_Tout ce qui précède — à commencer par l'adresse elle-même, qui n'a jamais été
fournie._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
