# Generates the original assets that need to be real files:
#   - the new sound effects (written into music/ as wav files)
#   - the launcher icon and the splash image (png files at the repo root)
#
# Run it once from the project root after changing any of the recipes:
#   ./venv/bin/python tools/gen_assets.py
#
# It needs numpy and Pillow, which are dev tools only. The game itself does not
# import this file or numpy at runtime.

import os
import sys
import wave
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(ROOT, "music")
# Alternative versions of the existing audio go here so the game keeps using the
# current files until the owner picks which set to keep.
ALT_DIR = os.path.join(ROOT, "audio_alternatives")
RATE = 44100


def _write_wav(name, samples, directory=MUSIC_DIR):
    # samples is a float array roughly in -1..1. Saved as 16-bit mono wav.
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype("<i2")
    path = os.path.join(directory, name)
    with wave.open(path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(data.tobytes())
    print("wrote", path)


def _envelope(length, attack=0.005, release=0.05):
    # Simple fade in/out so the sound does not click.
    env = np.ones(length)
    a = int(RATE * attack)
    r = int(RATE * release)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if r > 0:
        env[-r:] = np.linspace(1, 0, r)
    return env


def _tone(freq, dur, kind="sine"):
    t = np.linspace(0, dur, int(RATE * dur), endpoint=False)
    if kind == "square":
        wave_data = np.sign(np.sin(2 * np.pi * freq * t))
    else:
        wave_data = np.sin(2 * np.pi * freq * t)
    return wave_data


def _sweep(f0, f1, dur, kind="sine"):
    t = np.linspace(0, dur, int(RATE * dur), endpoint=False)
    freq = np.linspace(f0, f1, t.size)
    phase = 2 * np.pi * np.cumsum(freq) / RATE
    wave_data = np.sin(phase) if kind == "sine" else np.sign(np.sin(phase))
    return wave_data


def make_sfx():
    # shoot: quick high-to-low zap
    s = _sweep(880, 260, 0.16, "square") * 0.5
    _write_wav("sfx_shoot.wav", s * _envelope(s.size))

    # hit: very short noise tick
    n = np.random.uniform(-1, 1, int(RATE * 0.07)) * 0.5
    _write_wav("sfx_hit.wav", n * _envelope(n.size, 0.001, 0.04))

    # monster death: falling tone mixed with noise
    body = _sweep(440, 120, 0.32, "sine") * 0.5
    noise = np.random.uniform(-1, 1, body.size) * 0.2
    d = (body + noise) * _envelope(body.size, 0.005, 0.12)
    _write_wav("sfx_monster_death.wav", d)

    # damage: low buzz
    b = _tone(140, 0.22, "square") * 0.45
    _write_wav("sfx_damage.wav", b * _envelope(b.size, 0.003, 0.08))

    # click: tiny tick for buttons
    c = _tone(1100, 0.04) * 0.4
    _write_wav("sfx_click.wav", c * _envelope(c.size, 0.001, 0.02))

    # victory: rising four note arpeggio
    notes = [523, 659, 784, 1047]
    parts = []
    for f in notes:
        part = _tone(f, 0.13) * 0.45
        parts.append(part * _envelope(part.size, 0.005, 0.04))
    v = np.concatenate(parts)
    _write_wav("sfx_victory.wav", v)


def _coin(draw, cx, cy, r):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(204, 150, 26))
    draw.ellipse([cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78],
                 fill=(255, 214, 64))
    # a simple star in the middle
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r * (0.5 if i % 2 == 0 else 0.22)
        pts.append((cx + math.cos(ang) * rr, cy - math.sin(ang) * rr))
    draw.polygon(pts, fill=(204, 150, 26))


def _gradient(size, top, bottom):
    img = Image.new("RGB", size)
    px = img.load()
    w, h = size
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(bottom[i] + (top[i] - bottom[i]) * (1 - t)) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return img


