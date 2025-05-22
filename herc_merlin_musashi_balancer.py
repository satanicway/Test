#!/usr/bin/env python3
# ------------------------------------------------------------------------------
#  herc_merlin_musashi_balancer.py – accuracy-first monster tuner
#  2025-05-18  (dual-phase optimiser + 2 h watchdog; fully self-contained)
# ------------------------------------------------------------------------------

import random, copy, time, math
from collections import Counter
from enum import Enum, auto

# ╭───────────────────────── 0. INITIAL GAUNTLET STATE ─────────────────────────╮

from dataclasses import dataclass
from typing import Callable, Optional, List


@dataclass
class Enemy:
    """Description of a single enemy archetype."""

    hp: int
    defense: int
    band: List[int]
    vuln: Optional[CardType] = None
    ability: Optional[Callable[["Hero", dict], None]] = None


@dataclass
class Wave:
    """Descriptor for one combat wave."""

    count: int
    enemy: Enemy


BAND_CAP = {1: 12, 2: 7, 3: 6}  # max damage per band by group size

# enemy waves (count, Enemy)
WAVES: List[Wave] = [
    Wave(3, Enemy(1, 4, [1, 0, 1, 0])),
    Wave(2, Enemy(1, 4, [1, 1, 1, 2])),
    Wave(2, Enemy(1, 4, [0, 2, 0, 0])),
    Wave(1, Enemy(4, 4, [6, 1, 1, 1])),
    Wave(3, Enemy(1, 4, [1, 0, 6, 1])),
    Wave(2, Enemy(1, 4, [5, 0, 2, 3])),
    Wave(2, Enemy(1, 5, [3, 1, 2, 0])),
    Wave(1, Enemy(4, 4, [2, 0, 1, 0])),
]  # vulnerabilities and abilities can be filled per-wave if needed


# target bands
TARGET_LO, TARGET_HI = 0.45, 0.60        # desired hero win-rate window
MIN_THREAT           = 0.33              # min wave chance to deal ≥1 damage

# optimiser run-time parameters
TIME_LIMIT   = 2*3600          # 2 h without improvement → stop and print best
STALL_MAX    = 2_000           # proposals rejected before jump grows
MAX_JUMP_CAP = 7               # absolute max ±delta per step

# hero fate parameters
FATE_MAX = 10

class CardType(Enum):
    MELEE = auto()
    RANGED = auto()
    UTIL = auto()

# ╭───────────────────────── 1. DICE & HELPER FUNCTIONS ─────────────────────────╮
RNG = random.Random()
d8  = lambda: RNG.randint(1, 8)

def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def roll_hits(n: int, DF: int, mod: int = 0, *, hero=None, rerolls: int = 0) -> int:
    """Roll n dice against DF with optional rerolls consuming hero fate."""
    dmg = 0
    for _ in range(n):
        r = max(1, min(8, d8() + mod))
        while r < DF and rerolls and hero and hero.spend_fate(1):
            rerolls -= 1
            r = max(1, min(8, d8() + mod))
        if r >= DF:
            dmg += 2 if r == 8 else 1
    return dmg

# ╭───────────────────────── 2. CARD & DECK LAYERS ──────────────────────────────╮
class Card:
    __slots__ = ('name', 'ctype', 'dice', 'armor', 'tags', 'fx')
    def __init__(self, name, ctype, dice=0, armor=0, tags=None, fx=None):
        self.name, self.ctype, self.dice, self.armor = name, ctype, dice, armor
        self.tags = tags or {}
        self.fx   = fx
    def __repr__(self): return self.name

class Deck:
    MAX_HAND = 7
    def __init__(self, cards):
        self.draw_pile = cards[:]
        RNG.shuffle(self.draw_pile)
        self.hand, self.disc = [], []
    def _draw(self, n: int):
        while n and len(self.hand) < self.MAX_HAND:
            if not self.draw_pile:
                RNG.shuffle(self.disc)
                self.draw_pile, self.disc = self.disc, []
                if not self.draw_pile: break
            self.hand.append(self.draw_pile.pop())
            n -= 1
    def start_combat(self): self._draw(4 if RNG.random() < .6 else 3)
    def exch_draw(self):    self._draw(3)
    def pop_first(self, ctype):
        for i, c in enumerate(self.hand):
            if c.ctype == ctype:
                return self.hand.pop(i)
        return None

def armor_add(x): return lambda h, ctx: setattr(h, 'armor_pool', h.armor_pool + x)
def atk(name, ctype, dice, armor=0, fx=None, **tags):
    return Card(name, ctype, dice, armor, tags, fx)

