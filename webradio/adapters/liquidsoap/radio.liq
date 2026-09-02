# radio.liq — ce que Liquidsoap fait pour local-webradio, et rien de plus.
#
# Ce script ne décide de RIEN (ARCHITECTURE.md §4). Il demande le morceau
# suivant à l'API, il annonce ses auditeurs à l'API, il encode et il sert.
# Pas de playlist(), pas de hasard, pas de jingle, pas de chemin de fichier :
# un test lit ce fichier et refuse tout cela (GOAL-016-T04).
#
# Validé par `liquidsoap --check` contre la version épinglée, dans
# verifier.sh : la syntaxe change d'une version à l'autre
# (docs/liquidsoap.md §1.7).

settings.log.stdout := true
settings.log.level := 3
# Une émission YouTube est un fichier de ~30 Mo que la résolution TÉLÉCHARGE
# avant de jouer : 29 s (le défaut) ne suffisent pas toujours — constaté le
# 2026-08-30, la vidéo a été abandonnée à la seconde près (docs/youtube.md).
settings.request.timeout := 120.
# Et audio/webm manque à la table des extensions : sans elle, le fichier
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
# Liquidsoap, laissé à lui-même, réessaie sans fin et sert du silence
# (docs/liquidsoap.md §3). Ici : l'API dit « fini » (204) ou ne répond pas deux
# fois de suite → on s'arrête. Le superviseur relance un processus NEUF, et un
# auditeur qui se rebranche redémarre une radio neuve (SPECS.md §4.7).
failures = ref(0)

def stop_saying_why(why) =
  log(level=2, "la diffusion s'arrête : #{why}")
  shutdown()
end

# ── Un direct, sur instruction de l'API (SPECS.md §4.11, GOAL-015) ─────────
# L'API rend `live:<fin en secondes Unix>:<url>`. Un direct ne peut pas être
# une requête — la résolution d'un flux infini expire (docs/liquidsoap.md §5) —
# donc il passe par `input.http`, démarré dès l'instruction (un morceau
# d'avance, le temps qu'il se remplisse), mis à l'antenne **à la jonction**
# (`switch` sensible aux pistes), et coupé à l'heure dite. `self_sync=false` :
# sans lui, la rafale initiale du serveur accélère l'horloge de toute la
# sortie et le morceau en cours est avalé (docs/liquidsoap.md §5).
live_url = ref("")
live_entry = ref("")
live_pending = ref(false)
live = input.http(id="live", start=false, self_sync=false, max_buffer=3., {live_url()})

# Ce qu'il faut faire de l'avance quand le direct rend l'antenne. Un `ref` de
# fonction parce que `stop_live` est défini avant `programme` ; il est rempli
# plus bas, dès que `programme` existe.
vider_l_avance = ref(fun () -> ())

def stop_live(why) =
  if live_pending() then
    live_pending := false
    live.stop()
    log("le direct se termine : #{why}")
    # L'avance a dormi sous le direct : elle a été tirée à l'heure où la case
    # s'est ouverte, pas à celle où elle se ferme. C'est la même rassise que
    # celle d'une longue pause (SPECS.md §7 n°30), et le 2026-09-02 elle a
    # valu deux minutes de musique hors plage à 8 h.
    purger = vider_l_avance()
    purger()
  end
end

def start_live(entry) =
  parts = string.split(separator=":", entry)
  ends_at = float_of_string(default=0., list.nth(default="0", parts, 1))
  url = string.concat(separator=":", list.tl(list.tl(parts)))
  remaining = ends_at - time()
  if live_pending() then
    log(level=2, "un direct est déjà en cours, instruction ignorée")
  elsif remaining <= 0. then
    log(level=2, "direct déjà terminé à sa demande, ignoré")
  else
    live_url := url
    live_entry := entry
    live_pending := true
    live.start()
    log("direct demandé pour #{int_of_float(remaining)} s")
    thread.run(delay=remaining, {stop_live("heure de fin atteinte")})
  end
end