def make_icon():
    size = (512, 512)
    img = _gradient(size, (60, 130, 230), (20, 60, 150)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    _coin(draw, 256, 256, 170)
    img.save(os.path.join(ROOT, "cointex_logo.png"))
    print("wrote cointex_logo.png")


def make_presplash():
    size = (1024, 1024)
    img = _gradient(size, (60, 130, 230), (20, 60, 150)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    _coin(draw, 512, 430, 230)
    text = "CoinTex"
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 130)
    except Exception:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), text, font=font)
    tw = box[2] - box[0]
    draw.text((512 - tw / 2, 760), text, font=font, fill=(255, 255, 255))
    img.save(os.path.join(ROOT, "cointex_presplash.png"))
    print("wrote cointex_presplash.png")


# ---- alternative audio (music + the three flute sound effects) ----
# These are simple synthesized tunes offered as an option. They are written to
# audio_alternatives/ and are not used by the game unless the owner copies them
# into music/.

def _midi(note):
    return 440.0 * 2 ** ((note - 69) / 12.0)


def _adsr(length, attack=0.01, decay=0.06, sustain=0.6, release=0.08):
    env = np.full(length, sustain, dtype=float)
    a = min(int(RATE * attack), length)
    r = min(int(RATE * release), length)
    d = min(int(RATE * decay), max(0, length - a))
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0 and a + d <= length:
        env[a:a + d] = np.linspace(1, sustain, d)
    if r > 0:
        env[-r:] = env[-r:] * np.linspace(1, 0, r)
    return env


def _osc(freq, dur, kind="triangle"):
    t = np.linspace(0, dur, int(RATE * dur), endpoint=False)
    if kind == "sine":
        return np.sin(2 * np.pi * freq * t)
    if kind == "square":
        return np.sign(np.sin(2 * np.pi * freq * t))
    if kind == "saw":
        return 2 * (t * freq - np.floor(0.5 + t * freq))
    return 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1  # triangle


def _note(note, dur, kind="triangle", vol=0.5):
    if note is None:
        return np.zeros(int(RATE * dur))
    wave_data = _osc(_midi(note), dur, kind) * vol
    return wave_data * _adsr(wave_data.size)


def _seq(notes, kind, vol):
    return np.concatenate([_note(n, d, kind, vol) for n, d in notes])


def _mix(*tracks):
    length = max(len(t) for t in tracks)
    out = np.zeros(length)
    for t in tracks:
        out[:len(t)] += t
    peak = np.max(np.abs(out)) or 1.0
    return out / peak * 0.9


def _menu_music():
    # Calm looping arpeggio over C, Am, F, G.
    chords = [[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]]
    arp, bass, pad = [], [], []
    for _ in range(3):
        for tones in chords:
            for tone in tones:
                arp.append((tone, 0.30))
            bass.append((tones[0] - 12, 1.20))
            pad.append((tones[0], 1.20))
    return _mix(_seq(arp, "triangle", 0.5),
                _seq(bass, "sine", 0.5),
                _seq(pad, "sine", 0.16))


def _level_music():
    # Faster, livelier loop over Am, F, C, G.
    chords = [[57, 60, 64], [53, 57, 60], [60, 64, 67], [55, 59, 62]]
    lead, bass = [], []
    for _ in range(4):
        for tones in chords:
            pattern = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 12]
            for note in pattern:
                lead.append((note, 0.15))
            for _beat in range(4):
                bass.append((tones[0] - 12, 0.15))
    return _mix(_seq(lead, "square", 0.35),
                _seq(bass, "saw", 0.5))


def make_alternatives():
    os.makedirs(ALT_DIR, exist_ok=True)

    _write_wav("bg_music_piano_flute.wav", _menu_music(), ALT_DIR)
    _write_wav("bg_music_piano.wav", _level_music(), ALT_DIR)

    # coin pickup: two quick rising blips
    coin = _seq([(84, 0.06), (91, 0.10)], "triangle", 0.6)
    _write_wav("coin.wav", coin, ALT_DIR)

    # level complete: rising arpeggio finishing on a held note
    done = _seq([(72, 0.12), (76, 0.12), (79, 0.12), (84, 0.30)], "triangle", 0.55)
    _write_wav("level_completed_flaute.wav", done, ALT_DIR)

    # character death: a falling, sad tone
    death = _sweep(330, 90, 0.7, "sine") * 0.55
    death = death * _envelope(death.size, 0.01, 0.2)
    _write_wav("char_death_flaute.wav", death, ALT_DIR)
    print("alternatives written to", ALT_DIR)


