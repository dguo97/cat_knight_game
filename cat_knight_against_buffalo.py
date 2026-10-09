"""
Cat Knight Against Buffalo  --  Python / pygame version

Automatically converted from the Scratch 1.x project "Cat_Knight_Against_Buffalo.sb".
Every Scratch script is a Python generator; `yield` marks where Scratch would
switch to another script (end of a loop pass, wait, wait-until).  The engine that
runs them lives in scratch_runtime.py.

Run:   python cat_knight_against_buffalo.py        (Esc or closing the window quits)
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # find scratch_runtime.py next to this file
from scratch_runtime import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

stage = Stage("Cat Knight Against Buffalo")
V = stage.vars          # global variables
S = stage.sprites       # sprites by their Scratch name

# ---- variables (initial values stored in the project; the green-flag script resets them)
V['laser2'] = 0
V['laser1'] = 0
V['SPEED'] = 0.49999999999999933
V['Y1'] = 0
V['1 POWER'] = 1
V['T'] = 0
V['LASER22'] = 0
V['LASER21'] = 0
V['plane2'] = 0
V['PQ'] = 0
V['PLANE'] = 0
V['2 BLOOD'] = 5584.7815463724055
V['1 TIME'] = -0.599999999999973
V['DIRECTION'] = 262
V['direction 1'] = 12
V['OZ'] = 0
V['Chaos'] = 0
V['hit_scale'] = 1      # how hard buffalo bumps drain TIME (Easy mode lowers it)
V['buf_speed'] = 1      # buffalo speed multiplier (Easy mode lowers it)

# ---- FIX: shared flight loop for plane shots.  It always ends (step cap), also when the edge
# fence pins the shot, stops right after a hit, and ends if the shot touches the cat.
def fly_shot(shot, speed, damage):
    for _ in range(int(700 / speed) + 1):
        px, py = shot.x, shot.y
        shot.move(speed)
        if shot.touching(S['角色2']):
            V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -damage)
            return
        if shot.touching(S['角色1']):
            return
        if abs(shot.x) > 239 or abs(shot.y) > 179 or abs(shot.x - px) + abs(shot.y - py) < 1:
            return
        yield

# ---- REFACTOR: shared code for the cat's four arrow-key walk scripts
def cat_walk(cat, heading, key):
    """Walk in `heading` while `key` is held; speed and bump damage depend on the cat's form."""
    cat.set_heading(heading)
    while stage.key_pressed(key):
        if cat.costume_index == 1:
            cat.move(3)
            if cat.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -3)
                cat.move(-2.5)
        if cat.costume_index == 2:
            cat.move(5)
            if cat.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -2)
                cat.move(-4.5)
        if cat.costume_index == 3:
            for _ in range(rep(5)):
                cat.move(2)
                if cat.touching(S['角色2']):
                    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -5)
                    cat.move(-1.5)
                yield
        if cat.costume_index == 4:
            cat.move(10)
            if cat.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -50)
        yield

# ---- REFACTOR: shared code for the five buffalo-arrow scripts (角色91, 92, 94, 95, 88)
ARROW_BLOCKERS = ['角色3', '角色67', '角色69', '角色71', '角色72', '角色101', '角色99', '角色100', '角色102']

def arrow_blocked(arrow):
    return any(arrow.touching(S[n]) for n in ARROW_BLOCKERS)

def arrow_hit_blocker(arrow):
    """The arrow ran into one of the cat's attacks.  Returns True if the arrow is destroyed for good."""
    if arrow.touching(S['角色102']) or arrow.touching(S['角色99']):     # the form-4 swarm pixelates it
        for _ in range(rep(200)):
            arrow.change_effect('pixelate', 1)
            yield
        arrow.hide()
        return True
    arrow.goto_sprite(S['角色2'])                                       # otherwise it goes back to the buffalo
    arrow.hide()
    return False

def arrow_cycle(arrow, effect=None, clear_fx=False):
    """One volley of an arrow: shoot out from the buffalo, then wander around and hurt the cat on contact.
    `effect` is the visual effect it spins through while flying out; returns True if it was destroyed."""
    if clear_fx:
        arrow.clear_effects()
    yield from wait(stage, rand(0, 5))
    arrow.show()
    arrow.goto_sprite(S['角色2'])
    arrow.set_heading(0)
    if (not arrow.touching(S['角色71'])) and (not arrow.touching(S['角色72'])):
        for _ in range(rep(20)):
            if effect:
                arrow.change_effect(effect, rand(1, 10))
            arrow.move(10)
            if arrow_blocked(arrow):
                if (yield from arrow_hit_blocker(arrow)):
                    return True
            yield
        arrow.set_heading(rand(-180, 180))
        for _ in range(rep(rand(30, 1000))):
            arrow.bounce_off_edge()
            arrow.move(rand(50, 5))
            arrow.turn(rand(0, 50))
            if arrow.touching(S['角色1']):
                arrow.hide()
                V['1 POWER'] = add(V.get('1 POWER', 0), -10 * V['hit_scale'])
                V['1 TIME'] = add(V.get('1 TIME', 0), -10 * V['hit_scale'])
            if arrow_blocked(arrow):
                if (yield from arrow_hit_blocker(arrow)):
                    return True
            yield
    arrow.hide()
    return False

# ---- difficulty ramp and fight statistics
RAGE_SPEEDUP = 0.6          # the buffalo is up to 60% faster when it is nearly out of blood
stats = {'start_blood': 10000}      # filled in a moment after the game starts (Easy mode changes it)

def rage():
    """0.0 at the start of the fight -> 1.0 when the buffalo is almost out of blood"""
    start = max(1, stats['start_blood'])
    return max(0.0, min(1.0, 1 - V['2 BLOOD'] / start))

def buf_pace():
    """buffalo speed multiplier: the mode's own setting, plus the speed-up as its blood drops"""
    return V['buf_speed'] * (1 + RAGE_SPEEDUP * rage())

# ---- held-key attacks (A shield, S sword, R heavy shield, E heavy sword)
HOLD_COST = {'a': 12, 's': 15, 'r': 5, 'e': 10}      # POWER used per second while the key is held
HOLD_TIME_COST = 0.25                                # TIME used per second while the key is held

def hold_attack(sprite, key, dx, dy, form4_only=False, min_start=5, on_touch=None):
    """The sprite follows the cat while `key` is held and drains POWER/TIME the whole time.
    It drops when POWER runs out and can't be raised again until the key is released."""
    cat = S['角色1']
    active = locked = False
    while True:
        want = stage.key_pressed(key) and (not form4_only or cat.costume_index == 4)
        if not want:
            active = locked = False
        elif not active and not locked and V['1 POWER'] >= min_start:
            active = True
        if active and V['1 POWER'] <= 0:
            active, locked = False, True
        if active:
            sprite.show()
            sprite.set_heading(cat.heading)
            side = -1 if cat.heading == -90 else 1
            sprite.goto(cat.x + side * dx, cat.y - dy)
            if on_touch and sprite.touching(S['角色2']):
                on_touch()
            V['1 POWER'] = max(0, V['1 POWER'] - HOLD_COST[key] / FPS)
            V['1 TIME'] = V['1 TIME'] - HOLD_TIME_COST / FPS
        else:
            sprite.hide()
        yield

