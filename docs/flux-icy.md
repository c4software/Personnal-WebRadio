# docs/flux-icy.md — Relevé de ce qu'attendent les lecteurs de webradio

> **Ce relevé est vide de constats.** Il porte les questions auxquelles
> `GOAL-002` devra répondre **en branchant de vrais lecteurs**, pas en lisant une
> spécification.
>
> Règle applicable (AGENTS.md §3). Elle est ici particulièrement mal outillée :
> il n'existe **aucune norme** du « flux de webradio ». Ce que les lecteurs
> acceptent est une convention de fait, héritée de Shoutcast et d'Icecast, et
> chacun l'interprète à sa façon. **Rien ne se déduit ; tout se constate.**

SPECS.md §4.9 exige un flux lisible par n'importe quel lecteur, sans coupure. Ce
relevé établit ce que « n'importe quel lecteur » veut réellement dire.

---

## 1. Le branchement

- [ ] Quels en-têtes de réponse un lecteur attend-il ? `Content-Type`,
      `icy-name`, `icy-br`, `icy-genre` — lesquels sont **exigés**, lesquels sont
      décoratifs ?
- [ ] Que se passe-t-il si la réponse ne porte pas de `Content-Length` — cas
      obligatoire ici, puisque le flux est infini ? Certains lecteurs
      s'attendent-ils à un `Transfer-Encoding` particulier ?
- [ ] Un lecteur envoie-t-il `Icy-MetaData: 1` ? Que se passe-t-il si on
      l'ignore ? Et si on répond `icy-metaint` sans jamais envoyer de
      métadonnées ?
- [ ] **Combien de données un lecteur veut-il avant de commencer à jouer ?** Cela
      détermine le délai d'amorçage perçu (SPECS.md §4.1).

## 2. Entrer en cours de route

C'est le cas nominal de cette radio : on se branche au milieu d'un morceau
(SPECS.md §4.1).

- [ ] Un lecteur qui arrive après le début du flux reçoit-il assez d'information
      pour décoder, ou lui faut-il un en-tête que seul le début portait ?
- [ ] Si le format impose un en-tête initial, comment le servir à chaque nouvelle
      connexion sans réencoder pour autant ?

## 3. Ce qui fait décrocher

**La question centrale de ce relevé**, celle dont dépend la décision ouverte
SPECS.md §7 n°11.

- [ ] Que fait chaque lecteur si le **débit** change en cours de flux ?
- [ ] Si la **fréquence d'échantillonnage** change ?
- [ ] Si le **nombre de canaux** change — mono après stéréo ?
- [ ] Si le **codec** change ?
- [ ] Combien de temps un lecteur tolère-t-il une interruption de données avant
      de considérer la connexion perdue ?

Réponses à établir lecteur par lecteur : **VLC**, un **navigateur** (au moins
Firefox et Chromium), une **enceinte connectée**, une **application de radios**
sur téléphone. Ils ne réagissent pas de la même façon, et c'est le plus
intolérant qui fixe la contrainte.

## 4. Les métadonnées

- [ ] Faut-il annoncer le titre en cours, et par quel mécanisme ? Est-ce attendu,
      ou seulement agréable ?
- [ ] Un changement de métadonnée peut-il, à lui seul, provoquer une coupure chez
      certains lecteurs ?
- [ ] Que faut-il annoncer pendant un jingle ou un flash, où il n'y a ni titre ni
      artiste ?

## 5. Plusieurs auditeurs

- [ ] Un auditeur lent ralentit-il les autres si le flux est écrit dans une seule
      boucle ? Où doit se situer le tampon pour que non ?
- [ ] Comment détecter une déconnexion **brutale** — câble arraché, lecteur tué —
      plutôt que d'attendre un délai d'expiration ? SPECS.md §4.7 en dépend :
      sans cela, la chaîne tourne pour un auditeur qui n'existe plus.

---

## 6. Points incertains

_Tout ce qui précède._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
