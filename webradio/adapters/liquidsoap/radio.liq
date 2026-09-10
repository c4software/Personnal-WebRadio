# Ce que Liquidsoap fait pour local-webradio.
#
# Le script ne décide rien (ARCHITECTURE.md §4) : il demande le morceau suivant
# à l'API, lui annonce ses auditeurs, encode et sert. Pas de playlist(), pas de
# hasard, pas de jingle, pas de chemin de fichier ; un test le vérifie
# (GOAL-016-T04).
#
# Validé par `liquidsoap --check` contre la version épinglée, dans verifier.sh :
# la syntaxe change d'une version à l'autre (docs/liquidsoap.md §1.7).

settings.log.stdout := true
settings.log.level := 3
# La résolution télécharge la vidéo avant de jouer, une trentaine de Mo : le
# défaut de 29 s ne suffit pas toujours (docs/youtube.md).
settings.request.timeout := 120.
# audio/webm manque à la table des extensions ; sans elle le fichier
# téléchargé n'a pas de nom et la résolution échoue.
settings.http.mime.extnames := list.add(("audio/webm", ".webm"), settings.http.mime.extnames())
settings.harbor.bind_addrs := ["0.0.0.0"]

# ── Ce que l'environnement fournit ──────────────────────────────────────────
api = environment.get(default="http://127.0.0.1:8080", "RADIO_API")
port = int_of_string(default=8000, environment.get(default="8000", "RADIO_PORT"))
mount = environment.get(default="/stream", "RADIO_MOUNT")
bitrate = int_of_string(default=128, environment.get(default="128", "RADIO_BITRATE"))
name = environment.get(default="local-webradio", "RADIO_NAME")
# En secondes : au-delà, une API qui ne répond pas est une panne (SPECS.md §5.1).
api_timeout = float_of_string(default=10., environment.get(default="10", "RADIO_API_TIMEOUT"))

# ── Couper en le disant (SPECS.md §5.1) ─────────────────────────────────────
# Laissé à lui-même, Liquidsoap réessaie sans fin et sert du silence
# (docs/liquidsoap.md §3). Ici, on s'arrête quand l'API répond 204 ou ne répond
# pas deux fois de suite. Le superviseur relance un processus neuf, et un
# auditeur qui se rebranche redémarre une radio neuve (SPECS.md §4.7).
failures = ref(0)

def stop_saying_why(why) =
  log(level=2, "la diffusion s'arrête : #{why}")
  shutdown()
end

# ── Redire ce qui passe, sur ordre de l'API (SPECS.md §7 n°42) ─────────────
# Le corps du dernier POST vers `/playout/playing`. Un processus `radio` neuf
# ne sait pas ce qui passe : le diffuseur n'annonce qu'au début d'une entrée, et
# l'antenne resterait inconnue jusqu'à la jonction suivante. La route /announce
# le redit tel quel, sans toucher au morceau en cours (docs/liquidsoap.md §13).
derniere_annonce = ref("")

# ── Un direct, sur instruction de l'API (SPECS.md §4.11, GOAL-015) ─────────
# L'API rend `live:<fin en secondes Unix>:<libellé>:<url>`. Un direct ne peut
# pas être une requête : la résolution d'un flux infini expire
# (docs/liquidsoap.md §5). Il passe donc par `input.http`, démarré dès
# l'instruction pour avoir le temps de se remplir, mis à l'antenne à la jonction
# (`direct_arme`) et coupé à l'heure dite. Sans `self_sync=false`, la rafale
# initiale du serveur accélère l'horloge de la sortie et le morceau en cours est
# avalé (docs/liquidsoap.md §5).
live_url = ref("")
live_entry = ref("")
live_label = ref("")
live_pending = ref(false)
live_raw = input.http(id="live", start=false, self_sync=false, max_buffer=3., {live_url()})

# Le libellé que les lecteurs affichent pendant le direct (SPECS.md §4.9). Le
# flux distant n'envoie aucune métadonnée (docs/franceinfo.md), et sans ce
# titre le lecteur garde celui du morceau d'avant toute la case
# (docs/liquidsoap.md §15.5). `update=false` : la carte remplace ce qui vient
# du distant, un `artist` relayé ne survit donc pas.
live = metadata.map(
  insert_missing=true, update=false, fun (_) -> [("title", live_label())], live_raw
)