# ╭───────────────────────── 3. HERO & CARD POOLS ───────────────────────────────╮
class Hero:
    def __init__(self, key, max_hp, plate, base_cards, upg_pool):
        self.key, self.maxHP, self.plate = key, max_hp, plate
        self.base_cards, self.upg_pool = base_cards[:], upg_pool[:]
        self.reset_between_runs()
    def reset_between_runs(self):
        self.hp = self.maxHP
        self.deck = Deck(self.base_cards[:])
        self.fate = 0
    def gain_upgrades(self):
        n = 2 if RNG.random() < .5 else 1
        self.deck.draw_pile.extend(RNG.sample(self.upg_pool, n))

    def gain_fate(self, n: int):
        self.fate = min(self.fate + n, FATE_MAX)

    def spend_fate(self, n: int = 1) -> bool:
        if self.fate >= n:
            self.fate -= n
            return True
        return False

# ── Hercules cards
HERC_COMMON = (
    [atk("Pillar", CardType.MELEE, 2)] * 3 +
    [atk("Strangle", CardType.MELEE, 1,
         fx=lambda h, ctx: ctx.__setitem__('bleed', ctx.get('bleed', 0) + 1))] +
    [atk("Demigod", CardType.MELEE, 1, armor=1, fx=armor_add(1))] * 3 +
    [atk("SkyJav", CardType.RANGED, 2,
         fx=lambda h, ctx: ctx.__setitem__('sky', ctx.get('sky', 0) + 1))] +
    [atk("Spin", CardType.MELEE, 1)] * 2 +
    [atk("Atlas", CardType.UTIL, 0, armor=3, fx=armor_add(3))] * 2
)
HERC_UPG = [atk(f"HUpg{i}", CardType.MELEE, 3) for i in range(1, 31)]
hercules = Hero("Hercules", 25, 1.0, HERC_COMMON, HERC_UPG)

# ── Merlin cards
MER_COMMON = (
    [atk("Volley", CardType.RANGED, 1)] * 3 +
    [atk("Warden", CardType.MELEE, 2, armor=1, fx=armor_add(1))] +
    [atk("Weaver", CardType.RANGED, 1,
         fx=lambda h, ctx: ctx['efx'].__setitem__('reroll', ctx['efx'].get('reroll', 0) + 2))] * 2 +
    [atk("Staff", CardType.MELEE, 1)] * 2 +
    [atk("Mists", CardType.RANGED, 1,
         fx=lambda h, ctx: ctx.__setitem__('spell+', ctx.get('spell+', 0) + 1))] * 3 +
    [atk("Circle", CardType.RANGED, 1,
         fx=lambda h, ctx: ctx['cfx'].__setitem__('global_reroll', True))]
)
MER_UPG = [atk(f"MUpg{i}", CardType.RANGED, 3) for i in range(1, 31)]
merlin = Hero("Merlin", 15, 0.5, MER_COMMON, MER_UPG)

# ── Musashi cards  (compact pool)
MUS_COMMON = (
    [atk("Swallow-Cut", CardType.MELEE, 1)] * 2 +
    [atk("Cross-River", CardType.MELEE, 2)] * 2 +
    [atk("Heaven-Earth", CardType.MELEE, 2)] * 2 +
    [atk("Water Parry", CardType.MELEE, 1, armor=1)] * 2 +
    [atk("Dual-Moon Guard", CardType.UTIL, 0, armor=1)] * 2 +
    [atk("Wind-Read", CardType.MELEE, 1)] * 2
)

# 10× common, 10× uncommon, 8× rare (weights 3-2-1 as in earlier draft)
common = [("Gate-Breaker",2,0),("Battojutsu",2,2),("Scroll-Cut",3,0),
          ("Chance-Blade",0,0),("Susanoo",3,0),("Water-Mirror",0,0),
          ("Spirit-Cleaver",2,0),("Iron-Will",3,0),
          ("Ghost-Step",3,0),("Heaven-Dragon",2,0)]
uncommon=[("Dragon Slice",3,0),("River Reflex",0,0),("Two-Heaven",4,0),
          ("Crescent Guard",0,0),("Mountain Stance",0,0),("Mirror-Flow",0,0),
          ("Heaven Blade",0,0),("Ascending Venge",0,0),
          ("Menacing Step",0,0),("Iron-Shell",0,0)]
rare    =[("Final-Dragon",2,0),("Five-Ring",2,0),("Flash 2 Moons",5,0),
          ("Wanderer",6,0),("Formless",0,0),("Stone Lotus",4,0),
          ("Twin-Descent",0,0),("Edge Harmony",4,0),
          ("Two-as-One",4,0),("Perfection",0,4)]

