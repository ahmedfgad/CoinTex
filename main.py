import kivy.app
import kivy.uix.screenmanager
import kivy.uix.image
import random
import kivy.core.audio
import os
import functools
import kivy.uix.behaviors
import pickle


def read_game_info():
    try:
        game_info_file = open("game_info", 'rb')
        game_info = pickle.load(game_info_file)
        return game_info[0]['lastlvl'], game_info[0]['congrats_displayed_once']
        game_info_file.close()
    except:
        print("CoinTex FileNotFoundError: Game info file is not found. Game starts from level 1.")
        return 1, False


def char_animation_completed(*args):
    character_image = args[1]
    character_image.im_num = character_image.start_im_num


def change_char_im(character_image):
    character_image.source = str(int(character_image.im_num)) + ".png"


def start_fire_animation(fire_widget, pos, anim_duration):
    fire_anim = kivy.animation.Animation(pos_hint=fire_widget.fire_start_pos_hint,
                                         duration=fire_widget.fire_anim_duration) + kivy.animation.Animation(
        pos_hint=fire_widget.fire_end_pos_hint, duration=fire_widget.fire_anim_duration)
    fire_anim.repeat = True
    fire_anim.start(fire_widget)


def back_to_main_screen(screenmanager, *args):
    screenmanager.current = "main"