def _tremolo(signal, rate_hz=5.0, depth=0.06):
    t = np.linspace(0, len(signal) / RATE, len(signal), endpoint=False)
    return signal * (1 - depth + depth * np.sin(2 * np.pi * rate_hz * t))


def make_extra_alternatives():
    # More choices for the in-level music and the death sound. These all use soft
    # triangle/sine tones, no harsh square/saw, so they are gentler than the first
    # in-level alternative. Files get descriptive names so they are easy to tell apart.
    os.makedirs(ALT_DIR, exist_ok=True)

    # in-level music, calm arpeggio over C, Am, F, G
    chords = [[60, 64, 67, 72], [57, 60, 64, 69], [53, 57, 60, 65], [55, 59, 62, 67]]
    arp, bass, pad = [], [], []
    for _ in range(3):
        for tones in chords:
            for tone in tones:
                arp.append((tone, 0.25))
            bass.append((tones[0] - 12, 1.0))
            pad.append((tones[0], 1.0))
    _write_wav("bg_music_piano__calm.wav",
               _mix(_seq(arp, "triangle", 0.45), _seq(bass, "sine", 0.45), _seq(pad, "sine", 0.14)),
               ALT_DIR)

    # in-level music, slow and mellow over Am, F, C, G
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [60, 64, 67, 72], [55, 59, 62, 67]]
    mel, bass = [], []
    for _ in range(3):
        for tones in chords:
            mel += [(tones[3], 0.4), (tones[2], 0.4), (tones[1], 0.4), (None, 0.4)]
            bass.append((tones[0] - 12, 1.6))
    _write_wav("bg_music_piano__mellow.wav",
               _mix(_seq(mel, "triangle", 0.4), _seq(bass, "sine", 0.4)), ALT_DIR)

    # in-level music, light and bouncy over C, G, Am, F
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    mel, bass = [], []
    for _ in range(4):
        for tones in chords:
            mel += [(tones[0] + 12, 0.22), (tones[2] + 12, 0.22),
                    (tones[1] + 12, 0.22), (tones[2] + 12, 0.22)]
            bass += [(tones[0] - 12, 0.22), (tones[2] - 12, 0.22),
                     (tones[0] - 12, 0.22), (tones[2] - 12, 0.22)]
    _write_wav("bg_music_piano__bouncy.wav",
               _mix(_seq(mel, "triangle", 0.42), _seq(bass, "sine", 0.45)), ALT_DIR)

    # death sound, soft falling tone with a slight wobble
    soft = _sweep(300, 110, 0.8, "sine") * 0.5
    soft = _tremolo(soft) * _envelope(soft.size, 0.01, 0.2)
    _write_wav("char_death__soft.wav", soft, ALT_DIR)

    # death sound, four falling notes
    notes = _seq([(69, 0.18), (65, 0.18), (62, 0.18), (57, 0.34)], "triangle", 0.5)
    _write_wav("char_death__notes.wav", notes, ALT_DIR)

    # death sound, quick fall into a low thud
    fall = _sweep(260, 70, 0.4, "sine") * 0.5
    fall = fall * _envelope(fall.size, 0.005, 0.1)
    thud = _note(36, 0.28, "sine", 0.6)
    _write_wav("char_death__thud.wav", np.concatenate([fall, thud]), ALT_DIR)
    print("extra alternatives written to", ALT_DIR)


def _rep(seq, times):
    out = []
    for _ in range(times):
        out += seq
    return out


# Each world has its own tune. They use different scales, tempos, rhythms,
# instruments and bass styles so they sound clearly different from each other.

