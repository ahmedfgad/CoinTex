"""Generate CoinTex background music by rendering MIDI through a GM soundfont.

This replaces the pure-numpy synth (tools/gen_world_music.py), whose summed
harmonics + feedback delay + soft-clipping produced audible buzz/hiss on
sustained, overlapping voices. Here every note is a *recorded* General-MIDI
instrument sample played by FluidSynth, so there is no synthesis noise.

Pipeline per track:
  1. compose the part list (pad / melody / bass / drums) on a beat grid,
  2. write a tiny Standard MIDI File (pure stdlib — no python deps),
  3. render to 44.1 kHz WAV with `fluidsynth <soundfont> <midi>`,
  4. downmix to mono, fold the reverb tail back onto the head for a seamless
     loop, normalize, and write a 16-bit mono WAV into music/.

Dev/build-time only. Requires the `fluidsynth` binary and a GM soundfont
(default: /usr/share/sounds/sf2/default-GM.sf2). numpy is used only here, not
at runtime (audio.py just loads the shipped WAVs).

Usage:
    python tools/gen_world_music_sf2.py [--out music] [--only world3,piano_flute]
                                        [--soundfont /path/to.sf2]
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import tempfile
import wave

import numpy as np

SAMPLE_RATE = 44100
LOOP_SECONDS = 20.0          # nominal target; actual length snaps to whole bars
TICKS_PER_BEAT = 480
REVERB_TAIL_S = 2.2          # extra render time so the reverb tail is captured
DEFAULT_OUT = "music"
DEFAULT_SF2 = "/usr/share/sounds/sf2/default-GM.sf2"

# General MIDI program numbers (0-indexed) used below.
PIANO, CELESTA, MUSIC_BOX, VIBES, MARIMBA = 0, 8, 10, 11, 12
NYLON_GTR, STEEL_GTR = 24, 25
AC_BASS, FINGER_BASS, SYNTH_BASS = 32, 33, 38
STRINGS, SYNTH_STRINGS, HARP = 48, 50, 46
BRASS, FRENCH_HORN, OBOE, FLUTE = 61, 60, 68, 73
SYNTH_LEAD_SAW, WARM_PAD = 81, 89
DRUM_CH = 9                  # GM percussion channel (MIDI channel 10)
KICK, SNARE, HAT = 36, 38, 42


def bars_for(bpm: float, beats_per_bar: int = 4) -> int:
    bar_sec = 60.0 / bpm * beats_per_bar
    return max(1, round(LOOP_SECONDS / bar_sec))


def total_beats(bpm: float) -> int:
    return bars_for(bpm) * 4


# --------------------------------------------------------------------------
# Composition helpers — all return note lists of (start_beat, dur_beats, midi)
# --------------------------------------------------------------------------

def tile_chords(block, total, block_len=16):
    """Expand a chord progression [(off, dur, [midis])] tiled to `total` beats."""
    out = []
    for blk in range(0, int(total), block_len):
        for off, dur, midis in block:
            if blk + off < total:
                for m in midis:
                    out.append((blk + off, dur, m))
    return out


def tile_mel(motif, total, block_len=16, octave_alt=False):
    """Tile a single-line motif [(off, dur, midi)] across `total` beats."""
    out = []
    for i, blk in enumerate(range(0, int(total), block_len)):
        lift = 12 if (octave_alt and i % 2) else 0
        for off, dur, m in motif:
            if blk + off < total:
                out.append((blk + off, dur, m + lift))
    return out


def tile_arp(seq, total, bar=4, step=0.5):
    out = []
    for b in range(0, int(total), bar):
        for i, m in enumerate(seq):
            if b + i * step < total:
                out.append((b + i * step, step, m))
    return out


def bass_per_bar(roots, total):
    """One held root per 4-beat bar, cycling through `roots`."""
    out = []
    for i, b in enumerate(range(0, int(total), 4)):
        if b < total:
            out.append((b, 4, roots[i % len(roots)]))
    return out


def basic_beat(total):
    pat = []
    for b in range(int(total)):
        pat.append((b, 0.1, KICK if b % 2 == 0 else SNARE))
        pat.append((b, 0.1, HAT))
        pat.append((b + 0.5, 0.1, HAT))
    return pat


# --------------------------------------------------------------------------
# Track definitions — each returns (bpm, parts) where a part is a dict:
#   {ch, prog, vel, notes}.  ch == DRUM_CH renders on the GM drum kit.
# --------------------------------------------------------------------------

def build_piano_flute():
    """Gentle piano + flute title theme — D major I-V-vi-IV."""
    bpm = 82.0
    T = total_beats(bpm)
    prog = [(0, 4, [62, 66, 69]), (4, 4, [57, 61, 64]),
            (8, 4, [59, 62, 66]), (12, 4, [55, 59, 62])]
    pad = tile_chords(prog, T)
    arp = [62, 66, 69, 74, 69, 66, 57, 61, 64, 69, 64, 61,
           59, 62, 66, 71, 66, 62, 55, 59, 62, 67, 62, 59]
    step = 16.0 / len(arp)
    piano = [(blk + i * step, step, m) for blk in range(0, T, 16)
             for i, m in enumerate(arp) if blk + i * step < T]
    fmotif = [(0, 2, 78), (2, 2, 76), (4, 2, 73), (6, 2, 74),
              (8, 2, 76), (10, 2, 74), (12, 3, 69), (15, 1, 71)]
    flute = tile_mel(fmotif, T)
    parts = [
        {"ch": 0, "prog": STRINGS, "vel": 42, "notes": pad},
        {"ch": 1, "prog": PIANO,   "vel": 70, "notes": piano},
        {"ch": 2, "prog": FLUTE,   "vel": 92, "notes": flute},
    ]
    return bpm, parts


def build_world1():
    """Meadow — cheerful pastoral bounce, A major (A/E/F#m/D)."""
    bpm = 108.0
    T = total_beats(bpm)
    prog = [(0, 4, [57, 61, 64]), (4, 4, [52, 56, 59]),
            (8, 4, [54, 57, 61]), (12, 4, [50, 54, 57])]
    pad = tile_chords(prog, T)
    motif = [(0, 1, 69), (1, 1, 73), (2, 1, 76), (3, 1, 73), (4, 1, 71),
             (5, 1, 68), (6, 2, 64), (8, 1, 69), (9, 1, 66), (10, 2, 69),
             (12, 1, 62), (13, 1, 66), (14, 2, 69)]
    lead = tile_mel(motif, T, octave_alt=True)
    bass = bass_per_bar([45, 40, 42, 38], T)
    parts = [
        {"ch": 0, "prog": STRINGS, "vel": 40, "notes": pad},
        {"ch": 1, "prog": MARIMBA, "vel": 92, "notes": lead},
        {"ch": 2, "prog": AC_BASS, "vel": 80, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 88, "notes": basic_beat(T)},
    ]
    return bpm, parts


def build_world2():
    """Desert — exotic groove, D harmonic minor, oboe lead + hand percussion."""
    bpm = 96.0
    T = total_beats(bpm)
    prog = [(0, 4, [50, 53, 57]), (4, 4, [55, 58, 62]),
            (8, 4, [57, 61, 64]), (12, 4, [50, 53, 57])]
    pad = tile_chords(prog, T, block_len=16)
    mel = [(0, 0.75, 74), (0.75, 0.25, 73), (1, 1, 70), (2, 1, 69), (3, 1, 67),
           (4, 1.5, 73), (5.5, 0.5, 74), (6, 2, 69), (8, 1, 65), (9, 1, 67),
           (10, 2, 70), (12, 0.5, 73), (12.5, 0.5, 74), (13, 1, 77), (14, 2, 74)]
    lead = tile_mel(mel, T)
    bass = bass_per_bar([38, 43, 45, 38], T)
    # hand-percussion feel: kick + busy hats, sparse snare
    pat = []
    for b in range(int(T)):
        pat.append((b, 0.1, KICK))
        pat.append((b + 0.5, 0.1, HAT))
        pat.append((b + 0.75, 0.1, HAT))
        if b % 4 == 2:
            pat.append((b, 0.1, SNARE))
    parts = [
        {"ch": 0, "prog": SYNTH_STRINGS, "vel": 38, "notes": pad},
        {"ch": 1, "prog": OBOE,          "vel": 88, "notes": lead},
        {"ch": 2, "prog": AC_BASS,       "vel": 62, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 84, "notes": pat},
    ]
    return bpm, parts


def build_world3():
    """Ocean — bright flowing aquatic, D major, vibraphone arp + soft sway."""
    bpm = 90.0
    T = total_beats(bpm)
    prog = [(0, 4, [50, 57, 62]), (4, 4, [47, 54, 59]),
            (8, 4, [43, 50, 55]), (12, 4, [45, 52, 57])]
    pad = tile_chords(prog, T)
    arp = tile_arp([62, 66, 69, 74, 71, 69, 66, 62], T)
    bass = bass_per_bar([38, 35, 31, 33], T)
    pat = [(b, 0.1, KICK) for b in range(0, int(T), 2)]
    pat += [(b + 0.5, 0.1, HAT) for b in range(int(T))]
    parts = [
        {"ch": 0, "prog": WARM_PAD,    "vel": 40, "notes": pad},
        {"ch": 1, "prog": VIBES,       "vel": 82, "notes": arp},
        {"ch": 2, "prog": FINGER_BASS, "vel": 70, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 64, "notes": pat},
    ]
    return bpm, parts


def build_world4():
    """Cavern — dark driving action: pulsing bass, gritty riff, charging drums."""
    bpm = 124.0
    T = total_beats(bpm)
    # E natural minor (dark): Em C G D pads, kept low as atmosphere under the riff
    prog = [(0, 4, [52, 55, 59]), (4, 4, [48, 52, 55]),
            (8, 4, [55, 59, 62]), (12, 4, [50, 54, 57])]
    pad = tile_chords(prog, T)
    # driving E-minor-pentatonic riff (synth lead), one bar tiled across the loop
    riff = [(0, 0.5, 64), (0.5, 0.5, 67), (1, 0.5, 71), (1.5, 0.5, 67),
            (2, 0.5, 69), (2.5, 0.5, 67), (3, 0.5, 64), (3.5, 0.5, 62)]
    lead = [(bar + b, d, m) for bar in range(0, int(T), 4)
            for (b, d, m) in riff if bar + b < T]
    # pulsing syncopated bass (E minor) for forward drive
    bnote = [(0, 0.5, 40), (0.5, 0.5, 40), (1.5, 0.5, 40), (2, 0.5, 43),
             (2.5, 0.5, 40), (3, 0.5, 38), (3.5, 0.5, 42)]
    bass = [(bar + b, d, m) for bar in range(0, int(T), 4)
            for (b, d, m) in bnote if bar + b < T]
    # charging beat: kick every beat, snare backbeat, 8th hats
    pat = []
    for b in range(int(T)):
        pat.append((b, 0.1, KICK))
        if b % 2 == 1:
            pat.append((b, 0.1, SNARE))
        pat.append((b + 0.5, 0.1, HAT))
    parts = [
        {"ch": 0, "prog": STRINGS,        "vel": 42, "notes": pad},
        {"ch": 1, "prog": SYNTH_LEAD_SAW, "vel": 86, "notes": lead},
        {"ch": 2, "prog": FINGER_BASS,    "vel": 92, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 100, "notes": pat},
    ]
    return bpm, parts


def build_world5():
    """Volcano — heroic action march, D Mixolydian, brass + power chords."""
    bpm = 132.0
    T = total_beats(bpm)
    prog = [(0, 4, [50, 57, 62]), (4, 4, [48, 55, 60]),
            (8, 4, [43, 50, 55]), (12, 4, [45, 52, 57])]
    pad = tile_chords(prog, T, block_len=16)
    mel = [(0, 1, 62), (1, 1, 64), (2, 1, 66), (3, 1, 69), (4, 2, 71),
           (6, 2, 67), (8, 1, 69), (9, 1, 71), (10, 1, 72), (11, 1, 74),
           (12, 2, 76), (14, 2, 69)]
    brass = tile_mel(mel, T)
    bass = bass_per_bar([38, 36, 31, 33], T)
    pat = []
    for b in range(int(T)):
        pat.append((b, 0.1, KICK))
        if b % 2 == 1:
            pat.append((b, 0.1, SNARE))
        pat.append((b + 0.5, 0.1, HAT))
    parts = [
        {"ch": 0, "prog": STRINGS, "vel": 52, "notes": pad},
        {"ch": 1, "prog": BRASS,   "vel": 100, "notes": brass},
        {"ch": 2, "prog": AC_BASS, "vel": 82, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 95, "notes": pat},
    ]
    return bpm, parts


def build_world6():
    """Cosmos — dreamy synthwave, Cmaj7/Am/F/G, shimmering arp + round bass."""
    bpm = 88.0
    T = total_beats(bpm)
    prog = [(0, 4, [60, 64, 67, 71]), (4, 4, [57, 60, 64]),
            (8, 4, [53, 57, 60]), (12, 4, [55, 59, 62])]
    pad = tile_chords(prog, T, block_len=16)
    arp = tile_arp([72, 76, 79, 76, 71, 74, 79, 74], T)
    bass = bass_per_bar([36, 33, 29, 31], T)
    pat = []
    for b in range(int(T)):
        pat.append((b, 0.1, KICK))
        if b % 2 == 1:
            pat.append((b, 0.1, SNARE))
    parts = [
        {"ch": 0, "prog": WARM_PAD,       "vel": 42, "notes": pad},
        {"ch": 1, "prog": SYNTH_LEAD_SAW, "vel": 74, "notes": arp},
        {"ch": 2, "prog": SYNTH_BASS,     "vel": 72, "notes": bass},
        {"ch": DRUM_CH, "prog": 0, "vel": 66, "notes": pat},
    ]
    return bpm, parts


# --------------------------------------------------------------------------
# Minimal Standard MIDI File writer (format 1, pure stdlib)
# --------------------------------------------------------------------------

def _vlq(n: int) -> bytes:
    """Variable-length quantity encoding for MIDI delta times."""
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _track_chunk(events) -> bytes:
    """events: list of (abs_tick, status_byte, data1, data2). Sorted, delta-encoded.

    Program-change/channel-pressure (0xC0/0xD0) are 2-byte messages; everything
    else (note on/off) is 3 bytes. Writing the wrong length desyncs the parser.
    """
    events = sorted(events, key=lambda e: (e[0], 0 if e[1] & 0xF0 == 0x80 else 1))
    body = bytearray()
    last = 0
    for tick, status, d1, d2 in events:
        if status & 0xF0 in (0xC0, 0xD0):
            msg = bytes([status, d1])
        else:
            msg = bytes([status, d1, d2])
        body += _vlq(tick - last) + msg
        last = tick
    body += _vlq(0) + b"\xFF\x2F\x00"        # end of track
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(path: str, bpm: float, parts) -> None:
    tpb = TICKS_PER_BEAT
    inst_chunks = []
    max_tick = 0
    for p in parts:
        ch = p["ch"]
        ev = [(0, 0xC0 | ch, p["prog"], 0)]   # program change (2-byte msg)
        for start, dur, midi in p["notes"]:
            on = int(round(start * tpb))
            off = int(round((start + dur) * tpb))
            ev.append((on, 0x90 | ch, int(midi), p["vel"]))
            ev.append((off, 0x80 | ch, int(midi), 0))
            max_tick = max(max_tick, off)
        inst_chunks.append(_track_chunk(ev))

    # Tempo track: set tempo at tick 0, then hold end-of-track past the last
    # note so FluidSynth keeps rendering the reverb tail (no leading silence,
    # correct tempo — both were bugs before).
    us = int(round(60_000_000 / bpm))
    tail_ticks = max_tick + int(REVERB_TAIL_S * bpm / 60.0 * tpb)
    tempo = bytearray(_vlq(0) + b"\xFF\x51\x03" + struct.pack(">I", us)[1:])
    tempo += _vlq(tail_ticks) + b"\xFF\x2F\x00"
    tempo_trk = b"MTrk" + struct.pack(">I", len(tempo)) + bytes(tempo)

    track_chunks = [tempo_trk] + inst_chunks
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(track_chunks), tpb)
    with open(path, "wb") as f:
        f.write(header)
        for c in track_chunks:
            f.write(c)


