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

def stop_live(why) =
  if live_pending() then
    live_pending := false
    live.stop()
    log("le direct se termine : #{why}")
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
    # Sans la chaîne de requête : une URL Navidrome porte le jeton d'accès
    # (docs/navidrome.md), et un journal n'est pas un endroit pour un secret.
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
def on_track(metadata) =
  body = metadata["initial_uri"] ^ "\n" ^ metadata["artist"] ^ "\n" ^ metadata["title"]
  answer = http.post(timeout=api_timeout, data=body, "#{api}/playout/playing")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce du morceau (#{answer.status_code})")
  end
end
programme.on_track(on_track)
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

def announce() =
  answer = http.post(timeout=api_timeout, data="#{listeners()}", "#{api}/playout/listeners")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce des auditeurs (#{answer.status_code})")
  end
end

# Et PÉRIODIQUEMENT, pas seulement aux branchements : si `radio` redémarre
# pendant que des auditeurs écoutent, son compteur repart à zéro et l'antenne
# s'affiche vide alors qu'elle joue — constaté le 2026-08-30. Quinze secondes
# de battement ressoudent l'état sans que personne ne s'en aperçoive.
thread.run(every=15., announce)

def on_connect(~headers, ~uri, ~protocol, ip) =
  ignore(headers) ignore(uri) ignore(protocol)
  listeners := listeners() + 1
  log("auditeur #{ip} branché — #{listeners()} à l'écoute")
  announce()
end

def on_disconnect(ip) =
  listeners := listeners() - 1
  log("auditeur #{ip} parti — #{listeners()} à l'écoute")
  announce()
end

on_air = switch(track_sensitive=false, [({listeners() > 0}, on_air), ({true}, blank())])

output.harbor(
  %mp3(bitrate=bitrate),
  port=port, mount=mount,
  headers=[("icy-name", name), ("icy-br", "#{bitrate}")],
  on_connect=on_connect, on_disconnect=on_disconnect,
  on_air
)
