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

# ── Le morceau suivant : c'est l'API qui décide ─────────────────────────────
def next_entry() =
  answer = http.post(timeout=api_timeout, "#{api}/playout/next")
  if answer.status_code == 200 then
    failures := 0
    entry = string.trim(answer)
    log("suivant : #{entry}")
    request.create(entry)
  elsif answer.status_code == 204 then
    stop_saying_why("l'API n'a plus rien à jouer")
    null()
  else
    failures := failures() + 1
    log(level=2, "l'API ne répond pas (#{answer.status_code} #{answer.status_message}), essai #{failures()}")
    if failures() >= 2 then stop_saying_why("l'API ne répond plus") end
    null()
  end
end

# prefetch=1 est le minimum : à 0 la source n'est jamais prête
# (docs/liquidsoap.md §3). Un morceau est donc toujours demandé d'avance.
programme = request.dynamic(id="programme", retry_delay=5., prefetch=1, next_entry)
programme = normalize(programme)
programme = crossfade(duration=2., fade_in=1., fade_out=1., programme)

# ── Rien n'est décodé ni demandé sans auditeur (SPECS.md §1) ────────────────
listeners = ref(0)

def announce() =
  answer = http.post(timeout=api_timeout, data="#{listeners()}", "#{api}/playout/listeners")
  if answer.status_code != 204 then
    log(level=2, "l'API n'a pas pris l'annonce des auditeurs (#{answer.status_code})")
  end
end

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

on_air = switch(track_sensitive=false, [({listeners() > 0}, programme), ({true}, blank())])

output.harbor(
  %mp3(bitrate=bitrate),
  port=port, mount=mount,
  headers=[("icy-name", name), ("icy-br", "#{bitrate}")],
  on_connect=on_connect, on_disconnect=on_disconnect,
  on_air
)
