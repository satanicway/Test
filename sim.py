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

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class CardType(Enum):
    MELEE = auto()
    RANGED = auto()
    UTIL = auto()

class Element(Enum):
    B = 'Brutal'
    D = 'Divine'
    P = 'Precise'
    S = 'Spiritual'
    A = 'Arcane'

# ---------------------------------------------------------------------------
@dataclass
class Card:
    name: str
    ctype: CardType
    dice: int = 0
    element: Optional[Element] = None
    armor: int = 0
    multi: bool = False
    effect: Optional[Callable[["Hero", "Context", "Enemy"], None]] = None

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

@dataclass
class Hero:
    name: str
    max_hp: int
    base: List[Card]
    upgrades: List[Card]
    fate: int = 0

    def reset(self) -> None:
        self.hp = self.max_hp
        self.fate = 0
        self.deck = Deck(self.base.copy())
        self.deck.shuffle()
        self.armor_pool = 0
        self.combat_effects: Dict[str, int] = {}
        self.exchange_effects: Dict[str, int] = {}

@dataclass
class Enemy:
    name: str
    hp: int
    defense: int
    vulnerability: Element
    band: List[int]
    ability: Optional[Callable[["Hero", "Enemy", "Context"], None]] = None

Context = Dict[str, Any]

# ---------------------------------------------------------------------------
# Dice rolling with optional Fate reroll and vulnerability
# ---------------------------------------------------------------------------

def roll_hits(hero: Hero, enemy: Enemy, dice: int, element: Optional[Element]) -> int:
    dmg = 0
    for _ in range(dice):
        r = d8()
        threshold = 5 if hero.name == 'Brynhild' else 3
        if r < enemy.defense and hero.fate > threshold:
            hero.fate -= 1
            r = d8()
        if r >= enemy.defense:
            dmg += 2 if r == 8 else 1
    if element and element == enemy.vulnerability:
        dmg *= 2
    dmg += hero.exchange_effects.get('dmg_bonus', 0)
    return dmg

# Helper effect creators

def gain_armor(n: int) -> Callable[[Hero, Context, Enemy], None]:
    def fx(hero: Hero, ctx: Context, enemy: Enemy) -> None:
        hero.armor_pool += n
    return fx

def sky_javelin_fx(hero: Hero, ctx: Context, enemy: Enemy) -> None:
    hero.exchange_effects['dmg_bonus'] = hero.exchange_effects.get('dmg_bonus', 0) + 1

def lion_strangler_fx(hero: Hero, ctx: Context, enemy: Enemy) -> None:
    hero.combat_effects['bleed'] = hero.combat_effects.get('bleed', 0) + 1

# ---------------------------------------------------------------------------
# Hero decks (initial only)
# ---------------------------------------------------------------------------
HERCULES_BASE = [
    Card('Pillar-Breaker Blow', CardType.MELEE, 2, Element.B),
    Card('Pillar-Breaker Blow', CardType.MELEE, 2, Element.B),
    Card('Lion Strangler', CardType.MELEE, 1, Element.B, effect=lion_strangler_fx),
    Card('Demigodly Heroism', CardType.MELEE, 1, Element.D, armor=1, effect=gain_armor(1)),
    Card('Demigodly Heroism', CardType.MELEE, 1, Element.D, armor=1, effect=gain_armor(1)),
    Card('Sky Javelin', CardType.RANGED, 2, Element.D, effect=sky_javelin_fx),
    Card('Club Spin', CardType.MELEE, 1, Element.P, multi=True),
    Card('Club Spin', CardType.MELEE, 1, Element.P, multi=True),
    Card('Atlas Guard', CardType.UTIL, 0, None, armor=3, effect=gain_armor(3)),
    Card('Atlas Guard', CardType.UTIL, 0, None, armor=3, effect=gain_armor(3)),
]
hercules = Hero('Hercules', 25, HERCULES_BASE, [])

MERLIN_BASE = [
    Card('Arcane Volley', CardType.RANGED, 1, Element.A, multi=True),
    Card('Arcane Volley', CardType.RANGED, 1, Element.A, multi=True),
    Card("Lady's Warden", CardType.MELEE, 1, Element.A, armor=2, effect=gain_armor(2)),
    Card("Lady's Warden", CardType.MELEE, 1, Element.A, armor=2, effect=gain_armor(2)),
    Card('Weaver of Fate', CardType.RANGED, 1, Element.D),
    Card('Weaver of Fate', CardType.RANGED, 1, Element.D),
    Card("Crystal Cave's Staff", CardType.MELEE, 1, Element.P),
    Card('Mists of Time', CardType.RANGED, 1, Element.S),
    Card('Mists of Time', CardType.RANGED, 1, Element.S),
    Card('Circle of Avalon', CardType.RANGED, 1, Element.S),
]
merlin = Hero('Merlin', 15, MERLIN_BASE, [])

MUSASHI_BASE = [
    Card('Swallow-Cut', CardType.MELEE, 1, Element.P),
    Card('Swallow-Cut', CardType.MELEE, 1, Element.P),
    Card('Cross-River Strike', CardType.MELEE, 2, Element.P, multi=True),
    Card('Cross-River Strike', CardType.MELEE, 2, Element.P, multi=True),
    Card('Heaven-and-Earth Slash', CardType.MELEE, 2, Element.B),
    Card('Heaven-and-Earth Slash', CardType.MELEE, 2, Element.B),
    Card('Flowing Water Parry', CardType.MELEE, 1, Element.S, armor=1, effect=gain_armor(1)),
    Card('Flowing Water Parry', CardType.MELEE, 1, Element.S, armor=1, effect=gain_armor(1)),
    Card('Dual-Moon Guard', CardType.UTIL, 0, None),
    Card('Wind-Reading Focus', CardType.MELEE, 1, Element.A),
]
musashi = Hero('Musashi', 20, MUSASHI_BASE, [])

