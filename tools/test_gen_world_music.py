"""Headless tests for tools/gen_world_music.py — plain asserts, no pytest.

Run: venv/bin/python tools/test_gen_world_music.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import numpy as np
import gen_world_music as g


def test_note_freq():
    # A4 = MIDI 69 = 440 Hz; one octave up doubles.
    assert abs(g.note_freq(69) - 440.0) < 1e-6
    assert abs(g.note_freq(81) - 880.0) < 1e-6


def test_oscillators_shape_and_range():
    n = SR = g.SAMPLE_RATE // 10
    for osc in (g.osc_sine, g.osc_tri, g.osc_saw, g.osc_soft_square):
        buf = osc(220.0, n)
        assert buf.shape == (n,)
        assert np.max(np.abs(buf)) <= 1.0 + 1e-6, osc.__name__


def test_adsr_starts_and_ends_quiet():
    env = g.adsr(g.SAMPLE_RATE)  # 1 second
    assert env.shape == (g.SAMPLE_RATE,)
    assert env[0] < 0.05
    assert env[-1] < 0.05
    assert env.max() > 0.9


def test_lowpass_reduces_highs():
    n = g.SAMPLE_RATE
    hi = g.osc_sine(8000.0, n)
    lo = g.osc_sine(200.0, n)
    fhi = g.lowpass(hi, 800.0)
    flo = g.lowpass(lo, 800.0)
    # high tone is attenuated much more than the low tone
    assert np.max(np.abs(fhi)) < 0.5 * np.max(np.abs(flo))


def test_normalize_and_soft_clip_bounds():
    loud = g.osc_sine(440.0, 1000) * 5.0
    out = g.soft_clip(loud)
    assert np.max(np.abs(out)) <= 1.0
    norm = g.normalize(g.osc_sine(440.0, 1000) * 0.1, peak=0.9)
    assert abs(np.max(np.abs(norm)) - 0.9) < 1e-3


def test_drums_are_finite_and_bounded():
    for d in (g.kick(), g.snare(), g.hat()):
        assert d.ndim == 1 and d.shape[0] > 0
        assert np.all(np.isfinite(d))
        assert np.max(np.abs(d)) <= 1.0 + 1e-6


def test_seq_places_notes_on_grid():
    bpm = 120.0
    total = g.seconds_to_samples(2.0)   # 2 s == 1 bar at 120bpm 4/4
    voice = lambda f, n: g.osc_sine(f, n) * g.adsr(n)
    # one note on beat 0, one on beat 2
    buf = g.seq(total, bpm, [(0, 0.5, 60), (2, 0.5, 67)], voice)
    assert buf.shape == (total,)
    # energy near beat 0 and beat 2, ~silence right before beat 1's gap end
    b = g.seconds_to_samples(60.0 / bpm)   # one beat
    assert np.max(np.abs(buf[:b])) > 0.1
    assert np.max(np.abs(buf[2 * b:3 * b])) > 0.1


def test_crossfade_loop_is_seamless():
    n = g.SAMPLE_RATE
    x = g.osc_sine(220.0, n) * 0.8
    looped = g.crossfade_loop(x, fade_s=0.05)
    # boundary discontinuity (wrap from last sample to first) is small
    disc = abs(looped[-1] - looped[0])
    assert disc < 0.05


def test_write_and_read_wav(tmp_path="/tmp/gwm_test.wav"):
    x = g.osc_sine(330.0, g.SAMPLE_RATE) * 0.5
    g.write_wav(tmp_path, x)
    import wave
    with wave.open(tmp_path, "rb") as w:
        assert w.getnchannels() == 1
        assert w.getsampwidth() == 2
        assert w.getframerate() == g.SAMPLE_RATE
        assert w.getnframes() == g.SAMPLE_RATE


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


def test_all_tracks_structural():
    for key, builder in g.TRACKS.items():
        raw = builder()
        looped = g.soft_clip(g.crossfade_loop(raw, fade_s=0.06))
        dur = looped.shape[0] / g.SAMPLE_RATE
        assert 15.0 <= dur <= 26.0, (key, dur)             # ~20 s loop
        assert np.all(np.isfinite(looped)), key
        assert np.max(np.abs(looped)) <= 1.0 + 1e-6, key   # no clipping
        assert np.max(np.abs(looped)) > 0.3, key           # not silent
        assert abs(float(looped[-1] - looped[0])) < 0.08, key  # seamless-ish


if __name__ == "__main__":
    test_note_freq()
    test_oscillators_shape_and_range()
    test_adsr_starts_and_ends_quiet()
    test_lowpass_reduces_highs()
    test_normalize_and_soft_clip_bounds()
    test_drums_are_finite_and_bounded()
    test_seq_places_notes_on_grid()
    test_crossfade_loop_is_seamless()
    test_write_and_read_wav()
    test_piano_and_flute_voices()
    test_all_tracks_structural()
    print("PASS: all tests")
