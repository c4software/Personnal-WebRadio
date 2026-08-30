"""Le script Liquidsoap ne décide de rien (ARCHITECTURE.md §4, GOAL-016-T04).

Un test qui lit un fichier texte, parce que c'est le seul moyen de tenir la
règle : une `playlist()` ou un `random` glissé dans le script serait le noyau
contourné, et aucun test Python ne le verrait.
"""

import re
from pathlib import Path

import pytest

SCRIPT = Path("webradio/adapters/liquidsoap/radio.liq")

DECISIONS_INTERDITES = {
    r"\bplaylist\(": "une liste de lecture — c'est le noyau qui choisit",
    r"\brandom\b": "du hasard — il n'y en a qu'un, core/rng.py",
    r"\bsingle\(": "un fichier fixe — un jingle ne s'insère pas ici",
    r"\bfallback\(": "un repli local — la panne se dit, elle ne se cache pas",
    r"\.mp3\b": "un chemin de fichier — l'API rend les chemins",
    r"\bnavidrome\b": "Navidrome — seul adapters/sources/ le connaît",
    r"\btime\.": "l'horloge — il n'y en a qu'une, core/clock.py",
    r"\{\s*\d+h": "un prédicat horaire — la grille est dans le noyau",
}


def _code() -> str:
    return "\n".join(
        ligne for ligne in SCRIPT.read_text().splitlines() if not ligne.lstrip().startswith("#")
    )


@pytest.mark.parametrize(("motif", "pourquoi"), DECISIONS_INTERDITES.items())
def test_le_script_ne_prend_aucune_decision(motif: str, pourquoi: str) -> None:
    assert re.search(motif, _code()) is None, f"le script contient {pourquoi}"


def test_le_script_demande_et_annonce_par_l_api() -> None:
    code = _code()
    assert "/playout/next" in code
    assert "/playout/listeners" in code


def test_le_script_s_arrete_au_lieu_de_boucler() -> None:
    """Liquidsoap réessaie sans fin par défaut (docs/liquidsoap.md §3)."""
    assert "shutdown()" in _code()
    assert "status_code == 204" in _code()


def test_rien_ne_joue_sans_auditeur() -> None:
    assert re.search(r"listeners\(\)\s*>\s*0", _code())
    assert "blank()" in _code()
