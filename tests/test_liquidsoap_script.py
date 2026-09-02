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
    r"\b(?:subsonic|navidrome)\b": "la source de musique — seul adapters/sources/ la connaît",
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


def test_un_direct_est_une_instruction_de_l_api_pas_du_script() -> None:
    """GOAL-015 : le script capte ce qu'on lui dit, jusqu'à l'heure qu'on lui dit."""
    code = _code()
    assert 'prefix="live:"' in code
    assert "input.http(" in code
    assert "self_sync=false" in code, "sans lui la rafale initiale avale le morceau en cours"
    assert "track_sensitive=true" in code, "un direct prend la main à la jonction, jamais au milieu"


def test_le_saut_est_une_route_que_l_api_ordonne() -> None:
    """GOAL-017 : le script saute sur ordre, il ne décide jamais de sauter."""
    code = _code()
    assert '"/skip"' in code
    assert "programme.skip()" in code


def test_le_script_refuse_un_saut_a_vide() -> None:
    """GOAL-051 : un saut sans piste en cours mange l'entrée fraîche (7 ms
    constatées, docs/liquidsoap.md §9). Seul le script sait si une piste
    passe : `radio` redémarré seul l'a oublié."""
    code = _code()
    assert "piste_commencee = ref(false)" in code
    assert "piste_commencee := true" in code
    assert re.search(r"if piste_commencee\(\) then", code)


def test_l_avance_se_jette_sur_ordre_de_l_api() -> None:
    """GOAL-034 : un encore accepté vide le morceau d'avance."""
    code = _code()
    assert '"/requeue"' in code
    assert "set_queue([])" in code


def test_la_prise_d_antenne_se_fond() -> None:
    """GOAL-050 : le premier auditeur ne prend pas le son en pleine face.
    `fade.in` ne fond pas une source entamée — c'est la transition qui arme un
    `amplify` (docs/liquidsoap.md §8)."""
    code = _code()
    assert "transitions=[prise_antenne" in code
    assert re.search(r"amplify\(gain_antenne", code)


def test_le_branchement_s_annonce_avant_de_rendre_l_antenne() -> None:
    """GOAL-041 : tant que le compteur est à zéro, l'antenne reste muette —
    c'est ce qui laisse l'API purger une avance rassise sans course
    (docs/liquidsoap.md §5.bis)."""
    code = _code()
    connect = code[code.index("def on_connect") : code.index("def on_disconnect")]
    annonce = connect.index("announce_count(listeners() + 1)")
    bascule = connect.index("listeners := listeners() + 1")
    assert annonce < bascule, "la bascule avant l'annonce rendrait l'antenne avant la purge"
