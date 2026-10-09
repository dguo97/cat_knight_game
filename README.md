# Cat Knight Against Buffalo (Python version)

Python / pygame translation of the Scratch 1.x project `Cat_Knight_Against_Buffalo.sb`.

## Run

    pip install -r requirements.txt
    python cat_knight_against_buffalo.py

Esc or closing the window quits.

## Files

| File | What it is |
|------|-----------|
| `cat_knight_against_buffalo.py` | The game: variables, 43 sprites and all their scripts, translated block-for-block |
| `scratch_runtime.py` | Small Scratch-style engine (stage, sprites, collision, effects, threads) |
| `assets/` | The 60 costume images, extracted from the .sb file as PNGs |

## Controls

The game opens on a title screen, and **F1** opens the in-game help at any time (the game
pauses while it is open; use the left/right arrow keys to turn its five pages).

**Start:** `ENTER` = Easy (the buffalo only wanders), `B` = Battle (the buffalo charges you),
`A` = Hard (it charges you and arrows rain down). In the original these modes were switched
on by secretly holding `U`+`L` and `P`+`Q` at the start.

**Moving:** arrow keys. `1` / `2` / `3` change the cat's form (balanced / fastest / hardest-hitting).

**Special attacks** (cost POWER, which refills about 10 a second, max 100):
`F` leap (1), `Z` bolt (5), `X` homing shot (10), `D` summon (10),
`SPACE` big blast (80, but halves your TIME), `G` form 1 finisher (100, divides TIME by 15).

**Secrets** (all listed in the help screen): hold `Q`+`I` for a power-up that unlocks form 4
(`T` drain, `W` swarm, huge `SPACE` blasts); hold `H`+`E`+`L`+`P` or `W`+`I`+`N` for the two plane modes.

HUD: `1 TIME` (countdown), `1 POWER`, `2 BLOOD` (the buffalo's health). The round ends when time
runs out ("YOU LOSE") or the buffalo's blood reaches zero ("YOU WIN!").

## How the translation works

* Each Scratch script is a Python generator. A `yield` is where Scratch switches to
  another script (end of a loop pass, `wait`, `wait until`), so one loop pass is one frame.
* Scratch blocks map to small methods: `forward:` -> `self.move()`, `touching:` ->
  `self.touching()` (pixel-perfect), `glide` -> `yield from glide(...)`, and so on.
* Variables live in the dict `V`; sprites are looked up by their Scratch name in `S`.
* Sprite names are the original ones (角色 = "sprite").
* Tweakables at the top of `scratch_runtime.py`: `FPS` (game speed) and `FENCE`.

## Notes / differences from Scratch

* Removed as pointless: 12 empty scripts, and the hidden `L`+`U`+`Y` script (it *added* blood to the
  buffalo, i.e. worked against the player).
* Scripts that had no "when ..." hat block in the original (loose blocks lying on the
  scripting area) never ran in Scratch either, so they are not translated.
* Sounds are not used by any block in the project, so none are included.
* Graphic effects (whirl, fisheye, pixelate, color, ghost) are re-implemented with numpy and
  look close to, but not identical to, Scratch's.
* Holding a key keeps re-starting its "when key pressed" script once the previous run ends.