# --------------------------------------------------------------------------
# Render + post-process
# --------------------------------------------------------------------------

def render_midi(midi_path: str, wav_path: str, soundfont: str) -> None:
    cmd = [
        "fluidsynth", "-ni", "-C", "0",          # chorus off (avoids wobble)
        "-g", "0.7", "-r", str(SAMPLE_RATE),
        "-F", wav_path, soundfont, midi_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def read_wav_mono(path: str) -> np.ndarray:
    with wave.open(path, "rb") as w:
        ch, sw, fr, nf = (w.getnchannels(), w.getsampwidth(),
                          w.getframerate(), w.getnframes())
        raw = w.readframes(nf)
    assert sw == 2, "expected 16-bit PCM from fluidsynth"
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data


def seamless_loop(mono: np.ndarray, loop_samples: int,
                  fade_s: float = 0.04) -> np.ndarray:
    """Take `loop_samples` as the body and fold the post-loop reverb tail onto
    its head, then equal-power crossfade the seam so it wraps cleanly."""
    loop_samples = min(loop_samples, mono.shape[0])
    body = mono[:loop_samples].copy()
    tail = mono[loop_samples:]
    if tail.shape[0]:
        k = min(tail.shape[0], body.shape[0])
        body[:k] += tail[:k]
    f = min(int(fade_s * SAMPLE_RATE), body.shape[0] // 4)
    if f > 0:
        head = body[:f].copy()
        out = body[f:].copy()
        fade_out = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
        fade_in = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
        out[-f:] = out[-f:] * fade_out + head * fade_in
        return out
    return body


def normalize(x: np.ndarray, peak: float = 0.92) -> np.ndarray:
    m = np.max(np.abs(x)) or 1.0
    return x * (peak / m)


def write_wav_mono(path: str, x: np.ndarray) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

TRACKS = {
    "bg_music_piano_flute.wav": build_piano_flute,
    "bg_music_world1.wav":      build_world1,
    "bg_music_world2.wav":      build_world2,
    "bg_music_world3.wav":      build_world3,
    "bg_music_world4.wav":      build_world4,
    "bg_music_world5.wav":      build_world5,
    "bg_music_world6.wav":      build_world6,
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--soundfont", default=DEFAULT_SF2)
    ap.add_argument("--only", default="",
                    help="comma list of track keys w/o prefix, e.g. world3,piano_flute")
    args = ap.parse_args()
    if not os.path.exists(args.soundfont):
        raise SystemExit("soundfont not found: " + args.soundfont)
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    for fname, builder in TRACKS.items():
        key = fname.replace("bg_music_", "").replace(".wav", "")
        if only and key not in only:
            continue
        bpm, parts = builder()
        loop_samples = int(round(total_beats(bpm) * 60.0 / bpm * SAMPLE_RATE))
        with tempfile.TemporaryDirectory() as td:
            mid = os.path.join(td, key + ".mid")
            raw_wav = os.path.join(td, key + ".wav")
            write_midi(mid, bpm, parts)
            render_midi(mid, raw_wav, args.soundfont)
            mono = read_wav_mono(raw_wav)
        looped = normalize(seamless_loop(mono, loop_samples))
        path = os.path.join(args.out, fname)
        write_wav_mono(path, looped)
        disc = abs(float(looped[-1] - looped[0]))
        print("wrote {:<26} {:.1f}s peak={:.3f} loopΔ={:.4f} {:.1f}MB".format(
            fname, looped.shape[0] / SAMPLE_RATE, float(np.max(np.abs(looped))),
            disc, os.path.getsize(path) / 1e6))


if __name__ == "__main__":
    main()