# Ce qui commence, pour l'API — l'entrée telle qu'elle l'a rendue.
live.on_track(fun (_) -> begin
  answer = http.post(timeout=api_timeout, data=live_entry(), "#{api}/playout/playing")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce du direct (#{answer.status_code})")
  end
end)

# ── Le morceau suivant : c'est l'API qui décide ─────────────────────────────
def ask_next() =
  answer = http.post(timeout=api_timeout, "#{api}/playout/next")
  if answer.status_code == 200 then
    failures := 0
    entry = string.trim(answer)
    # Sans la chaîne de requête : une URL de flux Subsonic porte le jeton d'accès
    # (docs/subsonic.md), et un journal n'est pas un endroit pour un secret.
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
    null()
  elsif string.contains(prefix="live:", entry) then
    # Un direct n'est pas une requête : on le lance, et on redemande tout de
    # suite le morceau réel, pour que la file ne soit jamais vide.
    start_live(entry)
    following = ask_next()
    if following == "" or string.contains(prefix="live:", following) then null()
    else request.create(following) end
  else
    request.create(entry)
  end
end

# prefetch=1 est le minimum : à 0 la source n'est jamais prête
# (docs/liquidsoap.md §3). Un morceau est donc toujours demandé d'avance.
programme = request.dynamic(id="programme", retry_delay=5., prefetch=1, next_entry)

# Ce qui COMMENCE, par opposition à ce qui a été demandé : c'est de là que
# l'API sait ce qui passe (GOAL-016-T08).
# L'annonce porte l'entrée, puis les étiquettes lues dans le fichier même :
# si `radio` a redémarré et ne reconnaît pas l'entrée, il affichera au moins
# ce que le décodeur sait — au lieu de rien pendant deux jonctions.
#
# Ce `ref` est aussi le **seul témoin fiable** qu'une piste passe (relevé
# docs/liquidsoap.md §9) : `radio` redémarré seul a perdu le sien, et croirait
# l'antenne vide alors que ce processus tient un morceau depuis la veille.
piste_commencee = ref(false)

def on_track(metadata) =
  piste_commencee := true
  body = metadata["initial_uri"] ^ "\n" ^ metadata["artist"] ^ "\n" ^ metadata["title"]
  answer = http.post(timeout=api_timeout, data=body, "#{api}/playout/playing")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce du morceau (#{answer.status_code})")
  end
end
programme.on_track(on_track)

# ── Passer le morceau en cours (SPECS.md §4.6, GOAL-017) ───────────────────
# C'est `radio` qui décide d'un saut — un vote `stop` accepté — et qui nous
# l'ordonne par cette route. Le saut porte sur la file des morceaux : pendant
# un direct ou un jingle, le noyau refuse le vote et l'ordre n'arrive jamais.
#
# Un saut à vide n'est PAS inoffensif : il reste enregistré et mange l'entrée
# fraîche dès son départ — 7 ms constatées, et la cascade avale l'instruction
# de direct qui suivait (docs/liquidsoap.md §9). D'où le refus ici plutôt
# qu'un garde-fou chez l'appelant, qui ne sait pas ce que ce processus tient.
def on_skip(request, response) =
  ignore(request)
  if piste_commencee() then
    log("saut demandé par l'API")
    programme.skip()
  else
    log("saut demandé à vide : rien ne passe, il mangerait le premier morceau")
  end
  response.data("passé")
end
harbor.http.register(port=port, method="POST", "/skip", on_skip)

# Un « encore » accepté vide le morceau d'avance (GOAL-034) : sans cela, la
# chanson déjà demandée s'intercalait et l'effet — jingle puis même artiste —
# n'arrivait qu'avec un morceau de retard, ce qui rendait le jingle étrange.
def on_requeue(request, response) =
  ignore(request)
  log("avance jetée sur ordre de l'API")
  programme.set_queue([])
  response.data("vidé")
end
harbor.http.register(port=port, method="POST", "/requeue", on_requeue)

# La purge de fin de direct, maintenant que `programme` existe. Le script ne
# choisit rien de plus qu'avant : il jette ce qui a rassis et **redemande** à
# l'API, qui décide seule (ARCHITECTURE.md §4).
vider_l_avance := fun () -> begin
  log("fin du direct : l'avance rassie est jetée, le reliquat coupé")
  programme.set_queue([])
  if piste_commencee() then programme.skip() end
end

programme = normalize(programme)
programme = crossfade(duration=2., fade_in=1., fade_out=1., programme)

# Le direct prend la main à la jonction, jamais au milieu d'un morceau
# (SPECS.md §4.11), et la rend dès qu'il s'arrête. APRÈS normalize et
# crossfade : ces opérateurs refusent une source qui contrôle sa propre
# latence, ce qu'est input.http — et `--check` ne le voit pas, seule
# l'exécution le dit (docs/liquidsoap.md §5).
on_air = switch(track_sensitive=true, [({live_pending() and live.is_ready()}, live), ({true}, programme)])

# ── Rien n'est décodé ni demandé sans auditeur (SPECS.md §1) ────────────────
listeners = ref(0)

def announce_count(count) =
  answer = http.post(timeout=api_timeout, data="#{count}", "#{api}/playout/listeners")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce des auditeurs (#{answer.status_code})")
  end
end

def announce() = announce_count(listeners()) end

# Et PÉRIODIQUEMENT, pas seulement aux branchements : si `radio` redémarre
# pendant que des auditeurs écoutent, son compteur repart à zéro et l'antenne
# s'affiche vide alors qu'elle joue — constaté le 2026-08-30. Quinze secondes
# de battement ressoudent l'état sans que personne ne s'en aperçoive.
thread.run(every=15., announce)

# L'annonce part AVANT la bascule du compteur : tant que le ref est à zéro,
# l'antenne reste sur blank(), et l'API peut purger une avance rassise sans
# course avec la reprise du son (docs/liquidsoap.md §5.bis, SPECS.md §7 n°30).
def on_connect(~headers, ~uri, ~protocol, ip) =
  ignore(headers) ignore(uri) ignore(protocol)
  announce_count(listeners() + 1)
  listeners := listeners() + 1
  log("auditeur #{ip} branché — #{listeners()} à l'écoute")
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
antenne_prise = ref(0.)

def prise_antenne(_, b) =
  antenne_prise := time()
  b
end

def rendre_antenne(_, b) = b end

on_air = switch(track_sensitive=false, transitions=[prise_antenne, rendre_antenne],
                [({listeners() > 0}, on_air), ({true}, blank())])

def gain_antenne() =
  d = time() - antenne_prise()
  if d >= duree_fondu then 1. elsif d < 0. then 0. else d / duree_fondu end
end

on_air = amplify(gain_antenne, on_air)

output.harbor(
  %mp3(bitrate=bitrate),
  port=port, mount=mount,
  headers=[("icy-name", name), ("icy-br", "#{bitrate}")],
  on_connect=on_connect, on_disconnect=on_disconnect,
  on_air
)
