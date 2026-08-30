# docs/youtube.md — Relevé : une chaîne YouTube comme émission

> **Relevé établi le 2026-08-30** (`GOAL-025`), depuis cette machine, contre la
> chaîne d'exemple fournie par l'auteur (`@hardisk`). Règle applicable
> (AGENTS.md §3) : rien de ce qui suit n'est supposé.

**Outil constaté** : `yt-dlp 2026.08.19` (hôte). L'image `radio` doit
l'embarquer aussi : c'est elle qui résout.

## 1. Ce qui a été constaté

| Question | Constat |
|---|---|
| Trouver la chaîne depuis `https://www.youtube.com/@handle` | La page porte `<link rel="canonical" href=".../channel/UC…">` — le `channel_id` s'y lit. (Le JSON `"channelId"` de la page n'est **pas** fiable : absent au premier essai.) |
| Les dernières vidéos, sans clé d'API | `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` : un flux Atom de **15 entrées**, avec `yt:videoId`, `published`, `title`. **Pas de durée.** |
| La durée et l'audio d'une vidéo | `yt-dlp -g -f bestaudio --print duration --print urls` : `1742` puis une URL `googlevideo.com/videoplayback?…` |
| ffmpeg sait-il l'ouvrir ? | **Oui, exactement** : 3 s demandées → 529 200 octets de PCM (44100 × 2 × 2 × 3) |
| L'URL directe dure-t-elle ? | Elle porte `expire=` à ~6 h. **Résoudre au moment de diffuser**, jamais d'avance ni en cache long |

## 2. Ce que cela décide

Une émission YouTube est **un podcast dont le flux est le RSS de la chaîne** et
dont la « pièce jointe » se résout par `yt-dlp` au dernier moment :

- la **dernière vidéo non encore diffusée**, sinon la case est sautée —
  exactement SPECS.md §7 n°14 ;
- la case bornée par la **durée réelle** de la vidéo (n°13), lue par `yt-dlp`
  puisque le RSS ne la porte pas ;
- la trace en base par `videoId`, comme un `guid` de podcast.

## 3. Points incertains

- [ ] YouTube peut exiger une preuve d'humanité ou limiter `yt-dlp` sans
      préavis ; l'indisponibilité est un cas nominal — musique et journal —
      mais la **fréquence** de ces refus ne se connaîtra qu'à l'usage.
- [ ] Le niveau sonore d'une vidéo contre la musique : à l'oreille.
- [ ] Une vidéo « Short » ou un direct YouTube dans le RSS : le premier fera
      une émission d'une minute, le second n'a pas de fin — à observer, et
      peut-être filtrer un jour sur la durée.
- [ ] ffmpeg **de Liquidsoap** ouvrant `googlevideo` : constaté seulement avec
      le ffmpeg de l'hôte ; même famille, à confirmer à la première diffusion.