MUS_UPG=[]
for n,d,a in common:    MUS_UPG += [atk(n,CardType.MELEE,d,a)]*3
for n,d,a in uncommon:  MUS_UPG += [atk(n,CardType.MELEE,d,a)]*2
for n,d,a in rare:      MUS_UPG.append(atk(n,CardType.MELEE,d,a))

musashi = Hero("Musashi", 20, 1.0, MUS_COMMON, MUS_UPG)

HEROES = [hercules, merlin, musashi]

# ╭───────────────────────── 4. FIGHT ENGINE ──────────────────────────╮

def fight_one(proto: Hero, record=False):
    h = copy.deepcopy(proto)
    h.reset_between_runs()
    h.deck.start_combat()
    wave_hit = [False] * len(WAVES)
    cfx = {}

    for w, wave in enumerate(WAVES):
        enemies = [copy.deepcopy(wave.enemy) for _ in range(wave.count)]
        ctx = {'enemies': enemies, 'bleed': 0, 'sky': 0, 'cfx': cfx, 'efx': {}}
        for exch in range(4):
            ctx['efx'] = {}
            h.armor_pool = 0
            if exch:
                h.deck.exch_draw()

            # UTIL
            while True:
                c = h.deck.pop_first(CardType.UTIL)
                if not c: break
                h.armor_pool += c.armor
                if c.fx: c.fx(h, ctx)
                h.deck.disc.append(c)

            # RANGED
            while True:
                c = h.deck.pop_first(CardType.RANGED)
                if not c or not ctx['enemies']: break
                rer = ctx['efx'].pop('reroll', 0)
                if ctx['cfx'].get('global_reroll'):
                    rer += c.dice
                tgt = ctx['enemies'][0]
                dmg = roll_hits(c.dice + ctx['sky'], tgt.defense, hero=h, rerolls=rer)
                if c.fx:
                    c.fx(h, ctx)
                ctx['enemies'][0].hp -= dmg * (2 if tgt.vuln == CardType.RANGED else 1)
                if ctx['enemies'][0].hp <= 0:
                    ctx['enemies'].pop(0)
                h.deck.disc.append(c)
            if not ctx['enemies']:
                break

            # MONSTER STRIKE
            raw_total = 0
            for e in ctx['enemies']:
                if e.ability:
                    e.ability(h, ctx)
                raw_total += max(0, e.band[(d8() - 1)//2] - h.plate)
            soak = min(raw_total, h.armor_pool)
            raw_total -= soak
            if raw_total:
                wave_hit[w] = True
            h.hp -= raw_total
            if h.hp <= 0:
                return False, (wave_hit if record else None)

            # MELEE
            while True:
                c = h.deck.pop_first(CardType.MELEE)
                if not c or not ctx['enemies']: break
                h.armor_pool += c.armor
                rer = ctx['efx'].pop('reroll', 0)
                if ctx['cfx'].get('global_reroll'):
                    rer += c.dice
                tgt = ctx['enemies'][0]
                dmg = roll_hits(c.dice + ctx['sky'], tgt.defense, hero=h, rerolls=rer)
                if c.fx:
                    c.fx(h, ctx)
                ctx['enemies'][0].hp -= dmg * (2 if tgt.vuln == CardType.MELEE else 1)
                if ctx['enemies'][0].hp <= 0:
                    ctx['enemies'].pop(0)
                h.deck.disc.append(c)

            # BLEED tick
            if ctx['bleed'] and ctx['enemies']:
                ctx['enemies'][0].hp -= ctx['bleed']
                if ctx['enemies'][0].hp <= 0:
                    ctx['enemies'].pop(0)

            if not ctx['enemies']:
                break

        if ctx['enemies']:
            return False, (wave_hit if record else None)

        h.gain_upgrades()

    return True, (wave_hit if record else None)

# ╭───────────────────────── 5. SAMPLERS & METRICS ────────────────────╮
def _sample(n: int):
    wins = Counter(); threats = [0] * len(WAVES)
    for hero in HEROES:
        for _ in range(n):
            ok, waves = fight_one(hero, record=True)
            if ok: wins[hero.key] += 1
            for i, f in enumerate(waves):
                threats[i] += f
    rates = {h.key: wins[h.key] / n for h in HEROES}
    threats = [t / (n * len(HEROES)) for t in threats]
    return rates, threats


def sample_rates(temp: float):
    """adaptive N based on temperature"""
    if temp >= .5:
        n = 300
    elif temp >= .2:
        n = 600
    else:
        n = 1000
    return _sample(n)


def total_error(t_rates, t_thr, s_rates, s_thr):
    err = 0.0
    for hero in HEROES:
        target = 0.525
        err += (t_rates[hero.key] - target) ** 2
        err += (s_rates[hero.key] - target) ** 2
    for x in t_thr + s_thr:
        if x < MIN_THREAT:
            err += (MIN_THREAT - x) ** 2
    return err


def meets(rates, thr):
    return (
        all(TARGET_LO <= v <= TARGET_HI for v in rates.values()) and
        all(x >= MIN_THREAT for x in thr)
    )


def blocker(rates, thr):
    out = []
    for h, v in rates.items():
        if v < TARGET_LO or v > TARGET_HI:
            out.append(f"{h} {v:.2f}")
    for i, t in enumerate(thr):
        if t < MIN_THREAT:
            out.append(f"wave-{i+1} threat {t:.2f}")
    return ", ".join(out) if out else "-"

# ╭───────────────────────── 6. BAND POST-PROCESS ─────────────────────╮
def band_fix():
    for wave in WAVES:
        cap = BAND_CAP[wave.count]
        row = wave.enemy.band
        seen0 = False
        for j, x in enumerate(row):
            if x == 0 and seen0:
                row[j] = 1
            seen0 |= (x == 0)
            row[j] = clamp(row[j], 0, cap)

# ╭───────────────────────── 7. OPTIMISER ─────────────────────────────╮
def optimise():
    band_fix()
    best_HP = [w.enemy.hp for w in WAVES]
    best_B  = [w.enemy.band[:] for w in WAVES]
    best_err = float('inf')
    last_improve = time.time()
    start = last_improve

    T = 1.0           # initial “temperature” for simulated annealing
    cool = 0.997      # cooling factor
    stall = 0         # proposals rejected si
    stall = 0         # proposals rejected since last improve
    gen = 0

    while True:
        # watch-dog
        if time.time() - last_improve > TIME_LIMIT:
            print("\n◆ Watch-dog (2 h no progress) – returning best so far")
            break

        # enlarge jump when stuck
        jump = 1 + min(MAX_JUMP_CAP - 1, stall // STALL_MAX)

        # propose *both* an HP and a Band tweak
        hp_idx = RNG.randrange(len(WAVES))
        b_w    = RNG.randrange(len(WAVES))
        b_j    = RNG.randrange(4)

        d_hp = RNG.choice([-jump, jump])
        d_bd = RNG.choice([-jump, jump])

        WAVES[hp_idx].enemy.hp = clamp(WAVES[hp_idx].enemy.hp + d_hp, 1, 15)
        cap = BAND_CAP[WAVES[b_w].count]
        WAVES[b_w].enemy.band[b_j] = clamp(WAVES[b_w].enemy.band[b_j] + d_bd, 0, cap)

        # evaluate – Code-1 & Code-2 use the same sampler here
        t_rates, t_thr = sample_rates(T)
        s_rates, s_thr = sample_rates(T)

        err = total_error(t_rates, t_thr, s_rates, s_thr)
        dE  = err - best_err
        accept = (dE < 0) or (RNG.random() < math.exp(-dE / max(T, 1e-6)))

        if accept:
            if dE < 0:
                best_err = err
                best_HP  = [w.enemy.hp for w in WAVES]
                best_B   = [w.enemy.band[:] for w in WAVES]
                last_improve = time.time()
                stall = 0
                print(f"G{gen:05d} obj={best_err:.4f} T={T:.3f}")
                print("  blocker:", blocker(t_rates, t_thr))
                if meets(t_rates, t_thr) and meets(s_rates, s_thr):
                    print("\n=== FINISHED – all constraints satisfied ===")
                    break
            else:
                stall += 1
        else:
            # revert
            for i, wave in enumerate(WAVES):
                wave.enemy.hp = best_HP[i]
                wave.enemy.band = best_B[i][:]
            stall += 1

        # temperature schedule
        if T > 0.001:
            T *= cool
        if T < 0.05:  # phase-B: hill-climb, no uphill moves accepted
            cool = 1.0

        gen += 1
        if gen % 1000 == 0:
            elapsed = time.time() - start
            print(f"Generation {gen} - elapsed {int(elapsed)}s")

    # final dump
    print("\nBest error:", best_err)
    print("HP  :", best_HP)
    print("BANDS:")
    for row in best_B:
        print(" ", row)
    print(f"Runtime: {time.time() - last_improve:.1f}s since last improvement")

# ╭───────────────────────── 8. MAIN ──────────────────────────────────╮
if __name__ == "__main__":
    optimise()
