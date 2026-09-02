"""Le script Liquidsoap ne décide de rien (ARCHITECTURE.md §4, GOAL-016-T04).

Un test qui lit un fichier texte, parce que c'est le seul moyen de tenir la
règle : une `playlist()` ou un `random` glissé dans le script serait le noyau
contourné, et aucun test Python ne le verrait.
"""

import re
from pathlib import Path

import pytest

SCRIPT = Path("webradio/adapters/liquidsoap/radio.liq")
DOCKERFILE = Path("Dockerfile.liquidsoap")
COMPOSE = Path("docker-compose.yml")
VERIFIER = Path("verifier.sh")

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


def test_un_direct_prend_l_antenne_a_une_jonction() -> None:
    """GOAL-051 : `track_sensitive=true` ne suffit pas — derrière `crossfade`,
    le `switch` ne reçoit aucune fin de piste et cesse d'évaluer ses prédicats
    (docs/liquidsoap.md §9). C'est un témoin armé au début d'une piste qui
    tient la règle de SPECS.md §4.11."""
    code = _code()
    assert "direct_arme = ref(false)" in code
    assert "direct_arme := live_pending()" in code
    assert re.search(r"direct_arme\(\).*live\.is_ready\(\).*live", code, re.DOTALL)


def test_un_direct_s_annonce_quand_il_prend_l_antenne() -> None:
    """GOAL-051 : `live.on_track` s'annonçait deux fois, et une piste trop tôt
    (docs/liquidsoap.md §9). Seule la transition du `switch` dit l'instant où
    le direct est réellement à l'antenne."""
    code = _code()
    assert "live.on_track" not in code
    prise = re.search(r"def prise_direct.*?\nend\n", code, re.DOTALL)
    assert prise is not None
    assert "annoncer_le_direct()" in prise.group()
    assert "transitions=[prise_direct, rendu_direct]" in code


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


def test_la_fin_d_un_direct_jette_l_avance_rassie() -> None:
    """GOAL-051 : l'avance a dormi sous le direct — elle a été tirée à
    l'ouverture de la case, pas à sa fermeture. Le 2026-09-02, deux minutes de
    musique hors plage à 8 h (docs/liquidsoap.md §9)."""
    code = _code()
    fin_du_direct = re.search(r"def stop_live.*?\nend\n", code, re.DOTALL)
    assert fin_du_direct is not None
    assert "purger()" in fin_du_direct.group()
    assert "programme.set_queue([])" in code.split("vider_l_avance :=", 1)[1]


def test_un_saut_a_antenne_vide_ne_laisse_aucun_reliquat_au_premier_auditeur() -> None:
    """GOAL-055 : `cross` tient deux secondes déjà lues du morceau coupé, et un
    saut ordonné sans auditeur ne s'exécute qu'au premier tirage — quand le
    premier auditeur écoute déjà. Le 2026-09-02 à 13 h 20, un micro-flash du
    morceau de 11 h 03 (docs/liquidsoap.md §10). La transition jette ce
    reliquat ; le reste est l'appel même de `crossfade`."""
    code = _code()
    assert "reliquat_a_taire = ref(false)" in code
    saut = re.search(r"def sauter\(\).*?\nend\n", code, re.DOTALL)
    assert saut is not None
    assert "if listeners() == 0 then reliquat_a_taire := true end" in saut.group()
    assert "programme.skip()" in saut.group()
    appels = re.findall(r"(?<!def )sauter\(\)", code)
    assert len(appels) == 2, "le saut de l'API et celui de fin de direct passent par là"
    transition = re.search(r"def enchainer\(a, b\).*?\nend\n", code, re.DOTALL)
    assert transition is not None
    assert re.search(
        r"if reliquat_a_taire\(\) then.*?b\.source.*?else.*?cross\.simple\(",
        transition.group(),
        re.DOTALL,
    )
    assert "cross(duration=2., enchainer, programme)" in code
    assert "crossfade(" not in code, "crossfade ne laisse pas choisir sa transition"


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


# ── Le script voyage dans l'image (GOAL-053) ────────────────────────────────


def test_le_script_voyage_dans_l_image_du_diffuseur() -> None:
    """Monté depuis l'hôte, il n'avait pas de version : il a dérivé de six
    commits en silence, et le déploiement du 2026-09-02 a mis à jour `radio`
    en laissant le diffuseur à la veille."""
    assert f"COPY {SCRIPT} /etc/local-webradio/radio.liq" in DOCKERFILE.read_text()
    assert str(SCRIPT) not in COMPOSE.read_text(), "le script ne se monte plus, il est dans l'image"


def test_l_epingle_de_liquidsoap_ne_diverge_pas() -> None:
    """Deux fichiers nomment la version : l'image du diffuseur, et la
    vérification qui valide la syntaxe contre elle (docs/liquidsoap.md §1.7).
    Elles doivent dire la même chose, ou l'on validerait contre une version
    qu'on ne déploie pas."""
    depuis = re.search(r"^FROM (savonet/liquidsoap:\S+)", DOCKERFILE.read_text(), re.M)
    validee = re.search(r"LIQUIDSOAP_IMAGE:-(savonet/liquidsoap:\S+?)\}", VERIFIER.read_text())
    assert depuis is not None and validee is not None
    assert depuis.group(1) == validee.group(1)
