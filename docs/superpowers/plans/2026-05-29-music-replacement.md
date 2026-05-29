# CoinTex Music Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace CoinTex's 7 background-music WAVs (`bg_music_piano_flute.wav` menu + `bg_music_world1..6.wav`) in `music/` with new composed, clean, ~20 s seamless-loop tracks, by porting the proven numpy synth tool from the sibling project and adapting its builders to CoinTex's worlds.

**Architecture:** Port `tools/gen_world_music.py` + `tools/test_gen_world_music.py` verbatim from the sibling repo (`/home/ahmed-gad/projects/GateRunner/tools/`), then adapt: point output at `music/`, point the `TRACKS` registry at CoinTex's filenames (no boss), add two new voices (`_piano_voice`, `_flute_voice`), and rewrite 3 builders (menu, world3 Ocean, world4 Cavern). World1 (Meadow), world2 (Desert), world5 (Volcano), world6 (Space=synthwave) are reused unchanged. Filenames are unchanged so `audio.py` needs no edits. SFX and `music/originals/` are untouched.

**Tech Stack:** Python 3.12, numpy (already in CoinTex's venv + `requirements-dev.txt`, dev-only), stdlib `wave`. Tests are plain-`assert` scripts run with `venv/bin/python` (no pytest).

---

## File Structure

- **Create** `tools/gen_world_music.py` — synth core + 7 per-track builders + driver (ported + adapted).
- **Create** `tools/test_gen_world_music.py` — headless synth-core + structural tests (ported; structural test auto-covers all tracks in `TRACKS`).
- **Overwrite (generated)** `music/bg_music_piano_flute.wav`, `music/bg_music_world1.wav` … `music/bg_music_world6.wav`.
- **Untouched:** all `music/sfx_*.wav`, `music/coin.wav`, `music/char_death_flaute.wav`, `music/level_completed_flaute.wav`, and `music/originals/`.

The source module to port lives at `/home/ahmed-gad/projects/GateRunner/tools/gen_world_music.py` (565 lines) and its test at `/home/ahmed-gad/projects/GateRunner/tools/test_gen_world_music.py`. **Copying these existing files is allowed and expected** (this is a deliberate port, not "reading the plan file").

All CoinTex commands run from `/home/ahmed-gad/projects/CoinTex` on the `music-replacement` branch, using `venv/bin/python`. Commit messages get the trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Port the module + test, adapt registry/output

**Files:**
- Create: `tools/gen_world_music.py`, `tools/test_gen_world_music.py`

- [ ] **Step 1: Copy both files from the sibling repo**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex
cp /home/ahmed-gad/projects/GateRunner/tools/gen_world_music.py tools/gen_world_music.py
cp /home/ahmed-gad/projects/GateRunner/tools/test_gen_world_music.py tools/test_gen_world_music.py
```

- [ ] **Step 2: Adapt the module docstring + output dir**

In `tools/gen_world_music.py`, replace the module docstring (the triple-quoted block at the top) with:
```python
"""Generate composed background music for CoinTex (menu + 6 world tracks).

Higher-fidelity, melodic, seamless-looping tracks using a small numpy synth,
ported from the sibling project. Dev/build-time only: numpy is NOT a runtime
dependency (audio.py just loads WAVs). The WAVs ship pre-generated under
music/. Re-running overwrites them.

Usage:
    python tools/gen_world_music.py [--out music] [--only world3,piano_flute]
"""
```
Then change the output-dir constant:
```python
DEFAULT_OUT = "music"
```
(was `os.path.join("assets", "music")`).

- [ ] **Step 3: Point the TRACKS registry at CoinTex filenames (drop boss)**

Replace the entire `TRACKS = { ... }` dict with:
```python
TRACKS = {
    "bg_music_piano_flute.wav": build_menu,
    "bg_music_world1.wav":      build_world1,
    "bg_music_world2.wav":      build_world2,
    "bg_music_world3.wav":      build_world3,
    "bg_music_world4.wav":      build_world4,
    "bg_music_world5.wav":      build_world5,
    "bg_music_world6.wav":      build_world6,
}
```
Then **delete the `build_boss()` function entirely** (the whole `def build_boss(): ...` block, ~lines 492–520 in the source) since CoinTex has no boss track and it would be dead code.

> Note: the per-track deterministic seed in `main()` keys off the filename, so changing `bg_music_menu.wav` → `bg_music_piano_flute.wav` just changes that track's seed — fine, it's still reproducible.

- [ ] **Step 4: Verify the synth core still imports and its tests pass**

The synth core (oscillators … `write_wav`) is unchanged, so its tests pass immediately. `build_menu`/`build_world3`/`build_world4` are still the *sibling* versions at this point (rewritten in Task 3) — that's fine, they still produce valid buffers, so even the structural test passes now.

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex && venv/bin/python tools/test_gen_world_music.py
```
Expected: `PASS: all tests`

Also confirm the registry resolves to 7 builders:
```bash
cd /home/ahmed-gad/projects/CoinTex && venv/bin/python -c "import sys; sys.path.insert(0,'tools'); import gen_world_music as g; print(len(g.TRACKS), list(g.TRACKS)); assert 'build_boss' not in dir(g)"
```
Expected: `7 ['bg_music_piano_flute.wav', 'bg_music_world1.wav', ... 'bg_music_world6.wav']` and no error.

- [ ] **Step 5: Commit**

```bash
cd /home/ahmed-gad/projects/CoinTex
git add tools/gen_world_music.py tools/test_gen_world_music.py
git commit -m "Port music-gen tool from sibling project, adapt for CoinTex"
```

---

## Task 2: Add piano + flute voices (for the menu)

**Files:**
- Modify: `tools/gen_world_music.py`, `tools/test_gen_world_music.py`

- [ ] **Step 1: Add a failing test** (append to `tools/test_gen_world_music.py`, and add the call in `__main__` before `test_all_tracks_structural()`)

```python
def test_piano_and_flute_voices():
    n = g.SAMPLE_RATE // 2   # 0.5 s note
    f = g.note_freq(72)      # C5
    for voice in (g._piano_voice, g._flute_voice):
        buf = voice(f, n)
        assert buf.shape == (n,), voice.__name__
        assert np.all(np.isfinite(buf)), voice.__name__
        assert np.max(np.abs(buf)) <= 1.0 + 1e-6, voice.__name__
        assert np.max(np.abs(buf)) > 0.05, voice.__name__   # audible
    # piano is struck/decaying: end quieter than the early body
    p = g._piano_voice(f, n)
    early = np.max(np.abs(p[:n // 5]))
    late = np.max(np.abs(p[-n // 5:]))
    assert late < early, "piano should decay"
```

Add to `__main__` (before `test_all_tracks_structural()`):
```python
    test_piano_and_flute_voices()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /home/ahmed-gad/projects/CoinTex && venv/bin/python tools/test_gen_world_music.py`
Expected: FAIL — `module 'gen_world_music' has no attribute '_piano_voice'`

- [ ] **Step 3: Implement the two voices** — add them in `tools/gen_world_music.py` right after `_tri_voice` (so they sit with the other voice helpers, before `_drum_track`)

```python
def _piano_voice(f, n):
    """Struck, decaying harmonic tone — warm piano-ish timbre."""
    s = (osc_sine(f, n) + 0.5 * osc_sine(2 * f, n)
         + 0.25 * osc_sine(3 * f, n) + 0.12 * osc_sine(4 * f, n))
    env = adsr(n, attack=0.004, decay=0.6, sustain=0.0, release=0.2)
    return (s / 1.87) * env   # 1.87 = approx peak of the harmonic sum


def _flute_voice(f, n):
    """Breathy near-sine with gentle vibrato — airy flute-ish timbre."""
    t = _t(n)
    vib = 1.0 + 0.006 * np.sin(2 * np.pi * 5.0 * t)        # ~5 Hz vibrato
    tone = (np.sin(2 * np.pi * f * t * vib)
            + 0.08 * np.sin(2 * np.pi * 2 * f * t * vib))
    breath = lowpass(np.random.uniform(-1, 1, n), 3000.0) * 0.05
    env = adsr(n, attack=0.06, decay=0.1, sustain=0.8, release=0.15)
    return (tone / 1.08 + breath) * env
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /home/ahmed-gad/projects/CoinTex && venv/bin/python tools/test_gen_world_music.py`
Expected: `PASS: all tests`

- [ ] **Step 5: Commit**

```bash
cd /home/ahmed-gad/projects/CoinTex
git add tools/gen_world_music.py tools/test_gen_world_music.py
git commit -m "Music gen: add piano + flute voices for the menu track"
```

---

## Task 3: Rewrite the menu, Ocean (W3) and Cavern (W4) builders

**Files:**
- Modify: `tools/gen_world_music.py`

World1 (Meadow), world2 (Desert), world5 (Volcano), and world6 (Space — synthwave) carry over unchanged from the port and already match CoinTex's themes. Only `build_menu`, `build_world3`, and `build_world4` need rewriting (the ported versions are an upbeat menu / industrial / snowfield, which don't fit CoinTex).

