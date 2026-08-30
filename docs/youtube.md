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

## 4. Constaté à la première diffusion réelle (2026-08-30, 22:50)

Le mécanisme a fonctionné jusqu'au diffuseur — la case ouverte, la vidéo
résolue, l'URL servie — et c'est **la résolution côté Liquidsoap** qui a
échoué, deux fois dans le même journal :

- `Response has unknown mime-type: "audio/webm"` — la table
  `settings.http.mime.extnames` ne connaît pas le webm, le fichier téléchargé
  n'a pas d'extension, la résolution échoue ;
- `Time limit exceeded (timeout: 29.00)` — la résolution **télécharge** le
  fichier (~30 Mo) avant de jouer, et 29 s ne suffisent pas toujours.

Correctifs, dans cet ordre de préférence : `yt-dlp -f "bestaudio[ext=m4a]/bestaudio"`
(le mime `audio/mp4` est connu), la table complétée quand même, et
`settings.request.timeout := 120.`. À noter aussi : **la trace « diffusé »
s'écrit quand le planificateur décide, pas quand le son démarre** — deux
essais ont été perdus ainsi ; c'est une faiblesse consignée, pas encore un
correctif.

## 5. Le blanc, et sa suppression (GOAL-028)

Servir l'URL googlevideo faisait télécharger le **diffuseur** à la jonction :
trente à soixante secondes sans rien, inacceptable à l'antenne (constaté par
l'auteur). Depuis GOAL-028 :

- `radio` télécharge la vidéo **en tâche de fond** (`yt-dlp -o`, écrite en
  `.part` puis renommée — jamais un fichier à moitié plein sous le nom final)
  pendant que la musique continue ;
- la case ne rend l'émission que lorsque **le fichier local est prêt** : la
  résolution est alors instantanée, l'émission part à la jonction suivante,
  sans blanc ;
- le cache (`<dossier de l'état>/cache`, partagé en lecture seule avec le
  diffuseur) nomme le fichier **d'un nom stable par émission**
  (`hardisk.m4a` + témoin `hardisk.id`) : le téléchargement suivant écrase,
  un fichier mal supprimé ne s'accumule jamais, et le témoin garantit qu'un
  reste d'une autre semaine n'est jamais diffusé à la place de la candidate ;
  **la vidéo lue s'efface dès que la suite commence** — le moment sûr ;
- un téléchargement qui finit après la fin de case a manqué son heure : la
  case borne tout, comme partout.
