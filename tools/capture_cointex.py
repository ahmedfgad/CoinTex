"""Deterministic 4K/60 capture harness for CoinTex gameplay.

Boots CointexApp at a fixed capture size, drives GameScreen.update() at a fixed
dt (so playback speed is independent of how fast the machine renders), steers
the level with the genetic-algorithm autoplayer stepped INLINE on sim time
(CoinTex's real AutoPlayer runs in a wall-clock thread, which would desync from
fast fixed-dt stepping), and grabs each GL frame.

Each level ATTEMPT is captured to its own clip so the assembler can later keep
only the longest failed attempt + the successful one per level. Output:
  --outdir DIR : attempt_000.mp4, attempt_001.mp4, ... + manifest.json
  --shot  P.png: single-frame smoke-test screenshot.

Chaining (per world): on a win, roll into the next level of the same world
(no result dialog) until the soft target is met at a level completion; on a
loss, retry the same level up to --max-retries; never loop forever.

Must run under a display at least as large as --size; for 4K use Xvfb:
  xvfb-run -a -s "-screen 0 3840x2160x24" venv/bin/python tools/capture_cointex.py ...
"""

import argparse
import json
import os
import random
import subprocess
import sys

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import imageio_ffmpeg  # noqa: E402

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SUPPRESS_FLAGS = ["tutorial_seen", "gun_hint_seen", "freezer_hint_seen",
                  "hp_hint_seen", "intro_seen_w2", "intro_seen_w3",
                  "intro_seen_w4", "intro_seen_w5", "intro_seen_w6"]


def _parse_size(s):
    w, h = s.lower().split("x")
    return int(w), int(h)


def _build_argparser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, required=True, help="start level 1..60")
    ap.add_argument("--seconds", type=float, default=18.0,
                    help="soft target of SELECTED footage; once reached the clip "
                         "ends at the next level completion (levels never cut)")
    ap.add_argument("--max-seconds", type=float, default=60.0,
                    help="hard safety cap on total captured frames")
    ap.add_argument("--max-retries", type=int, default=3,
                    help="attempts to clear a level before giving up (so a hard "
                         "level cannot loop waiting for a win)")
    ap.add_argument("--warmup", type=int, default=8,
                    help="(compat) per-attempt spawn-flash skip is fixed")
    ap.add_argument("--size", default="3840x2160")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--outdir", default=None,
                    help="dir for per-attempt clips + manifest.json")
    ap.add_argument("--shot", default=None, help="single PNG (smoke test)")
    ap.add_argument("--crf", type=int, default=16)
    ap.add_argument("--chain", action="store_true",
                    help="play consecutive levels of the same world")
    return ap


