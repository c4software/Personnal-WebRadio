#!/usr/bin/env python3
"""Fabrique les génériques de plage : une voix de synthèse sur un lit musical.

**Cet outil ne fait pas partie de la radio.** Il produit des fichiers, une fois,
et le programme ne l'importe jamais : les jingles sont des données, pas du code
(SPECS.md §4.3). Il vit ici pour qu'on puisse refaire la série après avoir changé
un texte, plutôt que de la retrouver un an plus tard sans savoir comment elle a
été faite.

**Il tourne dans un conteneur**, lancé par `outils/generer-jingles.sh` : ses deux
dépendances — `ffmpeg` et `edge-tts` — vivent dans l'image `outils/Dockerfile`
et nulle part sur la machine. Rien n'oblige à faire autrement, mais rien ne
l'empêche non plus : les deux chemins qu'il écrit se règlent par
l'environnement.

Le lit musical est **synthétisé** par ffmpeg, note par note (`aevalsrc`) : rien
n'est téléchargé, rien n'est sous licence. C'est aussi pourquoi il sonne
« électronique » — c'est un habillage de station, pas de la musique.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# ── Ce qui se règle ────────────────────────────────────────────────────────
VOICE = "fr-FR-HenriNeural"  # `edge-tts --list-voices | grep fr-FR` pour les autres
RATE = "-4%"  # un rien plus lent que la vitesse par défaut : on est à l'antenne
# Les deux seuls chemins écrits, et le conteneur les fournit tous les deux :
# `/sortie` est le volume monté sur `jingles/bands/`, le montage reste dans le
# `/tmp` du conteneur et meurt avec lui.
OUTPUT = Path(os.environ.get("JINGLES_OUTPUT", "jingles/bands"))
WORK = Path(os.environ.get("JINGLES_WORK", "/tmp/jingles-montage"))
LEAD_IN = 0.9  # le lit attaque seul avant la voix
TAIL = 1.4  # et se termine seul après elle
LOUDNESS = "I=-16:TP=-1.5:LRA=11"  # le niveau habituel d'une webradio

# Une note tenue est ajoutée sous chaque générique pour que le lit ne meure pas
# avant la voix : les habillages ci-dessous n'ont donc pas à couvrir la durée.
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def frequency(note: str) -> float:
    """« A4 » → 440 Hz. Le tempérament égal, rien de plus."""
    name, octave = note[:-1], int(note[-1])
    return 440.0 * (2 ** ((NOTES.index(name) + 12 * (octave - 4) - 9) / 12))


def waveform(kind: str, note: str, decay: float) -> str:
    """L'expression `aevalsrc` d'une note : un timbre, une enveloppe.

    L'attaque (`1-exp(-t*80)`) évite le clic de début que produirait une onde
    démarrant à pleine amplitude ; la décroissance fait le reste du caractère.
    """
    if kind == "kick":
        return "(sin(2*PI*t*(55+70*exp(-t*28)))*exp(-t*9))"
    f = frequency(note)
    timbres = {
        "sine": f"sin(2*PI*{f:.3f}*t)",
        # Deux harmoniques qui s'éteignent plus vite que la fondamentale : une cloche.
        "bell": (
            f"(sin(2*PI*{f:.3f}*t)+0.5*sin(2*PI*{2 * f:.3f}*t)*exp(-6*t)"
            f"+0.25*sin(2*PI*{3 * f:.3f}*t)*exp(-10*t))"
        ),
        "saw": f"(2*({f:.3f}*t-floor(0.5+{f:.3f}*t)))",
        # `tanh` plutôt qu'un vrai carré : ffmpeg refuse `if(gt(...))` dans aevalsrc.
        "square": f"(tanh(6*sin(2*PI*{f:.3f}*t)))",
        # Un battement volontaire (2,01 au lieu de 2) : la nappe respire.
        "pad": (
            f"(sin(2*PI*{f:.3f}*t)+0.4*sin(2*PI*{f * 2.01:.3f}*t)+0.2*sin(2*PI*{f * 0.5:.3f}*t))"
        ),
    }
    return f"({timbres[kind]}*(1-exp(-t*80))*exp(-t*{decay}))"


# Une note du lit : début, durée, timbre, hauteur (None pour la grosse caisse),
# décroissance, volume.
Note = tuple[float, float, str, str | None, float, float]


def arpeggio(
    pitches: Sequence[str],
    start: float = 0.0,
    step: float = 0.18,
    length: float = 1.6,
    kind: str = "bell",
    decay: float = 3.0,
    volume: float = 0.5,
) -> list[Note]:
    """Des notes égrenées : chacune part `step` après la précédente."""
    return [(start + i * step, length, kind, p, decay, volume) for i, p in enumerate(pitches)]


def chord(
    pitches: Sequence[str],
    start: float,
    length: float = 2.2,
    kind: str = "pad",
    decay: float = 1.6,
    volume: float = 0.34,
) -> list[Note]:
    """Des notes ensemble."""
    return [(start, length, kind, p, decay, volume) for p in pitches]


def run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True)


def duration(path: Path) -> float:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(probe.stdout)["format"]["duration"])


def render_bed(name: str, notes: Sequence[Note], length: float, lowpass: int | None) -> Path:
    """Le lit musical seul, rendu en WAV à la longueur exacte du générique.

    Une entrée `lavfi` par note, puis un `amix` : c'est verbeux, mais chaque note
    garde son timbre, son enveloppe et son volume — ce qu'une expression unique
    ne permettrait pas de relire.
    """
    inputs: list[str] = []
    chains: list[str] = []
    labels: list[str] = []
    for index, (start, span, kind, pitch, decay, volume) in enumerate(notes):
        expression = waveform(kind, pitch or "A4", decay)
        inputs += ["-f", "lavfi", "-i", f"aevalsrc={expression}:d={min(span, length):.2f}:s=44100"]
        chains.append(f"[{index}:a]volume={volume},adelay={int(start * 1000)}[n{index}]")
        labels.append(f"[n{index}]")
    graph = ";".join(chains) + ";" + "".join(labels) + f"amix=inputs={len(notes)}:normalize=0"
    if lowpass:
        # Une scie brute est agressive : on lui coupe le haut du spectre.
        graph += f",lowpass=f={lowpass}"
    graph += (
        ",aecho=0.8:0.85:60|130:0.26|0.14,pan=stereo|c0=c0|c1=c0"
        f",apad=whole_dur={length:.2f},atrim=0:{length:.2f}"
        f",afade=t=in:st=0:d=0.05,afade=t=out:st={length - 1.1:.2f}:d=1.1,alimiter=limit=0.9"
    )
    bed = WORK / f"{name}-lit.wav"
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
        "-filter_complex", graph, "-ar", "44100", str(bed))  # fmt: skip
    return bed


def render_jingle(
    name: str, text: str, notes: Sequence[Note], drone: str, lowpass: int | None
) -> Path:
    """La voix, le lit, et le lit qui s'efface sous la voix."""
    voice = WORK / f"{name}-voix.mp3"
    run("edge-tts", "--voice", VOICE, f"--rate={RATE}", "--text", text, "--write-media", str(voice))
    length = duration(voice) + LEAD_IN + TAIL
    bed = render_bed(name, [*notes, (0.0, length, "pad", drone, 0.30, 0.13)], length, lowpass)
    delay = int(LEAD_IN * 1000)
    # `sidechaincompress` : le lit baisse tout seul quand la voix parle, et
    # remonte quand elle s'arrête. C'est le geste de base d'un habillage radio.
    graph = (
        f"[1:a]adelay={delay}|{delay},aformat=channel_layouts=stereo,highpass=f=90,"
        "acompressor=threshold=0.1:ratio=3:attack=15:release=250,volume=3.0[v];"
        "[v]asplit=2[v1][sc];"
        "[0:a][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=500[bd];"
        f"[bd][v1]amix=inputs=2:normalize=0,apad=whole_dur={length:.2f},atrim=0:{length:.2f},"
        f"loudnorm={LOUDNESS},alimiter=limit=0.95"
    )
    target = OUTPUT / f"{name}.mp3"
    run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(bed), "-i", str(voice),
        "-filter_complex", graph, "-ar", "44100", "-b:a", "192k", str(target))  # fmt: skip
    return target