def sword_hit():                 # S: damage depends on the cat's form
    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -10 * abs(S['角色1'].costume_index - 1.75) ** 0.5)

def heavy_sword_hit():           # E (form 4)
    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -200)

# ---- hint line: attacks you can't afford right now are greyed out
def hint_segments():
    grey, ok, no = (110, 110, 110), (20, 20, 20), (200, 200, 200)
    p = V['1 POWER']
    ready = S['角色2'].size == 100
    segs = [('F1 help   arrows move   1 2 3 form   ', grey)]
    for label, can in (('Z', p > 4), ('X', p > 9), ('F', p > 0 and ready), ('D', p > 9)):
        segs.append((label + ' ', ok if can else no))
    if S['角色1'].costume_index == 1:
        segs.append(('G ', ok if (p > 99 and ready) else no))
    segs.append(('SPACE', ok if p > 79 else no))
    segs.append((' attack', grey))
    return segs

# ===================================================================== stage scripts
stage_t = StageTarget(stage)

@stage.on_flag(stage_t)
def stage_script_1(self):
    if False: yield          # (makes this function a generator)
    V['T'] = 0
    V['1 POWER'] = 100
    V['2 BLOOD'] = 10000
    V['1 TIME'] = 180
    V['laser1'] = 0
    V['laser2'] = 0
    V['PLANE'] = 0
    V['plane2'] = 0
    V['SPEED'] = 2
    V['DIRECTION'] = 90
    V['LASER21'] = 0
    V['LASER22'] = 0
    V['PQ'] = 0
    V['OZ'] = 0
    V['Y1'] = 0
    while not (stage.key_pressed('p') and stage.key_pressed('q')):
        yield
    while True:
        yield from wait(stage, rand(0, 5) / (1 + rage()))       # arrows come more often as the buffalo weakens
        V['PQ'] = 1
        yield from wait(stage, rand(0, 10))
        V['PQ'] = 0
        yield

@stage.on_flag(stage_t)
def stage_script_2(self):
    if False: yield          # (makes this function a generator)
    while True:
        while not gt(V['1 POWER'], 99):
            yield from wait(stage, 0.1)
            V['1 POWER'] = add(V.get('1 POWER', 0), 1)
            yield
        yield

@stage.on_flag(stage_t)
def stage_script_3(self):
    if False: yield          # (makes this function a generator)
    while True:
        while not eq(V['1 TIME'], 0):
            yield from wait(stage, 1)
            V['1 TIME'] = add(V.get('1 TIME', 0), -1)
            yield
        yield

@stage.on_flag(stage_t)
def stage_script_4(self):
    if False: yield          # (makes this function a generator)
    stage.clear_pen()

@stage.on_flag(stage_t)
def stage_script_5(self):
    if False: yield          # (makes this function a generator)
    while not (stage.key_pressed('u') and stage.key_pressed('l')):
        yield
    while True:
        yield from wait(stage, rand(1, 10) / (1 + rage()))      # shorter calm periods as the buffalo weakens
        V['OZ'] = 1
        yield from wait(stage, rand(1, 10))
        V['OZ'] = 0
        yield

@stage.on_flag(stage_t)
def stage_script_6(self):
    if False: yield          # (makes this function a generator)
    yield
    yield
    stats['start_blood'] = V['2 BLOOD']

# ===================================================================== sprites
# (created back-to-front, i.e. later sprites are drawn on top)

# ---------------------------------------------------------------- 角色3
sp42 = stage.add_sprite('角色3', [
    Costume('造型1', 'assets/c510.png', (11, 25)),
], costume=1, x=240.0, y=-126.0, heading=90.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp42)
def script_42_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp42, 'z')
def script_42_2(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 4):
        V['1 POWER'] = add(V.get('1 POWER', 0), -5)
        self.goto_sprite(S['角色1'])
        self.show()
        self.set_heading(S['角色1'].attr('direction'))
        # FIX: hard step cap + "pinned by the edge fence" check, so this script can
        # never get stuck running (a running key script can't be restarted by pressing Z).
        for _ in range(80):
            px, py = self.x, self.y
            self.move(10)
            if self.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -200)
                break
            if abs(self.x) > 239 or abs(self.y) > 179 or abs(self.x - px) + abs(self.y - py) < 1:
                break
            yield
        self.hide()


# ---------------------------------------------------------------- 角色
sp41 = stage.add_sprite('角色', [
    Costume('造型1', 'assets/c1045.png', (1, 1)),
    Costume('造型2', 'assets/c501.png', (1, 1)),
], costume=2, x=20.0, y=135.0, heading=90.0, size=100.0,
   visible=False, rotation_style='normal')

# ---------------------------------------------------------------- 角色67
sp40 = stage.add_sprite('角色67', [
    Costume('造型1', 'assets/c492.png', (11, 25)),
], costume=1, x=25.8, y=-120.99, heading=88.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp40)
def script_40_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp40, 'x')
def script_40_2(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 9):
        V['1 POWER'] = add(V.get('1 POWER', 0), -10)
        self.goto_sprite(S['角色1'])
        self.show()
        self.set_heading(S['角色1'].attr('direction'))
        for _ in range(rep(25)):
            self.point_towards(S['角色2'])
            self.move(10)
            if self.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -300)
                break
            yield
        self.hide()
        return

# ---------------------------------------------------------------- 角色53
sp39 = stage.add_sprite('角色53', [
    Costume('造型1', 'assets/c1024.png', (9, 39)),
    Costume('造型2', 'assets/c1025.png', (37, 18)),
    Costume('造型3', 'assets/c1026.png', (24, 23)),
    Costume('造型4', 'assets/c485.png', (23, 22)),
], costume=4, x=-43.72, y=-21.98, heading=125.0, size=100.0,
   visible=False, rotation_style='leftRight')

@stage.on_key(sp39, 'space')
def script_39_1(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 79):
        V['1 POWER'] = add(V.get('1 POWER', 0), -80)
        V['1 TIME'] = div(V['1 TIME'], 2)
        self.switch_costume(S['角色1'].attr('costume #'))
        self.set_effect('color', 0)
        self.point_towards(S['角色2'])
        self.goto_sprite(S['角色1'])
        self.move(30)
        self.show()
        yield from wait(stage, 1)
        for _ in range(rep(20)):
            yield from wait(stage, 1e-06)
            self.point_towards(S['角色2'])
            self.stamp()
            self.move(10)
            self.set_effect('color', rand(0, 15))
            if self.touching(S['角色2']):
                if eq(S['角色1'].attr('costume #'), 4):
                    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -10000)
                else:
                    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -2500)
                stage.clear_pen()
                self.hide()
                return
            yield
        stage.clear_pen()
        self.hide()

@stage.on_flag(sp39)
def script_39_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色69
sp38 = stage.add_sprite('角色69', [
    Costume('造型1', 'assets/c477.png', (108, 114)),
], costume=1, x=-49.0, y=-194.0, heading=90.0, size=100.0,
   visible=False, rotation_style='leftRight')

@stage.on_flag(sp38)
def script_38_1(self):
    if False: yield          # (makes this function a generator)
    yield from hold_attack(self, 'a', 140, 68)