- [ ] **Step 1: Replace `build_menu`** with the warm piano + flute version

Replace the whole `def build_menu(): ...` block with:
```python
def build_menu():
    """Warm piano + flute melody — gentle, pretty, welcoming title theme."""
    bpm = 84.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # Gentle C major I-vi-IV-V (C/Am/F/G), tiled across the loop
    prog = [(0, 4, [60, 64, 67]), (4, 4, [57, 60, 64]),
            (8, 4, [53, 57, 60]), (12, 4, [55, 59, 62])]
    chord_beats = [(blk + b, d, m) for blk in range(0, int(beats), 16)
                   for (b, d, m) in prog if blk + b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # Piano: gentle broken-chord comping, 24 notes spread over each 16-beat block
    arp = [60, 64, 67, 72, 67, 64, 57, 60, 64, 69, 64, 60,
           53, 57, 60, 65, 60, 57, 55, 59, 62, 67, 62, 59]
    step = 16.0 / len(arp)
    piano_notes = [(blk + i * step, step, m)
                   for blk in range(0, int(beats), 16)
                   for i, m in enumerate(arp) if blk + i * step < beats]
    piano = seq(n, bpm, piano_notes, _piano_voice)
    # Flute: slow lyrical melody on top, lightly echoed
    fmotif = [(0, 2, 79), (2, 2, 76), (4, 2, 72), (6, 2, 74),
              (8, 2, 77), (10, 2, 76), (12, 3, 72), (15, 1, 74)]
    fmel = [(blk + b, d, m) for blk in range(0, int(beats), 16)
            for (b, d, m) in fmotif if blk + b < beats]
    flute = delay(seq(n, bpm, fmel, _flute_voice), 60.0 / bpm * 0.5,
                  feedback=0.25, mix=0.2)
    # Calm: no drums on the title theme.
    return normalize(mix(pad * 0.4, piano * 0.6, flute * 0.6), 0.9)
```

