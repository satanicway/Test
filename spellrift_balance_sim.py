#!/usr/bin/env python3
"""
Spellrift Dungeons v0.4.2 balance simulator (movement/grid abstracted).

What is modeled:
- 4 fixed heroes, up to 7 rooms, 20k Monte Carlo default.
- Gate choice loop (2 standard + 1 nexus), finite gate/room/boon decks.
- Initiative, round/turn loop, taint/despair/surge/collapse.
- Dice/specials/LP/rerolls, seal bank + channeling, fragment claim cost.
- Fragment tasks (abstract event-based) and boon drafting (3 + optional LP buys to 6).
- Conditions with tier escalation, opposing-pair cancellation, and duration classes.
- Hero attacks/utilities/unique powers (abstract but explicit for all 4 heroes).
- Villain targeting/effects, spawn-level scaling, elite +1 level support.
- Room-end metrics: avg HP, avg damage, avg taint, boon CP contribution.

Intentionally abstracted:
- Grid, exact movement paths/LOS/terrain geometry (assume average engagement).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict, Counter, deque
import argparse
import math
import random
import statistics
from typing import Dict, List, Optional, Tuple

# ---------- constants ----------
MAX_ROOMS = 7
DEFAULT_SIMS = 20_000
MAX_LP = 12
MAX_SEALS = 6

COLORS = ["red", "green", "grey", "blue", "yellow"]
DAMAGE_TYPE = {
    "red": "brutal",
    "green": "precision",
    "grey": "spiritual",
    "blue": "arcane",
    "yellow": "divine",
}

# CP budgets (GDD section 21)
CP_DAMAGE = 1.0
CP_HP = 1.0
CP_LP = 1.0
CP_ARMOR = 1.5
CP_DIE = 3.0

POSITIVE_CONDITIONS = {"empowered", "exalted", "toughened", "armored"}
NEGATIVE_CONDITIONS = {
    "slowed",
    "staggered",
    "bleeding",
    "hemorrhaging",
    "weakened",
    "enfeebled",
    "exposed",
    "breached",
}

# front/back condition pairs
COND_STRONGER = {
    "slowed": "staggered",
    "bleeding": "hemorrhaging",
    "weakened": "enfeebled",
    "empowered": "exalted",
    "toughened": "armored",
    "exposed": "breached",
}
COND_WEAKER = {v: k for k, v in COND_STRONGER.items()}

OPPOSING = {
    "weakened": "empowered",
    "enfeebled": "exalted",
    "toughened": "exposed",
    "armored": "breached",
    "empowered": "weakened",
    "exalted": "enfeebled",
    "exposed": "toughened",
    "breached": "armored",
}

COND_EXPIRY = {
    "slowed": "next_move",
    "staggered": "next_move",
    "bleeding": "heal",
    "hemorrhaging": "heal",
    "weakened": "surge",
    "enfeebled": "surge",
    "empowered": "surge",
    "exalted": "surge",
    "toughened": "surge",
    "armored": "surge",
    "exposed": "surge",
    "breached": "surge",
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


# ---------- data models ----------
@dataclass
class Attack:
    name: str
    base_dice: Dict[str, int]
    lp_cost: int = 0
    lp_gain: int = 0
    full_spender: bool = False
    ranged: bool = False
    targets: int = 1


@dataclass
class HeroTemplate:
    name: str
    max_hp: int
    relic_color: str
    attacks: List[Attack]


@dataclass
class VillainTemplate:
    name: str
    hp: int
    armor: int
    dmg: int
    target_rule: str
    vuln: Optional[str]
    effects: Tuple[str, ...] = ()


@dataclass
class GateCard:
    name: str
    gate_type: str  # basic/elite/temple/nexus
    threat: int
    fragments: List[str]
    start_lp: int = 0
    start_heal: int = 0


@dataclass
class RoomCard:
    name: str
    room_type: str  # basic/temple/nexus
    spawns: Dict[int, List[Tuple[str, bool]]]  # threat -> [(villain_name, elite)]
    rule: str


@dataclass
class Boon:
    name: str
    color: str
    dice_bonus: Dict[str, int] = field(default_factory=dict)
    # generic keyword-like contributions (abstracted)
    special_damage: Dict[str, int] = field(default_factory=dict)
    special_lp: Dict[str, int] = field(default_factory=dict)
    on_kill_lp: int = 0
    flat_damage: int = 0
    flat_armor: int = 0
    gives_condition: Optional[str] = None


@dataclass
class ConditionState:
    # condition -> tier (1 front, 2 back)
    active: Dict[str, int] = field(default_factory=dict)

    def has(self, c: str) -> bool:
        return self.active.get(c, 0) > 0

    def tier(self, c: str) -> int:
        return self.active.get(c, 0)

    def remove(self, c: str):
        self.active.pop(c, None)


@dataclass
class HeroState:
    template: HeroTemplate
    hp: int
    lp: int = 0
    armor: int = 0
    alive: bool = True
    conditions: ConditionState = field(default_factory=ConditionState)
    boons: List[Boon] = field(default_factory=list)
    damage_this_room: float = 0.0

    # unique power/room state
    free_reroll_pool: int = 0
    ignored_next_shatter: bool = False
    bloody_fate_ignore_used: bool = False
    first_attack_done: bool = False

    # Anansi / Joan / Merlin / Hercules abstractions
    on_web: bool = False
    oriflamme_active: bool = False
    rune_slots: List[str] = field(default_factory=list)
    overflow_seals: List[str] = field(default_factory=list)
    holding_enemy: bool = False


@dataclass
class EnemyState:
    template: VillainTemplate
    hp: int
    armor: int
    dmg: int
    level: int
    alive: bool = True
    conditions: ConditionState = field(default_factory=ConditionState)


@dataclass
class RoomContext:
    gate: GateCard
    room: RoomCard
    round_no: int = 0
    first_enemy_attack_done: bool = False
    attacked_enemy_ids: set = field(default_factory=set)
    gate_flags: Dict[str, bool] = field(default_factory=dict)
    room_flags: Dict[str, bool] = field(default_factory=dict)


# ---------- templates ----------
HEROES = [
    HeroTemplate(
        "Hercules",
        25,
        "red",
        [
            Attack("Pillar-Breaker Blow", {"red": 3}, lp_gain=1),
            Attack("Club Spin", {"green": 2}, lp_gain=2, targets=2),
            Attack("Colossus Smash", {"red": 4}, lp_cost=2),
            Attack("True Might", {"yellow": 4, "red": 0}, lp_cost=3, full_spender=True),
        ],
    ),
    HeroTemplate(
        "Merlin",
        18,
        "blue",
        [
            Attack("Arcane Volley", {"blue": 2}, lp_gain=1, ranged=True, targets=2),
            Attack("Spiritual Gifts", {"grey": 2}, lp_gain=2, ranged=True),
            Attack("Whispers of the Wyrd", {"grey": 2}, lp_cost=2, ranged=True),
            Attack("Avalon's Light", {"blue": 4}, lp_cost=3, full_spender=True),
        ],
    ),
    HeroTemplate(
        "Joan d’Arc",
        20,
        "yellow",
        [
            Attack("Blade of Lys", {"yellow": 1, "red": 2}, lp_gain=1),
            Attack("Holy Bolt", {"yellow": 2}, lp_gain=2, ranged=True),
            Attack("Vanguard Strike", {"red": 3}, lp_cost=3, ranged=True),
            Attack("Divine Punishment", {"yellow": 4}, lp_cost=3, full_spender=True, targets=2),
        ],
    ),
    HeroTemplate(
        "Anansi",
        20,
        "green",
        [
            Attack("Guile Strike", {"green": 2}, lp_gain=1),
            Attack("Story-weaver", {"yellow": 2}, lp_gain=2),
            Attack("Snare and Sever", {"green": 3, "blue": 2}, lp_cost=2, ranged=True),
            Attack("The Last Thread", {"green": 0}, lp_cost=3, full_spender=True),
        ],
    ),
]

VILLAINS = {
    "Voidling": VillainTemplate("Voidling", 2, 0, 2, "closest", None, ("drain_lp",)),
    "Shadow Spinner": VillainTemplate("Shadow Spinner", 4, 0, 3, "less_hp", "red", ("web",)),
    "Void Soldier": VillainTemplate("Void Soldier", 5, 0, 3, "closest", "blue", ("armor_up",)),
    "Dark Wizard": VillainTemplate("Dark Wizard", 10, 1, 3, "most_distant", "yellow", ("ignore_armor", "push")),
    "Shadow Banshee": VillainTemplate("Shadow Banshee", 10, 0, 4, "more_lp", "grey", ("terror",)),
    "Void Treant": VillainTemplate("Void Treant", 12, 2, 3, "closest", "green", ("splash",)),
}

LEVEL_MOD = {
    1: (0, 0, 0),
    2: (0, 2, 1),
    3: (1, 5, 3),
    4: (1, 7, 5),
    5: (2, 10, 7),
    6: (2, 15, 10),
}


def standard_gates() -> List[GateCard]:
    return [
        GateCard("Spiked Gate", "basic", 2, ["red", "red"], 1, 0),
        GateCard("Cursed Gate", "basic", 2, ["blue", "blue"], 1, 0),
        GateCard("Reinforced Gate", "basic", 2, ["red", "yellow"], 1, 0),
        GateCard("Predator's Gate", "basic", 2, ["red", "green"], 1, 0),
        GateCard("Assassin's Gate", "basic", 2, ["green", "yellow"], 0, 2),
        GateCard("Painful Gate", "basic", 2, ["grey", "yellow"], 1, 1),
        GateCard("Sturdy Gate", "basic", 3, ["red", "blue", "green"], 2, 1),
        GateCard("Glutton's Gate", "basic", 3, ["blue", "green", "grey"], 1, 2),
        GateCard("Glorious Gate", "basic", 3, ["red", "grey", "yellow"], 3, 0),
        GateCard("Shattering Gate", "basic", 3, ["red", "green", "yellow"], 2, 0),
        GateCard("Vengeance's Gate", "elite", 5, ["red", "green"], 2, 0),
        GateCard("Banner's Gate", "elite", 5, ["red", "grey"], 0, 2),
        GateCard("Fateful Gate", "elite", 5, ["blue", "yellow"], 1, 0),
        GateCard("Dampened Gate", "elite", 5, ["green", "green"], 0, 0),
        GateCard("Large Gate", "elite", 5, ["grey", "grey"], 1, 0),
        GateCard("Temple of Courage", "temple", 1, ["yellow"], 1, 0),
        GateCard("Temple of Mercy", "temple", 1, ["grey"], 0, 1),
        GateCard("Temple of Clarity", "temple", 1, ["blue"], 1, 0),
        GateCard("Temple of Fire", "temple", 1, ["green"], 1, 0),
        GateCard("Temple of Purity", "temple", 1, ["yellow"], 1, 0),
    ]


def nexus_gates() -> List[GateCard]:
    return [
        GateCard("Nexus Denied Strength", "nexus", 3, ["blue", "grey"], 1, 1),
        GateCard("Nexus Denied Magic", "nexus", 3, ["green", "yellow"], 2, 0),
        GateCard("Nexus Denied Speed", "nexus", 3, ["red", "blue"], 1, 0),
        GateCard("Nexus Denied Spirit", "nexus", 3, ["yellow", "yellow"], 0, 2),
        GateCard("Nexus Denied Faith", "nexus", 3, ["blue", "grey", "yellow"], 2, 1),
        GateCard("Nexus Denied Destiny", "nexus", 4, ["red", "red", "blue"], 3, 0),
    ]


def basic_rooms() -> List[RoomCard]:
    # 2..20 from GDD with threat 2/3/5 lists
    def r(name, t2, t3, t5, rule):
        return RoomCard(name, "basic", {2: [(x, False) for x in t2], 3: [(x, False) for x in t3], 5: t5}, rule)

    elite = lambda pairs: [(n, True if e else False) for n, e in pairs]

    return [
        r("Steelbound Footing", ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], ["Dark Wizard", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], elite([("Void Treant", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "guarded_advance"),
        r("Fate's Favor", ["Void Soldier", "Void Soldier", "Void Soldier"], ["Void Soldier", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Soldier", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "heroic_destiny"),
        r("Flanking Hymn", ["Void Soldier", "Void Soldier", "Shadow Spinner"], ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Dark Wizard", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "flank_flow"),
        r("Runes of Clarity", ["Dark Wizard", "Void Soldier"], ["Shadow Banshee", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Shadow Banshee", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "special_surge"),
        r("Prayer of the Bold", ["Void Soldier", "Void Soldier", "Shadow Spinner"], ["Void Soldier", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Treant", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "stand_firm"),
        r("Mercy Sigil", ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], ["Shadow Spinner", "Shadow Spinner", "Shadow Spinner", "Shadow Spinner"], elite([("Dark Wizard", True), ("Shadow Spinner", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "clean_hands"),
        r("Echo of Teamwork", ["Dark Wizard", "Shadow Spinner"], ["Void Treant", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], elite([("Void Treant", True), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "follow_up"),
        r("Watcher Blind Spot", ["Void Soldier", "Void Soldier", "Shadow Spinner"], ["Shadow Banshee", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Shadow Banshee", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "safe_step"),
        r("Shatter Song Hall", ["Void Soldier", "Void Soldier", "Void Soldier"], ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Soldier", True), ("Void Treant", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "strong_push"),
        r("Riftwind Range", ["Dark Wizard", "Void Soldier"], ["Dark Wizard", "Dark Wizard", "Void Soldier", "Shadow Spinner"], elite([("Dark Wizard", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "clear_shot"),
        r("Oath of Steel", ["Void Soldier", "Void Soldier", "Shadow Spinner"], ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Treant", True), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False)]), "armor_earned"),
        r("Glyphs of Fortune", ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], ["Void Treant", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], elite([("Void Treant", True), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "blank_to_spark"),
        r("Boon Lure", ["Shadow Spinner", "Shadow Spinner", "Void Soldier"], ["Dark Wizard", "Shadow Spinner", "Shadow Spinner", "Void Soldier"], elite([("Void Soldier", True), ("Dark Wizard", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "task_reward"),
        r("Harmonized Legend", ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], ["Void Treant", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], elite([("Void Treant", True), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "together_rise"),
        r("Archer Prayer", ["Dark Wizard", "Shadow Spinner"], ["Dark Wizard", "Void Treant", "Shadow Spinner", "Void Soldier"], elite([("Dark Wizard", True), ("Void Treant", False), ("Shadow Spinner", False)]), "mark_prey"),
        r("Weaver Gift", ["Dark Wizard", "Void Soldier"], ["Dark Wizard", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Soldier", True), ("Dark Wizard", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "pull_thread"),
        r("Lantern of Hope", ["Void Soldier", "Void Soldier", "Shadow Spinner"], ["Dark Wizard", "Void Soldier", "Void Soldier", "Shadow Spinner"], elite([("Void Soldier", True), ("Shadow Banshee", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]), "answer_wound"),
        r("Banner of Resolve", ["Void Soldier", "Void Soldier", "Void Soldier"], ["Void Soldier", "Void Soldier", "Void Soldier", "Void Soldier"], elite([("Void Soldier", True), ("Void Soldier", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "hold_line"),
        r("Heartbeat of War", ["Void Soldier", "Void Soldier", "Void Soldier"], ["Shadow Banshee", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], elite([("Shadow Banshee", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]), "spend_to_mend"),
    ]


def temple_rooms() -> List[RoomCard]:
    return [
        RoomCard("Font of Mercy", "temple", {1: [("Shadow Spinner", False), ("Shadow Spinner", False)]}, "temple_mercy"),
        RoomCard("Oracle Steps", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_oracle"),
        RoomCard("Anvil of Vows", "temple", {1: [("Void Soldier", False), ("Void Soldier", False)]}, "temple_anvil"),
        RoomCard("Hall of Courage", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_courage"),
        RoomCard("Salt of Purity", "temple", {1: [("Shadow Spinner", False), ("Shadow Spinner", False)]}, "temple_purity"),
        RoomCard("Mirror Reliquary", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_mirror"),
        RoomCard("Pilgrim Table", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_table"),
        RoomCard("Reforging Shrine", "temple", {1: [("Void Soldier", False), ("Void Soldier", False)]}, "temple_reforge"),
        RoomCard("Whispering Chapel", "temple", {1: [("Shadow Spinner", False), ("Shadow Spinner", False)]}, "temple_chapel"),
    ]


def nexus_rooms() -> List[RoomCard]:
    return [
        RoomCard("Stasis Lens", "nexus", {3: [("Void Treant", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "stasis_ray"),
        RoomCard("Disintegration Scar", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], 4: [("Shadow Banshee", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "disintegrating_glare"),
        RoomCard("Telekinetic Vault", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "telekinesis"),
        RoomCard("Future Devoured", "nexus", {3: [("Void Soldier", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_eats_legend"),
        RoomCard("Doubt Beam", "nexus", {3: [("Dark Wizard", False), ("Shadow Spinner", False), ("Shadow Spinner", False), ("Void Soldier", False)], 4: [("Shadow Banshee", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "fraying_certainty"),
        RoomCard("Unmaking Seal", "nexus", {3: [("Void Treant", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "unmaking_ray"),
        RoomCard("Mercy Noticed", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Shadow Banshee", False), ("Void Soldier", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_watches_heal"),
        RoomCard("Many Tomorrows", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], 4: [("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)]}, "bargain_fate"),
        RoomCard("Open Pupil", "nexus", {3: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Shadow Banshee", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_beam_alignment"),
    ]


def boon_catalog() -> Dict[str, List[Boon]]:
    # concise but all named cards from previous implementation + stronger keyword hooks
    # placeholders intentionally omitted from draft pool.
    return {
        "red": [
            Boon("Mjolnir’s Spark", "red", {"red": 1}, special_damage={"red": 5}),
            Boon("Hammering Thunder", "red", {"red": 1}, flat_damage=1),
            Boon("Mighty Storm", "red", {"red": 1}, flat_damage=1),
            Boon("Stormbreaker", "red", {}, special_damage={"red": 3}),
            Boon("War God’s Might", "red", {"red": 2}),
            Boon("War God’s Power", "red", {"red": 2}),
            Boon("Forge of War", "red", {"red": 1}),
            Boon("Onslaught", "red", {}, special_damage={"red": 5}),
            Boon("Tidal Slam", "red", {}, special_damage={"red": 3}),
            Boon("Maelstrom Crash", "red", {"red": 1}, special_damage={"red": 2}),
            Boon("Far Tide", "red", {"red": 1}),
            Boon("Command the Currents", "red", {"red": 1}),
            Boon("Sunshield Strike", "red", {"red": 1}, special_damage={"red": 2}, flat_armor=1),
            Boon("Winged Aegis", "red", {"red": 1}, flat_armor=1),
            Boon("Anointed Armor", "red", {}),
            Boon("Gaze of the Hawk", "red", {"red": 1}),
        ],
        "blue": [
            Boon("Allfather's Vision", "blue", {"blue": 2}),
            Boon("Rune Writing", "blue", {"blue": 1}),
            Boon("Yggdrasil's Sight", "blue", {"blue": 1}),
            Boon("Runic Sacrifice", "blue", {"blue": 1}),
            Boon("Nile's Flow", "blue", {"blue": 1}, special_lp={"blue": 2}),
            Boon("Lifebringer", "blue", {}, special_lp={"blue": 3}),
            Boon("Wings of Life", "blue", {"blue": 1}),
            Boon("Queen's Bloom", "blue", {"blue": 1}),
            Boon("Queen's Command", "blue", {}, special_damage={"blue": 4}),
            Boon("Wave of Roots", "blue", {"blue": 1}, special_damage={"blue": 2}),
            Boon("Faeric Pride", "blue", {"blue": 1}),
            Boon("Court's Reverie", "blue", {"blue": 1}, on_kill_lp=3),
            Boon("Dooming Hex", "blue", {"blue": 1}, special_damage={"blue": 2}),
            Boon("Witch’s Wound", "blue", {"blue": 1}, gives_condition="bleeding"),
            Boon("Red-Moon Curse", "blue", {"blue": 1}, gives_condition="exposed"),
            Boon("Withering Magic", "blue", {"blue": 1}, gives_condition="weakened"),
        ],
        "green": [
            Boon("Many Masks", "green", {"green": 1}),
            Boon("Hundred Illusions", "green", {"green": 1}, special_lp={"green": 1}),
            Boon("Chaos Wager", "green", {"green": 1}),
            Boon("Master of All Tricks", "green", {"green": 1}, flat_damage=2),
            Boon("Blessing of Alacrity", "green", {"green": 2}),
            Boon("Luck of the Messenger", "green", {"green": 1}),
            Boon("Winged Sandals", "green", {"green": 1}),
            Boon("Wind Step", "green", {"green": 1}),
            Boon("Desert Plague", "green", {}, special_damage={"green": 4}),
            Boon("Dune Snare", "green", {"green": 1}, special_damage={"green": 2}, gives_condition="slowed"),
            Boon("Cruelty", "green", {"green": 1}, special_damage={"green": 3}),
            Boon("Cruel Decay", "green", {"green": 1}, flat_damage=1),
            Boon("Whisper of the Coffin", "green", {"green": 1}, flat_damage=1),
            Boon("Funeral Ceremony", "green", {}, on_kill_lp=3),
            Boon("Coffin Nail", "green", {}, special_damage={"green": 8}),
            Boon("Graveyard Smile", "green", {"green": 1}, flat_damage=1),
        ],
        "grey": [
            Boon("Banner of Glory", "grey", {}, on_kill_lp=2),
            Boon("Athena’s Rally", "grey", {"grey": 1}, special_lp={"grey": 1}),
            Boon("Aegis Blessing", "grey", {"grey": 1}, special_lp={"grey": 1}),
            Boon("Laurel of Nike", "grey", {}, special_lp={"grey": 1}),
            Boon("Scriber's Insight", "grey", {"grey": 2}),
            Boon("Glyph's Wisdom", "grey", {"grey": 2}),
            Boon("Ancient Secrets", "grey", {}, special_lp={"grey": 4}),
            Boon("Moon's Manipulation", "grey", {"grey": 1}, special_damage={"grey": 1}),
            Boon("Wave of Mercy", "grey", {"grey": 1}, special_lp={"grey": 2}),
            Boon("Heavenly Will", "grey", {}, special_lp={"blue": 2}),
            Boon("Overflowing Compassion", "grey", {}, flat_damage=1),
            Boon("Lotus Dance", "grey", {"grey": 1}),
            Boon("Crow’s Judgment", "grey", {"grey": 1}, special_damage={"grey": 2}, special_lp={"grey": 3}),
            Boon("Death's Companion", "grey", {"grey": 1}),
            Boon("Thousand Pecks", "grey", {"grey": 1}, flat_damage=1),
            Boon("Raven’s Harvest", "grey", {"grey": 1}),
        ],
        "yellow": [
            Boon("Zeus’ Judgment", "yellow", {}, special_damage={"yellow": 7}),
            Boon("Olympus' Gift", "yellow", {"yellow": 1}, flat_damage=1),
            Boon("Heaven's Reach", "yellow", {"yellow": 1}, flat_damage=1),
            Boon("Storm of Wrath", "yellow", {}, special_damage={"yellow": 4}),
            Boon("Whispers of Love", "yellow", {"yellow": 1}),
            Boon("Protection of the Heart", "yellow", {}, special_lp={"yellow": 2}),
            Boon("Roses to Thorns", "yellow", {"yellow": 1}, special_damage={"yellow": 2}),
            Boon("Chorus of Passion", "yellow", {}, special_lp={"yellow": 2}),
            Boon("Fortress Strike", "yellow", {"yellow": 1}, special_damage={"yellow": 2}),
            Boon("Blessed Iron", "yellow", {}, flat_armor=1),
            Boon("Thousandfold Retribution", "yellow", {}, flat_damage=1),
            Boon("Guardian-God’s Defense", "yellow", {"yellow": 1}, flat_armor=1),
            Boon("Fey Majesty", "yellow", {"yellow": 2}),
            Boon("Courtly Glamour", "yellow", {"yellow": 2}),
            Boon("Royal Flourish", "yellow", {"yellow": 1}, special_damage={"yellow": 2}),
            Boon("Fae Bargain", "yellow", {"yellow": 1}, special_lp={"yellow": 8}),
        ],
    }


# ---------- condition handling ----------
def apply_condition(state: ConditionState, cond: str):
    # resolve opposing first
    opp = OPPOSING.get(cond)
    if opp and state.has(opp):
        t = state.tier(opp)
        if t == 2:
            state.active[opp] = 1
        else:
            state.remove(opp)
        return

    if state.has(cond):
        state.active[cond] = min(2, state.tier(cond) + 1)
    else:
        state.active[cond] = 1


def clear_by_expiry(state: ConditionState, expiry: str):
    todel = [c for c in state.active if COND_EXPIRY.get(c) == expiry]
    for c in todel:
        state.remove(c)


def clear_positive(state: ConditionState):
    for c in list(state.active):
        if c in POSITIVE_CONDITIONS:
            state.remove(c)


def clear_negative(state: ConditionState):
    for c in list(state.active):
        if c in NEGATIVE_CONDITIONS:
            state.remove(c)


# ---------- utility functions ----------
def draw_deck_card(deck: deque, fallback_list: List):
    if not deck:
        items = fallback_list[:]
        random.shuffle(items)
        deck.extend(items)
    return deck.popleft()


def hero_by_name(heroes: List[HeroState], name: str) -> HeroState:
    return next(h for h in heroes if h.template.name == name)


def spawn_enemy(name: str, level: int) -> EnemyState:
    t = VILLAINS[name]
    a, hp, d = LEVEL_MOD[level]
    return EnemyState(t, t.hp + hp, t.armor + a, t.dmg + d, level)


def pick_gate(options: List[GateCard], taint: int) -> GateCard:
    # simple strategy: prioritize lower threat at high taint, otherwise more fragments
    best = None
    best_score = -10**9
    for g in options:
        score = len(g.fragments) * 2.0 - g.threat * (1.2 if taint < 10 else 1.8)
        if g.gate_type == "nexus":
            score += 0.3 if taint < 12 else -0.3
        if g.gate_type == "temple" and taint >= 8:
            score += 1.5
        if score > best_score:
            best_score = score
            best = g
    return best


def pick_attack(hero: HeroState, enemies: List[EnemyState]) -> Attack:
    alive = [e for e in enemies if e.alive]
    bossy = any(e.hp >= 10 for e in alive)
    a0, a1, a2, a3 = hero.template.attacks
    if hero.lp >= 6:
        return a3
    if hero.lp >= a2.lp_cost and bossy:
        return a2
    return a0 if sum(a0.base_dice.values()) >= sum(a1.base_dice.values()) else a1


def choose_enemy_target(enemies: List[EnemyState]) -> Optional[EnemyState]:
    alive = [e for e in enemies if e.alive]
    if not alive:
        return None
    alive.sort(key=lambda e: (e.hp, -e.dmg))
    return alive[0]


def enemy_pick_hero(enemy: EnemyState, heroes: List[HeroState]) -> Optional[HeroState]:
    alive = [h for h in heroes if h.alive]
    if not alive:
        return None
    r = enemy.template.target_rule
    if r == "less_hp":
        return min(alive, key=lambda h: h.hp)
    if r == "more_lp":
        return max(alive, key=lambda h: h.lp)
    if r == "most_distant":
        # movement abstracted -> approximate as high HP backliner
        return max(alive, key=lambda h: (h.hp, h.lp))
    return min(alive, key=lambda h: h.hp)


# ---------- core resolution ----------
def build_dice_pool(hero: HeroState, attack: Attack, room_ctx: RoomContext, disabled_boon_color: Optional[str]) -> List[Tuple[str, Optional[str]]]:
    pool = []

    for c, n in attack.base_dice.items():
        count = n
        if attack.full_spender and hero.template.name == "Hercules" and c == "red":
            count = hero.lp  # X red
        if attack.full_spender and hero.template.name == "Merlin" and c == "blue":
            count = 4 + hero.lp
        if attack.full_spender and hero.template.name == "Anansi" and c == "green":
            count = hero.lp
        for _ in range(max(0, count)):
            pool.append((c, None))

    pool.append((hero.template.relic_color, None))

    for b in hero.boons:
        if disabled_boon_color and b.color == disabled_boon_color:
            continue
        for c, n in b.dice_bonus.items():
            for _ in range(n):
                pool.append((c, b.name))

    # gate/room rules
    if room_ctx.gate.name == "Nexus Denied Destiny":
        if len(pool) > 1:
            pool.pop()  # -1 die min1 implicit
    if room_ctx.room.rule == "follow_up" and room_ctx.attacked_enemy_ids and not room_ctx.room_flags.get(f"follow_{hero.template.name}"):
        pool.append((random.choice(COLORS), None))
        room_ctx.room_flags[f"follow_{hero.template.name}"] = True

    return pool


def apply_gate_start(hero: HeroState, gate: GateCard):
    hero.lp = clamp(hero.lp + gate.start_lp, 0, MAX_LP)
    if gate.start_heal:
        prev = hero.hp
        hero.hp = min(hero.template.max_hp, hero.hp + gate.start_heal)
        if gate.name == "Painful Gate" and hero.hp > prev:
            apply_condition(hero.conditions, "slowed")


def unseal_gate_if_possible(gate: GateCard, seal_bank: List[str], taint: int, heroes: List[HeroState]) -> int:
    for c in gate.fragments:
        if c in seal_bank:
            seal_bank.remove(c)
            taint = max(0, taint - 1)
            # unseal burst simplified: LP per frag to random heroes
            for _ in range(len(gate.fragments)):
                h = random.choice([x for x in heroes if x.alive])
                h.lp = clamp(h.lp + 1, 0, MAX_LP)
            return taint
    return taint


def maybe_use_utility(hero: HeroState, heroes: List[HeroState], enemies: List[EnemyState]):
    if not hero.alive:
        return
    if hero.template.name == "Joan d’Arc" and hero.lp >= 2:
        wounded = min([h for h in heroes if h.alive], key=lambda h: h.hp)
        if wounded.hp <= wounded.template.max_hp - 3:
            hero.lp -= 2
            wounded.hp = min(wounded.template.max_hp, wounded.hp + 2)
            clear_by_expiry(wounded.conditions, "heal")
    elif hero.template.name == "Merlin" and hero.lp >= 1:
        # wyrd weaver: grant free reroll to ally likely to act
        ally = max([h for h in heroes if h.alive], key=lambda h: h.lp)
        hero.lp -= 1
        ally.free_reroll_pool += 1
    elif hero.template.name == "Anansi" and hero.lp >= 1:
        # nudge story: slight enemy disruption approximated as weakened chance
        if random.random() < 0.35:
            e = choose_enemy_target(enemies)
            if e:
                apply_condition(e.conditions, "weakened")
            hero.lp -= 1


def resolve_attack(
    hero: HeroState,
    attack: Attack,
    heroes: List[HeroState],
    enemies: List[EnemyState],
    seal_bank: List[str],
    room_ctx: RoomContext,
    boon_cp: Dict[str, float],
    disabled_boon_color: Optional[str],
) -> Dict[str, int]:
    """Returns event summary for task checks and room effects."""
    events = {
        "kills": 0,
        "spent_lp": 0,
        "received_attack": 0,
        "converted_special_to_lp": 0,
        "rolled_specials": 0,
    }

    # costs
    lp_spent = attack.lp_cost
    if attack.full_spender:
        lp_spent = max(3, hero.lp)
    lp_spent = min(lp_spent, hero.lp)

    if room_ctx.gate.name == "Fateful Gate":
        tax = lp_spent
        if not hero.bloody_fate_ignore_used and tax > 0:
            tax -= 1
            hero.bloody_fate_ignore_used = True
        hero.hp -= max(0, tax)

    hero.lp = clamp(hero.lp - lp_spent, 0, MAX_LP)
    events["spent_lp"] += lp_spent

    if room_ctx.gate.name == "Dampened Gate" and room_ctx.gate_flags.get("dampened_free", 4) <= 0:
        # must pay any special or attack fails; approximate with LP fallback 50%
        if random.random() < 0.5:
            return events
    else:
        room_ctx.gate_flags["dampened_free"] = max(0, room_ctx.gate_flags.get("dampened_free", 4) - 1)

    pool = build_dice_pool(hero, attack, room_ctx, disabled_boon_color)
    if room_ctx.gate.name == "Cursed Gate" and not room_ctx.gate_flags.get("cursed_one_shot"):
        # one free reroll still allowed from unseal text; base gate blocks rerolls.
        pass

    faces = []
    for color, src in pool:
        f = roll_die()
        # reroll policy
        can_reroll = room_ctx.gate.name != "Cursed Gate"
        if not can_reroll and hero.free_reroll_pool <= 0 and room_ctx.gate_flags.get(f"cursed_free_{hero.template.name}", 0) <= 0:
            pass
        else:
            if f == "blank" and (hero.lp > 0 or hero.free_reroll_pool > 0 or room_ctx.gate_flags.get(f"cursed_free_{hero.template.name}", 0) > 0):
                if random.random() < 0.30:
                    if hero.free_reroll_pool > 0:
                        hero.free_reroll_pool -= 1
                    elif room_ctx.gate_flags.get(f"cursed_free_{hero.template.name}", 0) > 0:
                        room_ctx.gate_flags[f"cursed_free_{hero.template.name}"] -= 1
                    else:
                        hero.lp = max(0, hero.lp - 1)
                    f = roll_die()
        faces.append((color, f, src))

    dmg_by_color = Counter()
    specials = Counter()
    for c, f, src in faces:
        if f == "dmg":
            dmg_by_color[c] += 1
            if src:
                boon_cp[src] += CP_DAMAGE
        elif f == "special":
            specials[c] += 1
            events["rolled_specials"] += 1

    # room rule: blank_to_spark once/round/hero
    if room_ctx.room.rule == "blank_to_spark" and not room_ctx.room_flags.get(f"spark_{hero.template.name}"):
        blanks = [i for i, (_, f, _) in enumerate(faces) if f == "blank"]
        if blanks:
            c, _, src = faces[blanks[0]]
            dmg_by_color[c] += 1
            room_ctx.room_flags[f"spark_{hero.template.name}"] = True
            if src:
                boon_cp[src] += CP_DAMAGE

    # bank one seal before spending
    if sum(specials.values()) > 0 and (len(seal_bank) < MAX_SEALS or hero.template.name == "Merlin"):
        if random.random() < 0.45:
            c = max(specials, key=specials.get)
            specials[c] -= 1
            if specials[c] <= 0:
                specials.pop(c, None)
            if hero.template.name == "Merlin" and len(hero.rune_slots) < 3 and random.random() < 0.6:
                hero.rune_slots.append(c)
            elif len(seal_bank) < MAX_SEALS:
                seal_bank.append(c)
            else:
                hero.overflow_seals.append(c)

    # Merlin completed spell cast before conversion
    if hero.template.name == "Merlin" and len(hero.rune_slots) == 3:
        choice = random.choice(["lp", "weaken", "dice"])
        if choice == "lp":
            for _ in range(4):
                random.choice([h for h in heroes if h.alive]).lp = clamp(random.choice([h for h in heroes if h.alive]).lp + 1, 0, MAX_LP)
        elif choice == "weaken":
            e = choose_enemy_target(enemies)
            if e:
                apply_condition(e.conditions, "weakened")
        else:
            for _ in range(3):
                if roll_die() == "dmg":
                    dmg_by_color["blue"] += 1
                else:
                    specials["blue"] += 1
        for s in hero.rune_slots:
            if len(seal_bank) < MAX_SEALS:
                seal_bank.append(s)
            else:
                hero.overflow_seals.append(s)
        hero.rune_slots.clear()

    # channeling seals: 2 same color -> +1 special
    for c in COLORS:
        if seal_bank.count(c) >= 2 and random.random() < 0.25:
            seal_bank.remove(c)
            seal_bank.remove(c)
            specials[c] += 1

    # attack intrinsic special effects
    if attack.name == "Pillar-Breaker Blow" and specials.get("red", 0) >= 1:
        specials["red"] -= 1
        dmg_by_color["red"] += 3  # collision proxy
    elif attack.name == "Club Spin" and specials.get("green", 0) >= 1:
        specials["green"] -= 1
        # splash one extra target later
        attack_targets = 2
    elif attack.name == "True Might" and specials.get("yellow", 0) >= 1 and specials.get("red", 0) >= 2:
        specials["yellow"] -= 1
        specials["red"] -= 2
        dmg_by_color["red"] += 7
        hero.armor += 7
    elif attack.name == "Arcane Volley" and specials.get("blue", 0) >= 1:
        specials["blue"] -= 1
        for _ in range(3):
            if roll_die() == "dmg":
                dmg_by_color["blue"] += 1
            else:
                specials["blue"] += 1
    elif attack.name == "Spiritual Gifts" and specials.get("grey", 0) >= 1:
        specials["grey"] -= 1
        ally = max([h for h in heroes if h.alive], key=lambda h: h.lp)
        ally.lp = clamp(ally.lp + 2, 0, MAX_LP)
    elif attack.name == "Whispers of the Wyrd":
        ally = max([h for h in heroes if h.alive], key=lambda h: h.damage_this_room)
        apply_condition(ally.conditions, "empowered")
    elif attack.name == "Avalon's Light" and specials.get("blue", 0) >= 3:
        specials["blue"] -= 3
        for h in heroes:
            if h.alive:
                h.armor += 4
    elif attack.name == "Blade of Lys" and (specials.get("yellow", 0) >= 1 or specials.get("red", 0) >= 1):
        if specials.get("yellow", 0) >= 1:
            specials["yellow"] -= 1
        else:
            specials["red"] -= 1
        dmg_by_color["yellow"] += 1
        hero.armor += 1
    elif attack.name == "Holy Bolt" and specials.get("yellow", 0) >= 1:
        specials["yellow"] -= 1
        dmg_by_color["yellow"] += 4  # chain proxy
    elif attack.name == "Vanguard Strike":
        hero.armor += 3
    elif attack.name == "Divine Punishment":
        dmg_by_color["yellow"] += lp_spent
    elif attack.name == "Guile Strike":
        if random.random() < 0.35:  # isolated target proxy
            dmg_by_color["green"] += 2
        if specials.get("green", 0) >= 1:
            specials["green"] -= 1
            dmg_by_color["green"] += 1
    elif attack.name == "Story-weaver" and specials.get("yellow", 0) >= 1 and random.random() < 0.35:
        specials["yellow"] -= 1
        for c in ["green", "blue", "red", "grey"]:
            if roll_die() == "dmg":
                dmg_by_color[c] += 1
            else:
                specials[c] += 1
    elif attack.name == "Snare and Sever":
        if specials.get("green", 0) >= 2:
            specials["green"] -= 2
            tgt = choose_enemy_target(enemies)
            if tgt:
                apply_condition(tgt.conditions, "staggered")
    elif attack.name == "The Last Thread":
        iso = random.random() < 0.35
        if iso:
            dmg_by_color["green"] += 5
        if specials.get("green", 0) >= 3 and iso:
            specials["green"] -= 3
            dmg_by_color["green"] += 10

    # relic effects
    if hero.template.name == "Hercules" and specials.get("red", 0) >= 1 and random.random() < 0.5:
        specials["red"] -= 1
        apply_condition(hero.conditions, "empowered")
    if hero.template.name == "Merlin" and specials.get("blue", 0) >= 1 and random.random() < 0.4:
        # reroll up to 4 non-blue simulated as +expected 1 dmg
        specials["blue"] -= 1
        dmg_by_color[random.choice(COLORS)] += 1
    if hero.template.name == "Joan d’Arc" and specials.get("yellow", 0) >= 1 and random.random() < 0.4:
        specials["yellow"] -= 1
        ally = min([h for h in heroes if h.alive], key=lambda h: h.armor)
        ally.armor += 3
    if hero.template.name == "Anansi" and specials.get("green", 0) >= 1 and random.random() < 0.5:
        specials["green"] -= 1
        hero.lp = clamp(hero.lp + 2, 0, MAX_LP)

    # boon effects
    for b in hero.boons:
        if disabled_boon_color and b.color == disabled_boon_color:
            continue
        if b.flat_damage:
            dmg_by_color[random.choice(COLORS)] += b.flat_damage
            boon_cp[b.name] += b.flat_damage * CP_DAMAGE
        if b.flat_armor:
            hero.armor += b.flat_armor
            boon_cp[b.name] += b.flat_armor * CP_ARMOR
        for c, val in b.special_damage.items():
            if specials.get(c, 0) >= 1:
                specials[c] -= 1
                dmg_by_color[c] += val
                boon_cp[b.name] += val * CP_DAMAGE
        for c, val in b.special_lp.items():
            if specials.get(c, 0) >= 1:
                specials[c] -= 1
                hero.lp = clamp(hero.lp + val, 0, MAX_LP)
                boon_cp[b.name] += val * CP_LP
        if b.gives_condition and sum(specials.values()) > 0 and random.random() < 0.4:
            # spend any special
            cc = max(specials, key=specials.get)
            specials[cc] -= 1
            tgt = choose_enemy_target(enemies)
            if tgt:
                apply_condition(tgt.conditions, b.gives_condition)

    # remaining specials -> LP or damage
    for c in list(specials):
        while specials.get(c, 0) > 0:
            specials[c] -= 1
            if hero.lp <= 5:
                hero.lp = clamp(hero.lp + 2, 0, MAX_LP)
                events["converted_special_to_lp"] += 1
            else:
                dmg_by_color[c] += 2

    hero.lp = clamp(hero.lp + attack.lp_gain, 0, MAX_LP)

    # condition combat modifiers
    if hero.conditions.has("empowered"):
        dmg_by_color[random.choice(COLORS)] += 1
    if hero.conditions.has("exalted"):
        dmg_by_color[random.choice(COLORS)] += 3
    if hero.conditions.has("weakened"):
        dmg_by_color[random.choice(COLORS)] = max(0, dmg_by_color[random.choice(COLORS)] - 1)
    if hero.conditions.has("enfeebled"):
        dmg_by_color[random.choice(COLORS)] = max(0, dmg_by_color[random.choice(COLORS)] - 3)

    # room rule: mark prey
    if room_ctx.room.rule == "mark_prey" and events["rolled_specials"] >= 2 and not room_ctx.room_flags.get("mark_prey_used"):
        tgt = choose_enemy_target(enemies)
        if tgt:
            apply_condition(tgt.conditions, "breached")
        room_ctx.room_flags["mark_prey_used"] = True

    # multi-target assignment (greedy lowest hp)
    targets_n = attack.targets
    if attack.name == "Club Spin" and 'attack_targets' in locals():
        targets_n = max(targets_n, attack_targets)
    targets = sorted([e for e in enemies if e.alive], key=lambda e: e.hp)[: max(1, targets_n)]
    if not targets:
        return events

    # split by colors round-robin
    color_items = []
    for c, v in dmg_by_color.items():
        color_items.extend([c] * v)
    random.shuffle(color_items)

    splits = [Counter() for _ in targets]
    for i, c in enumerate(color_items):
        splits[i % len(targets)][c] += 1

    for tgt, dm in zip(targets, splits):
        total = 0
        for color, amount in dm.items():
            amt = amount
            if tgt.template.vuln == color:
                amt *= 2
            total += amt
        if room_ctx.gate.name == "Reinforced Gate" and room_ctx.round_no == 1:
            arm = tgt.armor + 1
        elif room_ctx.gate.name == "Sturdy Gate" and len([e for e in enemies if e.alive]) >= 2:
            arm = tgt.armor + 1
        else:
            arm = tgt.armor

        if room_ctx.gate.name == "Reinforced Gate" and room_ctx.round_no == 1 and not hero.first_attack_done:
            arm = max(0, arm - 1)

        post = max(0, total - arm)
        if tgt.conditions.has("exposed"):
            post += 1
        if tgt.conditions.has("breached"):
            post += 3

        # Titan grip living weapon
        if hero.template.name == "Hercules" and hero.holding_enemy and random.random() < 0.6:
            post += 1
            # held enemy chip damage
            pool = [e for e in enemies if e.alive and e is not tgt]
            if pool:
                random.choice(pool).hp -= 1

        tgt.hp -= post
        hero.damage_this_room += post
        room_ctx.attacked_enemy_ids.add(id(tgt))

        if tgt.hp <= 0 and tgt.alive:
            tgt.alive = False
            events["kills"] += 1
            if room_ctx.gate.name == "Glorious Gate":
                hero.lp = max(0, hero.lp - 1)
            if room_ctx.gate.name == "Shattering Gate":
                for h in heroes:
                    if h.alive:
                        if h.ignored_next_shatter:
                            h.ignored_next_shatter = False
                        else:
                            h.hp -= 1
            if room_ctx.gate.name == "Vengeance's Gate":
                for e2 in enemies:
                    if e2.alive:
                        apply_condition(e2.conditions, "empowered")

            for b in hero.boons:
                if b.on_kill_lp:
                    hero.lp = clamp(hero.lp + b.on_kill_lp, 0, MAX_LP)
                    boon_cp[b.name] += b.on_kill_lp * CP_LP

    hero.first_attack_done = True
    return events


def resolve_enemy_turn(enemy: EnemyState, heroes: List[HeroState], room_ctx: RoomContext, taint_box: List[int]):
    if not enemy.alive:
        return

    if room_ctx.gate.name == "Glutton's Gate":
        # remove one negative from enemy
        neg = [c for c in enemy.conditions.active if c in NEGATIVE_CONDITIONS]
        if neg:
            enemy.conditions.remove(neg[0])
            enemy.hp += 1

    target = enemy_pick_hero(enemy, heroes)
    if not target:
        return

    dmg = enemy.dmg
    if enemy.conditions.has("weakened"):
        dmg -= 1
    if enemy.conditions.has("enfeebled"):
        dmg -= 3
    if enemy.conditions.has("empowered"):
        dmg += 1
    if enemy.conditions.has("exalted"):
        dmg += 3
    dmg = max(0, dmg)

    incoming = dmg
    if target.conditions.has("exposed"):
        incoming += 1
    if target.conditions.has("breached"):
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
    if "web" in enemy.template.effects:
        apply_condition(target.conditions, "staggered")
    if "armor_up" in enemy.template.effects:
        apply_condition(enemy.conditions, "toughened")
    if "splash" in enemy.template.effects:
        others = [h for h in heroes if h.alive and h is not target]
        if others:
            random.choice(others).hp -= 1
    if "terror" in enemy.template.effects:
        # push ignored; model by adding exposed to random hero in wave chance
        if random.random() < 0.35:
            apply_condition(random.choice([h for h in heroes if h.alive]).conditions, "exposed")

    room_ctx.first_enemy_attack_done = True

    if target.hp <= 0 and target.alive:
        target.alive = False
        taint_box[0] += 1


# ---------- fragment tasks and boon draft ----------
def fragment_task_check(
    color: str,
    hero: HeroState,
    event: Dict[str, int],
    received_attack_this_round: bool,
    enemies_alive_count: int,
) -> bool:
    if color == "red":
        return event["kills"] > 0 and random.random() < 0.5
    if color == "blue":
        return event["spent_lp"] >= 3
    if color == "green":
        return event["kills"] > 0 and random.random() < 0.35
    if color == "grey":
        return received_attack_this_round
    if color == "yellow":
        return enemies_alive_count >= 2 and random.random() < 0.4
    return False


def draft_boon(hero: HeroState, color: str, boon_decks: Dict[str, deque], boon_cp: Dict[str, float]):
    draw_n = 3
    extra_buys = 0
    while hero.lp > 0 and extra_buys < 3 and random.random() < 0.35:
        hero.lp -= 1
        draw_n += 1
        extra_buys += 1

    deck = boon_decks[color]
    draws = []
    for _ in range(draw_n):
        if not deck:
            # reshuffle from catalog if exhausted
            items = boon_catalog()[color][:]
            random.shuffle(items)
            deck.extend(items)
        draws.append(deck.popleft())

    def score(b: Boon):
        return (
            sum(b.dice_bonus.values()) * 3
            + sum(b.special_damage.values()) * 0.8
            + sum(b.special_lp.values()) * 0.6
            + b.flat_damage * 1.0
            + b.flat_armor * 1.2
            + b.on_kill_lp * 0.7
            + (2 if b.gives_condition else 0)
        )

    pick = max(draws, key=score)
    hero.boons.append(pick)

    # put others on bottom in descending score for deterministic policy
    for b in sorted([x for x in draws if x is not pick], key=score, reverse=True):
        deck.append(b)

    boon_cp[pick.name] += 0.0


# ---------- simulation ----------
def run_single(seed_offset: int = 0) -> Dict:
    if seed_offset:
        random.seed(random.randint(1, 10**9) + seed_offset)

    heroes = [HeroState(template=t, hp=t.max_hp) for t in HEROES]
    taint_box = [0]
    spawn_level = 1
    seal_bank: List[str] = []
    essence = 0

    # finite decks
    sg = standard_gates()
    ng = nexus_gates()
    br = basic_rooms()
    tr = temple_rooms()
    nr = nexus_rooms()
    random.shuffle(sg)
    random.shuffle(ng)
    random.shuffle(br)
    random.shuffle(tr)
    random.shuffle(nr)
    standard_gate_deck = deque(sg)
    nexus_gate_deck = deque(ng)
    basic_room_deck = deque(br)
    temple_room_deck = deque(tr)
    nexus_room_deck = deque(nr)

    boon_decks = {}
    for c, cards in boon_catalog().items():
        cards = cards[:]
        random.shuffle(cards)
        boon_decks[c] = deque(cards)

    room_hp, room_dmg, room_taint = [], [], []
    boon_cp = defaultdict(float)

    collapse_pending_rounds = None

    for room_i in range(1, MAX_ROOMS + 1):
        # if party dead, fill remaining
        if not any(h.alive for h in heroes):
            for _ in range(room_i, MAX_ROOMS + 1):
                room_hp.append({h.template.name: 0.0 for h in heroes})
                room_dmg.append({h.template.name: 0.0 for h in heroes})
                room_taint.append(float(taint_box[0]))
            break

        # room reset
        for h in heroes:
            h.damage_this_room = 0.0
            h.lp = 0 if h.alive else h.lp
            h.armor = 0
            h.first_attack_done = False
            h.free_reroll_pool = 0
            h.bloody_fate_ignore_used = False
            h.ignored_next_shatter = False
            if h.template.name == "Joan d’Arc":
                h.oriflamme_active = True
            if h.template.name == "Anansi":
                h.on_web = True

        # choose gates
        options = [draw_deck_card(standard_gate_deck, standard_gates()), draw_deck_card(standard_gate_deck, standard_gates()), draw_deck_card(nexus_gate_deck, nexus_gates())]
        gate = pick_gate(options, taint_box[0])

        # unseal
        taint_box[0] = unseal_gate_if_possible(gate, seal_bank, taint_box[0], [h for h in heroes if h.alive])

        # gate starts
        for h in heroes:
            if not h.alive:
                continue
            apply_gate_start(h, gate)
            if gate.name == "Shattering Gate":
                h.ignored_next_shatter = True
            if gate.name == "Cursed Gate":
                h.free_reroll_pool += 1
            if gate.name == "Temple of Purity":
                # remove one negative else +1 LP
                neg = [c for c in h.conditions.active if c in NEGATIVE_CONDITIONS]
                if neg:
                    h.conditions.remove(neg[0])
                else:
                    h.lp = clamp(h.lp + 1, 0, MAX_LP)

        if gate.name == "Glorious Gate":
            for _ in range(12):
                random.choice([h for h in heroes if h.alive]).lp = clamp(random.choice([h for h in heroes if h.alive]).lp + 1, 0, 6)

        # draw room
        if gate.gate_type in ("basic", "elite"):
            room = draw_deck_card(basic_room_deck, basic_rooms())
            spawns = room.spawns[5 if gate.gate_type == "elite" else gate.threat]
        elif gate.gate_type == "temple":
            room = draw_deck_card(temple_room_deck, temple_rooms())
            spawns = room.spawns[1]
        else:
            room = draw_deck_card(nexus_room_deck, nexus_rooms())
            spawns = room.spawns[gate.threat]

        room_ctx = RoomContext(gate=gate, room=room)
        if gate.name == "Dampened Gate":
            room_ctx.gate_flags["dampened_free"] = 4

        # curse of denied deity boons
        disabled_color = None
        if gate.name == "Nexus Denied Strength":
            disabled_color = "red"
        elif gate.name == "Nexus Denied Magic":
            disabled_color = "blue"
        elif gate.name == "Nexus Denied Speed":
            disabled_color = "green"
        elif gate.name == "Nexus Denied Spirit":
            disabled_color = "grey"
        elif gate.name == "Nexus Denied Faith":
            disabled_color = "yellow"

        enemies = []
        for n, elite in spawns:
            lv = min(6, spawn_level + (1 if elite else 0))
            enemies.append(spawn_enemy(n, lv))

        fragments = gate.fragments[:]

        # combat loop
        safety_rounds = 0
        while any(e.alive for e in enemies) and any(h.alive for h in heroes):
            safety_rounds += 1
            if safety_rounds > 12:
                break

            room_ctx.round_no += 1
            room_ctx.first_enemy_attack_done = False
            room_ctx.attacked_enemy_ids.clear()
            room_ctx.room_flags.clear()

            # start-of-round room effects
            if room.rule == "eye_eats_legend":
                alive = [h for h in heroes if h.alive]
                if alive:
                    top = max(alive, key=lambda h: h.lp)
                    top.lp = max(0, top.lp - 3)
            if room.rule == "bargain_fate":
                alive = [h for h in heroes if h.alive]
                if alive:
                    v = max(alive, key=lambda h: h.hp)
                    v.hp -= 6
                    v.lp = clamp(v.lp + 2, 0, MAX_LP)
            if room.rule == "stand_firm":
                for h in heroes:
                    if h.alive and len([e for e in enemies if e.alive]) >= 2:
                        apply_condition(h.conditions, "empowered")
            if room.rule == "together_rise":
                for h in heroes:
                    if h.alive and random.random() < 0.6:
                        h.lp = clamp(h.lp + 1, 0, MAX_LP)

            # initiative
            tokens = [h.template.name for h in heroes if h.alive] + [f"E{i}" for i, e in enumerate(enemies) if e.alive]
            random.shuffle(tokens)
            if gate.name == "Assassin's Gate":
                tokens.sort(key=lambda t: 0 if t.startswith("E") else 1)

            # per-round task trackers
            received_attack_round = {h.template.name: False for h in heroes}

            for t in tokens:
                if t.startswith("E"):
                    idx = int(t[1:])
                    if idx < len(enemies) and enemies[idx].alive:
                        resolve_enemy_turn(enemies[idx], heroes, room_ctx, taint_box)
                        # mark target attacked is implicit; approximate all alive possible for grey task if random
                        for h in heroes:
                            if h.alive and random.random() < 0.25:
                                received_attack_round[h.template.name] = True
                else:
                    h = hero_by_name(heroes, t)
                    if not h.alive:
                        continue

                    # armor decay start
                    h.armor = 0
                    clear_by_expiry(h.conditions, "next_move")

                    # anansi web passive
                    if h.template.name == "Anansi" and h.on_web:
                        h.armor += 1

                    # joan oriflamme reroll aura -> free reroll
                    if h.template.name == "Joan d’Arc" and h.oriflamme_active:
                        h.free_reroll_pool += 1

                    # utility usage
                    maybe_use_utility(h, heroes, enemies)

                    atk = pick_attack(h, enemies)
                    events = resolve_attack(h, atk, heroes, enemies, seal_bank, room_ctx, boon_cp, disabled_color)

                    # room rules hooks
                    if room.rule == "special_surge" and events["converted_special_to_lp"] > 0 and not room_ctx.room_flags.get(f"ss_{h.template.name}"):
                        h.lp = clamp(h.lp + 1, 0, MAX_LP)
                        room_ctx.room_flags[f"ss_{h.template.name}"] = True
                    if room.rule == "answer_wound" and h.hp < h.template.max_hp and not room_ctx.room_flags.get(f"aw_{h.template.name}"):
                        h.lp = clamp(h.lp + 1, 0, MAX_LP)
                        room_ctx.room_flags[f"aw_{h.template.name}"] = True
                    if room.rule == "hold_line" and random.random() < 0.5 and not room_ctx.room_flags.get(f"hl_{h.template.name}"):
                        h.armor += 1
                        room_ctx.room_flags[f"hl_{h.template.name}"] = True
                    if room.rule == "spend_to_mend" and events["spent_lp"] >= 4 and not room_ctx.room_flags.get(f"stm_{h.template.name}"):
                        h.hp = min(h.template.max_hp, h.hp + 1)
                        room_ctx.room_flags[f"stm_{h.template.name}"] = True

                    # fragment claims: by task first, otherwise action chance
                    if fragments:
                        claimed = False
                        # check task for first matching color still in room
                        for c in list(dict.fromkeys(fragments)):
                            if fragment_task_check(c, h, events, received_attack_round[h.template.name], len([e for e in enemies if e.alive])):
                                fragments.remove(c)
                                if c in seal_bank:
                                    seal_bank.remove(c)
                                else:
                                    taint_box[0] += 1
                                draft_boon(h, c, boon_decks, boon_cp)
                                claimed = True
                                if room.rule == "task_reward" and not room_ctx.room_flags.get(f"tr_{h.template.name}"):
                                    # extra card view approximated by +1 LP
                                    h.lp = clamp(h.lp + 1, 0, MAX_LP)
                                    room_ctx.room_flags[f"tr_{h.template.name}"] = True
                                break
                        if not claimed and random.random() < 0.30:
                            c = fragments.pop(0)
                            if c in seal_bank:
                                seal_bank.remove(c)
                            else:
                                taint_box[0] += 1
                            draft_boon(h, c, boon_decks, boon_cp)

                    # end turn condition dmg
                    if h.conditions.has("bleeding"):
                        h.hp -= 1
                    if h.conditions.has("hemorrhaging"):
                        h.hp -= 3

                    # unmaking ray room rule
                    if room.rule == "unmaking_ray" and h.armor > 0 and not room_ctx.room_flags.get(f"um_{h.template.name}"):
                        room_ctx.room_flags[f"um_{h.template.name}"] = True
                        h.armor = 0

                    if h.hp <= 0 and h.alive:
                        h.alive = False
                        taint_box[0] += 1

            # round end taint and despair
            taint_box[0] += 1
            despair = 0 if taint_box[0] <= 5 else 1 if taint_box[0] <= 10 else 2 if taint_box[0] <= 15 else 3
            for h in heroes:
                if h.alive and len(h.boons) < despair:
                    taint_box[0] += 1

            # surges
            if taint_box[0] in (5, 10, 15):
                for h in heroes:
                    clear_positive(h.conditions)
                for e in enemies:
                    clear_negative(e.conditions)
                spawn_level = min(6, spawn_level + 1)

            # collapse
            if taint_box[0] >= 20:
                if collapse_pending_rounds is None:
                    collapse_pending_rounds = 1
                else:
                    collapse_pending_rounds -= 1
                    if collapse_pending_rounds < 0:
                        for h in heroes:
                            h.alive = False
                            h.hp = 0
                        break

        # room end temple rites / nexus essence / resurrect
        if not any(e.alive for e in enemies):
            if gate.gate_type == "nexus":
                essence += 1
            if gate.name == "Temple of Courage":
                for h in heroes:
                    if h.alive:
                        apply_condition(h.conditions, "toughened")
            if gate.name == "Temple of Mercy":
                for h in heroes:
                    if h.alive:
                        h.hp = min(h.template.max_hp, h.hp + 4)
            if gate.name == "Temple of Clarity":
                for h in heroes:
                    if h.alive:
                        h.lp = clamp(h.lp + 3, 0, MAX_LP)
            if gate.name == "Temple of Purity":
                taint_box[0] = max(0, taint_box[0] - 2)

            # temple exchanges abstract policy
            if gate.gate_type == "temple":
                alive = [h for h in heroes if h.alive]
                for h in alive:
                    if random.random() < 0.30:
                        taint_box[0] = max(0, taint_box[0] - 1)
                    if random.random() < 0.20 and h.boons:
                        h.boons.pop(random.randrange(len(h.boons)))

            # resurrect dead heroes when room cleared
            for h in heroes:
                if not h.alive:
                    h.alive = True
                    h.hp = h.template.max_hp // 2
                    h.lp = 0
                    h.conditions.active.clear()

        room_hp.append({h.template.name: float(max(0, h.hp)) for h in heroes})
        room_dmg.append({h.template.name: float(h.damage_this_room) for h in heroes})
        room_taint.append(float(taint_box[0]))

    return {
        "room_hp": room_hp,
        "room_dmg": room_dmg,
        "room_taint": room_taint,
        "boon_cp": dict(boon_cp),
    }


def aggregate(results: List[Dict]) -> Dict:
    hero_names = [h.name for h in HEROES]
    avg_hp, avg_dmg, avg_taint = [], [], []

    for r in range(MAX_ROOMS):
        hp_row, dmg_row = {}, {}
        for hn in hero_names:
            hp_vals = [res["room_hp"][r][hn] for res in results]
            dmg_vals = [res["room_dmg"][r][hn] for res in results]
            hp_row[hn] = statistics.fmean(hp_vals)
            dmg_row[hn] = statistics.fmean(dmg_vals)
        avg_hp.append(hp_row)
        avg_dmg.append(dmg_row)
        avg_taint.append(statistics.fmean(res["room_taint"][r] for res in results))

    boon_tot = defaultdict(float)
    for res in results:
        for k, v in res["boon_cp"].items():
            boon_tot[k] += v
    boon_avg = {k: v / len(results) for k, v in sorted(boon_tot.items(), key=lambda kv: kv[1], reverse=True)}

    return {
        "avg_hp": avg_hp,
        "avg_dmg": avg_dmg,
        "avg_taint": avg_taint,
        "boon_cp_avg": boon_avg,
    }


def print_report(agg: Dict, sims: int):
    print(f"Spellrift Dungeons simulation report ({sims} runs)")
    print("=" * 72)
    for i in range(MAX_ROOMS):
        print(f"\nRoom {i+1}")
        print(f"  Avg Taint: {agg['avg_taint'][i]:.2f}")
        print("  Avg Hero HP at room end:")
        for hn, v in agg["avg_hp"][i].items():
            print(f"    - {hn:12s}: {v:7.2f}")
        print("  Avg hero damage in room:")
        for hn, v in agg["avg_dmg"][i].items():
            print(f"    - {hn:12s}: {v:7.2f}")

    print("\nTop 50 boons by average CP contribution per run")
    print("-" * 72)
    for i, (name, cp) in enumerate(list(agg["boon_cp_avg"].items())[:50], start=1):
        print(f"{i:2d}. {name:34s} {cp:8.3f} CP/run")


def main():
    p = argparse.ArgumentParser(description="Spellrift Dungeons v0.4.2 balance simulator")
    p.add_argument("--sims", type=int, default=DEFAULT_SIMS)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    random.seed(args.seed)
    results = [run_single(i) for i in range(args.sims)]
    agg = aggregate(results)
    print_report(agg, args.sims)


if __name__ == "__main__":
    main()
