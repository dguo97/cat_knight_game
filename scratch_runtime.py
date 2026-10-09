"""
scratch_runtime.py
==================
A small Scratch-1.4-style engine on top of pygame, written to run the Python
translation of "Cat Knight Against Buffalo".

Concepts
--------
* Stage coordinates are Scratch coordinates: 480x360, origin in the centre,
  +x right, +y up, heading 0 = up / 90 = right (clockwise).
* Every Scratch script is a Python *generator*.  A `yield` is the point where
  Scratch would hand control to the next script (end of a loop pass, `wait`,
  `wait until` ...), so one loop pass == one frame, like in Scratch.
* Sprites are drawn back-to-front from `Stage.layers` (last item is on top).
"""
import math
import random
import time

import numpy as np
import pygame

STAGE_W, STAGE_H = 480, 360
FPS = 60                      # Scratch 1.4 redraws roughly this often
FENCE = True                  # keep sprites from leaving the stage completely


# --------------------------------------------------------------------------
# value helpers (Scratch is loosely typed: "10", 10 and 10.0 are all alike)
# --------------------------------------------------------------------------
def num(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in str(v) and "e" not in str(v).lower() else f
    except (TypeError, ValueError):
        return 0


def _is_num(v):
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    try:
        float(v)
        return str(v).strip() != ""
    except (TypeError, ValueError):
        return False


def add(a, b): return num(a) + num(b)
def sub(a, b): return num(a) - num(b)
def mul(a, b): return num(a) * num(b)


def div(a, b):
    b = num(b)
    return num(a) / b if b else 0


def lt(a, b):
    if _is_num(a) and _is_num(b):
        return float(a) < float(b)
    return str(a).lower() < str(b).lower()


def gt(a, b):
    if _is_num(a) and _is_num(b):
        return float(a) > float(b)
    return str(a).lower() > str(b).lower()


def eq(a, b):
    if _is_num(a) and _is_num(b):
        return float(a) == float(b)
    return str(a).lower() == str(b).lower()


def rep(n):
    """repeat count"""
    return max(0, int(math.floor(num(n) + 0.5)))


def rounded(v):
    return int(math.floor(num(v) + 0.5))


def rand(a, b):
    a, b = num(a), num(b)
    lo, hi = min(a, b), max(a, b)
    if float(lo).is_integer() and float(hi).is_integer():
        return random.randint(int(lo), int(hi))
    return random.uniform(lo, hi)


def compute(fn, x):
    x = num(x)
    try:
        if fn == "abs":   return abs(x)
        if fn == "sqrt":  return math.sqrt(x)
        if fn == "sin":   return math.sin(math.radians(x))
        if fn == "cos":   return math.cos(math.radians(x))
        if fn == "tan":   return math.tan(math.radians(x))
        if fn == "asin":  return math.degrees(math.asin(x))
        if fn == "acos":  return math.degrees(math.acos(x))
        if fn == "atan":  return math.degrees(math.atan(x))
        if fn == "ln":    return math.log(x)
        if fn == "log":   return math.log10(x)
        if fn == "e ^":   return math.exp(x)
        if fn == "10 ^":  return 10 ** x
    except (ValueError, OverflowError):
        return 0
    return 0


def norm_heading(h):
    """Scratch keeps headings in (-180, 180]."""
    h = (h + 180) % 360 - 180
    return 180 if h == -180 else h


# --------------------------------------------------------------------------
# keyboard
# --------------------------------------------------------------------------
def _build_keymap():
    km = {"space": pygame.K_SPACE, "left arrow": pygame.K_LEFT,
          "right arrow": pygame.K_RIGHT, "up arrow": pygame.K_UP,
          "down arrow": pygame.K_DOWN, "enter": pygame.K_RETURN}
    for c in "abcdefghijklmnopqrstuvwxyz":
        km[c] = getattr(pygame, "K_" + c)
    for d in "0123456789":
        km[d] = getattr(pygame, "K_" + d)
    return km


# --------------------------------------------------------------------------
# threads
# --------------------------------------------------------------------------
class Thread:
    def __init__(self, script, sprite):
        self.script = script
        self.sprite = sprite
        self.gen = script(sprite)
        self.alive = True

    def step(self):
        try:
            next(self.gen)
        except StopIteration:
            self.alive = False


def wait(stage, secs):
    end = stage.now() + num(secs)
    while stage.now() < end:
        yield


def glide(stage, sprite, secs, x, y):
    secs, x, y = num(secs), num(x), num(y)
    x0, y0 = sprite.x, sprite.y
    t0 = stage.now()
    while True:
        t = stage.now() - t0
        if t >= secs:
            break
        f = t / secs if secs > 0 else 1
        sprite.goto(x0 + (x - x0) * f, y0 + (y - y0) * f)
        yield
    sprite.goto(x, y)


# --------------------------------------------------------------------------
# costumes and sprites
# --------------------------------------------------------------------------
class Costume:
    def __init__(self, name, path, rotation_center):
        self.name = name
        self.surface = pygame.image.load(path).convert_alpha()
        w, h = self.surface.get_size()
        self.rc = rotation_center if rotation_center else (w / 2, h / 2)


def _make_surface(arr, alpha):
    """(w,h,3) colour array + (w,h) alpha array -> per-pixel-alpha Surface"""
    w, h = arr.shape[:2]
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(out, np.clip(arr, 0, 255).astype(np.uint8))
    ar = pygame.surfarray.pixels_alpha(out)
    ar[:, :] = np.clip(alpha, 0, 255).astype(np.uint8)
    del ar
    return out


def _effect_surface(surf, effects):
    """Apply the graphic effects (colour, ghost, pixelate, whirl, fisheye)."""
    if not any(effects.values()):
        return surf
    arr = pygame.surfarray.array3d(surf).astype(np.float32)          # (w,h,3)
    alpha = pygame.surfarray.array_alpha(surf).astype(np.float32)    # (w,h)
    w, h = arr.shape[:2]

    fish = effects.get("fisheye", 0)
    whirl = effects.get("whirl", 0)
    if fish or whirl:
        xs, ys = np.meshgrid(np.arange(w), np.arange(h), indexing="ij")
        dx = (xs - w / 2.0) / (w / 2.0)
        dy = (ys - h / 2.0) / (h / 2.0)
        r = np.sqrt(dx * dx + dy * dy)
        if fish:
            scale = max(0.0, (100 + fish) / 100.0)
            rr = np.where(r > 0, np.minimum(r, 1.0) ** scale, 0)
            k = np.where(r > 0, rr / np.maximum(r, 1e-6), 1)
            dx, dy = dx * k, dy * k
            r = np.sqrt(dx * dx + dy * dy)
        if whirl:
            ang = -math.radians(whirl) * (1 - np.minimum(r, 1.0)) ** 2
            c, s = np.cos(ang), np.sin(ang)
            dx, dy = dx * c - dy * s, dx * s + dy * c
        sx = np.clip((dx * (w / 2.0) + w / 2.0).astype(int), 0, w - 1)
        sy = np.clip((dy * (h / 2.0) + h / 2.0).astype(int), 0, h - 1)
        arr = arr[sx, sy]
        alpha = alpha[sx, sy]

    pix = effects.get("pixelate", 0)
    if pix:
        block = max(1, int(abs(pix) / 10) + 1)
        if block > 1:
            sw, sh = max(1, w // block), max(1, h // block)
            tmp = _make_surface(arr, alpha)
            small = pygame.transform.scale(pygame.transform.scale(tmp, (sw, sh)), (w, h))
            arr = pygame.surfarray.array3d(small).astype(np.float32)
            alpha = pygame.surfarray.array_alpha(small).astype(np.float32)

    col = effects.get("color", 0)
    if col:
        shift = (col / 200.0) % 1.0
        flat = arr.reshape(-1, 3) / 255.0
        mx = flat.max(1); mn = flat.min(1); d = mx - mn
        hue = np.zeros_like(mx)
        m = d > 1e-6
        r_, g_, b_ = flat[:, 0], flat[:, 1], flat[:, 2]
        hue = np.where(m & (mx == r_), ((g_ - b_) / np.where(m, d, 1)) % 6, hue)
        hue = np.where(m & (mx == g_), (b_ - r_) / np.where(m, d, 1) + 2, hue)
        hue = np.where(m & (mx == b_), (r_ - g_) / np.where(m, d, 1) + 4, hue)
        hue = (hue / 6.0 + shift) % 1.0
        sat = np.where(mx > 0, d / np.where(mx > 0, mx, 1), 0)
        # hsv -> rgb
        i = np.floor(hue * 6).astype(int) % 6
        f = hue * 6 - np.floor(hue * 6)
        p = mx * (1 - sat); q = mx * (1 - f * sat); t = mx * (1 - (1 - f) * sat)
        out = np.zeros_like(flat)
        for k, (rr, gg, bb) in enumerate(((mx, t, p), (q, mx, p), (p, mx, t),
                                          (p, q, mx), (t, p, mx), (mx, p, q))):
            sel = i == k
            out[sel, 0], out[sel, 1], out[sel, 2] = rr[sel], gg[sel], bb[sel]
        arr = (out * 255).reshape(arr.shape)

    bri = effects.get("brightness", 0)
    if bri:
        arr = arr + 2.55 * bri

    ghost = effects.get("ghost", 0)
    if ghost:
        alpha = alpha * max(0.0, min(1.0, 1 - ghost / 100.0))

    return _make_surface(arr, alpha)


class Sprite:
    def __init__(self, stage, name, costumes, costume=1, x=0, y=0, heading=90,
                 size=100, visible=True, rotation_style="normal"):
        self.stage = stage
        self.name = name
        self.costumes = costumes
        self.costume_index = costume          # 1-based like Scratch
        self.x, self.y = x, y
        self.heading = norm_heading(heading)
        self.size = size
        self.visible = visible
        self.rotation_style = rotation_style
        self.effects = {}
        self._cache = {}
        self._cache_key = None
        self._rendered = None

    # ---- motion ----------------------------------------------------------
    def goto(self, x, y):
        self.x, self.y = num(x), num(y)
        if FENCE:
            self._fence()

    def move(self, steps):
        r = math.radians(self.heading)
        self.goto(self.x + num(steps) * math.sin(r), self.y + num(steps) * math.cos(r))

    def change_x(self, dx): self.goto(self.x + num(dx), self.y)
    def change_y(self, dy): self.goto(self.x, self.y + num(dy))
    def turn(self, deg): self.set_heading(self.heading + num(deg))
    def set_heading(self, h): self.heading = norm_heading(num(h))

    def goto_sprite(self, other):
        if other == "mouse":
            self.goto(*self.stage.mouse_xy())
        elif other is not None:
            self.goto(other.x, other.y)

    def point_towards(self, other):
        if other == "mouse":
            tx, ty = self.stage.mouse_xy()
        else:
            tx, ty = other.x, other.y
        dx, dy = tx - self.x, ty - self.y
        if dx or dy:
            self.heading = norm_heading(math.degrees(math.atan2(dx, dy)))

    # ---- looks -----------------------------------------------------------
    def show(self): self.visible = True
    def hide(self): self.visible = False

    def switch_costume(self, which):
        if isinstance(which, str) and not _is_num(which):
            for i, c in enumerate(self.costumes):
                if c.name == which:
                    self.costume_index = i + 1
                    return
            return
        idx = int(num(which))
        self.costume_index = (idx - 1) % len(self.costumes) + 1

    def change_size(self, d): self.size = max(1, self.size + num(d))
    def set_size(self, s): self.size = max(1, num(s))
    def change_effect(self, name, v): self.effects[name] = self.effects.get(name, 0) + num(v)
    def set_effect(self, name, v): self.effects[name] = num(v)
    def clear_effects(self): self.effects.clear()

    def come_to_front(self):
        L = self.stage.layers
        L.remove(self)
        L.append(self)

    def go_back(self, n):
        L = self.stage.layers
        i = L.index(self)
        L.remove(self)
        L.insert(max(0, min(len(L), i - int(num(n)))), self)

    # ---- sensing ---------------------------------------------------------
    def attr(self, name):
        return {"x position": self.x, "y position": self.y, "direction": self.heading,
                "costume #": self.costume_index, "size": self.size}.get(name, 0)

    @property
    def costume(self):
        return self.costumes[self.costume_index - 1]

    # ---- rendering -------------------------------------------------------
    def _render(self):
        """returns (surface, top-left) in pygame screen coordinates"""
        costume = self.costume
        flip = False
        angle = 0
        if self.rotation_style == "normal":
            angle = self.heading - 90
        elif self.rotation_style == "leftRight":
            flip = self.heading < 0
        eff = tuple(sorted((k, round(v)) for k, v in self.effects.items() if round(v)))
        key = (self.costume_index, round(self.size, 1), round(angle), flip, eff)
        hit = self._cache.get(key)
        if hit is None:
            surf = costume.surface
            w, h = surf.get_size()
            rcx, rcy = costume.rc
            if flip:
                surf = pygame.transform.flip(surf, True, False)
                rcx = w - rcx
            scale = self.size / 100.0
            if eff:
                surf = _effect_surface(surf, dict(eff))
            if abs(scale - 1) > 1e-3 or angle:
                surf2 = pygame.transform.rotozoom(surf, -angle, scale) if (angle or scale != 1) else surf
            else:
                surf2 = surf
            # where is the rotation centre in the new image?
            vx, vy = (rcx - w / 2.0) * scale, (rcy - h / 2.0) * scale
            a = math.radians(angle)
            rx = vx * math.cos(a) - vy * math.sin(a)
            ry = vx * math.sin(a) + vy * math.cos(a)
            nw, nh = surf2.get_size()
            off = (nw / 2.0 + rx, nh / 2.0 + ry)             # pivot inside new image
            # collisions ignore graphic effects (as in Scratch)
            if eff:
                base = costume.surface
                if flip:
                    base = pygame.transform.flip(base, True, False)
                msurf = pygame.transform.rotozoom(base, -angle, scale) if (angle or scale != 1) else base
            else:
                msurf = surf2
            hit = (surf2, off, pygame.mask.from_surface(msurf, 1))
            if len(self._cache) > 400:
                self._cache.clear()
            self._cache[key] = hit
        surf, off, mask = hit
        px, py = self.x + STAGE_W / 2.0, STAGE_H / 2.0 - self.y
        return surf, (px - off[0], py - off[1]), mask

    def rect(self):
        surf, tl, _ = self._render()
        return pygame.Rect(round(tl[0]), round(tl[1]), surf.get_width(), surf.get_height())

    def draw(self, screen):
        if not self.visible:
            return
        surf, tl, _ = self._render()
        screen.blit(surf, (round(tl[0]), round(tl[1])))

    def _fence(self):
        r = self.rect()
        inset = int(min(15, r.width // 2, r.height // 2)) or 1
        dx = dy = 0
        if r.right < inset: dx = inset - r.right
        if r.left > STAGE_W - inset: dx = (STAGE_W - inset) - r.left
        if r.bottom < inset: dy = inset - r.bottom
        if r.top > STAGE_H - inset: dy = (STAGE_H - inset) - r.top
        if dx or dy:
            self.x += dx
            self.y -= dy

    def bounce_off_edge(self):
        r = self.rect()
        d_left = r.left
        d_right = STAGE_W - r.right
        d_top = r.top
        d_bottom = STAGE_H - r.bottom
        m = min(d_left, d_right, d_top, d_bottom)
        if m > 0:
            return
        rad = math.radians(self.heading)
        dx, dy = math.sin(rad), math.cos(rad)
        if m == d_left:   dx = max(0.2, abs(dx))
        elif m == d_right: dx = -max(0.2, abs(dx))
        elif m == d_top:   dy = -max(0.2, abs(dy))
        else:             dy = max(0.2, abs(dy))
        self.heading = norm_heading(math.degrees(math.atan2(dx, dy)))
        # nudge back inside
        nx, ny = self.x, self.y
        nx += max(0, -r.left) - max(0, r.right - STAGE_W)
        ny -= max(0, -r.top) - max(0, r.bottom - STAGE_H)
        self.x, self.y = nx, ny

    def touching(self, other):
        if not self.visible:
            return False
        if other == "edge":
            r = self.rect()
            return r.left <= 0 or r.right >= STAGE_W or r.top <= 0 or r.bottom >= STAGE_H
        if other == "mouse":
            mx, my = self.stage.mouse_xy()
            surf, tl, mask = self._render()
            ix, iy = int(mx + STAGE_W / 2 - tl[0]), int(STAGE_H / 2 - my - tl[1])
            return 0 <= ix < mask.get_size()[0] and 0 <= iy < mask.get_size()[1] and bool(mask.get_at((ix, iy)))
        if other is None or other is self or not other.visible:
            return False
        s1, t1, m1 = self._render()
        s2, t2, m2 = other._render()
        ox, oy = round(t2[0]) - round(t1[0]), round(t2[1]) - round(t1[1])
        return m1.overlap(m2, (ox, oy)) is not None

    def stamp(self):
        if not self.visible:
            return
        surf, tl, _ = self._render()
        self.stage.pen_layer.blit(surf, (round(tl[0]), round(tl[1])))


class StageTarget:
    """the owner of the Stage's own scripts (they never touch a sprite)"""
    name = 'Stage'

    def __init__(self, stage):
        self.stage = stage


# --------------------------------------------------------------------------
# watchers (the HUD read-outs on the stage)
# --------------------------------------------------------------------------
class Watcher:
    def __init__(self, stage, var, rect):
        self.stage, self.var, self.rect = stage, var, pygame.Rect(rect)

    def draw(self, screen, font):
        v = self.stage.vars.get(self.var, 0)
        if isinstance(v, float):
            v = int(round(v)) if abs(v - round(v)) < 1e-9 else round(v, 2)
        txt = font.render(f"{self.var}  {v}", True, (0, 0, 0))
        self.rect.width = max(self.rect.width, txt.get_width() + 8)   # widen if the number gets long
        pygame.draw.rect(screen, (193, 196, 199), self.rect)
        pygame.draw.rect(screen, (148, 145, 145), self.rect, 1)
        screen.blit(txt, (self.rect.x + 4, self.rect.y + (self.rect.height - txt.get_height()) // 2))


# --------------------------------------------------------------------------
# the stage / interpreter
# --------------------------------------------------------------------------
class Stage:
    def __init__(self, title="Scratch project"):
        pygame.display.init()      # (no audio: this project never plays a sound)
        pygame.font.init()
        self.title = title
        self.screen = pygame.display.set_mode((STAGE_W, STAGE_H))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 14, bold=True)
        self.vars = {}
        self.lists = {}
        self.sprites = {}
        self.layers = []          # back ... front
        self.watchers = []
        self.pen_layer = pygame.Surface((STAGE_W, STAGE_H), pygame.SRCALPHA)
        self.background = (255, 255, 255)
        self.threads = []
        self.flag_scripts = []    # (script, sprite)
        self.key_scripts = []     # (key, script, sprite)
        self.msg_scripts = []     # (message, script, sprite)
        self.keymap = _build_keymap()
        self.frame = 0
        self.keys_down = set()
        self.running = True
        self.stopped = False
        self.banner = None        # optional function -> text shown big in the centre
        # help / title screen (paged overlay; the game is paused while it is open)
        self.help_pages = []      # [(title, [lines])]; a line starting with '#' is a sub-heading
        self.start_options = []   # [(key letter, label, [keys held for a moment at the start])]
        self.help_visible = False
        self.help_page = 0
        self.started = False      # becomes True once the player leaves the title screen
        self.inject = {}          # keycode -> frames left (keys we press for the player)
        self.hint = "F1 = help"
        self.big_font = pygame.font.SysFont('arial', 64, bold=True)
        self.help_title_font = pygame.font.SysFont('arial', 26, bold=True)
        self.help_font = pygame.font.SysFont('arial', 14, bold=True)
        self.small_font = pygame.font.SysFont('arial', 12, bold=True)

    # ---- construction ------------------------------------------------------
    def add_sprite(self, *a, **kw):
        sp = Sprite(self, *a, **kw)
        self.sprites[sp.name] = sp
        self.layers.append(sp)
        return sp

    def on_flag(self, sprite):
        def deco(fn):
            self.flag_scripts.append((fn, sprite)); return fn
        return deco

    def on_key(self, sprite, key):
        def deco(fn):
            self.key_scripts.append((key, fn, sprite)); return fn
        return deco

    def on_message(self, sprite, msg):
        def deco(fn):
            self.msg_scripts.append((msg, fn, sprite)); return fn
        return deco

    # ---- helpers used by scripts --------------------------------------------
    def now(self):
        """game time in seconds (frame based, so 'wait' stays consistent if the PC is slow)"""
        return self.frame / FPS

    def mouse_xy(self):
        mx, my = pygame.mouse.get_pos()
        return mx - STAGE_W / 2, STAGE_H / 2 - my

    def key_pressed(self, key):
        k = self.keymap.get(key)
        return k is not None and k in self.keys_down

    def broadcast(self, msg):
        for m, fn, sp in self.msg_scripts:
            if m == msg:
                self._start(fn, sp)

    def stop_all(self):
        self.threads.clear()
        self.stopped = True

    def clear_pen(self):
        self.pen_layer.fill((0, 0, 0, 0))

    def _start(self, fn, sprite):
        for t in self.threads:
            if t.script is fn:
                t.gen = fn(sprite)         # restart, as Scratch does
                t.alive = True
                return
        self.threads.append(Thread(fn, sprite))

    # ---- main loop ------------------------------------------------------------
    def green_flag(self):
        self.threads.clear()
        self.stopped = False
        for fn, sp in self.flag_scripts:
            self.threads.append(Thread(fn, sp))

    def _step(self):
        # scripts: one pass for every thread
        for t in list(self.threads):
            if t in self.threads:
                t.step()
        self.threads = [t for t in self.threads if t.alive]

        # keys pressed on the player's behalf (start-screen options) wear off
        for k in list(self.inject):
            self.inject[k] -= 1
            if self.inject[k] <= 0:
                del self.inject[k]
                self.keys_down.discard(k)

        # "when <key> pressed": start the script if the key is held and idle
        for key, fn, sp in self.key_scripts:
            k = self.keymap.get(key)
            if k is not None and k in self.keys_down and not any(t.script is fn for t in self.threads):
                self.threads.append(Thread(fn, sp))

    def _draw(self):
        self.screen.fill(self.background)
        self.screen.blit(self.pen_layer, (0, 0))   # pen trails sit under the sprites
        for sp in self.layers:                     # layers[0] is the back-most sprite
            sp.draw(self.screen)
        if self.started or not self.help_visible:     # (no stale numbers behind the title screen)
            for w in self.watchers:
                w.draw(self.screen, self.font)
        if self.banner:
            text = self.banner()
            if text:
                for dx, dy, col in ((3, 3, (0, 0, 0)), (0, 0, (220, 30, 30))):
                    img = self.big_font.render(text, True, col)
                    self.screen.blit(img, ((STAGE_W - img.get_width()) // 2 + dx,
                                           (STAGE_H - img.get_height()) // 2 + dy))
        if self.help_visible:
            self._draw_help()
        elif self.hint:
            img = self.small_font.render(self.hint, True, (110, 110, 110))
            self.screen.blit(img, (STAGE_W - img.get_width() - 6, STAGE_H - img.get_height() - 4))
        pygame.display.flip()

    # ---- help screen ----------------------------------------------------------------
    def open_help(self, page=0):
        self.help_visible = True
        self.help_page = page
        self.keys_down.clear()

    def close_help(self):
        self.help_visible = False
        self.started = True
        self.keys_down.clear()

    def _help_key(self, key):
        """handle a key while the help screen is open"""
        n = len(self.help_pages)
        if key in (pygame.K_RIGHT, pygame.K_TAB, pygame.K_PAGEDOWN) and n:
            self.help_page = (self.help_page + 1) % n
        elif key in (pygame.K_LEFT, pygame.K_PAGEUP) and n:
            self.help_page = (self.help_page - 1) % n
        elif key == pygame.K_ESCAPE and self.started:
            self.close_help()
        elif key == pygame.K_ESCAPE:
            self.running = False
        else:
            if not self.started:                    # title screen: pick how to start
                for letter, _label, keys in self.start_options:
                    if key == getattr(pygame, "K_" + letter.lower()):
                        for kk in keys:
                            code = self.keymap[kk]
                            self.keys_down.add(code)
                            self.inject[code] = 5
                        self.help_visible = False
                        self.started = True
                        return
            if key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_F1) or self.started:
                self.close_help()

    def _draw_help(self):
        panel = pygame.Surface((STAGE_W - 24, STAGE_H - 20), pygame.SRCALPHA)
        panel.fill((15, 20, 45, 235))
        pygame.draw.rect(panel, (255, 210, 60), panel.get_rect(), 2)
        self.screen.blit(panel, (12, 10))
        if not self.help_pages:
            return
        title, lines = self.help_pages[self.help_page]
        img = self.help_title_font.render(title, True, (255, 210, 60))
        self.screen.blit(img, ((STAGE_W - img.get_width()) // 2, 18))
        y = 56
        for line in lines:
            if line.startswith("#"):
                y += 4
                img = self.help_font.render(line[1:].strip(), True, (120, 200, 255))
                self.screen.blit(img, (28, y))
            elif "\t" in line:
                keys, text = line.split("\t", 1)
                k = self.help_font.render(keys, True, (255, 255, 255))
                t = self.help_font.render(text, True, (205, 210, 225))
                self.screen.blit(k, (28, y))
                self.screen.blit(t, (104, y))
            else:
                img = self.help_font.render(line, True, (205, 210, 225))
                self.screen.blit(img, (28, y))
            y += 18
        foot = ("<- ->  turn page    ENTER / SPACE  play" if not self.started else
                "<- ->  turn page    any other key  back to the game")
        img = self.small_font.render(f"{foot}      page {self.help_page + 1}/{len(self.help_pages)}",
                                     True, (255, 210, 60))
        self.screen.blit(img, ((STAGE_W - img.get_width()) // 2, STAGE_H - 34))

    def run(self, max_frames=None, on_frame=None, realtime=True):
        self.green_flag()
        if self.help_pages and not self.started:
            self.help_visible = True              # title screen first
        n = 0
        while self.running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN:
                    if self.help_visible:
                        self._help_key(ev.key)
                    elif ev.key == pygame.K_F1 and self.help_pages:
                        self.open_help()
                    elif ev.key == pygame.K_ESCAPE:
                        self.running = False
                    else:
                        self.keys_down.add(ev.key)
                elif ev.type == pygame.KEYUP:
                    self.keys_down.discard(ev.key)
                elif ev.type == pygame.WINDOWFOCUSLOST:
                    self.keys_down.clear()
            if self.help_visible:                  # paused: game time stands still
                self._draw()
            else:
                self._step()
                self._draw()
                self.frame += 1
            n += 1
            if on_frame:
                on_frame(n)
            if max_frames and n >= max_frames:
                break
            if realtime:
                self.clock.tick(FPS)
        pygame.quit()