- [ ] **Step 2: Replace `build_world3`** with the Ocean version

Replace the whole `def build_world3(): ...` block with:
```python
def build_world3():
    """Ocean — bright flowing aquatic: bubbly arp, soft pad, gentle sway."""
    bpm = 96.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # Flowing G major: G  D  Em  C
    prog = [(0, 4, [55, 59, 62]), (4, 4, [50, 57, 62]),
            (8, 4, [52, 55, 59]), (12, 4, [48, 55, 60])]
    chord_beats = [(blk + b, d, m) for blk in range(0, int(beats), 16)
                   for (b, d, m) in prog if blk + b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # bubbly flowing 8th-note arpeggio, bell voice through delay
    arp_seq = [67, 71, 74, 79, 74, 71, 62, 67]
    arp = [(bar + i * 0.5, 0.5, m) for bar in range(0, int(beats), 4)
           for i, m in enumerate(arp_seq) if bar + i * 0.5 < beats]
    bubbles = delay(seq(n, bpm, arp, _bell_voice), 60.0 / bpm * 0.75,
                    feedback=0.35, mix=0.4)
    # gentle round bass on chord roots
    roots = [43, 38, 40, 36]
    bass = seq(n, bpm, [(b * 4, 4, roots[b]) for b in range(len(roots))
                        if b * 4 < beats], _bass_voice)
    # soft swaying beat: kick on 1/3, hats on off-beats
    pat = [(b, "k") for b in range(0, int(beats), 2)]
    pat += [(b + 0.5, "h") for b in range(int(beats))]
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.5, bubbles * 0.6, bass * 0.45, drums * 0.3), 0.9)
```

- [ ] **Step 3: Replace `build_world4`** with the Cavern version

