"""Le script Liquidsoap ne prend aucune décision (ARCHITECTURE.md §4, GOAL-016-T04).

Ces tests lisent le script comme du texte : une `playlist()` ou un `random`
glissé dedans contournerait le noyau sans qu'aucun test Python le voie.
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
    """Par défaut, Liquidsoap réessaie sans fin (docs/liquidsoap.md §3)."""
    assert "shutdown()" in _code()
    assert "status_code == 204" in _code()


def test_rien_ne_joue_sans_auditeur() -> None:
    assert re.search(r"listeners\(\)\s*>\s*0", _code())
    assert "blank()" in _code()


def test_rien_n_est_tire_ni_decode_sans_auditeur() -> None:
    """Le `switch` sur les auditeurs ne suffit pas : en 2.4, `normalize` tire sa
    source quelle que soit la sortie, et la chaîne décodait et annonçait un
    morceau devant `blank()` (docs/liquidsoap.md §17). La source est rendue
    indisponible avant `cross`, qui sinon commence une piste pour lui répondre.
    """
    code = _code()
    garde = "programme = source.available(programme, {listeners() > 0})"
    assert garde in code
    assert code.index(garde) < code.index("programme = cross(")
    assert code.index(garde) < code.index("programme = normalize(")


def test_un_direct_est_une_instruction_de_l_api_pas_du_script() -> None:
    """L'adresse et la fin du direct viennent de l'API, pas du script (GOAL-015)."""
    code = _code()
    assert 'prefix="live:"' in code
    assert "input.http(" in code
    assert "self_sync=false" in code, "sans lui la rafale initiale avale le morceau en cours"


def test_un_direct_prend_l_antenne_a_une_jonction() -> None:
    """`track_sensitive=true` ne suffit pas : derrière `crossfade`, le `switch`
    ne voit aucune fin de piste (docs/liquidsoap.md §9). Un témoin armé au
    début de chaque piste applique la règle de SPECS.md §4.11 (GOAL-051)."""
    code = _code()
    assert "direct_arme = ref(false)" in code
    assert "direct_arme := live_pending()" in code
    assert re.search(r"direct_arme\(\).*live\.is_ready\(\).*live", code, re.DOTALL)


def test_un_direct_s_annonce_quand_il_prend_l_antenne() -> None:
    """`live.on_track` se déclenche deux fois et une piste trop tôt
    (docs/liquidsoap.md §9). Seule la transition du `switch` marque l'instant
    où le direct est à l'antenne (GOAL-051)."""
    code = _code()
    assert "live.on_track" not in code
    prise = re.search(r"def prise_direct.*?\nend\n", code, re.DOTALL)
    assert prise is not None
    assert "annoncer_le_direct()" in prise.group()
    assert "transitions=[prise_direct, rendu_direct]" in code


def test_le_saut_est_une_route_que_l_api_ordonne() -> None:
    """Le script saute sur ordre de l'API, jamais de lui-même (GOAL-017)."""
    code = _code()
    assert '"/skip"' in code
    assert "programme.skip()" in code


def test_le_script_refuse_un_saut_a_vide() -> None:
    """Un saut sans piste en cours consomme l'entrée fraîche
    (docs/liquidsoap.md §9). Seul le script sait si une piste passe, car
    `radio` peut avoir redémarré seul (GOAL-051)."""
    code = _code()
    assert "piste_commencee = ref(false)" in code
    assert "piste_commencee := true" in code
    assert re.search(r"if piste_commencee\(\) then", code)


def test_la_fin_d_un_direct_jette_l_avance_rassie() -> None:
    """L'avance a été tirée à l'ouverture du direct, pas à sa fermeture : elle
    est rassise et doit être purgée (docs/liquidsoap.md §9, GOAL-051)."""
    code = _code()
    fin_du_direct = re.search(r"def stop_live.*?\nend\n", code, re.DOTALL)
    assert fin_du_direct is not None
    assert "purger()" in fin_du_direct.group()
    assert "programme.set_queue([])" in code.split("vider_l_avance :=", 1)[1]


def test_un_saut_a_antenne_vide_ne_laisse_aucun_reliquat_au_premier_auditeur() -> None:
    """`cross` garde deux secondes du morceau coupé, et un saut ordonné sans
    auditeur ne s'exécute qu'au premier tirage, quand quelqu'un écoute déjà
    (docs/liquidsoap.md §10). La transition jette ce reliquat ; le reste
    reproduit `crossfade` (GOAL-055)."""
    code = _code()
    assert "reliquat_a_taire = ref(false)" in code
    saut = re.search(r"def sauter\(\).*?\nend\n", code, re.DOTALL)
    assert saut is not None
    assert "if listeners() == 0 then reliquat_a_taire := true end" in saut.group()
    assert "programme.skip()" in saut.group()
    appels = re.findall(r"(?<!def )sauter\(\)", code)
    assert len(appels) == 3, "le saut de l'API, celui d'un épisode et celui de fin de direct"
    transition = re.search(r"def enchainer\(a, b\).*?\nend\n", code, re.DOTALL)
    assert transition is not None
    assert re.search(
        r"if reliquat_a_taire\(\) then.*?b\.source.*?else.*?cross\.simple\(",
        transition.group(),
        re.DOTALL,
    )
    assert "cross(duration=2., enchainer, programme)" in code
    assert "crossfade(" not in code, "crossfade ne laisse pas choisir sa transition"


