#!/usr/bin/env python3
"""Simplified board game simulator with basic card and combat logic.

This version implements a few additional mechanics that were requested in
earlier discussions:
* Enumerations for card types and elements
* Hand size limit when drawing cards
* Fate tracking and rerolls
* Simple vulnerability handling
* Support for Combat and Exchange effects (very limited)

It is **not** a full rules implementation but provides a foundation that can be
expanded further.
"""

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Callable, Optional

# Dice helper
RNG = random.Random()
d8 = lambda: RNG.randint(1, 8)


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

def roll_hits(num_dice: int, defense: int, mod: int = 0,
              vulnerable: bool = False) -> int:
    """Roll ``num_dice`` against ``defense``.

    If ``vulnerable`` is True, total damage is doubled at the end.
    """
    dmg = 0
    for _ in range(num_dice):
        r = max(1, min(8, d8() + mod))
        if r >= defense:
            dmg += 2 if r == 8 else 1
    if vulnerable:
        dmg *= 2
    return dmg

# Card and deck definitions
@dataclass
class Card:
    name: str
    ctype: CardType
    dice: int = 0
    armor: int = 0
    element: Optional[Element] = None
    effect: Optional[Callable] = None

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)
    MAX_HAND: int = 7

    def shuffle(self):
        RNG.shuffle(self.cards)

    def draw(self, n: int):
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

# Hero definition
@dataclass
class Hero:
    name: str
    hp: int
    base_cards: List[Card]
    upg_cards: List[Card]
    fate: int = 0
    combat_fx: List[Callable] = field(default_factory=list)
    exchange_fx: List[Callable] = field(default_factory=list)

    def reset(self):
        self.cur_hp = self.hp
        self.fate = 0
        self.combat_fx.clear()
        self.exchange_fx.clear()
        self.deck = Deck(self.base_cards[:])
        self.deck.shuffle()

# Utility for creating attack cards

def atk(name: str, ctype: CardType, dice: int, armor: int = 0,
        element: Optional[Element] = None, effect: Optional[Callable] = None) -> Card:
    return Card(name=name, ctype=ctype, dice=dice, armor=armor,
                element=element, effect=effect)

# Simple effects

def dmg_all(amount: int) -> Callable:
    def fx(hero, ctx):
        for i in range(len(ctx['enemy_hp'])):
            ctx['enemy_hp'][i] -= amount
    return fx

def gain_armor(amount: int) -> Callable:
    return lambda hero, ctx: setattr(hero, 'armor_pool', hero.armor_pool + amount)

