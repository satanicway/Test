#!/usr/bin/env python3
"""
Spellrift Dungeons alpha balance simulator (v0.4.2-inspired).

Scope:
- Simulates 4 fixed heroes through up to 7 rooms.
- Ignores board movement/grid/LOS details by assumption (average engagement model).
- Models dice, specials, LP, initiative, seals, taint/surges, villain attacks, conditions,
  gate/room selection, fragment -> boon drafting, and monster level scaling.
- Runs Monte Carlo and reports room-wise averages and boon CP contribution.

This is an approximation engine intended for balance exploration, not a strict rules validator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, Counter
import random
import statistics
from typing import Dict, List, Optional, Tuple

# ---------- Combat point model (from GDD section 21) ----------
CP_DAMAGE = 1.0
CP_HP = 1.0
CP_LP = 1.0
CP_ARMOR = 1.5
CP_DIE = 3.0
CP_SPECIAL_COST = 2.0

MAX_ROOMS = 7
DEFAULT_SIMS = 20_000

COLORS = ["red", "green", "grey", "blue", "yellow"]


@dataclass
class Attack:
    name: str
    base_dice: Dict[str, int]
    lp_cost: int = 0
    lp_gain: int = 0
    range_type: str = "melee"  # only used for heuristics
    special_rules: Dict[str, int] = field(default_factory=dict)
    full_spender: bool = False


@dataclass
class HeroTemplate:
    name: str
    max_hp: int
    attacks: List[Attack]
    relic_die_color: str


@dataclass
class VillainTemplate:
    name: str
    hp: int
    armor: int
    damage: int
    target_rule: str
    vulnerability: Optional[str]
    resistance: Optional[str] = None
    effects: Tuple[str, ...] = ()


@dataclass
class Boon:
    name: str
    color: str
    dice_bonus: Dict[str, int] = field(default_factory=dict)
    # tiny subset of effects modeled consistently across cards
    on_attack_flat_bonus: int = 0
    on_color_special_bonus_damage: Dict[str, int] = field(default_factory=dict)
    on_color_special_bonus_lp: Dict[str, int] = field(default_factory=dict)
    on_kill_lp: int = 0


@dataclass
class Enemy:
    template: VillainTemplate
    hp: int
    armor: int
    damage: int
    level: int
    conditions: Counter = field(default_factory=Counter)

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class HeroState:
    template: HeroTemplate
    hp: int
    lp: int = 0
    armor: int = 0
    alive: bool = True
    conditions: Counter = field(default_factory=Counter)
    boons: List[Boon] = field(default_factory=list)
    damage_done_this_room: float = 0.0


@dataclass
class Gate:
    name: str
    gate_type: str
    threat: int
    fragments: List[str]
    start_lp: int = 0
    start_heal: int = 0


# ---------- Data: heroes ----------
HEROES: List[HeroTemplate] = [
    HeroTemplate(
        "Hercules",
        25,
        [
            Attack("Pillar-Breaker Blow", {"red": 3}, lp_gain=1, special_rules={"red": 1}),
            Attack("Club Spin", {"green": 2}, lp_gain=2, special_rules={"green": 1}),
            Attack("Colossus Smash", {"red": 4}, lp_cost=2, special_rules={"red": 2}),
            Attack("True Might", {"yellow": 4, "red": 3}, lp_cost=3, full_spender=True),
        ],
        relic_die_color="red",
    ),
    HeroTemplate(
        "Merlin",
        18,
        [
            Attack("Arcane Volley", {"blue": 2}, lp_gain=1, range_type="ranged", special_rules={"blue": 1}),
            Attack("Spiritual Gifts", {"grey": 2}, lp_gain=2, range_type="ranged"),
            Attack("Whispers of the Wyrd", {"grey": 2}, lp_cost=2, range_type="ranged"),
            Attack("Avalon's Light", {"blue": 7}, lp_cost=3, full_spender=True),
        ],
        relic_die_color="blue",
    ),
    HeroTemplate(
        "Joan d’Arc",
        20,
        [
            Attack("Blade of Lys", {"yellow": 1, "red": 2}, lp_gain=1, special_rules={"yellow": 1, "red": 1}),
            Attack("Holy Bolt", {"yellow": 2}, lp_gain=2, range_type="ranged", special_rules={"yellow": 1}),
            Attack("Vanguard Strike", {"red": 3}, lp_cost=3, range_type="ranged"),
            Attack("Divine Punishment", {"yellow": 4}, lp_cost=3, full_spender=True),
        ],
        relic_die_color="yellow",
    ),
    HeroTemplate(
        "Anansi",
        20,
        [
            Attack("Guile Strike", {"green": 2}, lp_gain=1, special_rules={"green": 1}),
            Attack("Story-weaver", {"yellow": 2}, lp_gain=2, special_rules={"yellow": 1}),
            Attack("Snare and Sever", {"green": 3, "blue": 2}, lp_cost=2, range_type="ranged", special_rules={"green": 2}),
            Attack("The Last Thread", {"green": 3}, lp_cost=3, full_spender=True),
        ],
        relic_die_color="green",
    ),
]


VILLAINS: Dict[str, VillainTemplate] = {
    "Voidling": VillainTemplate("Voidling", hp=2, armor=0, damage=2, target_rule="closest", vulnerability=None, effects=("drain_lp",)),
    "Shadow Spinner": VillainTemplate("Shadow Spinner", hp=4, armor=0, damage=3, target_rule="low_hp", vulnerability="red", effects=("staggered",)),
    "Void Soldier": VillainTemplate("Void Soldier", hp=5, armor=0, damage=3, target_rule="closest", vulnerability="blue", effects=("self_toughened",)),
    "Dark Wizard": VillainTemplate("Dark Wizard", hp=10, armor=1, damage=3, target_rule="high_hp", vulnerability="yellow", effects=("ignore_armor",)),
    "Shadow Banshee": VillainTemplate("Shadow Banshee", hp=10, armor=0, damage=4, target_rule="high_lp", vulnerability="grey", effects=("terror",)),
    "Void Treant": VillainTemplate("Void Treant", hp=12, armor=2, damage=3, target_rule="closest", vulnerability="green", effects=("splash",)),
}

LEVEL_MODS = {
    1: (0, 0, 0),
    2: (0, 2, 1),
    3: (1, 5, 3),
    4: (1, 7, 5),
    5: (2, 10, 7),
    6: (2, 15, 10),
}

# Gate subset with key numeric impacts retained
STANDARD_GATES = [
    Gate("Spiked Gate", "basic", 2, ["red", "red"], start_lp=1),
    Gate("Cursed Gate", "basic", 2, ["blue", "blue"], start_lp=1),
    Gate("Reinforced Gate", "basic", 2, ["red", "yellow"], start_lp=1),
    Gate("Predator's Gate", "basic", 2, ["red", "green"], start_lp=1),
    Gate("Assassin's Gate", "basic", 2, ["green", "yellow"], start_heal=2),
    Gate("Painful Gate", "basic", 2, ["grey", "yellow"], start_heal=1, start_lp=1),
    Gate("Sturdy Gate", "basic", 3, ["red", "blue", "green"], start_heal=1, start_lp=2),
    Gate("Glutton's Gate", "basic", 3, ["blue", "green", "grey"], start_heal=2, start_lp=1),
    Gate("Glorious Gate", "basic", 3, ["red", "grey", "yellow"], start_lp=3),
    Gate("Shattering Gate", "basic", 3, ["red", "green", "yellow"], start_lp=2),
    Gate("Vengeance's Gate", "elite", 5, ["red", "green"], start_lp=2),
    Gate("Banner's Gate", "elite", 5, ["red", "grey"], start_heal=2),
    Gate("Fateful Gate", "elite", 5, ["blue", "yellow"], start_lp=1),
    Gate("Dampened Gate", "elite", 5, ["green", "green"], start_lp=0),
    Gate("Large Gate", "elite", 5, ["grey", "grey"], start_lp=1),
    Gate("Temple of Courage", "temple", 1, ["yellow"], start_lp=1),
    Gate("Temple of Mercy", "temple", 1, ["grey"], start_heal=1),
    Gate("Temple of Clarity", "temple", 1, ["blue"], start_lp=1),
    Gate("Temple of Fire", "temple", 1, ["green"], start_lp=1),
    Gate("Temple of Purity", "temple", 1, ["yellow"], start_lp=1),
]
NEXUS_GATES = [
    Gate("Nexus Denied Strength", "nexus", 3, ["blue", "grey"], start_lp=1, start_heal=1),
    Gate("Nexus Denied Magic", "nexus", 3, ["green", "yellow"], start_lp=2),
    Gate("Nexus Denied Speed", "nexus", 3, ["red", "blue"], start_lp=1),
    Gate("Nexus Denied Spirit", "nexus", 3, ["yellow", "yellow"], start_heal=2),
    Gate("Nexus Denied Faith", "nexus", 3, ["blue", "grey", "yellow"], start_lp=2, start_heal=1),
    Gate("Nexus Denied Destiny", "nexus", 4, ["red", "red", "blue"], start_lp=3),
]

ROOM_SPAWNS = {
    1: ["Void Soldier", "Shadow Spinner"],
    2: ["Void Soldier", "Shadow Spinner", "Shadow Spinner"],
    3: ["VoidTreantFix", "Void Soldier", "Shadow Spinner", "Dark Wizard"],
    4: ["Void Treant", "Void Soldier", "Shadow Spinner", "Dark Wizard", "Shadow Banshee"],
    5: ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner", "Dark Wizard"],
}

# ---------- Boon pools (simplified mechanical projection of listed cards) ----------
def boon_catalog() -> Dict[str, List[Boon]]:
    return {
        "red": [
            Boon("Mjolnir’s Spark", "red", {"red": 1}, on_color_special_bonus_damage={"red": 5}),
            Boon("Hammering Thunder", "red", {"red": 1}, on_attack_flat_bonus=1),
            Boon("Mighty Storm", "red", {"red": 1}, on_attack_flat_bonus=1),
            Boon("Stormbreaker", "red", {}, on_color_special_bonus_damage={"red": 4}),
            Boon("War God’s Might", "red", {"red": 2}),
            Boon("War God’s Power", "red", {"red": 2}),
            Boon("Forge of War", "red", {"red": 1}),
            Boon("Onslaught", "red", {}, on_color_special_bonus_damage={"red": 5}),
            Boon("Tidal Slam", "red", {}, on_color_special_bonus_damage={"red": 3}),
            Boon("Maelstrom Crash", "red", {"red": 1}, on_color_special_bonus_damage={"red": 2}),
            Boon("Far Tide", "red", {"red": 1}),
            Boon("Command the Currents", "red", {"red": 1}),
            Boon("Sunshield Strike", "red", {"red": 1}, on_color_special_bonus_damage={"red": 2}),
            Boon("Winged Aegis", "red", {"red": 1}),
            Boon("Anointed Armor", "red", {}),
            Boon("Gaze of the Hawk", "red", {"red": 1}),
        ],
        "blue": [
            Boon("Allfather's Vision", "blue", {"blue": 2}),
            Boon("Rune Writing", "blue", {"blue": 1}),
            Boon("Yggdrasil's Sight", "blue", {"blue": 1}),
            Boon("Runic Sacrifice", "blue", {"blue": 1}),
            Boon("Nile's Flow", "blue", {"blue": 1}, on_color_special_bonus_lp={"blue": 2}),
            Boon("Lifebringer", "blue", {}, on_color_special_bonus_lp={"blue": 3}),
            Boon("Wings of Life", "blue", {"blue": 1}),
            Boon("Queen's Bloom", "blue", {"blue": 1}),
            Boon("Queen's Command", "blue", {}, on_color_special_bonus_damage={"blue": 4}),
            Boon("Wave of Roots", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 2}),
            Boon("Faeric Pride", "blue", {"blue": 1}),
            Boon("Court's Reverie", "blue", {"blue": 1}, on_kill_lp=3),
            Boon("Dooming Hex", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 2}),
            Boon("Witch’s Wound", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 1}),
            Boon("Red-Moon Curse", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 1}),
            Boon("Withering Magic", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 1}),
        ],
        "green": [
            Boon("Many Masks", "green", {"green": 1}),
            Boon("Hundred Illusions", "green", {"green": 1}, on_color_special_bonus_lp={"green": 1}),
            Boon("Chaos Wager", "green", {"green": 1}),
            Boon("Master of All Tricks", "green", {"green": 1}, on_attack_flat_bonus=2),
            Boon("Blessing of Alacrity", "green", {"green": 2}),
            Boon("Luck of the Messenger", "green", {"green": 1}),
            Boon("Winged Sandals", "green", {"green": 1}),
            Boon("Wind Step", "green", {"green": 1}),
            Boon("Desert Plague", "green", {}, on_color_special_bonus_damage={"green": 4}),
            Boon("Dune Snare", "green", {"green": 1}, on_color_special_bonus_damage={"green": 2}),
            Boon("Cruelty", "green", {"green": 1}, on_color_special_bonus_damage={"green": 3}),
            Boon("Cruel Decay", "green", {"green": 1}, on_attack_flat_bonus=1),
            Boon("Whisper of the Coffin", "green", {"green": 1}, on_attack_flat_bonus=1),
            Boon("Funeral Ceremony", "green", {}, on_kill_lp=3),
            Boon("Coffin Nail", "green", {}, on_color_special_bonus_damage={"green": 8}),
            Boon("Graveyard Smile", "green", {"green": 1}, on_attack_flat_bonus=1),
        ],
        "grey": [
            Boon("Banner of Glory", "grey", {}, on_kill_lp=2),
            Boon("Athena’s Rally", "grey", {"grey": 1}, on_color_special_bonus_lp={"grey": 1}),
            Boon("Aegis Blessing", "grey", {"grey": 1}, on_color_special_bonus_lp={"grey": 1}),
            Boon("Laurel of Nike", "grey", {}, on_color_special_bonus_lp={"grey": 1}),
            Boon("Scriber's Insight", "grey", {"grey": 2}),
            Boon("Glyph's Wisdom", "grey", {"grey": 2}),
            Boon("Ancient Secrets", "grey", {}, on_color_special_bonus_lp={"grey": 4}),
            Boon("Moon's Manipulation", "grey", {"grey": 1}, on_color_special_bonus_damage={"grey": 1}),
            Boon("Wave of Mercy", "grey", {"grey": 1}, on_color_special_bonus_lp={"grey": 2}),
            Boon("Heavenly Will", "grey", {}, on_color_special_bonus_lp={"blue": 2}),
            Boon("Overflowing Compassion", "grey", {}, on_attack_flat_bonus=1),
            Boon("Lotus Dance", "grey", {"grey": 1}),
            Boon("Crow’s Judgment", "grey", {"grey": 1}, on_color_special_bonus_damage={"grey": 2}, on_color_special_bonus_lp={"grey": 3}),
            Boon("Death's Companion", "grey", {"grey": 1}),
            Boon("Thousand Pecks", "grey", {"grey": 1}, on_attack_flat_bonus=1),
            Boon("Raven’s Harvest", "grey", {"grey": 1}),
        ],
        "yellow": [
            Boon("Zeus’ Judgment", "yellow", {}, on_color_special_bonus_damage={"yellow": 7}),
            Boon("Olympus' Gift", "yellow", {"yellow": 1}, on_attack_flat_bonus=1),
            Boon("Heaven's Reach", "yellow", {"yellow": 1}, on_attack_flat_bonus=1),
            Boon("Storm of Wrath", "yellow", {}, on_color_special_bonus_damage={"yellow": 4}),
            Boon("Whispers of Love", "yellow", {"yellow": 1}),
            Boon("Protection of the Heart", "yellow", {}, on_color_special_bonus_lp={"yellow": 2}),
            Boon("Roses to Thorns", "yellow", {"yellow": 1}, on_color_special_bonus_damage={"yellow": 2}),
            Boon("Chorus of Passion", "yellow", {}, on_color_special_bonus_lp={"yellow": 2}),
            Boon("Fortress Strike", "yellow", {"yellow": 1}, on_color_special_bonus_damage={"yellow": 2}),
            Boon("Blessed Iron", "yellow", {}, on_attack_flat_bonus=1),
            Boon("Thousandfold Retribution", "yellow", {}, on_attack_flat_bonus=1),
            Boon("Guardian-God’s Defense", "yellow", {"yellow": 1}),
            Boon("Fey Majesty", "yellow", {"yellow": 2}),
            Boon("Courtly Glamour", "yellow", {"yellow": 2}),
            Boon("Royal Flourish", "yellow", {"yellow": 1}, on_color_special_bonus_damage={"yellow": 2}),
            Boon("Fae Bargain", "yellow", {"yellow": 1}, on_color_special_bonus_lp={"yellow": 8}),
        ],
    }


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def roll_die() -> str:
    r = random.random()
    if r < 1 / 3:
        return "dmg"
    if r < 2 / 3:
        return "special"
    return "blank"


def choose_gate(taint: int) -> Gate:
    options = random.sample(STANDARD_GATES, 2) + [random.choice(NEXUS_GATES)]
    best = None
    best_score = -1e9
    for g in options:
        score = len(g.fragments) * 1.4 - g.threat * 1.1
        if g.gate_type == "nexus":
            score -= 0.8 if taint < 10 else -0.2
        if taint >= 12 and g.gate_type in ("temple", "nexus"):
            score += 1.2
        if score > best_score:
            best_score = score
            best = g
    return best


def spawn_for_threat(threat: int, spawn_level: int) -> List[Enemy]:
    if threat == 3:
        names = ["Void Treant", "Void Soldier", "Shadow Spinner", "Dark Wizard"]
    elif threat >= 4:
        names = ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner", "Dark Wizard"]
    elif threat == 2:
        names = ["Void Soldier", "Shadow Spinner", "Shadow Spinner"]
    else:
        names = ["Void Soldier", "Shadow Spinner"]

    enemies = []
    for n in names:
        vt = VILLAINS[n]
        a_mod, hp_mod, d_mod = LEVEL_MODS[spawn_level]
        enemies.append(
            Enemy(vt, hp=vt.hp + hp_mod, armor=vt.armor + a_mod, damage=vt.damage + d_mod, level=spawn_level)
        )
    return enemies


def apply_condition(target: HeroState | Enemy, cond: str):
    target.conditions[cond] += 1


def remove_surge_conditions(heroes: List[HeroState], enemies: List[Enemy]):
    positive = {"empowered", "exalted", "toughened", "armored"}
    negative = {"weakened", "enfeebled", "exposed", "breached", "bleeding", "hemorrhaging", "staggered", "slowed"}
    for h in heroes:
        for c in list(h.conditions):
            if c in positive:
                del h.conditions[c]
    for e in enemies:
        for c in list(e.conditions):
            if c in negative:
                del e.conditions[c]


def pick_attack(hero: HeroState, enemies: List[Enemy]) -> Attack:
    alive_enemies = [e for e in enemies if e.alive]
    tanky = any(e.hp >= 10 for e in alive_enemies)
    if hero.lp >= 6:
        return hero.template.attacks[3]
    if hero.lp >= hero.template.attacks[2].lp_cost and tanky:
        return hero.template.attacks[2]
    # choose best builder by expected damage rough score
    b1, b2 = hero.template.attacks[0], hero.template.attacks[1]
    s1 = sum(b1.base_dice.values()) + b1.lp_gain * 0.7
    s2 = sum(b2.base_dice.values()) + b2.lp_gain * 0.7
    return b1 if s1 >= s2 else b2


def target_enemy(enemies: List[Enemy], damage_type: Optional[str] = None) -> Optional[Enemy]:
    alive = [e for e in enemies if e.alive]
    if not alive:
        return None
    # focus low hp to reduce incoming attacks
    alive.sort(key=lambda e: (e.hp, -e.damage))
    return alive[0]


def resolve_hero_attack(
    hero: HeroState,
    enemies: List[Enemy],
    seals: List[str],
    boon_cp: Dict[str, float],
    gate: Gate,
) -> None:
    if not hero.alive:
        return
    if hero.conditions.get("staggered", 0) > 0:
        del hero.conditions["staggered"]
        return

    atk = pick_attack(hero, enemies)
    if hero.lp < atk.lp_cost:
        atk = hero.template.attacks[0]

    lp_spent = atk.lp_cost
    if atk.full_spender:
        lp_spent = max(3, hero.lp)
    hero.lp = clamp(hero.lp - lp_spent, 0, 12)

    pool: List[Tuple[str, Optional[str]]] = []
    for color, n in atk.base_dice.items():
        n_roll = n
        if atk.full_spender and color == "red" and hero.template.name == "Hercules":
            n_roll += max(0, lp_spent - 3)
        if atk.full_spender and color == "green" and hero.template.name == "Anansi":
            n_roll = lp_spent
        for _ in range(n_roll):
            pool.append((color, None))

    pool.append((hero.template.relic_die_color, None))

    for b in hero.boons:
        for c, n in b.dice_bonus.items():
            for _ in range(n):
                pool.append((c, b.name))

    results: List[Tuple[str, str, Optional[str]]] = []
    for color, src in pool:
        face = roll_die()
        # simple reroll policy: spend LP on blank up to 2 rerolls
        if face == "blank" and hero.lp > 0 and random.random() < 0.35:
            hero.lp -= 1
            face = roll_die()
        results.append((color, face, src))

    # count results
    dmg = 0
    specials_by_color = Counter()
    blanks = 0
    for color, face, src in results:
        if face == "dmg":
            dmg += 1
            if src:
                boon_cp[src] += CP_DAMAGE
        elif face == "special":
            specials_by_color[color] += 1
        else:
            blanks += 1

    # once/turn bank one seal before spending specials
    if len(seals) < 6 and sum(specials_by_color.values()) > 0 and random.random() < 0.45:
        c = max(specials_by_color, key=specials_by_color.get)
        specials_by_color[c] -= 1
        if specials_by_color[c] <= 0:
            del specials_by_color[c]
        seals.append(c)

    # base attack special rules (spend one matching special for +2 dmg per trigger)
    for c, req in atk.special_rules.items():
        if specials_by_color.get(c, 0) >= req:
            specials_by_color[c] -= req
            dmg += 2

    # boon triggered effects
    for b in hero.boons:
        for c, bdmg in b.on_color_special_bonus_damage.items():
            if specials_by_color.get(c, 0) >= 1:
                specials_by_color[c] -= 1
                dmg += bdmg
                boon_cp[b.name] += bdmg * CP_DAMAGE
        for c, blp in b.on_color_special_bonus_lp.items():
            if specials_by_color.get(c, 0) >= 1:
                specials_by_color[c] -= 1
                hero.lp = clamp(hero.lp + blp, 0, 12)
                boon_cp[b.name] += blp * CP_LP
        if b.on_attack_flat_bonus:
            dmg += b.on_attack_flat_bonus
            boon_cp[b.name] += b.on_attack_flat_bonus * CP_DAMAGE

    # remaining specials -> LP or damage heuristic
    for c, n in list(specials_by_color.items()):
        for _ in range(n):
            if hero.lp <= 4:
                hero.lp = clamp(hero.lp + 2, 0, 12)
            else:
                dmg += 2

    dmg += atk.lp_gain * 0  # lp gain handled below
    hero.lp = clamp(hero.lp + atk.lp_gain, 0, 12)

    # condition modifiers
    if hero.conditions.get("empowered", 0):
        dmg += 1
    if hero.conditions.get("exalted", 0):
        dmg += 3
    if hero.conditions.get("weakened", 0):
        dmg -= 1
    if hero.conditions.get("enfeebled", 0):
        dmg -= 3
    dmg = max(0, dmg)

    target = target_enemy(enemies)
    if not target:
        return

    # approximate type by most common die in attack
    damage_type = max(atk.base_dice.items(), key=lambda kv: kv[1])[0] if atk.base_dice else "red"

    # vulnerability / resistance
    if target.template.vulnerability == damage_type:
        dmg *= 2
    if target.template.resistance == damage_type:
        dmg //= 2

    # armor application
    post = max(0, dmg - target.armor)
    target.hp -= post
    hero.damage_done_this_room += post

    if target.hp <= 0:
        for b in hero.boons:
            if b.on_kill_lp:
                hero.lp = clamp(hero.lp + b.on_kill_lp, 0, 12)
                boon_cp[b.name] += b.on_kill_lp * CP_LP


def choose_target_for_enemy(enemy: Enemy, heroes: List[HeroState]) -> Optional[HeroState]:
    alive = [h for h in heroes if h.alive]
    if not alive:
        return None
    if enemy.template.target_rule == "low_hp":
        return min(alive, key=lambda h: h.hp)
    if enemy.template.target_rule == "high_lp":
        return max(alive, key=lambda h: h.lp)
    if enemy.template.target_rule == "high_hp":
        return max(alive, key=lambda h: h.hp)
    return min(alive, key=lambda h: h.hp)


def resolve_enemy_attack(enemy: Enemy, heroes: List[HeroState], taint: List[int]):
    if not enemy.alive:
        return
    target = choose_target_for_enemy(enemy, heroes)
    if not target:
        return
    dmg = enemy.damage
    if enemy.conditions.get("weakened", 0):
        dmg = max(0, dmg - 1)
    if enemy.conditions.get("enfeebled", 0):
        dmg = max(0, dmg - 3)

    incoming = dmg
    if target.conditions.get("exposed", 0):
        incoming += 1
    if target.conditions.get("breached", 0):
        incoming += 3

    ignore_armor = "ignore_armor" in enemy.template.effects
    if not ignore_armor:
        prevented = min(target.armor, incoming)
        incoming -= prevented
        if prevented > 0:
            target.armor = max(0, target.armor - 1)

    target.hp -= incoming

    if "drain_lp" in enemy.template.effects:
        target.lp = max(0, target.lp - 1)
    if "staggered" in enemy.template.effects:
        apply_condition(target, "staggered")
    if "self_toughened" in enemy.template.effects:
        enemy.armor += 1
    if "splash" in enemy.template.effects:
        others = [h for h in heroes if h.alive and h is not target]
        if others:
            splash = random.choice(others)
            splash.hp -= 1

    if target.hp <= 0 and target.alive:
        target.alive = False
        taint[0] += 1


def attempt_fragment_claim(
    hero: HeroState,
    fragments_left: List[str],
    seals: List[str],
    taint: List[int],
    decks: Dict[str, List[Boon]],
):
    if not hero.alive or not fragments_left:
        return
    chance = 0.28 + (0.08 if hero.lp >= 4 else 0)
    if random.random() > chance:
        return
    color = fragments_left.pop(0)

    if color in seals:
        seals.remove(color)
    else:
        taint[0] += 1

    candidates = random.sample(decks[color], k=3)
    # choose by simple score = dice + effect potential
    def score(b: Boon):
        return sum(b.dice_bonus.values()) * 3 + b.on_attack_flat_bonus + sum(b.on_color_special_bonus_damage.values()) * 0.4 + sum(b.on_color_special_bonus_lp.values()) * 0.35 + b.on_kill_lp * 0.3

    pick = max(candidates, key=score)
    hero.boons.append(pick)


def run_single() -> Dict:
    heroes = [HeroState(template=h, hp=h.max_hp) for h in HEROES]
    decks = boon_catalog()
    seals: List[str] = []
    taint = [0]
    spawn_level = 1

    room_hp = []
    room_damage = []
    room_taint = []
    boon_cp = defaultdict(float)

    for room_idx in range(1, MAX_ROOMS + 1):
        # room reset
        for h in heroes:
            if h.alive:
                h.lp = 0
                h.armor = 0
            h.damage_done_this_room = 0.0

        gate = choose_gate(taint[0])

        # unseal heuristic
        if any(f in seals for f in gate.fragments):
            for f in gate.fragments:
                if f in seals:
                    seals.remove(f)
                    taint[0] = max(0, taint[0] - 1)
                    break

        # start bonuses
        for h in heroes:
            if not h.alive:
                continue
            h.lp = clamp(h.lp + gate.start_lp, 0, 12)
            if gate.start_heal > 0:
                h.hp = min(h.template.max_hp, h.hp + gate.start_heal)

        enemies = spawn_for_threat(gate.threat, spawn_level)
        fragments = gate.fragments.copy()

        round_num = 0
        collapse_pending = False
        while any(e.alive for e in enemies) and any(h.alive for h in heroes) and round_num < 8:
            round_num += 1
            initiative = [h.template.name for h in heroes if h.alive] + [f"E{i}" for i, e in enumerate(enemies) if e.alive]
            random.shuffle(initiative)
            if "Assassin" in gate.name:
                initiative.sort(key=lambda x: 0 if x.startswith("E") else 1)

            for token in initiative:
                if token.startswith("E"):
                    idx = int(token[1:])
                    if 0 <= idx < len(enemies) and enemies[idx].alive:
                        resolve_enemy_attack(enemies[idx], heroes, taint)
                else:
                    hero = next(h for h in heroes if h.template.name == token)
                    if hero.alive:
                        hero.armor = 0  # armor decay at start turn
                        resolve_hero_attack(hero, enemies, seals, boon_cp, gate)
                        attempt_fragment_claim(hero, fragments, seals, taint, decks)
                        if hero.conditions.get("bleeding", 0):
                            hero.hp -= 1
                        if hero.conditions.get("hemorrhaging", 0):
                            hero.hp -= 3
                        if hero.hp <= 0 and hero.alive:
                            hero.alive = False
                            taint[0] += 1

            # round end taint + despair
            taint[0] += 1
            despair = 0 if taint[0] <= 5 else 1 if taint[0] <= 10 else 2 if taint[0] <= 15 else 3
            for h in heroes:
                if h.alive and len(h.boons) < despair:
                    taint[0] += 1

            if taint[0] in (5, 10, 15):
                remove_surge_conditions(heroes, enemies)
                spawn_level = min(6, spawn_level + 1)

            if taint[0] >= 20 and not collapse_pending:
                collapse_pending = True
            elif taint[0] >= 20 and collapse_pending:
                for h in heroes:
                    h.alive = False
                    h.hp = 0
                break

        # room clear resurrect rule
        if any(e.alive for e in enemies):
            # room failure: keep dead as dead for this run
            pass
        else:
            for h in heroes:
                if not h.alive:
                    h.alive = True
                    h.hp = h.template.max_hp // 2
                    h.lp = 0
                    h.conditions.clear()

        room_hp.append({h.template.name: max(0, h.hp) for h in heroes})
        room_damage.append({h.template.name: h.damage_done_this_room for h in heroes})
        room_taint.append(taint[0])

        if not any(h.alive for h in heroes):
            # fill remaining rooms with zeros
            for _ in range(room_idx + 1, MAX_ROOMS + 1):
                room_hp.append({h.template.name: 0 for h in heroes})
                room_damage.append({h.template.name: 0.0 for h in heroes})
                room_taint.append(taint[0])
            break

    return {
        "room_hp": room_hp,
        "room_damage": room_damage,
        "room_taint": room_taint,
        "boon_cp": dict(boon_cp),
        "survived_7": int(any(h.alive for h in heroes) and len(room_hp) >= 7),
    }


def aggregate(sim_results: List[Dict]) -> Dict:
    hero_names = [h.name for h in HEROES]
    avg_hp = []
    avg_dmg = []
    avg_taint = []

    for r in range(MAX_ROOMS):
        hp_row = {}
        dmg_row = {}
        for hn in hero_names:
            hp_row[hn] = statistics.fmean(res["room_hp"][r][hn] for res in sim_results)
            dmg_row[hn] = statistics.fmean(res["room_damage"][r][hn] for res in sim_results)
        avg_hp.append(hp_row)
        avg_dmg.append(dmg_row)
        avg_taint.append(statistics.fmean(res["room_taint"][r] for res in sim_results))

    total_boon_cp = defaultdict(float)
    for res in sim_results:
        for k, v in res["boon_cp"].items():
            total_boon_cp[k] += v

    boon_avg = {k: v / len(sim_results) for k, v in sorted(total_boon_cp.items(), key=lambda kv: kv[1], reverse=True)}

    survival_rate = statistics.fmean(res["survived_7"] for res in sim_results)
    return {"avg_hp": avg_hp, "avg_dmg": avg_dmg, "avg_taint": avg_taint, "boon_cp_avg": boon_avg, "survival_rate": survival_rate}


def print_report(agg: Dict, sims: int):
    print(f"Spellrift balance simulation report ({sims} runs)")
    print("=" * 72)
    for i in range(MAX_ROOMS):
        print(f"\nRoom {i+1}")
        print(f"  Avg Taint: {agg['avg_taint'][i]:.2f}")
        print("  Avg Hero HP at room end:")
        for hn, val in agg["avg_hp"][i].items():
            print(f"    - {hn:12s}: {val:6.2f}")
        print("  Avg damage dealt by hero in this room:")
        for hn, val in agg["avg_dmg"][i].items():
            print(f"    - {hn:12s}: {val:6.2f}")

    print(f"\nEstimated run survival to room 7: {agg['survival_rate']*100:.2f}%")
    print("\nTop 40 Boon cards by average CP contribution per run")
    print("-" * 72)
    for i, (name, cp) in enumerate(list(agg["boon_cp_avg"].items())[:40], start=1):
        print(f"{i:2d}. {name:32s} {cp:8.3f} CP/run")


def run_simulations(n: int = DEFAULT_SIMS, seed: int = 42):
    random.seed(seed)
    results = []
    for _ in range(n):
        results.append(run_single())
    return aggregate(results)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Spellrift Dungeons alpha balance simulator")
    parser.add_argument("--sims", type=int, default=DEFAULT_SIMS, help="number of Monte Carlo simulations (default: 20000)")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    aggregated = run_simulations(args.sims, args.seed)
    print_report(aggregated, args.sims)