class TestApp(kivy.app.App):
    music_dir = os.getcwd() + "/music/"

    def __init__(self):
        self.char_death_sound = kivy.core.audio.SoundLoader.load(self.music_dir + "char_death_flaute.wav")
        self.level_completed_sound = kivy.core.audio.SoundLoader.load(self.music_dir + "level_completed_flaute.wav")
        self.coin_sound = kivy.core.audio.SoundLoader.load(self.music_dir + "coin.wav")
        self.bg_music = kivy.core.audio.SoundLoader.load(self.music_dir + "bg_music_piano.wav")
        self.main_bg_music = kivy.core.audio.SoundLoader.load(self.music_dir + "bg_music_piano_flute.wav")

    def on_start(self):
        self.main_bg_music.loop = True
        self.main_bg_music.play()

        next_level_num, congrats_displayed_once = read_game_info()
        self.activate_levels(next_level_num, congrats_displayed_once)

    def activate_levels(self, next_level_num, congrats_displayed_once):
        num_levels = len(self.root.screens[0].ids['lvls_imagebuttons'].children)

        levels_imagebuttons = self.root.screens[0].ids['lvls_imagebuttons'].children
        for i in range(num_levels - next_level_num, num_levels):
            levels_imagebuttons[i].disabled = False
            levels_imagebuttons[i].color = [1, 1, 1, 1]

        for i in range(0, num_levels - next_level_num):
            levels_imagebuttons[i].disabled = True
            levels_imagebuttons[i].color = [1, 1, 1, 0.5]

        if next_level_num == (num_levels + 1) and congrats_displayed_once == False:
            self.root.current = "alllevelscompleted"

    def screen_on_pre_leave(self, screen_num):
        curr_screen = self.root.screens[screen_num]
        for i in range(curr_screen.num_monsters): curr_screen.ids[
            'monster' + str(i + 1) + '_image_lvl' + str(screen_num)].pos_hint = {'x': 0.8, 'y': 0.8}
        curr_screen.ids['character_image_lvl' + str(screen_num)].pos_hint = {'x': 0.0, 'y': 0.0}

        next_level_num, congrats_displayed_once = read_game_info()
        self.activate_levels(next_level_num, congrats_displayed_once)

    def screen_on_pre_enter(self, screen_num):
        curr_screen = self.root.screens[screen_num]
        curr_screen.character_killed = False
        curr_screen.num_coins_collected = 0
        curr_screen.ids['character_image_lvl' + str(screen_num)].im_num = curr_screen.ids[
            'character_image_lvl' + str(screen_num)].start_im_num
        for i in range(curr_screen.num_monsters): curr_screen.ids[
            'monster' + str(i + 1) + '_image_lvl' + str(screen_num)].im_num = curr_screen.ids[
            'monster' + str(i + 1) + '_image_lvl' + str(screen_num)].start_im_num
        curr_screen.ids['num_coins_collected_lvl' + str(screen_num)].text = "Coins 0/" + str(curr_screen.num_coins)
        curr_screen.ids['level_number_lvl' + str(screen_num)].text = "Level " + str(screen_num)

        curr_screen.num_collisions_hit = 0
        remaining_life_percent_lvl_widget = curr_screen.ids['remaining_life_percent_lvl' + str(screen_num)]
        remaining_life_percent_lvl_widget.size_hint = (
            remaining_life_percent_lvl_widget.remaining_life_size_hint_x,
            remaining_life_percent_lvl_widget.size_hint[1])

        for i in range(curr_screen.num_fires): curr_screen.ids[
            'fire' + str(i + 1) + '_lvl' + str(screen_num)].pos_hint = {'x': 1.1, 'y': 1.1}

        for key, coin in curr_screen.coins_ids.items():
            curr_screen.ids['layout_lvl' + str(screen_num)].remove_widget(coin)
        curr_screen.coins_ids = {}

        coin_width = 0.05
        coin_height = 0.05

        curr_screen = self.root.screens[screen_num]

        section_width = 1.0 / curr_screen.num_coins
        for k in range(curr_screen.num_coins):
            x = random.uniform(section_width * k, section_width * (k + 1) - coin_width)
            y = random.uniform(0, 1 - coin_height)
            coin = kivy.uix.image.Image(source="coin.png", size_hint=(coin_width, coin_height),
                                        pos_hint={'x': x, 'y': y}, allow_stretch=True)
            curr_screen.ids['layout_lvl' + str(screen_num)].add_widget(coin, index=-1)
            curr_screen.coins_ids['coin' + str(k)] = coin

    def screen_on_enter(self, screen_num):
        self.bg_music.loop = True
        self.bg_music.play()

        curr_screen = self.root.screens[screen_num]
        for i in range(curr_screen.num_monsters):
            monster_image = curr_screen.ids['monster' + str(i + 1) + '_image_lvl' + str(screen_num)]
            new_pos = (random.uniform(0.0, 1 - monster_image.size_hint[0] / 4),
                       random.uniform(0.0, 1 - monster_image.size_hint[1] / 4))
            self.start_monst_animation(monster_image=monster_image, new_pos=new_pos,
                                       anim_duration=random.uniform(monster_image.monst_anim_duration_low,
                                                                    monster_image.monst_anim_duration_high))

        for i in range(curr_screen.num_fires):
            fire_widget = curr_screen.ids['fire' + str(i + 1) + '_lvl' + str(screen_num)]
            start_fire_animation(fire_widget=fire_widget, pos=(0.0, 0.5), anim_duration=5.0)

    def start_monst_animation(self, monster_image, new_pos, anim_duration):
        monst_anim = kivy.animation.Animation(pos_hint={'x': new_pos[0], 'y': new_pos[1]},
                                              im_num=monster_image.end_im_num, duration=anim_duration)
        monst_anim.bind(on_complete=self.monst_animation_completed)
        monst_anim.start(monster_image)

    def monst_animation_completed(self, *args):
        monster_image = args[1]
        monster_image.im_num = monster_image.start_im_num

        new_pos = (random.uniform(0.0, 1 - monster_image.size_hint[0] / 4),
                   random.uniform(0.0, 1 - monster_image.size_hint[1] / 4))
        self.start_monst_animation(monster_image=monster_image, new_pos=new_pos,
                                   anim_duration=random.uniform(monster_image.monst_anim_duration_low,
                                                                monster_image.monst_anim_duration_high))

    def monst_pos_hint(self, monster_image):
        screen_num = int(monster_image.parent.parent.name[5:])
        curr_screen = self.root.screens[screen_num]
        character_image = curr_screen.ids['character_image_lvl' + str(screen_num)]

        character_center = character_image.center
        monster_center = monster_image.center

        gab_x = character_image.width / 2
        gab_y = character_image.height / 2
        if character_image.collide_widget(monster_image) and abs(
                character_center[0] - monster_center[0]) <= gab_x and abs(
            character_center[1] - monster_center[1]) <= gab_y:
            curr_screen.num_collisions_hit = curr_screen.num_collisions_hit + 1
            life_percent = float(curr_screen.num_collisions_hit) / float(curr_screen.num_collisions_level)

            remaining_life_percent_lvl_widget = curr_screen.ids['remaining_life_percent_lvl' + str(screen_num)]
            remaining_life_size_hint_x = remaining_life_percent_lvl_widget.remaining_life_size_hint_x
            remaining_life_percent_lvl_widget.size_hint = (
                remaining_life_size_hint_x - remaining_life_size_hint_x * life_percent,
                remaining_life_percent_lvl_widget.size_hint[1])

            if curr_screen.num_collisions_hit == curr_screen.num_collisions_level:
                self.bg_music.stop()
                self.char_death_sound.play()
                curr_screen.character_killed = True

                kivy.animation.Animation.cancel_all(character_image)
                for i in range(curr_screen.num_monsters): kivy.animation.Animation.cancel_all(
                    curr_screen.ids['monster' + str(i + 1) + '_image_lvl' + str(screen_num)])
                for i in range(curr_screen.num_fires): kivy.animation.Animation.cancel_all(
                    curr_screen.ids['fire' + str(i + 1) + '_lvl' + str(screen_num)])

                character_image.im_num = character_image.dead_start_im_num
                char_anim = kivy.animation.Animation(im_num=character_image.dead_end_im_num, duration=1.0)
                char_anim.start(character_image)
                kivy.clock.Clock.schedule_once(functools.partial(back_to_main_screen, curr_screen.parent), 3)

    def change_monst_im(self, monster_image):
        monster_image.source = str(int(monster_image.im_num)) + ".png"

    def touch_down_handler(self, screen_num, args):
        curr_screen = self.root.screens[screen_num]
        if not curr_screen.character_killed:
            self.start_char_animation(screen_num, args[1].spos)

    def start_char_animation(self, screen_num, touch_pos):
        curr_screen = self.root.screens[screen_num]
        character_image = curr_screen.ids['character_image_lvl' + str(screen_num)]
        character_image.im_num = character_image.start_im_num
        char_anim = kivy.animation.Animation(pos_hint={'x': touch_pos[0] - character_image.size_hint[0] / 2,
                                                       'y': touch_pos[1] - character_image.size_hint[1] / 2},
                                             im_num=character_image.end_im_num, duration=curr_screen.char_anim_duration)
        char_anim.bind(on_complete=char_animation_completed)
        char_anim.start(character_image)

    def char_pos_hint(self, character_image):
        screen_num = int(character_image.parent.parent.name[5:])
        character_center = character_image.center

        gab_x = character_image.width / 3
        gab_y = character_image.height / 3
        coins_to_delete = []
        curr_screen = self.root.screens[screen_num]

        for coin_key, curr_coin in curr_screen.coins_ids.items():
            curr_coin_center = curr_coin.center
            if character_image.collide_widget(curr_coin) and abs(
                    character_center[0] - curr_coin_center[0]) <= gab_x and abs(
                character_center[1] - curr_coin_center[1]) <= gab_y:
                self.coin_sound.play()
                coins_to_delete.append(coin_key)
                curr_screen.ids['layout_lvl' + str(screen_num)].remove_widget(curr_coin)
                curr_screen.num_coins_collected = curr_screen.num_coins_collected + 1
                curr_screen.ids['num_coins_collected_lvl' + str(screen_num)].text = "Coins " + str(
                    curr_screen.num_coins_collected) + "/" + str(curr_screen.num_coins)
                if curr_screen.num_coins_collected == curr_screen.num_coins:
                    self.bg_music.stop()
                    self.level_completed_sound.play()
                    kivy.clock.Clock.schedule_once(functools.partial(back_to_main_screen, curr_screen.parent), 3)
                    for i in range(curr_screen.num_monsters): kivy.animation.Animation.cancel_all(
                        curr_screen.ids['monster' + str(i + 1) + '_image_lvl' + str(screen_num)])
                    for i in range(curr_screen.num_fires): kivy.animation.Animation.cancel_all(
                        curr_screen.ids['fire' + str(i + 1) + '_lvl' + str(screen_num)])

                    next_level_num, congrats_displayed_once = read_game_info()
                    if (screen_num + 1) > next_level_num:
                        game_info_file = open("game_info", 'wb')
                        pickle.dump([{'lastlvl': screen_num + 1, "congrats_displayed_once": False}], game_info_file)
                        game_info_file.close()
                    else:
                        game_info_file = open("game_info", 'wb')
                        pickle.dump([{'lastlvl': next_level_num, "congrats_displayed_once": True}], game_info_file)
                        game_info_file.close()

        if len(coins_to_delete) > 0:
            for coin_key in coins_to_delete:
                del curr_screen.coins_ids[coin_key]

    def fire_pos_hint(self, fire_widget):
        screen_num = int(fire_widget.parent.parent.name[5:])
        curr_screen = self.root.screens[screen_num]
        character_image = curr_screen.ids['character_image_lvl' + str(screen_num)]

        character_center = character_image.center
        fire_center = fire_widget.center

        gab_x = character_image.width / 3
        gab_y = character_image.height / 3
        if character_image.collide_widget(fire_widget) and abs(character_center[0] - fire_center[0]) <= gab_x and abs(
                character_center[1] - fire_center[1]) <= gab_y:
            curr_screen.num_collisions_hit = curr_screen.num_collisions_hit + 1
            life_percent = float(curr_screen.num_collisions_hit) / float(curr_screen.num_collisions_level)

            remaining_life_percent_lvl_widget = curr_screen.ids['remaining_life_percent_lvl' + str(screen_num)]

            remaining_life_size_hint_x = remaining_life_percent_lvl_widget.remaining_life_size_hint_x
            remaining_life_percent_lvl_widget.size_hint = (
                remaining_life_size_hint_x - remaining_life_size_hint_x * life_percent,
                remaining_life_percent_lvl_widget.size_hint[1])

            if curr_screen.num_collisions_hit == curr_screen.num_collisions_level:
                self.bg_music.stop()
                self.char_death_sound.play()
                curr_screen.character_killed = True

                kivy.animation.Animation.cancel_all(character_image)
                for i in range(curr_screen.num_monsters): kivy.animation.Animation.cancel_all(
                    curr_screen.ids['monster' + str(i + 1) + '_image_lvl' + str(screen_num)])
                for i in range(curr_screen.num_fires): kivy.animation.Animation.cancel_all(
                    curr_screen.ids['fire' + str(i + 1) + '_lvl' + str(screen_num)])

                character_image.im_num = character_image.dead_start_im_num
                char_anim = kivy.animation.Animation(im_num=character_image.dead_end_im_num, duration=1.0)
                char_anim.start(character_image)
                kivy.clock.Clock.schedule_once(functools.partial(back_to_main_screen, curr_screen.parent), 3)

    def main_screen_on_enter(self):
        self.main_bg_music.play()

    def main_screen_on_leave(self):
        self.main_bg_music.stop()


