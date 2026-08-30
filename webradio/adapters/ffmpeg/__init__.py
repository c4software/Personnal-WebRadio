"""L'encodage : tout ce qui connaît la ligne de commande de ffmpeg.

Rien au-dessus de ce dossier ne connaît d'option, de code de sortie ni de nom de
codec (ARCHITECTURE.md §2.1). Ce que le reste du programme manipule, c'est un
`FormatFlux` et une `Chaine` qui produit des octets.

Deux constats de `docs/ffmpeg.md` commandent tout ce qui est écrit ici, et il ne
faut pas les rediscuter en lisant le code :

- **on réencode systématiquement** (§2.bis) — un flux permanent coûte 1 % d'un
  cœur, et un chemin de copie aurait apporté deux régimes et une bascule pour
  ce prix-là ;
- **un décodeur par entrée, un seul encodeur** (§2.1) — c'est ce qui supprime le
  blanc aux jonctions, y compris entre deux formats différents, et c'est le seul
  chemin d'insertion : un jingle est une entrée de plus (§2.ter).
"""
