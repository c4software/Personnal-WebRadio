# docs/ffmpeg.md — Relevé des options réellement acceptées

> **Ce relevé est vide de constats.** Il porte les questions auxquelles
> `GOAL-002` devra répondre **contre la version installée sur cette machine** —
> pas contre la documentation d'une version quelconque.
>
> Règle applicable (AGENTS.md §3). Ici elle est particulièrement concrète : les
> options de ffmpeg changent de version en version, et une option acceptée
> silencieusement mais ignorée produit un défaut **audible** que rien ne
> signalera.

Commencer par consigner la version : `ffmpeg -version`.

---

## 1. Enchaîner deux morceaux sans blanc

C'est **le point le plus important du relevé** : la jonction entre deux morceaux
est ce qui distingue une radio d'une liste de lecture (SPECS.md §4.2).

- [ ] Comment alimenter un encodage **continu** avec une suite de fichiers dont
      on ne connaît pas la liste à l'avance ? Le démultiplexeur `concat` exige un
      fichier de liste écrit d'avance — incompatible avec une file tirée à la
      demande (ARCHITECTURE.md §2).
- [ ] Faut-il un processus ffmpeg **par morceau**, alimentant un encodeur unique
      par son entrée standard ? Ou un processus unique piloté autrement ?
- [ ] Que se passe-t-il **exactement** en fin de fichier : ffmpeg s'arrête-t-il,
      attend-il, produit-il un silence ? La réponse décide de toute la mécanique
      de jonction.
- [ ] Un fondu entre deux morceaux est-il faisable dans ce montage, ou impose-t-il
      de tout mixer nous-mêmes ?

## 2. Insérer un jingle ou un flash

- [ ] Comment intercaler un fichier au milieu d'un encodage continu, sans couper
      ni redémarrer le flux servi aux auditeurs ?
- [ ] Les jingles MP3 fournis par l'auteur et les morceaux Navidrome peuvent
      avoir des fréquences d'échantillonnage et des nombres de canaux différents.
      Quel rééchantillonnage est nécessaire, et à quel coût ?
- [ ] Existe-t-il un filtre de normalisation du niveau utilisable **en temps
      réel** ? Un jingle qui écrase la musique est l'un des quatre angles morts
      (AGENTS.md §4.1).
- [ ] Le jingle de vote `encore.mp3` s'insère à la jonction, comme un jingle
      horaire (ARCHITECTURE.md §6.2) : **aucun mixage par-dessus la musique n'est
      requis**. Vérifier qu'il n'existe bien qu'un seul chemin d'insertion à
      écrire, et que deux jingles dus à la même jonction ne posent pas de
      problème particulier.

## 2.bis Transcoder le moins possible

SPECS.md §4.9 demande d'économiser la machine ; SPECS.md §4.9 demande aussi de ne
jamais couper. Ce relevé doit établir ce qui est **réellement possible**, pas ce
qui serait souhaitable.

- [ ] ffmpeg sait-il **copier** un flux audio sans le réencoder (`-c copy`) tout
      en l'insérant dans une sortie continue ? À quelles conditions sur le format
      d'entrée ?
- [ ] Que produit exactement une copie lorsque deux fichiers successifs n'ont pas
      le même débit, la même fréquence d'échantillonnage ou le même nombre de
      canaux ? Un flux valide, ou un flux que les lecteurs refusent
      (→ [docs/flux-icy.md](./flux-icy.md) §3) ?
- [ ] Quel est le **coût réel** d'un réencodage permanent sur cette machine —
      pourcentage d'un cœur pour un auditeur, pour cinq ? Le chiffre décide :
      « économiser les ressources » n'a de sens qu'en regard de ce qu'on
      économise.
- [ ] Un réencodage **partiel** est-il possible : copier tant que le format
      correspond, ne réencoder que les fichiers qui s'en écartent ? Que se
      passe-t-il à la bascule entre les deux régimes ?

Ce relevé nourrit directement la décision ouverte **SPECS.md §7 n°11**.

## 3. Le flux de sortie

- [ ] Quel format et quel débit pour un flux HTTP lu indifféremment par VLC, un
      navigateur et une enceinte connectée ?
- [ ] Quels en-têtes ffmpeg produit-il en tête de flux, et un auditeur qui se
      branche **en cours** peut-il les manquer ? C'est exactement le cas nominal
      de SPECS.md §4.1 : il faut savoir ce qu'un auditeur tardif reçoit.
- [ ] Comment forcer un débit régulier, pour que l'encodage suive le temps réel
      plutôt que d'aller aussi vite qu'il peut ?

## 4. Le cycle de vie du processus

ARCHITECTURE.md §4 le signale comme le point à surveiller : **un ffmpeg orphelin
qui survit à la dernière déconnexion annule tout le bénéfice du démarrage à la
demande.**

- [ ] Comment l'arrêter proprement, et en combien de temps s'arrête-t-il ?
- [ ] Que fait-il si sa sortie n'est plus lue — le dernier auditeur vient de se
      débrancher ? Bloque-t-il, meurt-il, remplit-il un tampon ?
- [ ] Que renvoie-t-il comme code de sortie dans chacun de ces cas ?
- [ ] Sa sortie d'erreur doit-elle être lue en continu pour éviter qu'il ne se
      bloque sur un tuyau plein ?

---

## 5. Points incertains

_Tout ce qui précède._

Un point resté incertain **après** observation est reporté ici avec ce qui a été
tenté, et ouvre une tâche dans TASKS.md.