class ImageButton(kivy.uix.behaviors.ButtonBehavior, kivy.uix.image.Image):
    pass


class MainScreen(kivy.uix.screenmanager.Screen):
    pass


class AboutUs(kivy.uix.screenmanager.Screen):
    pass


class AllLevelsCompleted(kivy.uix.screenmanager.Screen):
    pass


class Level1(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 5
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.0
    num_monsters = 1
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 20


class Level2(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 8
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.1
    num_monsters = 1
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 30


class Level3(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 12
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.2
    num_monsters = 1
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 30


class Level4(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 10
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.2
    num_monsters = 1
    num_fires = 1
    num_collisions_hit = 0
    num_collisions_level = 20


class Level5(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.3
    num_monsters = 1
    num_fires = 2
    num_collisions_hit = 0
    num_collisions_level = 20


class Level6(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 12
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.3
    num_monsters = 1
    num_fires = 3
    num_collisions_hit = 0
    num_collisions_level = 20


class Level7(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 10
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.4
    num_monsters = 3
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 25


class Level8(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.4
    num_monsters = 2
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 25


class Level9(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 12
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.5
    num_monsters = 2
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 25


class Level10(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 14
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.5
    num_monsters = 3
    num_fires = 0
    num_collisions_hit = 0
    num_collisions_level = 30


class Level11(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.6
    num_monsters = 2
    num_fires = 1
    num_collisions_hit = 0
    num_collisions_level = 30


class Level12(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 12
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.6
    num_monsters = 2
    num_fires = 1
    num_collisions_hit = 0
    num_collisions_level = 30


class Level13(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 10
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.7
    num_monsters = 2
    num_fires = 2
    num_collisions_hit = 0
    num_collisions_level = 20


class Level14(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.7
    num_monsters = 0
    num_fires = 6
    num_collisions_hit = 0
    num_collisions_level = 30


class Level15(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 16
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.8
    num_monsters = 2
    num_fires = 3
    num_collisions_hit = 0
    num_collisions_level = 30


class Level16(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.8
    num_monsters = 3
    num_fires = 2
    num_collisions_hit = 0
    num_collisions_level = 35


class Level17(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 10
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.3
    num_monsters = 0
    num_fires = 4
    num_collisions_hit = 0
    num_collisions_level = 30


class Level18(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.5
    num_monsters = 3
    num_fires = 4
    num_collisions_hit = 0
    num_collisions_level = 30


class Level19(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 12
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.2
    num_monsters = 0
    num_fires = 6
    num_collisions_hit = 0
    num_collisions_level = 30


class Level20(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 15
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.1
    num_monsters = 0
    num_fires = 8
    num_collisions_hit = 0
    num_collisions_level = 30


class Level20(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 20
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.1
    num_monsters = 2
    num_fires = 4
    num_collisions_hit = 0
    num_collisions_level = 30


class Level21(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 18
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.3
    num_monsters = 2
    num_fires = 4
    num_collisions_hit = 0
    num_collisions_level = 30


class Level22(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 20
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.3
    num_monsters = 2
    num_fires = 4
    num_collisions_hit = 0
    num_collisions_level = 30


class Level23(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 25
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.1
    num_monsters = 2
    num_fires = 2
    num_collisions_hit = 0
    num_collisions_level = 30


class Level24(kivy.uix.screenmanager.Screen):
    character_killed = False
    num_coins = 20
    num_coins_collected = 0
    coins_ids = {}
    char_anim_duration = 1.1
    num_monsters = 3
    num_fires = 2
    num_collisions_hit = 0
    num_collisions_level = 30


app = TestApp(title="CoinTex")
app.run()