# Ce qu'il faut faire de l'avance quand le direct rend l'antenne. Un `ref` de
# fonction parce que `stop_live` est défini avant `programme` ; rempli plus bas.
# Elle reçoit de quoi sortir le direct de l'antenne, et choisit quand : le
# morceau frais est résolu avant, le saut vient après.
vider_l_avance = ref(fun (rendre) -> rendre())

def stop_live(why) =
  if live_pending() then
    log("le direct se termine : #{why}")
    # L'avance a dormi sous le direct : elle a été tirée à l'ouverture de la
    # case, pas à sa fermeture. Même rassise qu'après une longue pause
    # (SPECS.md §7 n°30).
    #
    # La purge tient l'ordre entier, arrêt du direct compris : elle résout le
    # morceau frais tant que le direct est encore à l'antenne, puis coupe. Sans
    # cela, les deux secondes que `cross` tient du morceau gelé passent à plein
    # volume et le frais entre à froid deux secondes plus tard
    # (docs/liquidsoap.md §16.4). Le direct se prolonge du temps de résolution,
    # ce que SPECS.md §7 n°22 tolère ; un blanc, non.
    #
    # Le fil est celui du `thread.run` de `start_live`, pas celui de la
    # diffusion : `request.resolve` peut y bloquer, avec le budget de
    # `settings.request.timeout`.
    purger = vider_l_avance()
    purger(fun () -> begin
      live_pending := false
      live_raw.stop()
    end)
  end
end

def start_live(entry) =
  parts = string.split(separator=":", entry)
  ends_at = float_of_string(default=0., list.nth(default="0", parts, 1))
  # Le libellé n'a pas de deux-points, l'API le garantit ; l'URL en a, et c'est
  # elle qu'on recompose.
  label = list.nth(default="", parts, 2)
  address = string.concat(separator=":", list.tl(list.tl(list.tl(parts))))
  remaining = ends_at - time()
  if live_pending() then
    log(level=2, "un direct est déjà en cours, instruction ignorée")
  elsif remaining <= 0. then
    log(level=2, "direct déjà terminé à sa demande, ignoré")
  else
    live_url := address
    live_entry := entry
    live_label := label
    live_pending := true
    live_raw.start()
    log("direct demandé pour #{int_of_float(remaining)} s")
    thread.run(delay=remaining, {stop_live("heure de fin atteinte")})
  end
end