# ---------------------------------------------------------------- 角色70
sp37 = stage.add_sprite('角色70', [
    Costume('造型1', 'assets/c470.png', (63, 20)),
], costume=1, x=36.0, y=-92.5, heading=0.0, size=100.0,
   visible=True, rotation_style='leftRight')

@stage.on_flag(sp37)
def script_37_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_flag(sp37)
def script_37_2(self):
    if False: yield          # (makes this function a generator)
    yield from hold_attack(self, 's', 85, 20, on_touch=sword_hit)

# ---------------------------------------------------------------- 角色72
sp36 = stage.add_sprite('角色72', [
    Costume('造型1', 'assets/c460.png', (101, 91)),
], costume=1, x=42.0, y=-120.0, heading=90.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp36)
def script_36_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp36, 'g')
def script_36_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)
    if eq(S['角色1'].attr('costume #'), 1):
        if gt(V['1 POWER'], 99):
            if eq(S['角色2'].attr('size'), 100):
                V['1 POWER'] = add(V.get('1 POWER', 0), -100)
                self.show()
                self.goto_sprite(S['角色1'])
                yield from glide(stage, self, 2, S['角色2'].attr('x position'), S['角色2'].attr('y position'))
                for _ in range(rep(90)):
                    self.change_size(-1)
                    self.goto(S['角色2'].attr('x position'), S['角色2'].attr('y position'))
                    yield
                V['1 TIME'] = div(V['1 TIME'], 15)
                V['2 BLOOD'] = div(V['2 BLOOD'], 99)
                self.hide()