def test_l_antenne_est_muette_tant_que_le_morceau_frais_n_est_pas_entre() -> None:
    """Jeter le reliquat à la transition ne suffit pas : elle ne s'exécute
    qu'une fois le morceau frais bufférisé, et l'API peut tarder à le rendre.
    La sortie a alors déjà tiré le reliquat entier — deux secondes qui
    finissent à plein volume (docs/liquidsoap.md §11). Seul le gain agit
    assez tôt.
    """
    code = _code()
    gain = re.search(r"def gain_antenne\(\).*?\nend\n", code, re.DOTALL)
    assert gain is not None
    assert "reliquat_a_taire()" in gain.group(), "le muet doit porter sur le gain"
    assert "direct_a_l_antenne()" in gain.group(), (
        "un direct n'a rien de rassis à taire, et le muet le rendrait silencieux"
    )
    assert "0." in gain.group(), "le muet est un gain nul, pas une atténuation"


def test_le_morceau_frais_entre_sous_la_rampe_de_prise_d_antenne() -> None:
    """La rampe est armée quand le `switch` rend l'antenne. L'attente du
    morceau frais l'épuise, et il entrait alors à plein gain. La transition la
    réarme (docs/liquidsoap.md §11).
    """
    code = _code()
    transition = re.search(r"def enchainer\(a, b\).*?\nend\n", code, re.DOTALL)
    assert transition is not None
    branche = transition.group().split("else", 1)[0]
    assert "antenne_prise := time()" in branche


def test_le_direct_et_le_muet_lisent_le_meme_predicat() -> None:
    """Deux copies du prédicat divergeraient, et c'est le muet qui perdrait :
    un direct pris entre le saut et la transition resterait silencieux toute
    sa case, puisque rien ne lève le muet avant que `programme` revienne."""
    code = _code()
    predicat = re.search(r"def direct_a_l_antenne\(\).*?\nend\n", code, re.DOTALL)
    assert predicat is not None
    assert "live.is_ready()" in predicat.group()
    ailleurs = code.replace(predicat.group(), "")
    assert "live.is_ready()" not in ailleurs, "le prédicat est nommé une fois, et lu partout"
    assert re.search(r"\{\s*direct_a_l_antenne\(\)\s*\}\s*,\s*live", code), (
        "le switch choisit le direct par le même prédicat que le muet"
    )


def test_l_avance_se_jette_sur_ordre_de_l_api() -> None:
    """Un encore accepté vide l'avance du diffuseur (GOAL-034)."""
    code = _code()
    assert '"/requeue"' in code
    assert "set_queue([])" in code


def test_passer_un_episode_remplace_l_avance_avant_de_sauter() -> None:
    """Vider l'avance puis sauter laisse 5,75 s de blanc, le temps que l'entrée
    fraîche se résolve ; résoudre avant le saut garde l'antenne pleine. L'ordre
    est imposé : `set_queue` détruit les requêtes de la file, donc une entrée
    fraîche obtenue avant lui ne survivrait pas (docs/liquidsoap.md §12 et §14,
    GOAL-086-T05). `fetch()` ne convient plus : il rend la main aussitôt et
    résout en arrière-plan (docs/liquidsoap.md §15.2, GOAL-088-T02)."""
    code = _code()
    assert '"/skip-fresh"' in code
    route = re.search(r"def on_skip_fresh.*?\nend\n", code, re.DOTALL)
    assert route is not None
    corps = route.group()
    assert "programme.fetch()" not in corps, (
        "en 2.4 il est asynchrone : le saut trouve la file vide"
    )
    assert corps.index("programme.set_queue([])") < corps.index("request.resolve(")
    assert corps.index("request.resolve(") < corps.index("programme.add(")
    assert corps.index("programme.add(") < corps.index("sauter()")


def test_passer_un_episode_se_refuse_a_vide_comme_un_saut() -> None:
    """Un saut sans piste en cours consomme l'entrée fraîche
    (docs/liquidsoap.md §9) : la route combinée n'y échappe pas."""
    route = re.search(r"def on_skip_fresh.*?\nend\n", _code(), re.DOTALL)
    assert route is not None
    assert "if piste_commencee() then" in route.group()
    assert "else" in route.group(), "un refus muet serait indistinguable d'une panne"


