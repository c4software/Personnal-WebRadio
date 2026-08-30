#!/usr/bin/env bash
# La commande de vérification unique d'AGENTS.md §5.2, plus les contrôles
# textuels des interdits d'AGENTS.md §2 que ruff ne sait pas exprimer.
#
# Elle échoue bruyamment : le premier contrôle en échec arrête tout.
set -euo pipefail

VENV="${VENV:-.venv/bin}"

echo "── mise en forme ─────────────────────────────────────────"
"$VENV/ruff" format --check .

echo "── analyse statique ──────────────────────────────────────"
"$VENV/ruff" check .

echo "── types ─────────────────────────────────────────────────"
"$VENV/mypy"

echo "── interdits d'AGENTS.md §2 ──────────────────────────────"
echec=0
signaler() { echo "  ✗ $1"; echec=1; }

# Le noyau ne parle à personne (ARCHITECTURE.md §1.1)
if grep -rnE '^\s*(import|from)\s+(httpx|requests|aiohttp|subprocess|socket|asyncio)\b' webradio/core/ 2>/dev/null; then
  signaler "le noyau importe une bibliothèque d'entrée-sortie"
fi

# Une seule horloge (ARCHITECTURE.md §3.1)
if grep -rnE '(datetime\.(now|today|utcnow)|time\.(time|monotonic))\s*\(' webradio/ \
   --include='*.py' 2>/dev/null | grep -v 'webradio/core/clock.py'; then
  signaler "accès à l'horloge hors de core/clock.py"
fi

# Un seul hasard (ARCHITECTURE.md §3.1)
if grep -rnE '^\s*(import|from)\s+(random|secrets)\b' webradio/ \
   --include='*.py' 2>/dev/null | grep -v 'webradio/core/rng.py'; then
  signaler "accès au hasard hors de core/rng.py"
fi

# L'interface web n'a aucun chemin privilégié (ARCHITECTURE.md §6)
if grep -rnE '^\s*(import|from)\s+(flask|jinja2)\b' webradio/ \
   --include='*.py' 2>/dev/null | grep -v 'webradio/adapters/web/'; then
  signaler "flask ou jinja2 importé hors de adapters/web/"
fi

# Aucun TODO sans tâche dans TASKS.md
while IFS= read -r ligne; do
  [ -z "$ligne" ] && continue
  echo "$ligne"
  signaler "TODO/FIXME sans tâche correspondante dans TASKS.md"
done < <(grep -rnE '\b(TODO|FIXME)\b' webradio/ tests/ --include='*.py' 2>/dev/null || true)

[ "$echec" -eq 0 ] && echo "  ✓ aucun interdit enfreint"
[ "$echec" -eq 0 ] || exit 1

echo "── tests et couverture ───────────────────────────────────"
"$VENV/pytest" --cov --cov-fail-under=80