# ---------------------------------------------------------------- 角色74
sp35 = stage.add_sprite('角色74', [
    Costume('造型1', 'assets/c453.png', (21, 7)),
], costume=1, x=36.0, y=-198.0, heading=180.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp35, '7')
def script_35_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        if eq(V['laser1'], 0):
            V['laser1'] = 1
            self.goto_sprite(S['角色73'])
            self.show()
            self.set_heading(S['角色73'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()
            V['laser1'] = 0

@stage.on_flag(sp35)
def script_35_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色2
sp34 = stage.add_sprite('角色2', [
    Costume('buffalo1', 'assets/c444.png', (85, 49)),
], costume=1, x=47.0, y=-120.0, heading=-90.0, size=100.0,
   visible=True, rotation_style='leftRight')

@stage.on_flag(sp34)
def script_34_1(self):
    if False: yield          # (makes this function a generator)
    while not self.touching(S['角色72']):
        yield
    while not eq(S['角色2'].attr('size'), 10):
        self.set_size(S['角色72'].attr('size'))
        yield

@stage.on_flag(sp34)
def script_34_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)
    self.goto(150, -120)
    self.set_heading(-90)
    while True:
        if (eq(V['OZ'], 1) and eq(100, S['角色2'].attr('size'))):
            for _ in range(rep(20)):
                if (not self.touching(S['角色71'])):
                    if self.touching(S['角色72']):
                        return
                    self.point_towards(S['角色1'])
                    if (((not self.touching(S['角色69'])) or (not self.touching(S['角色101']))) or (not self.touching(S['角色71']))):
                        self.move(10 * buf_pace())
                    if self.touching(S['角色1']):
                        if ((not self.touching(S['角色69'])) or (not self.touching(S['角色101']))):
                            if gt(V['1 POWER'], 2):
                                V['1 POWER'] = add(V.get('1 POWER', 0), -2)
                            V['1 TIME'] = add(V.get('1 TIME', 0), -3 * V['hit_scale'])
                yield
            if (not (self.touching(S['角色71']) and eq(S['角色71'].attr('costume #'), 5))):
                yield from glide(stage, self, 0.5, self.x, -120)
        else:
            if (not self.touching(S['角色71'])):
                yield from wait(stage, rand(1, 0))
                for _ in range(rep(rand(0, 50))):
                    if self.touching(S['角色72']):
                        return
                    if (not self.touching(S['角色71'])):
                        self.move(rand(10, -10) * buf_pace())
                        self.bounce_off_edge()
                        if self.touching(S['角色1']):
                            if ((not self.touching(S['角色69'])) or (not self.touching(S['角色101']))):
                                if gt(V['1 POWER'], 2):
                                    V['1 POWER'] = add(V.get('1 POWER', 0), -2)
                                V['1 TIME'] = add(V.get('1 TIME', 0), -1 * V['hit_scale'])
                    yield
        yield

# ---------------------------------------------------------------- 角色78
sp33 = stage.add_sprite('角色78', [
    Costume('造型1', 'assets/c437.png', (21, 7)),
], costume=1, x=56.0, y=-196.0, heading=180.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp33)
def script_33_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp33, '7')
def script_33_2(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        if eq(V['laser1'], 1):
            V['laser2'] = 1
            self.goto_sprite(S['角色73'])
            self.show()
            self.set_heading(S['角色73'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()
            V['laser2'] = 0

# ---------------------------------------------------------------- 角色79
sp32 = stage.add_sprite('角色79', [
    Costume('造型1', 'assets/c430.png', (15, 5)),
], costume=1, x=64.0, y=-191.0, heading=180.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp32, '9')
def script_32_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.goto_sprite(S['角色73'])
        self.show()
        self.set_heading(S['角色73'].attr('direction'))
        yield from fly_shot(self, 3, 200)
        self.hide()
        yield from wait(stage, 5)

@stage.on_flag(sp32)
def script_32_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色80
sp31 = stage.add_sprite('角色80', [
    Costume('造型1', 'assets/c421.png', (44, 18)),
], costume=1, x=-241.0, y=140.0, heading=-90.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp31, '0')
def script_31_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.goto_sprite(S['角色73'])
        self.show()
        self.set_heading(S['角色73'].attr('direction'))
        yield from fly_shot(self, 3, 500)
        self.hide()
        yield from wait(stage, 1)

@stage.on_flag(sp31)
def script_31_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色81
sp30 = stage.add_sprite('角色81', [
    Costume('造型1', 'assets/c414.png', (21, 7)),
], costume=1, x=56.0, y=-196.0, heading=180.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp30)
def script_30_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp30, '7')
def script_30_2(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        if (eq(V['laser1'], 1) and eq(V['laser2'], 1)):
            self.goto_sprite(S['角色73'])
            self.show()
            self.set_heading(S['角色73'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()

# ---------------------------------------------------------------- 角色73
sp29 = stage.add_sprite('角色73', [
    Costume('airplane1', 'assets/c957.png', (10, 6)),
    Costume('airplane2', 'assets/c406.png', (44, 71)),
], costume=2, x=240.0, y=-54.0, heading=90.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp29, '6')
def script_29_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.set_heading(90)
        self.move(2)

@stage.on_key(sp29, '5')
def script_29_2(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.set_heading(180)
        self.move(2)

@stage.on_flag(sp29)
def script_29_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    V['PLANE'] = 0
    while not ((stage.key_pressed('h') and stage.key_pressed('e')) and (stage.key_pressed('l') and stage.key_pressed('p'))):
        yield
    self.goto(200, 130)
    self.show()
    V['PLANE'] = 1
    self.switch_costume('airplane1')
    while not ((self.touching(S['角色2']) or self.touching(S['Following_Arrow'])) or (self.touching(S['角色87']) or (self.touching(S['角色92']) or ((self.touching(S['角色91']) or self.touching(S['角色94'])) or (self.touching(S['角色95']) or self.touching(S['角色88'])))))):
        yield
    V['PLANE'] = 0
    self.switch_costume('airplane2')
    if gt(S['角色73'].attr('x position'), 0):
        self.set_heading(90)
        while not (gt(S['角色73'].attr('x position'), 239) or (lt(S['角色73'].attr('x position'), -239) or lt(S['角色73'].attr('y position'), -179))):
            self.goto(add(self.x, 1), sub(self.y, 1))
            yield
    else:
        self.set_heading(180)
        while not (gt(S['角色73'].attr('x position'), 239) or (lt(S['角色73'].attr('x position'), -239) or lt(S['角色73'].attr('y position'), -179))):
            self.goto(sub(self.x, 1), sub(self.y, 1))
            yield
    self.hide()

@stage.on_key(sp29, '4')
def script_29_4(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.set_heading(-90)
        self.move(2)

@stage.on_key(sp29, '8')
def script_29_5(self):
    if False: yield          # (makes this function a generator)
    if eq(V['PLANE'], 1):
        self.set_heading(0)
        self.move(2)

# ---------------------------------------------------------------- 角色83
sp28 = stage.add_sprite('角色83', [
    Costume('造型1', 'assets/c398.png', (21, 7)),
], costume=1, x=186.36, y=-182.85, heading=-98.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp28, 'u')
def script_28_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        if eq(V['LASER21'], 0):
            V['LASER21'] = 1
            self.goto_sprite(S['角色82'])
            self.show()
            self.set_heading(S['角色82'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()
            V['LASER21'] = 0

@stage.on_flag(sp28)
def script_28_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色84
sp27 = stage.add_sprite('角色84', [
    Costume('造型1', 'assets/c391.png', (21, 7)),
], costume=1, x=247.42, y=-70.59, heading=78.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp27, 'u')
def script_27_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        if eq(V['LASER21'], 1):
            V['LASER22'] = 1
            self.goto_sprite(S['角色82'])
            self.show()
            self.set_heading(S['角色82'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()
            V['LASER22'] = 0

@stage.on_flag(sp27)
def script_27_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色85
sp26 = stage.add_sprite('角色85', [
    Costume('造型1', 'assets/c382.png', (21, 7)),
], costume=1, x=-15.7, y=-126.52, heading=78.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp26)
def script_26_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp26, 'u')
def script_26_2(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        if (eq(V['LASER21'], 1) and eq(V['LASER22'], 1)):
            self.goto_sprite(S['角色82'])
            self.show()
            self.set_heading(S['角色82'].attr('direction'))
            yield from fly_shot(self, 10, 50)
            self.hide()

# ---------------------------------------------------------------- 角色86
sp25 = stage.add_sprite('角色86', [
    Costume('造型1', 'assets/c373.png', (15, 5)),
], costume=1, x=240.29, y=-70.63, heading=78.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp25, 'o')
def script_25_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        self.goto_sprite(S['角色82'])
        self.show()
        self.set_heading(S['角色82'].attr('direction'))
        yield from fly_shot(self, 4, 200)
        self.hide()
        yield from wait(stage, 5)

@stage.on_flag(sp25)
def script_25_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色82
sp24 = stage.add_sprite('角色82', [
    Costume('airplane1', 'assets/c919.png', (8, 5)),
    Costume('airplane2', 'assets/c364.png', (40, 65)),
], costume=2, x=197.6, y=-180.0, heading=90.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp24, 'k')
def script_24_1(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        while not (not stage.key_pressed('k')):
            V['DIRECTION'] = add(V.get('DIRECTION', 0), 2)
            yield

@stage.on_key(sp24, 'l')
def script_24_2(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        while not (not stage.key_pressed('l')):
            if lt(V['SPEED'], 3):
                V['SPEED'] = add(V.get('SPEED', 0), 0.1)
            yield

@stage.on_key(sp24, 'j')
def script_24_3(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        while not (not stage.key_pressed('j')):
            if gt(V['SPEED'], 0.5):
                V['SPEED'] = add(V.get('SPEED', 0), -0.1)
            yield

@stage.on_key(sp24, 'i')
def script_24_4(self):
    if False: yield          # (makes this function a generator)
    if eq(V['plane2'], 1):
        while not (not stage.key_pressed('i')):
            V['DIRECTION'] = add(V.get('DIRECTION', 0), -2)
            yield

@stage.on_flag(sp24)
def script_24_5(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    V['plane2'] = 0
    self.goto(-200, 130)
    while not ((stage.key_pressed('w') and stage.key_pressed('i')) and stage.key_pressed('n')):
        yield
    self.show()
    V['plane2'] = 1
    self.switch_costume('airplane1')
    while not ((self.touching(S['角色2']) or self.touching(S['Following_Arrow'])) or (self.touching(S['角色87']) or (self.touching(S['角色92']) or ((self.touching(S['角色91']) or self.touching(S['角色94'])) or (self.touching(S['角色95']) or self.touching(S['角色88'])))))):
        self.set_heading(V['DIRECTION'])
        self.move(V['SPEED'])
        yield
    V['plane2'] = 0
    self.switch_costume('airplane2')
    if gt(S['角色82'].attr('x position'), 0):
        self.set_heading(90)
        while not (gt(S['角色82'].attr('x position'), 239) or (lt(S['角色82'].attr('x position'), -239) or lt(S['角色82'].attr('y position'), -179))):
            self.goto(add(self.x, 1), sub(self.y, 1))
            yield
    else:
        self.set_heading(180)
        while not (gt(S['角色82'].attr('x position'), 239) or (lt(S['角色82'].attr('x position'), -239) or lt(S['角色82'].attr('y position'), -179))):
            self.goto(sub(self.x, 1), sub(self.y, 1))
            yield
    self.hide()

# ---------------------------------------------------------------- 角色93
sp23 = stage.add_sprite('角色93', [
    Costume('造型1', 'assets/c353.png', (25, 25)),
], costume=1, x=3.17, y=126.92, heading=-95.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp23)
def script_23_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.goto(0, 130)
    self.set_size(100)
    self.clear_effects()
    while not (stage.key_pressed('q') and stage.key_pressed('i')):
        yield
    while True:
        if stage.key_pressed('q'):
            self.goto(0, 130)
            self.show()
            while not self.touching(S['角色1']):
                self.point_towards(S['角色1'])
                self.move(5)
                self.change_size(rand(-10, 10))
                self.change_effect('color', rand(-10, 10))
                yield
            self.hide()
            while not gt(V['1 TIME'], 10000):
                V['1 TIME'] = add(V.get('1 TIME', 0), 100)
                if lt(V['1 POWER'], 10000):
                    V['1 POWER'] = add(V.get('1 POWER', 0), 100)
                yield
        yield

# ---------------------------------------------------------------- 角色99
sp22 = stage.add_sprite('角色99', [
    Costume('造型1', 'assets/c345.png', (19, 43)),
], costume=1, x=-124.14, y=-110.39, heading=-174.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp22)
def script_22_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp22, 'w')
def script_22_2(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 0):
        if eq(S['角色1'].attr('costume #'), 4):
            if eq(V['Y1'], 0):
                V['Y1'] = 1
                V['1 POWER'] = add(V.get('1 POWER', 0), -1)
                self.goto_sprite(S['角色1'])
                self.show()
                self.set_heading(S['角色1'].attr('direction'))
                for _ in range(rep(100)):
                    self.point_towards(S['角色2'])
                    self.move(10)
                    if self.touching(S['角色2']):
                        V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -30)
                    yield
                self.hide()
                V['Y1'] = 0

# ---------------------------------------------------------------- 角色100
sp21 = stage.add_sprite('角色100', [
    Costume('造型1', 'assets/c336.png', (76, 20)),
], costume=1, x=-65.0, y=-150.0, heading=90.0, size=100.0,
   visible=False, rotation_style='leftRight')

@stage.on_flag(sp21)
def script_21_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_flag(sp21)
def script_21_2(self):
    if False: yield          # (makes this function a generator)
    yield from hold_attack(self, 'e', 85, 20, form4_only=True, min_start=1, on_touch=heavy_sword_hit)

# ---------------------------------------------------------------- 角色101
sp20 = stage.add_sprite('角色101', [
    Costume('造型1', 'assets/c327.png', (108, 145)),
], costume=1, x=-10.0, y=-198.0, heading=90.0, size=100.0,
   visible=False, rotation_style='leftRight')

@stage.on_flag(sp20)
def script_20_1(self):
    if False: yield          # (makes this function a generator)
    yield from hold_attack(self, 'r', 140, 68, form4_only=True, min_start=1)

# ---------------------------------------------------------------- 角色102
sp19 = stage.add_sprite('角色102', [
    Costume('造型1', 'assets/c317.png', (19, 43)),
], costume=1, x=-124.14, y=-110.39, heading=-174.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp19)
def script_19_1(self):
    if False: yield          # (makes this function a generator)
    self.set_effect('color', 0)

@stage.on_flag(sp19)
def script_19_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp19, 'w')
def script_19_3(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 0):
        if eq(S['角色1'].attr('costume #'), 4):
            if eq(V['Y1'], 1):
                V['1 POWER'] = add(V.get('1 POWER', 0), -1)
                self.goto_sprite(S['角色1'])
                self.show()
                self.set_heading(S['角色1'].attr('direction'))
                for _ in range(rep(100)):
                    self.change_effect('color', 1)
                    self.point_towards(S['角色2'])
                    self.move(10)
                    if self.touching(S['角色2']):
                        V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -30)
                    yield
                self.hide()

# ---------------------------------------------------------------- 角色97
sp18 = stage.add_sprite('角色97', [
    Costume('11', 'assets/c309.png', (220, 152)),
], costume=1, x=0.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp18)
def script_18_1(self):
    if False: yield          # (makes this function a generator)
    self.goto(0, 0)

# ---------------------------------------------------------------- 角色63
sp17 = stage.add_sprite('角色63', [
    Costume('11', 'assets/c300.png', (-20, 152)),
], costume=1, x=116.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp17)
def script_17_1(self):
    if False: yield          # (makes this function a generator)
    self.goto(200, 0)
    while True:
        yield from glide(stage, self, 0.5, div(V['2 BLOOD'], 50), 0)
        yield

# ---------------------------------------------------------------- 角色98
sp16 = stage.add_sprite('角色98', [
    Costume('11', 'assets/c289.png', (220, 142)),
], costume=1, x=-4.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp16)
def script_16_1(self):
    if False: yield          # (makes this function a generator)
    self.goto(-200, 0)
    while True:
        yield from glide(stage, self, 0.5, sub(0, div(V['1 POWER'], 0.5)), 0)
        yield

# ---------------------------------------------------------------- 角色62
sp15 = stage.add_sprite('角色62', [
    Costume('11', 'assets/c280.png', (220, 152)),
], costume=1, x=-23.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp15)
def script_15_1(self):
    if False: yield          # (makes this function a generator)
    self.goto(-200, 0)
    while True:
        yield from glide(stage, self, 0.5, sub(0, div(V['1 TIME'], 0.9)), 0)
        yield

# ---------------------------------------------------------------- 角色96
sp14 = stage.add_sprite('角色96', [
    Costume('12', 'assets/c271.png', (240, 158)),
], costume=1, x=0.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp14)
def script_14_1(self):
    if False: yield          # (makes this function a generator)
    self.goto(0, 0)

# ---------------------------------------------------------------- 角色103
sp13 = stage.add_sprite('角色103', [
    Costume('造型4', 'assets/c262.png', (19, 19)),
], costume=1, x=-78.37, y=40.68, heading=147.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp13, 'space')
def script_13_1(self):
    if False: yield          # (makes this function a generator)
    if eq(S['角色1'].attr('costume #'), 4):
        if gt(V['1 POWER'], 79):
            self.set_heading(90)
            self.set_effect('color', 0)
            self.goto_sprite(S['角色1'])
            self.set_heading(0)
            self.move(80)
            self.point_towards(S['角色2'])
            self.show()
            yield from wait(stage, 1)
            for _ in range(rep(20)):
                yield from wait(stage, 1e-06)
                self.point_towards(S['角色2'])
                self.stamp()
                self.move(10)
                self.turn(15)
                self.set_effect('color', rand(0, 15))
                if self.touching(S['角色2']):
                    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -5000)
                    stage.clear_pen()
                    self.hide()
                    return
                yield
            stage.clear_pen()
            self.hide()

@stage.on_flag(sp13)
def script_13_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色104
sp12 = stage.add_sprite('角色104', [
    Costume('造型4', 'assets/c253.png', (19, 19)),
], costume=1, x=-43.39, y=-61.58, heading=129.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_key(sp12, 'space')
def script_12_1(self):
    if False: yield          # (makes this function a generator)
    if eq(S['角色1'].attr('costume #'), 4):
        if gt(V['1 POWER'], 79):
            self.set_heading(90)
            self.set_effect('color', 0)
            self.goto_sprite(S['角色1'])
            self.set_heading(180)
            self.move(80)
            self.point_towards(S['角色2'])
            self.show()
            yield from wait(stage, 1)
            for _ in range(rep(20)):
                yield from wait(stage, 1e-06)
                self.point_towards(S['角色2'])
                self.stamp()
                self.move(10)
                self.turn(15)
                self.set_effect('color', rand(0, 15))
                if self.touching(S['角色2']):
                    V['2 BLOOD'] = add(V.get('2 BLOOD', 0), -5000)
                    stage.clear_pen()
                    self.hide()
                    return
                yield
            stage.clear_pen()
            self.hide()

@stage.on_flag(sp12)
def script_12_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()

# ---------------------------------------------------------------- 角色1
sp11 = stage.add_sprite('角色1', [
    Costume('造型1', 'assets/c771.png', (47, 51)),
    Costume('造型2', 'assets/c773.png', (47, 51)),
    Costume('造型3', 'assets/c242.png', (47, 51)),
    Costume('造型4', 'assets/c774.png', (47, 51)),
], costume=3, x=-68.0, y=-72.0, heading=-90.0, size=100.0,
   visible=True, rotation_style='leftRight')

sp11.keep_inside = True      # FIX: the cat can't go half off-screen (so Z/X always have room to fire)

@stage.on_flag(sp11)
def script_11_1(self):
    if False: yield          # (makes this function a generator)
    while not self.touching(S['角色93']):
        yield
    self.switch_costume('造型4')

@stage.on_key(sp11, 'right arrow')
def script_11_2(self):
    if False: yield          # (makes this function a generator)
    yield from cat_walk(self, 90, 'right arrow')

@stage.on_key(sp11, 'down arrow')
def script_11_3(self):
    if False: yield          # (makes this function a generator)
    yield from cat_walk(self, 180, 'down arrow')

@stage.on_key(sp11, 'up arrow')
def script_11_4(self):
    if False: yield          # (makes this function a generator)
    yield from cat_walk(self, 0, 'up arrow')

@stage.on_key(sp11, 'f')
def script_11_5(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 0):
        if eq(S['角色2'].attr('size'), 100):
            V['1 POWER'] = add(V.get('1 POWER', 0), -1)
            self.point_towards(S['角色2'])
            yield from glide(stage, self, div(mul(100, compute('sqrt', compute('abs', sub(S['角色1'].attr('costume #'), 1.75)))), 100), self.x, 150)
            yield from glide(stage, self, div(mul(100, compute('sqrt', compute('abs', sub(S['角色1'].attr('costume #'), 1.75)))), 200), S['角色2'].attr('x position'), add(S['角色2'].attr('y position'), 90))
            if self.touching(S['角色2']):
                V['2 BLOOD'] = add(V.get('2 BLOOD', 0), mul(-100, compute('sqrt', compute('abs', sub(S['角色1'].attr('costume #'), 1.75)))))
            yield from glide(stage, self, div(mul(100, compute('sqrt', compute('abs', div(sub(S['角色1'].attr('costume #'), 1.75), 120)))), 100), self.x, 150)

@stage.on_key(sp11, '1')
def script_11_6(self):
    if False: yield          # (makes this function a generator)
    self.switch_costume('造型1')

@stage.on_key(sp11, '3')
def script_11_7(self):
    if False: yield          # (makes this function a generator)
    self.switch_costume('造型3')

@stage.on_key(sp11, '2')
def script_11_8(self):
    if False: yield          # (makes this function a generator)
    self.switch_costume('造型2')

@stage.on_key(sp11, 'left arrow')
def script_11_9(self):
    if False: yield          # (makes this function a generator)
    yield from cat_walk(self, -90, 'left arrow')

@stage.on_flag(sp11)
def script_11_10(self):
    if False: yield          # (makes this function a generator)
    self.goto(-150, -130)
    self.set_heading(90)
    self.switch_costume('造型1')

# ---------------------------------------------------------------- 角色52
sp10 = stage.add_sprite('角色52', [
    Costume('造型1', 'assets/c232.png', (18, 35)),
], costume=1, x=-175.51, y=-99.26, heading=-85.0, size=103.0,
   visible=False, rotation_style='none')

@stage.on_flag(sp10)
def script_10_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()

@stage.on_key(sp10, 't')
def script_10_2(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 0):
        self.clear_effects()
        if eq(S['角色1'].attr('costume #'), 4):
            V['1 POWER'] = add(V.get('1 POWER', 0), -1)
            self.goto_sprite(S['角色2'])
            self.show()
            self.set_heading(S['角色1'].attr('direction'))
            while not self.touching(S['角色1']):
                self.set_size(rand(95, 105))
                self.change_effect('color', rand(0, -40))
                self.point_towards(S['角色1'])
                self.move(10)
                yield
            V['1 POWER'] = add(V.get('1 POWER', 0), mul(0.8, V['2 BLOOD']))
            V['1 TIME'] = add(V.get('1 TIME', 0), mul(0.8, V['2 BLOOD']))
            V['2 BLOOD'] = mul(0.2, V['2 BLOOD'])
            self.hide()

# ---------------------------------------------------------------- 角色71
sp09 = stage.add_sprite('角色71', [
    Costume('造型1', 'assets/c678.png', (11, 12)),
    Costume('造型2', 'assets/c679.png', (89, 41)),
    Costume('造型3', 'assets/c194.png', (23, 25)),
    Costume('造型4', 'assets/c680.png', (90, 55)),
    Costume('造型5', 'assets/c681.png', (118, 88)),
], costume=3, x=118.7, y=-117.5, heading=180.0, size=90.0,
   visible=False, rotation_style='leftRight')

@stage.on_flag(sp09)
def script_09_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()
    self.hide()
    yield from wait(stage, 50)

@stage.on_key(sp09, 'd')
def script_09_2(self):
    if False: yield          # (makes this function a generator)
    if gt(V['1 POWER'], 9):
        V['1 POWER'] = add(V.get('1 POWER', 0), -10)
        if eq(S['角色1'].attr('costume #'), 2):
            self.switch_costume('造型1')
            self.show()
            self.goto_sprite(S['角色1'])
            yield from glide(stage, self, 1, sub(S['角色2'].attr('x position'), 8), add(S['角色2'].attr('y position'), 80))
            yield from wait(stage, 1)
            self.switch_costume('造型2')
            self.goto(sub(S['角色2'].attr('x position'), 8), add(S['角色2'].attr('y position'), 80))
            for _ in range(rep(50)):
                self.set_heading(180)
                self.move(1)
                yield
            yield from wait(stage, 5)
            self.hide()
            return
        if eq(S['角色1'].attr('costume #'), 1):
            self.switch_costume('造型3')
            self.show()
            self.goto_sprite(S['角色1'])
            yield from glide(stage, self, 1, S['角色2'].attr('x position'), S['角色2'].attr('y position'))
            yield from wait(stage, 5)
            self.hide()
            return
        if eq(S['角色1'].attr('costume #'), 3):
            self.set_size(10)
            self.switch_costume('造型4')
            self.show()
            self.goto_sprite(S['角色1'])
            yield from glide(stage, self, 1, S['角色2'].attr('x position'), S['角色2'].attr('y position'))
            for _ in range(rep(90)):
                self.goto(S['角色2'].attr('x position'), S['角色2'].attr('y position'))
                self.change_size(1)
                yield
            yield from wait(stage, 5)
            self.hide()
            return
        if eq(S['角色1'].attr('costume #'), 4):
            self.set_size(190)
            self.switch_costume('造型5')
            self.show()
            self.goto_sprite(S['角色1'])
            yield from glide(stage, self, 1, S['角色2'].attr('x position'), S['角色2'].attr('y position'))
            for _ in range(rep(25)):
                self.goto(S['角色2'].attr('x position'), S['角色2'].attr('y position'))
                self.change_size(-4)
                yield
            yield from wait(stage, 30)
            self.hide()
            return
        self.hide()
        self.hide()

# ---------------------------------------------------------------- 角色95
sp08 = stage.add_sprite('角色95', [
    Costume('arrow2', 'assets/c184.png', (21, 21)),
], costume=1, x=102.01, y=-3.55, heading=-157.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp08)
def script_08_1(self):
    if False: yield          # (makes this function a generator)
    self.clear_effects()
    while True:
        while not eq(V['PQ'], 1):
            yield
        if eq(S['角色2'].attr('size'), 100):
            if (yield from arrow_cycle(self, 'whirl', True)):
                return          # destroyed for good (as in the original)
        yield

@stage.on_flag(sp08)
def script_08_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)

@stage.on_flag(sp08)
def script_08_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- 角色88
sp07 = stage.add_sprite('角色88', [
    Costume('arrow2', 'assets/c176.png', (21, 21)),
], costume=1, x=179.65, y=0.26, heading=-167.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp07)
def script_07_1(self):
    if False: yield          # (makes this function a generator)
    self.clear_effects()
    while True:
        while not eq(V['PQ'], 1):
            yield
        if eq(S['角色2'].attr('size'), 100):
            if (yield from arrow_cycle(self, 'color', True)):
                return          # destroyed for good (as in the original)
        yield

@stage.on_flag(sp07)
def script_07_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)
    for _ in range(rep(200)):
        pass
        yield

@stage.on_flag(sp07)
def script_07_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- 角色87
sp06 = stage.add_sprite('角色87', [
    Costume('造型1', 'assets/c167.png', (16, 15)),
], costume=1, x=-142.42, y=-127.77, heading=137.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp06)
def script_06_1(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)
    while not (stage.key_pressed('m') and stage.key_pressed('e')):
        yield
    while True:
        if eq(S['角色2'].attr('size'), 100):
            yield from wait(stage, rand(0, 2))
            self.show()
            self.goto_sprite(S['角色2'])
            self.set_heading(0)
            if ((not self.touching(S['角色71'])) and (not self.touching(S['角色72']))):
                self.set_heading(rand(-180, 180))
                for _ in range(rep(rand(30, 500))):
                    self.set_size(compute('sqrt', compute('abs', mul(self.y, self.y))))
                    self.bounce_off_edge()
                    self.move(25)
                    if self.touching(S['角色1']):
                        V['1 POWER'] = add(V.get('1 POWER', 0), -10 * V['hit_scale'])
                        V['1 TIME'] = add(V.get('1 TIME', 0), -30 * V['hit_scale'])
                        self.goto_sprite(S['角色2'])
                    if (((self.touching(S['角色3']) or self.touching(S['角色67'])) or self.touching(S['角色69'])) or (self.touching(S['角色72']) or (self.touching(S['角色101']) or self.touching(S['角色71'])))):
                        self.goto_sprite(S['角色2'])
                    yield
            self.hide()
        yield

@stage.on_flag(sp06)
def script_06_2(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- Following_Arrow
sp05 = stage.add_sprite('Following_Arrow', [
    Costume('arrow2', 'assets/c157.png', (100, 30)),
], costume=1, x=103.07, y=-71.05, heading=7.0, size=50.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp05)
def script_05_1(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

@stage.on_flag(sp05)
def script_05_2(self):
    if False: yield          # (makes this function a generator)
    while True:
        if eq(S['角色2'].attr('size'), 100):
            yield from wait(stage, rand(0, 5))
            self.show()
            self.goto_sprite(S['角色2'])
            self.set_heading(0)
            if ((not self.touching(S['角色71'])) and (not self.touching(S['角色72']))):
                for _ in range(rep(10)):
                    self.move(10)
                    if (((self.touching(S['角色3']) or self.touching(S['角色67'])) or self.touching(S['角色69'])) or (self.touching(S['角色71']) or (self.touching(S['角色72']) or ((self.touching(S['角色101']) or (self.touching(S['角色99']) or self.touching(S['角色100']))) or self.touching(S['角色102']))))):
                        self.goto_sprite(S['角色2'])
                        self.hide()
                    yield
                self.set_heading(rand(-180, 180))
                for _ in range(rep(rand(30, 200))):
                    self.bounce_off_edge()
                    self.move(10)
                    if self.touching(S['角色1']):
                        self.hide()
                        V['1 POWER'] = add(V.get('1 POWER', 0), -10 * V['hit_scale'])
                        V['1 TIME'] = add(V.get('1 TIME', 0), -5 * V['hit_scale'])
                    if (((self.touching(S['角色3']) or self.touching(S['角色67'])) or self.touching(S['角色69'])) or (self.touching(S['角色71']) or (self.touching(S['角色72']) or ((self.touching(S['角色101']) or (self.touching(S['角色99']) or self.touching(S['角色100']))) or self.touching(S['角色102']))))):
                        self.goto_sprite(S['角色2'])
                        self.hide()
                    yield
            self.hide()
        yield

# ---------------------------------------------------------------- 角色68
sp04 = stage.add_sprite('角色68', [
    Costume('造型1', 'assets/c602.png', (13, -15)),
    Costume('造型2', 'assets/c146.png', (13, -15)),
    Costume('造型3', 'assets/c603.png', (13, -15)),
    Costume('造型4', 'assets/c604.png', (13, -15)),
], costume=2, x=-65.5, y=-72.0, heading=-90.0, size=100.0,
   visible=True, rotation_style='leftRight')

@stage.on_flag(sp04)
def script_04_1(self):
    if False: yield          # (makes this function a generator)
    self.come_to_front()
    while True:
        if gt(V['1 TIME'], 10):
            if lt(V['1 TIME'], 181):
                self.switch_costume('造型1')
                while not (not (gt(V['1 TIME'], 10) and lt(V['1 TIME'], 181))):
                    self.set_heading(S['角色1'].attr('direction'))
                    self.goto(S['角色1'].attr('x position'), S['角色1'].attr('y position'))
                    yield
            else:
                while not (not gt(V['1 TIME'], 181)):
                    self.switch_costume('造型4')
                    self.set_heading(S['角色1'].attr('direction'))
                    self.goto(S['角色1'].attr('x position'), S['角色1'].attr('y position'))
                    self.switch_costume('造型3')
                    yield
        else:
            while not gt(V['1 TIME'], 10):
                if (not gt(V['1 TIME'], 10)):
                    self.set_heading(S['角色1'].attr('direction'))
                    self.goto(S['角色1'].attr('x position'), S['角色1'].attr('y position'))
                    self.switch_costume('造型2')
                    yield from wait(stage, div(V['1 TIME'], 50))
                    self.goto(S['角色1'].attr('x position'), S['角色1'].attr('y position'))
                    self.switch_costume('造型3')
                yield
        yield

# ---------------------------------------------------------------- 角色94
sp03 = stage.add_sprite('角色94', [
    Costume('arrow2', 'assets/c138.png', (21, 21)),
], costume=1, x=-10.03, y=-131.69, heading=-28.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp03)
def script_03_1(self):
    if False: yield          # (makes this function a generator)
    self.clear_effects()
    while True:
        while not eq(V['PQ'], 1):
            yield
        if eq(S['角色2'].attr('size'), 100):
            if (yield from arrow_cycle(self, 'fisheye', True)):
                return          # destroyed for good (as in the original)
        yield

@stage.on_flag(sp03)
def script_03_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)

@stage.on_flag(sp03)
def script_03_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- 角色92
sp02 = stage.add_sprite('角色92', [
    Costume('arrow2', 'assets/c129.png', (40, 1)),
], costume=1, x=180.43, y=78.02, heading=137.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp02)
def script_02_1(self):
    if False: yield          # (makes this function a generator)
    self.clear_effects()
    while True:
        while not eq(V['PQ'], 1):
            yield
        if eq(S['角色2'].attr('size'), 100):
            if (yield from arrow_cycle(self, None, False)):
                return          # destroyed for good (as in the original)
        yield

@stage.on_flag(sp02)
def script_02_2(self):
    if False: yield          # (makes this function a generator)
    self.change_size(-1)
    self.hide()
    self.come_to_front()

@stage.on_flag(sp02)
def script_02_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- 角色91
sp01 = stage.add_sprite('角色91', [
    Costume('arrow2', 'assets/c120.png', (41, 1)),
], costume=1, x=-225.71, y=-2.77, heading=-23.0, size=100.0,
   visible=False, rotation_style='normal')

@stage.on_flag(sp01)
def script_01_1(self):
    if False: yield          # (makes this function a generator)
    self.clear_effects()
    while True:
        while not eq(V['PQ'], 1):
            yield
        if eq(S['角色2'].attr('size'), 100):
            if (yield from arrow_cycle(self, None, False)):
                return          # destroyed for good (as in the original)
        yield

@stage.on_flag(sp01)
def script_01_2(self):
    if False: yield          # (makes this function a generator)
    self.set_size(100)

@stage.on_flag(sp01)
def script_01_3(self):
    if False: yield          # (makes this function a generator)
    self.hide()
    self.come_to_front()

# ---------------------------------------------------------------- 角色66
sp00 = stage.add_sprite('角色66', [
    Costume('背景1', 'assets/c108.png', (240, 180)),
    Costume('背景2', 'assets/c539.png', (240, 180)),
], costume=1, x=3.0, y=0.0, heading=90.0, size=100.0,
   visible=True, rotation_style='normal')

@stage.on_flag(sp00)
def script_00_1(self):
    if False: yield          # (makes this function a generator)
    while not lt(V['1 TIME'], 1):
        yield
    self.switch_costume('背景1')
    self.show()
    self.come_to_front()
    stage.stop_all()
    return

@stage.on_flag(sp00)
def script_00_2(self):
    if False: yield          # (makes this function a generator)
    V['1 TIME'] = 180
    while not lt(V['2 BLOOD'], 1):
        yield
    self.switch_costume('背景2')
    self.show()
    self.come_to_front()
    stage.stop_all()
    return

@stage.on_flag(sp00)
def script_00_3(self):
    if False: yield          # (makes this function a generator)
    self.come_to_front()
    self.hide()


# ===================================================================== HUD read-outs
stage.watchers.append(Watcher(stage, '1 POWER', (101, 2, 109, 21)))
stage.watchers.append(Watcher(stage, '2 BLOOD', (358, 2, 117, 21)))
stage.watchers.append(Watcher(stage, '1 TIME', (7, 1, 93, 21)))


# ===================================================================== help / title screen
# (shown on start and with F1; the game is paused while it is open)
stage.help_pages = [
    ('CAT KNIGHT AGAINST BUFFALO', [
        "Drain the buffalo's blood (2 BLOOD) to 0 before",
        'your 1 TIME runs out.  1 POWER refills by itself.',
        '#CHOOSE HOW TO START',
        'ENTER\tNormal: the buffalo just wanders about',
        'E\tEasy: more time, weaker buffalo, gentle hits',
        'B\tBattle: the buffalo charges at you',
        'A\tHard: it charges AND arrows rain down',
        '#QUICK CONTROLS',
        'ARROWS\tRun around.  Bump the buffalo to hurt it.',
        '1 2 3\tSwitch form',
        'Z X F D\tAttacks      SPACE  big blast',
        '#',
        'Use the <- -> keys to read about every control.',
        'F1 help any time    F11 fullscreen    Esc quits',
    ]),
    ('MOVING AND FORMS', [
        '#MOVE',
        'ARROWS\tRun around.  Bump the buffalo to hurt it.',
        '#FORMS  (press 1, 2 or 3 to change)',
        '1\tBalanced speed and hit strength',
        '2\tFastest runner, weakest hits',
        '3\tSlowest, hardest hits  (you start here)',
        '#KEEP IN MIND',
        'Each special attack uses POWER (max 100).',
        'POWER refills by about 10 every second.',
        'The buffalo drains your TIME if it bumps you.',
        'It gets faster and angrier as its blood drops.',
    ]),
    ('SPECIAL ATTACKS', [
        '#COST IN POWER  /  DAMAGE',
        'F\tLeap at the buffalo: 1 power, 50-150 damage',
        'Z\tFire a bolt ahead: 5 power, 200 damage',
        'X\tHoming shot: 10 power, 300 damage',
        'D\tSummon an attack (differs per form): 10 power',
        'A  S\tHold: shield / sword.  They use POWER and TIME',
        '\tthe whole time you hold them.',
        'SPACE\tBig homing blast: 80 power, 2500 damage',
        '\t...but it halves your TIME!',
        'G\tForm 1 only, 100 power: buffalo blood / 99,',
        '\tbut your TIME is divided by 15.',
    ]),
    ('SECRET FORM 4', [
        'Hold Q + I, then keep Q held: a power-up flies',
        'to the cat.  Touching it refills TIME and POWER',
        'to 10,000 and unlocks FORM 4:',
        '#FORM 4',
        'ARROWS\tFastest, and every bump does 50 damage',
        'SPACE\tHuge blasts: 10,000+ damage',
        "T\tDrain: takes 80% of the buffalo's blood into",
        '\tyour POWER and TIME',
        'W\tHoming swarm: 30 damage per hit',
        'R  E\tHold: heavy shield / heavy sword',
    ]),
    ('PLANE MODES', [
        '#PLANE 1  -  hold H + E + L + P together',
        '4 6 8 5\tFly left / right / up / down',
        '7\tFire (press up to 3 times in a row)',
        '9  0\tShots that do 200 / 500 damage',
        '#PLANE 2  -  hold W + I + N together',
        'I  K\tTurn left / right',
        'L  J\tSpeed up / slow down',
        'U\tFire (up to 3 in a row)      O  Missile',
        'Planes crash if they touch the buffalo or arrows.',
    ]),
]
# letter on the title screen -> label, keys that get "pressed" for the player at the start
stage.start_options = [
    # Easy: wandering buffalo (like Normal) but slower, only 6000 blood, 300 TIME, and bumps hurt a quarter as much
    ('E', 'Easy', [], {'1 TIME': 300, '2 BLOOD': 6000, 'hit_scale': 0.25, 'buf_speed': 0.6}),
    ('B', 'Battle', ['u', 'l']),                # same as holding U+L: the buffalo charges at you
    ('A', 'Hard', ['u', 'l', 'p', 'q']),        # ... and P+Q: arrows rain down
]


# ---- win / lose banner (the original only swaps in a blank cover costume)
# cover sprite 角色66: costume 2 (背景2) is shown when BLOOD runs out = win, costume 1 = time up = lose
def end_banner():
    if stage.stopped:
        return 'YOU WIN!' if S['角色66'].costume_index == 2 else 'YOU LOSE'
stage.banner = end_banner
stage.hint = hint_segments      # (greys out attacks you can't afford right now)

def end_details():
    secs = stage.stop_frame / FPS
    if S['角色66'].costume_index == 2:
        return ['Won in %.1f s with %d TIME left' % (secs, max(0, V['1 TIME']))]
    left = max(0, V['2 BLOOD'])
    pct = 100 * left / max(1, stats['start_blood'])
    return ['Time ran out after %d s' % secs,
            'The buffalo had %d blood left (%d%%)' % (left, pct)]
stage.banner_detail = end_details


if __name__ == "__main__":
    stage.run()