# ── La série ───────────────────────────────────────────────────────────────
# Un nom de fichier → le texte dit, le lit musical, la note tenue dessous, et
# la coupure du haut du spectre si le lit est agressif. Les noms sont ceux que
# `webradio.toml` déclare en `intro` : les changer ici oblige à les y changer.
JINGLES: dict[str, tuple[str, list[Note], str, int | None]] = {
    "aube": (
        "Il est cinq heures. La nuit se retire.",
        chord(["C3", "G3", "C4"], 0.0, 3.0, "pad", 0.9, 0.30)
        + arpeggio(["E4", "G4", "D5"], 0.4, 0.5, 2.2, "bell", 2.2, 0.26),
        "C3",
        None,
    ),
    "matinale": (
        "La matinale. Des chansons françaises pour se lever.",
        [
            *arpeggio(["C4", "E4", "G4"], 0.0, 0.16, 1.2, "bell", 3.5, 0.34),
            (0.48, 2.4, "bell", "C5", 1.8, 0.36),
        ],
        "C3",
        None,
    ),
    "cafe": (
        "Neuf heures, le café serré. Jazz et soul.",
        arpeggio(["D4", "F#4", "A4", "C#5", "E5"], 0.0, 0.13, 1.5, "bell", 3.0, 0.30),
        "D3",
        None,
    ),
    "table": (
        "Midi. À table. Pop et folk, rien qui coupe l'appétit.",
        chord(["F3", "A3", "C4"], 0.0, 1.1, "pad", 2.2, 0.24)
        + chord(["G3", "B3", "D4"], 0.7, 1.6, "pad", 1.8, 0.24)
        + arpeggio(["F4", "A4", "C5"], 0.7, 0.15, 1.4, "bell", 3.0, 0.28),
        "F2",
        None,
    ),
    "carte-blanche": (
        "Carte blanche. Une heure, un seul artiste, tiré au sort.",
        [
            *arpeggio(["C4", "D4", "E4", "F#4", "G#4", "A#4"], 0.0, 0.12, 1.2, "bell", 4.0, 0.28),
            (0.72, 2.2, "bell", "C5", 1.6, 0.34),
        ],
        "C3",
        None,
    ),
    "contretemps": (
        "Quinze heures, l'heure du contretemps. Reggae et dub.",
        [
            (t, 0.35, "square", n, 9.0, 0.13)
            for t, n in (
                (0.25, "A3"),
                (0.25, "C4"),
                (0.25, "E4"),
                (0.75, "A3"),
                (0.75, "C4"),
                (0.75, "E4"),
                (1.25, "G3"),
                (1.25, "B3"),
                (1.25, "D4"),
            )
        ]
        + [(1.6, 2.0, "bell", "A4", 2.0, 0.28)],
        "A2",
        3600,
    ),
    "mystere": (
        "Un genre au hasard, et on s'y tient une heure.",
        [
            *arpeggio(["G4", "G#4", "A4"], 0.0, 0.22, 1.4, "bell", 3.2, 0.3),
            (0.9, 2.4, "bell", "D5", 1.5, 0.32),
        ],
        "D3",
        None,
    ),
    "retour": (
        "Dix-sept heures, le retour. Rap, slam, hip-hop.",
        [
            (0.0, 0.6, "kick", None, 0.0, 0.55),
            (0.5, 0.6, "kick", None, 0.0, 0.42),
            (1.1, 0.6, "kick", None, 0.0, 0.55),
            (0.0, 1.0, "saw", "E2", 3.0, 0.15),
            (1.1, 1.8, "saw", "G2", 2.0, 0.15),
            *arpeggio(["E4", "G4", "B4"], 1.15, 0.14, 1.4, "bell", 3.0, 0.24),
        ],
        "E2",
        3200,
    ),
    "guitares": (
        "Vingt heures. Guitares.",
        [(0.0, 1.0, "saw", n, 2.2, 0.15) for n in ("E2", "B2", "E3")]
        + [(1.0, 2.2, "saw", n, 1.4, 0.15) for n in ("G2", "D3", "G3")]
        + arpeggio(["B4", "E5"], 1.05, 0.16, 1.6, "bell", 2.6, 0.24),
        "E2",
        2600,
    ),
    "electrique": (
        "Le soir électrique.",
        [
            (i * 0.16, 0.3, "saw", n, 7.0, 0.15)
            for i, n in enumerate(["A3", "E4", "A4", "C5", "E5", "A4", "E4", "C5"])
        ]
        + [(1.28, 2.2, "bell", "A5", 1.6, 0.26)],
        "A2",
        4000,
    ),
    "velours": (
        "Fin de soirée. Voix et velours.",
        chord(["F2", "C3", "G#3", "C4", "G4"], 0.0, 3.4, "pad", 0.7, 0.20)
        + arpeggio(["C5", "G4", "D#4"], 0.5, 0.55, 2.4, "bell", 1.8, 0.22),
        "F2",
        None,
    ),
    "nuit": (
        "Une heure du matin. La nuit, et presque rien.",
        [
            *chord(["C2", "G2", "C3", "D#3"], 0.0, 4.0, "pad", 0.5, 0.22),
            (1.2, 3.0, "bell", "G4", 1.0, 0.18),
        ],
        "C2",
        None,
    ),
    "enfants": (
        "C'est le week-end. La maison se réveille avec des enfants dedans.",
        [
            *arpeggio(["C5", "D5", "E5", "G5", "A5", "C6"], 0.0, 0.15, 1.4, "bell", 3.4, 0.3),
            (0.9, 2.0, "bell", "G5", 2.0, 0.32),
        ],
        "C3",
        None,
    ),
    "brunch": (
        "Le brunch du dimanche.",
        [
            (t, 0.5, "saw", n, 6.0, 0.13)
            for t, n in (
                (0.0, "C4"),
                (0.0, "E4"),
                (0.0, "G4"),
                (0.4, "D4"),
                (0.4, "F4"),
                (0.4, "A4"),
                (0.8, "E4"),
                (0.8, "G4"),
                (0.8, "C5"),
            )
        ]
        + [(1.3, 2.2, "bell", "C5", 1.8, 0.28)],
        "C3",
        3000,
    ),
    "samedi-soir": (
        "Samedi soir. On pousse le son jusqu'à deux heures.",
        [(i * 0.5, 0.6, "kick", None, 0.0, 0.5) for i in range(4)]
        + [
            (t, 0.3, "saw", n, 8.0, 0.13)
            for t in (0.25, 0.75, 1.25, 1.75)
            for n in ("F3", "G#3", "C4")
        ]
        + [(2.0, 2.4, "bell", "C5", 1.6, 0.28)],
        "F2",
        3400,
    ),
}


def main(wanted: Sequence[str]) -> int:
    """Toute la série, ou seulement les génériques nommés en argument."""
    unknown = [name for name in wanted if name not in JINGLES]
    if unknown:
        print(f"générique inconnu : {', '.join(unknown)}", file=sys.stderr)
        print(f"connus : {', '.join(JINGLES)}", file=sys.stderr)
        return 2
    OUTPUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    for name in wanted or list(JINGLES):
        text, notes, drone, lowpass = JINGLES[name]
        target = render_jingle(name, text, notes, drone, lowpass)
        print(f"{target}  {duration(target):.1f} s  « {text} »")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
