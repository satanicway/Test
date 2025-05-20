#!/usr/bin/env python3
"""Simplified board game simulator with partial card logic.
This version introduces enumerations, Fate tracking, vulnerability,
and placeholder hooks for [Combat]/[Exchange] effects.
The rule set is condensed but demonstrates key mechanics.
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Dict

RNG = random.Random()

def d8() -> int:
    return RNG.randint(1, 8)

class CardType(Enum):
    MELEE = auto()
    RANGED = auto()
    UTIL = auto()

class Element(Enum):
    BRUTAL = "B"
    DIVINE = "D"
    PRECISE = "P"
    ARCANE = "A"
    SPIRITUAL = "S"

@dataclass
class Card:
    name: str
    ctype: CardType
    element: Optional[Element] = None
    dice: int = 0
    armor: int = 0
    effect: Optional[Callable[["Hero", Dict], None]] = None

@dataclass
class Deck:
    draw_pile: List[Card]
    hand: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    HAND_MAX: int = 7

    def shuffle(self) -> None:
        RNG.shuffle(self.draw_pile)

    def draw(self, n: int) -> None:
        for _ in range(n):
            if len(self.hand) >= self.HAND_MAX:
                break
            if not self.draw_pile:
                RNG.shuffle(self.discard)
                self.draw_pile, self.discard = self.discard, []
                if not self.draw_pile:
                    break
            self.hand.append(self.draw_pile.pop())

    def pop_first(self, ctype: CardType) -> Optional[Card]:
        for i, c in enumerate(self.hand):
            if c.ctype == ctype:
                return self.hand.pop(i)
        return None

@dataclass
class Hero:
    name: str
    max_hp: int
    base_deck: List[Card]
    upgrade_pool: List[Card] = field(default_factory=list)
    plate: float = 1.0

    def reset(self) -> None:
        self.cur_hp = self.max_hp
        self.fate = 0
        self.armor_pool = 0
        self.combat_effects: Dict[str, int] = {}
        self.exchange_effects: Dict[str, int] = {}
        self.hymns = 0
        self.deck = Deck(self.base_deck[:])
        self.deck.shuffle()

    def can_reroll(self) -> bool:
        limit = 5 if self.name == "Brynhild" else 3
        return self.fate > limit

    def spend_fate(self, n: int = 1) -> None:
        self.fate = max(0, self.fate - n)

@dataclass
class Enemy:
    hp: int
    defense: int
    vulnerability: Element

# effect helpers

def gain_armor(x: int) -> Callable[[Hero, Dict], None]:
    def fx(hero: Hero, ctx: Dict) -> None:
        hero.armor_pool += x
    return fx

def gain_fate(x: int) -> Callable[[Hero, Dict], None]:
    def fx(hero: Hero, ctx: Dict) -> None:
        hero.fate = min(10, hero.fate + x)
    return fx

def dmg_all(x: int) -> Callable[[Hero, Dict], None]:
    def fx(hero: Hero, ctx: Dict) -> None:
        for e in ctx["enemies"]:
            e.hp -= x
    return fx

def atk(name: str, ctype: CardType, element: Element, dice: int = 0,
        armor: int = 0, effect: Optional[Callable[[Hero, Dict], None]] = None) -> Card:
    return Card(name, ctype, element, dice, armor, effect)

# -- heroes --
hercules_base = [
    atk("Pillar-Breaker Blow", CardType.MELEE, Element.BRUTAL, 2),
    atk("Pillar-Breaker Blow", CardType.MELEE, Element.BRUTAL, 2),
    atk("Lion Strangler", CardType.MELEE, Element.BRUTAL, 1),
    atk("Demigodly Heroism", CardType.MELEE, Element.DIVINE, 1, armor=1, effect=gain_armor(1)),
    atk("Demigodly Heroism", CardType.MELEE, Element.DIVINE, 1, armor=1, effect=gain_armor(1)),
    atk("Sky Javelin", CardType.RANGED, Element.DIVINE, 2),
    atk("Club Spin", CardType.MELEE, Element.PRECISE, 1),
    atk("Club Spin", CardType.MELEE, Element.PRECISE, 1),
    atk("Atlas Guard", CardType.UTIL, Element.SPIRITUAL, armor=3, effect=gain_armor(3)),
    atk("Atlas Guard", CardType.UTIL, Element.SPIRITUAL, armor=3, effect=gain_armor(3)),
]

merlin_base = [
    atk("Arcane Volley", CardType.RANGED, Element.ARCANE, 1, effect=dmg_all(1)),
    atk("Arcane Volley", CardType.RANGED, Element.ARCANE, 1, effect=dmg_all(1)),
    atk("Lady's Warden", CardType.MELEE, Element.ARCANE, 1, armor=2, effect=gain_armor(2)),
    atk("Lady's Warden", CardType.MELEE, Element.ARCANE, 1, armor=2, effect=gain_armor(2)),
    atk("Weaver of Fate", CardType.RANGED, Element.DIVINE, 1),
    atk("Weaver of Fate", CardType.RANGED, Element.DIVINE, 1),
    atk("Crystal Cave's Staff", CardType.MELEE, Element.PRECISE, 1),
    atk("Mists of Time", CardType.RANGED, Element.SPIRITUAL, 1),
    atk("Mists of Time", CardType.RANGED, Element.SPIRITUAL, 1),
    atk("Circle of Avalon", CardType.RANGED, Element.SPIRITUAL, 1),
]

musashi_base = [
    atk("Swallow-Cut", CardType.MELEE, Element.PRECISE, 1),
    atk("Swallow-Cut", CardType.MELEE, Element.PRECISE, 1),
    atk("Cross-River Strike", CardType.MELEE, Element.PRECISE, 2),
    atk("Cross-River Strike", CardType.MELEE, Element.PRECISE, 2),
    atk("Heaven-and-Earth Slash", CardType.MELEE, Element.BRUTAL, 2),
    atk("Heaven-and-Earth Slash", CardType.MELEE, Element.BRUTAL, 2),
    atk("Flowing Water Parry", CardType.MELEE, Element.SPIRITUAL, 1, armor=1, effect=gain_armor(1)),
    atk("Flowing Water Parry", CardType.MELEE, Element.SPIRITUAL, 1, armor=1, effect=gain_armor(1)),
    atk("Dual-Moon Guard", CardType.UTIL, Element.DIVINE, armor=1, effect=gain_armor(1)),
    atk("Wind-Reading Focus", CardType.MELEE, Element.ARCANE, 1),
]

brynhild_base = [
    atk("Valkyrie's Descent", CardType.MELEE, Element.SPIRITUAL, 1),
    atk("Valkyrie's Descent", CardType.MELEE, Element.SPIRITUAL, 1),
    atk("Sky-Piercer", CardType.RANGED, Element.SPIRITUAL, 1, effect=gain_fate(1)),
    atk("Hymn of Shields", CardType.UTIL, Element.DIVINE),
    atk("Hymn of Shields", CardType.UTIL, Element.DIVINE),
    atk("Hymn of Storms", CardType.UTIL, Element.DIVINE),
    atk("Thrust of Destiny", CardType.MELEE, Element.PRECISE, 1),
    atk("Thrust of Destiny", CardType.MELEE, Element.PRECISE, 1),
    atk("Spear of the Aesir", CardType.MELEE, Element.BRUTAL, 1),
    atk("Spear of the Aesir", CardType.MELEE, Element.BRUTAL, 1),
]

HEROES = [
    Hero("Hercules", 25, hercules_base),
    Hero("Merlin", 15, merlin_base),
    Hero("Musashi", 20, musashi_base),
    Hero("Brynhild", 18, brynhild_base),
]

# simplified enemy waves
GROUP = [1,1]
HP0 = [3,3]
DEF0 = [4,5]
VULN = [Element.BRUTAL, Element.SPIRITUAL]
BANDS = [[2,2,2,2],[2,2,2,2]]


def roll_attack(hero: Hero, card: Card, enemy: Enemy) -> int:
    hits = 0
    for _ in range(card.dice):
        face = d8()
        val = max(1, min(8, face))
        if val >= enemy.defense:
            hits += 2 if val == 8 else 1
        else:
            if hero.can_reroll() and enemy.hp - hits <= 2:
                hero.spend_fate(1)
                face = d8()
                val = max(1, min(8, face))
                if val >= enemy.defense:
                    hits += 2 if val == 8 else 1
    dmg = hits
    if card.element == enemy.vulnerability:
        dmg *= 2
    return dmg


def fight_one(hero: Hero) -> bool:
    hero.reset()
    hero.deck.draw(4)
    for g,hp,df,band,vuln in zip(GROUP,HP0,DEF0,BANDS,VULN):
        enemies = [Enemy(hp, df, vuln) for _ in range(g)]
        hero.combat_effects.clear()
        for exch in range(3):
            hero.exchange_effects.clear()
            hero.armor_pool = 0
            if exch:
                hero.deck.draw(2)
            while True:
                c = hero.deck.pop_first(CardType.UTIL)
                if not c:
                    break
                hero.armor_pool += c.armor
                if c.effect:
                    c.effect(hero, {"enemies": enemies})
                hero.deck.discard.append(c)
            while enemies:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c:
                    break
                dmg = roll_attack(hero, c, enemies[0])
                if c.effect:
                    c.effect(hero, {"enemies": enemies})
                enemies[0].hp -= dmg
                if enemies[0].hp <= 0:
                    enemies.pop(0)
                hero.deck.discard.append(c)
            if not enemies:
                break
            raw = band[(d8()-1)//2] * len(enemies)
            raw = max(0, raw - hero.plate)
            soak = min(raw, hero.armor_pool)
            hero.armor_pool -= soak
            hero.cur_hp -= max(0, raw - soak)
            if hero.cur_hp <= 0:
                return False
            while enemies:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                hero.armor_pool += c.armor
                dmg = roll_attack(hero, c, enemies[0])
                if c.effect:
                    c.effect(hero, {"enemies": enemies})
                enemies[0].hp -= dmg
                if enemies[0].hp <= 0:
                    enemies.pop(0)
                hero.deck.discard.append(c)
            if not enemies:
                break
        if enemies:
            return False
        if hero.upgrade_pool:
            hero.deck.draw_pile.extend(RNG.sample(hero.upgrade_pool,1))
        hero.fate = min(10, hero.fate + 1)
    return True

if __name__ == "__main__":
    wins = 0
    N = 100
    for _ in range(N):
        if fight_one(random.choice(HEROES)):
            wins += 1
    print("Win rate:", wins / N)
