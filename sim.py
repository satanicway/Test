#!/usr/bin/env python3
"""Simplified board game simulator demonstrating card effects and monster
abilities. Not a full implementation of the board game rules but shows how
heroes, fate, vulnerability, and a few special effects interact.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Callable, Optional, Dict, Any

RNG = random.Random()

def d8() -> int:
    return RNG.randint(1, 8)

# Enumerations
  
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

# Data structures


@dataclass
class Card:
    name: str
    ctype: CardType
    dice: int = 0
    element: Element = Element.NONE
    armor: int = 0
    effect: Optional[Callable[["Hero", Dict], None]] = None
    persistent: Optional[str] = None  # "combat" or "exchange"


@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)

    def shuffle(self) -> None:
        RNG.shuffle(self.cards)

    def draw(self, n: int) -> None:
        for _ in range(n):
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

FATE_MAX = 10

def roll_hits(
    num_dice: int, defense: int, mod: int = 0,
    *, hero: Optional["Hero"] = None
) -> int:
    """Roll `num_dice` d8 and count hits against `defense`.

    If ``hero`` is supplied, allow rerolls by spending Fate when below the
    defense threshold. Heroes only spend Fate while above 3 points (or 5 for
    Brynhild).
    """
    dmg = 0
    for _ in range(num_dice):
        r = max(1, min(8, d8() + mod))
        while (
            hero is not None
            and r < defense
            and hero.fate > (5 if hero.name == "Brynhild" else 3)
            and hero.spend_fate(1)
        ):
            r = max(1, min(8, d8() + mod))
        if r >= defense:
            dmg += 2 if r == 8 else 1
    return dmg

@dataclass
class Hero:
    name: str
    max_hp: int
    base_cards: List[Card]
    upg_cards: List[Card]
    fate: int = 0

    def reset(self) -> None:
        self.hp = self.max_hp
        self.fate = 0
        self.deck = Deck(self.base_cards[:])
        self.deck.shuffle()
        self.combat_effects: List[Callable[["Hero", Dict], None]] = []
        self.exchange_effects: List[Callable[["Hero", Dict], None]] = []
        self.armor_pool = 0

    def gain_fate(self, n: int = 1) -> None:
        """Increase fate up to ``FATE_MAX``."""
        self.fate = min(FATE_MAX, self.fate + n)

    def spend_fate(self, n: int = 1) -> bool:
        """Spend ``n`` fate if available, returning True on success."""
        if self.fate >= n:
            self.fate -= n
            return True
        return False

# Utility

def gain_armor(amount: int) -> Callable[[Hero, Dict], None]:
    return lambda hero, ctx: setattr(hero, "armor_pool", hero.armor_pool + amount)

# [Combat] enemy loses 1 HP per attack you resolve

def lion_strangler_fx(hero: Hero, ctx: Dict) -> None:
    def tick(h: Hero, cx: Dict) -> None:
        if cx.get("current_target") is not None and cx["enemy_hp"]:
            cx["enemy_hp"][0] -= 1
    hero.combat_effects.append(tick)

# [Exchange] +1 damage to other attacks

def sky_javelin_fx(hero: Hero, ctx: Dict) -> None:
    def buff(h: Hero, cx: Dict) -> None:
        cx["dmg_bonus"] = cx.get("dmg_bonus", 0) + 1
    hero.exchange_effects.append(buff)

# Card constructor

def atk(name: str, ctype: CardType, dice: int, element: Element = Element.NONE,
        armor: int = 0, effect: Optional[Callable[[Hero, Dict], None]] = None,
        persistent: Optional[str] = None) -> Card:
    return Card(name, ctype, dice, element, armor, effect, persistent)

# Hero decks (incomplete)
herc_base = [
    atk("Pillar", CardType.MELEE, 2, Element.BRUTAL),
    atk("Pillar", CardType.MELEE, 2, Element.BRUTAL),
    atk("Strangler", CardType.MELEE, 1, Element.BRUTAL, effect=lion_strangler_fx,
        persistent="combat"),
    atk("Heroism", CardType.MELEE, 1, Element.DIVINE, armor=1, effect=gain_armor(1)),
    atk("Heroism", CardType.MELEE, 1, Element.DIVINE, armor=1, effect=gain_armor(1)),
    atk("Javelin", CardType.RANGED, 2, Element.DIVINE, effect=sky_javelin_fx,
        persistent="exchange"),
    atk("Spin", CardType.MELEE, 1, Element.PRECISE),
    atk("Spin", CardType.MELEE, 1, Element.PRECISE),
    atk("Atlas", CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
    atk("Atlas", CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
]
hercules = Hero("Hercules", 25, herc_base, [])

mer_base = [
    atk("Volley", CardType.RANGED, 1, Element.ARCANE),
    atk("Volley", CardType.RANGED, 1, Element.ARCANE),
    atk("Warden", CardType.MELEE, 1, Element.ARCANE, armor=2, effect=gain_armor(2)),
    atk("Warden", CardType.MELEE, 1, Element.ARCANE, armor=2, effect=gain_armor(2)),
    atk("Weaver", CardType.RANGED, 1, Element.DIVINE),
    atk("Weaver", CardType.RANGED, 1, Element.DIVINE),
    atk("Staff", CardType.MELEE, 1, Element.PRECISE),
    atk("Mists", CardType.RANGED, 1, Element.SPIRITUAL),
    atk("Mists", CardType.RANGED, 1, Element.SPIRITUAL),
    atk("Circle", CardType.RANGED, 1, Element.SPIRITUAL),
]
merlin = Hero("Merlin", 15, mer_base, [])

mus_base = [
    atk("Swallow", CardType.MELEE, 1, Element.PRECISE),
    atk("Swallow", CardType.MELEE, 1, Element.PRECISE),
    atk("Cross", CardType.MELEE, 2, Element.PRECISE),
    atk("Cross", CardType.MELEE, 2, Element.PRECISE),
    atk("Heaven", CardType.MELEE, 2, Element.BRUTAL),
    atk("Heaven", CardType.MELEE, 2, Element.BRUTAL),
    atk("Parry", CardType.MELEE, 1, Element.SPIRITUAL, armor=1, effect=gain_armor(1)),
    atk("Parry", CardType.MELEE, 1, Element.SPIRITUAL, armor=1, effect=gain_armor(1)),
    atk("Guard", CardType.UTIL, 0),
    atk("Focus", CardType.MELEE, 1, Element.ARCANE),
]
musashi = Hero("Musashi", 20, mus_base, [])

bryn_base = [
    atk("Descent", CardType.MELEE, 1, Element.SPIRITUAL),
    atk("Descent", CardType.MELEE, 1, Element.SPIRITUAL),
    atk("Piercer", CardType.RANGED, 1, Element.SPIRITUAL),
    atk("Shields", CardType.UTIL, 0),
    atk("Shields", CardType.UTIL, 0),
    atk("Storms", CardType.UTIL, 0),
    atk("Thrust", CardType.MELEE, 1, Element.PRECISE),
    atk("Thrust", CardType.MELEE, 1, Element.PRECISE),
    atk("Spear", CardType.MELEE, 1, Element.BRUTAL),
    atk("Spear", CardType.MELEE, 1, Element.BRUTAL),
]
brynhild = Hero("Brynhild", 18, bryn_base, [])

HEROES = [hercules, merlin, musashi, brynhild]

@dataclass
class EnemyType:
    name: str
    hp: int
    defense: int
    bands: List[int]
    vulnerability: Element

def make_wave(enemy: EnemyType, count: int) -> Dict:
    return {"enemy_hp": [enemy.hp for _ in range(count)], "enemy_type": enemy}

BASIC_WAVES = [
    (EnemyType("Spinner", 1, 4, [1,0,1,0], Element.SPIRITUAL), 3),
    (EnemyType("Soldier", 2, 5, [1,1,1,2], Element.PRECISE), 3),
]

def apply_persistent(hero: Hero, ctx: Dict) -> None:
    for fx in hero.combat_effects:
        fx(hero, ctx)
    for fx in hero.exchange_effects:
        fx(hero, ctx)

def resolve_attack(hero: Hero, card: Card, ctx: Dict) -> None:
    dmg_bonus = ctx.get("dmg_bonus", 0)
    defense = ctx["enemy_type"].defense
    dmg = roll_hits(card.dice, defense, hero=hero) + dmg_bonus
    if ctx["enemy_type"].vulnerability == card.element:
        dmg *= 2
    if ctx["enemy_hp"]:
        ctx["enemy_hp"][0] -= dmg
        if ctx["enemy_hp"][0] <= 0:
            ctx["enemy_hp"].pop(0)
    if card.effect:
        card.effect(hero, ctx)


def monster_attack(hero: Hero, ctx: Dict) -> None:
    band = ctx["enemy_type"].bands
    raw = band[(d8()-1)//2] * len(ctx["enemy_hp"])
    soak = min(hero.armor_pool, raw)
    hero.armor_pool -= soak
    hero.hp -= max(0, raw - soak)

def fight_one(hero: Hero) -> bool:
    hero.reset()
    hero.deck.draw(4)
    for enemy, count in BASIC_WAVES:
        ctx = make_wave(enemy, count)
        for exch in range(3):
            hero.exchange_effects.clear()
            hero.armor_pool = 0
            if exch:
                hero.deck.draw(1)
            apply_persistent(hero, ctx)
            while True:
                c = hero.deck.pop_first(CardType.UTIL)
                if not c:
                    break
                hero.armor_pool += c.armor
                if c.effect:
                    c.effect(hero, ctx)
                hero.deck.disc.append(c)
            while ctx["enemy_hp"]:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c:
                    break
                resolve_attack(hero, c, ctx)
                hero.deck.disc.append(c)
            if not ctx["enemy_hp"]:
                break
            monster_attack(hero, ctx)
            if hero.hp <= 0:
                return False
            while ctx["enemy_hp"]:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                resolve_attack(hero, c, ctx)
                hero.deck.disc.append(c)
            if not ctx["enemy_hp"]:
                break
        if ctx["enemy_hp"] or hero.hp <= 0:
            return False
        hero.gain_fate(1)
        # gain upgrades placeholder
    return True

if __name__ == "__main__":
    N = 20
    wins = sum(fight_one(random.choice(HEROES)) for _ in range(N))
    print("Win rate", wins/N)
