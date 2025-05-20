#!/usr/bin/env python3
"""Improved board game simulator with simplified card effects."""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

RNG = random.Random()

def d8():
    return RNG.randint(1, 8)

class CardType(Enum):
    MELEE = auto()
    RANGED = auto()
    UTIL = auto()

class Element(Enum):
    BRUTAL = 'B'
    PRECISE = 'P'
    DIVINE = 'D'
    ARCANE = 'A'
    SPIRITUAL = 'S'
    NONE = '-'

@dataclass
class Card:
    name: str
    ctype: CardType
    element: Element
    dice: int = 0
    armor: int = 0
    effect: Optional[Callable] = None
    combat: bool = False
    exchange: bool = False

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)
    MAX_HAND: int = 7

    def shuffle(self) -> None:
        RNG.shuffle(self.cards)

    def draw(self, n: int) -> None:
        while n and len(self.hand) < self.MAX_HAND:
            if not self.cards:
                RNG.shuffle(self.disc)
                self.cards, self.disc = self.disc, []
                if not self.cards:
                    break
            self.hand.append(self.cards.pop())
            n -= 1

    def pop_first(self, ctype: CardType) -> Optional[Card]:
        for i, c in enumerate(self.hand):
            if c.ctype == ctype:
                return self.hand.pop(i)
        return None

@dataclass
class Hero:
    name: str
    max_hp: int
    base_cards: List[Card]
    upg_cards: List[Card]
    plate: int = 0

    def reset(self) -> None:
        self.hp = self.max_hp
        self.fate = 0
        self.armor_pool = 0
        self.deck = Deck(self.base_cards[:])
        self.deck.shuffle()
        self.combat_effects: Dict[str, int] = {}
        self.exchange_effects: Dict[str, int] = {}

    def gain_upgrade(self) -> None:
        if self.upg_cards:
            self.deck.cards.extend(RNG.sample(self.upg_cards, 1))

@dataclass
class EnemyType:
    name: str
    hp: int
    defense: int
    vuln: Element

@dataclass
class Enemy:
    etype: EnemyType
    hp: int
    def __init__(self, etype: EnemyType):
        self.etype = etype
        self.hp = etype.hp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def roll_hits(num_dice: int, defense: int, mod: int = 0) -> int:
    dmg = 0
    for _ in range(num_dice):
        r = max(1, min(8, d8() + mod))
        if r >= defense:
            dmg += 2 if r == 8 else 1
    return dmg


def deal_damage(enemy: Enemy, dmg: int, element: Element) -> None:
    if element != Element.NONE and enemy.etype.vuln == element:
        dmg *= 2
    enemy.hp -= dmg

# Example effect callbacks

def lion_strangler_fx(hero: Hero, ctx: Dict) -> None:
    hero.combat_effects['bleed'] = hero.combat_effects.get('bleed', 0) + 1


def sky_javelin_fx(hero: Hero, ctx: Dict) -> None:
    hero.exchange_effects['bonus_dmg'] = hero.exchange_effects.get('bonus_dmg', 0) + 1


def club_spin_fx(hero: Hero, ctx: Dict) -> None:
    for e in list(ctx['enemies']):
        dmg = roll_hits(1, e.etype.defense)
        deal_damage(e, dmg, Element.PRECISE)
        if e.hp <= 0:
            ctx['enemies'].remove(e)


def atlas_guard_fx(hero: Hero, ctx: Dict) -> None:
    hero.armor_pool += 3

# Card constructor

def atk(name, ctype, element, dice, armor=0, effect=None, combat=False, exchange=False):
    return Card(name, ctype, element, dice, armor, effect, combat, exchange)

# ---------------------------------------------------------------------------
# Heroes (initial decks only for brevity)
# ---------------------------------------------------------------------------
herc_base = [
    atk('Pillar-Breaker Blow', CardType.MELEE, Element.BRUTAL, 2),
    atk('Pillar-Breaker Blow', CardType.MELEE, Element.BRUTAL, 2),
    atk('Lion Strangler', CardType.MELEE, Element.BRUTAL, 1, effect=lion_strangler_fx, combat=True),
    atk('Demigodly Heroism', CardType.MELEE, Element.DIVINE, 1, armor=1),
    atk('Demigodly Heroism', CardType.MELEE, Element.DIVINE, 1, armor=1),
    atk('Sky Javelin', CardType.RANGED, Element.DIVINE, 2, effect=sky_javelin_fx, exchange=True),
    atk('Club Spin', CardType.MELEE, Element.PRECISE, 0, effect=club_spin_fx),
    atk('Club Spin', CardType.MELEE, Element.PRECISE, 0, effect=club_spin_fx),
    atk('Atlas Guard', CardType.UTIL, Element.NONE, 0, effect=atlas_guard_fx),
    atk('Atlas Guard', CardType.UTIL, Element.NONE, 0, effect=atlas_guard_fx),
]
hercules = Hero('Hercules', 25, herc_base, [])

mer_base = [
    atk('Arcane Volley', CardType.RANGED, Element.ARCANE, 1),
    atk('Arcane Volley', CardType.RANGED, Element.ARCANE, 1),
    atk("Lady's Warden", CardType.MELEE, Element.ARCANE, 1, armor=2),
    atk("Lady's Warden", CardType.MELEE, Element.ARCANE, 1, armor=2),
    atk('Weaver of Fate', CardType.RANGED, Element.DIVINE, 1),
    atk('Weaver of Fate', CardType.RANGED, Element.DIVINE, 1),
    atk("Crystal Cave's Staff", CardType.MELEE, Element.PRECISE, 1),
    atk('Mists of Time', CardType.RANGED, Element.SPIRITUAL, 1, exchange=True),
    atk('Mists of Time', CardType.RANGED, Element.SPIRITUAL, 1, exchange=True),
    atk('Circle of Avalon', CardType.RANGED, Element.SPIRITUAL, 1, combat=True),
]
merlin = Hero('Merlin', 15, mer_base, [])