Replace the whole `def build_world4(): ...` block with:
```python
def build_world4():
    """Cavern — mysterious echoey: spacious pad, sparse melody through heavy delay."""
    bpm = 88.0
    n = _bar_n(bpm)
    beats = n / SAMPLE_RATE / (60.0 / bpm)
    # D natural minor mood: Dm  Bb  F  C
    prog = [(0, 4, [50, 53, 57]), (4, 4, [46, 50, 53]),
            (8, 4, [53, 57, 60]), (12, 4, [48, 52, 55])]
    chord_beats = [(blk + b, d, m) for blk in range(0, int(beats), 16)
                   for (b, d, m) in prog if blk + b < beats]
    pad = _layered_pad(n, bpm, chord_beats)
    # sparse mysterious melody (D minor), tri voice through heavy echo
    mmotif = [(0, 1.5, 74), (2, 1, 72), (3.5, 0.5, 70), (5, 2, 69),
              (8, 1.5, 77), (10, 1, 74), (12, 2, 70), (14.5, 1.5, 69)]
    mel = [(blk + b, d, m) for blk in range(0, int(beats), 16)
           for (b, d, m) in mmotif if blk + b < beats]
    echoey = delay(seq(n, bpm, mel, _tri_voice), 60.0 / bpm * 0.75,
                   feedback=0.5, mix=0.45)
    # low drone bass on roots
    roots = [38, 34, 41, 36]
    bass = seq(n, bpm, [(b * 4, 4, roots[b]) for b in range(len(roots))
                        if b * 4 < beats], _bass_voice)
    # minimal heartbeat: kick on beat 1 of each bar only
    pat = [(b, "k") for b in range(0, int(beats), 4)]
    drums = _drum_track(n, bpm, pat)
    return normalize(mix(pad * 0.55, echoey * 0.6, bass * 0.4, drums * 0.3), 0.9)
```

- [ ] **Step 4: Verify all 7 builders produce valid buffers + tests pass**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex && venv/bin/python -c "
import sys; sys.path.insert(0,'tools'); import numpy as np, gen_world_music as g
for k,b in g.TRACKS.items():
    buf=b(); assert buf.ndim==1 and buf.shape[0]>g.SAMPLE_RATE*15, k
    assert np.all(np.isfinite(buf)) and np.max(np.abs(buf))<=1.0+1e-6, k
    print('ok',k,round(buf.shape[0]/g.SAMPLE_RATE,1),'s')
print('ALL BUILDERS OK')"
venv/bin/python tools/test_gen_world_music.py
```
Expected: 7 `ok …` lines + `ALL BUILDERS OK`, then `PASS: all tests`. (If a builder trips the structural assert — clipping/silent/seam — tune that builder's gains/fade; do NOT loosen thresholds.)

- [ ] **Step 5: Commit**

```bash
cd /home/ahmed-gad/projects/CoinTex
git add tools/gen_world_music.py
git commit -m "Music gen: CoinTex menu (piano+flute), Ocean (W3), Cavern (W4) builders"
```

---

## Task 4: Generate the WAVs, verify, confirm SFX/originals untouched

**Files:**
- Overwrite: the 7 `music/bg_music_*.wav`

- [ ] **Step 1: Generate all tracks**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex && venv/bin/python tools/gen_world_music.py
```
Expected: 7 `wrote …` lines (`bg_music_piano_flute.wav` + `bg_music_world1..6.wav`), each `peak<1.0`, small `loopΔ` (< 0.08), ~1.6–1.9 MB.

- [ ] **Step 2: Verify format of the written files**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex && venv/bin/python -c "
import wave, os
mus='music'
for f in sorted(os.listdir(mus)):
    if not f.startswith('bg_music_') or not f.endswith('.wav'): continue
    with wave.open(os.path.join(mus,f),'rb') as w:
        assert w.getnchannels()==1 and w.getsampwidth()==2 and w.getframerate()==44100, f
        print(f, round(w.getnframes()/44100,1),'s', round(os.path.getsize(os.path.join(mus,f))/1e6,2),'MB')
print('FORMAT OK')"
```
Expected: 7 lines (44.1k mono, ~20 s) + `FORMAT OK`.

- [ ] **Step 3: Confirm ONLY the 7 music files changed; SFX + originals untouched**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex && git status --porcelain music/
```
Expected: only the 7 `music/bg_music_*.wav` appear as modified (`M`). **No** `sfx_*.wav`, `coin.wav`, `char_death_flaute.wav`, `level_completed_flaute.wav`, and **nothing** under `music/originals/` may appear. If anything else shows up, STOP and report — do not commit.

- [ ] **Step 4: Determinism check (full run vs `--only`)**