def _world1_meadow():
    # bright and bouncy, C major pentatonic, hopping bass
    a = [60, 64, 67, 64, 69, 67, 64, 62]
    b = [60, 62, 64, 67, 69, 72, 69, 67]
    mel = _rep([(n, 0.18) for n in a] + [(n, 0.18) for n in b], 3)
    bass = _rep([(48, 0.18), (48, 0.18), (55, 0.18), (48, 0.18)], 12)
    return _mix(_seq(mel, "triangle", 0.45), _seq(bass, "sine", 0.5))


def _world2_desert():
    # exotic desert feel from a Phrygian-dominant scale, bright with a moving bass
    a = [69, 70, 73, 70, 69, 73, 76, 73]
    b = [76, 73, 70, 69, 70, 69, 67, 69]
    mel = _rep([(n, 0.20) for n in a] + [(n, 0.20) for n in b], 3)
    bass = _rep([(45, 0.20), (52, 0.20), (45, 0.20), (50, 0.20)], 12)
    return _mix(_seq(mel, "triangle", 0.46), _seq(bass, "sine", 0.50))


def _world3_ocean():
    # flowing and bright, F major waves in a higher register with a steady bass
    a = [65, 69, 72, 69, 67, 72, 76, 72]
    b = [69, 72, 77, 72, 65, 69, 72, 69]
    mel = _rep([(n, 0.20) for n in a] + [(n, 0.20) for n in b], 3)
    bass = _rep([(53, 0.20), (48, 0.20), (50, 0.20), (46, 0.20)], 12)
    return _mix(_seq(mel, "triangle", 0.46), _seq(bass, "sine", 0.50))


def _world4_cavern():
    # mysterious but active, A minor melody over a walking bass
    a = [57, 60, 64, 62, 60, 64, 67, 64]
    b = [65, 64, 60, 57, 59, 57, 55, 57]
    mel = _rep([(n, 0.20) for n in a] + [(n, 0.20) for n in b], 3)
    bass = _rep([(45, 0.20), (45, 0.20), (52, 0.20), (48, 0.20)], 12)
    return _mix(_seq(mel, "triangle", 0.46), _seq(bass, "sine", 0.50))


def _world5_volcano():
    # fast, relentless and tense, E minor, pulsing bass on every step
    a = [52, 52, 55, 52, 59, 52, 55, 52]
    b = [52, 55, 59, 55, 62, 59, 55, 52]
    mel = _rep([(n, 0.13) for n in a] + [(n, 0.13) for n in b], 4)
    bass = _rep([(40, 0.13)], 64)
    return _mix(_seq(mel, "triangle", 0.40), _seq(bass, "sine", 0.50))


def _world6_space():
    # bright and shimmery, a high major arpeggio over a moving bass and soft pad
    a = [72, 76, 79, 83, 79, 76, 72, 74]
    b = [76, 79, 83, 86, 79, 76, 74, 72]
    mel = _rep([(n, 0.22) for n in a] + [(n, 0.22) for n in b], 3)
    bass = _rep([(48, 0.22), (48, 0.22), (55, 0.22), (52, 0.22)], 12)
    pad = _rep([(60, 1.76), (64, 1.76)], 3)
    return _mix(_seq(mel, "triangle", 0.45), _seq(bass, "sine", 0.48), _seq(pad, "sine", 0.18))


WORLD_BUILDERS = [_world1_meadow, _world2_desert, _world3_ocean,
                  _world4_cavern, _world5_volcano, _world6_space]


def make_world_music():
    os.makedirs(MUSIC_DIR, exist_ok=True)
    for i, builder in enumerate(WORLD_BUILDERS, start=1):
        _write_wav("bg_music_world{}.wav".format(i), builder(), MUSIC_DIR)
    print("world music written to", MUSIC_DIR)


if __name__ == "__main__":
    if "world" in sys.argv:
        make_world_music()
    elif "more" in sys.argv:
        make_extra_alternatives()
    elif "alternatives" in sys.argv:
        make_alternatives()
    else:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        make_sfx()
        make_icon()
        make_presplash()
        print("done")