mus_base = [
    atk('Swallow-Cut', CardType.MELEE, Element.PRECISE, 1),
    atk('Swallow-Cut', CardType.MELEE, Element.PRECISE, 1),
    atk('Cross-River Strike', CardType.MELEE, Element.PRECISE, 2),
    atk('Cross-River Strike', CardType.MELEE, Element.PRECISE, 2),
    atk('Heaven-and-Earth Slash', CardType.MELEE, Element.BRUTAL, 2),
    atk('Heaven-and-Earth Slash', CardType.MELEE, Element.BRUTAL, 2),
    atk('Flowing Water Parry', CardType.MELEE, Element.SPIRITUAL, 1, armor=1),
    atk('Flowing Water Parry', CardType.MELEE, Element.SPIRITUAL, 1, armor=1),
    atk('Dual-Moon Guard', CardType.UTIL, Element.NONE, 0),
    atk('Wind-Reading Focus', CardType.MELEE, Element.ARCANE, 1),
]
musashi = Hero('Musashi', 20, mus_base, [])

bryn_base = [
    atk("Valkyrie's Descent", CardType.MELEE, Element.SPIRITUAL, 1, combat=True),
    atk("Valkyrie's Descent", CardType.MELEE, Element.SPIRITUAL, 1, combat=True),
    atk('Sky-Piercer', CardType.RANGED, Element.SPIRITUAL, 1),
    atk('Hymn of Shields', CardType.UTIL, Element.NONE, 0, combat=True),
    atk('Hymn of Shields', CardType.UTIL, Element.NONE, 0, combat=True),
    atk('Hymn of Storms', CardType.UTIL, Element.NONE, 0, combat=True),
    atk('Thrust of Destiny', CardType.MELEE, Element.PRECISE, 1),
    atk('Thrust of Destiny', CardType.MELEE, Element.PRECISE, 1),
    atk('Spear of the Aesir', CardType.MELEE, Element.BRUTAL, 1, exchange=True),
    atk('Spear of the Aesir', CardType.MELEE, Element.BRUTAL, 1, exchange=True),
]
brynhild = Hero('Brynhild', 18, bryn_base, [])

HEROES = [hercules, merlin, musashi, brynhild]

# ---------------------------------------------------------------------------
# Enemies (simplified subset)
# ---------------------------------------------------------------------------
ENEMY_TYPES = {
    'spinner': EnemyType('Shadow Spinner', 3, 4, Element.SPIRITUAL),
    'soldier': EnemyType('Void Soldier', 3, 5, Element.PRECISE),
}
WAVES = [
    ('spinner', 2),
    ('soldier', 2),
]

# ---------------------------------------------------------------------------
# Combat helpers
# ---------------------------------------------------------------------------

def spend_fate_for_reroll(hero: Hero, dmg: int, enemy: Enemy) -> int:
    thresh = 5 if hero.name == 'Brynhild' else 3
    while hero.fate > thresh and enemy.hp > dmg:
        hero.fate -= 1
        r = max(1, min(8, d8()))
        if r >= enemy.etype.defense:
            dmg += 2 if r == 8 else 1
    return dmg


def resolve_attack(hero: Hero, card: Card, enemy: Enemy, ctx: Dict) -> None:
    hero.armor_pool += card.armor
    dmg = roll_hits(card.dice, enemy.etype.defense)
    dmg = spend_fate_for_reroll(hero, dmg, enemy)
    dmg += hero.exchange_effects.get('bonus_dmg', 0)
    deal_damage(enemy, dmg, card.element)
    if card.effect:
        card.effect(hero, ctx)


def fight_one(hero: Hero) -> bool:
    hero.reset()
    hero.deck.draw(4)
    for key, count in WAVES:
        enemies = [Enemy(ENEMY_TYPES[key]) for _ in range(count)]
        hero.combat_effects.clear()
        for exch in range(3):
            hero.exchange_effects.clear()
            hero.armor_pool = 0
            if exch:
                hero.deck.draw(1)
            ctx = {'enemies': enemies}
            while True:
                c = hero.deck.pop_first(CardType.UTIL)
                if not c:
                    break
                if c.effect:
                    c.effect(hero, ctx)
                hero.deck.disc.append(c)
            for enemy in enemies[:]:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c:
                    break
                resolve_attack(hero, c, enemy, ctx)
                hero.deck.disc.append(c)
                if enemy.hp <= 0 and enemy in enemies:
                    enemies.remove(enemy)
            if not enemies:
                break
            dmg_in = len(enemies)
            soak = min(dmg_in, hero.armor_pool)
            hero.armor_pool -= soak
            hero.hp -= max(0, dmg_in - soak)
            if hero.hp <= 0:
                return False
            for enemy in enemies[:]:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                resolve_attack(hero, c, enemy, ctx)
                hero.deck.disc.append(c)
                if enemy.hp <= 0 and enemy in enemies:
                    enemies.remove(enemy)
            if not enemies:
                break
            bleed = hero.combat_effects.get('bleed', 0)
            if bleed and enemies:
                enemies[0].hp -= bleed
                if enemies[0].hp <= 0:
                    enemies.pop(0)
            if not enemies:
                break
        if enemies:
            return False
        hero.fate = min(10, hero.fate + 1)
        hero.gain_upgrade()
    return True

if __name__ == '__main__':
    wins = 0
    trials = 50
    for _ in range(trials):
        if fight_one(random.choice(HEROES)):
            wins += 1
    print('Win rate:', wins / trials)