Run:
```bash
cd /home/ahmed-gad/projects/CoinTex
venv/bin/python tools/gen_world_music.py --out /tmp/ct_full
venv/bin/python tools/gen_world_music.py --out /tmp/ct_only --only world3,piano_flute
cmp /tmp/ct_full/bg_music_world3.wav /tmp/ct_only/bg_music_world3.wav && echo "world3 MATCH"
cmp /tmp/ct_full/bg_music_piano_flute.wav /tmp/ct_only/bg_music_piano_flute.wav && echo "menu MATCH"
cmp music/bg_music_world1.wav /tmp/ct_full/bg_music_world1.wav && echo "committed==fresh world1"
```
Expected: `world3 MATCH`, `menu MATCH`, `committed==fresh world1` (the committed files equal a fresh full run; `--only` reproduces those exact tracks).

- [ ] **Step 5: Commit the WAVs**

```bash
cd /home/ahmed-gad/projects/CoinTex
git add music/bg_music_piano_flute.wav music/bg_music_world1.wav music/bg_music_world2.wav music/bg_music_world3.wav music/bg_music_world4.wav music/bg_music_world5.wav music/bg_music_world6.wav
git commit -m "Replace CoinTex background music with composed numpy-synth tracks"
```

---

## Task 5: Kivy-loader smoke test + final verification

**Files:** none (verification only)

- [ ] **Step 1: Confirm the game's real audio loader accepts all 7 files**

Run (headless — needs no display for SoundLoader):
```bash
cd /home/ahmed-gad/projects/CoinTex && SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=dummy KIVY_NO_ARGS=1 KIVY_LOG_LEVEL=warning venv/bin/python - <<'PY'
import os
from kivy.core.audio import SoundLoader
d = "music"
ok = True
for f in sorted(os.listdir(d)):
    if not f.startswith("bg_music_") or not f.endswith(".wav"): continue
    s = SoundLoader.load(os.path.join(d, f))
    if s is None:
        print("FAIL load None:", f); ok = False; continue
    s.loop = True
    print("loaded %-26s len=%5.1fs" % (f, (s.length or 0)))
    s.unload()
print("ALL LOADED OK" if ok else "SOME FAILED")
PY
```
Expected: 7 `loaded …` lines (durations ~19–21 s) + `ALL LOADED OK`. (`SDL_AUDIODRIVER=dummy` means no audible sound — this only confirms the files load cleanly through the real runtime path.)

- [ ] **Step 2: Final full test run**

Run: `cd /home/ahmed-gad/projects/CoinTex && venv/bin/python tools/test_gen_world_music.py`
Expected: `PASS: all tests`

> Audible quality ("does it sound good") is a manual check for the user: `venv/bin/python main.py` on audio hardware (without `SDL_AUDIODRIVER=dummy`), listening to the menu and worlds 1–6.

---

## Self-Review Notes

- **Spec coverage:** port tool (Task 1) ✓; numpy dev-only — already in `requirements-dev.txt`, no buildozer change (Task 1 touches only tool files) ✓; 7 tracks to CoinTex filenames incl. menu `bg_music_piano_flute.wav`, no boss (Task 1 registry) ✓; new piano+flute voices (Task 2) ✓; menu warm piano+flute + Ocean + Cavern builders, W1/W2/W5/W6 reused (Task 3) ✓; 44.1k/mono/16-bit/~20s seamless (ported core + Task 4 checks) ✓; determinism incl. `--only` (Task 4 Step 4) ✓; SFX + `originals/` untouched (Task 4 Step 3 guard) ✓; Kivy-loader smoke (Task 5) ✓; filenames unchanged → no `audio.py` edit (no task touches it) ✓.
- **Placeholder scan:** no TBD/TODO; every code step shows full code.
- **Type consistency:** new voices `_piano_voice(f, n)` / `_flute_voice(f, n)` match the `voice(freq_hz, n)` contract used by `seq`; rewritten builders use only existing helpers (`_bar_n`, `_layered_pad`, `_pad`, `_bass_voice`, `_bell_voice`, `_tri_voice`, `_drum_track`, `seq`, `delay`, `mix`, `normalize`) plus the two new voices; `TRACKS` keys match `audio.py`'s `MENU_MUSIC` (`bg_music_piano_flute.wav`) and `world_music_name` (`bg_music_world{N}.wav`).