BRYN_BASE = [
    Card("Valkyrie's Descent", CardType.MELEE, 1, Element.S),
    Card("Valkyrie's Descent", CardType.MELEE, 1, Element.S),
    Card('Sky-Piercer', CardType.RANGED, 1, Element.S),
    Card('Hymn of Shields', CardType.UTIL, 0),
    Card('Hymn of Shields', CardType.UTIL, 0),
    Card('Hymn of Storms', CardType.UTIL, 0),
    Card('Thrust of Destiny', CardType.MELEE, 1, Element.P),
    Card('Thrust of Destiny', CardType.MELEE, 1, Element.P),
    Card('Spear of the Aesir', CardType.MELEE, 1, Element.B),
    Card('Spear of the Aesir', CardType.MELEE, 1, Element.B),
]
brynhild = Hero('Brynhild', 18, BRYN_BASE, [])

HEROES = [hercules, merlin, musashi, brynhild]

# ---------------------------------------------------------------------------
# Enemies (subset only)
# ---------------------------------------------------------------------------

def web_slinger(hero: Hero, enemy: Enemy, ctx: Context) -> None:
    ctx['ranged_as_melee'] = True

def cursed_thorns(hero: Hero, enemy: Enemy, ctx: Context) -> None:
    ctx['cursed_thorns'] = True

def dark_phalanx(hero: Hero, enemy: Enemy, ctx: Context) -> None:
    ctx['soldiers'] = ctx.get('soldiers', 0) + 1

def power_of_death(hero: Hero, enemy: Enemy, ctx: Context) -> None:
    ctx['priests'] = ctx.get('priests', 0) + 1

BASIC_ENEMIES = [
    Enemy('Shadow Spinner', 1, 4, Element.S, [0,0,1,3], ability=web_slinger),
    Enemy('Void Soldier', 2, 5, Element.P, [0,0,0,2], ability=dark_phalanx),
    Enemy('Priest of Oblivion', 2, 3, Element.A, [0,0,1,1], ability=power_of_death),
    Enemy('Corrupted Dryad', 2, 4, Element.B, [0,0,1,1], ability=cursed_thorns),
]

# ---------------------------------------------------------------------------
# Combat engine
# ---------------------------------------------------------------------------

def monster_strike(enemy: Enemy) -> int:
    return enemy.band[(d8() - 1) // 2]

def fight_one(hero: Hero) -> bool:
    hero.reset()
    hero.deck.draw(4)
    waves = [random.choice(BASIC_ENEMIES) for _ in range(2)]
    ctx: Context = {}
    for enemy in waves:
        enemy_hp = enemy.hp
        ctx.clear()
        if enemy.ability:
            enemy.ability(hero, enemy, ctx)
        for exch in range(3):
            hero.exchange_effects.clear()
            hero.deck.draw(2)
            hero.armor_pool = 0
            # UTIL
            while True:
                card = hero.deck.pop_first(CardType.UTIL)
                if not card:
                    break
                hero.armor_pool += card.armor
                if card.effect:
                    card.effect(hero, ctx, enemy)
                hero.deck.disc.append(card)
            ranged_type = CardType.RANGED if not ctx.get('ranged_as_melee') else CardType.MELEE
            # RANGED
            while True:
                card = hero.deck.pop_first(ranged_type)
                if not card or enemy_hp <= 0:
                    break
                dmg = roll_hits(hero, enemy, card.dice, card.element)
                if card.multi and ctx.get('soldiers',0)>1:
                    dmg = max(1, dmg - 1)
                if card.effect:
                    card.effect(hero, ctx, enemy)
                enemy_hp -= dmg
                hero.deck.disc.append(card)
            if enemy_hp <= 0:
                hero.fate = min(10, hero.fate + 1)
                break
            # MONSTER ATTACK
            m_dmg = monster_strike(enemy)
            soak = min(m_dmg, hero.armor_pool)
            hero.armor_pool -= soak
            hero.hp -= max(0, m_dmg - soak) + ctx.get('priests',0)
            if hero.hp <= 0:
                return False
            # MELEE
            while True:
                card = hero.deck.pop_first(CardType.MELEE)
                if not card or enemy_hp <= 0:
                    break
                hero.armor_pool += card.armor
                hero.exchange_effects['element'] = card.element
                dmg = roll_hits(hero, enemy, card.dice, card.element)
                if card.multi and ctx.get('soldiers',0)>1:
                    dmg = max(1, dmg - 1)
                if card.effect:
                    card.effect(hero, ctx, enemy)
                enemy_hp -= dmg
                hero.deck.disc.append(card)
                bleed = hero.combat_effects.get('bleed',0)
                if bleed:
                    enemy_hp -= bleed
            if enemy_hp <= 0:
                hero.fate = min(10, hero.fate + 1)
                break
            # End exchange
            if ctx.get('cursed_thorns') and hero.armor_pool > 0:
                hero.hp -= hero.armor_pool
                hero.armor_pool = 0
            if hero.hp <= 0:
                return False
        if enemy_hp > 0:
            return False
    return hero.hp > 0

# ---------------------------------------------------------------------------
if __name__ == '__main__':
    wins = 0
    N = 20
    for _ in range(N):
        if fight_one(random.choice(HEROES)):
            wins += 1
    print(f'Win rate: {wins/N:.2f}')
