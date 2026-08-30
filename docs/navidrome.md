# docs/navidrome.md — Relevé de l'API Subsonic telle que Navidrome l'implémente

> **Ce relevé est vide de constats.** Il porte les **questions** auxquelles
> `GOAL-002` devra répondre **par observation**, contre un vrai serveur.
>
> Règle applicable (AGENTS.md §3) : **ne jamais inventer le comportement d'un
> endpoint**, et ne jamais l'inférer d'une implémentation existante de ce dépôt.
> La spécification Subsonic établit l'usage ; **ce que Navidrome renvoie
> réellement fait foi**.

Références de départ :

- API Subsonic : <https://www.subsonic.org/pages/api.jsp>
- Navidrome : <https://www.navidrome.org/docs/developers/subsonic-api/>

---

## 1. Authentification

- [ ] Quelle forme d'authentification Navidrome accepte-t-il réellement ?
      `p=` en clair, `p=enc:…`, ou le couple `t=` / `s=` (jeton dérivé + sel) ?
- [ ] Les paramètres `v` (version) et `c` (client) sont-ils obligatoires ? Quelle
      valeur de `v` cette instance accepte-t-elle au minimum ?
- [ ] Que renvoie une authentification refusée : un code HTTP, ou un HTTP 200
      portant une erreur dans le corps ? **C'est le piège classique de cette
      API**, et il change la forme du client.

## 2. Trouver de la musique

- [ ] Existe-t-il un tirage aléatoire côté serveur (`getRandomSongs`) ? Accepte-t-il
      un filtre par genre ? Par année ?
- [ ] Quelle est la **taille maximale** d'un lot ? Que se passe-t-il au-delà —
      erreur, ou troncature silencieuse ?
- [ ] Le tirage aléatoire du serveur est-il satisfaisant, ou faut-il récupérer la
      bibliothèque et tirer **de notre côté** ? La réponse détermine si
      `core/rng.py` tire parmi des identifiants connus ou délègue.
      → Elle conditionne aussi la règle de non-répétition (SPECS.md §7 n°3) :
      on ne peut pas garantir « pas deux fois le même artiste » si c'est le
      serveur qui tire.
- [ ] Comment lister les genres disponibles, et sous quelle forme exacte ? Un
      morceau peut-il porter plusieurs genres ?
- [ ] Comment retrouver les autres morceaux **d'un même artiste** ? C'est ce dont
      dépend `encore` (SPECS.md §4.6).

## 3. Récupérer le son

- [ ] `stream` contre `download` : lequel donne le fichier **sans transcodage**
      côté serveur ? Un double transcodage (Navidrome puis ffmpeg) dégrade le son
      pour rien.
- [ ] Peut-on désactiver le transcodage serveur par paramètre, ou dépend-il d'une
      configuration Navidrome hors de notre portée ?
- [ ] Quels formats sortent réellement, et avec quel `Content-Type` ?
- [ ] Le flux est-il servi en une fois, ou par morceaux ? Supporte-t-il les
      requêtes partielles ?

## 4. Les métadonnées dont la radio a besoin

- [ ] Artiste, titre, genre, durée : lesquels sont **toujours** présents, et
      lesquels peuvent manquer ? Une durée absente casserait la planification des
      jingles.
- [ ] Les identifiants de morceau sont-ils stables entre deux analyses de la
      bibliothèque ?

## 5. Quand ça se passe mal

- [ ] Que renvoie Navidrome pour un identifiant inexistant ?
- [ ] Que renvoie-t-il pendant une analyse de bibliothèque en cours ?
- [ ] Renvoie-t-il jamais du **HTML** là où du JSON était promis — page d'erreur
      d'un proxy, par exemple ? C'est un cas de test obligatoire (AGENTS.md §4).
- [ ] Y a-t-il une limite de débit, et sous quelle forme se manifeste-t-elle ?

---

## 6. Points incertains

_Tout ce qui précède, tant que `GOAL-002` n'a pas eu lieu._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md. Il n'est jamais remplacé par une
supposition.
