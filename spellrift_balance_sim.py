#!/usr/bin/env python3
"""Spellrift Dungeons alpha simulator (abstracted positionless model).

This simulator intentionally ignores grid movement/terrain geometry, but models:
- initiative and per-turn flow
- hero attacks, LP economy, specials, rerolls, seals and seal channeling
- gate + room draw loop with finite shuffled decks per run
- villain attacks, level scaling, core villain effects
- condition escalation/opposition and surge cleanup
- fragment claiming + boon drafting
- room-wise aggregates up to room 7 over Monte Carlo runs
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import random
import statistics
from typing import Dict, List, Optional, Tuple

CP_DAMAGE = 1.0
CP_LP = 1.0
MAX_ROOMS = 7
DEFAULT_SIMS = 20_000

POSITIVE_CONDS = {"empowered", "exalted", "toughened", "armored"}
NEGATIVE_CONDS = {"weakened", "enfeebled", "exposed", "breached", "bleeding", "hemorrhaging", "staggered", "slowed"}
CONDITION_LADDERS = {
    "weakened": ["weakened", "enfeebled"],
    "empowered": ["empowered", "exalted"],
    "toughened": ["toughened", "armored"],
    "exposed": ["exposed", "breached"],
    "bleeding": ["bleeding", "hemorrhaging"],
    "slowed": ["slowed", "staggered"],
}
OPPOSING = {
    "weakened": "empowered",
    "enfeebled": "exalted",
    "empowered": "weakened",
    "exalted": "enfeebled",
    "toughened": "exposed",
    "armored": "breached",
    "exposed": "toughened",
    "breached": "armored",
}


@dataclass
class Attack:
    name: str
    base_dice: Dict[str, int]
    lp_cost: int = 0
    lp_gain: int = 0
    full_spender: bool = False
    range_type: str = "melee"
    special_rules: Dict[str, int] = field(default_factory=dict)


@dataclass
class HeroTemplate:
    name: str
    max_hp: int
    relic_die_color: str
    attacks: List[Attack]


@dataclass
class HeroState:
    template: HeroTemplate
    hp: int
    lp: int = 0
    armor: int = 0
    alive: bool = True
    conditions: set[str] = field(default_factory=set)
    boons: List["Boon"] = field(default_factory=list)
    damage_done_this_room: float = 0.0
    reroll_free_this_round: bool = False
    first_attack_this_round: bool = True
    rune_slots: List[str] = field(default_factory=list)


@dataclass
class VillainTemplate:
    name: str
    hp: int
    armor: int
    damage: int
    target_rule: str
    vulnerability: Optional[str] = None
    effects: Tuple[str, ...] = ()


@dataclass
class Enemy:
    template: VillainTemplate
    hp: int
    armor: int
    damage: int
    level: int
    conditions: set[str] = field(default_factory=set)

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Gate:
    name: str
    gate_type: str
    threat: int
    fragments: List[str]
    start_lp: int = 0
    start_heal: int = 0
    rule_tag: str = "none"


@dataclass
class RoomCard:
    name: str
    room_type: str
    spawns_by_threat: Dict[int, List[Tuple[str, bool]]]
    rule_tag: str = "none"


@dataclass
class Boon:
    name: str
    color: str
    dice_bonus: Dict[str, int] = field(default_factory=dict)
    on_attack_flat_bonus: int = 0
    on_color_special_bonus_damage: Dict[str, int] = field(default_factory=dict)
    on_color_special_bonus_lp: Dict[str, int] = field(default_factory=dict)
    on_kill_lp: int = 0


HEROES = [
    HeroTemplate("Hercules", 25, "red", [
        Attack("Pillar-Breaker Blow", {"red": 3}, lp_gain=1, special_rules={"red": 1}),
        Attack("Club Spin", {"green": 2}, lp_gain=2, special_rules={"green": 1}),
        Attack("Colossus Smash", {"red": 4}, lp_cost=2, special_rules={"red": 2}),
        Attack("True Might", {"yellow": 4, "red": 3}, lp_cost=3, full_spender=True),
    ]),
    HeroTemplate("Merlin", 18, "blue", [
        Attack("Arcane Volley", {"blue": 2}, lp_gain=1, range_type="ranged", special_rules={"blue": 1}),
        Attack("Spiritual Gifts", {"grey": 2}, lp_gain=2, range_type="ranged", special_rules={"grey": 1}),
        Attack("Whispers of the Wyrd", {"grey": 2}, lp_cost=2, range_type="ranged"),
        Attack("Avalon's Light", {"blue": 7}, lp_cost=3, full_spender=True),
    ]),
    HeroTemplate("Joan d’Arc", 20, "yellow", [
        Attack("Blade of Lys", {"yellow": 1, "red": 2}, lp_gain=1, special_rules={"yellow": 1, "red": 1}),
        Attack("Holy Bolt", {"yellow": 2}, lp_gain=2, range_type="ranged", special_rules={"yellow": 1}),
        Attack("Vanguard Strike", {"red": 3}, lp_cost=3, range_type="ranged"),
        Attack("Divine Punishment", {"yellow": 4}, lp_cost=3, full_spender=True),
    ]),
    HeroTemplate("Anansi", 20, "green", [
        Attack("Guile Strike", {"green": 2}, lp_gain=1, special_rules={"green": 1}),
        Attack("Story-weaver", {"yellow": 2}, lp_gain=2, special_rules={"yellow": 1}),
        Attack("Snare and Sever", {"green": 3, "blue": 2}, lp_cost=2, range_type="ranged", special_rules={"green": 2}),
        Attack("The Last Thread", {"green": 3}, lp_cost=3, full_spender=True),
    ]),
]

VILLAINS = {
    "Voidling": VillainTemplate("Voidling", 2, 0, 2, "closest", effects=("drain_lp",)),
    "Shadow Spinner": VillainTemplate("Shadow Spinner", 4, 0, 3, "low_hp", vulnerability="red", effects=("staggered",)),
    "Void Soldier": VillainTemplate("Void Soldier", 5, 0, 3, "closest", vulnerability="blue", effects=("self_toughened",)),
    "Dark Wizard": VillainTemplate("Dark Wizard", 10, 1, 3, "far", vulnerability="yellow", effects=("ignore_armor", "push")),
    "Shadow Banshee": VillainTemplate("Shadow Banshee", 10, 0, 4, "high_lp", vulnerability="grey", effects=("terror",)),
    "Void Treant": VillainTemplate("Void Treant", 12, 2, 3, "closest", vulnerability="green", effects=("splash",)),
}
LEVEL_MODS = {1: (0, 0, 0), 2: (0, 2, 1), 3: (1, 5, 3), 4: (1, 7, 5), 5: (2, 10, 7), 6: (2, 15, 10)}


STANDARD_GATES = [
    Gate("Spiked Gate", "basic", 2, ["red", "red"], start_lp=1),
    Gate("Cursed Gate", "basic", 2, ["blue", "blue"], start_lp=1, rule_tag="no_reroll"),
    Gate("Reinforced Gate", "basic", 2, ["red", "yellow"], start_lp=1, rule_tag="enemy_armor_round1"),
    Gate("Predator's Gate", "basic", 2, ["red", "green"], start_lp=1),
    Gate("Assassin's Gate", "basic", 2, ["green", "yellow"], start_heal=2, rule_tag="enemy_first"),
    Gate("Painful Gate", "basic", 2, ["grey", "yellow"], start_heal=1, start_lp=1, rule_tag="heal_slows"),
    Gate("Sturdy Gate", "basic", 3, ["red", "blue", "green"], start_heal=1, start_lp=2, rule_tag="guardian_foes"),
    Gate("Glutton's Gate", "basic", 3, ["blue", "green", "grey"], start_heal=2, start_lp=1),
    Gate("Glorious Gate", "basic", 3, ["red", "grey", "yellow"], start_lp=3, rule_tag="lose_lp_on_kill"),
    Gate("Shattering Gate", "basic", 3, ["red", "green", "yellow"], start_lp=2, rule_tag="shatterburst"),
    Gate("Vengeance's Gate", "elite", 5, ["red", "green"], start_lp=2, rule_tag="vengeance"),
    Gate("Banner's Gate", "elite", 5, ["red", "grey"], start_heal=2, rule_tag="no_positive"),
    Gate("Fateful Gate", "elite", 5, ["blue", "yellow"], start_lp=1, rule_tag="lp_costs_hp"),
    Gate("Dampened Gate", "elite", 5, ["green", "green"], rule_tag="pay_special_or_fail"),
    Gate("Large Gate", "elite", 5, ["grey", "grey"], start_lp=1),
    Gate("Temple of Courage", "temple", 1, ["yellow"], start_lp=1),
    Gate("Temple of Mercy", "temple", 1, ["grey"], start_heal=1),
    Gate("Temple of Clarity", "temple", 1, ["blue"], start_lp=1),
    Gate("Temple of Fire", "temple", 1, ["green"], start_lp=1),
    Gate("Temple of Purity", "temple", 1, ["yellow"], start_lp=1),
]
NEXUS_GATES = [
    Gate("Nexus of Denied Strength", "nexus", 3, ["blue", "grey"], start_lp=1, start_heal=1),
    Gate("Nexus of Denied Magic", "nexus", 3, ["green", "yellow"], start_lp=2),
    Gate("Nexus of Denied Speed", "nexus", 3, ["red", "blue"], start_lp=1),
    Gate("Nexus of Denied Spirit", "nexus", 3, ["yellow", "yellow"], start_heal=2),
    Gate("Nexus of Denied Faith", "nexus", 3, ["blue", "grey", "yellow"], start_lp=2, start_heal=1),
    Gate("Nexus of Denied Destiny", "nexus", 4, ["red", "red", "blue"], start_lp=3, rule_tag="minus_hero_die"),
]


def basic_rooms() -> List[RoomCard]:
    # uses full room list but single rule tags for key numerical effects
    data = [
        ("Steelbound Footing", 2, ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], 3, ["Dark Wizard", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], 5, [("Void Treant", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], "armor_on_engage"),
        ("Fate’s Favor", 2, ["Void Soldier", "Void Soldier", "Void Soldier"], 3, ["Void Soldier", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Void Soldier", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], "free_reroll"),
        ("The Flanking Hymn", 2, ["Void Soldier", "Void Soldier", "Shadow Spinner"], 3, ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Dark Wizard", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], "flank_bonus"),
        ("Runes of Clarity", 2, ["Dark Wizard", "Void Soldier"], 3, ["Shadow Banshee", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Shadow Banshee", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], "special_lp_bonus"),
        ("Prayer of the Bold", 2, ["Void Soldier", "Void Soldier", "Shadow Spinner"], 3, ["Void Soldier", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Void Treant", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], "empower_if_surrounded"),
        ("The Mercy Sigil", 2, ["Void Soldier", "Shadow Spinner", "Shadow Spinner"], 3, ["Shadow Spinner", "Shadow Spinner", "Shadow Spinner", "Shadow Spinner"], 5, [("Dark Wizard", True), ("Shadow Spinner", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], "ignore_first_negative"),
        ("Echo of Teamwork", 2, ["Dark Wizard", "Shadow Spinner"], 3, ["Void Treant", "Void Soldier", "Shadow Spinner", "Shadow Spinner"], 5, [("Void Treant", True), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], "follow_up_die"),
        ("The Watcher’s Blind Spot", 2, ["Void Soldier", "Void Soldier", "Shadow Spinner"], 3, ["Shadow Banshee", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Shadow Banshee", True), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], "none"),
        ("Shatter-Song Hall", 2, ["Void Soldier", "Void Soldier", "Void Soldier"], 3, ["Void Treant", "Void Soldier", "Void Soldier", "Shadow Spinner"], 5, [("Void Soldier", True), ("Void Treant", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], "none"),
    ]
    rooms: List[RoomCard] = []
    for name, t2, s2, t3, s3, t5, s5, tag in data:
        rooms.append(RoomCard(name, "basic", {
            t2: [(x, False) for x in s2],
            t3: [(x, False) for x in s3],
            t5: s5,
        }, tag))
    return rooms


def temple_rooms() -> List[RoomCard]:
    return [
        RoomCard("Temple Ruin 2", "temple", {1: [("Shadow Spinner", False), ("Shadow Spinner", False)]}, "temple_exchange"),
        RoomCard("Temple Ruin 3", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_exchange"),
        RoomCard("Temple Ruin 4", "temple", {1: [("Void Soldier", False), ("Void Soldier", False)]}, "temple_exchange"),
        RoomCard("Temple Ruin 5", "temple", {1: [("Void Soldier", False), ("Shadow Spinner", False)]}, "temple_exchange"),
        RoomCard("Temple Ruin 6", "temple", {1: [("Shadow Spinner", False), ("Shadow Spinner", False)]}, "temple_exchange"),
    ]


def nexus_rooms() -> List[RoomCard]:
    return [
        RoomCard("Altar Room 2", "nexus", {3: [("Void Treant", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_omen"),
        RoomCard("Altar Room 3", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Shadow Spinner", False), ("Shadow Spinner", False)], 4: [("Shadow Banshee", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_omen"),
        RoomCard("Altar Room 4", "nexus", {3: [("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)], 4: [("Void Treant", False), ("Dark Wizard", False), ("Void Soldier", False), ("Void Soldier", False), ("Shadow Spinner", False)]}, "eye_omen"),
    ]


def boon_catalog() -> Dict[str, List[Boon]]:
    return {
        "red": [Boon("War God’s Might", "red", {"red": 2}), Boon("War God’s Power", "red", {"red": 2}), Boon("Mjolnir’s Spark", "red", {"red": 1}, on_color_special_bonus_damage={"red": 5}), Boon("Onslaught", "red", {}, on_color_special_bonus_damage={"red": 5})],
        "green": [Boon("Blessing of Alacrity", "green", {"green": 2}), Boon("Wind Step", "green", {"green": 1}), Boon("Whisper of the Coffin", "green", {"green": 1}, on_attack_flat_bonus=2), Boon("Coffin Nail", "green", {}, on_color_special_bonus_damage={"green": 8})],
        "grey": [Boon("Scriber's Insight", "grey", {"grey": 2}), Boon("Glyph's Wisdom", "grey", {"grey": 2}), Boon("Athena’s Rally", "grey", {"grey": 1}, on_color_special_bonus_lp={"grey": 1}), Boon("Ancient Secrets", "grey", {}, on_color_special_bonus_lp={"grey": 4})],
        "blue": [Boon("Allfather's Vision", "blue", {"blue": 2}), Boon("Rune Writing", "blue", {"blue": 1}), Boon("Nile's Flow", "blue", {"blue": 1}, on_color_special_bonus_lp={"blue": 2}), Boon("Dooming Hex", "blue", {"blue": 1}, on_color_special_bonus_damage={"blue": 2})],
        "yellow": [Boon("Fey Majesty", "yellow", {"yellow": 2}), Boon("Courtly Glamour", "yellow", {"yellow": 2}), Boon("Zeus’ Judgment", "yellow", {}, on_color_special_bonus_damage={"yellow": 7}), Boon("Fae Bargain", "yellow", {"yellow": 1}, on_color_special_bonus_lp={"yellow": 8})],
    }


def roll_die() -> str:
    r = random.random()
    if r < 0.5:
        return "dmg"
    if r < (5 / 6):
        return "special"
    return "blank"


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def init_deck(cards: List):
    deck = cards.copy()
    random.shuffle(deck)
    return deck


def draw_one(deck: List, refill: Optional[List] = None):
    if not deck and refill:
        deck.extend(refill.copy())
        random.shuffle(deck)
    return deck.pop() if deck else None


def apply_condition(entity: HeroState | Enemy, incoming: str):
    opp = OPPOSING.get(incoming)
    if opp and opp in entity.conditions:
        entity.conditions.remove(opp)
        weaker = CONDITION_LADDERS.get(opp, [opp])[0]
        if weaker in entity.conditions:
            entity.conditions.remove(weaker)
        return

    if incoming in CONDITION_LADDERS:
        weak, strong = CONDITION_LADDERS[incoming]
        if strong in entity.conditions:
            return
        if weak in entity.conditions:
            entity.conditions.remove(weak)
            entity.conditions.add(strong)
            return
        entity.conditions.add(weak)
    else:
        entity.conditions.add(incoming)


def remove_surge_conditions(heroes: List[HeroState], enemies: List[Enemy]):
    for h in heroes:
        h.conditions = {c for c in h.conditions if c not in POSITIVE_CONDS}
    for e in enemies:
        e.conditions = {c for c in e.conditions if c not in NEGATIVE_CONDS}


def spawn_from_card(room: RoomCard, threat: int, spawn_level: int) -> List[Enemy]:
    entries = room.spawns_by_threat.get(threat) or room.spawns_by_threat.get(3) or room.spawns_by_threat[min(room.spawns_by_threat)]
    enemies: List[Enemy] = []
    for name, elite in entries:
        lvl = min(6, spawn_level + (1 if elite else 0))
        a, hp_b, d = LEVEL_MODS[lvl]
        t = VILLAINS[name]
        enemies.append(Enemy(t, t.hp + hp_b, t.armor + a, t.damage + d, lvl))
    return enemies


def choose_target_enemy(enemies: List[Enemy]) -> Optional[Enemy]:
    alive = [e for e in enemies if e.alive]
    return min(alive, key=lambda e: (e.hp, -e.damage)) if alive else None


def choose_enemy_target(enemy: Enemy, heroes: List[HeroState]) -> Optional[HeroState]:
    alive = [h for h in heroes if h.alive]
    if not alive:
        return None
    if enemy.template.target_rule == "low_hp":
        return min(alive, key=lambda h: h.hp)
    if enemy.template.target_rule == "high_hp":
        return max(alive, key=lambda h: h.hp)
    if enemy.template.target_rule == "high_lp":
        return max(alive, key=lambda h: h.lp)
    if enemy.template.target_rule == "far":
        ranged = [h for h in alive if h.template.name == "Merlin"]
        return ranged[0] if ranged else alive[0]
    return min(alive, key=lambda h: h.hp)


def pick_attack(hero: HeroState, enemies: List[Enemy]) -> Attack:
    if hero.lp >= 6:
        return hero.template.attacks[3]
    if hero.lp >= hero.template.attacks[2].lp_cost and any(e.hp >= 10 for e in enemies if e.alive):
        return hero.template.attacks[2]
    b1, b2 = hero.template.attacks[0], hero.template.attacks[1]
    return b1 if (sum(b1.base_dice.values()) + 0.6 * b1.lp_gain) >= (sum(b2.base_dice.values()) + 0.6 * b2.lp_gain) else b2


def try_reroll(face: str, hero: HeroState, gate: Gate, room: RoomCard) -> str:
    if face != "blank":
        return face
    if gate.rule_tag == "no_reroll":
        return face
    free = room.rule_tag == "free_reroll" and not hero.reroll_free_this_round
    if free and random.random() < 0.8:
        hero.reroll_free_this_round = True
        return roll_die()
    if hero.lp > 0 and random.random() < 0.35:
        hero.lp -= 1
        return roll_die()
    return face


def resolve_hero_attack(hero: HeroState, enemies: List[Enemy], seals: List[str], boon_cp: Dict[str, float], gate: Gate, room: RoomCard, round_no: int):
    if not hero.alive:
        return
    if "staggered" in hero.conditions:
        hero.conditions.remove("staggered")
        return

    atk = pick_attack(hero, enemies)
    if hero.lp < atk.lp_cost:
        atk = hero.template.attacks[0]

    # defense conditions grant temporary armor for this turn-cycle
    if "toughened" in hero.conditions:
        hero.armor += 1
    if "armored" in hero.conditions:
        hero.armor += 3

    lp_spent = max(3, hero.lp) if atk.full_spender else atk.lp_cost
    hero.lp = clamp(hero.lp - lp_spent, 0, 12)
    if gate.rule_tag == "lp_costs_hp" and lp_spent > 0:
        hero.hp -= max(0, lp_spent - (1 if hero.first_attack_this_round else 0))

    if gate.rule_tag == "pay_special_or_fail" and random.random() < 0.3:
        return

    pool: List[Tuple[str, Optional[str]]] = []
    for c, n in atk.base_dice.items():
        if atk.full_spender and c == "red" and hero.template.name == "Hercules":
            n += max(0, lp_spent - 3)
        if atk.full_spender and c == "green" and hero.template.name == "Anansi":
            n = lp_spent
        if gate.rule_tag == "minus_hero_die":
            n = max(1, n - 1)
        for _ in range(n):
            pool.append((c, None))
    pool.append((hero.template.relic_die_color, None))

    for b in hero.boons:
        for c, n in b.dice_bonus.items():
            for _ in range(n):
                pool.append((c, b.name))

    # seal channeling
    if len(seals) >= 2:
        c = Counter(seals).most_common(1)[0][0]
        if seals.count(c) >= 2 and random.random() < 0.2:
            seals.remove(c)
            seals.remove(c)
            pool.append((c, "sealed_channel"))

    rolled: List[Tuple[str, str, Optional[str]]] = []
    for c, src in pool:
        face = try_reroll(roll_die(), hero, gate, room)
        rolled.append((c, face, src))

    specials_by_color = Counter()
    specials_by_color_source = defaultdict(list)
    dmg_by_color = defaultdict(int)
    for c, face, src in rolled:
        if face == "dmg":
            dmg_by_color[c] += 1
            if src and src not in ("sealed_channel",):
                boon_cp[src] += CP_DAMAGE
        elif face == "special":
            specials_by_color[c] += 1
            specials_by_color_source[c].append(src)

    # bank 1 seal (or Merlin rune slot)
    if sum(specials_by_color.values()) > 0 and len(seals) < 6 and random.random() < 0.45:
        k = specials_by_color.most_common(1)[0][0]
        specials_by_color[k] -= 1
        if specials_by_color_source[k]:
            specials_by_color_source[k].pop()
        if specials_by_color[k] <= 0:
            del specials_by_color[k]
        if hero.template.name == "Merlin" and len(hero.rune_slots) < 3 and random.random() < 0.5:
            hero.rune_slots.append(k)
            if len(hero.rune_slots) == 3 and random.random() < 0.5:
                alive_heroes = [h for h in HERO_STATES if h.alive]
                for ally in random.sample(alive_heroes, k=min(4, len(alive_heroes))):
                    ally.lp = clamp(ally.lp + 1, 0, 12)
                seals.extend(hero.rune_slots)
                hero.rune_slots.clear()
        else:
            seals.append(k)

    for c, req in atk.special_rules.items():
        if specials_by_color.get(c, 0) >= req:
            for _ in range(req):
                if specials_by_color_source[c]:
                    specials_by_color_source[c].pop()
            specials_by_color[c] -= req
            dmg_by_color[c] += 2

    for b in hero.boons:
        for c, extra in b.on_color_special_bonus_damage.items():
            if specials_by_color.get(c, 0) >= 1:
                specials_by_color[c] -= 1
                src = specials_by_color_source[c].pop() if specials_by_color_source[c] else None
                dmg_by_color[c] += extra
                boon_cp[b.name] += extra * CP_DAMAGE
                if src and src not in ("sealed_channel",):
                    boon_cp[src] += extra * CP_DAMAGE * 0.1
        for c, lp in b.on_color_special_bonus_lp.items():
            if specials_by_color.get(c, 0) >= 1:
                specials_by_color[c] -= 1
                if specials_by_color_source[c]:
                    specials_by_color_source[c].pop()
                hero.lp = clamp(hero.lp + lp, 0, 12)
                boon_cp[b.name] += lp * CP_LP
        if b.on_attack_flat_bonus:
            dmg_by_color["grey"] += b.on_attack_flat_bonus
            boon_cp[b.name] += b.on_attack_flat_bonus * CP_DAMAGE

    for c, n in list(specials_by_color.items()):
        for _ in range(n):
            src = specials_by_color_source[c].pop() if specials_by_color_source[c] else None
            if hero.lp <= 4:
                hero.lp = clamp(hero.lp + 2, 0, 12)
            else:
                dmg_by_color[c] += 2
                if src and src not in ("sealed_channel",):
                    boon_cp[src] += 2 * CP_DAMAGE

    flat_mod = 0
    if "empowered" in hero.conditions:
        flat_mod += 1
    if "exalted" in hero.conditions:
        flat_mod += 3
    if "weakened" in hero.conditions:
        flat_mod -= 1
    if "enfeebled" in hero.conditions:
        flat_mod -= 3
    if room.rule_tag == "flank_bonus" and random.random() < 0.35:
        flat_mod += 1
    if room.rule_tag == "follow_up_die" and not hero.first_attack_this_round and random.random() < 0.5:
        dmg_by_color["grey"] += 1 if roll_die() == "dmg" else 0
    if gate.rule_tag == "enemy_armor_round1" and round_no == 1:
        flat_mod -= 1

    hero.lp = clamp(hero.lp + atk.lp_gain, 0, 12)
    target = choose_target_enemy(enemies)
    if not target:
        return

    # apply vulnerability / resistance by damage color
    total = 0
    for c, amt in dmg_by_color.items():
        adjusted = amt
        if target.template.vulnerability == c:
            adjusted *= 2
        total += adjusted

    total += flat_mod
    total = max(0, total)

    enemy_armor = target.armor
    if gate.rule_tag == "guardian_foes" and len([e for e in enemies if e.alive]) > 1:
        enemy_armor += 1

    dealt = max(0, total - enemy_armor)
    if "exposed" in target.conditions:
        dealt += 1
    if "breached" in target.conditions:
        dealt += 3

    target.hp -= dealt
    hero.damage_done_this_room += dealt

    if target.hp <= 0:
        for b in hero.boons:
            if b.on_kill_lp:
                hero.lp = clamp(hero.lp + b.on_kill_lp, 0, 12)
                boon_cp[b.name] += b.on_kill_lp * CP_LP
        if gate.rule_tag == "lose_lp_on_kill":
            hero.lp = max(0, hero.lp - 1)
        if gate.rule_tag == "shatterburst":
            hero.hp -= 1
        if gate.rule_tag == "vengeance":
            for e in enemies:
                if e.alive:
                    apply_condition(e, "empowered")

    hero.first_attack_this_round = False


def resolve_enemy_attack(enemy: Enemy, heroes: List[HeroState], taint: List[int], round_no: int):
    target = choose_enemy_target(enemy, heroes)
    if not target:
        return
    dmg = enemy.damage
    if "weakened" in enemy.conditions:
        dmg = max(0, dmg - 1)
    if "enfeebled" in enemy.conditions:
        dmg = max(0, dmg - 3)
    if "empowered" in enemy.conditions:
        dmg += 1
    if "exalted" in enemy.conditions:
        dmg += 3

    if "exposed" in target.conditions:
        dmg += 1
    if "breached" in target.conditions:
        dmg += 3

    if "ignore_armor" not in enemy.template.effects:
        prevented = min(target.armor, dmg)
        dmg -= prevented
        if prevented > 0:
            target.armor = max(0, target.armor - 1)

    target.hp -= dmg
    if "drain_lp" in enemy.template.effects:
        target.lp = max(0, target.lp - 1)
    if "staggered" in enemy.template.effects:
        apply_condition(target, "staggered")
    if "self_toughened" in enemy.template.effects:
        enemy.armor += 1
    if "splash" in enemy.template.effects:
        for other in random.sample([h for h in heroes if h.alive and h is not target], k=min(1, len([h for h in heroes if h.alive and h is not target]))):
            other.hp -= 1
    if "terror" in enemy.template.effects and random.random() < 0.4:
        for h in heroes:
            if h.alive:
                h.lp = max(0, h.lp - 1)

    if target.hp <= 0 and target.alive:
        target.alive = False
        taint[0] += 1


def attempt_fragment_claim(hero: HeroState, fragments_left: List[str], seals: List[str], taint: List[int], decks: Dict[str, List[Boon]]):
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

    draw_n = 3
    if hero.lp >= 1 and random.random() < 0.25:
        pay = min(3, hero.lp)
        hero.lp -= pay
        draw_n += pay

    picks = random.sample(decks[color], k=min(draw_n, len(decks[color])))
    pick = max(picks, key=lambda b: sum(b.dice_bonus.values()) * 3 + b.on_attack_flat_bonus + 0.4 * sum(b.on_color_special_bonus_damage.values()) + 0.35 * sum(b.on_color_special_bonus_lp.values()) + b.on_kill_lp * 0.3)
    hero.boons.append(pick)


def choose_gate(taint: int, std_deck: List[Gate], nexus_deck: List[Gate]) -> Gate:
    std1 = draw_one(std_deck, STANDARD_GATES)
    std2 = draw_one(std_deck, STANDARD_GATES)
    nx = draw_one(nexus_deck, NEXUS_GATES)
    options = [x for x in [std1, std2, nx] if x is not None]
    best = options[0]
    best_score = -1e9
    for g in options:
        score = 1.4 * len(g.fragments) - 1.1 * g.threat
        if g.gate_type == "nexus":
            score += 0.5 if taint > 11 else -0.5
        if g.gate_type == "temple" and taint > 10:
            score += 1.0
        if score > best_score:
            best_score = score
            best = g
    return best


def apply_room_start(heroes: List[HeroState], gate: Gate, room: RoomCard, taint: List[int]):
    for h in heroes:
        if not h.alive:
            continue
        h.lp = clamp(h.lp + gate.start_lp, 0, 12)
        if gate.start_heal:
            h.hp = min(h.template.max_hp, h.hp + gate.start_heal)
            if gate.rule_tag == "heal_slows":
                apply_condition(h, "slowed")
        if room.rule_tag == "temple_exchange" and random.random() < 0.25:
            taint[0] = max(0, taint[0] - 1)


def run_single(max_rounds_safety: int = 16) -> Dict:
    global HERO_STATES
    heroes = [HeroState(h, h.max_hp) for h in HEROES]
    HERO_STATES = heroes
    decks = boon_catalog()
    std_gate_deck = init_deck(STANDARD_GATES)
    nexus_gate_deck = init_deck(NEXUS_GATES)
    basic_room_deck = init_deck(basic_rooms())
    temple_room_deck = init_deck(temple_rooms())
    nexus_room_deck = init_deck(nexus_rooms())

    seals: List[str] = []
    taint = [0]
    spawn_level = 1
    room_hp, room_damage, room_taint = [], [], []
    boon_cp = defaultdict(float)

    for room_idx in range(1, MAX_ROOMS + 1):
        for h in heroes:
            if h.alive:
                h.lp = 0
                h.armor = 0
                h.first_attack_this_round = True
            h.damage_done_this_room = 0.0

        gate = choose_gate(taint[0], std_gate_deck, nexus_gate_deck)

        if any(f in seals for f in gate.fragments):
            for f in gate.fragments:
                if f in seals:
                    seals.remove(f)
                    taint[0] = max(0, taint[0] - 1)
                    break

        if gate.gate_type == "temple":
            room = draw_one(temple_room_deck, temple_rooms())
        elif gate.gate_type == "nexus":
            room = draw_one(nexus_room_deck, nexus_rooms())
        else:
            room = draw_one(basic_room_deck, basic_rooms())

        apply_room_start(heroes, gate, room, taint)

        enemies = spawn_from_card(room, gate.threat, spawn_level)
        fragments = gate.fragments.copy()
        collapse_pending = False
        round_no = 0

        while any(e.alive for e in enemies) and any(h.alive for h in heroes) and round_no < max_rounds_safety:
            round_no += 1
            for h in heroes:
                h.reroll_free_this_round = False
                h.first_attack_this_round = True
                if room.rule_tag == "empower_if_surrounded" and random.random() < 0.35:
                    apply_condition(h, "empowered")

            initiative = [h.template.name for h in heroes if h.alive] + [f"E{i}" for i, e in enumerate(enemies) if e.alive]
            random.shuffle(initiative)
            if gate.rule_tag == "enemy_first":
                initiative.sort(key=lambda t: 0 if t.startswith("E") else 1)

            for token in initiative:
                if token.startswith("E"):
                    enemy = enemies[int(token[1:])]
                    if enemy.alive:
                        resolve_enemy_attack(enemy, heroes, taint, round_no)
                else:
                    hero = next(h for h in heroes if h.template.name == token)
                    if not hero.alive:
                        continue
                    hero.armor = 0
                    if "slowed" in hero.conditions and random.random() < 0.25:
                        hero.conditions.remove("slowed")
                    resolve_hero_attack(hero, enemies, seals, boon_cp, gate, room, round_no)
                    attempt_fragment_claim(hero, fragments, seals, taint, decks)
                    if "bleeding" in hero.conditions:
                        hero.hp -= 1
                    if "hemorrhaging" in hero.conditions:
                        hero.hp -= 3
                    if hero.hp <= 0 and hero.alive:
                        hero.alive = False
                        taint[0] += 1

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

        if not any(e.alive for e in enemies):
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


def aggregate(results: List[Dict]) -> Dict:
    names = [h.name for h in HEROES]
    avg_hp, avg_dmg, avg_taint = [], [], []
    for i in range(MAX_ROOMS):
        avg_hp.append({n: statistics.fmean(r["room_hp"][i][n] for r in results) for n in names})
        avg_dmg.append({n: statistics.fmean(r["room_damage"][i][n] for r in results) for n in names})
        avg_taint.append(statistics.fmean(r["room_taint"][i] for r in results))

    boon_totals = defaultdict(float)
    for r in results:
        for k, v in r["boon_cp"].items():
            boon_totals[k] += v
    boon_avg = {k: v / len(results) for k, v in sorted(boon_totals.items(), key=lambda kv: kv[1], reverse=True)}

    return {
        "avg_hp": avg_hp,
        "avg_dmg": avg_dmg,
        "avg_taint": avg_taint,
        "boon_cp_avg": boon_avg,
        "survival_rate": statistics.fmean(r["survived_7"] for r in results),
    }


def run_simulations(n: int = DEFAULT_SIMS, seed: int = 42, max_rounds_safety: int = 16) -> Dict:
    random.seed(seed)
    results = [run_single(max_rounds_safety=max_rounds_safety) for _ in range(n)]
    return aggregate(results)


def print_report(agg: Dict, sims: int):
    print(f"Spellrift balance simulation report ({sims} runs)")
    print("=" * 72)
    for i in range(MAX_ROOMS):
        print(f"\nRoom {i+1}")
        print(f"  Avg Taint: {agg['avg_taint'][i]:.2f}")
        print("  Avg Hero HP at room end:")
        for hn, v in agg["avg_hp"][i].items():
            print(f"    - {hn:12s}: {v:6.2f}")
        print("  Avg damage dealt by hero in this room:")
        for hn, v in agg["avg_dmg"][i].items():
            print(f"    - {hn:12s}: {v:6.2f}")

    print(f"\nEstimated run survival to room 7: {agg['survival_rate']*100:.2f}%")
    print("\nTop 40 Boon cards by average CP contribution per run")
    print("-" * 72)
    for i, (name, cp) in enumerate(list(agg["boon_cp_avg"].items())[:40], start=1):
        print(f"{i:2d}. {name:32s} {cp:8.3f} CP/run")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Spellrift Dungeons alpha balance simulator")
    parser.add_argument("--sims", type=int, default=DEFAULT_SIMS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-rounds-safety", type=int, default=16)
    args = parser.parse_args()

    aggregated = run_simulations(args.sims, args.seed, args.max_rounds_safety)
    print_report(aggregated, args.sims)
