#!/usr/bin/env python3
"""Minimal board game simulator showing fate, armor, vulnerability and
persistent effects.
This version rewrites the broken previous script with a compact
implementation that still demonstrates the same mechanics."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple, Set

RNG = random.Random()

# Damage bands per wave for monster attacks
BANDS = [
    [1, 0, 1, 0],
    [1, 1, 1, 2],
    [0, 2, 0, 0],
    [6, 1, 1, 1],
    [1, 0, 6, 1],
    [5, 0, 2, 3],
    [3, 1, 2, 0],
    [2, 0, 1, 0],
]

def d8() -> int:
    return RNG.randint(1, 8)

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class CardType(Enum):
    MELEE = auto()
    RANGED = auto()
    UTIL = auto()

class Element(Enum):
    BRUTAL = "B"
    PRECISE = "P"
    DIVINE = "D"
    ARCANE = "A"
    SPIRITUAL = "S"
    NONE = "-"

# ---------------------------------------------------------------------------
# Card and deck helpers
# ---------------------------------------------------------------------------
@dataclass
class Card:
    name: str
    ctype: CardType
    dice: int = 0
    element: Element = Element.NONE
    armor: int = 0
    effect: Optional[Callable[["Hero", Dict], None]] = None
    persistent: Optional[str] = None  # "combat" or "exchange"
    hymn: bool = False
    multi: bool = False

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)

    MAX_HAND: int = 7

    def start_combat(self) -> None:
        """Initial draw at the start of combat (3 or 4 cards randomly)."""
        self.draw(4 if RNG.random() < 0.5 else 3)

    def shuffle(self) -> None:
        RNG.shuffle(self.cards)

    def draw(self, n: int) -> None:
        for _ in range(n):
            if len(self.hand) >= self.MAX_HAND:
                break
            if not self.cards:
                RNG.shuffle(self.disc)
                self.cards, self.disc = self.disc, []
                if not self.cards:
                    break
            self.hand.append(self.cards.pop())

    def pop_first(self, ctype: CardType) -> Optional[Card]:
        for i, c in enumerate(self.hand):
            if c.ctype == ctype:
                return self.hand.pop(i)
        return None

# ---------------------------------------------------------------------------
# Hero and Enemy definitions
# ---------------------------------------------------------------------------
FATE_MAX = 10

@dataclass
class Hero:
    name: str
    max_hp: int
    base_cards: List[Card]
    upg_pool: List[Card] = field(default_factory=list)

    # dynamic state
    fate: int = 0
    armor_pool: int = 0
    deck: Deck = field(init=False)
    combat_effects: List[Tuple[Callable[["Hero", Dict], None], Card]] = field(default_factory=list)
    exchange_effects: List[Tuple[Callable[["Hero", Dict], None], Card]] = field(default_factory=list)
    active_hymns: List[Card] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.hp = self.max_hp
        self.fate = 0
        self.armor_pool = 0
        self.deck = Deck(self.base_cards[:])
        self.deck.shuffle()
        self.combat_effects.clear()
        self.exchange_effects.clear()
        self.active_hymns.clear()

    def gain_fate(self, n: int = 1) -> None:
        self.fate = min(FATE_MAX, self.fate + n)

    def gain_upgrades(self, n: int = 1) -> None:
        if not self.upg_pool:
            return
        choices = RNG.sample(self.upg_pool, min(n, len(self.upg_pool)))
        self.deck.cards.extend(choices)

    def spend_fate(self, n: int = 1) -> bool:
        if self.fate >= n:
            self.fate -= n
            return True
        return False

@dataclass
class Enemy:
    """Enemy template/instance used during combat."""

    name: str
    hp: int
    defense: int
    vulnerability: Element
    damage_band: List[int]
    ability: Optional[Callable[[Dict[str, object]], None] | str] = None
    armor_pool: int = 0
    barrier_elems: Set[Element] = field(default_factory=set)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def roll_die(defense: int, mod: int = 0, *, hero: Optional[Hero] = None,
             allow_reroll: bool = True) -> int:
    """Roll a single d8 with optional fate based rerolls."""
    r = max(1, min(8, d8() + mod))
    if not allow_reroll or hero is None:
        return r
    thresh = 5 if hero.name == "Brynhild" else 3
    while r < defense and hero.fate > thresh and hero.spend_fate(1):
        r = max(1, min(8, d8() + mod))
    return r


def roll_hits(num_dice: int, defense: int, mod: int = 0, *,
              hero: Optional[Hero] = None,
              element: Element = Element.NONE,
              vulnerability: Element = Element.NONE,
              allow_reroll: bool = True,
              enemy: Optional[Enemy] = None) -> int:
    dmg = 0
    for _ in range(num_dice):
        r = roll_die(defense, mod, hero=hero, allow_reroll=allow_reroll)
        if enemy and enemy.ability == "curse_of_torment" and hero:
            curse_of_torment(hero, r)
        if r >= defense:
            hit = 2 if r == 8 else 1
            if element != Element.NONE and element == vulnerability:
                hit *= 2
            dmg += hit
    return dmg

# persistent effect application

def apply_persistent(hero: Hero, ctx: Dict[str, object]) -> None:
    if ctx.get("silenced"):
        return
    for fx, _ in hero.combat_effects:
        fx(hero, ctx)
    for fx, _ in hero.exchange_effects:
        fx(hero, ctx)

# ---------------------------------------------------------------------------
# Enemy ability helpers
# ---------------------------------------------------------------------------
def dark_phalanx(enemies: List[Enemy], dmg: int) -> int:
    """Reduce damage from multi-target attacks while multiple Soldiers live."""
    if sum(1 for e in enemies if e.ability == "dark-phalanx") >= 2:
        return max(1, dmg - 1)
    return dmg


def spiked_armor(hero: Hero, dmg: int) -> None:
    """Punish heavy hits against the soldier."""
    if dmg >= 3:
        hero.hp -= 1

# map ability names to helper functions
ABILITY_FUNCS = {
    "dark-phalanx": dark_phalanx,
    "spiked-armor": spiked_armor,
}

# simple card effects ---------------------------------------------------------

def gain_armor(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += n
    return _fx

def draw_cards(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.deck.draw(n)
    return _fx

def discard_random(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        for _ in range(n):
            if h.deck.hand:
                i = RNG.randrange(len(h.deck.hand))
                h.deck.disc.append(h.deck.hand.pop(i))
    return _fx

def gain_fate_fx(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.gain_fate(n)
    return _fx

def temp_vuln(elem: Element) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['temp_vuln'] = elem
    return _fx

def area_damage(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['area_damage'] = ctx.get('area_damage', 0) + n
    return _fx

def cleave_all(hero_list: List[Hero], dmg: int) -> None:
    """Apply ``dmg`` to every hero in ``hero_list`` ignoring order."""
    for h in hero_list:
        soak = min(h.armor_pool, dmg)
        h.armor_pool -= soak
        h.hp -= max(0, dmg - soak)

def enrage(enemy: Enemy) -> bool:
    """Return True if ``enemy`` is enraged and attacks twice."""
    return enemy.hp <= 3

def end_hymns_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    hero.active_hymns.clear()
    hero.combat_effects = [p for p in hero.combat_effects if not p[1].hymn]
    hero.exchange_effects = [p for p in hero.exchange_effects if not p[1].hymn]

# ---------------------------------------------------------------------------
# Enemy ability helpers
# ---------------------------------------------------------------------------
def curse_of_torment(hero: Hero, roll: int) -> None:
    """Inflict 1 damage when ``roll`` is 1 or 2."""
    if roll in (1, 2):
        hero.hp -= 1


def void_barrier(enemy: Enemy, element: Element) -> None:
    """Grant armor when hit by a new damage element."""
    if element != Element.NONE and element not in enemy.barrier_elems:
        enemy.barrier_elems.add(element)
        enemy.armor_pool += 1

def power_of_death(ctx: Dict[str, object]) -> None:
    """Set priest damage bonus based on fallen priests."""
    ctx["priest_bonus"] = ctx.get("dead_priests", 0)


def silence(ctx: Dict[str, object]) -> None:
    """Prevent all card effects for the rest of combat."""
    ctx["silenced"] = True

# ---------------------------------------------------------------------------
# Card helpers to create attack cards
# ---------------------------------------------------------------------------
def atk(name: str, ctype: CardType, dice: int, element: Element = Element.NONE,
        armor: int = 0, effect: Optional[Callable[[Hero, Dict], None]] = None,
        persistent: Optional[str] = None, hymn: bool = False,
        multi: bool = False) -> Card:
    return Card(name, ctype, dice, element, armor, effect, persistent, hymn, multi)

def weighted_pool(common: List[Card], uncommon: List[Card], rare: List[Card]) -> List[Card]:
    pool: List[Card] = []
    for c in common:
        pool.extend([c] * 3)
    for c in uncommon:
        pool.extend([c] * 2)
    pool.extend(rare)
    return pool

# sample hero decks -----------------------------------------------------------
herc_base = [
    atk("Pillar", CardType.MELEE, 2, Element.BRUTAL),
    atk("Heroism", CardType.MELEE, 1, Element.DIVINE, armor=1, effect=gain_armor(1)),
    atk("Javelin", CardType.RANGED, 2, Element.DIVINE),
]
# placeholder upgrade cards
herc_common_upg = [atk("Slam", CardType.MELEE, 2)]
herc_uncommon_upg = [atk("Dragon Spear", CardType.MELEE, 3, Element.DIVINE)]
herc_rare_upg = [atk("Labour", CardType.MELEE, 4, Element.BRUTAL, effect=gain_fate_fx(1))]
herc_pool = weighted_pool(herc_common_upg, herc_uncommon_upg, herc_rare_upg)
hercules = Hero("Hercules", 25, herc_base, herc_pool)

bryn_base = [
    atk("Descent", CardType.MELEE, 1, Element.SPIRITUAL),
    atk("Shields", CardType.UTIL, 0, hymn=True, persistent="combat"),
    atk("Storms", CardType.UTIL, 0, effect=end_hymns_fx),
]
_b_c = [atk("Song", CardType.MELEE, 1, Element.SPIRITUAL, effect=gain_fate_fx(1))]
_b_u = [atk("Choir", CardType.UTIL, 0, hymn=True, persistent="exchange", effect=draw_cards(1))]
_b_r = [atk("Valhalla", CardType.MELEE, 3, Element.DIVINE, effect=temp_vuln(Element.DIVINE))]
b_pool = weighted_pool(_b_c, _b_u, _b_r)
brynhild = Hero("Brynhild", 18, bryn_base, b_pool)

HEROES = [hercules, brynhild]

# ---------------------------------------------------------------------------
# Enemy abilities and catalog
# ---------------------------------------------------------------------------

def web_slinger(ctx: Dict[str, object]) -> None:
    """Ranged attacks become melee while any Spinners remain."""
    ctx["ranged_to_melee"] = True


def sticky_web(ctx: Dict[str, object]) -> None:
    """Reduce cards drawn each exchange by one."""
    ctx["draw_penalty"] = ctx.get("draw_penalty", 0) + 1


ENEMIES: Dict[str, Enemy] = {
    "Shadow Spinner (basic)": Enemy("Shadow Spinner (basic)", 1, 4, Element.SPIRITUAL, [0, 0, 1, 3], web_slinger),
    "Shadow Spinner (elite)": Enemy("Shadow Spinner (elite)", 2, 5, Element.SPIRITUAL, [0, 0, 1, 3], sticky_web),
    # legacy entries used by the existing waves
    "Spinner": Enemy("Spinner", 1, 4, Element.SPIRITUAL, [1, 0, 1, 0], "web-slinger"),
    "Soldier": Enemy("Soldier", 2, 5, Element.PRECISE, [0, 0, 0, 2], "dark-phalanx"),
    "Banshee": Enemy("Banshee", 4, 5, Element.DIVINE, [0, 0, 1, 3], "banshee-wail"),
    "Priest": Enemy("Priest", 2, 3, Element.ARCANE, [0, 0, 1, 1], power_of_death),
    "Dryad": Enemy("Dryad", 2, 4, Element.BRUTAL, [0, 0, 1, 1], "cursed-thorns"),
    "Minotaur": Enemy("Minotaur", 4, 3, Element.PRECISE, [0, 0, 1, 3], "cleave_all"),
    "Wizard": Enemy("Wizard", 2, 3, Element.BRUTAL, [0, 1, 1, 3], "curse-of-torment"),
    "Shadow Banshee": Enemy("Shadow Banshee", 3, 5, Element.DIVINE, [0, 0, 1, 2], "ghostly"),
    "Gryphon": Enemy("Gryphon", 4, 5, Element.SPIRITUAL, [0, 1, 3, 4], "aerial-combat"),
    "Treant": Enemy("Treant", 7, 6, Element.DIVINE, [0, 1, 1, 4], "power-sap"),
    "Angel": Enemy("Angel", 5, 5, Element.ARCANE, [0, 1, 2, 5], "corrupted-destiny"),
    "Elite Spinner": Enemy("Elite Spinner", 2, 5, Element.SPIRITUAL, [0, 0, 1, 4], "sticky-web"),
    "Elite Soldier": Enemy("Elite Soldier", 3, 6, Element.PRECISE, [0, 0, 1, 3], "spiked-armor"),
    "Elite Priest": Enemy("Elite Priest", 3, 4, Element.ARCANE, [0, 0, 1, 2], silence),
    "Elite Dryad": Enemy("Elite Dryad", 2, 5, Element.BRUTAL, [0, 1, 1, 2], "disturbed-flow"),
    "Elite Minotaur": Enemy("Elite Minotaur", 5, 3, Element.PRECISE, [0, 0, 2, 4], "enrage"),
    "Elite Wizard": Enemy("Elite Wizard", 2, 4, Element.BRUTAL, [0, 2, 2, 3], "void-barrier"),
    "Elite Banshee": Enemy("Elite Banshee", 4, 5, Element.DIVINE, [0, 0, 1, 3], "banshee-wail"),
    "Elite Gryphon": Enemy("Elite Gryphon", 5, 5, Element.SPIRITUAL, [0, 2, 4, 6], "ephemeral-wings"),
    "Elite Treant": Enemy("Elite Treant", 8, 7, Element.DIVINE, [0, 1, 3, 5], "roots-of-despair"),
    "Elite Angel": Enemy("Elite Angel", 7, 6, Element.ARCANE, [0, 3, 3, 6], "denied-heaven"),
}

def make_wave(name: str, count: int) -> Dict[str, object]:
    tmpl = ENEMIES[name]
    return {
        "enemy_type": tmpl,
        "enemies": [
            Enemy(
                tmpl.name,
                tmpl.hp,
                tmpl.defense,
                tmpl.vulnerability,
                tmpl.damage_band[:],
                tmpl.ability,
            )
            for _ in range(count)
        ],
    }


def cursed_thorns(hero: Hero) -> None:
    """Convert remaining armor into HP loss."""
    if hero.armor_pool > 0:
        hero.hp -= hero.armor_pool
        hero.armor_pool = 0


def disturbed_flow(ctx: Dict[str, object]) -> None:
    """Disable fate-based rerolls for the current combat."""
    ctx["no_reroll"] = True

# basic and elite monster roster
ENEMY_WAVES = [
    ("Spinner", 3),
    ("Soldier", 3),
    ("Banshee", 2),
    ("Priest", 3),
    ("Dryad", 3),
    ("Minotaur", 2),
    ("Wizard", 2),
    ("Shadow Banshee", 2),
    ("Void Gryphon", 1),
    ("Treant", 1),
    ("Angel", 1),
    ("Elite Spinner", 3),
    ("Elite Soldier", 3),
    ("Elite Priest", 3),
    ("Elite Dryad", 3),
    ("Elite Minotaur", 2),
    ("Elite Wizard", 2),
    ("Elite Banshee", 2),
    ("Elite Void Gryphon", 1),
    ("Elite Treant", 1),
    ("Elite Angel", 1),
]


# ---------------------------------------------------------------------------
# Combat helpers
# ---------------------------------------------------------------------------
def resolve_attack(hero: Hero, card: Card, ctx: Dict[str, object]) -> None:
    """Resolve ``card`` against current enemies in ``ctx``."""

    enemies: List[Enemy] = ctx["enemies"]
    if not enemies:
        return

    block_void = ctx.pop("ephemeral_block", False)
    targets = enemies[:] if card.multi else [enemies[0]]
    allow_reroll = not ctx.get("no_reroll", False)
    for e in targets[:]:
        mod = -1 if (card.ctype == CardType.MELEE and e.ability == "aerial-combat") else 0
        vuln = ctx.pop("temp_vuln", e.vulnerability)
        dmg = roll_hits(card.dice, e.defense, mod, hero=hero, element=card.element,
                        vulnerability=vuln)
        if block_void and e.ability == "ephemeral-wings":
            dmg = 0
            block_void = False
        if card.multi and e.ability == "dark-phalanx":
            dmg = dark_phalanx(enemies, dmg)
        area = ctx.pop("area_damage", 0)
        dmg += area
        soak = min(e.armor_pool, dmg)
        e.armor_pool -= soak
        dmg -= soak
        e.hp -= dmg
        if e.ability == "spiked-armor":
            spiked_armor(hero, dmg)
        if e.ability == "ephemeral-wings" and not block_void:
            ctx["ephemeral_block"] = True

        if e.hp <= 0:
            enemies.remove(e)
            if e.ability == "power-of-death" or e.ability is power_of_death:
                ctx["dead_priests"] = ctx.get("dead_priests", 0) + 1
                ctx["priest_bonus"] = ctx["dead_priests"]
    if card.effect and not ctx.get("silenced"):
        card.effect(hero, ctx)
        if card.persistent:
            if card.persistent == "combat":
                hero.combat_effects.append((card.effect, card))
            elif card.persistent == "exchange":
                hero.exchange_effects.append((card.effect, card))
    if card.hymn:
        hero.active_hymns.append(card)
    hero.deck.disc.append(card)


def monster_attack(heroes: List[Hero], ctx: Dict[str, object]) -> None:
    """Resolve monster attacks for the current wave."""

    def apply(hero: Hero, dmg: int) -> None:
        soak = min(hero.armor_pool, dmg)
        hero.armor_pool -= soak
        hero.hp -= max(0, dmg - soak)

    bonus = ctx.get("priest_bonus", 0)
    for e in ctx["enemies"]:
        attacks = 2 if e.ability == "enrage" and enrage(e) else 1
        for _ in range(attacks):
            band = e.damage_band
            dmg = band[(d8() - 1) // 2]
            if e.ability == "cleave_all":
                cleave_all(heroes, dmg)
            else:
                apply(heroes[0], dmg)

    if bonus:
        apply(heroes[0], bonus)

# very small fight simulation -------------------------------------------------

def fight_one(hero: Hero) -> bool:
    """Run one full gauntlet for ``hero``."""

    hero.reset()
    hero.deck.start_combat()

    for name, count in ENEMY_WAVES:
        ctx = make_wave(name, count)
        for exch in range(3):
            ctx["exchange"] = exch
            if any((e.ability == "silence" or e.ability is silence) for e in ctx["enemies"]):
                if not ctx.get("silenced"):
                    ctx["silenced"] = True
                    hero.combat_effects.clear()
                    hero.exchange_effects.clear()
                    hero.active_hymns.clear()
            apply_persistent(hero, ctx)

            ctx["ranged_to_melee"] = False
            ctx["draw_penalty"] = 0
            for e in ctx["enemies"]:
                if callable(e.ability):
                    e.ability(ctx)

            # utilities first
            c = hero.deck.pop_first(CardType.UTIL)
            if c:
                resolve_attack(hero, c, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            delayed: List[Card] = []
            while ctx["enemies"]:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c:
                    break
                if ctx.get("ranged_to_melee"):
                    delayed.append(c)
                    continue
                resolve_attack(hero, c, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            if ctx["enemies"]:
                monster_attack([hero], ctx)
                if hero.hp <= 0:
                    return False

            for card in delayed:
                if not ctx["enemies"]:
                    break
                resolve_attack(hero, card, ctx)

            while ctx["enemies"]:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                resolve_attack(hero, c, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            # end-of-exchange abilities
            if any(e.ability == "cursed-thorns" for e in ctx["enemies"]):
                cursed_thorns(hero)
            if any(e.ability == "ghostly" for e in ctx["enemies"]) and exch >= 2:
                ctx["enemies"].clear()
            if any(e.ability == "power-sap" for e in ctx["enemies"]) and hero.combat_effects:
                hero.combat_effects.pop(RNG.randrange(len(hero.combat_effects)))
                for e in ctx["enemies"]:
                    if e.ability == "power-sap":
                        e.hp += 1
                        break

            if not ctx["enemies"]:
                break

            draw_amt = max(0, 1 - ctx.get("draw_penalty", 0))
            if draw_amt:
                hero.deck.draw(draw_amt)

        if ctx["enemies"] or hero.hp <= 0:
            return False

        hero.gain_upgrades(1)
        hero.gain_fate(1)
        hero.deck.draw(2)
        hero.combat_effects.clear()
        hero.exchange_effects.clear()
        hero.active_hymns.clear()

    return hero.hp > 0

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    N = 20
    wins = sum(fight_one(random.choice(HEROES)) for _ in range(N))
    print("Win rate", wins / N)