# Annonce le direct à l'API, avec l'entrée telle qu'elle l'a rendue. Appelée
# depuis la transition qui met le direct à l'antenne, et de nulle part ailleurs :
# `live.on_track` se déclenche deux fois au démarrage d'un `input.http` et une
# piste trop tôt (docs/liquidsoap.md §9).
def annoncer_le_direct() =
  derniere_annonce := live_entry()
  answer = http.post(timeout=api_timeout, data=live_entry(), "#{api}/playout/playing")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce du direct (#{answer.status_code})")
  end
end

# ── Le morceau suivant : c'est l'API qui décide ─────────────────────────────
def ask_next() =
  answer = http.post(timeout=api_timeout, "#{api}/playout/next")
  if answer.status_code == 200 then
    failures := 0
    entry = string.trim(answer)
    # Sans la chaîne de requête : une URL de flux Subsonic porte le jeton
    # d'accès (docs/subsonic.md).
    shown = list.hd(default=entry, string.split(separator="\\?", entry))
    log("suivant : #{shown}")
    entry
  elsif answer.status_code == 204 then
    stop_saying_why("l'API n'a plus rien à jouer")
    ""
  else
    failures := failures() + 1
    log(level=2, "l'API ne répond pas (#{answer.status_code} #{answer.status_message}), essai #{failures()}")
    if failures() >= 2 then stop_saying_why("l'API ne répond plus") end
    ""
  end
end

def next_entry() =
  entry = ask_next()
  if entry == "" then
    null
  elsif string.contains(prefix="live:", entry) then
    # Un direct n'est pas une requête : on le lance, puis on redemande le
    # morceau réel pour que la file ne soit jamais vide.
    start_live(entry)
    following = ask_next()
    if following == "" or string.contains(prefix="live:", following) then null
    else request.create(following) end
  else
    request.create(entry)
  end
end

# prefetch=1 est le minimum : à 0 la source n'est jamais prête
# (docs/liquidsoap.md §3).
programme = request.dynamic(id="programme", retry_delay=5., prefetch=1, next_entry)

# Ce qui commence réellement, par opposition à ce qui a été demandé : c'est de
# là que l'API sait ce qui passe (GOAL-016-T08). L'annonce porte l'entrée puis
# les étiquettes lues dans le fichier, pour que `radio` redémarré affiche au
# moins ce que le décodeur sait.
#
# Seul témoin fiable qu'une piste passe (docs/liquidsoap.md §9) : `radio`
# redémarré a perdu le sien et croirait l'antenne vide.
piste_commencee = ref(false)

# Seul signal de jonction dont dispose le direct. Un `switch(track_sensitive=true)`
# derrière `crossfade` ne reçoit aucune fin de piste et cesse d'évaluer ses
# prédicats (docs/liquidsoap.md §9). Le `switch` évalue donc en continu, et ce
# témoin, armé à un début de piste, garantit que le direct n'entre pas au milieu
# d'un morceau (SPECS.md §4.11).
direct_arme = ref(false)

def annoncer_la_piste(tags) =
  piste_commencee := true
  direct_arme := live_pending()
  # La quatrième ligne date le début : une ré-annonce arrive plus tard, et
  # l'écoulé annoncé à l'antenne repartirait de zéro (SPECS.md §4.8).
  body = tags["initial_uri"] ^ "\n" ^ tags["artist"] ^ "\n" ^ tags["title"]
         ^ "\n" ^ "#{time()}"
  derniere_annonce := body
  answer = http.post(timeout=api_timeout, data=body, "#{api}/playout/playing")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce du morceau (#{answer.status_code})")
  end
end
# `synchronous` est exigé de tous les rappels de source en 2.4
# (docs/liquidsoap.md §15.1). Vrai : l'annonce part du fil de diffusion, comme
# en 2.3.3.
programme.on_track(synchronous=true, annoncer_la_piste)

# Redit la dernière annonce, telle quelle. C'est `radio` qui l'ordonne, au
# premier battement d'un processus qui ne sait pas ce qui passe.
def on_announce(req, response) =
  ignore(req)
  if derniere_annonce() == "" then
    log("ré-annonce demandée, mais rien n'a encore été annoncé")
    response.data("rien annoncé")
  else
    log("ré-annonce de ce qui passe, sur ordre de l'API")
    answer = http.post(timeout=api_timeout, data=derniere_annonce(), "#{api}/playout/playing")
    if answer.status_code != 204 then
      log(level=2, "l'API n'a pas pris la ré-annonce (#{answer.status_code})")
    end
    response.data("redit")
  end
end
harbor.http.register(port=port, method="POST", "/announce", on_announce)

# ── Passer le morceau en cours (SPECS.md §4.6, GOAL-017) ───────────────────
# C'est `radio` qui décide d'un saut, sur un vote `stop` accepté, et qui
# l'ordonne par cette route. Le saut porte sur la file des morceaux : pendant
# un direct ou un jingle, le noyau refuse le vote et l'ordre n'arrive jamais.
#
# Un saut à vide n'est pas inoffensif : il reste enregistré et mange l'entrée
# fraîche dès son départ (docs/liquidsoap.md §9). Le refus est ici plutôt que
# chez l'appelant, qui ne sait pas ce que ce processus tient.
#
# Le compteur d'auditeurs est déclaré avant le saut, qui a besoin de savoir si
# quelqu'un écoute. Il est tenu plus bas, par le harbor.
listeners = ref(0)

# Un saut ordonné sans auditeur (purge de reprise, SPECS.md §7 n°30, ou fin de
# direct) ne s'exécute qu'au premier tirage, quand quelqu'un écoute déjà. Or
# `cross` tient deux secondes déjà lues du morceau coupé, qui partiraient en
# fondu de sortie. Ce témoin dit à la transition de les jeter
# (docs/liquidsoap.md §10).
#
# Il tait aussi l'antenne jusque-là : la transition attend que le morceau frais
# soit bufférisé, et si l'API tarde, la sortie a déjà servi le reliquat entier
# (docs/liquidsoap.md §11).
reliquat_a_taire = ref(false)

# Déclarée ici, loin du reste de son mécanisme (GOAL-050) : la transition de
# `cross` la réarme, et elle est définie plus haut que lui.
antenne_prise = ref(0.)

def sauter() =
  if listeners() == 0 then reliquat_a_taire := true end
  programme.skip()
end

def on_skip(req, response) =
  ignore(req)
  if piste_commencee() then
    log("saut demandé par l'API")
    sauter()
  else
    log("saut demandé à vide : rien ne passe, il mangerait le premier morceau")
  end
  response.data("passé")
end
harbor.http.register(port=port, method="POST", "/skip", on_skip)

# Un encore accepté vide le morceau d'avance (GOAL-034) : sans cela la chanson
# déjà demandée s'intercale et l'effet arrive un morceau trop tard.
def on_requeue(req, response) =
  ignore(req)
  log("avance jetée sur ordre de l'API")
  programme.set_queue([])
  response.data("vidé")
end
harbor.http.register(port=port, method="POST", "/requeue", on_requeue)

# Passer un épisode de plage : c'en piocher un autre (SPECS.md §7 n°44). Vider
# l'avance puis sauter laisse 5,75 s de blanc, le temps que l'entrée fraîche se
# résolve ; remplacer d'abord garde l'antenne pleine jusqu'à la bascule
# (docs/liquidsoap.md §12). L'ordre est imposé : une requête rendue par
# `queue()` est détruite par le `set_queue` suivant, donc la résolution ne peut
# pas précéder la purge (§14).
#
# En 2.4, `fetch()` rend `unit` et résout en arrière-plan : le saut tomberait
# sur une file vide, 3,75 s de blanc mesurées. Le gestionnaire tire donc
# lui-même, résout, puis ajoute la requête (docs/liquidsoap.md §15.2).
# `request.resolve` bloque ce gestionnaire toute la résolution, avec le budget
# du tirage ordinaire (`settings.request.timeout`) : l'API poste sans attendre
# la réponse, et ce journal est le seul témoin de ce qui s'est passé.
def on_skip_fresh(req, response) =
  ignore(req)
  if piste_commencee() then
    log("épisode passé sur ordre de l'API : l'avance est remplacée avant le saut")
    programme.set_queue([])
    fraiche = next_entry()
    if null.defined(fraiche) then
      r = null.get(fraiche)
      if request.resolve(r) then
        ignore(programme.add(r))
        log("entrée fraîche résolue et mise en file")
      else
        log(level=2, "l'entrée fraîche ne s'est pas résolue, le saut aura un blanc")
      end
    else
      # Un direct ou une API à court : le tirage d'avance que la purge réveille
      # reste le seul recours.
      log(level=2, "aucune entrée fraîche à mettre en file")
    end
    sauter()
    log("épisode passé : le saut est fait")
  else
    log("saut demandé à vide : rien ne passe, il mangerait le premier morceau")
  end
  response.data("passé")
end
harbor.http.register(port=port, method="POST", "/skip-fresh", on_skip_fresh)

# La purge de fin de direct, maintenant que `programme` existe. Le script ne
# choisit rien : il jette ce qui a rassis et redemande à l'API
# (ARCHITECTURE.md §4).
#
# Même mécanique que `on_skip_fresh`, pour la même raison : `set_queue` détruit
# les requêtes de la file, la résolution ne peut donc pas le précéder
# (docs/liquidsoap.md §14), et `fetch()` résout en arrière-plan en 2.4, ce qui
# laisserait la file vide au saut (§15.2). Ici la résolution a un second effet :
# elle se fait direct encore à l'antenne, donc sans blanc (SPECS.md §7 n°22).
#
# Le témoin est armé avant que le direct ne rende l'antenne, pas après :
# `gain_antenne` épargne un direct à l'antenne, l'armer tôt n'a donc aucun effet
# audible, tandis que l'armer après `live_raw.stop()` laisserait la sortie
# servir le reliquat gelé à plein volume le temps que l'arrêt rende la main
# (docs/liquidsoap.md §16.4). Le saut, lui, vient après : sous le direct il
# ferait commencer le morceau frais hors antenne.
#
# Les deux sous la garde de `piste_commencee` : sans piste en cours, aucune
# transition ne viendrait consommer le témoin et l'antenne resterait muette.
vider_l_avance := fun (rendre) -> begin
  log("fin du direct : l'avance rassie est jetée, le reliquat coupé")
  programme.set_queue([])
  fraiche = next_entry()
  if null.defined(fraiche) then
    r = null.get(fraiche)
    if request.resolve(r) then
      ignore(programme.add(r))
      log("morceau frais résolu avant que le direct ne rende l'antenne")
    else
      log(level=2, "le morceau frais ne s'est pas résolu, la fin du direct aura un blanc")
    end
  else
    # Une API à court, ou un nouveau direct : le tirage d'avance que la purge
    # réveille reste le seul recours.
    log(level=2, "aucun morceau frais à mettre en file")
  end
  if piste_commencee() then reliquat_a_taire := true end
  rendre()
  if piste_commencee() then sauter() end
end

# Le fondu enchaîné de `crossfade`, à une exception près : après un saut à
# antenne vide, le reliquat de `a` est jeté et `b` entre seul, sous le fondu de
# prise d'antenne. Le reste reprend l'appel de `crossfade` (fades.liq,
# docs/liquidsoap.md §10) : mêmes fondus, mêmes étiquettes honorées.
def enchainer(a, b) =
  if reliquat_a_taire() then
    reliquat_a_taire := false
    # La rampe est réarmée ici, pas à la prise d'antenne : l'attente du morceau
    # frais l'aurait épuisée, et il entrerait à froid (docs/liquidsoap.md §11).
    antenne_prise := time()
    log("saut à antenne vide : le reliquat est jeté, le morceau frais entre seul")
    b.source
  else
    cross.simple(fade_in=1., fade_out=1., initial_fade_in_metadata=b.metadata,
                 initial_fade_out_metadata=a.metadata, a.source, b.source)
  end
end
# En 2.4, `normalize` consomme sa source en continu quelle que soit la sortie :
# la chaîne tirait, décodait et annonçait un morceau avec `blank()` à l'antenne
# (docs/liquidsoap.md §17). Rendre la source indisponible avant `cross` la fige
# jusqu'au premier auditeur, comme en 2.3.3 (SPECS.md §1). Ici et pas plus bas :
# posée après `cross`, elle laisse encore `cross` commencer une piste.
programme = source.available(programme, {listeners() > 0})
programme = cross(duration=2., enchainer, programme)

# ── Ce que les lecteurs affichent hors chanson (SPECS.md §4.9) ─────────────
# Une chanson garde « Artiste - Titre », que Liquidsoap assemble des étiquettes
# du fichier. Le reste annonce le libellé de l'interface, qui affiche le titre
# déclaré ou, à défaut, la nature. Annoter `title=` ne suffirait pas : l'artiste
# du fichier subsiste, et une valeur vide ne retire pas la clé — seul
# `strip=true` nettoie (docs/liquidsoap.md §15.4).
#
# Après le `on_track` de `programme`, donc sans effet sur ce que l'API reçoit.
def libelle_hors_chanson(tags) =
  nature = tags["radio_kind"]
  if nature == "" or nature == "musique" then
    []
  else
    libelle = if tags["radio_label"] == "" then nature else tags["radio_label"] end
    [("title", libelle), ("artist", "")]
  end
end
programme = metadata.map(strip=true, libelle_hors_chanson, programme)

# Après `cross`, jamais avant : en 2.4, `normalize` devant lui supprime les
# métadonnées et le recouvrement (docs/liquidsoap.md §15.3).
programme = normalize(programme)

# Le direct prend la main à la jonction, jamais au milieu d'un morceau
# (SPECS.md §4.11), et la rend à la seconde dès qu'il s'arrête. Placé après
# `normalize` et `cross` : ces opérateurs refusent une source qui contrôle sa
# propre latence, ce qu'est `input.http`, et `--check` ne le voit pas
# (docs/liquidsoap.md §5).
#
# `track_sensitive=false` plus `direct_arme` plutôt que `true` : voir le témoin
# plus haut. La jonction obtenue tombe environ deux secondes avant la fin
# audible du morceau, en plein fondu de sortie qu'elle écourte ; compromis
# arbitré au profit d'une heure d'entrée garantie (SPECS.md §7 n°22).
#
# L'annonce part d'ici seulement, seul instant où le direct est à l'antenne.
# `thread.run` parce qu'une transition s'exécute dans le fil de diffusion, où
# un POST bloquant ferait un trou.
def prise_direct(_, b) =
  log("le direct prend l'antenne")
  # Le titre est posé ici, sur la source brute, et pas seulement par la carte :
  # celle-ci ne parle qu'au début de la piste, or le flux coule depuis
  # l'instruction, parfois une jonction entière plus tôt, et le bloc est alors
  # perdu avant l'antenne (docs/liquidsoap.md §19).
  live_raw.insert_metadata([("title", live_label())])
  thread.run({annoncer_le_direct()})
  b
end

# Le retour à la musique s'annonce seul : la purge de `stop_live` force un
# tirage frais, dont le `on_track` dit ce qui commence.
def rendu_direct(_, b) = b end

# Nommé parce que le muet de la reprise lit le même prédicat que le `switch` :
# un direct n'a rien de rassis à taire, et le muet le laisserait silencieux
# toute sa case, la transition qui le lève n'ayant lieu qu'au retour de
# `programme`.
def direct_a_l_antenne() =
  direct_arme() and live_pending() and live.is_ready()
end

on_air = switch(
  track_sensitive=false, transitions=[prise_direct, rendu_direct],
  [({direct_a_l_antenne()}, live), ({true}, programme)]
)

# ── Rien n'est décodé ni demandé sans auditeur (SPECS.md §1) ────────────────
def announce_count(count) =
  answer = http.post(timeout=api_timeout, data="#{count}", "#{api}/playout/listeners")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce des auditeurs (#{answer.status_code})")
  end
end

def announce() = announce_count(listeners()) end

# Périodiquement, pas seulement aux branchements : si `radio` redémarre pendant
# que des auditeurs écoutent, son compteur repart à zéro et l'antenne s'affiche
# vide alors qu'elle joue. Le battement ressoude l'état.
thread.run(every=15., announce)

# L'annonce part avant la bascule du compteur : tant que le `ref` est à zéro
# l'antenne reste sur `blank()`, et l'API peut purger une avance rassise sans
# course avec la reprise du son (docs/liquidsoap.md §5.bis, SPECS.md §7 n°30).
def on_connect(client) =
  announce_count(listeners() + 1)
  listeners := listeners() + 1
  log("auditeur #{client.ip} branché — #{listeners()} à l'écoute")
end

def on_disconnect(ip) =
  listeners := listeners() - 1
  log("auditeur #{ip} parti — #{listeners()} à l'écoute")
  announce()
end

# ── Le fondu à la prise d'antenne (GOAL-050) ────────────────────────────────
# Le flux est encodé une fois et partagé : pas de fondu par auditeur. Quand le
# premier se branche, la bascule blank() → antenne tombe au milieu du morceau,
# plein volume. `fade.in` ne fond pas une source entamée : la transition arme
# un instant, et un `amplify` monte le gain de 0 à 1 en deux secondes
# (docs/liquidsoap.md §8).
duree_fondu = 2.

def prise_antenne(_, b) =
  antenne_prise := time()
  b
end

def rendre_antenne(_, b) = b end

on_air = switch(track_sensitive=false, transitions=[prise_antenne, rendre_antenne],
                [({listeners() > 0}, on_air), ({true}, blank())])

def gain_antenne() =
  if reliquat_a_taire() and not direct_a_l_antenne() then
    0.
  else
    d = time() - antenne_prise()
    if d >= duree_fondu then 1. elsif d < 0. then 0. else d / duree_fondu end
  end
end

on_air = amplify(gain_antenne, on_air)

radio = output.harbor(
  %mp3(bitrate=bitrate),
  port=port, mount=mount,
  headers=[("icy-name", name), ("icy-br", "#{bitrate}")],
  on_air
)

# Par méthode : en 2.4 les arguments `on_connect` et `on_disconnect` sont
# dépréciés, et le rappel reçoit un enregistrement au lieu d'en-têtes
# (docs/liquidsoap.md §15.1).
radio.on_connect(synchronous=true, on_connect)
radio.on_disconnect(synchronous=true, on_disconnect)
