"""Mix a CoinTex segment soundtrack from the capture's audio-event log.

Lays down the segment's world-music bed (looped/trimmed to the clip length)
and overlays each logged SFX (shoot, coin, hit, monster_death, ...) at its
timestamp, using the game's OWN wav files. Output: 44.1k stereo wav matched to
the segment's exact video duration.
"""

import json
import os
import sys
import wave

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import audio as audio_mod  # SFX_FILES name->wav mapping

SR = 44100


def _read_wav_mono(path):
    w = wave.open(path, "rb")
    n, ch = w.getnframes(), w.getnchannels()
    raw = w.readframes(n)
    w.close()
    a = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        a = a.reshape(-1, ch).mean(1)
    return a


def build_mix(audio_json, out_wav, music_dir, seconds=None,
              music_gain=0.45, sfx_gain=0.9):
    d = json.load(open(audio_json))
    return build_mix_events(d.get("events", []), d.get("world"),
                            seconds if seconds is not None else d["seconds"],
                            out_wav, music_dir, music_gain, sfx_gain)


def build_mix_events(events, world, seconds, out_wav, music_dir,
                     music_gain=0.45, sfx_gain=0.9):
    dur = float(seconds)
    d = {"events": events, "world": world}
    total = int(round(dur * SR)) + SR  # +1s tail for SFX ring-out
    buf = np.zeros(total, np.float32)

    # world-music bed
    world = d.get("world")
    if world:
        mp = os.path.join(music_dir, "bg_music_world%d.wav" % world)
        if os.path.exists(mp):
            m = _read_wav_mono(mp)
            need = int(round(dur * SR))
            if len(m) < need:
                m = np.tile(m, int(np.ceil(need / len(m))))
            m = m[:need].copy()
            # gentle fade in/out on the bed
            fi = int(0.15 * SR)
            fo = int(0.5 * SR)
            if len(m) > fi + fo:
                m[:fi] *= np.linspace(0, 1, fi)
                m[-fo:] *= np.linspace(1, 0, fo)
            buf[:len(m)] += m * music_gain

    # SFX overlays
    cache = {}
    for e in d.get("events", []):
        fn = audio_mod.SFX_FILES.get(e["name"])
        if not fn:
            continue
        p = os.path.join(music_dir, fn)
        if not os.path.exists(p):
            continue
        if fn not in cache:
            cache[fn] = _read_wav_mono(p)
        s = cache[fn]
        i = int(round(e["t"] * SR))
        if i < 0:
            s = s[-i:]
            i = 0
        j = min(i + len(s), total)
        if j > i:
            buf[i:j] += s[:j - i] * sfx_gain

    peak = float(np.max(np.abs(buf))) or 1.0
    if peak > 1.0:
        buf /= peak / 0.98
    stereo = np.stack([buf, buf], 1)
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out_wav
