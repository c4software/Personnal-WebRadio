# docs/franceinfo.md — Relevé du flash d'information

> **Ce relevé est vide de constats**, et il commence par une inconnue plus grande
> que les autres : **aucune adresse n'a été fournie**. L'auteur a indiqué que
> France Info « donne le flash accessible », sans préciser par quel moyen.
>
> **Décidé le 2026-08-30** : c'est `GOAL-002` qui cherche. Point de départ — les
> flux publics de Radio France : podcast, RSS, fichier à URL stable. On constate
> ce qui répond réellement, on documente. **Si rien de fiable n'existe, la
> question remonte à l'auteur** plutôt que de bricoler autour d'une source
> instable (AGENTS.md §1.2).
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'une
> dépendance externe.**

---

## 1. Trouver la source — **relevé : aucune source confirmée**

> **Constaté le 2026-08-30** (`GOAL-002-T07`). Recherche menée depuis le web,
> sans URL fournie par l'auteur.

**Aucun flux de flash horaire n'a pu être confirmé.** Voici ce qui a été établi,
et pourquoi cela ne suffit pas.

### 1.1 Radio France a retiré la découvrabilité de ses flux RSS

En **mars 2026**, Radio France a supprimé les liens RSS visibles des pages
d'émission. Les flux historiques de `radiofrance-podcast.net` répondaient encore
en **avril 2026** — mais ils ne sont plus annoncés nulle part, ce qui est le
statut le plus fragile qui soit : ils fonctionnent sans être promis.

### 1.2 Les flux officiels sont volontairement courts

Quand ils existent, les flux RSS de Radio France **se limitent aux cinq derniers
épisodes** plus ceux du mois précédent.

> **Ce n'est pas un problème pour nous, et c'est un point positif du relevé.**
> SPECS.md §7 n°14 a tranché « l'épisode le plus récent » : cinq épisodes
> suffisent largement. Une décision prise pour d'autres raisons se trouve être
> celle qui résiste à cette contrainte.

### 1.3 Trois voies, aucune sans risque

| Voie | Ce qu'elle vaut |
|---|---|
| Un flux `radiofrance-podcast.net` direct | Fonctionne, mais n'est plus documenté ni annoncé. Peut disparaître sans préavis, et rien ne préviendra |
| `rss-rf.aerion.me` (tiers, source ouverte, MIT) | Utilise les **mêmes API que l'application Radio France**. Actif. Mais c'est un service tiers : sa disponibilité ne dépend ni de nous ni de Radio France |
| Auto-héberger ce pont | Supprime la dépendance au tiers, ajoute un service à faire tourner — et déplace le problème plutôt que de le résoudre |

### 1.4 Ce qui reste réellement inconnu

Ce relevé n'a **pas** établi le plus important :

- [ ] **Aucune URL de flux de flash horaire n'a été confirmée.** Les émissions
      trouvées (« franceinfo en 3 minutes », « 8h30 franceinfo », « Les
      informés ») sont des **émissions**, pas des flashs. Elles relèveraient de
      `GOAL-010`, pas de `GOAL-006`.
- [ ] Un flash d'information — le bulletin bref diffusé à l'heure ronde — est-il
      seulement publié en podcast, ou n'existe-t-il qu'au fil de l'antenne ?
- [ ] Si seul le direct le porte, la question change de nature : il faudrait
      capter un flux continu et en extraire un segment, ce qui n'a rien à voir
      avec lire un podcast.

### 1.5 Conclusion : la question remonte à l'auteur

C'est la conduite qu'`AGENTS.md §1.2` prescrit, et que
[TASKS.md](../TASKS.md) avait inscrite : *si rien de fiable n'existe, remonter
plutôt que bricoler autour d'une source instable.*

**Trois questions, dans l'ordre :**

1. **Avez-vous une URL précise en tête ?** L'intention initiale disait
   « normalement il donne le flash accessible ». Si vous savez où, tout ce qui
   précède devient sans objet.
2. **Sinon, acceptez-vous une dépendance à un service tiers** (`rss-rf.aerion.me`)
   ou à un flux non documenté, en sachant qu'il peut disparaître sans préavis —
   auquel cas la radio se replie sur la musique et le journalise (SPECS.md §4.5) ?
3. **Ou bien : « franceinfo en 3 minutes » vous suffirait-il ?** C'est une
   émission courte et régulière. Elle ne serait plus un *flash* au sens de
   SPECS.md §4.5 mais une *émission* au sens de §4.11 — et le projet sait déjà
   faire, sans code supplémentaire.

> **La troisième piste est la plus intéressante.** Elle ferait disparaître
> `GOAL-006`'s dépendance externe entière : les flashs cesseraient d'être un
> mécanisme à part pour devenir un cas particulier des émissions.

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
