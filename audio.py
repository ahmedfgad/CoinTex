# Plays the music and sound effects and respects the player's settings.
# There is one menu track and a separate in-level track for each world, so the
# music changes as the player moves through the worlds. The sound effects are
# shipped wav files, so this module only loads and plays files (no numpy needed).

import os
from kivy.core.audio import SoundLoader

import levels

MENU_MUSIC = "bg_music_piano_flute.wav"


def world_music_name(world):
    return "bg_music_world{}.wav".format(world)


# name used in code -> wav file in the music folder
SFX_FILES = {
    "coin": "coin.wav",
    "level_complete": "level_completed_flaute.wav",
    "death": "char_death_flaute.wav",
    "shoot": "sfx_shoot.wav",
    "hit": "sfx_hit.wav",
    "monster_death": "sfx_monster_death.wav",
    "damage": "sfx_damage.wav",
    "click": "sfx_click.wav",
    "victory": "sfx_victory.wav",
}


class AudioManager:
    def __init__(self, music_dir, get_setting):
        # get_setting is a function(key) that returns a setting value.
        self.music_dir = music_dir
        self.get_setting = get_setting
        self._menu = None
        self._world = {}      # world number -> Sound
        self._sfx = {}
        self._current = None  # ("menu",) or ("world", number)
        self._load()

    def _load_sound(self, filename, loop=False):
        path = os.path.join(self.music_dir, filename)
        if not os.path.exists(path):
            return None
        sound = SoundLoader.load(path)
        if sound is not None:
            sound.loop = loop
        return sound

    def _load(self):
        self._menu = self._load_sound(MENU_MUSIC, loop=True)
        for world in range(1, levels.NUM_WORLDS + 1):
            self._world[world] = self._load_sound(world_music_name(world), loop=True)
        for name, filename in SFX_FILES.items():
            self._sfx[name] = self._load_sound(filename, loop=False)

    def _volume(self):
        try:
            return float(self.get_setting("volume"))
        except (TypeError, ValueError):
            return 1.0

    def _sound_for(self, key):
        if key is None:
            return None
        if key[0] == "menu":
            return self._menu
        return self._world.get(key[1])

    def _all_music(self):
        return [self._menu] + list(self._world.values())

    def play_menu_music(self):
        self._switch(("menu",))

    def play_level_music(self, world):
        self._switch(("world", world))

    def _switch(self, key):
        if self._current == key:
            sound = self._sound_for(key)
            if sound is not None and sound.state == "play":
                return
        self.stop_music()
        self._current = key
        if not self.get_setting("music_on"):
            return
        sound = self._sound_for(key)
        if sound is not None:
            sound.volume = self._volume()
            sound.play()

    def stop_music(self):
        for sound in self._all_music():
            if sound is not None and sound.state == "play":
                sound.stop()

    def play_sfx(self, name):
        if not self.get_setting("sfx_on"):
            return
        sound = self._sfx.get(name)
        if sound is not None:
            sound.volume = self._volume()
            if sound.state == "play":
                sound.stop()
            sound.play()

    def apply_settings(self):
        # Call after settings change so music/volume follow the new values.
        volume = self._volume()
        for sound in self._all_music():
            if sound is not None:
                sound.volume = volume
        if not self.get_setting("music_on"):
            self.stop_music()
        elif self._current is not None:
            current = self._sound_for(self._current)
            if current is not None and current.state != "play":
                current.volume = volume
                current.play()