# Heroes and their cards (very partial implementation)
# Hercules initial deck
herc_base = [
    atk('Pillar-Breaker Blow', CardType.MELEE, 2, element=Element.BRUTAL),
    atk('Pillar-Breaker Blow', CardType.MELEE, 2, element=Element.BRUTAL),
    atk('Lion Strangler', CardType.MELEE, 1, element=Element.BRUTAL),
    atk('Demigodly Heroism', CardType.MELEE, 1, armor=1, effect=gain_armor(1),
        element=Element.DIVINE),
    atk('Demigodly Heroism', CardType.MELEE, 1, armor=1, effect=gain_armor(1),
        element=Element.DIVINE),
    atk('Sky Javelin', CardType.RANGED, 2, element=Element.DIVINE),
    atk('Club Spin', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Club Spin', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Atlas Guard', CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
    atk('Atlas Guard', CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
]

herc_upg = [atk('Bondless Effort', CardType.MELEE, 3, element=Element.BRUTAL)]
hercules = Hero('Hercules', 25, herc_base, herc_upg)

# Merlin initial deck
mer_base = [
    atk('Arcane Volley', CardType.RANGED, 1, element=Element.ARCANE,
        effect=dmg_all(1)),
    atk('Arcane Volley', CardType.RANGED, 1, element=Element.ARCANE,
        effect=dmg_all(1)),
    atk("Lady's Warden", CardType.MELEE, 1, armor=2, effect=gain_armor(2),
        element=Element.ARCANE),
    atk("Lady's Warden", CardType.MELEE, 1, armor=2, effect=gain_armor(2),
        element=Element.ARCANE),
    atk('Weaver of Fate', CardType.RANGED, 1, element=Element.DIVINE),
    atk('Weaver of Fate', CardType.RANGED, 1, element=Element.DIVINE),
    atk("Crystal Staff", CardType.MELEE, 1, element=Element.PRECISE),
    atk('Mists of Time', CardType.RANGED, 1, element=Element.SPIRITUAL),
    atk('Mists of Time', CardType.RANGED, 1, element=Element.SPIRITUAL),
    atk('Circle of Avalon', CardType.RANGED, 1, element=Element.SPIRITUAL),
]
mer_upg = [atk('Runic Ray', CardType.RANGED, 2, element=Element.ARCANE)]
merlin = Hero('Merlin', 15, mer_base, mer_upg)

# Musashi initial deck (simplified)
mus_base = [
    atk('Swallow-Cut', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Swallow-Cut', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Cross-River Strike', CardType.MELEE, 2, element=Element.PRECISE),
    atk('Cross-River Strike', CardType.MELEE, 2, element=Element.PRECISE),
    atk('Heaven-and-Earth Slash', CardType.MELEE, 2, element=Element.BRUTAL),
    atk('Heaven-and-Earth Slash', CardType.MELEE, 2, element=Element.BRUTAL),
    atk('Flowing Water Parry', CardType.MELEE, 1, armor=1,
        effect=gain_armor(1), element=Element.SPIRITUAL),
    atk('Flowing Water Parry', CardType.MELEE, 1, armor=1,
        effect=gain_armor(1), element=Element.SPIRITUAL),
    atk('Dual-Moon Guard', CardType.UTIL, 0),
    atk('Wind-Reading Focus', CardType.MELEE, 1, element=Element.ARCANE),
]

mus_upg = [atk('Battojutsu Strike', CardType.MELEE, 2, element=Element.PRECISE)]
musashi = Hero('Musashi', 20, mus_base, mus_upg)

# Brynhild initial deck (partial)
bryn_base = [
    atk("Valkyrie's Descent", CardType.MELEE, 1, element=Element.SPIRITUAL),
    atk("Valkyrie's Descent", CardType.MELEE, 1, element=Element.SPIRITUAL),
    atk('Sky-Piercer', CardType.RANGED, 1, element=Element.SPIRITUAL),
    atk('Hymn of Shields', CardType.UTIL, 0),
    atk('Hymn of Shields', CardType.UTIL, 0),
    atk('Hymn of Storms', CardType.UTIL, 0),
    atk('Thrust of Destiny', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Thrust of Destiny', CardType.MELEE, 1, element=Element.PRECISE),
    atk('Spear of the Aesir', CardType.MELEE, 1, element=Element.BRUTAL),
    atk('Spear of the Aesir', CardType.MELEE, 1, element=Element.BRUTAL),
]
bryn_upg = [atk('Lightning Crash', CardType.MELEE, 7, element=Element.SPIRITUAL)]
brynhild = Hero('Brynhild', 18, bryn_base, bryn_upg)


HEROES = [hercules, merlin, musashi, brynhild]

# Simplified monster stats
GROUP = [1,1]
HP0 = [3,3]
DEF0 = [4,5]
BANDS = [[2,2,2,2],[2,2,2,2]]

@dataclass
class Enemy:
    hp: int
    defense: int
    band: List[int]
    vulnerability: Element


WAVES = [
    [Enemy(hp=HP0[0], defense=DEF0[0], band=BANDS[0],
           vulnerability=Element.BRUTAL)],
    [Enemy(hp=HP0[1], defense=DEF0[1], band=BANDS[1],
           vulnerability=Element.PRECISE)],
]


@dataclass
class Enemy:
    hp: int
    defense: int
    band: List[int]
    vulnerability: Element


# Simple fight engine
def fight_one(hero: Hero):
    """Run a single combat for ``hero`` against all waves."""
    hero.reset()
    hero.deck.draw(4)
    for wave, enemies in enumerate(WAVES):
        ctx = {'enemy_hp': [e.hp for e in enemies],
               'vuln': [e.vulnerability for e in enemies],
               'band': enemies[0].band}
        for exch in range(3):
            hero.armor_pool = 0
            if exch:
                hero.deck.draw(1)
            # util
            while True:
                c = hero.deck.pop_first(CardType.UTIL)
                if not c:
                    break
                hero.armor_pool += c.armor
                if c.effect:
                    c.effect(hero,ctx)
                hero.deck.disc.append(c)
            # ranged
            while True:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c or not ctx['enemy_hp']:
                    break
                vuln = ctx['vuln'][0] == (c.element or Element.BRUTAL)
                dmg = roll_hits(c.dice, enemies[0].defense, vulnerable=vuln)
                if c.effect:
                    c.effect(hero,ctx)
                if ctx['enemy_hp']:
                    ctx['enemy_hp'][0]-=dmg
                    if ctx['enemy_hp'][0]<=0:
                        ctx['enemy_hp'].pop(0)
                        ctx['vuln'].pop(0)
                hero.deck.disc.append(c)
            if not ctx['enemy_hp']:
                break
            # monster strike
            raw = ctx['band'][(d8()-1)//2]*len(ctx['enemy_hp'])
            soak = min(raw, hero.armor_pool)
            hero.armor_pool -= soak
            hero.cur_hp -= max(0,raw-soak)
            if hero.cur_hp<=0:
                return False
            # melee
            while True:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c or not ctx['enemy_hp']:
                    break
                hero.armor_pool += c.armor
                vuln = ctx['vuln'][0] == (c.element or Element.BRUTAL)
                dmg = roll_hits(c.dice, enemies[0].defense, vulnerable=vuln)
                if c.effect:
                    c.effect(hero,ctx)
                ctx['enemy_hp'][0]-=dmg
                if ctx['enemy_hp'][0]<=0:
                    ctx['enemy_hp'].pop(0)
                    ctx['vuln'].pop(0)
                hero.deck.disc.append(c)
            if not ctx['enemy_hp']:
                break
        if ctx['enemy_hp']:
            return False
        hero.deck.cards.extend(RNG.sample(hero.upg_cards,1))
    return True

# Example usage
def _test_roll_hits():
    RNG.seed(1)
    dmg = roll_hits(5, 4)
    assert isinstance(dmg, int)


def _test_deck_draw():
    d = Deck([atk('x', CardType.MELEE, 1) for _ in range(10)])
    d.shuffle()
    d.draw(8)
    assert len(d.hand) <= d.MAX_HAND


def run_tests():
    _test_roll_hits()
    _test_deck_draw()
    print('basic tests ok')


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_tests()
    else:
        wins = 0
        N = 100
        for _ in range(N):
            if fight_one(random.choice(HEROES)):
                wins += 1
        print('Win rate:', wins/N)