def main(argv=None):
    args = _build_argparser().parse_args(argv)
    w, h = _parse_size(args.size)
    fps = args.fps
    DT = 1.0 / float(fps)
    soft_target = int(round(args.seconds * fps))   # SELECTED frames before stopping
    hard_cap = 1 if args.shot else int(round(args.max_seconds * fps))
    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)

    # Kivy parses sys.argv at import; neutralise our flags first.
    sys.argv = ["main"]
    from kivy.config import Config
    Config.set("graphics", "width", str(w))
    Config.set("graphics", "height", str(h))
    Config.set("graphics", "resizable", "1")
    from kivy.core.window import Window   # create the singleton at our size
    from kivy.uix.modalview import ModalView
    import main as appmod
    from kivy.clock import Clock
    import autoplay
    import levels
    import graphics
    from tools.capture_cointex_core import grab_frame

    # Sprite animations (coin spin, idle bob, particles) are normally advanced by
    # graphics' OWN Clock.schedule_interval with real wall-clock dt. Under slow 4K
    # capture (~0.18s real per frame) that runs them ~10x too fast. Disable that
    # real-clock driver and step the sprites at the SAME fixed dt as the sim
    # (see _drive), so animation speed matches gameplay exactly.
    if graphics._anim_event is not None:
        graphics._anim_event.cancel()
        graphics._anim_event = None
    graphics._register = lambda s: graphics._anim_sprites.add(s)
    graphics._unregister = lambda s: graphics._anim_sprites.discard(s)

    app = appmod.CointexApp()

    st = {"settle": 0, "ready": False, "world": None, "level": args.level,
          "simt": 0.0, "ap_accum": 0.0, "pop": None,
          # current attempt
          "att_idx": 0, "att_file": None, "att_level": args.level,
          "ff": None, "att_frames": 0, "att_skip": 0,
          "att_events": [], "att_t0": None,
          # per-level + global bookkeeping
          "level_attempts": [], "retries": 0,
          "selected_total": 0, "total_emitted": 0, "manifest": []}
    SETTLE_FRAMES = 8
    ATTEMPT_WARMUP = 8     # skip the level-spawn flash at the start of each attempt

    def gs():
        return app.game

    def _wrap_audio():
        au = app.audio
        _orig_sfx = au.play_sfx
        _orig_music = au.play_level_music

        def play_sfx(name, *a, **k):
            st["att_events"].append({"t": st["simt"], "name": name})
            return _orig_sfx(name, *a, **k)

        def play_level_music(world, *a, **k):
            st["world"] = world
            return _orig_music(world, *a, **k)

        au.play_sfx = play_sfx
        au.play_level_music = play_level_music

    def _new_pop():
        return [(random.random(), random.random())
                for _ in range(autoplay.POPULATION)]

    def _begin_attempt(level):
        st["att_file"] = os.path.join(args.outdir, "attempt_%03d.mp4" % st["att_idx"])
        st["att_idx"] += 1
        st["att_level"] = level
        st["ff"] = None
        st["att_frames"] = 0
        st["att_skip"] = ATTEMPT_WARMUP
        st["att_events"] = []
        st["att_t0"] = None

    def _open_ffmpeg(path):
        cmd = [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", "%dx%d" % (w, h), "-r", str(fps), "-i", "-",
               "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", str(args.crf), "-preset", "fast",
               "-movflags", "+faststart", path]
        return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)

    def _emit(arr):
        if args.shot:
            os.makedirs(os.path.dirname(args.shot) or ".", exist_ok=True)
            Image.fromarray(arr).save(args.shot)
            return
        if st["att_skip"] > 0:                 # drop the spawn-in flash
            st["att_skip"] -= 1
            return
        if st["att_t0"] is None:
            st["att_t0"] = st["simt"]
        if st["ff"] is None:
            st["ff"] = _open_ffmpeg(st["att_file"])
        st["ff"].stdin.write(arr.tobytes())
        st["att_frames"] += 1
        st["total_emitted"] += 1

    def _close_attempt(outcome):
        if st["ff"] is not None:
            st["ff"].stdin.close()
            st["ff"].wait()
            st["ff"] = None
        if st["att_frames"] > 0:
            t0 = st["att_t0"] or 0.0
            evs = [{"t": e["t"] - t0, "name": e["name"]}
                   for e in st["att_events"] if e["t"] - t0 >= -0.05]
            st["manifest"].append({"file": os.path.basename(st["att_file"]),
                                   "level": st["att_level"], "outcome": outcome,
                                   "frames": st["att_frames"], "events": evs})
            st["level_attempts"].append({"outcome": outcome,
                                         "frames": st["att_frames"]})

    def _finish():
        if st["ff"] is not None:
            st["ff"].stdin.close()
            st["ff"].wait()
            st["ff"] = None
        if args.outdir:
            with open(os.path.join(args.outdir, "manifest.json"), "w") as f:
                json.dump({"fps": fps, "world": st["world"],
                           "attempts": st["manifest"]}, f)
        app.stop()

    def _dismiss_modals():
        for c in list(Window.children):
            if isinstance(c, ModalView):
                try:
                    c.dismiss(animation=False)
                except Exception:
                    pass

    def _next_level_same_world():
        nxt = st["level"] + 1
        same = (nxt - 1) // levels.LEVELS_PER_WORLD == \
               (st["level"] - 1) // levels.LEVELS_PER_WORLD
        return nxt if (nxt <= levels.NUM_LEVELS and same) else None

    def _reload(level):
        # Drop the win/lose modal and (re)load a level inline, starting a fresh
        # attempt clip. Used to advance on a win and to retry on a loss.
        _dismiss_modals()
        st["level"] = level
        _begin_attempt(level)
        app.game.load_level(level)
        try:
            app.game.auto_mode = True
            app.game._refresh_auto_button()
        except Exception:
            pass
        st["pop"] = _new_pop()
        st["ap_accum"] = 0.0

    def _ensure_ready():
        g = gs()
        if app.sm.current != "game" and g is not None and g.active:
            app.sm.current = "game"
        if g is None or g.player is None or not g.active:
            return False
        if getattr(g, "_update_event", None) is not None:
            g._update_event.cancel()
            g._update_event = None
        try:
            g.auto_mode = True
            g._refresh_auto_button()
        except Exception:
            pass
        st["ready"] = True
        return True

    def _step_ga(g):
        st["ap_accum"] += DT
        if st["ap_accum"] < autoplay.RETARGET_DELAY:
            return
        st["ap_accum"] = 0.0
        snap = autoplay.sense(g)
        if not snap or not snap.get("coins"):
            return
        ranked = sorted(st["pop"],
                        key=lambda p: autoplay.fitness(snap, p[0], p[1]),
                        reverse=True)
        best = ranked[0]
        if g.player is not None:
            g.player.tx = min(max(best[0], 0.05), 0.95)
            g.player.ty = min(max(best[1], 0.05), 0.95)
        if autoplay.should_fire(snap):
            g.fire()
        st["pop"] = g.auto._next_generation(ranked)

    def _resolve_win():
        # A cleared level contributes its longest failure (if any) + the win.
        loses = [a["frames"] for a in st["level_attempts"] if a["outcome"] == "lose"]
        wins = [a["frames"] for a in st["level_attempts"] if a["outcome"] == "win"]
        return (max(loses) if loses else 0) + (wins[-1] if wins else 0)

    def _resolve_giveup():
        loses = [a["frames"] for a in st["level_attempts"] if a["outcome"] == "lose"]
        return max(loses) if loses else 0

    def after_build(_dt):
        Window.size = (w, h)
        for f in SUPPRESS_FLAGS:
            try:
                app.state.set_setting(f, True)
            except Exception:
                pass
        _wrap_audio()
        if not args.shot:
            _begin_attempt(args.level)
        app._enter_level(args.level)
        st["pop"] = _new_pop()
        Clock.schedule_once(_drive, 0)

    def _drive(_dt):
        if st["settle"] < SETTLE_FRAMES or tuple(Window.size) != (w, h):
            if tuple(Window.size) != (w, h):
                Window.size = (w, h)
            st["settle"] += 1
            Clock.schedule_once(_drive, 0)
            return

        if not st["ready"]:
            if not _ensure_ready():
                Clock.schedule_once(_drive, 0)
                return

        g = gs()
        if getattr(g, "_update_event", None) is not None:
            g._update_event.cancel()
            g._update_event = None
        g.update(DT)
        graphics._global_tick(DT)      # advance sprite animations at the sim dt
        _step_ga(g)
        st["simt"] += DT

        # Level ended this step (do NOT grab — never films the result dialog).
        if not g.active and not args.shot:
            outcome = "win" if not g.coins else "lose"
            _close_attempt(outcome)
            under_cap = st["total_emitted"] < hard_cap
            if not args.chain or not under_cap:
                _finish()
                return
            if outcome == "win":
                st["selected_total"] += _resolve_win()
                st["level_attempts"] = []
                st["retries"] = 0
                nxt = _next_level_same_world()
                if st["selected_total"] < soft_target and nxt is not None:
                    _reload(nxt)
                    Clock.schedule_once(_drive, 0)
                    return
                _finish()
                return
            st["retries"] += 1
            if st["retries"] <= args.max_retries:
                _reload(st["level"])
                Clock.schedule_once(_drive, 0)
                return
            st["selected_total"] += _resolve_giveup()   # given up: keep longest fail
            _finish()
            return

        _emit(grab_frame(Window))
        if args.shot:
            app.stop()
            return
        if st["total_emitted"] >= hard_cap:            # safety only
            _close_attempt("lose")
            _finish()
            return
        Clock.schedule_once(_drive, 0)

    Clock.schedule_once(after_build, 0.3)
    app.run()


if __name__ == "__main__":
    main()
