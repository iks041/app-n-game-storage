import base64
import json
import logging
import math
import os
import queue
import random
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import wave

if sys.platform == "win32":
    import winsound


WIDTH = 960
HEIGHT = 640
MAX_FLOORS = 200
ARENA = (24, 92, WIDTH - 24, HEIGHT - 48)
REGIONS = [
    ("ASHEN FRONT", "#45544a", "#b7955f", "#60725c"),
    ("FROSTLINE PASS", "#496777", "#b2d8e6", "#617d89"),
    ("REDSTONE WASTES", "#704b3c", "#dd9b62", "#8e6245"),
    ("IRONWOOD", "#3f6749", "#9bb96d", "#577752"),
]
REGION_ACCENTS = ("#f1b85a", "#8ee5f0", "#ff8c54", "#a5d46d")
ROMAN_NUMERALS = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")
QUEST_OPTIONS = (
    ("CLEAR THE HALL", "Defeat 6 enemies", 6),
    ("HARDEN THE FRONT", "Defeat 9 enemies", 9),
    ("SWEEP THE FLOOR", "Defeat 12 enemies", 12),
)
QUEST_REWARD_BONUSES = (0, 10, 20)
TOWER_MINIONS = (
    ("Vesper, the Glasswing", "A shadow with your face pulled the Demon King through a black gate."),
    ("Korr, the Chainbound", "The kidnapper steps between moments. Watch for the space bending behind you."),
    ("Nhalia, the Ash Seer", "Five seals bind the Demon King. Each of us carried one clue."),
    ("Drazhul, the Gate Eater", "The last seal opens a shortcut. Seek the throne passage, not the long stairs."),
    ("Mordane, the Hollow Fang", "The one who took him is his own shadow, wearing a stolen shape."),
)
BOSS_SKILLS = (
    ("Groundsplit", 'Earth, answer me! Groundsplit!',
     "You have earned my Groundsplit. Make it count."),
    ("Frost Nova", 'Winter, rise! Frost Nova!',
     "Take my Frost Nova. Let the cold guard your path."),
    ("Ember Volley", 'Burn bright! Ember Volley!',
     "The Ember Volley is yours. Aim true, little spark."),
    ("Ironbark Guard", 'Roots, guard me! Ironbark Guard!',
     "My Ironbark Guard is yours. Stand firm."),
)
MILESTONE_BOSS_SKILLS = (
    ("Time Freeze", "Time, stand still! Time Freeze!",
     "Time bends to my will. Use the pause to strike."),
    ("Ice Stars", "Winter sky, fall! Ice Stars!",
     "Call the stars down wherever your enemies gather."),
    ("Epic Fall", "Become the mountain! Epic Fall!",
     "Grow mighty, then bring the whole battlefield down."),
)
ALL_BOSS_SKILLS = BOSS_SKILLS + MILESTONE_BOSS_SKILLS
MAX_ABILITIES = 5
TARGETED_SKILLS = frozenset(("Ice Stars", "Epic Fall"))
SIDE_QUESTS = (
    ("superhuman", "Become a Superhuman", "superhuman", 1, 25),
    ("buy_weapon_1", "Buy 1 special weapon", "weapons_purchased", 1, 5),
    ("obtain_skill_1", "Obtain 1 skill", "skills_obtained", 1, 4),
    ("forge_skill_1", "Forge 1 skill", "skills_forged", 1, 7),
    ("buy_weapon_5", "Buy 5 special weapons", "weapons_purchased", 5, 10),
    ("obtain_skill_3", "Obtain 3 skills", "skills_obtained", 3, 7),
    ("forge_skill_3", "Forge 3 skills", "skills_forged", 3, 12),
    ("obtain_skill_7", "Obtain 7 skills", "skills_obtained", 7, 18),
    ("forge_skill_10", "Forge 10 skills", "skills_forged", 10, 20),
)
SKILL_DAMAGE_RANGE = {
    "Groundsplit": (130, 320),
    "Frost Nova": (85, 235),
    "Ember Volley": (350, 460),
    "Ironbark Guard": (60, 325),
    "Time Freeze": (100, 400),
    "Ice Stars": (310, 90),
    "Epic Fall": (175, 105),
}
FORGED_SKILL_NAMES = {
    "Groundsplit": "Quake",
    "Frost Nova": "Glacius",
    "Ember Volley": "Pyro",
    "Ironbark Guard": "Thorn",
    "Time Freeze": "Chrono",
    "Ice Stars": "Astral",
    "Epic Fall": "Titan",
}
SAVE_VERSION = 1
MINION_DIFFICULTIES = (
    ("SCOUT", 100_000, 200),
    ("WARRIOR", 250_000, 500),
    ("DEMON SLAYER", 500_000, 1_000),
)
MARKET_WEAPON_COUNT = 1_000
SPECIAL_SHOTS_PER_FLOOR = 3
AUTO_SAVE_INTERVAL = 10
MARKET_WEAPONS = tuple(
    {
        "id": index,
        "name": f"{('Prism Lance', 'Frostfire Rocket', 'Starfall Bomb')[index % 3]} "
                f"{index + 1:04d}",
        "type": ("LASER", "ROCKET", "ATOMIC")[index % 3],
        "price": math.floor((5_000 + (index // 3) * 125) * 0.35 + 0.5),
    }
    for index in range(MARKET_WEAPON_COUNT)
)
BOSS_DIALOGUES = (
    "I WILL KILL YOU!",
    "ONLY DEATH AWAITS YOU!",
    "NO ONE CAN SAVE YOU FROM THE WRATH OF MY SKILLS!",
    "YOUR LAST STAND ENDS HERE!",
)
BOSS_DEFEAT_DIALOGUE = (
    "I acknowledge your power and might to kill me. I give you my skill."
)
COSMETIC_ITEMS = {
    "HAIR": (
        ("Close Crop", 0, "#4b4238"),
        ("Ranger Sweep", 18, "#c9a65a"),
        ("Wild Tuft", 30, "#6a493c"),
        ("Silver Crest", 45, "#b9c3c0"),
    ),
    "GUN": (
        ("Service Rifle", 0, "#858678"),
        ("Scattergun", 25, "#c47c4c"),
        ("Longshot", 35, "#81a4b0"),
        ("Ember Carbine", 50, "#e07a45"),
        ("Warden Breaker", 0, "#f0c45a"),
    ),
    "GLOVES": (
        ("Field Wraps", 0, "#303530"),
        ("Leather Grips", 15, "#9a6848"),
        ("Iron Gauntlets", 30, "#9da6a2"),
        ("Frost Gloves", 45, "#8ee5f0"),
    ),
    "MASK": (
        ("No Mask", 0, ""),
        ("Cloth Mask", 20, "#b69a75"),
        ("Iron Visor", 35, "#899b9d"),
        ("Ashen Mask", 50, "#6e7774"),
    ),
    "OUTFIT": (
        ("Scout Jacket", 0, "#72a2ad"),
        ("Wasteland Coat", 35, "#9f7352"),
        ("Frost Mantle", 45, "#779da8"),
        ("Ironwood Armor", 55, "#687e58"),
    ),
}


class GameAudio:
    def __init__(self, root):
        self.root = root
        self._directory = tempfile.TemporaryDirectory(prefix="ashen_front_audio_")
        self._sounds = {}
        self._voice_queue = queue.Queue(maxsize=3)
        self._voice_process = None
        self._voice_thread = None
        for name, start_hz, end_hz, duration, volume in (
            ("shot", 1250, 260, 0.075, 0.65),
            ("kill", 390, 1050, 0.16, 0.7),
            ("impact", 310, 115, 0.09, 0.5),
        ):
            path = f"{self._directory.name}\\{name}.wav"
            self._write_tone(path, start_hz, end_hz, duration, volume)
            self._sounds[name] = path
        if sys.platform == "win32":
            self._voice_thread = threading.Thread(
                target=self._voice_worker, daemon=True
            )
            self._voice_thread.start()

    @staticmethod
    def _write_tone(path, start_hz, end_hz, duration, volume):
        sample_rate = 22050
        sample_count = int(sample_rate * duration)
        samples = bytearray()
        phase = 0.0
        for index in range(sample_count):
            progress = index / max(1, sample_count - 1)
            frequency = start_hz + (end_hz - start_hz) * progress
            phase += 2 * math.pi * frequency / sample_rate
            envelope = min(
                1.0,
                index / (sample_rate * 0.008),
                (sample_count - index) / (sample_rate * 0.018),
            )
            value = int(32767 * volume * max(0, envelope) * math.sin(phase))
            samples.extend(struct.pack("<h", value))
        with wave.open(path, "wb") as audio_file:
            audio_file.setnchannels(1)
            audio_file.setsampwidth(2)
            audio_file.setframerate(sample_rate)
            audio_file.writeframes(samples)

    def play(self, name):
        if sys.platform == "win32":
            try:
                winsound.PlaySound(
                    self._sounds[name],
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
            except (OSError, RuntimeError):
                logging.exception("Could not play the %s sound effect", name)
        else:
            self.root.bell()

    def speak(self, text):
        if sys.platform != "win32":
            return
        try:
            self._voice_queue.put_nowait(text)
        except queue.Full:
            try:
                self._voice_queue.get_nowait()
            except queue.Empty:
                pass
            self._voice_queue.put_nowait(text)

    def _voice_worker(self):
        script = """
Add-Type -AssemblyName System.Speech
$voice = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice.Volume = 82
while (($line = [Console]::In.ReadLine()) -ne $null) {
    $text = [Text.Encoding]::UTF8.GetString(
        [Convert]::FromBase64String($line)
    )
    $voice.Speak($text)
}
$voice.Dispose()
"""
        encoded_script = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-NonInteractive",
                 "-EncodedCommand", encoded_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                text=True,
                encoding="ascii",
                bufsize=1,
            )
        except OSError:
            logging.exception("Could not start Windows speech synthesis")
            return
        self._voice_process = process
        while True:
            text = self._voice_queue.get()
            if text is None:
                break
            if process.poll() is not None:
                logging.error("Windows speech synthesis exited unexpectedly")
                return
            try:
                encoded_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
                process.stdin.write(encoded_text + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                logging.exception("Could not send dialogue to Windows speech synthesis")
                return
        process.stdin.close()

    def close(self):
        while True:
            try:
                self._voice_queue.get_nowait()
            except queue.Empty:
                break
        self._voice_queue.put(None)
        if sys.platform == "win32":
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except (OSError, RuntimeError):
                logging.exception("Could not stop the current sound effect")
            if self._voice_process and self._voice_process.poll() is None:
                self._voice_process.terminate()
        self._directory.cleanup()


class BattlefieldRPG:
    def __init__(self, root):
        self.root = root
        self.root.title("Ashen Front")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(
            root, width=WIDTH, height=HEIGHT, bg="#171d20", highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.save_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ashen_front_save.json"
        )
        self.save_notice = ""
        self.save_notice_until = 0

        self.keys = set()
        self.decor = self.make_decor()
        mote_rng = random.Random(731)
        self.ambient_motes = [
            (
                mote_rng.random(),
                mote_rng.random(),
                mote_rng.uniform(7, 24),
                mote_rng.uniform(0, math.tau),
                mote_rng.choice((2, 3, 4)),
            )
            for _ in range(18)
        ]
        self.mouse_position = (WIDTH / 2 + 100, HEIGHT / 2)
        self.state = "menu"
        self.last_tick = time.monotonic()
        self.audio = GameAudio(root)
        self.owned_cosmetics = {
            category: {items[0][0]} for category, items in COSMETIC_ITEMS.items()
        }
        self.equipped_cosmetics = {
            category: items[0][0] for category, items in COSMETIC_ITEMS.items()
        }
        self.customize_category = 0
        self.customize_item = 0
        self.pending_cosmetic_chest = None
        self.new_game()
        self.state = "menu"
        self.draw_background()
        self.tick()

    def make_decor(self):
        rng = random.Random(17)
        items = []
        for _ in range(52):
            x = rng.randint(ARENA[0] + 14, ARENA[2] - 14)
            y = rng.randint(ARENA[1] + 14, ARENA[3] - 14)
            kind = rng.choice(("stone", "grass", "crater"))
            size = rng.randint(3, 10) if kind != "crater" else rng.randint(12, 24)
            items.append((x, y, kind, size))
        return items

    def new_game(self):
        self.player = {
            "x": WIDTH / 2,
            "y": (ARENA[1] + ARENA[3]) / 2,
            "hp": 100,
            "max_hp": 100,
            "level": 1,
            "xp": 0,
            "next_xp": 40,
            "speed": 190,
            "face": (1.0, 0.0),
            "attack_until": 0,
            "attack_ready": 0,
            "hurt_until": 0,
            "shoot_until": 0,
            "ability_ready": 0,
            "ability_until": 0,
            "knockdown_until": 0,
            "shield_until": 0,
            "frozen_until": 0,
        }
        self.enemies = []
        self.pickups = []
        self.projectiles = []
        self.effects = []
        self.boss_corpses = []
        self.boss_chests = []
        self.wave = 1
        self.floor_number = 1
        self.floor_wave = 1
        self.encounter_clear = False
        self.replay_active = False
        self.replay_return_snapshot = None
        self.wave_left = 0
        self.wave_pause = 0
        self.minion_difficulty = None
        self.floor_records = {}
        self.progression_page = 0
        self.progression_selected_floor = 1
        self.progression_return_state = "menu"
        self.market_stand_floor = None
        self.market_page = 0
        self.market_filter = "ALL"
        self.market_search = ""
        self.skill_market_page = 0
        self.preview_weapon_id = None
        self.weapon_test_started_at = 0
        self.pending_purchase = None
        self.owned_special_weapons = []
        self.equipped_special_weapon = None
        self.special_shots_left = SPECIAL_SHOTS_PER_FLOOR
        self.special_loadout_page = 0
        self.special_loadout_return_state = "menu"
        self.special_loadout_tab = "weapons"
        self.skill_copies = []
        self.crafted_skill_data = {}
        self.next_crafted_skill_id = 1
        self.forge_selected_skills = []
        self.forge_page = 0
        self.evolved = False
        self.superhuman_active = False
        self.superhuman_original_stats = None
        self.superhuman_xp_earned = 0
        self.forge_animation_started_at = 0
        self.forge_animation_name = ""
        self.quick_loadout_open = False
        self.quick_loadout_page = 0
        self.side_quests_return_state = "marketplace"
        self.last_autosave_at = time.monotonic()
        self.kills = 0
        self.floor_kills_start = 0
        self.coins = 1_000
        self.gems = 0
        self.side_quest_stats = {
            "weapons_purchased": 0,
            "skills_obtained": 0,
            "skills_forged": 0,
            "superhuman": 0,
        }
        self.side_quests_claimed = set()
        self.auto_aim_enabled = False
        self.region = 0
        self.territories = [False] * len(REGIONS)
        self.territories[0] = True
        self.has_boss_ability = False
        self.unlocked_abilities = []
        self.equipped_abilities = []
        self.active_ability = 0
        self.ability_cooldowns = {}
        self.pending_target_ability = None
        self.time_freeze_until = 0
        self.time_freeze_owner = None
        self.message = ""
        self.message_until = 0
        self.weapon_upgrade = 0
        self.skill_upgrade = 0
        self.health_upgrade = 0
        self.stage_intro_until = 0
        self.boss_warning_until = 0
        self.boss_cutscene_until = 0
        self.boss_dialogue_until = 0
        self.skill_acquire_progress = 0
        self.pending_skill = None
        self.boss_weapon_owned = False
        self.advanced_gun_owned = "Warden Breaker" in self.owned_cosmetics["GUN"]
        self.quests_completed = set()
        self.active_quest = None
        self.quest_progress = 0
        self.quest_reward = 0
        self.quest_rewards = []
        self.quest_complete = False
        self.active_quest_index = 0
        self.tower_clues = []
        self.rescue_route_unlocked = False
        self.rescue_battle = False
        self.demon_ally_next_attack = 0
        self.kidnapper_reveal_until = 0
        self.opening_cutscene_started = 0
        self.last_spoken_dialogue = None
        self.clue_dialogue = ""
        self.post_boss_at = 0
        self.travel_ready_at = 0
        self.shop_return_state = "post_boss"
        self.map_return_state = "playing"
        self.spawn_wave()

    def stage_number(self):
        return max(1, min(MAX_FLOORS, self.floor_number))

    def stage_label(self):
        return f"FLOOR {self.stage_number()}/{MAX_FLOORS}"

    def regular_waves_per_floor(self, floor=None):
        floor = self.stage_number() if floor is None else floor
        return 3 + 2 * ((floor - 1) // 5)

    def is_minion_boss_wave(self):
        return (
            not self.rescue_battle
            and self.stage_number() >= 15
            and self.stage_number() % 5 == 0
            and self.floor_wave == self.regular_waves_per_floor() + 1
        )

    def floor_wave_count(self, floor=None):
        floor = self.stage_number() if floor is None else floor
        return self.regular_waves_per_floor(floor) + (
            2 if floor >= 15 and floor % 5 == 0 else 1
        )

    def begin_floor(self, floor):
        self.floor_number = max(1, min(MAX_FLOORS, floor))
        self.floor_wave = 1
        self.active_quest = None
        self.quest_progress = 0
        self.quest_complete = False
        self.encounter_clear = False
        self.wave += 1
        self.wave_left = 0
        self.wave_pause = 0
        self.minion_difficulty = None
        self.special_shots_left = SPECIAL_SHOTS_PER_FLOOR
        self.floor_kills_start = self.kills
        self.pending_target_ability = None
        self.boss_corpses.clear()
        self.boss_chests.clear()
        self.pickups.clear()
        self.projectiles.clear()
        self.effects.clear()
        self.spawn_wave()
        self.save_game()

    def spawn_wave(self):
        regular_waves = self.regular_waves_per_floor()
        if self.floor_wave > regular_waves:
            self.wave_left = 1
            if self.is_minion_boss_wave():
                self.state = "minion_difficulty"
                self.message = "CHOOSE THE DEMON MINION'S DIFFICULTY"
            else:
                self.message = "BOSS WAVE  -  " + self.boss_name()
                self.state = "boss_warning"
                self.boss_warning_until = time.monotonic() + 3
        else:
            self.wave_left = 4 + self.stage_number() * 2 + self.floor_wave * 2
            stage = ROMAN_NUMERALS[(self.stage_number() - 1) % len(ROMAN_NUMERALS)]
            self.message = (
                f"FLOOR {self.stage_number()}  -  WAVE "
                f"{self.floor_wave}/{self.regular_waves_per_floor()}  -  HOLD THE LINE"
            )
        self.message_until = time.monotonic() + 2.2

    def select_minion_difficulty(self, difficulty_index):
        if not 0 <= difficulty_index < len(MINION_DIFFICULTIES):
            return
        self.minion_difficulty = difficulty_index
        difficulty, health, reward = MINION_DIFFICULTIES[difficulty_index]
        self.state = "boss_warning"
        self.boss_warning_until = time.monotonic() + 3
        self.message = (
            f"{difficulty} MINION  -  {health:,} HP  -  "
            f"{reward:,} COINS ON DEFEAT"
        )
        self.message_until = self.boss_warning_until

    def boss_name(self):
        if self.rescue_battle:
            return "The Veil Thief"
        floor = self.stage_number()
        if self.is_minion_boss_wave():
            return TOWER_MINIONS[(floor // 5 - 1) % len(TOWER_MINIONS)][0]
        names = ("The Faultkeeper", "Rimebreaker", "The Red Maw", "Ironwood Colossus")
        return names[(floor - 1) % len(names)]

    def boss_dialogue(self):
        if self.rescue_battle:
            return "Your borrowed weapon cannot touch the truth behind me!"
        floor = self.stage_number()
        if self.is_minion_boss_wave():
            return TOWER_MINIONS[(floor // 5 - 1) % len(TOWER_MINIONS)][1]
        return BOSS_DIALOGUES[(floor - 1) % len(BOSS_DIALOGUES)]

    def boss_skill(self):
        milestone = min(
            len(MILESTONE_BOSS_SKILLS), self.player["level"] // 10
        )
        if milestone:
            return MILESTONE_BOSS_SKILLS[milestone - 1]
        return BOSS_SKILLS[(self.stage_number() - 1) % len(BOSS_SKILLS)]

    def boss_skills(self):
        primary = self.boss_skill()
        if not self.is_minion_boss_wave() or self.rescue_battle:
            return [primary]
        primary_index = ALL_BOSS_SKILLS.index(primary)
        return [primary, ALL_BOSS_SKILLS[(primary_index + 1) % len(ALL_BOSS_SKILLS)]]

    def has_all_boss_skills(self):
        return all(skill in self.unlocked_abilities for skill in ALL_BOSS_SKILLS)

    def player_radius(self):
        return 20 if self.evolved or self.superhuman_active else 15

    def apply_evolution(self, save=True, heal=True):
        if self.superhuman_active or self.evolved or len(self.skill_copies) < 7:
            return False
        self.superhuman_original_stats = {
            **{
                field: self.player[field]
                for field in ("level", "xp", "next_xp", "speed", "max_hp", "hp")
            },
            "weapon_upgrade": self.weapon_upgrade,
            "skill_upgrade": self.skill_upgrade,
            "health_upgrade": self.health_upgrade,
        }
        self.superhuman_xp_earned = 0
        self.superhuman_active = True
        self.player.update({
            "level": 100,
            "xp": 0,
            "next_xp": 40,
            "max_hp": 100_000,
            "hp": 100_000 if heal else min(self.player["hp"], 100_000),
        })
        self.weapon_upgrade = 100
        self.skill_upgrade = 100
        self.health_upgrade = 100
        self.track_side_quest_progress("superhuman")
        self.message = "SUPERHUMAN AWAKENED  -  POWER LASTS UNTIL THE FLOOR BOSS FALLS"
        self.message_until = time.monotonic() + 4
        if save:
            self.save_game()
        return True

    def end_superhuman(self, save=True):
        if not self.superhuman_active:
            return
        original = self.superhuman_original_stats
        if isinstance(original, dict):
            for field in ("level", "xp", "next_xp", "speed", "max_hp", "hp"):
                self.player[field] = original[field]
            for field in ("weapon_upgrade", "skill_upgrade", "health_upgrade"):
                setattr(self, field, original[field])
            self.player["xp"] += self.superhuman_xp_earned
        self.superhuman_active = False
        self.superhuman_original_stats = None
        self.superhuman_xp_earned = 0
        if isinstance(original, dict):
            self.check_level_up()
        self.message = "FLOOR BOSS DEFEATED  -  SUPERHUMAN FORM ENDED"
        self.message_until = time.monotonic() + 3
        if save:
            self.save_game()

    @staticmethod
    def gem_price(coin_price):
        return max(1, math.ceil(coin_price / 1_000))

    def track_side_quest_progress(self, counter, amount=1):
        if counter not in self.side_quest_stats or amount <= 0:
            return
        self.side_quest_stats[counter] += amount
        self.award_side_quests()

    def award_side_quests(self, save=True):
        newly_awarded = []
        for quest_id, title, counter, target, reward in SIDE_QUESTS:
            if (quest_id not in self.side_quests_claimed
                    and self.side_quest_stats[counter] >= target):
                self.side_quests_claimed.add(quest_id)
                self.gems += reward
                newly_awarded.append((title, reward))
        if newly_awarded:
            reward_total = sum(reward for _, reward in newly_awarded)
            self.message = f"SIDE QUEST COMPLETE  +{reward_total} GEMS"
            self.message_until = time.monotonic() + 3
            if save:
                self.save_game()

    def open_side_quests(self, return_state):
        self.quick_loadout_open = False
        self.side_quests_return_state = return_state
        self.state = "side_quests"

    def skill_damage_range(self, skill):
        if skill[0] in self.crafted_skill_data:
            data = self.crafted_skill_data[skill[0]]
            return data["damage"], data["range"]
        return SKILL_DAMAGE_RANGE[skill[0]]

    def visible_skill_copies(self):
        counts = {}
        for skill in self.skill_copies:
            counts[skill] = counts.get(skill, 0) + 1
        return list(counts.items())

    def open_skill_forge(self):
        self.forge_selected_skills = []
        self.forge_page = 0
        self.state = "skill_forge"

    def open_skill_market(self):
        self.skill_market_page = 0
        self.state = "skill_market"

    def request_market_purchase(self, kind, item_id, return_state):
        if kind == "weapon":
            if not isinstance(item_id, int) or not 0 <= item_id < len(MARKET_WEAPONS):
                return
            item = MARKET_WEAPONS[item_id]
            name, price = item["name"], item["price"]
            already_owned = item_id in self.owned_special_weapons
        elif kind == "skill":
            if not isinstance(item_id, int) or not 0 <= item_id < len(ALL_BOSS_SKILLS):
                return
            item = ALL_BOSS_SKILLS[item_id]
            name, price = item[0], MARKET_WEAPONS[item_id]["price"]
            already_owned = False
        else:
            return
        if already_owned:
            self.message = f"{name.upper()} IS ALREADY OWNED"
            self.message_until = time.monotonic() + 2
            return
        if return_state not in ("skill_market", "weapon_preview"):
            return
        self.pending_purchase = {
            "kind": kind,
            "item_id": item_id,
            "return_state": return_state,
        }
        self.state = "purchase_confirmation"

    def complete_market_purchase(self, currency):
        purchase = self.pending_purchase
        if not isinstance(purchase, dict):
            self.state = "marketplace"
            return
        kind, item_id = purchase.get("kind"), purchase.get("item_id")
        details = self.pending_purchase_details()
        if details is None or currency not in ("coins", "gems"):
            self.message = "PURCHASE CANCELLED  -  ITEM OR PAYMENT IS UNAVAILABLE"
            self.pending_purchase = None
            self.state = purchase.get("return_state", "marketplace")
            return
        price = details[1]
        cost = price if currency == "coins" else self.gem_price(price)
        balance = self.coins if currency == "coins" else self.gems
        if balance < cost:
            self.message = (
                f"NOT ENOUGH {currency.upper()}  -  NEED {cost:,}"
            )
            self.message_until = time.monotonic() + 2.5
            return
        if kind == "weapon" and isinstance(item_id, int) and 0 <= item_id < len(MARKET_WEAPONS):
            weapon = MARKET_WEAPONS[item_id]
            if item_id in self.owned_special_weapons:
                self.message = "SPECIAL WEAPON IS ALREADY OWNED"
            else:
                if currency == "coins":
                    self.coins -= cost
                else:
                    self.gems -= cost
                self.owned_special_weapons.append(item_id)
                self.track_side_quest_progress("weapons_purchased")
                self.message = f'{weapon["name"].upper()} PURCHASED'
                self.save_game()
        elif kind == "skill" and isinstance(item_id, int) and 0 <= item_id < len(ALL_BOSS_SKILLS):
            skill = ALL_BOSS_SKILLS[item_id]
            if currency == "coins":
                self.coins -= cost
            else:
                self.gems -= cost
            if skill not in self.unlocked_abilities:
                self.unlocked_abilities.append(skill)
            self.skill_copies.append(skill)
            if skill not in self.equipped_abilities and len(self.equipped_abilities) < MAX_ABILITIES:
                self.equipped_abilities.append(skill)
            self.has_boss_ability = bool(self.equipped_abilities)
            self.ability_cooldowns.setdefault(skill[0], 0)
            self.track_side_quest_progress("skills_obtained")
            self.message = f"{skill[0].upper()} SKILL COPY PURCHASED"
            self.save_game()
        else:
            self.message = "PURCHASE CANCELLED  -  ITEM IS UNAVAILABLE"
        self.pending_purchase = None
        self.state = purchase.get("return_state", "marketplace")
        self.message_until = time.monotonic() + 2.5

    def cancel_market_purchase(self):
        purchase = self.pending_purchase
        self.pending_purchase = None
        self.state = (
            purchase.get("return_state", "marketplace")
            if isinstance(purchase, dict) else "marketplace"
        )

    def pending_purchase_details(self):
        purchase = self.pending_purchase
        if not isinstance(purchase, dict):
            return None
        kind, item_id = purchase.get("kind"), purchase.get("item_id")
        if kind == "weapon" and isinstance(item_id, int) and 0 <= item_id < len(MARKET_WEAPONS):
            item = MARKET_WEAPONS[item_id]
            return item["name"], item["price"]
        if kind == "skill" and isinstance(item_id, int) and 0 <= item_id < len(ALL_BOSS_SKILLS):
            return ALL_BOSS_SKILLS[item_id][0], MARKET_WEAPONS[item_id]["price"]
        return None

    def buy_boss_skill(self, skill_index):
        self.request_market_purchase("skill", skill_index, "skill_market")

    def open_weapon_preview(self, weapon_id):
        if not 0 <= weapon_id < len(MARKET_WEAPONS):
            return
        self.preview_weapon_id = weapon_id
        self.weapon_test_started_at = 0
        self.state = "weapon_preview"

    def craft_selected_skills(self):
        if len(self.forge_selected_skills) != 2:
            return
        skill_by_name = {
            skill[0]: skill for skill in self.unlocked_abilities
        }
        if any(name not in skill_by_name for name in self.forge_selected_skills):
            return
        for skill_name in set(self.forge_selected_skills):
            required = self.forge_selected_skills.count(skill_name)
            available = sum(copy[0] == skill_name for copy in self.skill_copies)
            if available < required:
                self.message = f"NOT ENOUGH {skill_name.upper()} COPIES"
                self.message_until = time.monotonic() + 2
                return
        ingredients = [
            skill_by_name[name] for name in self.forge_selected_skills
        ]
        damage_and_range = [self.skill_damage_range(skill) for skill in ingredients]
        damage = sum(values[0] for values in damage_and_range)
        skill_range = sum(values[1] for values in damage_and_range)
        for ingredient in ingredients:
            self.skill_copies.remove(ingredient)
        skill_name = "-".join(
            FORGED_SKILL_NAMES[ingredient[0]] for ingredient in ingredients
        )
        base_name = skill_name
        suffix = 2
        while skill_name in self.crafted_skill_data or any(
                skill[0] == skill_name for skill in self.unlocked_abilities):
            skill_name = f"{base_name} {suffix}"
            suffix += 1
        self.next_crafted_skill_id += 1
        crafted_skill = (
            skill_name,
            f"Unleash the combined power of {ingredients[0][0]} and {ingredients[1][0]}!",
            "A custom technique forged from two boss skills.",
        )
        self.crafted_skill_data[skill_name] = {
            "damage": damage,
            "range": skill_range,
            "crafted": True,
        }
        self.skill_copies.append(crafted_skill)
        self.unlocked_abilities.append(crafted_skill)
        if len(self.equipped_abilities) < MAX_ABILITIES:
            self.equipped_abilities.append(crafted_skill)
        self.has_boss_ability = bool(self.equipped_abilities)
        self.ability_cooldowns.setdefault(skill_name, 0)
        self.track_side_quest_progress("skills_forged")
        self.track_side_quest_progress("skills_obtained")
        self.forge_selected_skills = []
        self.forge_animation_started_at = time.monotonic()
        self.forge_animation_name = skill_name
        self.message = (
            f"{skill_name.upper()} FORGED  -  {damage} DAMAGE / "
            f"{skill_range} RANGE"
        )
        self.message_until = time.monotonic() + 3
        self.audio.speak(f"{skill_name} forged")
        self.save_game()

    def on_click(self, event):
        if self.quick_loadout_open and self.state == "playing":
            self.handle_quick_loadout_click(event.x, event.y)
            return
        if self.state == "side_quests":
            if 50 <= event.x <= 250 and event.y >= 555:
                self.state = self.side_quests_return_state
            return
        if self.state == "menu":
            if 165 <= event.x <= 465 and 331 <= event.y <= 381:
                if self.has_save():
                    self.load_game()
                else:
                    self.start_game()
            elif 495 <= event.x <= 795 and 331 <= event.y <= 381:
                if self.has_save():
                    self.load_game()
                self.open_floor_progression("menu")
            elif self.has_save() and 165 <= event.x <= 465 and 398 <= event.y <= 448:
                self.start_game()
            elif 495 <= event.x <= 795 and 398 <= event.y <= 448:
                if self.has_save():
                    self.load_game()
                self.open_special_loadout("menu")
            return
        if self.state == "tower_exterior":
            if 340 <= event.x <= 620 and 330 <= event.y <= 500:
                self.start_opening_cutscene()
            elif 760 <= event.x <= 930 and 20 <= event.y <= 58:
                self.open_floor_progression("tower_exterior")
            return
        if self.state == "tower_gate":
            self.message = "FIND THE PORTAL BEHIND THE THRONE, THEN PRESS E"
            self.message_until = time.monotonic() + 1.5
            return
        if self.state == "quest_select":
            for index in range(len(QUEST_OPTIONS)):
                x1 = 80 + index * 275
                if x1 <= event.x <= x1 + 245 and 285 <= event.y <= 470:
                    self.accept_quest(index)
                    return
            return
        if self.state == "minion_difficulty":
            for index in range(len(MINION_DIFFICULTIES)):
                x1 = 55 + index * 285
                if x1 <= event.x <= x1 + 255 and 260 <= event.y <= 430:
                    self.select_minion_difficulty(index)
                    return
            return
        if self.state == "character":
            self.handle_character_click(event.x, event.y)
            return
        if self.state == "cosmetic_chest":
            self.handle_cosmetic_chest_click(event.x, event.y)
            return
        if self.state in ("playing", "post_boss", "boss_skill"):
            if self.handle_boss_chest_click(event.x, event.y):
                return
        if (self.state in ("playing", "post_boss")
                and 812 <= event.x <= 936 and 61 <= event.y <= 87):
            self.auto_aim_enabled = not self.auto_aim_enabled
            status = "ON" if self.auto_aim_enabled else "OFF"
            self.message = f"AUTO AIM {status} FOR THIS STAGE"
            self.message_until = time.monotonic() + 1.5
            return
        if self.state == "auto_aim_prompt":
            if 280 <= event.y <= 360:
                if 170 <= event.x <= 460:
                    self.resolve_auto_aim_prompt(True)
                elif 500 <= event.x <= 790:
                    self.resolve_auto_aim_prompt(False)
            return
        if self.state == "paused":
            if 370 <= event.x <= 590 and 320 <= event.y <= 370:
                self.state = "playing"
                self.last_tick = time.monotonic()
            elif 370 <= event.x <= 590 and 390 <= event.y <= 440:
                self.state = "character"
            elif 370 <= event.x <= 590 and 460 <= event.y <= 510:
                self.open_floor_progression("paused")
            elif 370 <= event.x <= 590 and 530 <= event.y <= 580:
                self.restart_floor()
            return
        if self.state == "shop":
            self.handle_shop_click(event.x, event.y)
            return
        if self.state == "region_map":
            if event.y > 320:
                region_index = min(len(REGIONS) - 1, max(0, (event.x - 70) // 210))
                self.claim_region(region_index)
            return
        if self.state == "floor_progression":
            self.handle_progression_click(event.x, event.y)
            return
        if self.state == "marketplace":
            self.handle_market_click(event.x, event.y)
            return
        if self.state == "purchase_confirmation":
            self.handle_purchase_confirmation_click(event.x, event.y)
            return
        elif self.state == "skill_market":
            self.handle_skill_market_click(event.x, event.y)
            return
        elif self.state == "weapon_preview":
            self.handle_weapon_preview_click(event.x, event.y)
            return
        elif self.state == "skill_forge":
            self.handle_skill_forge_click(event.x, event.y)
            return
        if self.state == "special_loadout":
            self.handle_special_loadout_click(event.x, event.y)
            return
        if self.state == "post_boss":
            if 340 <= event.x <= 620 and 465 <= event.y <= 500:
                self.collect_floor_coins()
                return
            shop_left, shop_right = ((80, 260) if self.rescue_route_unlocked
                                     else (100, 300))
            terrain_left, terrain_right = ((270, 450) if self.rescue_route_unlocked
                                           else (320, 520))
            if 545 <= event.y <= 600 and shop_left <= event.x <= shop_right:
                self.open_shop()
                return
            elif 545 <= event.y <= 600 and terrain_left <= event.x <= terrain_right:
                if time.monotonic() >= self.travel_ready_at:
                    self.map_return_state = "post_boss"
                    self.state = "region_map"
                else:
                    self.message = f"TRAVEL OPENS IN {self.travel_ready_at - time.monotonic():.1f} SECONDS"
                    self.message_until = time.monotonic() + 1
                return
            if self.rescue_route_unlocked and 545 <= event.y <= 600 and 470 <= event.x <= 670:
                self.start_rescue_route()
                return
            continue_x1 = 690 if self.rescue_route_unlocked else 650
            continue_x2 = 880 if self.rescue_route_unlocked else 850
            if (545 <= event.y <= 600 and continue_x1 <= event.x <= continue_x2
                    and time.monotonic() >= self.travel_ready_at):
                self.open_floor_progression("post_boss")
                return
            elif (545 <= event.y <= 600 and continue_x1 <= event.x <= continue_x2):
                self.message = f"STAY AND COLLECT COINS FOR {self.travel_ready_at - time.monotonic():.1f} MORE SECONDS"
                self.message_until = time.monotonic() + 1
                return
            dx, dy = event.x - self.player["x"], event.y - self.player["y"]
            self.shoot(time.monotonic(), dx, dy)
            return
        if self.state == "gameover":
            self.restart_stage()
        elif self.state == "stage_intro":
            self.state = "playing"
        elif self.state == "playing":
            dx, dy = event.x - self.player["x"], event.y - self.player["y"]
            self.shoot(time.monotonic(), dx, dy)

    def on_right_click(self, event):
        if self.state not in ("playing", "post_boss", "boss_skill"):
            return
        if self.collect_medkit_at(event.x, event.y):
            return
        if self.state != "playing":
            return
        if self.pending_target_ability is not None:
            ability_index = self.pending_target_ability
            self.pending_target_ability = None
            self.use_boss_ability(
                time.monotonic(), ability_index, event.x, event.y
            )
            return
        if 0 <= self.active_ability < len(self.equipped_abilities):
            skill_name = self.equipped_abilities[self.active_ability][0]
            if skill_name in TARGETED_SKILLS:
                self.use_boss_ability(
                    time.monotonic(), self.active_ability, event.x, event.y
                )

    def collect_medkit_at(self, x, y):
        medkit = next(
            (
                pickup for pickup in self.pickups
                if pickup["kind"] == "medkit"
                and math.hypot(pickup["x"] - x, pickup["y"] - y) <= 20
            ),
            None,
        )
        if medkit is None:
            return False
        self.pickups.remove(medkit)
        self.player["hp"] = min(
            self.player["max_hp"], self.player["hp"] + 30
        )
        self.message = "FIELD MEDKIT  +30 HP"
        self.message_until = time.monotonic() + 1.3
        return True

    def on_mouse_move(self, event):
        self.mouse_position = (event.x, event.y)

    def on_key_down(self, event):
        key = event.keysym.lower()
        if (key == "s" and event.state & 0x4 and event.state & 0x1):
            self.save_game(notify=True)
            return
        was_down = key in self.keys
        self.keys.add(key)
        if self.quick_loadout_open and key == "escape":
            self.quick_loadout_open = False
            self.keys.clear()
            return
        if key in ("grave", "asciitilde") and not was_down and self.state == "playing":
            self.quick_loadout_open = not self.quick_loadout_open
            self.quick_loadout_page = 0
            return
        if key == "q" and not was_down and self.state in (
                "playing", "paused", "floor_progression", "marketplace",
                "skill_market", "skill_forge"):
            self.open_side_quests(self.state)
            return
        if key in ("return", "space") and self.state == "menu":
            self.load_game() if self.has_save() else self.start_game()
        elif key in ("return", "space") and self.state == "gameover":
            self.restart_stage()
        elif key in ("1", "2", "3", "4", "5") and not was_down and self.state == "playing":
            self.use_boss_ability(time.monotonic(), int(key) - 1)
        elif key == "t" and not was_down and self.state in ("playing", "post_boss"):
            if self.evolved or self.superhuman_active:
                self.message = "SUPERHUMAN POWER IS ALREADY AWAKENED"
                self.message_until = time.monotonic() + 2
            elif self.apply_evolution():
                self.message = "SUPERHUMAN AWAKENED  -  LEVEL 100 POWER"
                self.message_until = time.monotonic() + 4
            else:
                self.message = (
                    f"SUPERHUMAN LOCKED  -  COLLECT 7 SKILL COPIES "
                    f"({len(self.skill_copies)}/7)"
                )
                self.message_until = time.monotonic() + 2.5
        elif key in ("1", "2", "3") and not was_down and self.state == "minion_difficulty":
            self.select_minion_difficulty(int(key) - 1)
        elif key == "m" and not was_down and self.state in ("playing", "post_boss"):
            if self.state == "post_boss" and time.monotonic() < self.travel_ready_at:
                remaining = self.travel_ready_at - time.monotonic()
                self.message = f"TRAVEL OPENS IN {remaining:.1f} SECONDS"
                self.message_until = time.monotonic() + 1
                return
            self.map_return_state = self.state
            self.state = "region_map"
        elif key == "p" and not was_down and self.state in (
                "playing", "paused", "tower_exterior"):
            self.open_floor_progression(self.state)
        elif self.state == "marketplace" and key in ("backspace", "escape"):
            if key == "backspace":
                self.market_search = self.market_search[:-1]
            else:
                self.state = "floor_progression"
        elif self.state == "skill_forge" and key == "escape":
            self.state = "marketplace"
        elif self.state in ("skill_market", "weapon_preview") and key == "escape":
            self.state = "marketplace"
        elif self.state == "purchase_confirmation" and key == "escape":
            self.cancel_market_purchase()
        elif self.state == "marketplace" and len(key) == 1 and key.isprintable():
            self.market_search += key
        elif key == "b" and not was_down and self.state == "post_boss":
            self.open_shop()
        elif key == "c" and not was_down and self.state == "paused":
            self.state = "character"
        elif key == "return" and self.state == "stage_intro":
            self.state = "playing"
        elif key in ("e", "return", "space") and self.state == "tower_exterior":
            self.start_opening_cutscene()
        elif key == "e" and self.state == "tower_gate":
            gate_x, gate_y = WIDTH / 2, ARENA[1] + 208
            if math.hypot(self.player["x"] - gate_x,
                          self.player["y"] - gate_y) <= 68:
                self.enter_tower_floor()
        elif key == "escape":
            if self.state == "playing":
                self.state = "paused"
                self.keys.clear()
            elif self.state == "paused":
                self.state = "playing"
                self.last_tick = time.monotonic()
            elif self.state == "shop":
                self.state = self.shop_return_state
            elif self.state == "region_map":
                self.state = self.map_return_state
            elif self.state == "floor_progression":
                self.state = self.progression_return_state
            elif self.state == "marketplace":
                self.state = "floor_progression"
            elif self.state == "skill_forge":
                self.state = "marketplace"
            elif self.state in ("skill_market", "weapon_preview"):
                self.state = "marketplace"
            elif self.state == "purchase_confirmation":
                self.cancel_market_purchase()
            elif self.state == "side_quests":
                self.state = self.side_quests_return_state
            elif self.state == "special_loadout":
                self.state = self.special_loadout_return_state
            elif self.state == "character":
                self.state = "paused"
            elif self.state == "auto_aim_prompt":
                self.resolve_auto_aim_prompt(False)

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def start_game(self):
        self.new_game()
        self.state = "tower_exterior"
        self.player["x"] = WIDTH / 2
        self.player["y"] = HEIGHT - 100
        self.keys.clear()
        self.last_tick = time.monotonic()
        self.canvas.delete("background")
        self.draw_background()
        self.canvas.focus_set()
        self.save_game()

    def close(self):
        if self.state != "menu":
            self.save_game()
        self.audio.close()
        self.root.destroy()

    def has_save(self):
        return os.path.isfile(self.save_path)

    def save_game(self, notify=False):
        player_fields = ("level", "xp", "next_xp", "speed", "max_hp", "hp")
        data = {
            "version": SAVE_VERSION,
            "floor": self.stage_number(),
            "floor_wave": self.floor_wave,
            "floor_records": self.floor_records,
            "owned_special_weapons": self.owned_special_weapons,
            "equipped_special_weapon": self.equipped_special_weapon,
            "special_shots_left": self.special_shots_left,
            "floor_kills_start": self.floor_kills_start,
            "active_quest_index": (
                self.active_quest_index if self.active_quest is not None else None
            ),
            "quest_progress": self.quest_progress,
            "quest_complete": self.quest_complete,
            "encounter_clear": self.encounter_clear,
            "minion_difficulty": self.minion_difficulty,
            "replay_active": self.replay_active,
            "replay_return_snapshot": self.replay_return_snapshot,
            "progression_return_state": self.progression_return_state,
            "player": {field: self.player[field] for field in player_fields},
            "coins": self.coins,
            "gems": self.gems,
            "side_quest_stats": self.side_quest_stats,
            "side_quests_claimed": sorted(self.side_quests_claimed),
            "kills": self.kills,
            "region": self.region,
            "territories": self.territories,
            "unlocked_abilities": self.unlocked_abilities,
            "equipped_abilities": self.equipped_abilities,
            "skill_copies": self.skill_copies,
            "crafted_skill_data": self.crafted_skill_data,
            "next_crafted_skill_id": self.next_crafted_skill_id,
            "evolved": self.evolved,
            "superhuman_active": self.superhuman_active,
            "superhuman_original_stats": self.superhuman_original_stats,
            "superhuman_xp_earned": self.superhuman_xp_earned,
            "active_ability": self.active_ability,
            "weapon_upgrade": self.weapon_upgrade,
            "skill_upgrade": self.skill_upgrade,
            "health_upgrade": self.health_upgrade,
            "boss_weapon_owned": self.boss_weapon_owned,
            "advanced_gun_owned": self.advanced_gun_owned,
            "owned_cosmetics": {
                category: sorted(items)
                for category, items in self.owned_cosmetics.items()
            },
            "equipped_cosmetics": self.equipped_cosmetics,
            "quests_completed": sorted(self.quests_completed),
            "tower_clues": self.tower_clues,
            "rescue_route_unlocked": self.rescue_route_unlocked,
        }
        temporary_path = self.save_path + ".tmp"
        try:
            with open(temporary_path, "w", encoding="utf-8") as save_file:
                json.dump(data, save_file, indent=2)
                save_file.flush()
                os.fsync(save_file.fileno())
            os.replace(temporary_path, self.save_path)
        except (OSError, TypeError, ValueError):
            logging.exception("Could not save the game")
            self.save_notice = "SAVE FAILED  -  CHECK THE GAME FOLDER"
        else:
            self.save_notice = f"GAME SAVED  -  FLOOR {data['floor']}"
        self.save_notice_until = time.monotonic() + 3
        self.last_autosave_at = time.monotonic()
        if notify:
            self.message = self.save_notice
            self.message_until = self.save_notice_until

    def autosave_if_due(self, now):
        if (self.state == "menu"
                or now - self.last_autosave_at < AUTO_SAVE_INTERVAL):
            return False
        self.save_game()
        return True

    def load_game(self):
        try:
            with open(self.save_path, "r", encoding="utf-8") as save_file:
                data = json.load(save_file)
            if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
                raise ValueError("Unsupported save version")
            floor = data["floor"]
            player_data = data["player"]
            if (not isinstance(floor, int) or not 1 <= floor <= MAX_FLOORS
                    or not isinstance(player_data, dict)):
                raise ValueError("Invalid saved floor or player data")

            restored_player = {}
            for field in ("level", "xp", "next_xp", "speed", "max_hp", "hp"):
                value = player_data[field]
                if not isinstance(value, int) or value < 0:
                    raise ValueError(f"Invalid player field: {field}")
                restored_player[field] = value
            if restored_player["max_hp"] < 1 or restored_player["next_xp"] < 1:
                raise ValueError("Invalid player statistics")
            restored_player["hp"] = max(
                1, min(restored_player["hp"], restored_player["max_hp"])
            )
            coins = int(data["coins"])
            kills = int(data["kills"])
            region = int(data["region"])
            if coins < 0 or kills < 0 or not 0 <= region < len(REGIONS):
                raise ValueError("Invalid saved progress")
            gems = int(data.get("gems", 0))
            if gems < 0:
                raise ValueError("Invalid gem balance")
            saved_side_quest_stats = data.get("side_quest_stats", {})
            if not isinstance(saved_side_quest_stats, dict):
                raise ValueError("Invalid side quest progress")
            side_quest_stats = {
                counter: max(0, int(saved_side_quest_stats.get(counter, 0)))
                for counter in (
                    "weapons_purchased", "skills_obtained",
                    "skills_forged", "superhuman",
                )
            }
            valid_side_quest_ids = {quest[0] for quest in SIDE_QUESTS}
            saved_side_quests_claimed = data.get("side_quests_claimed", [])
            if not isinstance(saved_side_quests_claimed, list):
                raise ValueError("Invalid claimed side quests")
            side_quests_claimed = {
                quest_id for quest_id in saved_side_quests_claimed
                if isinstance(quest_id, str) and quest_id in valid_side_quest_ids
            }
            original_stats_data = data.get("superhuman_original_stats")
            superhuman_original_stats = None
            if original_stats_data is not None:
                expected_stats = (
                    "level", "xp", "next_xp", "speed", "max_hp", "hp",
                    "weapon_upgrade", "skill_upgrade", "health_upgrade",
                )
                if (not isinstance(original_stats_data, dict)
                        or any(not isinstance(original_stats_data.get(field), int)
                               or original_stats_data[field] < 0
                               for field in expected_stats)
                        or original_stats_data["max_hp"] < 1
                        or original_stats_data["next_xp"] < 1):
                    raise ValueError("Invalid saved Superhuman state")
                superhuman_original_stats = {
                    field: original_stats_data[field] for field in expected_stats
                }
            superhuman_xp_earned = max(
                0, int(data.get("superhuman_xp_earned", 0))
            )
            superhuman_active = (
                bool(data.get("superhuman_active", False))
                and superhuman_original_stats is not None
            )
            if bool(data.get("superhuman_active", False)) and not superhuman_active:
                raise ValueError("Missing saved Superhuman restoration state")
            territories = data["territories"]
            if (not isinstance(territories, list)
                    or len(territories) != len(REGIONS)
                    or not all(isinstance(value, bool) for value in territories)):
                raise ValueError("Invalid territories")
            territories = territories.copy()
            territories[region] = True
            crafted_skill_data = data.get("crafted_skill_data", {})
            if not isinstance(crafted_skill_data, dict):
                raise ValueError("Invalid crafted skills")
            valid_crafted_skill_data = {}
            for name, metadata in crafted_skill_data.items():
                if (isinstance(name, str)
                        and isinstance(metadata, dict)
                        and isinstance(metadata.get("damage"), int)
                        and metadata["damage"] > 0
                        and isinstance(metadata.get("range"), int)
                        and metadata["range"] > 0
                        and (metadata.get("crafted") is True
                             or name.startswith("Fusion "))):
                    valid_crafted_skill_data[name] = {
                        "damage": metadata["damage"],
                        "range": metadata["range"],
                        "crafted": True,
                    }
            if not isinstance(data["unlocked_abilities"], list):
                raise ValueError("Invalid saved skills")
            unlocked_abilities = []
            for skill in data["unlocked_abilities"]:
                if (isinstance(skill, list) and len(skill) == 3
                        and isinstance(skill[0], str)
                        and (tuple(skill) in ALL_BOSS_SKILLS
                             or tuple(skill)[0] in valid_crafted_skill_data)
                        and tuple(skill) not in unlocked_abilities):
                    unlocked_abilities.append(tuple(skill))
            skill_copies_data = data.get("skill_copies")
            if skill_copies_data is None:
                skill_copies = unlocked_abilities.copy()
            elif isinstance(skill_copies_data, list):
                skill_copies = [
                    tuple(skill) for skill in skill_copies_data
                    if isinstance(skill, list) and len(skill) == 3
                    and isinstance(skill[0], str)
                    and (tuple(skill) in ALL_BOSS_SKILLS
                         or tuple(skill)[0] in valid_crafted_skill_data)
                ]
            else:
                raise ValueError("Invalid boss skill copies")
            saved_equipped_abilities = data.get("equipped_abilities")
            if saved_equipped_abilities is None:
                equipped_abilities = unlocked_abilities[:MAX_ABILITIES]
            elif isinstance(saved_equipped_abilities, list):
                equipped_abilities = []
                for skill in saved_equipped_abilities:
                    if (isinstance(skill, list)
                            and tuple(skill) in unlocked_abilities
                            and tuple(skill) not in equipped_abilities
                            and len(equipped_abilities) < MAX_ABILITIES):
                        equipped_abilities.append(tuple(skill))
            else:
                raise ValueError("Invalid equipped boss skills")
            active_ability = max(
                0, min(int(data["active_ability"]), len(equipped_abilities) - 1)
            ) if equipped_abilities else 0
            upgrades = {
                field: max(0, int(data[field]))
                for field in ("weapon_upgrade", "skill_upgrade", "health_upgrade")
            }
            owned_cosmetics = {}
            equipped_cosmetics = {}
            for category, items in COSMETIC_ITEMS.items():
                saved_owned = data["owned_cosmetics"][category]
                if not isinstance(saved_owned, list):
                    raise ValueError("Invalid cosmetic ownership")
                owned_cosmetics[category] = {
                    name for name, _, _ in items if name in saved_owned
                } | {items[0][0]}
                equipped = data["equipped_cosmetics"][category]
                equipped_cosmetics[category] = (
                    equipped if equipped in owned_cosmetics[category]
                    else items[0][0]
                )
            quests_completed = {
                value for value in data["quests_completed"]
                if isinstance(value, int) and 1 <= value <= MAX_FLOORS
            }
            tower_clues = [
                clue for clue in data["tower_clues"]
                if clue in {entry[1] for entry in TOWER_MINIONS}
            ]
            floor_records = data.get("floor_records", {})
            if not isinstance(floor_records, dict):
                raise ValueError("Invalid floor progression")
            floor_records = {
                str(record_floor): record
                for record_floor, record in floor_records.items()
                if str(record_floor).isdigit()
                and 1 <= int(record_floor) <= MAX_FLOORS
                and isinstance(record, dict)
            }
            owned_weapons = data.get("owned_special_weapons", [])
            weapon_ids = {weapon["id"] for weapon in MARKET_WEAPONS}
            if not isinstance(owned_weapons, list):
                raise ValueError("Invalid special weapon ownership")
            owned_weapons = [
                weapon_id for weapon_id in owned_weapons
                if isinstance(weapon_id, int) and weapon_id in weapon_ids
            ]
            equipped_weapon = data.get("equipped_special_weapon")
            if equipped_weapon not in owned_weapons:
                equipped_weapon = owned_weapons[0] if owned_weapons else None

            self.new_game()
            self.player.update(restored_player)
            self.coins = coins
            self.gems = gems
            self.side_quest_stats = side_quest_stats
            self.side_quests_claimed = side_quests_claimed
            self.kills = kills
            self.floor_kills_start = max(
                0, min(int(data.get("floor_kills_start", kills)), kills)
            )
            self.region = region
            self.territories = territories
            self.unlocked_abilities = unlocked_abilities
            self.equipped_abilities = equipped_abilities
            self.skill_copies = skill_copies
            self.crafted_skill_data = valid_crafted_skill_data
            self.next_crafted_skill_id = max(
                1, int(data.get("next_crafted_skill_id", 1))
            )
            self.evolved = bool(data.get("evolved", False))
            self.superhuman_active = superhuman_active
            self.superhuman_original_stats = (
                superhuman_original_stats if superhuman_active else None
            )
            self.superhuman_xp_earned = (
                superhuman_xp_earned if superhuman_active else 0
            )
            self.has_boss_ability = bool(equipped_abilities)
            self.active_ability = active_ability
            for field, value in upgrades.items():
                setattr(self, field, value)
            if self.evolved and self.has_all_boss_skills():
                self.player.update({
                    "level": 100,
                    "xp": 0,
                    "next_xp": 40,
                    "max_hp": 100_000,
                    "hp": min(self.player["hp"], 100_000),
                })
                self.weapon_upgrade = 100
                self.skill_upgrade = 100
                self.health_upgrade = 100
            elif self.evolved:
                self.evolved = False
            self.boss_weapon_owned = bool(data["boss_weapon_owned"])
            self.advanced_gun_owned = bool(data["advanced_gun_owned"])
            self.owned_cosmetics = owned_cosmetics
            self.equipped_cosmetics = equipped_cosmetics
            self.quests_completed = quests_completed
            self.tower_clues = tower_clues
            self.rescue_route_unlocked = bool(data["rescue_route_unlocked"])
            self.floor_number = floor
            self.floor_wave = max(
                1, min(int(data.get("floor_wave", 1)), self.floor_wave_count(floor))
            )
            self.encounter_clear = bool(data.get("encounter_clear", False))
            if self.encounter_clear and self.superhuman_active:
                self.end_superhuman(save=False)
            replay_active = bool(data.get("replay_active", False))
            replay_snapshot = data.get("replay_return_snapshot")
            if replay_active and not isinstance(replay_snapshot, dict):
                raise ValueError("Invalid floor replay state")
            progression_return_state = data.get(
                "progression_return_state", "menu"
            )
            if progression_return_state not in (
                    "menu", "paused", "post_boss", "tower_exterior"):
                progression_return_state = "menu"
            if replay_active:
                snapshot_floor = replay_snapshot.get("floor")
                snapshot_wave = replay_snapshot.get("floor_wave")
                snapshot_quest = replay_snapshot.get("quest_index")
                if (not isinstance(snapshot_floor, int)
                        or not 1 <= snapshot_floor <= MAX_FLOORS
                        or not isinstance(snapshot_wave, int)
                        or not 1 <= snapshot_wave <= self.floor_wave_count(snapshot_floor)
                        or (snapshot_quest is not None
                            and (not isinstance(snapshot_quest, int)
                                 or not 0 <= snapshot_quest < len(QUEST_OPTIONS)))):
                    raise ValueError("Invalid floor replay return snapshot")
            self.replay_active = replay_active
            self.replay_return_snapshot = replay_snapshot if replay_active else None
            self.progression_return_state = progression_return_state
            minion_difficulty = data.get("minion_difficulty")
            self.minion_difficulty = (
                minion_difficulty
                if isinstance(minion_difficulty, int)
                and 0 <= minion_difficulty < len(MINION_DIFFICULTIES)
                else None
            )
            self.floor_records = floor_records
            self.owned_special_weapons = owned_weapons
            self.equipped_special_weapon = equipped_weapon
            self.special_shots_left = max(
                0, min(int(data.get("special_shots_left", SPECIAL_SHOTS_PER_FLOOR)),
                       SPECIAL_SHOTS_PER_FLOOR)
            )
            self.wave = max(1, (floor - 1) * 10 + self.floor_wave)
            self.player["x"] = WIDTH / 2
            self.player["y"] = (ARENA[1] + ARENA[3]) / 2
            self.wave_left = 0
            self.wave_pause = 0
            self.rescue_battle = False
            self.prepare_quest_options()
            quest_index = data.get("active_quest_index")
            if isinstance(quest_index, int) and 0 <= quest_index < len(QUEST_OPTIONS):
                self.active_quest_index = quest_index
                self.active_quest = QUEST_OPTIONS[quest_index]
                self.quest_reward = self.quest_rewards[quest_index]
                self.quest_progress = max(
                    0, min(int(data.get("quest_progress", 0)), self.active_quest[2])
                )
                self.quest_complete = bool(data.get("quest_complete", False))
                self.quests_completed = set(quests_completed)
                if self.encounter_clear:
                    self.state = "post_boss"
                    self.travel_ready_at = time.monotonic()
                else:
                    self.state = "stage_intro"
                    self.stage_intro_until = time.monotonic() + 1.5
                    self.spawn_wave()
            else:
                self.active_quest = None
                self.state = "quest_select"
            self.keys.clear()
            self.award_side_quests(save=False)
            self.save_game()
            self.canvas.delete("background")
            self.draw_background()
            self.last_tick = time.monotonic()
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            logging.exception("Could not load the game")
            self.save_notice = "LOAD FAILED  -  SAVE FILE IS MISSING OR DAMAGED"
            self.save_notice_until = time.monotonic() + 3
            self.message = self.save_notice
            self.message_until = self.save_notice_until
            return
        self.save_notice = f"CHECKPOINT LOADED  -  FLOOR {floor}"
        self.save_notice_until = time.monotonic() + 3
        self.message = self.save_notice
        self.message_until = self.save_notice_until

    def speak_dialogue(self, text):
        if text and text != self.last_spoken_dialogue:
            self.last_spoken_dialogue = text
            self.audio.speak(text)

    def start_opening_cutscene(self):
        self.state = "opening_cutscene"
        self.opening_cutscene_started = time.monotonic()
        self.last_spoken_dialogue = None
        self.keys.clear()

    def enter_tower_floor(self):
        self.floor_wave = 1
        self.wave_pause = 0
        self.enemies.clear()
        self.pickups.clear()
        self.projectiles.clear()
        self.effects.clear()
        self.player["x"] = WIDTH / 2
        self.player["y"] = (ARENA[1] + ARENA[3]) / 2
        self.state = "quest_select"
        self.prepare_quest_options()
        self.keys.clear()

    def prepare_quest_options(self):
        floor = self.stage_number()
        growth = 1.25 ** (floor - 1)
        self.quest_rewards = [
            math.floor((50 + bonus) * growth + 0.5)
            for bonus in QUEST_REWARD_BONUSES
        ]
        self.quest_reward = self.quest_rewards[0]

    def accept_quest(self, quest_index):
        if not 0 <= quest_index < len(QUEST_OPTIONS):
            return
        self.active_quest = QUEST_OPTIONS[quest_index]
        self.active_quest_index = quest_index
        self.quest_reward = self.quest_rewards[quest_index]
        self.quest_progress = 0
        self.quest_complete = False
        self.begin_stage()
        self.save_game()

    def restart_stage(self):
        self.floor_wave = 1
        self.encounter_clear = False
        self.minion_difficulty = None
        self.special_shots_left = SPECIAL_SHOTS_PER_FLOOR
        self.player.update(
            x=WIDTH / 2,
            y=(ARENA[1] + ARENA[3]) / 2,
            hp=self.player["max_hp"],
            hurt_until=0,
            knockdown_until=0,
            shield_until=0,
            frozen_until=0,
            attack_ready=0,
            ability_ready=0,
        )
        self.enemies.clear()
        self.pickups.clear()
        self.projectiles.clear()
        self.effects.clear()
        self.boss_corpses.clear()
        self.boss_chests.clear()
        self.wave_pause = 0
        self.pending_skill = None
        self.skill_acquire_progress = 0
        self.pending_target_ability = None
        self.ability_cooldowns.clear()
        self.time_freeze_until = 0
        self.time_freeze_owner = None
        self.wave_left = 0
        self.state = "stage_intro"
        self.stage_intro_until = time.monotonic() + 2.2
        self.keys.clear()
        self.canvas.delete("background")
        self.draw_background()
        self.spawn_wave()
        self.message = f"{self.stage_label()} RESTARTED"
        self.message_until = self.stage_intro_until
        self.last_tick = time.monotonic()
        self.save_game()

    def restart_floor(self):
        if self.active_quest is not None and not self.quest_complete:
            self.quest_progress = 0
        self.floor_kills_start = self.kills
        self.restart_stage()

    def spawn_enemy(self):
        if self.floor_wave > self.regular_waves_per_floor():
            if self.state == "playing":
                self.state = "boss_warning"
                self.boss_warning_until = time.monotonic() + 3
            return

        side = random.randrange(4)
        if side == 0:
            x, y = random.uniform(ARENA[0], ARENA[2]), ARENA[1] + 12
        elif side == 1:
            x, y = random.uniform(ARENA[0], ARENA[2]), ARENA[3] - 12
        elif side == 2:
            x, y = ARENA[0] + 12, random.uniform(ARENA[1], ARENA[3])
        else:
            x, y = ARENA[2] - 12, random.uniform(ARENA[1], ARENA[3])

        if self.wave >= 3 and random.random() < 0.24:
            kind = "brute"
            hp, speed, damage, xp, radius = 72, 48, 17, 24, 16
        elif self.wave >= 2 and random.random() < 0.38:
            kind = "ranger"
            hp, speed, damage, xp, radius = 28, 83, 8, 12, 11
        else:
            kind = "raider"
            hp, speed, damage, xp, radius = 42, 64, 11, 16, 13
        self.enemies.append(
            {
                "x": x,
                "y": y,
                "hp": hp,
                "max_hp": hp,
                "speed": speed,
                "damage": damage,
                "xp": xp,
                "radius": radius,
                "kind": kind,
                "attack_ready": 0,
                "hurt_until": 0,
            }
        )
        self.wave_left -= 1

    def spawn_boss(self):
        x, y = ARENA[2] - 75, ARENA[1] + 85
        is_rescue_boss = self.rescue_battle
        is_minion_boss = self.is_minion_boss_wave() and not is_rescue_boss
        kind = "kidnapper" if is_rescue_boss else (
            "minion_boss" if is_minion_boss else "boss"
        )
        minion_clue = None
        if is_minion_boss:
            clue_index = min(self.stage_number() // 5 - 1, len(TOWER_MINIONS) - 1)
            minion_clue = TOWER_MINIONS[clue_index][1]
        floor = self.stage_number()
        difficulty = None
        if is_minion_boss:
            difficulty = self.minion_difficulty
            if difficulty is None:
                difficulty = 0
            base_hp = MINION_DIFFICULTIES[difficulty][1]
        else:
            base_hp = 1_000 + (floor - 1) * 5_000
        self.enemies.append(
            {
                "x": x,
                "y": y,
                "hp": base_hp,
                "max_hp": base_hp,
                "speed": 36 if is_minion_boss else 42,
                "damage": 8 if is_minion_boss else 15,
                "xp": 1_000 + floor * 250,
                "radius": 30,
                "kind": kind,
                "attack_ready": 0,
                "hurt_until": 0,
                "special_ready": time.monotonic() + 2.5,
                "special_until": 0,
                "special_hit": False,
                "special_line": None,
                "boss_name": self.boss_name(),
                "skill": None if is_rescue_boss else self.boss_skill(),
                "skills": [] if is_rescue_boss else self.boss_skills(),
                "next_skill_index": 0,
                "clue": minion_clue,
                "difficulty": difficulty if is_minion_boss else None,
                "floor_final_boss": self.floor_wave == self.floor_wave_count(),
                "teleport_ready": time.monotonic() + 3,
                "clone_ready": time.monotonic() + 5,
            }
        )

    def update_flow(self, now):
        if self.state == "opening_cutscene" and now - self.opening_cutscene_started >= 12:
            self.state = "tower_gate"
            self.player["x"] = WIDTH / 2
            self.player["y"] = HEIGHT - 105
            self.keys.clear()
        elif self.state == "stage_intro" and now >= self.stage_intro_until:
            self.state = "playing"
        elif self.state == "boss_warning" and now >= self.boss_warning_until:
            self.spawn_boss()
            self.wave_left = 0
            self.state = "playing"
            self.message = f'{self.boss_name()}: "{self.boss_dialogue()}"'
            self.message_until = now + 2
            self.audio.speak(f"{self.boss_name()}: {self.boss_dialogue()}")
        elif self.state == "boss_cutscene" and now >= self.boss_cutscene_until:
            self.state = "boss_dialogue"
            self.boss_dialogue_until = now + 3.2
        elif self.state == "boss_dialogue" and now >= self.boss_dialogue_until:
            self.state = "boss_skill"
            self.skill_acquire_progress = 0
        elif self.state == "minion_reveal" and now >= self.boss_dialogue_until:
            if self.pending_skill:
                self.state = "boss_skill"
                self.skill_acquire_progress = 0
            else:
                self.state = "post_boss"
                self.travel_ready_at = now
                self.message = self.clue_dialogue
                self.message_until = now + 3
        elif self.state == "kidnapper_reveal" and now >= self.kidnapper_reveal_until:
            self.state = "victory"
            self.rescue_battle = False

    def continue_stage(self):
        if self.floor_wave < self.floor_wave_count():
            self.boss_corpses.clear()
            self.boss_chests.clear()
            self.floor_wave += 1
            self.wave += 1
            self.minion_difficulty = None
            self.pending_target_ability = None
            self.wave_pause = 0
            self.projectiles.clear()
            self.state = "stage_intro"
            self.encounter_clear = False
            self.stage_intro_until = time.monotonic() + 1.5
            self.spawn_wave()
            if self.state == "minion_difficulty":
                self.message = "CHOOSE THE DEMON MINION'S DIFFICULTY"
            self.save_game()
            return
        if self.replay_active:
            snapshot = self.replay_return_snapshot
            if snapshot is None:
                raise ValueError("Missing floor replay return state")
            self.floor_number = snapshot["floor"]
            self.floor_wave = snapshot["floor_wave"]
            self.wave = snapshot["wave"]
            self.wave_left = snapshot["wave_left"]
            self.floor_kills_start = snapshot["floor_kills_start"]
            self.active_quest_index = snapshot["quest_index"] or 0
            self.active_quest = (
                QUEST_OPTIONS[snapshot["quest_index"]]
                if snapshot["quest_index"] is not None else None
            )
            self.quest_progress = snapshot["quest_progress"]
            self.quest_complete = snapshot["quest_complete"]
            self.encounter_clear = snapshot["encounter_clear"]
            self.minion_difficulty = snapshot["minion_difficulty"]
            if self.active_quest is not None:
                self.prepare_quest_options()
                self.quest_reward = self.quest_rewards[self.active_quest_index]
            self.replay_active = False
            self.replay_return_snapshot = None
            self.boss_corpses.clear()
            self.boss_chests.clear()
            self.enemies.clear()
            self.pickups.clear()
            self.projectiles.clear()
            self.effects.clear()
            self.state = "floor_progression"
            self.message = "FLOOR REPLAY COMPLETE  -  ORIGINAL PROGRESS PRESERVED"
            self.message_until = time.monotonic() + 3
            self.save_game()
            return
        if self.stage_number() >= MAX_FLOORS:
            self.state = "victory"
            self.message = "THE 200TH FLOOR IS YOURS. THE TOWER IS CONQUERED."
            self.save_game()
            return
        self.begin_floor(self.stage_number() + 1)
        self.state = "quest_select"
        self.prepare_quest_options()
        self.auto_aim_enabled = False
        self.save_game()

    def open_floor_progression(self, return_state=None):
        self.quick_loadout_open = False
        if return_state is not None:
            self.progression_return_state = return_state
        self.progression_selected_floor = self.stage_number()
        self.progression_page = (self.progression_selected_floor - 1) // 12
        self.state = "floor_progression"

    def floor_record(self, floor):
        return self.floor_records.get(str(floor))

    def market_stand_unlocked(self, floor):
        return self.player["level"] >= 15

    def record_floor_clear(self):
        floor = self.stage_number()
        if self.floor_record(floor):
            return
        quest_index = self.active_quest_index
        self.floor_records[str(floor)] = {
            "cleared": True,
            "quest_index": quest_index,
            "quest_title": self.active_quest[0] if self.active_quest else "No quest",
            "quest_complete": self.quest_complete,
            "stars": quest_index + 1,
            "quest_progress": self.quest_progress,
            "quest_target": self.active_quest[2] if self.active_quest else 0,
            "quest_reward": self.quest_reward,
            "kills": self.kills - self.floor_kills_start,
            "level": self.player["level"],
            "coins": self.coins,
        }
        self.save_game()

    def replay_cleared_floor(self, floor):
        record = self.floor_record(floor)
        if record is None or self.replay_active:
            return
        quest_index = record.get("quest_index", 0)
        if not isinstance(quest_index, int) or not 0 <= quest_index < len(QUEST_OPTIONS):
            quest_index = 0
        self.replay_return_snapshot = {
            "floor": self.stage_number(),
            "floor_wave": self.floor_wave,
            "wave": self.wave,
            "wave_left": self.wave_left,
            "floor_kills_start": self.floor_kills_start,
            "quest_index": (
                self.active_quest_index if self.active_quest is not None else None
            ),
            "quest_progress": self.quest_progress,
            "quest_complete": self.quest_complete,
            "encounter_clear": self.encounter_clear,
            "minion_difficulty": self.minion_difficulty,
        }
        self.replay_active = True
        self.floor_number = floor
        self.floor_wave = 1
        self.wave = max(1, (floor - 1) * 10 + 1)
        self.wave_left = 0
        self.floor_kills_start = self.kills
        self.active_quest = None
        self.active_quest_index = quest_index
        self.quest_progress = 0
        self.quest_complete = False
        self.encounter_clear = False
        self.minion_difficulty = None
        self.special_shots_left = SPECIAL_SHOTS_PER_FLOOR
        self.enemies.clear()
        self.pickups.clear()
        self.projectiles.clear()
        self.effects.clear()
        self.boss_corpses.clear()
        self.boss_chests.clear()
        self.prepare_quest_options()
        self.state = "quest_select"
        self.message = f"REPLAYING FLOOR {floor}  -  CHOOSE A QUEST"
        self.message_until = time.monotonic() + 3
        self.save_game()

    def advance_progression_page(self, delta):
        self.progression_page = max(
            0, min((MAX_FLOORS - 1) // 12, self.progression_page + delta)
        )

    def select_progression_floor(self, floor):
        if 1 <= floor <= self.stage_number():
            self.progression_selected_floor = floor

    def open_marketplace(self, floor=None):
        floor = self.progression_selected_floor if floor is None else floor
        if not self.market_stand_unlocked(floor):
            return
        self.market_stand_floor = floor
        self.market_page = 0
        self.market_filter = "ALL"
        self.market_search = ""
        self.state = "marketplace"

    def handle_skill_forge_click(self, x, y):
        if 90 <= y <= 118:
            if 50 <= x <= 450 and self.forge_selected_skills:
                self.forge_selected_skills.pop(0)
            elif 510 <= x <= 910 and len(self.forge_selected_skills) > 1:
                self.forge_selected_skills.pop(1)
            return
        if 130 <= y < 500 and 52 <= x <= 908:
            row = (y - 130) // 44
            visible = self.visible_skill_copies()
            index = self.forge_page * 8 + row
            if 0 <= index < len(visible) and len(self.forge_selected_skills) < 2:
                skill, count = visible[index]
                selected_count = self.forge_selected_skills.count(skill[0])
                if selected_count >= count:
                    self.message = f"ONLY {count} {skill[0].upper()} COPY/COPIES AVAILABLE"
                    self.message_until = time.monotonic() + 2
                else:
                    self.forge_selected_skills.append(skill[0])
            return
        if y >= 550:
            if x <= 220:
                self.state = "marketplace"
            elif 245 <= x <= 375:
                self.forge_page = max(0, self.forge_page - 1)
            elif 385 <= x <= 575:
                self.craft_selected_skills()
            elif 600 <= x <= 730:
                pages = max(1, (len(self.visible_skill_copies()) + 7) // 8)
                self.forge_page = min(pages - 1, self.forge_page + 1)
            elif x >= 750:
                self.forge_selected_skills = []

    def handle_skill_market_click(self, x, y):
        if y >= 555 and x <= 250:
            self.state = "marketplace"
            return
        if 125 <= y < 545 and 52 <= x <= 910:
            row = (y - 125) // 58
            index = self.skill_market_page * 7 + row
            if 0 <= index < len(ALL_BOSS_SKILLS):
                self.buy_boss_skill(index)

    def handle_weapon_preview_click(self, x, y):
        if 535 <= y <= 595:
            if x <= 245:
                self.state = "marketplace"
            elif 270 <= x <= 505:
                self.weapon_test_started_at = time.monotonic()
            elif x >= 530 and self.preview_weapon_id is not None:
                self.request_market_purchase(
                    "weapon", self.preview_weapon_id, "weapon_preview"
                )

    def handle_purchase_confirmation_click(self, x, y):
        if 410 <= y <= 480:
            details = self.pending_purchase_details()
            if not details:
                self.cancel_market_purchase()
            elif 120 <= x <= 365:
                if self.coins >= details[1]:
                    self.complete_market_purchase("coins")
            elif 380 <= x <= 600:
                gem_cost = self.gem_price(details[1])
                if self.gems >= gem_cost:
                    self.complete_market_purchase("gems")
            elif 615 <= x <= 840:
                self.cancel_market_purchase()

    def open_special_loadout(self, return_state):
        self.special_loadout_return_state = return_state
        self.special_loadout_page = 0
        self.special_loadout_tab = "weapons"
        self.state = "special_loadout"

    def handle_special_loadout_click(self, x, y):
        if 90 <= y <= 120:
            if 180 <= x <= 460:
                self.special_loadout_tab = "weapons"
                return
            if 500 <= x <= 780:
                self.special_loadout_tab = "skills"
                return
        if y >= 555 and x <= 260:
            self.state = self.special_loadout_return_state
            return
        if self.special_loadout_tab == "skills":
            if 125 <= y < 545 and 52 <= x <= 910:
                row = (y - 125) // 54
                if 0 <= row < len(self.unlocked_abilities):
                    self.toggle_equipped_skill(self.unlocked_abilities[row])
            return
        if y >= 555 and x >= 690:
            self.special_loadout_page += 1
            return
        if y >= 555 and 360 <= x <= 620:
            self.special_loadout_page = max(0, self.special_loadout_page - 1)
            return
        if 125 <= y < 545 and 52 <= x <= 910:
            row = (y - 125) // 42
            start = self.special_loadout_page * 10
            owned = self.owned_special_weapons[start:start + 10]
            if 0 <= row < len(owned):
                weapon_id = owned[row]
                self.equipped_special_weapon = weapon_id
                weapon = MARKET_WEAPONS[weapon_id]
                self.message = f'{weapon["name"].upper()} EQUIPPED'
                self.message_until = time.monotonic() + 2
                self.save_game()

    def toggle_equipped_skill(self, skill):
        if skill not in self.unlocked_abilities:
            return
        active_skill = (
            self.equipped_abilities[self.active_ability]
            if 0 <= self.active_ability < len(self.equipped_abilities) else None
        )
        if skill in self.equipped_abilities:
            self.equipped_abilities.remove(skill)
            self.message = f"{skill[0].upper()} UNEQUIPPED"
        elif len(self.equipped_abilities) >= MAX_ABILITIES:
            self.message = f"ONLY {MAX_ABILITIES} SKILLS CAN BE EQUIPPED  -  UNEQUIP ONE FIRST"
            self.message_until = time.monotonic() + 2.5
            return
        else:
            self.equipped_abilities.append(skill)
            self.message = f"{skill[0].upper()} EQUIPPED"
        self.has_boss_ability = bool(self.equipped_abilities)
        if active_skill in self.equipped_abilities:
            self.active_ability = self.equipped_abilities.index(active_skill)
        else:
            self.active_ability = 0
        self.message_until = time.monotonic() + 2
        self.save_game()

    def handle_quick_loadout_click(self, x, y):
        if y >= 505 and 680 <= x <= 790:
            self.quick_loadout_open = False
            return
        if 125 <= y <= 160:
            if 180 <= x <= 390:
                self.special_loadout_tab = "weapons"
                self.quick_loadout_page = 0
            elif 420 <= x <= 630:
                self.special_loadout_tab = "skills"
                self.quick_loadout_page = 0
            return
        if y >= 505:
            if 300 <= x <= 420:
                self.quick_loadout_page = max(0, self.quick_loadout_page - 1)
            elif 540 <= x <= 660:
                self.quick_loadout_page += 1
            return
        if not (175 <= y < 495 and 170 <= x <= 790):
            return
        row = (y - 175) // 40
        index = self.quick_loadout_page * 8 + row
        if self.special_loadout_tab == "skills":
            if index < len(self.unlocked_abilities):
                self.toggle_equipped_skill(self.unlocked_abilities[index])
        else:
            owned = self.owned_special_weapons
            if index < len(owned):
                weapon_id = owned[index]
                self.equipped_special_weapon = weapon_id
                self.message = f'{MARKET_WEAPONS[weapon_id]["name"].upper()} EQUIPPED'
                self.message_until = time.monotonic() + 2
                self.save_game()

    def draw_quick_loadout(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#080b10",
                           stipple="gray50", outline="", tags="frame")
        c.create_rectangle(135, 85, 825, 565, fill="#202a27",
                           outline="#d4bd91", width=2, tags="frame")
        c.create_text(WIDTH / 2, 108, text="QUICK LOADOUT",
                      fill="#f0d7c5", font=("Segoe UI", 19, "bold"), tags="frame")
        for x1, x2, label, tab in (
                (180, 390, "SPECIAL WEAPONS", "weapons"),
                (420, 630, "BOSS SKILLS", "skills")):
            selected = self.special_loadout_tab == tab
            c.create_rectangle(x1, 125, x2, 160,
                               fill="#53634d" if selected else "#35443d",
                               outline="#d4bd91", tags="frame")
            c.create_text((x1 + x2) / 2, 142, text=label,
                          fill="#fff1d2", font=("Segoe UI", 9, "bold"),
                          tags="frame")
        if self.special_loadout_tab == "skills":
            items = self.unlocked_abilities
            pages = max(1, (len(items) + 7) // 8)
            equipped_names = {skill[0] for skill in self.equipped_abilities}
            page_items = items[self.quick_loadout_page * 8:
                               self.quick_loadout_page * 8 + 8]
            for row, skill in enumerate(page_items):
                y = 175 + row * 40
                equipped = skill in self.equipped_abilities
                c.create_rectangle(170, y, 790, y + 34,
                                   fill="#46523e" if equipped else "#29332f",
                                   outline="#e5c874" if equipped else "#69766b",
                                   tags="frame")
                c.create_text(190, y + 17, anchor="w", text=skill[0],
                              fill="#f0d7c5", font=("Segoe UI", 9, "bold"),
                              tags="frame")
                c.create_text(770, y + 17, anchor="e",
                              text="EQUIPPED" if skill[0] in equipped_names else "CLICK TO EQUIP",
                              fill="#e5c874", font=("Segoe UI", 8, "bold"),
                              tags="frame")
            if not items:
                c.create_text(WIDTH / 2, 300, text="NO BOSS SKILLS OWNED",
                              fill="#c2c7b9", font=("Segoe UI", 11, "bold"),
                              tags="frame")
        else:
            items = self.owned_special_weapons
            pages = max(1, (len(items) + 7) // 8)
            page_items = items[self.quick_loadout_page * 8:
                               self.quick_loadout_page * 8 + 8]
            for row, weapon_id in enumerate(page_items):
                weapon = MARKET_WEAPONS[weapon_id]
                y = 175 + row * 40
                equipped = weapon_id == self.equipped_special_weapon
                c.create_rectangle(170, y, 790, y + 34,
                                   fill="#46523e" if equipped else "#29332f",
                                   outline="#e5c874" if equipped else "#69766b",
                                   tags="frame")
                c.create_text(190, y + 17, anchor="w",
                              text=f'{weapon["name"]} [{weapon["type"]}]',
                              fill="#f0d7c5", font=("Segoe UI", 9, "bold"),
                              tags="frame")
                c.create_text(770, y + 17, anchor="e",
                              text="EQUIPPED" if equipped else "CLICK TO EQUIP",
                              fill="#e5c874", font=("Segoe UI", 8, "bold"),
                              tags="frame")
            if not items:
                c.create_text(WIDTH / 2, 300, text="NO SPECIAL WEAPONS OWNED",
                              fill="#c2c7b9", font=("Segoe UI", 11, "bold"),
                              tags="frame")
        self.quick_loadout_page = min(self.quick_loadout_page, pages - 1)
        c.create_rectangle(300, 505, 420, 545, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(360, 525, text="◀ PREVIOUS",
                      fill="#fff1d2", font=("Segoe UI", 8, "bold"),
                      tags="frame")
        c.create_text(WIDTH / 2, 525,
                      text=f"PAGE {self.quick_loadout_page + 1}/{pages}  |  PRESS ` OR ESC TO CLOSE",
                      fill="#c2c7b9", font=("Segoe UI", 8, "bold"),
                      tags="frame")
        c.create_rectangle(540, 505, 660, 545, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(600, 525, text="NEXT ▶",
                      fill="#fff1d2", font=("Segoe UI", 8, "bold"),
                      tags="frame")
        c.create_rectangle(680, 505, 790, 545, fill="#53634d",
                           outline="#d4bd91", tags="frame")
        c.create_text(735, 525, text="CLOSE",
                      fill="#fff1d2", font=("Segoe UI", 9, "bold"),
                      tags="frame")

    def handle_progression_click(self, x, y):
        if y < 112 and 300 <= x <= 430:
            self.advance_progression_page(-1)
            return
        if y < 112 and 530 <= x <= 660:
            self.advance_progression_page(1)
            return
        start = self.progression_page * 12 + 1
        for index in range(12):
            col, row = index % 4, index // 4
            x1, y1 = 36 + col * 153, 170 + row * 96
            floor = start + index
            if x1 <= x <= x1 + 137 and y1 <= y <= y1 + 72:
                self.select_progression_floor(floor)
                return
        if y >= 555:
            if 40 <= x <= 260:
                self.state = self.progression_return_state
            elif 355 <= x <= 595:
                self.open_marketplace()
            elif 655 <= x <= 920:
                if (self.progression_return_state == "post_boss"
                        and self.progression_selected_floor == self.stage_number()):
                    self.continue_stage()
                elif self.floor_record(self.progression_selected_floor):
                    self.replay_cleared_floor(self.progression_selected_floor)

    def visible_market_weapons(self):
        weapons = [
            weapon for weapon in MARKET_WEAPONS
            if self.market_filter == "ALL" or weapon["type"] == self.market_filter
        ]
        query = self.market_search.strip().casefold()
        if query:
            weapons = [
                weapon for weapon in weapons
                if query in weapon["name"].casefold()
                or query in weapon["type"].casefold()
                or query in str(weapon["id"])
            ]
        return weapons

    def handle_market_click(self, x, y):
        if 410 <= x <= 570 and 50 <= y <= 100:
            self.open_side_quests("marketplace")
            return
        if 760 <= x <= 915 and 50 <= y <= 100:
            self.open_skill_forge()
            return
        if 585 <= x <= 745 and 50 <= y <= 100:
            self.open_skill_market()
            return
        if y >= 570 and x <= 180:
            self.state = "floor_progression"
            return
        if y >= 570 and 210 <= x <= 360:
            filters = ("ALL", "LASER", "ROCKET", "ATOMIC")
            self.market_filter = filters[
                (filters.index(self.market_filter) + 1) % len(filters)
            ]
            self.market_page = 0
            return
        if y >= 570 and x >= 760:
            self.market_page = max(0, self.market_page - 1)
            return
        if y >= 570 and 570 <= x <= 740:
            self.market_page += 1
            return
        if 125 <= y <= 546 and 52 <= x <= 910:
            row = (y - 125) // 43
            visible = self.visible_market_weapons()
            index = self.market_page * 10 + row
            if 0 <= row < 10 and 0 <= index < len(visible):
                self.open_weapon_preview(visible[index]["id"])

    def fire_special_weapon(self, now, fx, fy):
        if self.special_shots_left <= 0 or self.equipped_special_weapon is None:
            return
        weapon = MARKET_WEAPONS[self.equipped_special_weapon]
        self.special_shots_left -= 1
        start_x = self.player["x"] + fx * 20
        start_y = self.player["y"] + fy * 20
        if weapon["type"] == "LASER":
            end_x, end_y = start_x + fx * 900, start_y + fy * 900
            self.effects.append({
                "kind": "laser", "line": (start_x, start_y, end_x, end_y),
                "until": now + 0.25,
            })
            for enemy in self.enemies[:]:
                ex, ey = enemy["x"] - start_x, enemy["y"] - start_y
                along = ex * fx + ey * fy
                across = abs(ex * fy - ey * fx)
                if 0 <= along <= 900 and across <= enemy["radius"] + 12:
                    enemy["hp"] -= 500
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
        elif weapon["type"] == "ROCKET":
            self.projectiles.append({
                "x": start_x, "y": start_y, "vx": fx * 430, "vy": fy * 430,
                "damage": max(85, int(85 * 0.15)),
                "life": 1.4, "kind": "rocket", "owner": self.player,
            })
        else:
            self.effects.append({
                "kind": "atomic_bomb",
                "x": self.mouse_position[0],
                "y": self.mouse_position[1],
                "impact_at": now + 0.8,
                "until": now + 1.5,
                "detonated": False,
            })
        self.save_game()

    def blast_at(self, x, y, now, damage, radius):
        self.effects.append({
            "kind": "atomic", "x": x, "y": y, "radius": radius,
            "until": now + 0.7,
        })
        for enemy in self.enemies[:]:
            if math.hypot(enemy["x"] - x, enemy["y"] - y) <= radius:
                enemy["hp"] -= damage
                if enemy["hp"] <= 0:
                    self.defeat_enemy(enemy, now)

    def collect_floor_coins(self):
        coin_pickups = [
            pickup for pickup in self.pickups if pickup["kind"] == "coins"
        ]
        total = sum(pickup["value"] for pickup in coin_pickups)
        if total:
            self.pickups = [
                pickup for pickup in self.pickups if pickup["kind"] != "coins"
            ]
            self.coins += total
            self.message = f"FLOOR COINS COLLECTED  +{total} COINS"
            self.save_game()
        else:
            self.message = "NO FLOOR COINS LEFT TO COLLECT"
        self.message_until = time.monotonic() + 2.5

    def resolve_auto_aim_prompt(self, enabled):
        self.auto_aim_enabled = enabled
        self.show_next_quest()

    def show_next_quest(self):
        self.active_quest = None
        self.prepare_quest_options()
        self.state = "quest_select"

    def start_rescue_route(self):
        if not self.rescue_route_unlocked:
            return
        self.rescue_battle = True
        self.active_quest = None
        self.demon_ally_next_attack = time.monotonic() + 0.8
        self.wave_pause = 0
        self.enemies.clear()
        self.pickups.clear()
        self.projectiles.clear()
        self.effects.clear()
        self.player["x"] = WIDTH / 2
        self.player["y"] = (ARENA[1] + ARENA[3]) / 2
        self.state = "boss_warning"
        self.boss_warning_until = time.monotonic() + 3
        self.message = "THE FIVE CLUES OPEN A PATH TO THE TOP FLOOR"
        self.message_until = self.boss_warning_until
        self.keys.clear()

    def begin_stage(self):
        self.state = "stage_intro"
        self.stage_intro_until = time.monotonic() + 2.2
        self.spawn_wave()
        self.message = f"{self.stage_label()}  -  PREPARE FOR BATTLE"
        self.message_until = self.stage_intro_until

    def open_shop(self):
        self.shop_return_state = self.state
        self.state = "shop"

    def handle_shop_click(self, x, y):
        row = (y - 230) // 72
        upgrades = (
            ("weapon", 15 + self.weapon_upgrade * 12),
            ("skill", 25 + self.skill_upgrade * 15),
            ("health", 20 + self.health_upgrade * 12),
        )
        if 0 <= row < len(upgrades) and 180 <= x <= 780:
            upgrade, cost = upgrades[row]
            if self.coins < cost:
                self.message = f"NOT ENOUGH COINS  -  NEED {cost}"
                self.message_until = time.monotonic() + 1.5
                return
            self.coins -= cost
            if upgrade == "weapon":
                self.weapon_upgrade += 1
            elif upgrade == "skill":
                self.skill_upgrade += 1
            else:
                self.health_upgrade += 1
                self.player["max_hp"] += 25
                self.player["hp"] = min(
                    self.player["max_hp"], self.player["hp"] + 25
                )
            self.message = f"{upgrade.upper()} UPGRADED!"
            self.message_until = time.monotonic() + 1.5
            self.save_game()

    def handle_character_click(self, x, y):
        if 640 <= x <= 920 and 505 <= y <= 545:
            self.open_special_loadout("character")
            return
        if 70 <= x <= 260 and 550 <= y <= 600:
            self.state = "paused"
            return
        if 125 <= y <= 170:
            category_index = (x - 30) // 180
            if 0 <= category_index < len(COSMETIC_ITEMS) and x <= 930:
                self.customize_category = category_index
                self.customize_item = 0
            return
        category = tuple(COSMETIC_ITEMS)[self.customize_category]
        items = COSMETIC_ITEMS[category]
        if 210 <= y <= 488 and 60 <= x <= 600:
            item_index = (y - 210) // 70
            if item_index < len(items):
                self.customize_item = item_index
            return

        if not (60 <= x <= 600 and 505 <= y <= 550):
            return
        name, cost, _ = items[self.customize_item]
        if name not in self.owned_cosmetics[category]:
            if self.coins < cost:
                self.message = f"NOT ENOUGH COINS  -  NEED {cost}"
                self.message_until = time.monotonic() + 1.5
                return
            self.coins -= cost
            self.pending_cosmetic_chest = (category, name)
            self.cosmetic_chest_clicks = 0
            self.state = "cosmetic_chest"
            return
        self.equipped_cosmetics[category] = name
        self.message = f"{name.upper()} EQUIPPED"
        self.message_until = time.monotonic() + 1.5

    def handle_cosmetic_chest_click(self, x, y):
        if not (350 <= x <= 610 and 285 <= y <= 455):
            return
        self.cosmetic_chest_clicks += 1
        if self.cosmetic_chest_clicks < 5:
            return
        category, name = self.pending_cosmetic_chest
        self.owned_cosmetics[category].add(name)
        self.equipped_cosmetics[category] = name
        self.pending_cosmetic_chest = None
        self.state = "character"
        self.message = f"CHEST OPENED  -  {name.upper()} EQUIPPED"
        self.message_until = time.monotonic() + 2

    def handle_boss_chest_click(self, x, y):
        for chest in self.boss_chests:
            if chest["opened"]:
                continue
            if abs(x - chest["x"]) <= 24 and abs(y - chest["y"]) <= 18:
                chest["clicks"] += 1
                if chest["clicks"] == 5:
                    chest["opened"] = True
                    if self.boss_weapon_owned:
                        self.coins += 40
                        reward = "40 BONUS COINS"
                    else:
                        self.boss_weapon_owned = True
                        self.advanced_gun_owned = True
                        self.owned_cosmetics["GUN"].add("Warden Breaker")
                        self.equipped_cosmetics["GUN"] = "Warden Breaker"
                        reward = "WARDEN BREAKER RIFLE  -  SKILL COOLDOWN -30%"
                    self.message = f"BOSS CHEST OPENED  -  {reward}"
                    self.message_until = time.monotonic() + 3
                else:
                    self.message = f"BOSS CHEST  -  {chest['clicks']}/5 CLICKS"
                    self.message_until = time.monotonic() + 1
                return True
        return False

    def update_skill_acquire(self, dt, now):
        corpse = self.boss_corpses[-1] if self.boss_corpses else None
        if corpse is None or self.pending_skill is None:
            return
        head_x, head_y = corpse["x"] + 22, corpse["y"] - 8
        distance = math.hypot(
            self.player["x"] - head_x, self.player["y"] - head_y
        )
        if "e" in self.keys and distance <= 82:
            self.skill_acquire_progress = min(2.5, self.skill_acquire_progress + dt)
        else:
            self.skill_acquire_progress = 0
        if self.skill_acquire_progress < 2.5:
            return

        skill = self.pending_skill
        was_known = skill in self.unlocked_abilities
        if skill not in self.unlocked_abilities:
            self.unlocked_abilities.append(skill)
        self.skill_copies.append(skill)
        self.track_side_quest_progress("skills_obtained")
        if skill not in self.equipped_abilities and len(self.equipped_abilities) < MAX_ABILITIES:
            self.equipped_abilities.append(skill)
        self.has_boss_ability = bool(self.equipped_abilities)
        if skill in self.equipped_abilities:
            self.active_ability = self.equipped_abilities.index(skill)
        self.ability_cooldowns.setdefault(skill[0], 0)
        self.pending_skill = None
        self.skill_acquire_progress = 0
        self.state = "post_boss"
        self.travel_ready_at = now
        self.message = (
            f"{'DUPLICATE SKILL COPY ACQUIRED' if was_known else 'SKILL ACQUIRED'}"
            f"  -  {skill[0]}  |  MANAGE SKILLS IN SPECIAL WEAPONS"
        )
        self.message_until = now + 2.5
        self.save_game()

    def update(self, dt, now):
        if self.state == "boss_skill" and self.pending_skill:
            self.update_skill_acquire(dt, now)
        p = self.player
        if now >= self.time_freeze_until:
            self.time_freeze_until = 0
            self.time_freeze_owner = None
        dx = (("d" in self.keys or "right" in self.keys) -
              ("a" in self.keys or "left" in self.keys))
        dy = (("s" in self.keys or "down" in self.keys) -
              ("w" in self.keys or "up" in self.keys))
        player_frozen = now < p["frozen_until"]
        if (dx or dy) and now >= p["knockdown_until"] and not player_frozen:
            length = math.hypot(dx, dy)
            dx, dy = dx / length, dy / length
            p["face"] = (dx, dy)
            p["x"] += dx * p["speed"] * dt
            p["y"] += dy * p["speed"] * dt
            p["x"] = max(ARENA[0] + 16, min(ARENA[2] - 16, p["x"]))
            p["y"] = max(ARENA[1] + 16, min(ARENA[3] - 16, p["y"]))

        mouse_dx = self.mouse_position[0] - p["x"]
        mouse_dy = self.mouse_position[1] - p["y"]
        if math.hypot(mouse_dx, mouse_dy) > 8:
            aim_length = math.hypot(mouse_dx, mouse_dy)
            p["face"] = (mouse_dx / aim_length, mouse_dy / aim_length)

        if "space" in self.keys and now >= p["attack_ready"] and not player_frozen:
            fx, fy = p["face"]
            self.shoot(now, fx, fy)

        if self.wave_left > 0 and len(self.enemies) < 5 + self.wave:
            self.spawn_enemy()

        for enemy in self.enemies[:]:
            if (now < self.time_freeze_until
                    and enemy is not self.time_freeze_owner):
                continue
            ex, ey = p["x"] - enemy["x"], p["y"] - enemy["y"]
            distance = max(1, math.hypot(ex, ey))
            if distance > enemy["radius"] + self.player_radius() + 5:
                speed = enemy["speed"] * (0.45 if now < enemy.get("slowed_until", 0) else 1)
                enemy["x"] += ex / distance * speed * dt
                enemy["y"] += ey / distance * speed * dt
            elif now >= enemy["attack_ready"] and now >= p["hurt_until"] and now >= p["knockdown_until"]:
                shielded = now < p["shield_until"]
                if not shielded:
                    p["hp"] -= enemy["damage"]
                p["hurt_until"] = now + 0.58
                enemy["attack_ready"] = now + 0.95
                self.message = "IRONBARK GUARD ABSORBS THE HIT!" if shielded else "UNDER ATTACK!"
                self.message_until = now + 0.65
                if p["hp"] <= 0:
                    p["hp"] = 0
                    self.state = "gameover"
                    self.keys.clear()
                    return
            if enemy["kind"] in ("boss", "minion_boss"):
                self.update_boss(enemy, now)
            elif enemy["kind"] == "kidnapper":
                self.update_kidnapper(enemy, now)

        for projectile in self.projectiles[:]:
            if (now < self.time_freeze_until
                    and projectile.get("owner", p) is not self.time_freeze_owner):
                continue
            projectile["x"] += projectile["vx"] * dt
            projectile["y"] += projectile["vy"] * dt
            projectile["life"] -= dt
            hit = False
            for enemy in self.enemies[:]:
                if math.hypot(projectile["x"] - enemy["x"],
                              projectile["y"] - enemy["y"]) <= enemy["radius"] + 5:
                    if projectile.get("kind") == "rocket":
                        self.blast_at(projectile["x"], projectile["y"], now, 750, 35)
                        hit = True
                        break
                    damage = projectile["damage"]
                    if enemy["kind"] == "kidnapper":
                        damage = int(
                            damage * (2.5 if self.advanced_gun_owned and
                                      self.equipped_cosmetics["GUN"] == "Warden Breaker"
                                      else 0.3)
                        )
                    enemy["hp"] -= damage
                    enemy["hurt_until"] = now + 0.1
                    hit = True
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
                    break
            if (not hit and projectile.get("kind") == "rocket"
                    and projectile["life"] <= 0):
                self.blast_at(projectile["x"], projectile["y"], now, 750, 35)
                hit = True
            if hit or projectile["life"] <= 0:
                self.projectiles.remove(projectile)

        self.effects = [effect for effect in self.effects if effect["until"] > now]
        for effect in self.effects:
            if (effect["kind"] == "atomic_bomb"
                    and not effect["detonated"] and now >= effect["impact_at"]):
                effect["detonated"] = True
                effect["kind"] = "atomic"
                effect["until"] = now + 0.7
                self.blast_at(effect["x"], effect["y"], now, 650, 275)
            if effect["kind"] == "shield":
                effect["x"], effect["y"] = p["x"], p["y"]
            if (effect["kind"] in ("ice_star_fall", "epic_fall")
                    and not effect.get("hit")
                    and now >= effect["impact_at"]):
                self.resolve_impact(effect, now)
        for pickup in self.pickups[:]:
            if math.hypot(p["x"] - pickup["x"], p["y"] - pickup["y"]) < 24:
                self.pickups.remove(pickup)
                if pickup["kind"] == "medkit":
                    p["hp"] = min(p["max_hp"], p["hp"] + 30)
                    self.message = "FIELD MEDKIT  +30 HP"
                else:
                    self.coins += pickup["value"]
                    self.message = f"COINS COLLECTED  +{pickup['value']}"
                self.message_until = now + 1.3

        if self.state == "playing" and not self.enemies and self.wave_left == 0:
            if self.wave_pause == 0:
                self.wave_pause = now + 1.8
                self.message = "AREA SECURED"
                self.message_until = self.wave_pause
            elif now >= self.wave_pause:
                self.wave_pause = 0
                if self.floor_wave < self.floor_wave_count():
                    self.floor_wave += 1
                    self.wave += 1
                    self.spawn_wave()

        if self.rescue_battle and now >= self.demon_ally_next_attack:
            target = next(
                (enemy for enemy in self.enemies if enemy["kind"] == "kidnapper"),
                None,
            )
            if target:
                target["hp"] -= 48
                target["hurt_until"] = now + 0.15
                self.demon_ally_next_attack = now + 0.85
                self.effects.append({
                    "kind": "burst", "x": target["x"], "y": target["y"],
                    "until": now + 0.25,
                })
                if target["hp"] <= 0:
                    self.defeat_enemy(target, now)

    def update_kidnapper(self, boss, now):
        if now >= boss["teleport_ready"]:
            p = self.player
            fx, fy = p["face"]
            boss["x"] = max(ARENA[0] + 35, min(ARENA[2] - 35, p["x"] - fx * 105))
            boss["y"] = max(ARENA[1] + 35, min(ARENA[3] - 35, p["y"] - fy * 105))
            boss["special_line"] = (boss["x"], boss["y"], p["x"], p["y"])
            boss["special_until"] = now + 0.55
            boss["special_ready"] = now + 2.4
            boss["teleport_ready"] = now + 5
            self.effects.append({
                "kind": "burst", "x": boss["x"], "y": boss["y"],
                "until": now + 0.45,
            })
            self.message = "THE VEIL THIEF TELEPORTS BEHIND YOU!"
            self.message_until = now + 1
        elif boss["special_until"] > 0 and now >= boss["special_ready"] - 1.85:
            boss["special_until"] = 0
            boss["special_line"] = None
        if now >= boss["clone_ready"]:
            clones = sum(enemy["kind"] == "kidnapper_clone" for enemy in self.enemies)
            for offset in (-1, 1):
                if clones >= 4:
                    break
                self.enemies.append({
                    "x": max(ARENA[0] + 20, min(ARENA[2] - 20,
                                               boss["x"] + offset * 55)),
                    "y": max(ARENA[1] + 20, min(ARENA[3] - 20,
                                               boss["y"] + 35)),
                    "hp": 105,
                    "max_hp": 105,
                    "speed": 90,
                    "damage": 12,
                    "xp": 0,
                    "radius": 17,
                    "kind": "kidnapper_clone",
                    "attack_ready": now + 0.7,
                    "hurt_until": 0,
                })
            boss["clone_ready"] = now + 8
            self.message = "A VEIL THIEF CLONE STEPS OUT OF THE SHADOWS!"
            self.message_until = now + 1.4

    def update_boss(self, boss, now):
        if now >= boss["special_ready"] and boss["special_until"] <= 0:
            p = self.player
            skills = boss.get("skills") or [boss["skill"]]
            skill_index = boss.get("next_skill_index", 0) % len(skills)
            boss["skill"] = skills[skill_index]
            boss["next_skill_index"] = (skill_index + 1) % len(skills)
            skill_name = boss["skill"][0]
            boss["special_ready"] = now + 5.5
            if skill_name == "Time Freeze":
                self.time_freeze_owner = boss
                self.time_freeze_until = now + 3
                p["frozen_until"] = self.time_freeze_until
                self.effects.append({
                    "kind": "time_freeze", "x": p["x"], "y": p["y"],
                    "until": self.time_freeze_until,
                })
                self.message = f'{boss["boss_name"]}: "TIME FREEZE!"'
                self.message_until = now + 2
                self.audio.speak(f'{boss["boss_name"]}: Time Freeze!')
                return
            if skill_name == "Ice Stars":
                self.spawn_ice_stars(
                    p["x"], p["y"], now, boss, damage=24, count=3,
                    spread=34,
                )
                self.message = f'{boss["boss_name"]}: "ICE STARS!"'
                self.message_until = now + 1.5
                self.audio.speak(f'{boss["boss_name"]}: Ice Stars!')
                return
            if skill_name == "Epic Fall":
                self.spawn_epic_fall(
                    p["x"], p["y"], now, boss, damage=42
                )
                self.message = f'{boss["boss_name"]}: "EPIC FALL!"'
                self.message_until = now + 1.5
                self.audio.speak(f'{boss["boss_name"]}: Epic Fall!')
                return
            dx, dy = p["x"] - boss["x"], p["y"] - boss["y"]
            distance = max(1, math.hypot(dx, dy))
            direction = (dx / distance, dy / distance)
            boss["special_line"] = (
                boss["x"], boss["y"],
                boss["x"] + direction[0] * (560 if skill_name in ("Groundsplit", "Ember Volley") else 320),
                boss["y"] + direction[1] * (560 if skill_name in ("Groundsplit", "Ember Volley") else 320),
            )
            boss["special_until"] = now + 1.05
            boss["special_hit"] = False
            boss["special_ready"] = now + 4.2
            boss["special_direction"] = direction
            dialogue = {
                "Groundsplit": "The earth will swallow you whole!",
                "Frost Nova": "Kneel beneath the endless winter!",
                "Ember Volley": "Run from the fire. It follows!",
                "Ironbark Guard": "The whole forest strikes as one!",
            }
            self.message = f'{boss["boss_name"]}: "{dialogue[skill_name]}"'
            self.message_until = now + 1.4
            self.audio.speak(f'{boss["boss_name"]}: {dialogue[skill_name]}')
        elif boss["special_until"] > 0 and now >= boss["special_until"]:
            x1, y1, x2, y2 = boss["special_line"]
            p = self.player
            line_dx, line_dy = x2 - x1, y2 - y1
            line_length_sq = line_dx * line_dx + line_dy * line_dy
            projection = max(0, min(1, ((p["x"] - x1) * line_dx +
                                        (p["y"] - y1) * line_dy) / line_length_sq))
            closest_x, closest_y = x1 + projection * line_dx, y1 + projection * line_dy
            skill_name = boss["skill"][0]
            distance_to_boss = math.hypot(p["x"] - boss["x"], p["y"] - boss["y"])
            direction = boss["special_direction"]
            along = (p["x"] - boss["x"]) * direction[0] + (p["y"] - boss["y"]) * direction[1]
            across = abs((p["x"] - boss["x"]) * direction[1] -
                         (p["y"] - boss["y"]) * direction[0])
            if skill_name == "Frost Nova":
                in_aoe = distance_to_boss < 270
            elif skill_name == "Ironbark Guard":
                in_aoe = distance_to_boss < 325
            elif skill_name == "Ember Volley":
                in_aoe = 0 < along < 560 and across < 105 + along * 0.18
            else:
                in_aoe = 0 < along < 560 and across < 70
            if not boss["special_hit"] and in_aoe:
                damage = 25 if boss["kind"] == "minion_boss" else 50
                p["hp"] = max(0, p["hp"] - damage)
                p["hurt_until"] = now + 0.9
                if skill_name == "Groundsplit":
                    p["knockdown_until"] = now + 1.15
                    p["x"] = max(ARENA[0] + 20, min(
                        ARENA[2] - 20, p["x"] + direction[0] * 55
                    ))
                    p["y"] = max(ARENA[1] + 20, min(
                        ARENA[3] - 20, p["y"] + direction[1] * 55
                    ))
                self.message = f'"{skill_name} hits!  -{damage} HP"'
                self.message_until = now + 1.4
                boss["special_hit"] = True
                if p["hp"] <= 0:
                    self.state = "gameover"
                    self.keys.clear()
            self.effects.append({"kind": "fissure", "line": boss["special_line"],
                                 "until": now + 0.65, "skill": boss["skill"][0]})
            if skill_name == "Frost Nova":
                self.effects.append({"kind": "boss_frost", "x": boss["x"], "y": boss["y"],
                                     "radius": 270, "until": now + 0.75})
            elif skill_name == "Ironbark Guard":
                self.effects.append({"kind": "boss_guard", "x": boss["x"], "y": boss["y"],
                                     "radius": 325, "until": now + 0.75})
            elif skill_name == "Ember Volley":
                self.effects.append({"kind": "boss_ember", "line": boss["special_line"],
                                     "until": now + 0.75})
            boss["special_until"] = 0
            boss["special_line"] = None

    def shoot(self, now, dx, dy):
        p = self.player
        if (now < p["attack_ready"] or now < p["knockdown_until"]
                or now < p["frozen_until"]):
            return
        if self.auto_aim_enabled and self.enemies:
            target = min(
                self.enemies,
                key=lambda enemy: (enemy["x"] - p["x"]) ** 2 +
                (enemy["y"] - p["y"]) ** 2,
            )
            dx, dy = target["x"] - p["x"], target["y"] - p["y"]
        length = max(1, math.hypot(dx, dy))
        fx, fy = dx / length, dy / length
        p["face"] = (fx, fy)
        p["attack_ready"] = now + 0.22
        p["shoot_until"] = now + 0.12
        p["attack_until"] = now + 0.16
        start_x, start_y = p["x"] + fx * 20, p["y"] + fy * 20
        self.projectiles.append({
            "x": start_x, "y": start_y, "vx": fx * 520, "vy": fy * 520,
            "damage": 26 + (p["level"] - 1) * 4 + self.weapon_upgrade * 8,
            "life": 0.75,
        })
        self.fire_special_weapon(now, fx, fy)
        self.audio.play("shot")
        self.effects.append({"kind": "muzzle", "x": start_x, "y": start_y,
                             "until": now + 0.1, "direction": (fx, fy)})

    def defeat_enemy(self, enemy, now):
        if enemy not in self.enemies:
            return
        self.enemies.remove(enemy)
        self.audio.play("kill")
        self.kills += 1
        if self.superhuman_active:
            self.superhuman_xp_earned += enemy["xp"]
        else:
            self.player["xp"] += enemy["xp"]
        quest_just_completed = False
        minion_coin_reward = None
        end_superhuman_after_boss = False
        if self.active_quest and not self.quest_complete:
            self.quest_progress += 1
            if self.quest_progress >= self.active_quest[2]:
                self.quest_complete = True
                quest_just_completed = True
                self.quests_completed.add(self.stage_number())
                self.coins += self.quest_reward
                self.message = f"QUEST COMPLETE  +{self.quest_reward} COINS"
                self.message_until = now + 2.5

        if enemy["kind"] in ("boss", "minion_boss", "kidnapper"):
            self.encounter_clear = True
            is_final_boss = enemy.get(
                "floor_final_boss",
                enemy["kind"] != "minion_boss",
            )
            end_superhuman_after_boss = is_final_boss
            if enemy["kind"] == "minion_boss":
                difficulty = enemy.get("difficulty", self.minion_difficulty or 0)
                reward = MINION_DIFFICULTIES[difficulty][2]
                self.coins += reward
                minion_coin_reward = reward
            else:
                self.pickups.append({
                    "x": enemy["x"], "y": enemy["y"],
                    "kind": "coins", "value": 40,
                })
            self.wave_left = 0
            self.wave_pause = 0
            self.keys.clear()
            self.territories[self.region] = True
            if is_final_boss and enemy["kind"] != "kidnapper":
                self.record_floor_clear()
            if enemy["kind"] == "kidnapper":
                self.enemies = [
                    remaining for remaining in self.enemies
                    if remaining["kind"] != "kidnapper_clone"
                ]
                self.state = "kidnapper_reveal"
                self.kidnapper_reveal_until = now + 6
                self.message = "DEMON ALLY: THE KIDNAPPER IS DEFEATED!"
                self.message_until = self.kidnapper_reveal_until
                self.audio.speak("The kidnapper is defeated. The Demon King is free!")
            else:
                self.boss_corpses.append({
                    "x": enemy["x"],
                    "y": enemy["y"],
                    "name": enemy["boss_name"],
                    "skill": enemy["skill"] or self.boss_skill(),
                })
                self.boss_chests.append({
                    "x": enemy["x"] + 40,
                    "y": enemy["y"] + 24,
                    "clicks": 0,
                    "opened": False,
                    "reward": ("40 BONUS COINS" if self.boss_weapon_owned
                               else "WARDEN BREAKER"),
                })
                if enemy["kind"] == "minion_boss":
                    clue = enemy["clue"]
                    if clue and clue not in self.tower_clues:
                        self.tower_clues.append(clue)
                    if len(self.tower_clues) >= len(TOWER_MINIONS):
                        self.rescue_route_unlocked = True
                        self.advanced_gun_owned = True
                        self.owned_cosmetics["GUN"].add("Warden Breaker")
                        self.equipped_cosmetics["GUN"] = "Warden Breaker"
                    self.clue_dialogue = f"{enemy['boss_name']}: \"{enemy['clue']}\""
                    if enemy["skill"] in MILESTONE_BOSS_SKILLS:
                        self.pending_skill = enemy["skill"]
                        self.skill_acquire_progress = 0
                    self.state = "minion_reveal"
                    self.boss_dialogue_until = now + 5
                    self.message = "A TOWER MINION HAS LEFT A CLUE"
                    self.message_until = self.boss_dialogue_until
                    self.audio.speak(self.clue_dialogue)
                else:
                    self.pending_skill = enemy["skill"]
                    self.skill_acquire_progress = 0
                    self.last_spoken_dialogue = None
                    self.state = "boss_cutscene"
                    self.boss_cutscene_until = now + 2.4
                    self.message = f"{enemy['boss_name']} HAS FALLEN"
                    self.message_until = self.boss_cutscene_until
        else:
            if random.random() < 0.16:
                self.pickups.append({"x": enemy["x"], "y": enemy["y"], "kind": "medkit",
                                     "value": 0})
            if random.random() < 0.3:
                self.pickups.append({"x": enemy["x"] + random.randint(-12, 12),
                                     "y": enemy["y"] + random.randint(-12, 12),
                                     "kind": "coins", "value": random.randint(1, 4)})
        self.effects.append({"kind": "burst", "x": enemy["x"], "y": enemy["y"],
                             "until": now + 0.3})
        self.check_level_up()
        if end_superhuman_after_boss:
            self.end_superhuman(save=False)
        if minion_coin_reward is not None:
            self.message = f"DEMON MINION DEFEATED  +{minion_coin_reward:,} COINS"
            self.message_until = now + 3
        if quest_just_completed or enemy["kind"] in (
                "boss", "minion_boss", "kidnapper"):
            self.save_game()

    def use_boss_ability(self, now, ability_index=None,
                         target_x=None, target_y=None):
        p = self.player
        if not self.equipped_abilities:
            self.message = 'SCOUT: "I need to defeat a warlord to learn their technique."'
            self.message_until = now + 1.8
            return
        if ability_index is None:
            ability_index = self.active_ability
        if not 0 <= ability_index < len(self.equipped_abilities):
            return
        self.active_ability = ability_index
        skill = self.equipped_abilities[ability_index]
        skill_name = skill[0]
        ready_at = self.ability_cooldowns.get(skill_name, 0)
        if now < ready_at:
            self.message = f"{skill_name.upper()} COOLDOWN  -  {ready_at - now:.1f}s"
            self.message_until = now + 1
            return
        if now < p["knockdown_until"] or now < p["frozen_until"]:
            return
        if skill_name in TARGETED_SKILLS and (target_x is None or target_y is None):
            self.pending_target_ability = ability_index
            self.message = f"{skill_name.upper()} READY  -  RIGHT-CLICK A TARGET"
            self.message_until = now + 2
            return
        self.ability_cooldowns[skill_name] = now + self.boss_ability_cooldown()
        p["ability_ready"] = self.ability_cooldowns[skill_name]
        p["ability_until"] = now + 0.55
        self.message = f'SCOUT: "{skill[1]}"'
        self.message_until = now + 1.6
        self.audio.speak(skill[1])
        power = 1 + self.skill_upgrade * 0.45
        area = 1 + self.skill_upgrade * 0.16
        if skill_name in self.crafted_skill_data:
            damage, skill_range = self.skill_damage_range(skill)
            radius = skill_range * area
            self.effects.append({
                "kind": "frost", "x": p["x"], "y": p["y"],
                "radius": radius, "until": now + 0.65,
            })
            for enemy in self.enemies[:]:
                if math.hypot(enemy["x"] - p["x"], enemy["y"] - p["y"]) <= radius:
                    enemy["hp"] -= int(damage * power)
                    enemy["hurt_until"] = now + 0.2
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
        elif skill[0] == "Groundsplit":
            fx, fy = p["face"]
            end_x, end_y = p["x"] + fx * 320 * area, p["y"] + fy * 320 * area
            self.effects.append({"kind": "player_fissure",
                                 "line": (p["x"], p["y"], end_x, end_y),
                                 "until": now + 0.55})
            for enemy in self.enemies[:]:
                ex, ey = enemy["x"] - p["x"], enemy["y"] - p["y"]
                along = ex * fx + ey * fy
                across = abs(ex * fy - ey * fx)
                if 0 <= along <= 320 * area and across < 68 * area + enemy["radius"]:
                    enemy["hp"] -= int(130 * power)
                    enemy["hurt_until"] = now + 0.2
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
        elif skill[0] == "Frost Nova":
            self.effects.append({"kind": "frost", "x": p["x"], "y": p["y"],
                                 "radius": 235 * area, "until": now + 0.55})
            for enemy in self.enemies[:]:
                if math.hypot(enemy["x"] - p["x"], enemy["y"] - p["y"]) <= 235 * area:
                    enemy["hp"] -= int(85 * power)
                    enemy["slowed_until"] = now + 3
                    enemy["hurt_until"] = now + 0.2
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
        elif skill[0] == "Ember Volley":
            angle = math.atan2(p["face"][1], p["face"][0])
            for offset in (-0.42, -0.21, 0, 0.21, 0.42):
                shot_angle = angle + offset
                fx, fy = math.cos(shot_angle), math.sin(shot_angle)
                self.projectiles.append({
                    "x": p["x"] + fx * 20, "y": p["y"] + fy * 20,
                    "vx": fx * 460, "vy": fy * 460,
                    "damage": int(70 * power), "life": 1.1, "kind": "ember",
                    "owner": p,
                })
        elif skill[0] == "Ironbark Guard":
            p["shield_until"] = now + 6 + self.skill_upgrade
            self.effects.append({"kind": "shield", "x": p["x"], "y": p["y"],
                                 "until": p["shield_until"]})
        elif skill_name == "Time Freeze":
            self.time_freeze_owner = p
            self.time_freeze_until = now + 3
            self.effects.append({
                "kind": "time_freeze", "x": p["x"], "y": p["y"],
                "until": self.time_freeze_until,
            })
            for enemy in self.enemies[:]:
                damage = max(1, math.floor(enemy["max_hp"] * 0.0199 + 0.5))
                enemy["hp"] -= damage
                enemy["hurt_until"] = now + 0.2
                if enemy["hp"] <= 0:
                    self.defeat_enemy(enemy, now)
        elif skill_name == "Ice Stars":
            self.spawn_ice_stars(
                target_x, target_y, now, p, damage=int(62 * power),
                count=5, spread=30 * area,
            )
        elif skill_name == "Epic Fall":
            self.spawn_epic_fall(
                target_x, target_y, now, p, damage=int(175 * power),
                radius=105 * area,
            )
        self.message = f'SCOUT: "{skill[1]}"'
        self.message_until = now + 1.6

    def spawn_ice_stars(self, x, y, now, caster, damage, count, spread):
        offsets = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
        for index in range(count):
            offset_x, offset_y = offsets[index % len(offsets)]
            target_x = max(ARENA[0] + 15, min(
                ARENA[2] - 15, x + offset_x * spread
            ))
            target_y = max(ARENA[1] + 15, min(
                ARENA[3] - 15, y + offset_y * spread
            ))
            impact_at = now + 0.72 + index * 0.08
            self.effects.append({
                "kind": "ice_star_fall",
                "x": target_x,
                "y": target_y,
                "start_y": max(ARENA[1], target_y - 190),
                "impact_at": impact_at,
                "until": impact_at + 0.38,
                "caster": caster,
                "damage": damage,
                "radius": 31,
                "hit": False,
            })

    def spawn_epic_fall(self, x, y, now, caster, damage, radius=95):
        x = max(ARENA[0] + radius, min(ARENA[2] - radius, x))
        y = max(ARENA[1] + radius, min(ARENA[3] - radius, y))
        impact_at = now + 0.9
        if caster is self.player:
            self.player["knockdown_until"] = impact_at
        self.effects.append({
            "kind": "epic_fall",
            "x": x,
            "y": y,
            "start_y": max(ARENA[1], y - 210),
            "impact_at": impact_at,
            "until": impact_at + 0.5,
            "caster": caster,
            "damage": damage,
            "radius": radius,
            "hit": False,
        })

    def resolve_impact(self, effect, now):
        effect["hit"] = True
        caster = effect["caster"]
        if caster is self.player:
            if effect["kind"] == "epic_fall":
                self.player["x"] = effect["x"]
                self.player["y"] = effect["y"]
                self.player["knockdown_until"] = now + 0.45
            for enemy in self.enemies[:]:
                distance = math.hypot(
                    enemy["x"] - effect["x"], enemy["y"] - effect["y"]
                )
                if distance <= effect["radius"] + enemy["radius"]:
                    enemy["hp"] -= effect["damage"]
                    enemy["hurt_until"] = now + 0.2
                    if enemy["hp"] <= 0:
                        self.defeat_enemy(enemy, now)
        elif math.hypot(
                self.player["x"] - effect["x"],
                self.player["y"] - effect["y"]) <= (
                    effect["radius"] + self.player_radius()
                ):
            if now >= self.player["shield_until"]:
                self.player["hp"] = max(
                    0, self.player["hp"] - effect["damage"]
                )
            self.player["hurt_until"] = now + 0.8
            if self.player["hp"] <= 0:
                self.state = "gameover"
                self.keys.clear()

    def boss_ability_cooldown(self):
        return 7 * 0.7 if self.boss_weapon_owned else 7

    def claim_region(self, region_index):
        region_index = max(0, min(len(REGIONS) - 1, region_index))
        post_boss = (
            self.pending_skill is not None
            or self.state in ("post_boss", "floor_progression")
            or self.map_return_state in ("post_boss", "floor_progression")
        )
        self.region = region_index
        self.territories[region_index] = True
        self.player["x"] = WIDTH / 2
        self.player["y"] = (ARENA[1] + ARENA[3]) / 2
        self.projectiles.clear()
        self.canvas.delete("background")
        self.draw_background()
        if post_boss:
            self.pending_skill = None
            self.boss_corpses.clear()
            self.boss_chests.clear()
            self.open_floor_progression("post_boss")
            self.message = f"TERRITORY CLAIMED  -  {REGIONS[self.region][0]}"
            self.message_until = time.monotonic() + 2
        else:
            self.state = "playing"
            self.last_tick = time.monotonic()
            self.message = f"TRAVELED TO  -  {REGIONS[self.region][0]}"
            self.message_until = time.monotonic() + 2.5

    def update_tower_gate(self, dt):
        dx = (("d" in self.keys or "right" in self.keys) -
              ("a" in self.keys or "left" in self.keys))
        dy = (("s" in self.keys or "down" in self.keys) -
              ("w" in self.keys or "up" in self.keys))
        if not (dx or dy):
            return
        length = math.hypot(dx, dy)
        self.player["x"] += dx / length * 185 * dt
        self.player["y"] += dy / length * 185 * dt
        self.player["x"] = max(ARENA[0] + 20, min(ARENA[2] - 20, self.player["x"]))
        self.player["y"] = max(ARENA[1] + 20, min(ARENA[3] - 20, self.player["y"]))

    def check_level_up(self):
        if self.superhuman_active:
            return
        p = self.player
        leveled_up = False
        while p["xp"] >= p["next_xp"]:
            leveled_up = True
            p["xp"] -= p["next_xp"]
            p["level"] += 1
            p["next_xp"] = int(p["next_xp"] * 1.45)
            p["max_hp"] += 16
            p["hp"] = min(p["max_hp"], p["hp"] + 42)
            p["speed"] += 3
            self.message = "LEVEL UP!  LEVEL " + str(p["level"])
            self.message_until = time.monotonic() + 2
        if leveled_up:
            self.save_game()

    def rect(self, x1, y1, x2, y2, color, outline="", tag="frame"):
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=color, outline=outline, width=1, tags=tag
        )

    def draw_background(self):
        c = self.canvas
        _, ground, border, grid = REGIONS[self.region]
        accent = REGION_ACCENTS[self.region]
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#151a20",
                           outline="", tags="background")
        c.create_rectangle(
            ARENA[0] - 7, ARENA[1] - 7, ARENA[2] + 7, ARENA[3] + 7,
            fill="#20282a", outline=border, width=3, tags="background"
        )
        self.rect(*ARENA, ground, border, tag="background")
        c.create_rectangle(
            ARENA[0] + 5, ARENA[1] + 5, ARENA[2] - 5, ARENA[3] - 5,
            outline=grid, width=1, tag="background"
        )
        for x in range(ARENA[0] + 12, ARENA[2], 48):
            c.create_line(x, ARENA[1], x, ARENA[3], fill=grid, width=1,
                          tags="background")
        for y in range(ARENA[1] + 12, ARENA[3], 48):
            c.create_line(ARENA[0], y, ARENA[2], y, fill=grid, width=1,
                          tags="background")
        terrain_rng = random.Random(401 + self.region * 37)
        for _ in range(13):
            x = terrain_rng.randint(ARENA[0] + 35, ARENA[2] - 35)
            y = terrain_rng.randint(ARENA[1] + 32, ARENA[3] - 32)
            size = terrain_rng.randint(9, 22)
            if self.region == 1:
                c.create_polygon(
                    x, y - size, x + size * 0.45, y - size * 0.15,
                    x + size * 0.2, y + size, x - size * 0.35, y + size * 0.25,
                    fill="#6b9aa5", outline="#9bcbd2", width=1,
                    tags="background"
                )
                c.create_line(x, y - size * 0.6, x - size * 0.1, y + size * 0.3,
                              fill="#c6eef0", width=1, tags="background")
            elif self.region == 2:
                c.create_oval(
                    x - size, y - size * 0.48, x + size, y + size * 0.48,
                    fill="#76513e", outline="#b57a4d", width=1,
                    tags="background"
                )
                c.create_line(x - size * 0.55, y, x + size * 0.3, y - size * 0.12,
                              fill="#d08a50", width=1, tags="background")
            elif self.region == 3:
                c.create_line(x, y + size, x, y - size,
                              fill="#40583a", width=max(3, size // 3),
                              tags="background")
                c.create_oval(x - size, y - size * 0.9,
                              x + size, y + size * 0.15,
                              fill="#5f844e", outline="#87a961",
                              width=1, tags="background")
                c.create_oval(x - size * 0.55, y - size * 0.62,
                              x + size * 0.25, y - size * 0.05,
                              fill="#83a85e", outline="", tags="background")
            else:
                c.create_line(
                    x - size, y + size * 0.45,
                    x - size * 0.15, y - size * 0.35,
                    x + size * 0.35, y - size * 0.55,
                    fill="#6d6251", width=2, tags="background"
                )
                c.create_line(x - size * 0.12, y - size * 0.26,
                              x + size * 0.75, y + size * 0.28,
                              fill=accent, width=1, tags="background")
        for x, y, kind, size in self.decor:
            if kind == "crater":
                c.create_oval(x - size, y - size * 0.45, x + size, y + size * 0.45,
                              fill="#303a32", outline=grid, tags="background")
            elif kind == "stone":
                c.create_oval(x - size / 2, y - size / 3, x + size / 2, y + size / 3,
                              fill=border, outline=ground, tags="background")
            else:
                c.create_line(x, y, x + size, y - size // 2, fill=accent, width=2,
                              tags="background")
        self.draw_barricade(ARENA[0] + 105, ARENA[1] + 55, accent, "background")
        self.draw_barricade(ARENA[2] - 170, ARENA[3] - 68, border, "background")
        for x, y in (
            (ARENA[0] + 22, ARENA[1] + 22),
            (ARENA[2] - 22, ARENA[1] + 22),
            (ARENA[0] + 22, ARENA[3] - 22),
            (ARENA[2] - 22, ARENA[3] - 22),
        ):
            c.create_oval(x - 7, y - 7, x + 7, y + 7,
                          fill=accent, outline="#fff1d2", width=1,
                          tags="background")
            c.create_oval(x - 3, y - 3, x + 3, y + 3,
                          fill="#fff1d2", outline="", tags="background")
        self.canvas.create_line(ARENA[0] + 36, ARENA[1] + 28,
                                ARENA[0] + 36, ARENA[1] + 66, fill="#c6c1a6", width=2,
                                tags="background")
        self.canvas.create_polygon(
            ARENA[0] + 38, ARENA[1] + 29, ARENA[0] + 64, ARENA[1] + 36,
            ARENA[0] + 38, ARENA[1] + 44, fill=accent, outline="", tags="background"
        )
        self.canvas.create_line(ARENA[2] - 38, ARENA[3] - 68,
                                ARENA[2] - 38, ARENA[3] - 30, fill="#c6c1a6", width=2,
                                tags="background")
        self.canvas.create_polygon(
            ARENA[2] - 36, ARENA[3] - 67, ARENA[2] - 62, ARENA[3] - 60,
            ARENA[2] - 36, ARENA[3] - 52, fill=accent, outline="", tags="background"
        )

    def draw_barricade(self, x, y, color, tag="frame"):
        c = self.canvas
        c.create_oval(x - 3, y + 4, x + 80, y + 24, fill="#293129",
                      outline="", tags=tag)
        for row in range(2):
            for i in range(4):
                bx = x + i * 18 - row * 8
                by = y + row * 8
                c.create_oval(bx, by, bx + 18, by + 13, fill=color,
                              outline="#33372f", width=1, tags=tag)
                c.create_arc(bx + 3, by + 2, bx + 13, by + 9, start=25,
                             extent=115, style=tk.ARC, outline="#a9a58b",
                             width=1, tags=tag)

    def draw_bar(self, x, y, width, ratio, color, height=6):
        self.rect(x, y, x + width, y + height, "#252a29")
        if ratio > 0:
            self.rect(x, y, x + width * max(0, min(1, ratio)), y + height, color)

    def draw_entity(self, x, y, radius, body, outline, direction=(1, 0),
                    kind="raider", cosmetic_override=None, moving=False):
        c = self.canvas
        appearance = cosmetic_override or self.equipped_cosmetics
        phase = time.monotonic() * 10
        stride = math.sin(phase) if moving else 0
        bob = (abs(math.sin(phase)) * radius * 0.045 if moving else
               math.sin(phase * 0.2) * radius * 0.012)
        fx, fy = direction
        length = max(1, math.hypot(fx, fy))
        fx, fy = fx / length, fy / length
        sx, sy = -fy, fx

        def point(forward, sideways):
            return (x + fx * radius * forward + sx * radius * sideways,
                    y + fy * radius * forward + sy * radius * sideways + bob)

        body_color = body
        if kind == "scout":
            body_color = next(
                item[2] for item in COSMETIC_ITEMS["OUTFIT"]
                if item[0] == appearance["OUTFIT"]
            )

        c.create_oval(x - radius * 0.82, y - radius * 0.48,
                      x + radius * 0.82, y + radius * 0.78,
                      fill="#252b27", outline="", tags="frame")

        hip = point(-0.2, 0)
        for side in (-0.23, 0.23):
            swing = stride * (1 if side < 0 else -1) * 0.23
            knee = point(-0.4 + swing, side)
            boot = point(-0.62 + swing * 1.6, side * 1.2)
            c.create_line(*hip, *knee, fill="#303530",
                          width=max(3, int(radius * 0.3)), tags="frame")
            c.create_line(*knee, *boot, fill="#282d29",
                          width=max(3, int(radius * 0.25)), tags="frame")

        for side in (-0.45, 0.45):
            shoulder = point(0.28, side)
            arm_swing = stride * (1 if side < 0 else -1) * 0.18
            elbow = point(0.02 + arm_swing, side * 1.1)
            hand = point(-0.2 + arm_swing * 1.5, side * 1.22)
            c.create_line(*shoulder, *elbow, *hand, fill=body_color,
                          width=max(3, int(radius * 0.18)), tags="frame")
            c.create_oval(hand[0] - radius * 0.1, hand[1] - radius * 0.1,
                          hand[0] + radius * 0.1, hand[1] + radius * 0.1,
                          fill="#c69a77", outline=outline, width=1, tags="frame")

        left_shoulder = point(0.35, 0.42)
        right_shoulder = point(0.35, -0.42)
        left_hip = point(-0.42, 0.3)
        right_hip = point(-0.42, -0.3)
        c.create_polygon(*left_shoulder, *right_shoulder, *right_hip, *left_hip,
                         fill=body_color, outline=outline, width=2, tags="frame")
        c.create_polygon(*point(0.23, 0.22), *point(0.23, -0.22),
                         *point(-0.32, -0.18), *point(-0.32, 0.18),
                         fill="#46514a", outline="#303b36", width=1, tags="frame")
        c.create_line(*point(0.12, 0), *point(-0.22, 0),
                      fill="#a5a58b", width=max(1, int(radius * 0.1)), tags="frame")

        for side in (-0.45, 0.45):
            shoulder = point(0.28, side)
            c.create_oval(shoulder[0] - radius * 0.19, shoulder[1] - radius * 0.19,
                          shoulder[0] + radius * 0.19, shoulder[1] + radius * 0.19,
                          fill=body_color, outline=outline, width=1, tags="frame")

        if kind in ("brute", "boss", "minion_boss", "kidnapper"):
            pack = point(-0.42, 0)
            c.create_oval(pack[0] - radius * 0.42, pack[1] - radius * 0.37,
                          pack[0] + radius * 0.42, pack[1] + radius * 0.37,
                          fill="#473a43" if kind == "brute" else
                          "#432f40" if kind == "boss" else "#302439",
                          outline="#302e32", width=2, tags="frame")

        head = point(0.55, 0)
        head_radius = radius * 0.29
        c.create_oval(head[0] - head_radius, head[1] - head_radius,
                      head[0] + head_radius, head[1] + head_radius,
                      fill="#c69a77", outline="#39332c", width=1, tags="frame")
        if kind == "scout":
            hair = appearance["HAIR"]
            hair_color = next(
                item[2] for item in COSMETIC_ITEMS["HAIR"] if item[0] == hair
            )
            c.create_oval(
                head[0] - head_radius * 0.95,
                head[1] - head_radius * 0.95,
                head[0] + head_radius * 0.95,
                head[1] - head_radius * 0.12,
                fill=hair_color, outline="#39332c", width=1, tags="frame"
            )
            if hair == "Wild Tuft":
                c.create_polygon(
                    head[0] - head_radius * 0.8, head[1] - head_radius * 0.5,
                    head[0] - head_radius * 0.5, head[1] - head_radius * 1.5,
                    head[0] - head_radius * 0.05, head[1] - head_radius * 0.75,
                    head[0] + head_radius * 0.45, head[1] - head_radius * 1.35,
                    head[0] + head_radius * 0.85, head[1] - head_radius * 0.2,
                    fill=hair_color, outline="#39332c", width=1, tags="frame"
                )
            mask = appearance["MASK"]
            mask_color = next(
                item[2] for item in COSMETIC_ITEMS["MASK"] if item[0] == mask
            )
            if mask_color:
                c.create_rectangle(
                    head[0] - head_radius * 0.78,
                    head[1] + head_radius * 0.05,
                    head[0] + head_radius * 0.78,
                    head[1] + head_radius * 0.55,
                    fill=mask_color, outline="#39332c", width=1, tags="frame"
                )
            else:
                for side in (-0.14, 0.14):
                    eye = point(0.69, side)
                    c.create_oval(
                        eye[0] - radius * 0.045, eye[1] - radius * 0.065,
                        eye[0] + radius * 0.045, eye[1] + radius * 0.065,
                        fill="#f3ead4", outline="", tags="frame"
                    )
                    pupil = point(0.72, side)
                    c.create_oval(
                        pupil[0] - radius * 0.02, pupil[1] - radius * 0.035,
                        pupil[0] + radius * 0.02, pupil[1] + radius * 0.035,
                        fill="#252b27", outline="", tags="frame"
                    )
        else:
            helmet = point(0.66, 0)
            helmet_radius = radius * (
                0.42 if kind in ("boss", "minion_boss", "kidnapper") else 0.3
            )
            c.create_oval(helmet[0] - helmet_radius, helmet[1] - helmet_radius,
                          helmet[0] + helmet_radius, helmet[1] + helmet_radius,
                          fill="#a04e53" if kind in
                          ("boss", "minion_boss", "kidnapper") else "#6c6d57",
                          outline="#353b32", width=1, tags="frame")
            c.create_arc(helmet[0] - helmet_radius + 1, helmet[1] - helmet_radius + 1,
                         helmet[0] + helmet_radius - 1, helmet[1] + helmet_radius - 1,
                         start=35, extent=115, style=tk.ARC, outline="#b4b28e",
                         width=1, tags="frame")

        weapon_start = point(0.12, -0.33)
        weapon_name = appearance["GUN"] if kind == "scout" else ""
        weapon_length = 1.18 if weapon_name == "Longshot" else 0.94
        weapon_width = 1.5 if weapon_name == "Scattergun" else 1
        weapon_color = next(
            (item[2] for item in COSMETIC_ITEMS["GUN"] if item[0] == weapon_name),
            "#858678",
        )
        weapon_end = point(weapon_length, -0.33)
        c.create_line(*point(-0.05, -0.33), *weapon_start,
                      fill="#292c29", width=max(3, int(radius * 0.22 * weapon_width)),
                      tags="frame")
        c.create_line(*weapon_start, *weapon_end, fill="#262b2a",
                      width=max(3, int(radius * 0.2 * weapon_width)), tags="frame")
        c.create_line(*point(0.45, -0.33), *weapon_end,
                      fill=weapon_color, width=max(1, int(radius * 0.07)),
                      tags="frame")
        if kind == "scout":
            glove_color = next(
                item[2] for item in COSMETIC_ITEMS["GLOVES"]
                if item[0] == appearance["GLOVES"]
            )
            for side in (-0.57, 0.57):
                hand = point(0.15, side)
                c.create_oval(
                    hand[0] - radius * 0.12, hand[1] - radius * 0.12,
                    hand[0] + radius * 0.12, hand[1] + radius * 0.12,
                    fill=glove_color, outline="#292c29", width=1, tags="frame"
                )

    def draw_floor_progression(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 34, text="THE 200-FLOOR SPIRAL",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 70,
                      text=f"CURRENT FLOOR {self.stage_number()} / {MAX_FLOORS}",
                      fill="#e5c874", font=("Segoe UI", 12, "bold"), tags="frame")
        c.create_rectangle(292, 88, 432, 122, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(362, 105, text="◀  PREVIOUS", fill="#fff1d2",
                      font=("Segoe UI", 9, "bold"), tags="frame")
        c.create_rectangle(528, 88, 668, 122, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(598, 105, text="NEXT  ▶", fill="#fff1d2",
                      font=("Segoe UI", 9, "bold"), tags="frame")
        center_x, center_y = 600, 355
        for floor in range(1, MAX_FLOORS + 1):
            progress = floor / MAX_FLOORS
            angle = floor * 0.21
            radius = 8 + progress * 152
            x = center_x + math.cos(angle) * radius * 1.15
            y = center_y + math.sin(angle) * radius * 0.92
            record = self.floor_record(floor)
            color = "#e5c874" if record else (
                "#8ca094" if floor == self.stage_number() else "#38403c"
            )
            dot = 3 if floor % 10 == 0 else 1.5
            c.create_oval(x - dot, y - dot, x + dot, y + dot,
                          fill=color, outline="", tags="frame")
        page_first = self.progression_page * 12 + 1
        for index in range(12):
            floor = page_first + index
            col, row = index % 4, index // 4
            x1, y1 = 36 + col * 153, 170 + row * 96
            record = self.floor_record(floor)
            available = floor <= self.stage_number()
            selected = floor == self.progression_selected_floor
            fill = "#74563d" if selected else (
                "#35443d" if available else "#202624"
            )
            c.create_rectangle(x1, y1, x1 + 137, y1 + 72, fill=fill,
                               outline="#e5c874" if selected else "#849087",
                               width=2 if selected else 1, tags="frame")
            label = f"FLOOR {floor}"
            if record:
                label += "  " + ("★" * record.get("stars", 1))
            elif floor == self.stage_number():
                label += "  CURRENT"
            c.create_text(x1 + 68, y1 + 25, text=label,
                          fill="#fff1d2" if available else "#7a817b",
                          font=("Segoe UI", 9, "bold"), tags="frame")
            if self.market_stand_unlocked(floor):
                c.create_text(x1 + 68, y1 + 62, text="MARKET STAND",
                              fill="#8ee5f0", font=("Segoe UI", 7, "bold"),
                              tags="frame")
            if record:
                c.create_text(x1 + 68, y1 + 49,
                              text=record.get("quest_title", "CLEARED"),
                              fill="#c2c7b9", font=("Segoe UI", 7, "bold"),
                              tags="frame")
        selected = self.progression_selected_floor
        record = self.floor_record(selected)
        c.create_text(820, 180, text=f"FLOOR {selected}",
                      fill="#e5c874", font=("Segoe UI", 17, "bold"), tags="frame")
        if record:
            c.create_text(820, 224, text=f"{record.get('stars', 0)} STARS",
                          fill="#ffe58c", font=("Segoe UI", 13, "bold"), tags="frame")
            c.create_text(820, 267,
                          text=f"QUEST: {record.get('quest_title', 'Unknown')}",
                          width=230, fill="#f0d7c5",
                          font=("Segoe UI", 9, "bold"), tags="frame")
            c.create_text(820, 314,
                          text=(f"QUEST {'COMPLETE' if record.get('quest_complete') else 'INCOMPLETE'}"
                      f"  {record.get('quest_progress', 0)}/"
                      f"{record.get('quest_target', 0)}"),
                          fill="#c2c7b9", font=("Segoe UI", 9), tags="frame")
            c.create_text(820, 350,
                          text=f"KILLS {record.get('kills', 0)}  |  REWARD {record.get('quest_reward', 0):,}",
                          fill="#c2c7b9", font=("Segoe UI", 9), tags="frame")
        else:
            c.create_text(820, 245, text="NOT CLEARED YET",
                          fill="#929c93", font=("Segoe UI", 10, "bold"), tags="frame")
        c.create_rectangle(40, 555, 260, 598, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(150, 576, text="BACK", fill="#fff1d2",
                      font=("Segoe UI", 10, "bold"), tags="frame")
        unlocked = self.market_stand_unlocked(selected)
        c.create_rectangle(355, 555, 595, 598,
                           fill="#53634d" if unlocked else "#202624",
                           outline="#d4bd91", tags="frame")
        c.create_text(475, 576,
                      text="MARKETPLACE" if unlocked else "MARKET: REACH LV 15",
                      fill="#fff1d2" if unlocked else "#7a817b",
                      font=("Segoe UI", 8, "bold"), tags="frame")
        next_allowed = (
            self.progression_return_state == "post_boss"
            and selected == self.stage_number()
            and not self.replay_active
        )
        replay_finish_allowed = (
            self.replay_active
            and self.progression_return_state == "post_boss"
            and selected == self.stage_number()
            and self.encounter_clear
        )
        replay_allowed = record is not None and not self.replay_active
        action_enabled = next_allowed or replay_finish_allowed or replay_allowed
        c.create_rectangle(655, 555, 920, 598,
                           fill="#53634d" if action_enabled else "#202624",
                           outline="#d4bd91", tags="frame")
        action = (
            "NEXT FLOOR / BOSS" if next_allowed
            else (
                "RETURN AFTER REPLAY" if replay_finish_allowed
                else ("REPLAY IN PROGRESS" if self.replay_active
                      else ("PLAY THIS FLOOR AGAIN" if replay_allowed
                            else "SELECT A CLEARED FLOOR"))
            )
        )
        c.create_text(787, 576, text=action,
                      fill="#fff1d2" if action_enabled else "#7a817b",
                      font=("Segoe UI", 9, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 625,
                      text="REPLAY CLEARED FLOORS TO CHOOSE A QUEST AND FIGHT THROUGH THEM AGAIN",
                      fill="#aeb6aa", font=("Segoe UI", 9, "bold"), tags="frame")

    def draw_marketplace(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 38, text="SPECIAL WEAPON MARKET",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        c.create_text(52, 76, anchor="w",
                      text=f"COINS {self.coins:,}  |  GEMS {self.gems}",
                      fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame")
        c.create_text(52, 96, anchor="w",
                      text=f"SEARCH: {self.market_search or 'TYPE TO SEARCH'}",
                      fill="#c2c7b9", font=("Segoe UI", 8, "bold"), tags="frame")
        c.create_rectangle(410, 50, 570, 100, fill="#53634d",
                           outline="#d4bd91", tags="frame")
        c.create_text(490, 75, text="SIDE QUESTS",
                      fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                      tags="frame")
        c.create_rectangle(760, 50, 915, 100, fill="#53634d",
                           outline="#d4bd91", tags="frame")
        c.create_text(837, 75, text="SKILL FORGE",
                      fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                      tags="frame")
        c.create_rectangle(585, 50, 745, 100, fill="#53634d",
                           outline="#d4bd91", tags="frame")
        c.create_text(665, 75, text="SKILL MARKET",
                      fill="#fff1d2", font=("Segoe UI", 9, "bold"),
                      tags="frame")
        visible = self.visible_market_weapons()
        pages = max(1, (len(visible) + 9) // 10)
        self.market_page = min(self.market_page, pages - 1)
        for row, weapon in enumerate(visible[self.market_page * 10:self.market_page * 10 + 10]):
            y = 122 + row * 43
            owned = weapon["id"] in self.owned_special_weapons
            equipped = weapon["id"] == self.equipped_special_weapon
            status = (
                "EQUIPPED" if equipped
                else ("OWNED - EQUIP IN SPECIAL WEAPONS" if owned
                      else (f"BUY {weapon['price']:,} COINS / "
                            f"{self.gem_price(weapon['price'])} GEMS"))
            )
            c.create_rectangle(52, y, 908, y + 37, fill="#29332f",
                               outline="#69766b", tags="frame")
            c.create_text(72, y + 18, anchor="w",
                          text=f'{weapon["id"] + 1:04d}  {weapon["name"]}  [{weapon["type"]}]',
                          fill="#f0d7c5", font=("Segoe UI", 9, "bold"), tags="frame")
            c.create_text(885, y + 18, anchor="e", text=status,
                          fill="#e5c874", font=("Segoe UI", 9, "bold"), tags="frame")
            c.create_text(610, y + 18, anchor="e", text="CLICK TO VIEW / TEST",
                          fill="#8ee5f0", font=("Segoe UI", 8, "bold"), tags="frame")
        controls = ((40, "BACK"), (210, f"TYPE: {self.market_filter}"),
                    (390, "TYPE TO SEARCH"), (570, "NEXT PAGE ▶"),
                    (760, "◀ PREVIOUS"))
        for x, label in controls:
            c.create_rectangle(x, 570, x + 150, 606, fill="#35443d",
                               outline="#d4bd91", tags="frame")
            c.create_text(x + 75, 588, text=label, fill="#fff1d2",
                          font=("Segoe UI", 8, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 626,
                      text="LASER: PIERCING BEAM  |  ROCKET: AREA BLAST  |  ATOMIC: HALF-MAP BLAST  |  3 SHOTS PER FLOOR",
                      fill="#c2c7b9", font=("Segoe UI", 8, "bold"), tags="frame")

    def draw_skill_market(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 42, text="SKILL MARKET",
                      fill="#f0d7c5", font=("Segoe UI", 27, "bold"), tags="frame")
        c.create_text(
            WIDTH / 2, 82,
            text=f"COINS: {self.coins:,}  |  GEMS: {self.gems}  |  1 GEM = 1,000 COINS (ROUNDED UP)",
            fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        for index, skill in enumerate(ALL_BOSS_SKILLS):
            y = 125 + index * 58
            price = MARKET_WEAPONS[index]["price"]
            copies = sum(copy[0] == skill[0] for copy in self.skill_copies)
            c.create_rectangle(
                52, y, 908, y + 48,
                fill="#46523e" if skill in self.unlocked_abilities else "#29332f",
                outline="#e5c874" if skill in self.unlocked_abilities else "#69766b",
                width=2 if skill in self.unlocked_abilities else 1, tags="frame"
            )
            c.create_text(72, y + 15, anchor="w", text=skill[0],
                          fill="#f0d7c5", font=("Segoe UI", 10, "bold"),
                          tags="frame")
            c.create_text(72, y + 34, anchor="w", text=skill[2],
                          fill="#c2c7b9", font=("Segoe UI", 8), tags="frame")
            c.create_text(
                885, y + 24, anchor="e",
                text=(f"BUY COPY  {price:,} COINS / "
                      f"{self.gem_price(price)} GEMS  |  COPIES: {copies}"),
                fill="#e5c874", font=("Segoe UI", 9, "bold"), tags="frame"
            )
        c.create_rectangle(50, 555, 250, 600, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(150, 577, text="BACK TO WEAPON MARKET",
                      fill="#fff1d2", font=("Segoe UI", 9, "bold"), tags="frame")
        if time.monotonic() < self.message_until:
            c.create_text(WIDTH / 2, 535, text=self.message,
                          fill="#e5c874", font=("Segoe UI", 10, "bold"),
                          tags="frame")

    def draw_side_quests(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 38, text="SIDE QUESTS",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 76,
                      text=f"GEMS: {self.gems}  |  NO TIME LIMIT  |  REWARDS ARE PAID AUTOMATICALLY",
                      fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame")
        for index, (quest_id, title, counter, target, reward) in enumerate(SIDE_QUESTS):
            y = 105 + index * 49
            progress = min(target, self.side_quest_stats[counter])
            completed = quest_id in self.side_quests_claimed
            c.create_rectangle(
                70, y, 890, y + 42,
                fill="#35443d" if completed else "#29332f",
                outline="#a5d46d" if completed else "#69766b",
                width=2 if completed else 1, tags="frame"
            )
            c.create_text(92, y + 21, anchor="w", text=title,
                          fill="#f0d7c5", font=("Segoe UI", 10, "bold"),
                          tags="frame")
            c.create_text(
                650, y + 21, anchor="e",
                text=("COMPLETE" if completed else f"{progress}/{target}"),
                fill="#a5d46d" if completed else "#c2c7b9",
                font=("Segoe UI", 9, "bold"), tags="frame"
            )
            c.create_text(860, y + 21, anchor="e", text=f"+{reward} GEMS",
                          fill="#e5c874", font=("Segoe UI", 9, "bold"),
                          tags="frame")
        c.create_rectangle(50, 555, 250, 600, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(150, 577, text="BACK",
                      fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                      tags="frame")

    def draw_weapon_preview(self):
        if self.preview_weapon_id is None:
            self.state = "marketplace"
            return
        c = self.canvas
        weapon = MARKET_WEAPONS[self.preview_weapon_id]
        now = time.monotonic()
        elapsed = now - self.weapon_test_started_at if self.weapon_test_started_at else -1
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 48, text="SPECIAL WEAPON PREVIEW",
                      fill="#f0d7c5", font=("Segoe UI", 24, "bold"), tags="frame")
        c.create_text(
            WIDTH / 2, 92,
            text=(f'{weapon["name"]}  |  {weapon["type"]}  |  '
                  f'{weapon["price"]:,} COINS OR '
                  f'{self.gem_price(weapon["price"])} GEMS'),
            fill="#e5c874", font=("Segoe UI", 12, "bold"), tags="frame"
        )
        c.create_rectangle(100, 130, 860, 445, fill="#18201f",
                           outline="#69766b", width=2, tags="frame")
        c.create_text(480, 152, text="TEST RANGE",
                      fill="#c2c7b9", font=("Segoe UI", 10, "bold"), tags="frame")
        c.create_oval(704, 270, 770, 336, fill="#473a43",
                      outline="#d4bd91", width=3, tags="frame")
        c.create_rectangle(724, 287, 750, 317, fill="#875b72",
                           outline="#302e32", tags="frame")
        c.create_text(737, 350, text="TARGET", fill="#c2c7b9",
                      font=("Segoe UI", 8, "bold"), tags="frame")
        c.create_oval(245, 270, 285, 310, fill="#72a2ad",
                      outline="#d5d9c0", width=2, tags="frame")
        c.create_line(282, 291, 342, 291, fill="#d2a64e", width=6, tags="frame")

        if 0 <= elapsed <= 1.8:
            progress = min(1, elapsed / 1.25)
            if weapon["type"] == "LASER":
                c.create_line(344, 291, 737, 303, fill="#7cf9ff",
                              width=15, tags="frame")
                c.create_line(344, 291, 737, 303, fill="#ffffff",
                              width=4, tags="frame")
                c.create_oval(717, 283, 757, 323, outline="#8ee5f0",
                              width=4, tags="frame")
            elif weapon["type"] == "ROCKET":
                rocket_x = 344 + (737 - 344) * progress
                c.create_line(344, 291, rocket_x - 8, 291, fill="#ff824a",
                              width=4, tags="frame")
                c.create_oval(rocket_x - 10, 281, rocket_x + 10, 301,
                              fill="#d5d6c6", outline="#ffb64d",
                              width=3, tags="frame")
                if elapsed >= 1.25:
                    c.create_oval(690, 256, 784, 350, outline="#ffb64d",
                                  width=7, tags="frame")
                    c.create_text(737, 238, text="AREA BLAST",
                                  fill="#ffb64d", font=("Segoe UI", 9, "bold"),
                                  tags="frame")
            else:
                bomb_y = 170 + 130 * progress
                c.create_line(737, 169, 737, bomb_y, fill="#d2a64e",
                              dash=(3, 5), width=3, tags="frame")
                c.create_oval(725, bomb_y - 12, 749, bomb_y + 12,
                              fill="#282d29", outline="#ffb64d",
                              width=3, tags="frame")
                if elapsed >= 1.25:
                    c.create_oval(480, 165, 860, 445, fill="#bd6555",
                                  stipple="gray50", outline="#ffb64d",
                                  width=5, tags="frame")
                    c.create_text(670, 210, text="LARGE ATOMIC BLAST",
                                  fill="#fff1d2", font=("Segoe UI", 11, "bold"),
                                  tags="frame")
        if elapsed < 0:
            instruction = "Press TEST FIRE to see this weapon's attack."
        else:
            instruction = (
                "LASER: piercing beam" if weapon["type"] == "LASER" else
                ("ROCKET: projectile and area blast" if weapon["type"] == "ROCKET"
                 else "ATOMIC: half-map blast")
            )
        c.create_text(
            WIDTH / 2, 475,
            text=f"{instruction}  |  TEST ONLY: uses no ammo, coins, or combat damage.",
            fill="#c2c7b9", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        c.create_rectangle(45, 535, 245, 590, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(145, 562, text="BACK TO MARKET",
                      fill="#fff1d2", font=("Segoe UI", 9, "bold"), tags="frame")
        c.create_rectangle(270, 535, 505, 590, fill="#53634d",
                           outline="#d4bd91", tags="frame")
        c.create_text(387, 562, text="TEST FIRE",
                      fill="#fff1d2", font=("Segoe UI", 11, "bold"), tags="frame")
        owned = self.preview_weapon_id in self.owned_special_weapons
        c.create_rectangle(530, 535, 915, 590,
                           fill="#35443d" if not owned else "#202624",
                           outline="#d4bd91", tags="frame")
        c.create_text(
            722, 562,
            text=("OWNED - EQUIP IN SPECIAL WEAPONS" if owned
                  else f"BUY FOR {weapon['price']:,} COINS"),
            fill="#e5c874" if not owned else "#929c93",
            font=("Segoe UI", 9, "bold"), tags="frame"
        )
        if now < self.message_until:
            c.create_text(WIDTH / 2, 510, text=self.message,
                          fill="#e5c874", font=("Segoe UI", 10, "bold"),
                          tags="frame")

    def draw_purchase_confirmation(self):
        details = self.pending_purchase_details()
        if details is None:
            self.cancel_market_purchase()
            return
        name, price = details
        gem_cost = self.gem_price(price)
        can_afford_coins = self.coins >= price
        can_afford_gems = self.gems >= gem_cost
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_rectangle(170, 130, 790, 515, fill="#202a27",
                           outline="#d4bd91", width=2, tags="frame")
        c.create_text(WIDTH / 2, 175, text="CONFIRM PURCHASE",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 225, text=name,
                      fill="#e5c874", font=("Segoe UI", 17, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 275,
                      text=f"PRICE: {price:,} COINS  OR  {gem_cost} GEMS",
                      fill="#d0d4c2", font=("Segoe UI", 13, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 312,
                      text=f"CURRENT: {self.coins:,} COINS  |  {self.gems} GEMS",
                      fill="#8ee5f0", font=("Segoe UI", 13, "bold"), tags="frame")
        c.create_text(
            WIDTH / 2, 344,
            text=f"AFTER COINS: {self.coins - price:,}  |  AFTER GEMS: {self.gems - gem_cost}",
            fill="#a5d46d" if can_afford_coins or can_afford_gems else "#e28b73",
            font=("Segoe UI", 12, "bold"), tags="frame"
        )
        if not can_afford_coins and not can_afford_gems:
            c.create_text(WIDTH / 2, 375, text="NOT ENOUGH COINS OR GEMS",
                          fill="#e28b73", font=("Segoe UI", 10, "bold"),
                          tags="frame")
        c.create_rectangle(
            120, 410, 365, 480,
            fill="#53634d" if can_afford_coins else "#303735",
            outline="#d4bd91", tags="frame"
        )
        c.create_text(242, 445,
                      text="BUY WITH COINS" if can_afford_coins else "NOT ENOUGH COINS",
                      fill="#fff1d2" if can_afford_coins else "#929c93",
                      font=("Segoe UI", 9, "bold"), tags="frame")
        c.create_rectangle(
            380, 410, 600, 480,
            fill="#53634d" if can_afford_gems else "#303735",
            outline="#d4bd91", tags="frame"
        )
        c.create_text(490, 445,
                      text=f"BUY WITH {gem_cost} GEMS" if can_afford_gems else "NOT ENOUGH GEMS",
                      fill="#fff1d2" if can_afford_gems else "#929c93",
                      font=("Segoe UI", 9, "bold"), tags="frame")
        c.create_rectangle(615, 410, 840, 480, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(727, 445, text="CANCEL",
                      fill="#fff1d2", font=("Segoe UI", 11, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 490, text="Press ESC to cancel",
                      fill="#aeb6aa", font=("Segoe UI", 9), tags="frame")

    def draw_skill_forge(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 35, text="BOSS SKILL FORGE",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        c.create_text(
            WIDTH / 2, 68,
            text="Choose two skill copies. Both are consumed; damage and range are added.",
            fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        selected = self.forge_selected_skills
        for index, (x1, x2) in enumerate(((50, 450), (510, 910))):
            name = selected[index] if index < len(selected) else "CLICK TO CLEAR / SELECT AN INGREDIENT"
            c.create_rectangle(x1, 90, x2, 118, fill="#35443d",
                               outline="#d4bd91", tags="frame")
            c.create_text((x1 + x2) / 2, 104, text=name,
                          fill="#fff1d2", font=("Segoe UI", 9, "bold"),
                          tags="frame")
        visible = self.visible_skill_copies()
        pages = max(1, (len(visible) + 7) // 8)
        self.forge_page = min(self.forge_page, pages - 1)
        page_skills = visible[self.forge_page * 8:self.forge_page * 8 + 8]
        for row, (skill, count) in enumerate(page_skills):
            y = 130 + row * 44
            selected_count = selected.count(skill[0])
            c.create_rectangle(52, y, 908, y + 38, fill="#29332f",
                               outline="#e5c874" if selected_count else "#69766b",
                               width=2 if selected_count else 1, tags="frame")
            damage, skill_range = self.skill_damage_range(skill)
            c.create_text(
                72, y + 19, anchor="w",
                text=f"{skill[0]}  x{count}  |  {damage} DAMAGE  /  {skill_range} RANGE",
                fill="#f0d7c5", font=("Segoe UI", 9, "bold"), tags="frame"
            )
            c.create_text(
                885, y + 19, anchor="e",
                text=f"SELECTED {selected_count}" if selected_count else "CLICK TO SELECT",
                fill="#e5c874", font=("Segoe UI", 8, "bold"), tags="frame"
            )
        controls = (
            (40, 220, "BACK TO MARKET"),
            (245, 375, "◀ PREVIOUS"),
            (385, 575, "FORGE SKILL"),
            (600, 730, "NEXT ▶"),
            (750, 920, "CLEAR CHOICES"),
        )
        for x1, x2, label in controls:
            c.create_rectangle(x1, 550, x2, 598, fill="#35443d",
                               outline="#d4bd91", tags="frame")
            c.create_text((x1 + x2) / 2, 574, text=label,
                          fill="#fff1d2", font=("Segoe UI", 8, "bold"),
                          tags="frame")
        c.create_text(
            WIDTH / 2, 625,
            text=f"COPIES HELD: {len(self.skill_copies)}  |  PAGE {self.forge_page + 1}/{pages}  |  NO COIN COST",
            fill="#c2c7b9", font=("Segoe UI", 9, "bold"), tags="frame"
        )
        self.draw_forge_animation()

    def draw_forge_animation(self):
        if not self.forge_animation_started_at:
            return
        elapsed = time.monotonic() - self.forge_animation_started_at
        if elapsed >= 2.8:
            self.forge_animation_started_at = 0
            self.forge_animation_name = ""
            return
        progress = max(0, min(1, elapsed / 2.4))
        radius = 42 + progress * 185
        c = self.canvas
        center_x, center_y = WIDTH / 2, HEIGHT / 2
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#07090d",
                           stipple="gray50", outline="", tags="frame")
        c.create_oval(center_x - radius, center_y - radius,
                      center_x + radius, center_y + radius,
                      fill="#10232a", stipple="gray50",
                      outline="#80eaff", width=4, tags="frame")
        for index, (start, extent) in enumerate(((15, 88), (125, 102), (263, 79))):
            inset = index * 13
            c.create_arc(
                center_x - radius + inset, center_y - radius + inset,
                center_x + radius - inset, center_y + radius - inset,
                start=start + elapsed * 35, extent=extent,
                style=tk.ARC, outline=("#d7fbff", "#83eaff", "#e5c874")[index],
                width=4 - index, tags="frame"
            )
        for angle in (18, 83, 151, 218, 297, 340):
            radians = math.radians(angle + elapsed * 7)
            inner = radius * 0.62
            outer = radius + 16
            c.create_line(
                center_x + math.cos(radians) * inner,
                center_y + math.sin(radians) * inner,
                center_x + math.cos(radians) * outer,
                center_y + math.sin(radians) * outer,
                fill="#d9faff", width=2, tags="frame"
            )
        c.create_oval(center_x - 32, center_y - 32,
                      center_x + 32, center_y + 32,
                      fill="#d9faff", outline="#fff7d1", width=3,
                      tags="frame")
        c.create_text(center_x, center_y + radius + 38,
                      text=f"{self.forge_animation_name.upper()} FORGED",
                      fill="#fff1d2", font=("Segoe UI", 20, "bold"),
                      tags="frame")

    def draw_boss_corpse(self, corpse):
        x, y = corpse["x"], corpse["y"]
        c = self.canvas
        c.create_oval(x - 48, y + 9, x + 44, y + 26,
                      fill="#252b27", outline="", tags="frame")
        c.create_polygon(x - 34, y - 5, x + 18, y - 10,
                         x + 30, y + 10, x - 24, y + 15,
                         fill="#573943", outline="#302e32", width=2,
                         tags="frame")
        c.create_line(x - 20, y + 8, x - 44, y + 20,
                      fill="#42373a", width=8, tags="frame")
        c.create_line(x - 15, y + 9, x - 35, y + 25,
                      fill="#42373a", width=7, tags="frame")
        c.create_oval(x + 16, y - 15, x + 40, y + 9,
                      fill="#c69a77", outline="#302e32", width=2,
                      tags="frame")
        c.create_oval(x + 20, y - 20, x + 45, y + 3,
                      fill="#70434a", outline="#302e32", width=2,
                      tags="frame")
        c.create_line(x - 5, y - 7, x + 34, y + 18,
                      fill="#262b2a", width=5, tags="frame")
        c.create_line(x + 23, y + 11, x + 49, y + 27,
                      fill="#858678", width=2, tags="frame")

    def draw_boss_chest(self, chest):
        x, y = chest["x"], chest["y"]
        c = self.canvas
        if chest["opened"]:
            c.create_rectangle(x - 19, y - 8, x + 19, y + 7,
                               fill="#514832", outline="#c8a957",
                               width=2, tags="frame")
            c.create_line(x - 18, y - 8, x - 14, y - 20,
                          x + 14, y - 20, x + 18, y - 8,
                          fill="#c8a957", width=3, tags="frame")
            c.create_text(x, y + 23, text=chest.get("reward", "REWARD CLAIMED"),
                          width=150, fill="#f0d99f",
                          font=("Segoe UI", 7, "bold"), tags="frame")
            return
        c.create_rectangle(x - 20, y - 10, x + 20, y + 10,
                           fill="#704c32", outline="#f0c45a",
                           width=2, tags="frame")
        c.create_rectangle(x - 20, y - 4, x + 20, y + 1,
                           fill="#c28c3d", outline="#f0c45a",
                           width=1, tags="frame")
        c.create_oval(x - 3, y - 3, x + 3, y + 4,
                      fill="#f3e5a5", outline="", tags="frame")
        c.create_text(x, y + 22, text=chest.get("reward", "BOSS REWARD"),
                      width=150, fill="#f0d99f",
                      font=("Segoe UI", 7, "bold"), tags="frame")
        c.create_text(x, y + 35, text=f"CLICK {chest['clicks']}/5",
                      fill="#fff1d2", font=("Segoe UI", 7, "bold"),
                      tags="frame")

    def draw_skill_dialogue(self):
        if self.state not in ("boss_cutscene", "boss_dialogue", "boss_skill"):
            return
        c = self.canvas
        if self.state == "boss_cutscene":
            corpse = self.boss_corpses[-1] if self.boss_corpses else None
            if corpse:
                elapsed = 2.4 - max(0, self.boss_cutscene_until - time.monotonic())
                radius = 45 + int(elapsed * 75)
                c.create_oval(
                    corpse["x"] - radius, corpse["y"] - radius,
                    corpse["x"] + radius, corpse["y"] + radius,
                    outline="#d9a453", width=4, tags="frame"
                )
            c.create_rectangle(0, 0, WIDTH, 85, fill="#080b10",
                               stipple="gray50", outline="", tags="frame")
            c.create_rectangle(0, HEIGHT - 85, WIDTH, HEIGHT,
                               fill="#080b10", stipple="gray50",
                               outline="", tags="frame")
            c.create_text(WIDTH / 2, 42,
                          text=f"{self.boss_corpses[-1]['name'].upper()} HAS FALLEN",
                          fill="#f1d59d", font=("Segoe UI", 23, "bold"),
                          tags="frame")
            c.create_text(WIDTH / 2, HEIGHT - 42,
                          text="THE BATTLEFIELD FALLS SILENT...",
                          fill="#e3ddd0", font=("Segoe UI", 12, "bold"),
                          tags="frame")
            return

        corpse = self.boss_corpses[-1] if self.boss_corpses else None
        if corpse is None:
            return
        if self.state == "boss_dialogue":
            elapsed = 3.2 - max(0, self.boss_dialogue_until - time.monotonic())
            text = (BOSS_DEFEAT_DIALOGUE if elapsed < 1.6 else
                    corpse["skill"][2])
            prompt = ""
        else:
            text = corpse["skill"][2]
            head_x, head_y = corpse["x"] + 22, corpse["y"] - 8
            distance = math.hypot(
                self.player["x"] - head_x, self.player["y"] - head_y
            )
            if distance <= 82 and "e" in self.keys:
                shoulder = (self.player["x"] + 3, self.player["y"] - 12)
                hand = (head_x, head_y - 4)
                c.create_line(*shoulder, *hand, fill="#d2a27d",
                              width=7, tags="frame")
                c.create_oval(hand[0] - 6, hand[1] - 6,
                              hand[0] + 6, hand[1] + 6,
                              fill="#e7bd91", outline="#fff1d2",
                              width=2, tags="frame")
                phase = time.monotonic() * 8
                for index in range(8):
                    angle = phase + index * math.tau / 8
                    inner = 15 + math.sin(phase * 2 + index) * 3
                    outer = 42 + math.cos(phase + index) * 5
                    c.create_line(
                        head_x + math.cos(angle) * inner,
                        head_y + math.sin(angle) * inner,
                        head_x + math.cos(angle) * outer,
                        head_y + math.sin(angle) * outer,
                        fill="#e5c874", width=2, tags="frame"
                    )
                prompt = "HOLD E  -  CHANNELING THE BOSS'S POWER"
            elif distance <= 82:
                prompt = "HOLD E TO RECEIVE THE BOSS'S SKILL"
            else:
                prompt = "MOVE CLOSE TO THE BOSS'S HEAD"

        c.create_rectangle(190, 96, 770, 160, fill="#101718",
                           outline="#d4bd91", width=2, tags="frame")
        c.create_text(WIDTH / 2, 113, text=corpse["name"],
                      fill="#e5c874", font=("Segoe UI", 10, "bold"),
                      tags="frame")
        c.create_text(WIDTH / 2, 139, text=f'"{text}"', width=550,
                      fill="#f0d7c5", font=("Segoe UI", 11, "bold"),
                      tags="frame")
        if prompt:
            if self.state == "boss_skill" and "e" in self.keys:
                c.create_rectangle(0, 0, WIDTH, 70, fill="#080b10",
                                   stipple="gray50", outline="", tags="frame")
                c.create_rectangle(0, HEIGHT - 48, WIDTH, HEIGHT,
                                   fill="#080b10", stipple="gray50",
                                   outline="", tags="frame")
                c.create_text(WIDTH / 2, 35,
                              text="THE POWER PASSES BETWEEN WARRIORS",
                              fill="#f1d59d", font=("Segoe UI", 13, "bold"),
                              tags="frame")
            c.create_text(WIDTH / 2, 482, text=prompt,
                          fill="#fff1d2", font=("Segoe UI", 12, "bold"),
                          tags="frame")
            if self.state == "boss_skill":
                self.draw_bar(350, 500, 260, self.skill_acquire_progress / 2.5,
                              "#e5c874", 9)

    def draw_game(self, now):
        p = self.player
        self.rect(0, 0, WIDTH, 80, "#20292b")
        self.canvas.create_text(24, 19, text="ASHEN FRONT", anchor="w",
                                fill="#e6d9ba", font=("Segoe UI", 13, "bold"), tags="frame")
        self.canvas.create_text(24, 48,
                                text=f"LV {p['level']}  |  FLOOR {self.stage_number()}/{MAX_FLOORS}  |  WAVE {self.floor_wave}/{self.floor_wave_count()}",
                                anchor="w", fill="#c6c5b4", font=("Segoe UI", 10, "bold"),
                                tags="frame")
        self.draw_bar(180, 20, 200, p["hp"] / p["max_hp"], "#c4584e", 13)
        self.canvas.create_text(180, 43, text=f"HP  {p['hp']} / {p['max_hp']}",
                                anchor="w", fill="#e7d8c8", font=("Segoe UI", 9), tags="frame")
        self.draw_bar(180, 57, 200, p["xp"] / p["next_xp"], "#d2a64e", 7)
        self.canvas.create_text(408, 23, text=f"XP  {p['xp']} / {p['next_xp']}",
                                anchor="w", fill="#d8c58f", font=("Segoe UI", 9), tags="frame")
        self.canvas.create_text(WIDTH - 24, 24, text=f"DEFEATED  {self.kills}",
                                anchor="e", fill="#c6c5b4", font=("Segoe UI", 10, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH - 24, 51,
                                text=f"COINS {self.coins}  |  GEMS {self.gems}",
                                anchor="e", fill="#ebc86a",
                                font=("Segoe UI", 10, "bold"), tags="frame")
        if self.state in ("playing", "post_boss"):
            auto_aim_label = "AUTO AIM: ON" if self.auto_aim_enabled else "AUTO AIM: OFF"
            auto_aim_color = "#53634d" if self.auto_aim_enabled else "#343b38"
            self.canvas.create_rectangle(812, 61, 936, 87, fill=auto_aim_color,
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text(874, 74, text=auto_aim_label,
                                    fill="#fff1d2", font=("Segoe UI", 8, "bold"),
                                    tags="frame")
        region_status = f"REGION  {REGIONS[self.region][0]}"
        if self.superhuman_active:
            region_status = f"SUPERHUMAN  -  LEVEL 100  |  {region_status}"
        elif self.evolved:
            region_status = f"ASCENDED  -  LEVEL 100  |  {region_status}"
        elif len(self.skill_copies) >= 7:
            region_status += "  |  SUPERHUMAN READY  -  PRESS T"
        self.canvas.create_text(WIDTH / 2, 68,
                                text=region_status,
                                fill="#d0d4c2", font=("Segoe UI", 8, "bold"), tags="frame")
        if self.equipped_abilities:
            skill_labels = []
            for index, skill in enumerate(self.equipped_abilities):
                ready_at = self.ability_cooldowns.get(skill[0], 0)
                state = "READY" if now >= ready_at else f"{ready_at - now:.1f}s"
                skill_labels.append(f"{index + 1} {skill[0]} {state}")
            self.canvas.create_text(
                WIDTH / 2, HEIGHT - 48, text="   |   ".join(skill_labels[:3]),
                fill="#e1c77d", font=("Segoe UI", 8, "bold"), tags="frame"
            )
            if len(skill_labels) > 3:
                self.canvas.create_text(
                    WIDTH / 2, HEIGHT - 33, text="   |   ".join(skill_labels[3:]),
                    fill="#e1c77d", font=("Segoe UI", 8, "bold"), tags="frame"
                )
        else:
            self.canvas.create_text(
                WIDTH / 2, HEIGHT - 40, text="DEFEAT A BOSS TO LEARN A SKILL",
                fill="#e1c77d", font=("Segoe UI", 9, "bold"), tags="frame"
            )
        if self.boss_weapon_owned:
            self.canvas.create_text(
                408, 51, text="WEAPON: WARDEN BREAKER",
                anchor="w", fill="#f0c45a",
                font=("Segoe UI", 8, "bold"), tags="frame"
            )
        if self.equipped_special_weapon is not None:
            special_weapon = MARKET_WEAPONS[self.equipped_special_weapon]
            self.canvas.create_text(
                600, 51,
                text=f"SPECIAL: {special_weapon['name']}  {self.special_shots_left}/3",
                anchor="w", fill="#8ee5f0",
                font=("Segoe UI", 8, "bold"), tags="frame"
            )

        for pickup in self.pickups:
            x, y = pickup["x"], pickup["y"]
            if pickup["kind"] == "medkit":
                self.canvas.create_oval(x - 9, y - 9, x + 9, y + 9,
                                        fill="#83b581", outline="#d9e3b2", width=2,
                                        tags="frame")
                self.canvas.create_text(x, y, text="+", fill="#f3f5da",
                                        font=("Segoe UI", 12, "bold"), tags="frame")
                if math.hypot(
                    self.mouse_position[0] - x,
                    self.mouse_position[1] - y,
                ) <= 22:
                    self.canvas.create_text(
                        x, y - 20, text="RIGHT-CLICK TO COLLECT",
                        fill="#f3f5da", font=("Segoe UI", 7, "bold"),
                        tags="frame"
                    )
            else:
                self.canvas.create_oval(x - 9, y - 9, x + 9, y + 9,
                                        fill="#d8ae48", outline="#ffeb9e", width=2,
                                        tags="frame")
                self.canvas.create_text(x, y, text="$", fill="#fff3ba",
                                        font=("Segoe UI", 9, "bold"), tags="frame")

        for corpse in self.boss_corpses:
            self.draw_boss_corpse(corpse)
        for chest in self.boss_chests:
            self.draw_boss_chest(chest)

        if self.rescue_battle:
            ally_x = max(ARENA[0] + 30, p["x"] - 48)
            self.draw_demon_king(ally_x, p["y"] + 4, scale=0.38, wings=False)
            self.canvas.create_text(ally_x, p["y"] - 44, text="DEMON KING",
                                    fill="#e5c874",
                                    font=("Segoe UI", 7, "bold"), tags="frame")

        for enemy in self.enemies:
            color = {
                "raider": "#bd6555", "ranger": "#ce9c51", "brute": "#875b72",
                "boss": "#a44951", "minion_boss": "#75517c",
                "kidnapper": "#3e263f", "kidnapper_clone": "#8f739b",
            }[enemy["kind"]]
            if now < enemy["hurt_until"]:
                color = "#f4e3c9"
            facing = (p["x"] - enemy["x"], p["y"] - enemy["y"])
            facing_length = max(1, math.hypot(*facing))
            facing = (facing[0] / facing_length, facing[1] / facing_length)
            self.draw_entity(
                enemy["x"], enemy["y"], enemy["radius"], color, "#352c2b",
                facing, enemy["kind"],
                moving=(math.hypot(p["x"] - enemy["x"], p["y"] - enemy["y"])
                        > enemy["radius"] + 20)
            )
            if enemy["kind"] in ("boss", "minion_boss", "kidnapper"):
                boss_bar_x = WIDTH / 2 - 150
                self.draw_bar(boss_bar_x, 104, 300, enemy["hp"] / enemy["max_hp"],
                              "#c3424a", 10)
                self.canvas.create_text(WIDTH / 2, 91,
                                        text=f'{enemy["boss_name"]}  {enemy["hp"]} HP',
                                        fill="#f0d7c5", font=("Segoe UI", 10, "bold"),
                                        tags="frame")
                if enemy["special_until"] > 0 and enemy["special_line"]:
                    x1, y1, x2, y2 = enemy["special_line"]
                    skill_name = (enemy.get("skill") or ("",))[0]
                    if skill_name in ("Frost Nova", "Ironbark Guard"):
                        radius = 270 if skill_name == "Frost Nova" else 325
                        color = "#8ee5f0" if skill_name == "Frost Nova" else "#a5d46d"
                        self.canvas.create_oval(
                            enemy["x"] - radius, enemy["y"] - radius,
                            enemy["x"] + radius, enemy["y"] + radius,
                            outline=color, width=3, dash=(8, 6), tags="frame"
                        )
                    self.canvas.create_line(x1, y1, x2, y2, fill="#e9b64d",
                                            width=13, dash=(3, 5), tags="frame")
                    self.canvas.create_line(x1, y1, x2, y2, fill="#ffe59a",
                                            width=3, dash=(8, 5), tags="frame")
                if enemy["kind"] == "minion_boss" and enemy.get("clue"):
                    bubble_y = max(
                        ARENA[1] + 52,
                        enemy["y"] - enemy["radius"] - 44,
                    )
                    self.canvas.create_rectangle(
                        enemy["x"] - 142, bubble_y - 37,
                        enemy["x"] + 142, bubble_y + 15,
                        fill="#101214", outline="#d4bd91", width=1,
                        tags="frame"
                    )
                    self.canvas.create_text(
                        enemy["x"], bubble_y - 11,
                        text=enemy["clue"], width=266,
                        fill="#f0d7c5", font=("Segoe UI", 8, "bold"),
                        tags="frame"
                    )
            else:
                self.draw_bar(enemy["x"] - 16, enemy["y"] - enemy["radius"] - 11, 32,
                              enemy["hp"] / enemy["max_hp"], "#d57462", 4)

        player_becomes_titan = any(
            effect["kind"] == "epic_fall"
            and effect["caster"] is p
            and effect["impact_at"] > now
            for effect in self.effects
        )
        facing = p["face"]
        player_radius = self.player_radius()
        if not player_becomes_titan:
            if now < p["knockdown_until"]:
                self.draw_knockdown(p["x"], p["y"])
            else:
                if self.evolved or self.superhuman_active:
                    self.canvas.create_oval(
                        p["x"] - player_radius - 5,
                        p["y"] - player_radius - 5,
                        p["x"] + player_radius + 5,
                        p["y"] + player_radius + 5,
                        outline="#e5c874", width=2, tags="frame"
                    )
                self.draw_entity(
                    p["x"], p["y"], player_radius, "#72a2ad", "#d5d9c0",
                    facing, "scout",
                    moving=any(key in self.keys for key in
                               ("w", "a", "s", "d", "up", "down", "left", "right"))
                )
            if now < p["frozen_until"]:
                self.canvas.create_oval(
                    p["x"] - player_radius - 8,
                    p["y"] - player_radius - 10,
                    p["x"] + player_radius + 8,
                    p["y"] + player_radius + 10,
                    outline="#a9efff", width=3, tags="frame"
                )
                self.canvas.create_text(
                    p["x"], p["y"] - 32, text="FROZEN",
                    fill="#dffbff", font=("Segoe UI", 7, "bold"),
                    tags="frame"
                )
        for projectile in self.projectiles:
            fill = "#ff824a" if projectile.get("kind") == "ember" else "#ffe28a"
            self.canvas.create_oval(projectile["x"] - 4, projectile["y"] - 4,
                                    projectile["x"] + 4, projectile["y"] + 4,
                                    fill=fill, outline="#fff7d1", tags="frame")
        for effect in self.effects:
            if effect["kind"] == "laser":
                x1, y1, x2, y2 = effect["line"]
                self.canvas.create_line(x1, y1, x2, y2, fill="#7cf9ff",
                                        width=14, tags="frame")
                self.canvas.create_line(x1, y1, x2, y2, fill="#ffffff",
                                        width=4, tags="frame")
            elif effect["kind"] == "atomic":
                radius = effect["radius"]
                self.canvas.create_oval(
                    effect["x"] - radius, effect["y"] - radius,
                    effect["x"] + radius, effect["y"] + radius,
                    outline="#ffb64d", width=8, tags="frame"
                )
            elif effect["kind"] == "atomic_bomb":
                progress = 1 - max(
                    0, min(1, (effect["impact_at"] - now) / 0.8)
                )
                bomb_y = ARENA[1] + (effect["y"] - ARENA[1]) * progress
                self.canvas.create_line(
                    effect["x"], ARENA[1], effect["x"], bomb_y,
                    fill="#d2a64e", dash=(3, 5), width=2, tags="frame"
                )
                self.canvas.create_oval(
                    effect["x"] - 12, bomb_y - 12,
                    effect["x"] + 12, bomb_y + 12,
                    fill="#282d29", outline="#ffb64d", width=3, tags="frame"
                )
            elif effect["kind"] in ("fissure", "player_fissure"):
                x1, y1, x2, y2 = effect["line"]
                color = "#e9c65e" if effect["kind"] == "fissure" else "#8ed0c1"
                if effect.get("skill") == "Frost Nova":
                    color = "#8ee5f0"
                elif effect.get("skill") == "Ember Volley":
                    color = "#ff824a"
                elif effect.get("skill") == "Ironbark Guard":
                    color = "#a5d46d"
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=8,
                                        tags="frame")
                self.canvas.create_line(x1, y1, x2, y2, fill="#f4e8bd", width=2,
                                        dash=(4, 3), tags="frame")
            elif effect["kind"] == "muzzle":
                fx, fy = effect["direction"]
                self.canvas.create_oval(effect["x"] - 7, effect["y"] - 7,
                                        effect["x"] + 7, effect["y"] + 7,
                                        fill="#ffe28a", outline="#fff6d0", tags="frame")
                self.canvas.create_line(effect["x"], effect["y"],
                                        effect["x"] + fx * 15, effect["y"] + fy * 15,
                                        fill="#fff6d0", width=3, tags="frame")
            elif effect["kind"] == "burst":
                self.canvas.create_oval(effect["x"] - 12, effect["y"] - 12,
                                        effect["x"] + 12, effect["y"] + 12,
                                        outline="#ffdb8d", width=2, tags="frame")
            elif effect["kind"] == "frost":
                radius = effect.get("radius", 235)
                self.canvas.create_oval(effect["x"] - radius, effect["y"] - radius,
                                        effect["x"] + radius, effect["y"] + radius,
                                        outline="#a4e8f2", width=5, tags="frame")
                inner = radius * 0.83
                self.canvas.create_oval(effect["x"] - inner, effect["y"] - inner,
                                        effect["x"] + inner, effect["y"] + inner,
                                        outline="#daf8ff", width=2, dash=(5, 4),
                                        tags="frame")
            elif effect["kind"] == "shield":
                self.canvas.create_oval(effect["x"] - 24, effect["y"] - 24,
                                        effect["x"] + 24, effect["y"] + 24,
                                        outline="#95c98b", width=4, tags="frame")
            elif effect["kind"] == "boss_frost":
                self.canvas.create_oval(effect["x"] - effect["radius"],
                                        effect["y"] - effect["radius"],
                                        effect["x"] + effect["radius"],
                                        effect["y"] + effect["radius"],
                                        outline="#8ee5f0", width=9, tags="frame")
            elif effect["kind"] == "boss_guard":
                self.canvas.create_oval(effect["x"] - effect["radius"],
                                        effect["y"] - effect["radius"],
                                        effect["x"] + effect["radius"],
                                        effect["y"] + effect["radius"],
                                        outline="#a5d46d", width=9, tags="frame")
            elif effect["kind"] == "boss_ember":
                x1, y1, x2, y2 = effect["line"]
                self.canvas.create_line(x1, y1, x2, y2, fill="#ff824a",
                                        width=20, tags="frame")
                self.canvas.create_line(x1, y1, x2, y2, fill="#ffdc8a",
                                        width=4, dash=(6, 4), tags="frame")
            elif effect["kind"] == "time_freeze":
                pulse = 22 + 10 * math.sin(now * 12)
                for radius in (pulse, pulse + 18, pulse + 36):
                    self.canvas.create_oval(
                        effect["x"] - radius, effect["y"] - radius,
                        effect["x"] + radius, effect["y"] + radius,
                        outline="#9be9ff", width=2, tags="frame"
                    )
            elif effect["kind"] == "ice_star_fall":
                progress = max(0, min(
                    1, (now - (effect["impact_at"] - 0.72)) / 0.72
                ))
                star_y = effect["start_y"] + (
                    effect["y"] - effect["start_y"]
                ) * progress
                self.canvas.create_oval(
                    effect["x"] - 23, effect["y"] - 12,
                    effect["x"] + 23, effect["y"] + 12,
                    outline="#74d9f0", width=2, dash=(4, 3), tags="frame"
                )
                self.canvas.create_polygon(
                    effect["x"], star_y - 15,
                    effect["x"] + 6, star_y - 4,
                    effect["x"] + 16, star_y,
                    effect["x"] + 6, star_y + 5,
                    effect["x"], star_y + 16,
                    effect["x"] - 6, star_y + 5,
                    effect["x"] - 16, star_y,
                    effect["x"] - 6, star_y - 4,
                    fill="#b8f3ff", outline="#effdff", width=2,
                    tags="frame"
                )
                self.canvas.create_line(
                    effect["x"], star_y - 25, effect["x"], star_y - 8,
                    fill="#dffbff", width=3, tags="frame"
                )
            elif effect["kind"] == "epic_fall":
                progress = max(0, min(
                    1, (now - (effect["impact_at"] - 0.9)) / 0.9
                ))
                titan_y = effect["start_y"] + (
                    effect["y"] - effect["start_y"]
                ) * progress
                self.canvas.create_oval(
                    effect["x"] - effect["radius"],
                    effect["y"] - 16,
                    effect["x"] + effect["radius"],
                    effect["y"] + 16,
                    outline="#e9c65e", width=3, dash=(7, 5), tags="frame"
                )
                titan_color = "#9bb8bf" if effect["caster"] is self.player else "#9a5260"
                self.canvas.create_line(
                    effect["x"] - 48, titan_y, effect["x"] + 32, titan_y,
                    fill=titan_color, width=28, tags="frame"
                )
                self.canvas.create_oval(
                    effect["x"] + 27, titan_y - 20,
                    effect["x"] + 68, titan_y + 20,
                    fill=titan_color, outline="#f2d5a5", width=2,
                    tags="frame"
                )
                self.canvas.create_line(
                    effect["x"] - 24, titan_y + 2,
                    effect["x"] - 72, titan_y + 25,
                    fill=titan_color, width=12, tags="frame"
                )
                self.canvas.create_line(
                    effect["x"] + 5, titan_y + 2,
                    effect["x"] + 48, titan_y + 27,
                    fill=titan_color, width=12, tags="frame"
                )
        if self.rescue_battle and self.state in ("playing", "boss_warning"):
            self.draw_demon_king(p["x"] - 58, p["y"] + 5, scale=0.36)
        if now < p["hurt_until"] and int(now * 18) % 2 == 0:
            self.canvas.create_oval(p["x"] - 20, p["y"] - 20, p["x"] + 20, p["y"] + 20,
                                    outline="#f2d5a5", width=2, tags="frame")
        if now < p["shoot_until"]:
            fx, fy = facing
            self.canvas.create_line(p["x"] + fx * 20, p["y"] + fy * 20,
                                    p["x"] + fx * 37, p["y"] + fy * 37,
                                    fill="#fff1b0", width=4, tags="frame")

        if now < self.message_until:
            self.canvas.create_text(WIDTH / 2, 128, text=self.message,
                                    fill="#f0d99f", font=("Segoe UI", 12, "bold"),
                                    tags="frame")
        self.canvas.create_text(WIDTH / 2, HEIGHT - 22,
                                text="MOVE: WASD   SHOOT: SPACE/CLICK   SKILLS: 1-5   AIM: RIGHT-CLICK   E: INTERACT   `: LOADOUT   Q: SIDE QUESTS",
                                fill="#b9c1ac", font=("Segoe UI", 9, "bold"), tags="frame")
        self.draw_skill_dialogue()
        if self.active_quest:
            quest_title, _, quest_target = self.active_quest
            quest_status = ("COMPLETE" if self.quest_complete else
                            f"{self.quest_progress}/{quest_target}")
            self.canvas.create_text(WIDTH - 170, 116,
                                    text=f"QUEST: {quest_title}  {quest_status}",
                                    fill="#e5c874", font=("Segoe UI", 9, "bold"),
                                    tags="frame")
        if self.quick_loadout_open:
            self.draw_quick_loadout()

    def draw_knockdown(self, x, y):
        c = self.canvas
        c.create_oval(x - 24, y - 10, x + 24, y + 10, fill="#252b27",
                      outline="", tags="frame")
        c.create_oval(x - 16, y - 7, x + 12, y + 7, fill="#527e87",
                      outline="#d5d9c0", width=2, tags="frame")
        c.create_oval(x + 8, y - 8, x + 22, y + 6, fill="#77866a",
                      outline="#353b32", width=1, tags="frame")
        c.create_line(x - 7, y, x + 13, y, fill="#292c29", width=4, tags="frame")
        c.create_text(x, y - 20, text="STUNNED", fill="#f0d7a2",
                      font=("Segoe UI", 8, "bold"), tags="frame")

    def draw_region_select(self):
        boss_kills = self.stage_number()
        choices = [
            (self.region + 1) % len(REGIONS),
            (self.region + 2) % len(REGIONS),
        ]
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 185, text="WARLORD DEFEATED",
                                fill="#f0d7c5", font=("Segoe UI", 28, "bold"),
                                tags="frame")
        self.canvas.create_text(
            WIDTH / 2, 235,
            text=f'"{self.boss_skill()[2]}"  -  {self.boss_name()}',
            fill="#e2c98e", font=("Segoe UI", 11), tags="frame"
        )
        self.canvas.create_text(
            WIDTH / 2, 280,
            text=f"Territory {boss_kills} claimed. Choose the next region to travel to:",
            fill="#d0d4c2", font=("Segoe UI", 12), tags="frame"
        )
        for index, region_id in enumerate(choices):
            x1 = 90 + index * 410
            x2 = x1 + 350
            self.canvas.create_rectangle(x1, 320, x2, 410, fill="#39453b",
                                         outline="#d4bd91", width=2, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 350, text=REGIONS[region_id][0],
                                    fill="#f0dfb8", font=("Segoe UI", 17, "bold"),
                                    tags="frame")
            claim_text = "CLAIMED" if self.territories[region_id] else "UNCLAIMED"
            self.canvas.create_text((x1 + x2) / 2, 383,
                                    text=f"{claim_text}  -  CLICK TO TRAVEL",
                                    fill="#d0d4c2", font=("Segoe UI", 10, "bold"),
                                    tags="frame")
        self.canvas.create_text(WIDTH / 2, 463,
                                text=f"Boss skill acquired: {self.boss_skill()[0]}. Cast skills directly with keys 1-5.",
                                fill="#9fe0ce", font=("Segoe UI", 12, "bold"), tags="frame")
        if len(self.equipped_abilities) > 1:
            skills = ", ".join(skill[0] for skill in self.equipped_abilities)
            self.canvas.create_text(WIDTH / 2, 480,
                                    text=f"Unlocked skills: {skills}",
                                    fill="#c2c7b9", font=("Segoe UI", 9), tags="frame")
        self.canvas.create_text(WIDTH / 2, 495,
                                text="Collect dropped coins by walking over them. Space or click to shoot.",
                                fill="#c2c7b9", font=("Segoe UI", 10), tags="frame")

    def draw_stage_intro(self):
        self.canvas.create_rectangle(
            WIDTH / 2 - 210, HEIGHT / 2 - 70,
            WIDTH / 2 + 210, HEIGHT / 2 + 70,
            fill="#18201f", outline="#d4bd91", width=2, tags="frame"
        )
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 - 24,
                                text=self.stage_label(),
                                fill="#f1dfb8", font=("Segoe UI", 30, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, HEIGHT / 2 + 23,
                                text=f"REGION  {REGIONS[self.region][0]}",
                                fill="#d3c28f", font=("Segoe UI", 12, "bold"),
                                tags="frame")

    def draw_boss_warning(self, now):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#080b10", outline="", tags="frame")
        shake = math.sin(now * 37) * 5
        tear_x = WIDTH * 0.53 + shake
        c.create_polygon(
            tear_x - 20, 70, tear_x + 9, 70, tear_x - 8, 177,
            tear_x + 22, 262, tear_x - 15, 344, tear_x + 12, 453,
            tear_x - 7, HEIGHT - 48, tear_x - 31, HEIGHT - 48,
            tear_x - 4, 453, tear_x - 37, 344, tear_x - 5, 262,
            tear_x - 34, 177, fill="#b9c9d1", outline="#f2e7d4",
            width=2, tags="frame"
        )
        c.create_line(tear_x, 82, tear_x - 28, 180, tear_x + 15, 260,
                      tear_x - 21, 344, tear_x + 8, 446,
                      fill="#fff3d4", width=4, tags="frame")
        c.create_text(WIDTH / 2, 150, text="THE SKY RIPS OPEN",
                      fill="#d7e3e5", font=("Segoe UI", 23, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 236, text=f'{self.boss_name().upper()}',
                      fill="#e2a99a", font=("Segoe UI", 29, "bold"), tags="frame")
        c.create_text(WIDTH / 2, 295, text=f'"{self.boss_dialogue()}"',
                      fill="#f7e8d0", font=("Segoe UI", 22, "bold"),
                      width=800, tags="frame")
        remaining = max(0, self.boss_warning_until - now)
        c.create_text(WIDTH / 2, 365, text=f"ENTERING THE BATTLEFIELD  {remaining:.1f}",
                      fill="#c7c7c2", font=("Segoe UI", 13, "bold"), tags="frame")

    def draw_minion_difficulty(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101214",
                           outline="", tags="frame")
        c.create_text(
            WIDTH / 2, 155, text="A DEMON MINION BLOCKS THE FLOOR",
            fill="#e2a99a", font=("Segoe UI", 25, "bold"), tags="frame"
        )
        c.create_text(
            WIDTH / 2, 205,
            text="Choose its strength. Higher danger earns more coins.",
            fill="#d0d4c2", font=("Segoe UI", 13), tags="frame"
        )
        for index, (name, health, reward) in enumerate(MINION_DIFFICULTIES):
            x1 = 55 + index * 285
            x2 = x1 + 255
            c.create_rectangle(
                x1, 260, x2, 430, fill="#35443d",
                outline="#d4bd91", width=2, tags="frame"
            )
            c.create_text(
                (x1 + x2) / 2, 300, text=f"{index + 1}. {name}",
                fill="#f0dfb8", font=("Segoe UI", 15, "bold"), tags="frame"
            )
            c.create_text(
                (x1 + x2) / 2, 345, text=f"{health:,} HP",
                fill="#e2a99a", font=("Segoe UI", 17, "bold"), tags="frame"
            )
            c.create_text(
                (x1 + x2) / 2, 385, text=f"REWARD  {reward:,} COINS",
                fill="#e5c874", font=("Segoe UI", 11, "bold"), tags="frame"
            )
            c.create_text(
                (x1 + x2) / 2, 414, text="CLICK TO CHOOSE",
                fill="#c2c7b9", font=("Segoe UI", 8, "bold"), tags="frame"
            )
        c.create_text(
            WIDTH / 2, 480, text="PRESS 1, 2, OR 3 TO CHOOSE",
            fill="#c2c7b9", font=("Segoe UI", 10, "bold"), tags="frame"
        )

    def draw_tower_exterior(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#121619", tags="frame")
        c.create_rectangle(760, 20, 930, 58, fill="#35443d",
                           outline="#d4bd91", tags="frame")
        c.create_text(845, 39, text="FLOOR STAIRS  P",
                      fill="#fff1d2", font=("Segoe UI", 9, "bold"), tags="frame")
        for x in range(0, WIDTH, 80):
            c.create_line(x, 0, WIDTH / 2, 370, fill="#20282a", width=2,
                          tags="frame")
        c.create_polygon(300, 520, 335, 170, 390, 105, 570, 105,
                         625, 170, 660, 520, fill="#303638",
                         outline="#a78d60", width=4, tags="frame")
        c.create_polygon(390, 180, 480, 90, 570, 180,
                         fill="#252c2e", outline="#c1a56d", width=3, tags="frame")
        c.create_rectangle(385, 280, 575, 520, fill="#111719",
                           outline="#c1a56d", width=3, tags="frame")
        c.create_arc(385, 235, 575, 385, start=0, extent=180,
                     style=tk.ARC, outline="#c1a56d", width=3, tags="frame")
        c.create_text(WIDTH / 2, 48, text="THE TOWER OF THE VEIL",
                      fill="#e5c874", font=("Segoe UI", 22, "bold"),
                      tags="frame")
        c.create_text(WIDTH / 2, 557,
                      text="ENTER THE TOWER  -  PRESS E OR CLICK THE GATE",
                      fill="#fff1d2", font=("Segoe UI", 12, "bold"),
                      tags="frame")

    def draw_hall(self, c, vanishing_x, vanishing_y, now):
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#15191d", tags="frame")
        for index in range(7):
            x = vanishing_x + (index - 3) * 112
            c.create_polygon(x, vanishing_y, x - 76, HEIGHT, x - 18, HEIGHT,
                             fill="#4a3b2e", stipple="gray75", outline="",
                             tags="frame")
        c.create_polygon(0, 0, WIDTH, 0, vanishing_x + 130, vanishing_y,
                         vanishing_x - 130, vanishing_y,
                         fill="#25282b", outline="", tags="frame")
        c.create_polygon(0, HEIGHT, WIDTH, HEIGHT, vanishing_x + 130, vanishing_y,
                         vanishing_x - 130, vanishing_y,
                         fill="#333337", outline="#8b7557", width=2, tags="frame")
        for index in range(11):
            x = index * 100
            c.create_line(x, HEIGHT, vanishing_x, vanishing_y,
                          fill="#585044", width=1, tags="frame")
        for depth in (0.25, 0.43, 0.62, 0.82):
            y = vanishing_y + (HEIGHT - vanishing_y) * depth
            c.create_line(0, y, WIDTH, y, fill="#51483f", width=2, tags="frame")
        for side in (-1, 1):
            for index in range(4):
                depth = (index + 1) / 5
                center_x = vanishing_x + side * (120 + depth * 370)
                base_y = vanishing_y + depth * 420
                half = 13 + depth * 43
                torch_y = base_y - (45 + depth * 110)
                glow = 13 + 3 * math.sin(now * 5 + index * 2 + side)
                c.create_oval(center_x - glow, torch_y - glow,
                              center_x + glow, torch_y + glow,
                              fill="#c1914d", stipple="gray50", outline="",
                              tags="frame")
                c.create_polygon(
                    center_x - half, base_y,
                    center_x - half * 0.65, base_y - (45 + depth * 110),
                    center_x + half * 0.65, base_y - (45 + depth * 110),
                    center_x + half, base_y,
                    fill="#4a4741", outline="#93805f", width=2, tags="frame"
                )
                c.create_oval(center_x - half * 0.55, torch_y - 10 * depth,
                              center_x + half * 0.55, torch_y + 10 * depth,
                              fill="#c1914d", outline="#d9b66f", tags="frame")

    def draw_demon_king(self, x, y, scale=1, wings=True, pulled=0,
                        animation_time=None):
        c = self.canvas
        wing_flap = (math.sin(animation_time * 9) * 18 * scale
                     if animation_time is not None else 0)
        if wings:
            c.create_polygon(x - 18 * scale, y - 10 * scale,
                             x - 100 * scale, y - 82 * scale - wing_flap,
                             x - 73 * scale, y + 3 * scale - wing_flap * 0.35,
                             x - 112 * scale, y + 35 * scale + wing_flap * 0.45,
                             x - 25 * scale, y + 40 * scale,
                             fill="#4c2938", outline="#c16a5d", width=2,
                             tags="frame")
            c.create_polygon(x + 18 * scale, y - 10 * scale,
                             x + 100 * scale, y - 82 * scale - wing_flap,
                             x + 73 * scale, y + 3 * scale - wing_flap * 0.35,
                             x + 112 * scale, y + 35 * scale + wing_flap * 0.45,
                             x + 25 * scale, y + 40 * scale,
                             fill="#4c2938", outline="#c16a5d", width=2,
                             tags="frame")
        c.create_oval(x - 23 * scale, y - 52 * scale,
                      x + 23 * scale, y - 5 * scale,
                      fill="#a45b48", outline="#e2bb83", width=2, tags="frame")
        c.create_polygon(x - 18 * scale, y - 42 * scale,
                         x - 40 * scale, y - 88 * scale,
                         x - 7 * scale, y - 60 * scale,
                         fill="#d2a264", outline="#f0d7a2", tags="frame")
        c.create_polygon(x + 18 * scale, y - 42 * scale,
                         x + 40 * scale, y - 88 * scale,
                         x + 7 * scale, y - 60 * scale,
                         fill="#d2a264", outline="#f0d7a2", tags="frame")
        c.create_polygon(x - 32 * scale, y + 44 * scale,
                         x + 32 * scale, y + 44 * scale,
                         x + 22 * scale, y - 15 * scale,
                         x - 22 * scale, y - 15 * scale,
                         fill="#563444", outline="#c17d67", width=2, tags="frame")
        for side in (-1, 1):
            c.create_oval(x + side * 8 * scale - 3 * scale,
                          y - 34 * scale - 3 * scale,
                          x + side * 8 * scale + 3 * scale,
                          y - 34 * scale + 3 * scale,
                          fill="#f3cf68", outline="", tags="frame")
        c.create_line(x - 10 * scale, y - 5 * scale,
                      x + 10 * scale, y - 5 * scale,
                      fill="#f0d7c5", width=max(1, int(2 * scale)), tags="frame")

    def draw_opening_cutscene(self, now):
        elapsed = min(12, max(0, now - self.opening_cutscene_started))
        walk_progress = min(1, elapsed / 4)
        vanishing_x = WIDTH / 2 + math.sin(elapsed * 0.7) * 38
        vanishing_y = 205 + walk_progress * 42 + math.sin(elapsed * 1.2) * 5
        self.draw_hall(self.canvas, vanishing_x, vanishing_y, now)

        if elapsed < 4:
            for index in range(22):
                angle = index * math.tau / 22
                inner = 35 + (index % 4) * 14
                outer = 130 + (index % 5) * 34
                drift = (now * (85 + index % 4 * 24)) % 105
                self.canvas.create_line(
                    vanishing_x + math.cos(angle) * (inner + drift),
                    vanishing_y + math.sin(angle) * (inner + drift),
                    vanishing_x + math.cos(angle) * (outer + drift),
                    vanishing_y + math.sin(angle) * (outer + drift),
                    fill="#bba77d", width=1, tags="frame"
                )

        flash = max(0, 1 - abs(elapsed - 4.05) / 0.28)
        if flash:
            self.canvas.create_rectangle(
                0, 0, WIDTH, HEIGHT, fill="#d9efff",
                stipple="gray75", outline="", tags="frame"
            )

        demon_x, demon_y, demon_scale = WIDTH / 2, 315, 1.3
        if elapsed < 4:
            scout_y = HEIGHT - 125 - walk_progress * 245
            scout_x = WIDTH / 2 + math.sin(elapsed * 1.7) * 12
            self.canvas.create_text(WIDTH / 2, HEIGHT - 38,
                                    text="A NEW JOURNEY BEGINS",
                                    fill="#e3ddd0", font=("Segoe UI", 12, "bold"),
                                    tags="frame")
            self.draw_entity(scout_x, scout_y, 22 - walk_progress * 12,
                             "#72a2ad", "#d5d9c0", (0, -1), "scout",
                             moving=True)
        elif elapsed < 7:
            arrival = min(1, (elapsed - 4) / 1.35)
            arrival = arrival * arrival * (3 - 2 * arrival)
            demon_x = WIDTH + 145 - arrival * (WIDTH / 2 + 145)
            demon_y = 315 + math.sin(elapsed * 3.2) * 10
            demon_scale = 0.75 + arrival * 0.62
            pulse = 72 + 9 * math.sin(now * 7)
            for index in range(18):
                angle = index * math.tau / 18 + now * 0.12
                inner = 95 + (index % 3) * 12
                outer = 175 + (index % 4) * 24
                self.canvas.create_line(
                    demon_x + math.cos(angle) * inner,
                    demon_y + math.sin(angle) * inner,
                    demon_x + math.cos(angle) * outer,
                    demon_y + math.sin(angle) * outer,
                    fill="#8c5264", width=2, tags="frame"
                )
            self.canvas.create_oval(demon_x - pulse, demon_y - pulse * 1.35,
                                    demon_x + pulse, demon_y + pulse * 1.35,
                                    outline="#bb6681", width=3, tags="frame")
            for side in (-1, 1):
                self.canvas.create_line(
                    demon_x + side * 115, demon_y - 100,
                    demon_x + side * 26, demon_y + 10,
                    fill="#edb1bd", width=3, tags="frame"
                )
            self.draw_demon_king(demon_x, demon_y, scale=demon_scale,
                                 animation_time=now)
        elif elapsed < 9:
            self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT,
                                         fill="#8bb4ca", stipple="gray75",
                                         outline="", tags="frame")
            for index in range(32):
                angle = index * math.tau / 32 + now * 0.18
                inner = 58 + (index % 4) * 9
                outer = inner + 34 + (index % 3) * 17
                self.canvas.create_line(
                    demon_x + math.cos(angle) * inner,
                    demon_y + math.sin(angle) * inner,
                    demon_x + math.cos(angle) * outer,
                    demon_y + math.sin(angle) * outer,
                    fill="#d9f0ff", width=2, tags="frame"
                )
            for index in range(26):
                drift = (now * (24 + index % 5 * 8) + index * 61) % HEIGHT
                x = (index * 83 + 31 + math.sin(now + index) * 12) % WIDTH
                self.canvas.create_polygon(
                    x, drift, x + 4, drift + 13, x - 3, drift + 19,
                    fill="#f3e8c6", outline="#c9efff", tags="frame"
                )
            self.draw_demon_king(demon_x, demon_y, scale=demon_scale,
                                 animation_time=now)
        else:
            pull = min(1, (elapsed - 9) / 2)
            pull = pull * pull * (3 - 2 * pull)
            portal_x = WIDTH / 2 + 285
            portal_pulse = 8 * math.sin(now * 8)
            self.canvas.create_oval(portal_x - 62 - portal_pulse, 198,
                                    portal_x + 62 + portal_pulse, 432,
                                    fill="#21132e", outline="#9f66bd",
                                    width=8, tags="frame")
            for ring in range(3):
                inset = ring * 13
                self.canvas.create_arc(
                    portal_x - 50 + inset, 210 + inset,
                    portal_x + 50 - inset, 420 - inset,
                    start=(now * 100 + ring * 120) % 360,
                    extent=235, style=tk.ARC,
                    outline="#e0b5ff" if ring % 2 == 0 else "#8e55bf",
                    width=3, tags="frame"
                )
            demon_x = WIDTH / 2 + pull * 260
            demon_y = 315 - pull * 25
            demon_scale = max(0.06, 1.37 - pull * 1.32)
            self.canvas.create_line(demon_x - 28, demon_y,
                                    portal_x - 48, 315,
                                    fill="#7540a5", width=12, tags="frame")
            self.canvas.create_line(demon_x - 22, demon_y,
                                    portal_x - 48, 315,
                                    fill="#e1a9ff", width=3, tags="frame")
            for index in range(18):
                angle = index * math.tau / 18 + now * 1.1
                radius = 30 + (index % 5) * 18 + pull * 38
                x = demon_x + math.cos(angle) * radius
                y = demon_y + math.sin(angle) * radius
                self.canvas.create_oval(x - 2, y - 2, x + 3, y + 3,
                                        fill="#dfb6ff", outline="", tags="frame")
            self.draw_demon_king(demon_x, demon_y, scale=demon_scale,
                                 animation_time=now)

        if elapsed < 6.6:
            dialogue = "WELCOME TO MY WORLD OF DEATH AND DESIRE!"
        elif elapsed < 9:
            dialogue = ("YOU HAVE TO MAKE YOUR WAY FROM THE 1ST STAGE TO THE "
                        "200TH FLOOR, WHERE MY MINION WILL FIGHT YOU WITH "
                        "50% OF MY ORIGINAL POWERS...")
        elif elapsed < 10.8:
            dialogue = ("THEN, AFTER CLIMBING ALL 200 FLOORS, FIND AND DEFEAT ME "
                        "TO BECOME THE TOWER KING...")
        else:
            dialogue = "HELP!!"
        if elapsed >= 4:
            self.canvas.create_rectangle(0, 480, WIDTH, 590, fill="#101214",
                                         stipple="gray50", outline="",
                                         tags="frame")
            self.canvas.create_line(110, 485, 850, 485,
                                    fill="#c17d67", width=2, tags="frame")
            self.canvas.create_text(130, 506, text="DEMON KING",
                                    anchor="w", fill="#e5c874",
                                    font=("Segoe UI", 10, "bold"),
                                    tags="frame")
            self.canvas.create_text(WIDTH / 2, 546, text=f'"{dialogue}"',
                                    width=730, fill="#fff1d2",
                                    font=("Segoe UI", 14, "bold"), tags="frame")
        if elapsed > 9:
            self.canvas.create_text(WIDTH / 2, 615,
                                    text="A DARK FORCE DRAGS HIM INTO THE PORTAL",
                                    fill="#cf9bd9", font=("Segoe UI", 9, "bold"),
                                    tags="frame")
        self.canvas.create_rectangle(0, 0, WIDTH, 25, fill="#090b0e",
                                     outline="", tags="frame")
        self.canvas.create_rectangle(0, HEIGHT - 22, WIDTH, HEIGHT,
                                     fill="#090b0e", outline="", tags="frame")
        self.canvas.create_text(28, 12, text="THE TOWER OF THE VEIL",
                                anchor="w", fill="#d7c69f",
                                font=("Segoe UI", 8, "bold"), tags="frame")
        self.canvas.create_text(WIDTH - 28, 12,
                                text=f"PROLOGUE  /  {min(12, int(elapsed)):02d}:12",
                                anchor="e", fill="#d7c69f",
                                font=("Segoe UI", 8, "bold"), tags="frame")
        for impact_time, strength in ((4.05, 7), (7.0, 4), (9.1, 5), (11.4, 3)):
            impact = max(0, 1 - abs(elapsed - impact_time) / 0.3)
            if impact:
                self.canvas.move(
                    "frame",
                    math.sin(now * 95) * strength * impact,
                    math.cos(now * 83) * strength * impact
                )

    def draw_tower_gate(self):
        self.draw_hall(self.canvas, WIDTH / 2, 200, time.monotonic())
        gate_x, gate_y = WIDTH / 2, ARENA[1] + 208
        pulse = 8 + math.sin(time.monotonic() * 4) * 5
        self.canvas.create_oval(gate_x - 42 - pulse, gate_y - 58 - pulse,
                                gate_x + 42 + pulse, gate_y + 58 + pulse,
                                fill="#221331", outline="#a86aca", width=4,
                                tags="frame")
        self.canvas.create_text(gate_x, gate_y, text="FLOOR 1",
                                fill="#f5dc9b", font=("Segoe UI", 10, "bold"),
                                tags="frame")
        self.canvas.create_rectangle(375, 195, 585, 335, fill="#303036",
                                     outline="#c4a56a", width=4, tags="frame")
        self.canvas.create_text(WIDTH / 2, 235, text="THE THRONE",
                                fill="#f0d7c5", font=("Segoe UI", 15, "bold"),
                                tags="frame")
        self.canvas.create_polygon(420, 325, 435, 260, 525, 260, 540, 325,
                                  fill="#613849", outline="#cfaa70",
                                  width=3, tags="frame")
        self.draw_entity(self.player["x"], self.player["y"], 15,
                         "#72a2ad", "#d5d9c0", (1, 0), "scout",
                         moving=bool(self.keys))
        self.canvas.create_text(WIDTH / 2, 38,
                                text="THE PORTAL IS HIDDEN BEHIND THE THRONE",
                                fill="#f0d7c5", font=("Segoe UI", 16, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, HEIGHT - 22,
                                text="MOVE WITH WASD / ARROWS  -  STAND BY THE PORTAL AND PRESS E",
                                fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                                tags="frame")

    def draw_quest_select(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        floor = self.stage_number()
        self.canvas.create_text(WIDTH / 2, 105,
                                text=f"FLOOR {floor}  -  CHOOSE A QUEST",
                                fill="#f0d7c5", font=("Segoe UI", 27, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 158,
                                text="HIGHER-RISK QUESTS PAY MORE",
                                fill="#e5c874", font=("Segoe UI", 13, "bold"),
                                tags="frame")
        for index, (title, description, target) in enumerate(QUEST_OPTIONS):
            x1 = 80 + index * 275
            x2 = x1 + 245
            self.canvas.create_rectangle(x1, 245, x2, 455,
                                         fill="#35443d", outline="#d4bd91",
                                         width=2, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 292, text=f"QUEST {index + 1}",
                                    fill="#c8b487", font=("Segoe UI", 11, "bold"),
                                    tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 342, text=title,
                                    width=210, fill="#f0dfb8",
                                    font=("Segoe UI", 15, "bold"), tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 390, text=description,
                                    fill="#c2c7b9", font=("Segoe UI", 11),
                                    tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 430,
                                    text=f"REWARD  {self.quest_rewards[index]} COINS",
                                    fill="#e5c874", font=("Segoe UI", 10, "bold"),
                                    tags="frame")
        self.canvas.create_text(WIDTH / 2, 510,
                                text="CHOOSE ONE QUEST BEFORE ENTERING THE FLOOR",
                                fill="#d0d4c2", font=("Segoe UI", 11, "bold"),
                                tags="frame")

    def draw_minion_reveal(self, now):
        remaining = max(0, self.boss_dialogue_until - now)
        corpse = self.boss_corpses[-1] if self.boss_corpses else None
        x = corpse["x"] if corpse else WIDTH / 2
        y = corpse["y"] if corpse else HEIGHT / 2
        box_x = max(155, min(WIDTH - 155, x))
        box_y = max(150, y - 120)
        self.canvas.create_rectangle(
            box_x - 150, box_y - 42, box_x + 150, box_y + 34,
            fill="#101214", stipple="gray50",
            outline="#d4bd91", width=2, tags="frame"
        )
        self.canvas.create_text(
            box_x, box_y - 25, text="THE MINION'S CLUE",
            fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        self.canvas.create_text(
            box_x, box_y + 1, text=self.clue_dialogue, width=278,
            fill="#f0d7c5", font=("Segoe UI", 9, "bold"), tags="frame"
        )
        self.canvas.create_text(
            box_x, box_y + 52,
            text=f"CLUES FOUND  {len(self.tower_clues)}/{len(TOWER_MINIONS)}"
            + (f"  -  {remaining:.1f}" if remaining else ""),
            fill="#c2c7b9", font=("Segoe UI", 9, "bold"), tags="frame"
        )

    def draw_kidnapper_reveal(self, now):
        elapsed = 6 - max(0, self.kidnapper_reveal_until - now)
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#090a0d",
                                     stipple="gray50", outline="", tags="frame")
        self.draw_demon_king(355, 310, scale=1.1)
        self.canvas.create_text(640, 205, text="SCOUT: WHY DID YOU KIDNAP HIM?",
                                width=430, fill="#f0d7c5",
                                font=("Segoe UI", 13, "bold"), tags="frame")
        if elapsed < 2:
            answer = "VEIL THIEF: I TOOK HIM TO KEEP THE FIRST GATE SEALED."
        elif elapsed < 4:
            answer = "VEIL THIEF: I AM THE SHADOW HE CAST AWAY."
        else:
            answer = "VEIL THIEF: I AM HIS OTHER SELF—"
        self.canvas.create_text(640, 275, text=f'"{answer}"', width=480,
                                fill="#d4b8ed", font=("Segoe UI", 12, "bold"),
                                tags="frame")
        self.canvas.create_oval(720, 350, 850, 500, fill="#17101f",
                                outline="#9f66bd", width=6, tags="frame")
        if elapsed > 4:
            self.canvas.create_text(640, 390, text="THE VEIL THIEF VANISHES",
                                    fill="#e5c874", font=("Segoe UI", 16, "bold"),
                                    tags="frame")
        self.canvas.create_text(WIDTH / 2, 565,
                                text="THE DEMON KING IS FREE. THE TOWER CROWN IS YOURS.",
                                fill="#f0d7c5", font=("Segoe UI", 13, "bold"),
                                tags="frame")

    def draw_victory(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101214",
                                     tags="frame")
        self.draw_demon_king(330, 310, scale=1.25)
        self.draw_entity(600, 360, 28, "#72a2ad", "#d5d9c0",
                         (1, 0), "scout")
        self.canvas.create_text(WIDTH / 2, 110, text="TOWER KING",
                                fill="#f1d59d", font=("Segoe UI", 40, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 475,
                                text="THE DEMON KING IS FREE. YOUR CLIMB IS COMPLETE.",
                                width=800, fill="#e3ddd0",
                                font=("Segoe UI", 13, "bold"), tags="frame")

    def draw_cosmetic_chest(self):
        category, name = self.pending_cosmetic_chest
        clicks = self.cosmetic_chest_clicks
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 150, text="A NEW ITEM!",
                                fill="#f0d7c5", font=("Segoe UI", 28, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 195, text=f"{category}: {name}",
                                fill="#e5c874", font=("Segoe UI", 17, "bold"),
                                tags="frame")
        chest_x, chest_y = WIDTH / 2, 355
        self.canvas.create_oval(chest_x - 118, chest_y + 45,
                                chest_x + 118, chest_y + 75,
                                fill="#080b10", outline="", tags="frame")
        self.canvas.create_rectangle(chest_x - 90, chest_y - 10,
                                     chest_x + 90, chest_y + 52,
                                     fill="#704c32", outline="#f0c45a",
                                     width=4, tags="frame")
        self.canvas.create_rectangle(chest_x - 90, chest_y + 7,
                                     chest_x + 90, chest_y + 23,
                                     fill="#c28c3d", outline="#f0c45a",
                                     width=2, tags="frame")
        self.canvas.create_rectangle(chest_x - 13, chest_y + 2,
                                     chest_x + 13, chest_y + 33,
                                     fill="#f3e5a5", outline="#fff1d2",
                                     width=2, tags="frame")
        lid_lift = min(clicks, 5) * 5
        self.canvas.create_polygon(
            chest_x - 90, chest_y - 10,
            chest_x - 75, chest_y - 60 - lid_lift,
            chest_x + 75, chest_y - 60 - lid_lift,
            chest_x + 90, chest_y - 10,
            fill="#8b5a35", outline="#f0c45a", width=4, tags="frame"
        )
        self.canvas.create_text(WIDTH / 2, 465,
                                text=f"CLICK THE CHEST  {clicks}/5",
                                fill="#fff1d2", font=("Segoe UI", 14, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 500,
                                text="CLICK FIVE TIMES TO OPEN IT",
                                fill="#c2c7b9", font=("Segoe UI", 10, "bold"),
                                tags="frame")

    def draw_post_boss(self, now):
        remaining = max(0, self.travel_ready_at - now)
        floor_coins = sum(
            pickup["value"] for pickup in self.pickups
            if pickup["kind"] == "coins"
        )
        collect_label = (
            f"COLLECT ALL FLOOR COINS  +{floor_coins}"
            if floor_coins else "ALL FLOOR COINS COLLECTED"
        )
        collect_color = "#53634d" if floor_coins else "#343b38"
        self.canvas.create_rectangle(340, 465, 620, 500, fill=collect_color,
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(
            WIDTH / 2, 482, text=collect_label,
            fill="#fff1d2", font=("Segoe UI", 9, "bold"), tags="frame"
        )
        self.canvas.create_rectangle(96, 512, WIDTH - 96, 612,
                                     fill="#18201f", outline="#d4bd91",
                                     width=2, tags="frame")
        self.canvas.create_text(WIDTH / 2, 530,
                                text=f"COINS: {self.coins}   |   COLLECT THE BOSS'S COINS BEFORE YOU GO",
                                fill="#e5c874", font=("Segoe UI", 11, "bold"),
                                tags="frame")
        if remaining <= 0:
            stage_text = "NEXT STAGE READY  -  MOVE WITH WASD / ARROWS"
        else:
            stage_text = f"NEXT STAGE IN {remaining:.1f} SECONDS  -  MOVE WITH WASD / ARROWS"
        self.canvas.create_text(WIDTH / 2, 550,
                                text=stage_text,
                                fill="#d8c58f", font=("Segoe UI", 10, "bold"),
                                tags="frame")
        if self.rescue_route_unlocked:
            buttons = (
                (80, 560, 260, 600, "SHOP  B"),
                (270, 560, 450, 600, "TERRAIN  M"),
                (470, 560, 670, 600, "RESCUE ROUTE"),
                (690, 560, 880, 600, "KEEP CLIMBING"),
            )
        else:
            buttons = (
                (110, 560, 300, 600, "SHOP  B"),
                (320, 560, 520, 600, "TERRAIN  M"),
                (650, 560, 850, 600, "NEXT FLOOR"),
            )
        if self.rescue_route_unlocked:
            clue_status = f"FIVE CLUES FOUND  |  {len(self.tower_clues)}/{len(TOWER_MINIONS)}"
            self.canvas.create_text(WIDTH / 2, 545, text=clue_status,
                                    fill="#e5c874", font=("Segoe UI", 9, "bold"),
                                    tags="frame")
        for x1, y1, x2, y2, label in buttons:
            enabled = label not in ("NEXT FLOOR", "KEEP CLIMBING") or remaining <= 0
            fill = "#53634d" if enabled else "#343b38"
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill,
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                    text=label, fill="#fff1d2",
                                    font=("Segoe UI", 10, "bold"), tags="frame")

    def draw_auto_aim_prompt(self):
        next_stage = ROMAN_NUMERALS[(self.stage_number() - 1) % len(ROMAN_NUMERALS)]
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_rectangle(130, 205, WIDTH - 130, 405,
                                     fill="#18201f", outline="#d4bd91",
                                     width=2, tags="frame")
        self.canvas.create_text(WIDTH / 2, 250,
                                text=f"STAGE {next_stage}  -  AUTO AIM",
                                fill="#f0d7c5", font=("Segoe UI", 23, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 292,
                                text="Continue using auto aim for this stage?",
                                fill="#d8c58f", font=("Segoe UI", 13, "bold"),
                                tags="frame")
        for x1, x2, label in ((170, 460, "YES  -  KEEP AUTO AIM"),
                              (500, 790, "NO  -  TURN IT OFF")):
            self.canvas.create_rectangle(x1, 320, x2, 360, fill="#53634d",
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 340, text=label,
                                    fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                                    tags="frame")
        self.canvas.create_text(WIDTH / 2, 385,
                                text="AUTO AIM IS ALWAYS OFF AT THE START OF A NEW RUN.",
                                fill="#b9c1ac", font=("Segoe UI", 9, "bold"),
                                tags="frame")

    def draw_character_customization(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 58, text="CHARACTER CUSTOMIZATION",
                                fill="#f0d7c5", font=("Segoe UI", 25, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH - 50, 94, text=f"COINS: {self.coins}",
                                anchor="e", fill="#e5c874",
                                font=("Segoe UI", 12, "bold"), tags="frame")

        categories = tuple(COSMETIC_ITEMS)
        for index, category in enumerate(categories):
            x1 = 30 + index * 180
            x2 = x1 + 160
            fill = "#74563d" if index == self.customize_category else "#35443d"
            self.canvas.create_rectangle(x1, 125, x2, 170, fill=fill,
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, 147, text=category,
                                    fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                                    tags="frame")
            self.canvas.create_text(330, 190,
                                    text="SELECT AN ITEM TO PREVIEW IT BEFORE BUYING",
                                    fill="#c2c7b9", font=("Segoe UI", 9, "bold"),
                                    tags="frame")

            category = categories[self.customize_category]
        for index, (name, cost, color) in enumerate(COSMETIC_ITEMS[category]):
            y1 = 210 + index * 70
            y2 = y1 + 58
            fill = "#74563d" if index == self.customize_item else "#35443d"
            self.canvas.create_rectangle(60, y1, 600, y2, fill=fill,
                                         outline="#d4bd91" if index == self.customize_item
                                         else "#b7a982", width=1, tags="frame")
            if color:
                self.canvas.create_oval(76, y1 + 17, 100, y1 + 41,
                                        fill=color, outline="#d4bd91", tags="frame")
            self.canvas.create_text(112, y1 + 20, text=name,
                                    anchor="w", fill="#f0dfb8",
                                    font=("Segoe UI", 11, "bold"), tags="frame")
            if name in self.owned_cosmetics[category]:
                status = "EQUIPPED" if name == self.equipped_cosmetics[category] else "EQUIP"
            else:
                status = f"BUY  {cost}"
            self.canvas.create_text(575, y1 + 30, text=status,
                                    anchor="e", fill="#e5c874",
                                    font=("Segoe UI", 10, "bold"), tags="frame")

        selected_name, selected_cost, _ = COSMETIC_ITEMS[category][self.customize_item]
        preview_appearance = self.equipped_cosmetics.copy()
        preview_appearance[category] = selected_name
        self.canvas.create_text(770, 233, text="PREVIEW",
                                fill="#d8c58f", font=("Segoe UI", 11, "bold"),
                                tags="frame")
        self.draw_entity(770, 340, 42, "#72a2ad", "#d5d9c0",
                         (1, 0), "scout", preview_appearance)
        self.canvas.create_text(770, 410, text=f"{category}: {selected_name}",
                                width=290, fill="#e5c874",
                                font=("Segoe UI", 10, "bold"), tags="frame")
        equipped = ", ".join(
            self.equipped_cosmetics[category] for category in categories
        )
        self.canvas.create_text(770, 435, text=f"Equipped: {equipped}", width=290,
                                fill="#c2c7b9", font=("Segoe UI", 9),
                                tags="frame")
        if selected_name in self.owned_cosmetics[category]:
            action_label = "EQUIPPED" if selected_name == self.equipped_cosmetics[category] else "EQUIP ITEM"
        else:
            action_label = f"BUY  {selected_cost} COINS"
        self.canvas.create_rectangle(60, 505, 600, 545, fill="#53634d",
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(330, 525, text=action_label,
                                fill="#fff1d2", font=("Segoe UI", 11, "bold"),
                                tags="frame")
        self.canvas.create_rectangle(70, 550, 260, 600, fill="#53634d",
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(165, 575, text="BACK TO PAUSE",
                                fill="#fff1d2", font=("Segoe UI", 10, "bold"),
                                tags="frame")
        self.canvas.create_rectangle(640, 505, 920, 545, fill="#35443d",
                                     outline="#d4bd91", width=1, tags="frame")
        equipped_special = (
            MARKET_WEAPONS[self.equipped_special_weapon]["name"]
            if self.equipped_special_weapon is not None else "NONE"
        )
        self.canvas.create_text(
            780, 525, text=f"SPECIAL WEAPONS  -  {equipped_special}",
            fill="#8ee5f0", font=("Segoe UI", 9, "bold"), tags="frame"
        )
        if time.monotonic() < self.message_until:
            self.canvas.create_text(770, 470, text=self.message,
                                    fill="#e5c874", font=("Segoe UI", 10, "bold"),
                                    tags="frame")

    def draw_special_loadout(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", tags="frame")
        c.create_text(WIDTH / 2, 40, text="SPECIAL LOADOUT",
                      fill="#f0d7c5", font=("Segoe UI", 25, "bold"), tags="frame")
        for x1, x2, tab, label in (
                (180, 460, "weapons", "SPECIAL WEAPONS"),
                (500, 780, "skills", "BOSS SKILLS")):
            selected = self.special_loadout_tab == tab
            c.create_rectangle(
                x1, 90, x2, 120,
                fill="#74563d" if selected else "#35443d",
                outline="#d4bd91", width=1, tags="frame"
            )
            c.create_text((x1 + x2) / 2, 105, text=label,
                          fill="#fff1d2", font=("Segoe UI", 9, "bold"),
                          tags="frame")

        pages = 1
        if self.special_loadout_tab == "skills":
            c.create_text(
                WIDTH / 2, 78,
                text=f"EQUIP UP TO {MAX_ABILITIES}  |  "
                     f"{len(self.equipped_abilities)}/{MAX_ABILITIES} EQUIPPED  |  "
                     f"{len(self.skill_copies)} SKILL COPIES",
                fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame"
            )
            if not self.unlocked_abilities:
                c.create_text(WIDTH / 2, 280,
                              text="NO BOSS SKILLS LEARNED YET",
                              fill="#c2c7b9", font=("Segoe UI", 16, "bold"),
                              tags="frame")
            for row, skill in enumerate(self.unlocked_abilities):
                y = 128 + row * 54
                is_equipped = skill in self.equipped_abilities
                c.create_rectangle(
                    52, y, 908, y + 46,
                    fill="#46523e" if is_equipped else "#29332f",
                    outline="#e5c874" if is_equipped else "#69766b",
                    width=2 if is_equipped else 1, tags="frame"
                )
                c.create_text(
                    72, y + 15, anchor="w", text=skill[0],
                    fill="#f0d7c5", font=("Segoe UI", 10, "bold"),
                    tags="frame"
                )
                c.create_text(
                    72, y + 33, anchor="w", text=skill[2],
                    fill="#c2c7b9", font=("Segoe UI", 8), tags="frame"
                )
                c.create_text(
                    885, y + 23, anchor="e",
                    text=(
                        f"COPIES {sum(copy[0] == skill[0] for copy in self.skill_copies)}"
                        f"  |  {'EQUIPPED' if is_equipped else 'CLICK TO EQUIP'}"
                    ),
                    fill="#e5c874", font=("Segoe UI", 9, "bold"), tags="frame"
                )
            controls = (
                (40, 230, "BACK"),
                (365, 620, "SELECT UP TO FIVE SKILLS"),
                (700, 920, ""),
            )
            c.create_text(WIDTH / 2, 630,
                          text="EQUIPPED SKILLS USE HOTKEYS 1-5 IN THE ORDER SHOWN",
                          fill="#aeb6aa", font=("Segoe UI", 9, "bold"),
                          tags="frame")
        else:
            equipped = (
                MARKET_WEAPONS[self.equipped_special_weapon]
                if self.equipped_special_weapon is not None else None
            )
            equipped_label = (
                f'EQUIPPED: {equipped["name"]} [{equipped["type"]}]'
                if equipped else "EQUIPPED: NONE"
            )
            c.create_text(
                WIDTH / 2, 78,
                text=f"{equipped_label}  |  {len(self.owned_special_weapons)} OWNED",
                fill="#8ee5f0", font=("Segoe UI", 11, "bold"), tags="frame"
            )
            per_page = 10
            pages = max(
                1, (len(self.owned_special_weapons) + per_page - 1) // per_page
            )
            self.special_loadout_page = min(self.special_loadout_page, pages - 1)
            start = self.special_loadout_page * per_page
            visible = self.owned_special_weapons[start:start + per_page]
            if not visible:
                c.create_text(WIDTH / 2, 280,
                              text="NO SPECIAL WEAPONS OWNED YET",
                              fill="#c2c7b9", font=("Segoe UI", 16, "bold"),
                              tags="frame")
                c.create_text(
                    WIDTH / 2, 320,
                    text="Reach player level 15 to unlock the marketplace from floor progression.",
                    fill="#929c93", font=("Segoe UI", 10), tags="frame"
                )
            for row, weapon_id in enumerate(visible):
                weapon = MARKET_WEAPONS[weapon_id]
                y = 125 + row * 42
                is_equipped = weapon_id == self.equipped_special_weapon
                c.create_rectangle(
                    52, y, 908, y + 36,
                    fill="#46523e" if is_equipped else "#29332f",
                    outline="#e5c874" if is_equipped else "#69766b",
                    width=2 if is_equipped else 1, tags="frame"
                )
                c.create_text(
                    72, y + 18, anchor="w",
                    text=f'{weapon["id"] + 1:04d}  {weapon["name"]}  [{weapon["type"]}]',
                    fill="#f0d7c5", font=("Segoe UI", 10, "bold"), tags="frame"
                )
                c.create_text(
                    885, y + 18, anchor="e",
                    text="EQUIPPED" if is_equipped else "CLICK TO EQUIP",
                    fill="#e5c874", font=("Segoe UI", 9, "bold"), tags="frame"
                )
            controls = (
                (40, 230, "BACK"),
                (365, 620, f"PAGE {self.special_loadout_page + 1}/{pages}  -  PREVIOUS"),
                (700, 920, "NEXT PAGE"),
            )
            c.create_text(
                WIDTH / 2, 630,
                text="SPECIAL WEAPONS ARE SEPARATE FROM NORMAL CHARACTER GUN COSMETICS",
                fill="#aeb6aa", font=("Segoe UI", 9, "bold"), tags="frame"
            )
        for x1, x2, label in controls:
            if not label:
                continue
            c.create_rectangle(x1, 565, x2, 605, fill="#35443d",
                               outline="#d4bd91", tags="frame")
            c.create_text((x1 + x2) / 2, 585, text=label,
                          fill="#fff1d2", font=("Segoe UI", 9, "bold"), tags="frame")
        if time.monotonic() < self.message_until:
            c.create_text(WIDTH / 2, 530, text=self.message,
                          fill="#e5c874", font=("Segoe UI", 10, "bold"), tags="frame")

    def draw_paused(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 220, text="PAUSED",
                                fill="#e8d9b8", font=("Segoe UI", 31, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 276, text="The frontline is waiting.",
                                fill="#c2c7b9", font=("Segoe UI", 12), tags="frame")
        for y1, y2, label in ((320, 370, "RESUME  -  ESC"),
                              (390, 440, "CHANGE CHARACTER  -  C"),
                              (460, 510, "FLOOR PROGRESSION  -  P"),
                              (530, 580, "RESTART FLOOR")):
            self.canvas.create_rectangle(370, y1, 590, y2, fill="#53634d",
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text(WIDTH / 2, (y1 + y2) / 2, text=label,
                                    fill="#fff1d2", font=("Segoe UI", 11, "bold"),
                                    tags="frame")

    def draw_shop(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 135, text="FIELD UPGRADES",
                                fill="#f0d7c5", font=("Segoe UI", 28, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 180, text=f"AVAILABLE COINS: {self.coins}",
                                fill="#e5c874", font=("Segoe UI", 15, "bold"),
                                tags="frame")
        rows = (
            (self.weapon_upgrade, 15 + self.weapon_upgrade * 12,
             "WEAPON DAMAGE", "Increase every shot's damage."),
            (self.skill_upgrade, 25 + self.skill_upgrade * 15,
             "BOSS SKILL POWER + AREA", "Make acquired skills stronger and wider."),
            (self.health_upgrade, 20 + self.health_upgrade * 12,
             "MAX HEALTH", "Gain 25 maximum HP and heal 25."),
        )
        for i, (level, cost, title, description) in enumerate(rows):
            y = 220 + i * 72
            self.canvas.create_rectangle(180, y, 780, y + 60, fill="#35443d",
                                         outline="#b7a982", width=2, tags="frame")
            self.canvas.create_text(205, y + 17, text=f"{title}  LV {level}",
                                    anchor="w", fill="#f0dfb8",
                                    font=("Segoe UI", 12, "bold"), tags="frame")
            self.canvas.create_text(205, y + 42, text=description,
                                    anchor="w", fill="#c2c7b9",
                                    font=("Segoe UI", 9), tags="frame")
            self.canvas.create_text(745, y + 30, text=f"BUY  {cost}",
                                    anchor="e", fill="#e5c874",
                                    font=("Segoe UI", 11, "bold"), tags="frame")
        self.canvas.create_text(WIDTH / 2, 465, text="CLICK AN UPGRADE  |  ESC TO RETURN",
                                fill="#d0d4c2", font=("Segoe UI", 11, "bold"),
                                tags="frame")
        if time.monotonic() < self.message_until:
            self.canvas.create_text(WIDTH / 2, 500, text=self.message,
                                    fill="#e5c874", font=("Segoe UI", 11, "bold"),
                                    tags="frame")

    def draw_region_map(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 155, text="CHOOSE YOUR TERRAIN",
                                fill="#f0d7c5", font=("Segoe UI", 27, "bold"),
                                tags="frame")
        self.canvas.create_text(WIDTH / 2, 205,
                                text="Travel is always your choice. Click a region to move there.",
                                fill="#c2c7b9", font=("Segoe UI", 11), tags="frame")
        for i, region in enumerate(REGIONS):
            col = i % 4
            x1 = 70 + col * 210
            x2 = x1 + 190
            y1, y2 = 270, 395
            color = region[1]
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color,
                                         outline="#d4bd91", width=2, tags="frame")
            self.canvas.create_text((x1 + x2) / 2, y1 + 38, text=region[0],
                                    fill="#fff1d2", font=("Segoe UI", 12, "bold"),
                                    tags="frame")
            status = "CURRENT" if i == self.region else (
                "CLAIMED" if self.territories[i] else "UNCLAIMED"
            )
            self.canvas.create_text((x1 + x2) / 2, y1 + 82, text=status,
                                    fill="#e5c874", font=("Segoe UI", 10, "bold"),
                                    tags="frame")
            self.canvas.create_text((x1 + x2) / 2, y2 - 18, text="CLICK TO TRAVEL",
                                    fill="#f5eee0", font=("Segoe UI", 9), tags="frame")
        self.canvas.create_text(WIDTH / 2, 450,
                                text="ESC TO RETURN  |  M OPENS THIS MAP DURING BATTLES",
                                fill="#d0d4c2", font=("Segoe UI", 11, "bold"),
                                tags="frame")

    def draw_overlay(self, title, subtitle, action):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", stipple="gray50",
                                     outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 220, text=title, fill="#e8d9b8",
                                font=("Segoe UI", 31, "bold"), tags="frame")
        self.canvas.create_text(WIDTH / 2, 276, text=subtitle, fill="#c2c7b9",
                                font=("Segoe UI", 12), tags="frame")
        self.rect(WIDTH / 2 - 115, 331, WIDTH / 2 + 115, 381, "#a0784d", "#d4bd91")
        self.canvas.create_text(WIDTH / 2, 356, text=action, fill="#fff1d2",
                                font=("Segoe UI", 13, "bold"), tags="frame")
        self.canvas.create_text(WIDTH / 2, 430,
                                text="WASD / ARROWS MOVE   SPACE / CLICK SHOOT   1-5 CAST SKILLS   RIGHT-CLICK TO AIM   ESC PAUSE",
                                fill="#b7c1b4", font=("Segoe UI", 10, "bold"), tags="frame")
        self.canvas.create_text(WIDTH / 2, 461,
                                text="Defeat the warlords, claim new territories, and take their power.",
                                fill="#9ea99d", font=("Segoe UI", 10), tags="frame")

    def draw_main_menu(self):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718",
                                     stipple="gray50", outline="", tags="frame")
        self.canvas.create_text(WIDTH / 2, 220, text="WELCOME TO THE GAME!",
                                fill="#e8d9b8", font=("Segoe UI", 31, "bold"),
                                tags="frame")
        self.canvas.create_text(
            WIDTH / 2, 276,
            text="DEFEAT MONSTERS, CLAIM TERRITORIES, AND TAKE THEIR POWER",
            fill="#c2c7b9", font=("Segoe UI", 12), tags="frame"
        )
        has_save = self.has_save()
        self.canvas.create_rectangle(165, 331, 465, 381,
                                     fill="#a0784d" if has_save else "#53634d",
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(
            315, 356,
            text="CONTINUE  -  ENTER" if has_save else "DEPLOY  -  ENTER",
            fill="#fff1d2", font=("Segoe UI", 13, "bold"), tags="frame"
        )
        self.canvas.create_rectangle(495, 331, 795, 381, fill="#35443d",
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(645, 356, text="FLOOR PROGRESSION",
                                fill="#fff1d2", font=("Segoe UI", 11, "bold"),
                                tags="frame")
        if has_save:
            self.canvas.create_rectangle(165, 398, 465, 448, fill="#35443d",
                                         outline="#d4bd91", width=1, tags="frame")
            self.canvas.create_text(315, 423, text="NEW GAME",
                                    fill="#fff1d2", font=("Segoe UI", 11, "bold"),
                                    tags="frame")
        self.canvas.create_rectangle(495, 398, 795, 448, fill="#35443d",
                                     outline="#d4bd91", width=1, tags="frame")
        self.canvas.create_text(
            645, 423, text=f"SPECIAL WEAPONS  ({len(self.owned_special_weapons)} OWNED)",
            fill="#8ee5f0", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        self.canvas.create_text(
            WIDTH / 2, 482,
            text="WASD / ARROWS MOVE   SPACE / CLICK SHOOT   1-5 CAST SKILLS   ESC PAUSE",
            fill="#b7c1b4", font=("Segoe UI", 10, "bold"), tags="frame"
        )
        self.canvas.create_text(
            WIDTH / 2, 510,
            text="AUTO-SAVES EVERY 10 SECONDS  |  CTRL+SHIFT+S SAVES NOW",
            fill="#9ea99d", font=("Segoe UI", 9, "bold"), tags="frame"
        )
        if time.monotonic() < self.save_notice_until:
            self.canvas.create_text(WIDTH / 2, 550, text=self.save_notice,
                                    fill="#e5c874", font=("Segoe UI", 10, "bold"),
                                    tags="frame")

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.05)
        self.last_tick = now
        self.canvas.delete("frame")
        self.update_flow(now)
        if self.state == "tower_gate":
            self.update_tower_gate(dt)
        if self.state in ("playing", "boss_skill", "post_boss"):
            self.update(dt, now)
        self.autosave_if_due(now)
        if self.state in ("playing", "paused", "gameover", "region_map",
                          "boss_cutscene", "boss_dialogue", "boss_skill",
                          "minion_reveal", "kidnapper_reveal", "post_boss",
                          "auto_aim_prompt"):
            self.draw_game(now)
        else:
            self.canvas.delete("frame")
        if self.state == "menu":
            self.draw_main_menu()
        elif self.state == "tower_exterior":
            self.draw_tower_exterior()
        elif self.state == "opening_cutscene":
            self.draw_opening_cutscene(now)
        elif self.state == "tower_gate":
            self.draw_tower_gate()
            if now < self.message_until:
                self.canvas.create_text(WIDTH / 2, HEIGHT - 48, text=self.message,
                                        fill="#f0d99f",
                                        font=("Segoe UI", 10, "bold"),
                                        tags="frame")
        elif self.state == "quest_select":
            self.draw_quest_select()
        elif self.state == "minion_difficulty":
            self.draw_minion_difficulty()
        elif self.state == "stage_intro":
            self.draw_stage_intro()
        elif self.state == "boss_warning":
            self.draw_boss_warning(now)
        elif self.state == "post_boss":
            self.draw_post_boss(now)
        elif self.state == "minion_reveal":
            self.draw_minion_reveal(now)
        elif self.state == "kidnapper_reveal":
            self.draw_kidnapper_reveal(now)
        elif self.state == "shop":
            self.draw_shop()
        elif self.state == "region_map":
            self.draw_region_map()
        elif self.state == "floor_progression":
            self.draw_floor_progression()
        elif self.state == "marketplace":
            self.draw_marketplace()
        elif self.state == "side_quests":
            self.draw_side_quests()
        elif self.state == "purchase_confirmation":
            self.draw_purchase_confirmation()
        elif self.state == "skill_market":
            self.draw_skill_market()
        elif self.state == "weapon_preview":
            self.draw_weapon_preview()
        elif self.state == "skill_forge":
            self.draw_skill_forge()
        elif self.state == "special_loadout":
            self.draw_special_loadout()
        elif self.state == "paused":
            self.draw_paused()
        elif self.state == "character":
            self.draw_character_customization()
        elif self.state == "auto_aim_prompt":
            self.draw_auto_aim_prompt()
        elif self.state == "cosmetic_chest":
            self.draw_cosmetic_chest()
        elif self.state == "gameover":
            self.draw_overlay(f"FALLEN  -  WAVE {self.wave}",
                              f"You defeated {self.kills} enemies and reached level {self.player['level']}.",
                              "REDEPLOY  -  ENTER")
        elif self.state == "victory":
            self.draw_victory()
        self.root.after(33, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    BattlefieldRPG(root)
    root.mainloop()