def test_le_script_redit_ce_qu_il_joue_sur_ordre_de_l_api() -> None:
    """Le diffuseur n'annonce qu'au début d'une entrée : un processus `radio`
    neuf resterait sans savoir ce qui passe jusqu'à la jonction suivante. Le
    script garde son dernier corps posté et le redit (GOAL-086-T03)."""
    code = _code()
    assert 'derniere_annonce = ref("")' in code
    assert "derniere_annonce := body" in code
    assert '"/announce"' in code
    annonce = re.search(r"def on_announce.*?\nend\n", code, re.DOTALL)
    assert annonce is not None
    assert "derniere_annonce()" in annonce.group()
    assert "/playout/playing" in annonce.group()


def test_l_annonce_du_morceau_date_son_debut() -> None:
    """Une ré-annonce arrive après le début : sans l'instant du début, l'écoulé
    annoncé à l'antenne repartirait de zéro (GOAL-086-T03)."""
    code = _code()
    corps = re.search(r"def annoncer_la_piste.*?\nend\n", code, re.DOTALL)
    assert corps is not None
    assert '"#{time()}"' in corps.group()


def test_la_prise_d_antenne_se_fond() -> None:
    """Le premier auditeur a un fondu d'entrée. `fade.in` ne fond pas une
    source déjà entamée : c'est la transition qui arme un `amplify`
    (docs/liquidsoap.md §8, GOAL-050)."""
    code = _code()
    assert "transitions=[prise_antenne" in code
    assert re.search(r"amplify\(gain_antenne", code)


def test_le_branchement_s_annonce_avant_de_rendre_l_antenne() -> None:
    """L'antenne reste muette tant que le compteur est à zéro, ce qui laisse
    l'API purger une avance rassise sans course (docs/liquidsoap.md §5.bis,
    GOAL-041). Les rappels sont posés par méthode sur la sortie : en 2.4
    l'argument d'`output.harbor` est déprécié et change de type
    (docs/liquidsoap.md §15.1)."""
    code = _code()
    assert "radio.on_connect(synchronous=true, on_connect)" in code
    assert "radio.on_disconnect(synchronous=true, on_disconnect)" in code
    connect = code[code.index("def on_connect") : code.index("def on_disconnect")]
    annonce = connect.index("announce_count(listeners() + 1)")
    bascule = connect.index("listeners := listeners() + 1")
    assert annonce < bascule, "la bascule avant l'annonce rendrait l'antenne avant la purge"


# ── Le script voyage dans l'image (GOAL-053) ────────────────────────────────


def test_le_script_voyage_dans_l_image_du_diffuseur() -> None:
    """Monté depuis l'hôte, le script n'était pas versionné avec l'image et
    pouvait dériver de `radio` sans que le déploiement le voie."""
    assert f"COPY {SCRIPT} /etc/local-webradio/radio.liq" in DOCKERFILE.read_text()
    assert str(SCRIPT) not in COMPOSE.read_text(), "le script ne se monte plus, il est dans l'image"


@pytest.mark.parametrize("service", ["radio", "liquidsoap"])
def test_chaque_service_lit_le_fuseau_de_l_hote(service: str) -> None:
    """Sans le fuseau de l'hôte, le journal du diffuseur est en UTC et celui
    de `radio` en heure locale : deux fuseaux pour un seul incident. `radio`
    en a besoin pour la grille, qui est en heure locale (GOAL-015)."""
    compose = COMPOSE.read_text()
    debut = compose.index(f"\n  {service}:")
    suite = re.search(r"\n  [a-z]", compose[debut + 1 :])
    bloc = compose[debut:] if suite is None else compose[debut : debut + 1 + suite.start()]
    assert "/etc/localtime:/etc/localtime:ro" in bloc


def test_l_epingle_de_liquidsoap_ne_diverge_pas() -> None:
    """L'image du diffuseur et la vérification de syntaxe nomment la même
    image, sinon on valide contre une version qu'on ne déploie pas
    (docs/liquidsoap.md §1.7). Un condensat, pas un tag : la branche 2.4 est la
    seule à émettre les métadonnées ICY et son tag flotte, donc un tag ne
    fixerait rien (docs/liquidsoap.md §15)."""
    epingle = r"savonet/liquidsoap@sha256:[0-9a-f]{64}"
    depuis = re.search(rf"^FROM ({epingle})$", DOCKERFILE.read_text(), re.M)
    validee = re.search(rf"LIQUIDSOAP_IMAGE:-({epingle})\}}", VERIFIER.read_text())
    assert depuis is not None and validee is not None
    assert depuis.group(1) == validee.group(1)
