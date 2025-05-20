#!/usr/bin/env python3
"""Minimal board game simulator showing fate, armor, vulnerability and
persistent effects.
This version rewrites the broken previous script with a compact
implementation that still demonstrates the same mechanics."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple

RNG = random.Random()

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
    upg_cards: List[Card] = field(default_factory=list)

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

    def spend_fate(self, n: int = 1) -> bool:
        if self.fate >= n:
            self.fate -= n
            return True
        return False

@dataclass
class Enemy:
    hp: int
    defense: int
    vulnerability: Element = Element.NONE
    ability: Optional[str] = None

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
              allow_reroll: bool = True) -> int:
    dmg = 0
    for _ in range(num_dice):
        r = roll_die(defense, mod, hero=hero, allow_reroll=allow_reroll)
        if r >= defense:
            hit = 2 if r == 8 else 1
            if element != Element.NONE and element == vulnerability:
                hit *= 2
            dmg += hit
    return dmg

# persistent effect application

def apply_persistent(hero: Hero, ctx: Dict[str, object]) -> None:
    for fx, _ in hero.combat_effects:
        fx(hero, ctx)
    for fx, _ in hero.exchange_effects:
        fx(hero, ctx)

# simple card effects ---------------------------------------------------------

def gain_armor(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += n
    return _fx

def end_hymns_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    hero.active_hymns.clear()
    hero.combat_effects = [p for p in hero.combat_effects if not p[1].hymn]
    hero.exchange_effects = [p for p in hero.exchange_effects if not p[1].hymn]

# ---------------------------------------------------------------------------
# Card helpers to create attack cards
# ---------------------------------------------------------------------------
def atk(name: str, ctype: CardType, dice: int, element: Element = Element.NONE,
        armor: int = 0, effect: Optional[Callable[[Hero, Dict], None]] = None,
        persistent: Optional[str] = None, hymn: bool = False,
        multi: bool = False) -> Card:
    return Card(name, ctype, dice, element, armor, effect, persistent, hymn, multi)

# sample hero decks -----------------------------------------------------------
herc_base = [
    atk("Pillar", CardType.MELEE, 2, Element.BRUTAL),
    atk("Heroism", CardType.MELEE, 1, Element.DIVINE, armor=1, effect=gain_armor(1)),
    atk("Javelin", CardType.RANGED, 2, Element.DIVINE),
]
hercules = Hero("Hercules", 25, herc_base)

bryn_base = [
    atk("Descent", CardType.MELEE, 1, Element.SPIRITUAL),
    atk("Shields", CardType.UTIL, 0, hymn=True, persistent="combat"),
    atk("Storms", CardType.UTIL, 0, effect=end_hymns_fx),
]
brynhild = Hero("Brynhild", 18, bryn_base)

HEROES = [hercules, brynhild]

# sample enemy
BASIC_ENEMY = Enemy(hp=4, defense=5, vulnerability=Element.DIVINE)

# ---------------------------------------------------------------------------
# Combat helpers
# ---------------------------------------------------------------------------
def resolve_attack(hero: Hero, card: Card, enemy: Enemy, ctx: Dict[str, object]) -> None:
    dmg = roll_hits(card.dice, enemy.defense, hero=hero, element=card.element,
                    vulnerability=enemy.vulnerability)
    enemy.hp -= dmg
    if card.effect:
        card.effect(hero, ctx)
        if card.persistent == "combat":
            hero.combat_effects.append((card.effect, card))
        elif card.persistent == "exchange":
            hero.exchange_effects.append((card.effect, card))
    if card.hymn:
        hero.active_hymns.append(card)
    hero.deck.disc.append(card)

# very small fight simulation -------------------------------------------------

def fight_one(hero: Hero) -> bool:
    enemy = Enemy(BASIC_ENEMY.hp, BASIC_ENEMY.defense, BASIC_ENEMY.vulnerability,
                  BASIC_ENEMY.ability)
    hero.reset()
    hero.deck.draw(3)
    ctx: Dict[str, object] = {}

    for _ in range(3):  # three exchanges
        apply_persistent(hero, ctx)
        # use first util if any
        c = hero.deck.pop_first(CardType.UTIL)
        if c:
            resolve_attack(hero, c, enemy, ctx)
        if enemy.hp <= 0:
            break

        c = hero.deck.pop_first(CardType.RANGED) or hero.deck.pop_first(CardType.MELEE)
        if c:
            resolve_attack(hero, c, enemy, ctx)
        if enemy.hp <= 0:
            break

        hero.deck.draw(1)

    hero.combat_effects.clear()
    hero.exchange_effects.clear()
    hero.active_hymns.clear()
    return enemy.hp <= 0

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    N = 20
    wins = sum(fight_one(random.choice(HEROES)) for _ in range(N))
    print("Win rate", wins / N)
