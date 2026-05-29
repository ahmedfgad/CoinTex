"""Generate composed background music for CoinTex (menu + 6 world tracks).

Higher-fidelity, melodic, seamless-looping tracks using a small numpy synth,
ported from the sibling project. Dev/build-time only: numpy is NOT a runtime
dependency (audio.py just loads WAVs). The WAVs ship pre-generated under
music/. Re-running overwrites them.

Usage:
    python tools/gen_world_music.py [--out music] [--only world3,piano_flute]
"""

from __future__ import annotations

import argparse
import os
import wave
import zlib

import numpy as np

SAMPLE_RATE = 44100
LOOP_SECONDS = 20.0          # nominal target; actual length snaps to whole bars
DEFAULT_OUT = "music"


def bars_for(bpm: float, beats_per_bar: int = 4) -> int:
    """Whole bars whose total duration is closest to LOOP_SECONDS."""
    bar_sec = 60.0 / bpm * beats_per_bar
    return max(1, round(LOOP_SECONDS / bar_sec))


def _t(n: int) -> np.ndarray:
    """Time vector of length n in seconds."""
    return np.arange(n, dtype=np.float64) / SAMPLE_RATE


def note_freq(midi: float) -> float:
    """MIDI note number -> frequency in Hz (A4 = 69 = 440 Hz)."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def osc_sine(freq: float, n: int) -> np.ndarray:
    return np.sin(2 * np.pi * freq * _t(n))


def osc_tri(freq: float, n: int) -> np.ndarray:
    # triangle via arcsin of sine -> band-limited, no harsh edges
    return (2.0 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * _t(n)))


def _bandlimited(freq: float, n: int, weights) -> np.ndarray:
    """Sum harmonics k*freq with given weights, skipping any above Nyquist."""
    t = _t(n)
    out = np.zeros(n)
    nyq = SAMPLE_RATE / 2.0
    for k, w in enumerate(weights, start=1):
        if k * freq >= nyq:
            break
        out += w * np.sin(2 * np.pi * k * freq * t)
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


def osc_saw(freq: float, n: int) -> np.ndarray:
    # band-limited saw: harmonic k has amplitude 1/k
    return _bandlimited(freq, n, [1.0 / k for k in range(1, 25)])


def osc_soft_square(freq: float, n: int) -> np.ndarray:
    # band-limited square: odd harmonics 1/k only -> rounded, not buzzy
    weights = [1.0 / k if k % 2 == 1 else 0.0 for k in range(1, 25)]
    return _bandlimited(freq, n, weights)


def adsr(n: int, attack=0.01, decay=0.08, sustain=0.7, release=0.12) -> np.ndarray:
    """ADSR envelope sized to n samples; clamps segments to fit."""
    a = min(int(attack * SAMPLE_RATE), n)
    d = min(int(decay * SAMPLE_RATE), n - a)
    r = min(int(release * SAMPLE_RATE), n - a - d)
    s = max(0, n - a - d - r)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a, endpoint=False) if a else np.array([]),
        np.linspace(1.0, sustain, d, endpoint=False) if d else np.array([]),
        np.full(s, sustain),
        np.linspace(sustain, 0.0, r) if r else np.array([]),
    ])
    if env.shape[0] < n:
        env = np.concatenate([env, np.zeros(n - env.shape[0])])
    return env[:n]


def lowpass(x: np.ndarray, cutoff: float, resonance: float = 0.0) -> np.ndarray:
    """One-pole low-pass (optionally light resonance via a second pass)."""
    dt = 1.0 / SAMPLE_RATE
    rc = 1.0 / (2 * np.pi * cutoff)
    alpha = dt / (rc + dt)
    y = np.empty_like(x)
    prev = 0.0
    for i in range(x.shape[0]):
        prev = prev + alpha * (x[i] - prev)
        y[i] = prev
    if resonance > 0.0:
        y = y + resonance * (y - lowpass(y, cutoff * 0.5))
    return y


def delay(x: np.ndarray, time_s: float, feedback: float = 0.35,
          mix: float = 0.3) -> np.ndarray:
    """Simple feedback delay (echo/space)."""
    d = max(1, int(time_s * SAMPLE_RATE))
    out = x.copy()
    buf = np.zeros(x.shape[0] + d)
    buf[:x.shape[0]] = x
    for i in range(x.shape[0]):
        echo = buf[i] * feedback
        if i + d < buf.shape[0]:
            buf[i + d] += echo
        out[i] = x[i] + mix * buf[i + d]
    peak = np.max(np.abs(out)) or 1.0
    return out / peak if peak > 1.0 else out


def kick(dur: float = 0.18) -> np.ndarray:
    n = int(dur * SAMPLE_RATE)
    t = _t(n)
    freq = 120.0 * np.exp(-t * 30.0) + 45.0   # pitch sweep down
    env = np.exp(-t * 18.0)
    return np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE) * env


def snare(dur: float = 0.16) -> np.ndarray:
    n = int(dur * SAMPLE_RATE)
    t = _t(n)
    noise = np.random.uniform(-1, 1, n)
    body = np.sin(2 * np.pi * 180.0 * t) * 0.4
    env = np.exp(-t * 22.0)
    return lowpass(noise, 6000.0) * 0.8 * env + body * env


def hat(dur: float = 0.05) -> np.ndarray:
    n = int(dur * SAMPLE_RATE)
    env = np.exp(-_t(n) * 80.0)
    noise = np.random.uniform(-1, 1, n)
    return (noise - lowpass(noise, 7000.0)) * env   # crude high-pass


def mix(*layers: np.ndarray) -> np.ndarray:
    """Sum equal/variable-length layers (zero-padded to the longest)."""
    length = max(l.shape[0] for l in layers)
    out = np.zeros(length)
    for l in layers:
        out[:l.shape[0]] += l
    return out


def normalize(x: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = np.max(np.abs(x)) or 1.0
    return x * (peak / m)


def soft_clip(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def seconds_to_samples(s: float) -> int:
    return int(round(s * SAMPLE_RATE))


def seq(total_n: int, bpm: float, notes, voice) -> np.ndarray:
    """Place notes on a beat grid.

    notes: list of (beat_offset, duration_beats, midi) — midi may be a float
    frequency-as-MIDI or an iterable of midi numbers for a chord.
    voice: callable(freq_hz, n_samples) -> np.ndarray buffer.
    """
    out = np.zeros(total_n)
    beat = 60.0 / bpm
    for beat_off, dur_beats, midi in notes:
        start = seconds_to_samples(beat_off * beat)
        n = seconds_to_samples(dur_beats * beat)
        if start >= total_n:
            continue
        n = min(n, total_n - start)
        midis = midi if hasattr(midi, "__iter__") else [midi]
        for m in midis:
            out[start:start + n] += voice(note_freq(m), n)
    return out


def crossfade_loop(x: np.ndarray, fade_s: float = 0.05) -> np.ndarray:
    """Fold the tail into the head with an equal-power crossfade so the
    buffer loops seamlessly. Returns a buffer shortened by the fade length."""
    f = min(seconds_to_samples(fade_s), x.shape[0] // 4)
    if f <= 0:
        return x
    head = x[:f].copy()
    body = x[f:].copy()
    tail = body[-f:]
    fade_out = np.cos(np.linspace(0, np.pi / 2, f)) ** 2
    fade_in = np.sin(np.linspace(0, np.pi / 2, f)) ** 2
    body[-f:] = tail * fade_out + head * fade_in
    return body


def write_wav(path: str, x: np.ndarray) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    clipped = np.clip(x, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SAMPLE_RATE)
        out.writeframes(pcm.tobytes())


# --------------------------------------------------------------------------
# Per-track builders
# --------------------------------------------------------------------------

def _bar_n(bpm: float, beats_per_bar: int = 4) -> int:
    bars = bars_for(bpm, beats_per_bar)
    return seconds_to_samples(bars * beats_per_bar * 60.0 / bpm)


def _pad(midis, n, cutoff=1800.0, detune=0.04):
    """Warm detuned-saw chord pad through a low-pass."""
    buf = np.zeros(n)
    for m in midis:
        f = note_freq(m)
        buf += osc_saw(f * (1 - detune), n) + osc_saw(f * (1 + detune), n)
    return lowpass(buf / (2 * len(midis)), cutoff) * adsr(n, attack=0.2, release=0.3)


def _bass_voice(f, n):
    return lowpass(osc_saw(f, n), 600.0) * adsr(n, attack=0.005, decay=0.05,
                                                sustain=0.8, release=0.05)


def _pluck_voice(f, n):
    return osc_soft_square(f, n) * adsr(n, attack=0.002, decay=0.12,
                                        sustain=0.2, release=0.06)


def _bell_voice(f, n):
    s = osc_sine(f, n) + 0.3 * osc_sine(2 * f, n) + 0.12 * osc_sine(3 * f, n)
    return s * adsr(n, attack=0.003, decay=0.5, sustain=0.0, release=0.3)


def _brass_voice(f, n):
    s = osc_saw(f * 0.997, n) + osc_saw(f, n) + osc_saw(f * 1.003, n)
    return lowpass(s / 3.0, 2600.0) * adsr(n, attack=0.03, decay=0.1,
                                           sustain=0.7, release=0.15)


def _tri_voice(f, n):
    return osc_tri(f, n) * adsr(n, attack=0.01, decay=0.15,
                                sustain=0.5, release=0.1)


def _drum_track(n, bpm, pattern):
    """pattern: list of (beat_offset, 'k'|'s'|'h'). Renders one-shots."""
    out = np.zeros(n)
    beat = 60.0 / bpm
    samp = {"k": kick(), "s": snare(), "h": hat()}
    for off, which in pattern:
        start = seconds_to_samples(off * beat)
        d = samp[which]
        end = min(n, start + d.shape[0])
        if start < n:
            out[start:end] += d[:end - start]
    return out


def _layered_pad(n, bpm, chord_beats):
    """Render each (beat_off, dur_beats, midis) chord as a pad into a buffer."""
    out = np.zeros(n)
    beat = 60.0 / bpm
    for off, dur, midis in chord_beats:
        start = seconds_to_samples(off * beat)
        k = seconds_to_samples(dur * beat)
        k = min(k, n - start)
        if start < n and k > 0:
            out[start:start + k] += _pad(midis, k)
    return out


def _basic_beat(beats):
    """Kick on down-beats, snare on back-beats, hats on every beat."""
    pat = []
    for b in range(int(beats)):
        pat.append((b, "k" if b % 2 == 0 else "s"))
        pat.append((b, "h"))
        pat.append((b + 0.5, "h"))
    return pat


def build_menu():
    bpm = 110.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # Upbeat I-V-vi-IV in C: chords over the whole loop, bouncy pluck melody.
    chord_beats = [(0, 4, [60, 64, 67]), (4, 4, [67, 71, 74]),
                   (8, 4, [57, 60, 64]), (12, 4, [53, 57, 60])]
    chord_beats = [(b, d, m) for (b, d, m) in chord_beats if b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    mel = [(0, 1, 72), (1, 0.5, 74), (1.5, 0.5, 76), (2, 1, 79), (3, 1, 76),
           (4, 1, 79), (6, 2, 74), (8, 1, 72), (10, 2, 67), (12, 1, 72),
           (13, 1, 74), (14, 2, 76)]
    mel = [(b, d, m) for (b, d, m) in mel if b < beats]
    lead = delay(seq(n, bpm, mel, _pluck_voice), 60.0 / bpm / 2, mix=0.2)
    drums = _drum_track(n, bpm, _basic_beat(beats))
    return normalize(mix(pad * 0.5, lead * 0.7, drums * 0.6), 0.9)


def build_world1():
    """Meadow — cheerful pastoral bounce, bright C major (C/G/Am/F)."""
    bpm = 104.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # 16-beat chord progression (C/G/Am/F), tiled across the full loop
    prog = [(0, 4, [60, 64, 67]), (4, 4, [55, 59, 62]),
            (8, 4, [57, 60, 64]), (12, 4, [53, 57, 60])]
    chord_beats = [(blk + b, d, m) for blk in range(0, int(beats), 16)
                   for (b, d, m) in prog if blk + b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # 16-beat melody motif, tiled; alternate passes lifted an octave for variety
    motif = [(0, 1, 72), (1, 1, 76), (2, 1, 79), (3, 1, 76), (4, 1, 74),
             (5, 1, 71), (6, 2, 67), (8, 1, 72), (9, 1, 69), (10, 2, 72),
             (12, 1, 65), (13, 1, 69), (14, 2, 72)]
    mel = []
    for i, blk in enumerate(range(0, int(beats), 16)):
        lift = 12 if i % 2 else 0
        mel += [(blk + b, d, m + lift) for (b, d, m) in motif if blk + b < beats]
    lead = delay(seq(n, bpm, mel, _pluck_voice), 60.0 / bpm / 2, mix=0.18)
    roots = [48, 43, 45, 41]
    bn = [(blk + bar * 4 + off, 1, roots[bar])
          for blk in range(0, int(beats), 16)
          for bar in range(len(roots))
          for off in (0, 2) if blk + bar * 4 + off < beats]
    bass = seq(n, bpm, bn, _bass_voice)
    drums = _drum_track(n, bpm, _basic_beat(beats))
    return normalize(mix(pad * 0.5, lead * 0.7, bass * 0.5, drums * 0.45), 0.9)


def build_world2():
    """Desert — exotic groove, A harmonic minor, tri lead, hand-percussion."""
    bpm = 100.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # A harmonic minor: A B C D E F G#  -> midi 57 59 60 62 64 65 68
    chord_beats = [(0, 4, [57, 60, 64]), (4, 4, [62, 65, 68]),
                   (8, 4, [53, 57, 60]), (12, 4, [55, 59, 62])]
    chord_beats = [(b, d, m) for (b, d, m) in chord_beats if b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    mel = [(0, 0.75, 69), (0.75, 0.25, 68), (1, 1, 65), (2, 1, 64), (3, 1, 62),
           (4, 1.5, 68), (5.5, 0.5, 69), (6, 2, 64), (8, 1, 60), (9, 1, 62),
           (10, 2, 65), (12, 0.5, 68), (12.5, 0.5, 69), (13, 1, 72), (14, 2, 69)]
    mel = [(b, d, m) for (b, d, m) in mel if b < beats]
    lead = delay(seq(n, bpm, mel, _tri_voice), 60.0 / bpm / 3, mix=0.22)
    # hand-percussion feel: kick + busy hats, sparse snare
    pat = []
    for b in range(int(beats)):
        pat.append((b, "k"))
        pat.append((b + 0.5, "h"))
        pat.append((b + 0.75, "h"))
        if b % 4 == 2:
            pat.append((b, "s"))
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.5, lead * 0.65, drums * 0.5), 0.9)


def build_world3():
    """Industrial — funky electro-groove, E minor pentatonic, filtered funk."""
    bpm = 112.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # E minor pentatonic: E G A B D -> 52 55 57 59 62 (and octaves)
    pent = [52, 55, 57, 59, 62, 64, 67, 69]
    # syncopated funk bass on the low pent notes
    bass_notes = [(0, 0.5, 40), (0.75, 0.25, 40), (1.5, 0.5, 43), (2, 0.5, 40),
                  (2.75, 0.25, 45), (3.5, 0.5, 38)]
    bn = []
    for bar in range(0, int(beats), 4):
        for (b, d, m) in bass_notes:
            bn.append((bar + b, d, m))
    bn = [(b, d, m) for (b, d, m) in bn if b < beats]
    bass = seq(n, bpm, bn, _bass_voice)
    # plucky pentatonic riff
    riff = [(0, 0.5, 64), (0.5, 0.5, 67), (1, 0.5, 69), (2, 0.5, 67),
            (2.5, 0.5, 64), (3, 0.5, 62), (3.5, 0.5, 64)]
    rn = []
    for bar in range(0, int(beats), 4):
        for (b, d, m) in riff:
            rn.append((bar + b, d, m))
    rn = [(b, d, m) for (b, d, m) in rn if b < beats]
    lead = seq(n, bpm, rn, _pluck_voice)
    pat = []
    for b in range(int(beats)):
        pat.append((b, "k"))
        pat.append((b + 0.5, "h"))
        pat.append((b + 0.25, "h"))
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(bass * 0.65, lead * 0.55, drums * 0.5), 0.9)


def build_world4():
    """Snowfield — sparkly crystalline, E major, bell arp through delay."""
    bpm = 96.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # E major pad: E B G#m C#m -> chords
    chord_beats = [(0, 4, [64, 68, 71]), (4, 4, [59, 64, 68]),
                   (8, 4, [61, 64, 68]), (12, 4, [57, 64, 68])]
    chord_beats = [(b, d, m) for (b, d, m) in chord_beats if b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # bell arpeggio (E major scale notes), 16th-ish sparkle
    arp_seq = [76, 80, 83, 88, 83, 80, 71, 76]
    arp = []
    for bar in range(0, int(beats), 4):
        for i, m in enumerate(arp_seq):
            arp.append((bar + i * 0.5, 0.5, m))
    arp = [(b, d, m) for (b, d, m) in arp if b < beats]
    bells = delay(seq(n, bpm, arp, _bell_voice), 60.0 / bpm * 0.75,
                  feedback=0.4, mix=0.35)
    # sparse beat: kick on 1 and 3 only
    pat = [(b, "k") for b in range(0, int(beats), 2)]
    pat += [(b + 0.5, "h") for b in range(int(beats))]
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.55, bells * 0.7, drums * 0.35), 0.9)


def build_world5():
    """Volcano — heroic action march, C Lydian, brass rising + power chords."""
    bpm = 128.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # C Lydian: C D E F# G A B -> power-chord pads (root+fifth)
    chord_beats = [(0, 4, [48, 55, 60]), (4, 4, [50, 57, 62]),
                   (8, 4, [53, 60, 65]), (12, 4, [55, 62, 67])]
    chord_beats = [(b, d, m) for (b, d, m) in chord_beats if b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # rising heroic brass motif
    mel = [(0, 1, 60), (1, 1, 62), (2, 1, 64), (3, 1, 66), (4, 2, 67),
           (6, 2, 64), (8, 1, 65), (9, 1, 67), (10, 1, 69), (11, 1, 71),
           (12, 2, 72), (14, 2, 67)]
    mel = [(b, d, m) for (b, d, m) in mel if b < beats]
    brass = seq(n, bpm, mel, _brass_voice)
    # driving beat: kick + snare backbeat + 8th hats
    pat = []
    for b in range(int(beats)):
        pat.append((b, "k"))
        if b % 2 == 1:
            pat.append((b, "s"))
        pat.append((b + 0.5, "h"))
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.45, brass * 0.7, drums * 0.55), 0.9)


def build_world6():
    """Cosmos — dreamy synthwave, Dmaj7/A/Bm/G, shimmering arp + round bass."""
    bpm = 92.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    chord_beats = [(0, 4, [62, 66, 69, 73]), (4, 4, [57, 61, 64]),
                   (8, 4, [59, 62, 66]), (12, 4, [55, 59, 62])]
    chord_beats = [(b, d, m) for (b, d, m) in chord_beats if b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # shimmering arp through heavy delay
    arp_seq = [74, 78, 81, 78, 73, 76, 81, 76]
    arp = []
    for bar in range(0, int(beats), 4):
        for i, m in enumerate(arp_seq):
            arp.append((bar + i * 0.5, 0.5, m))
    arp = [(b, d, m) for (b, d, m) in arp if b < beats]
    shimmer = delay(seq(n, bpm, arp, _tri_voice), 60.0 / bpm * 0.75,
                    feedback=0.45, mix=0.4)
    # round bass on chord roots
    roots = [38, 33, 35, 31]
    bass = seq(n, bpm, [(b * 4, 4, roots[b]) for b in range(len(roots))
                        if b * 4 < beats], _bass_voice)
    # gentle backbeat
    pat = []
    for b in range(int(beats)):
        pat.append((b, "k"))
        if b % 2 == 1:
            pat.append((b, "s"))
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.5, shimmer * 0.55, bass * 0.5, drums * 0.35), 0.9)


# --------------------------------------------------------------------------
# Registry + driver
# --------------------------------------------------------------------------

TRACKS = {
    "bg_music_piano_flute.wav": build_menu,
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
    ap.add_argument("--only", default="",
                    help="comma list of track keys w/o prefix, e.g. world3,piano_flute")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",") if s.strip()}
    for fname, builder in TRACKS.items():
        key = fname.replace("bg_music_", "").replace(".wav", "")
        if only and key not in only:
            continue
        # Per-track deterministic seed derived from the filename so each track's
        # drum noise is byte-reproducible regardless of --only / render order.
        np.random.seed(20260529 + (zlib.adler32(fname.encode()) & 0xFFFF))
        raw = builder()
        looped = soft_clip(crossfade_loop(raw, fade_s=0.06))
        path = os.path.join(args.out, fname)
        write_wav(path, looped)
        disc = abs(float(looped[-1] - looped[0]))
        size = os.path.getsize(path)
        print("wrote {:<22} {:.1f}s peak={:.3f} loopΔ={:.4f} {:.1f}MB".format(
            fname, looped.shape[0] / SAMPLE_RATE, float(np.max(np.abs(looped))),
            disc, size / 1e6))


if __name__ == "__main__":
    main()
