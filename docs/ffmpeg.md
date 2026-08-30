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
