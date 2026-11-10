import math
import random
import time
import tkinter as tk


WIDTH = 960
HEIGHT = 640
ARENA = (24, 92, WIDTH - 24, HEIGHT - 48)


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
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)

        self.keys = set()
        self.decor = self.make_decor()
        self.state = "menu"
        self.last_tick = time.monotonic()
        self.new_game()
        self.state = "menu"
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
        }
        self.enemies = []
        self.pickups = []
        self.wave = 1
        self.wave_left = 5
        self.wave_pause = 0
        self.kills = 0
        self.message = ""
        self.message_until = 0
        self.spawn_wave()

    def spawn_wave(self):
        self.wave_left = 4 + self.wave * 2
        self.message = "WAVE " + str(self.wave) + "  -  HOLD THE LINE"
        self.message_until = time.monotonic() + 2.2

    def on_click(self, event):
        if self.state in ("menu", "gameover"):
            self.start_game()
        elif self.state == "paused":
            self.state = "playing"
            self.last_tick = time.monotonic()

    def on_key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key in ("return", "space") and self.state in ("menu", "gameover"):
            self.start_game()
        elif key == "escape":
            if self.state == "playing":
                self.state = "paused"
                self.keys.clear()
            elif self.state == "paused":
                self.state = "playing"
                self.last_tick = time.monotonic()

    def on_key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def start_game(self):
        self.new_game()
        self.state = "playing"
        self.keys.clear()
        self.last_tick = time.monotonic()
        self.canvas.focus_set()

    def spawn_enemy(self):
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

    def update(self, dt, now):
        p = self.player
        dx = (("d" in self.keys or "right" in self.keys) -
              ("a" in self.keys or "left" in self.keys))
        dy = (("s" in self.keys or "down" in self.keys) -
              ("w" in self.keys or "up" in self.keys))
        if dx or dy:
            length = math.hypot(dx, dy)
            dx, dy = dx / length, dy / length
            p["face"] = (dx, dy)
            p["x"] += dx * p["speed"] * dt
            p["y"] += dy * p["speed"] * dt
            p["x"] = max(ARENA[0] + 16, min(ARENA[2] - 16, p["x"]))
            p["y"] = max(ARENA[1] + 16, min(ARENA[3] - 16, p["y"]))

        if "space" in self.keys and now >= p["attack_ready"]:
            self.attack(now)

        if self.wave_left > 0 and len(self.enemies) < 5 + self.wave:
            self.spawn_enemy()

        for enemy in self.enemies[:]:
            ex, ey = p["x"] - enemy["x"], p["y"] - enemy["y"]
            distance = max(1, math.hypot(ex, ey))
            if distance > enemy["radius"] + 20:
                enemy["x"] += ex / distance * enemy["speed"] * dt
                enemy["y"] += ey / distance * enemy["speed"] * dt
            elif now >= enemy["attack_ready"] and now >= p["hurt_until"]:
                p["hp"] -= enemy["damage"]
                p["hurt_until"] = now + 0.58
                enemy["attack_ready"] = now + 0.95
                self.message = "UNDER ATTACK!"
                self.message_until = now + 0.65
                if p["hp"] <= 0:
                    p["hp"] = 0
                    self.state = "gameover"
                    self.keys.clear()
                    return

        for pickup in self.pickups[:]:
            if math.hypot(p["x"] - pickup["x"], p["y"] - pickup["y"]) < 24:
                p["hp"] = min(p["max_hp"], p["hp"] + 30)
                self.pickups.remove(pickup)
                self.message = "FIELD MEDKIT  +30 HP"
                self.message_until = now + 1.3

        if not self.enemies and self.wave_left == 0:
            if self.wave_pause == 0:
                self.wave_pause = now + 1.8
                self.message = "AREA SECURED"
                self.message_until = self.wave_pause
            elif now >= self.wave_pause:
                self.wave += 1
                self.wave_pause = 0
                self.spawn_wave()

    def attack(self, now):
        p = self.player
        p["attack_ready"] = now + 0.38
        p["attack_until"] = now + 0.18
        fx, fy = p["face"]
        for enemy in self.enemies[:]:
            ex, ey = enemy["x"] - p["x"], enemy["y"] - p["y"]
            distance = math.hypot(ex, ey)
            if distance <= 66 + enemy["radius"] and (
                distance < 1 or (ex * fx + ey * fy) / distance > 0.12
            ):
                enemy["hp"] -= 34 + (p["level"] - 1) * 7
                enemy["hurt_until"] = now + 0.12
                if enemy["hp"] <= 0:
                    self.enemies.remove(enemy)
                    self.kills += 1
                    p["xp"] += enemy["xp"]
                    if random.random() < 0.16:
                        self.pickups.append({"x": enemy["x"], "y": enemy["y"]})
                    self.check_level_up()

    def check_level_up(self):
        p = self.player
        while p["xp"] >= p["next_xp"]:
            p["xp"] -= p["next_xp"]
            p["level"] += 1
            p["next_xp"] = int(p["next_xp"] * 1.45)
            p["max_hp"] += 16
            p["hp"] = min(p["max_hp"], p["hp"] + 42)
            p["speed"] += 3
            self.message = "LEVEL UP!  LEVEL " + str(p["level"])
            self.message_until = time.monotonic() + 2

    def rect(self, x1, y1, x2, y2, color, outline=""):
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=color, outline=outline, width=1
        )

    def draw_background(self):
        c = self.canvas
        c.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#171d20", outline="")
        self.rect(*ARENA, "#39453b", "#7d8065")
        for x in range(ARENA[0] + 12, ARENA[2], 48):
            c.create_line(x, ARENA[1], x, ARENA[3], fill="#414b3e")
        for y in range(ARENA[1] + 12, ARENA[3], 48):
            c.create_line(ARENA[0], y, ARENA[2], y, fill="#414b3e")
        for x, y, kind, size in self.decor:
            if kind == "crater":
                c.create_oval(x - size, y - size * 0.45, x + size, y + size * 0.45,
                              fill="#303a32", outline="#485044")
            elif kind == "stone":
                c.create_oval(x - size / 2, y - size / 3, x + size / 2, y + size / 3,
                              fill="#626356", outline="")
            else:
                c.create_line(x, y, x + size, y - size // 2, fill="#89906b", width=2)
        self.draw_barricade(ARENA[0] + 105, ARENA[1] + 55, "#71807a")
        self.draw_barricade(ARENA[2] - 170, ARENA[3] - 68, "#806d56")
        self.canvas.create_line(ARENA[0] + 36, ARENA[1] + 28,
                                ARENA[0] + 36, ARENA[1] + 66, fill="#c6c1a6", width=2)
        self.canvas.create_polygon(
            ARENA[0] + 38, ARENA[1] + 29, ARENA[0] + 64, ARENA[1] + 36,
            ARENA[0] + 38, ARENA[1] + 44, fill="#708ea0", outline=""
        )
        self.canvas.create_line(ARENA[2] - 38, ARENA[3] - 68,
                                ARENA[2] - 38, ARENA[3] - 30, fill="#c6c1a6", width=2)
        self.canvas.create_polygon(
            ARENA[2] - 36, ARENA[3] - 67, ARENA[2] - 62, ARENA[3] - 60,
            ARENA[2] - 36, ARENA[3] - 52, fill="#a36a57", outline=""
        )

    def draw_barricade(self, x, y, color):
        for i in range(4):
            self.rect(x + i * 18, y + (i % 2) * 5, x + 17 + i * 18, y + 9 + (i % 2) * 5,
                      color, "#252c28")
        self.rect(x + 12, y + 12, x + 67, y + 18, "#4b5148", "#252c28")

    def draw_bar(self, x, y, width, ratio, color, height=6):
        self.rect(x, y, x + width, y + height, "#252a29")
        if ratio > 0:
            self.rect(x, y, x + width * max(0, min(1, ratio)), y + height, color)

    def draw_entity(self, x, y, radius, body, outline, direction=(0, 0)):
        c = self.canvas
        c.create_oval(x - radius, y - radius + 4, x + radius, y + radius + 4,
                      fill="#252b27", outline="")
        c.create_oval(x - radius, y - radius, x + radius, y + radius,
                      fill=body, outline=outline, width=2)
        c.create_oval(x - radius * 0.52, y - radius * 0.54,
                      x - radius * 0.12, y - radius * 0.12, fill="#ffffff", outline="")
        if direction != (0, 0):
            c.create_line(x, y, x + direction[0] * radius * 0.65,
                          y + direction[1] * radius * 0.65, fill="#f3e7c9", width=2)

    def draw_game(self, now):
        self.draw_background()
        p = self.player
        self.rect(0, 0, WIDTH, 80, "#20292b")
        self.canvas.create_text(24, 19, text="ASHEN FRONT", anchor="w",
                                fill="#e6d9ba", font=("Segoe UI", 13, "bold"))
        self.canvas.create_text(24, 48, text=f"LV {p['level']}  |  WAVE {self.wave}",
                                anchor="w", fill="#c6c5b4", font=("Segoe UI", 10, "bold"))
        self.draw_bar(180, 20, 200, p["hp"] / p["max_hp"], "#c4584e", 13)
        self.canvas.create_text(180, 43, text=f"HP  {p['hp']} / {p['max_hp']}",
                                anchor="w", fill="#e7d8c8", font=("Segoe UI", 9))
        self.draw_bar(180, 57, 200, p["xp"] / p["next_xp"], "#d2a64e", 7)
        self.canvas.create_text(408, 23, text=f"XP  {p['xp']} / {p['next_xp']}",
                                anchor="w", fill="#d8c58f", font=("Segoe UI", 9))
        self.canvas.create_text(WIDTH - 24, 24, text=f"DEFEATED  {self.kills}",
                                anchor="e", fill="#c6c5b4", font=("Segoe UI", 10, "bold"))

        for pickup in self.pickups:
            x, y = pickup["x"], pickup["y"]
            self.canvas.create_oval(x - 9, y - 9, x + 9, y + 9,
                                    fill="#83b581", outline="#d9e3b2", width=2)
            self.canvas.create_text(x, y, text="+", fill="#f3f5da",
                                    font=("Segoe UI", 12, "bold"))

        for enemy in self.enemies:
            color = {"raider": "#bd6555", "ranger": "#ce9c51", "brute": "#875b72"}[enemy["kind"]]
            if now < enemy["hurt_until"]:
                color = "#f4e3c9"
            self.draw_entity(enemy["x"], enemy["y"], enemy["radius"], color, "#352c2b")
            self.draw_bar(enemy["x"] - 16, enemy["y"] - enemy["radius"] - 11, 32,
                          enemy["hp"] / enemy["max_hp"], "#d57462", 4)

        facing = p["face"]
        self.draw_entity(p["x"], p["y"], 15, "#72a2ad", "#d5d9c0", facing)
        if now < p["hurt_until"] and int(now * 18) % 2 == 0:
            self.canvas.create_oval(p["x"] - 20, p["y"] - 20, p["x"] + 20, p["y"] + 20,
                                    outline="#f2d5a5", width=2)
        if now < p["attack_until"]:
            fx, fy = facing
            self.canvas.create_arc(
                p["x"] - 51, p["y"] - 51, p["x"] + 51, p["y"] + 51,
                start=-math.degrees(math.atan2(fy, fx)) - 40, extent=80,
                style=tk.ARC, outline="#f3dc9c", width=4
            )

        if now < self.message_until:
            self.canvas.create_text(WIDTH / 2, 103, text=self.message,
                                    fill="#f0d99f", font=("Segoe UI", 12, "bold"))
        self.canvas.create_text(WIDTH / 2, HEIGHT - 22,
                                text="WASD / ARROWS  MOVE     SPACE  ATTACK     ESC  PAUSE",
                                fill="#b9c1ac", font=("Segoe UI", 9, "bold"))

    def draw_overlay(self, title, subtitle, action):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#101718", stipple="gray50",
                                     outline="")
        self.canvas.create_text(WIDTH / 2, 220, text=title, fill="#e8d9b8",
                                font=("Segoe UI", 31, "bold"))
        self.canvas.create_text(WIDTH / 2, 276, text=subtitle, fill="#c2c7b9",
                                font=("Segoe UI", 12))
        self.rect(WIDTH / 2 - 115, 331, WIDTH / 2 + 115, 381, "#a0784d", "#d4bd91")
        self.canvas.create_text(WIDTH / 2, 356, text=action, fill="#fff1d2",
                                font=("Segoe UI", 13, "bold"))
        self.canvas.create_text(WIDTH / 2, 430,
                                text="WASD / ARROWS  MOVE     SPACE  ATTACK     ESC  PAUSE",
                                fill="#b7c1b4", font=("Segoe UI", 10, "bold"))
        self.canvas.create_text(WIDTH / 2, 461,
                                text="Defeat raiders, earn XP, level up, and collect field medkits.",
                                fill="#9ea99d", font=("Segoe UI", 10))

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.05)
        self.last_tick = now
        if self.state == "playing":
            self.update(dt, now)
        if self.state in ("playing", "paused", "gameover"):
            self.draw_game(now)
        else:
            self.canvas.delete("all")
            self.draw_background()
            self.draw_overlay("ASHEN FRONT", "A lone scout. An endless frontline.", "DEPLOY  -  ENTER")
        if self.state == "paused":
            self.draw_overlay("PAUSED", "The frontline is waiting.", "RESUME  -  ESC")
        elif self.state == "gameover":
            self.draw_overlay(f"FALLEN  -  WAVE {self.wave}",
                              f"You defeated {self.kills} enemies and reached level {self.player['level']}.",
                              "REDEPLOY  -  ENTER")
        self.root.after(16, self.tick)


if __name__ == "__main__":
    root = tk.Tk()
    BattlefieldRPG(root)
    root.mainloop()
