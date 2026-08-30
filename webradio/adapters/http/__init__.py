"""Le flux servi aux auditeurs : tout ce qui connaît HTTP.

Rien au-dessus de ce dossier ne connaît de code de réponse, d'en-tête ni de
socket (ARCHITECTURE.md §2.1).

Deux responsabilités, volontairement séparées :

- `diffusion` — un flux, N connexions, chacune servie sans retenir les autres
  (ARCHITECTURE.md §4.1) ;
- `serveur` — le cycle de vie : la chaîne naît à la première connexion et meurt
  à la dernière (SPECS.md §1, §4.7).
"""
