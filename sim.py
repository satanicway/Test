#!/usr/bin/env python3
"""Simplified board game simulator with updated heroes and cards."""

import random
from dataclasses import dataclass, field
from typing import List, Callable, Optional

# Dice helper
RNG = random.Random()
d8 = lambda: RNG.randint(1, 8)

def roll_hits(num_dice: int, defense: int, mod: int = 0) -> int:
    dmg = 0
    for _ in range(num_dice):
        r = max(1, min(8, d8() + mod))
        if r >= defense:
            dmg += 2 if r == 8 else 1
    return dmg

# Card and deck definitions
@dataclass
class Card:
    name: str
    ctype: str
    dice: int = 0
    armor: int = 0
    effect: Optional[Callable] = None

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)

    def shuffle(self):
        RNG.shuffle(self.cards)

    def draw(self, n: int):
        for _ in range(n):
            if not self.cards:
                RNG.shuffle(self.disc)
                self.cards, self.disc = self.disc, []
                if not self.cards:
                    break
            self.hand.append(self.cards.pop())

    def pop_first(self, ctype: str) -> Optional[Card]:
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

    def reset(self):
        self.cur_hp = self.hp
        self.deck = Deck(self.base_cards[:])
        self.deck.shuffle()

# Utility for creating attack cards

def atk(name, ctype, dice, armor=0, effect=None):
    return Card(name=name, ctype=ctype, dice=dice, armor=armor, effect=effect)

# Simple effects

def dmg_all(amount: int) -> Callable:
    def fx(hero, ctx):
        for i in range(len(ctx['enemy_hp'])):
            ctx['enemy_hp'][i] -= amount
    return fx

def gain_armor(amount: int) -> Callable:
    def fx(hero, ctx):
        hero.armor_pool += amount
    return fx

# Heroes and their cards (very partial implementation)
# Hercules initial deck
herc_base = [
    atk('Pillar-Breaker Blow', 'Melee', 2),
    atk('Pillar-Breaker Blow', 'Melee', 2),
    atk('Lion Strangler', 'Melee', 1),
    atk('Demigodly Heroism', 'Melee', 1, armor=1, effect=gain_armor(1)),
    atk('Demigodly Heroism', 'Melee', 1, armor=1, effect=gain_armor(1)),
    atk('Sky Javelin', 'Ranged', 2),
    atk('Club Spin', 'Melee', 1),
    atk('Club Spin', 'Melee', 1),
    atk('Atlas Guard', 'Util', 0, armor=3, effect=gain_armor(3)),
    atk('Atlas Guard', 'Util', 0, armor=3, effect=gain_armor(3)),
]

herc_upg = [atk('Bondless Effort', 'Melee', 3)]
hercules = Hero('Hercules', 25, herc_base, herc_upg)

# Merlin initial deck
mer_base = [
    atk('Arcane Volley', 'Ranged', 1, effect=dmg_all(1)),
    atk('Arcane Volley', 'Ranged', 1, effect=dmg_all(1)),
    atk('Lady\'s Warden', 'Melee', 1, armor=2, effect=gain_armor(2)),
    atk('Lady\'s Warden', 'Melee', 1, armor=2, effect=gain_armor(2)),
    atk('Weaver of Fate', 'Ranged', 1),
    atk('Weaver of Fate', 'Ranged', 1),
    atk('Crystal Staff', 'Melee', 1),
    atk('Mists of Time', 'Ranged', 1),
    atk('Mists of Time', 'Ranged', 1),
    atk('Circle of Avalon', 'Ranged', 1),
]
mer_upg = [atk('Runic Ray', 'Ranged', 2)]
merlin = Hero('Merlin', 15, mer_base, mer_upg)

# Musashi initial deck (simplified)
mus_base = [
    atk('Swallow-Cut', 'Melee', 1),
    atk('Swallow-Cut', 'Melee', 1),
    atk('Cross-River Strike', 'Melee', 2),
    atk('Cross-River Strike', 'Melee', 2),
    atk('Heaven-and-Earth Slash', 'Melee', 2),
    atk('Heaven-and-Earth Slash', 'Melee', 2),
    atk('Flowing Water Parry', 'Melee', 1, armor=1, effect=gain_armor(1)),
    atk('Flowing Water Parry', 'Melee', 1, armor=1, effect=gain_armor(1)),
    atk('Dual-Moon Guard', 'Util', 0),
    atk('Wind-Reading Focus', 'Melee', 1),
]

mus_upg = [atk('Battojutsu Strike', 'Melee', 2)]
musashi = Hero('Musashi', 20, mus_base, mus_upg)

# Brynhild initial deck (partial)
bryn_base = [
    atk("Valkyrie's Descent", 'Melee', 1),
    atk("Valkyrie's Descent", 'Melee', 1),
    atk('Sky-Piercer', 'Ranged', 1),
    atk('Hymn of Shields', 'Util', 0),
    atk('Hymn of Shields', 'Util', 0),
    atk('Hymn of Storms', 'Util', 0),
    atk('Thrust of Destiny', 'Melee', 1),
    atk('Thrust of Destiny', 'Melee', 1),
    atk('Spear of the Aesir', 'Melee', 1),
    atk('Spear of the Aesir', 'Melee', 1),
]
bryn_upg = [atk('Lightning Crash', 'Melee', 7)]
brynhild = Hero('Brynhild', 18, bryn_base, bryn_upg)

HEROES = [hercules, merlin, musashi, brynhild]

# Simplified monster stats
GROUP = [1,1]
HP0 = [3,3]
DEF0 = [4,5]
BANDS = [[2,2,2,2],[2,2,2,2]]

# Simple fight engine
def fight_one(hero: Hero):
    hero.reset()
    hero.deck.draw(4)
    for wave,(g,hp,df,band) in enumerate(zip(GROUP,HP0,DEF0,BANDS)):
        ctx = {'enemy_hp':[hp]*g}
        for exch in range(3):
            hero.armor_pool = 0
            if exch:
                hero.deck.draw(1)
            # util
            while True:
                c = hero.deck.pop_first('Util')
                if not c:
                    break
                hero.armor_pool += c.armor
                if c.effect:
                    c.effect(hero,ctx)
                hero.deck.disc.append(c)
            # ranged
            while True:
                c = hero.deck.pop_first('Ranged')
                if not c or not ctx['enemy_hp']:
                    break
                dmg = roll_hits(c.dice, df)
                if c.effect:
                    c.effect(hero,ctx)
                if ctx['enemy_hp']:
                    ctx['enemy_hp'][0]-=dmg
                    if ctx['enemy_hp'][0]<=0:
                        ctx['enemy_hp'].pop(0)
                hero.deck.disc.append(c)
            if not ctx['enemy_hp']:
                break
            # monster strike
            raw = band[(d8()-1)//2]*len(ctx['enemy_hp'])
            soak = min(raw, hero.armor_pool)
            hero.armor_pool -= soak
            hero.cur_hp -= max(0,raw-soak)
            if hero.cur_hp<=0:
                return False
            # melee
            while True:
                c = hero.deck.pop_first('Melee')
                if not c or not ctx['enemy_hp']:
                    break
                hero.armor_pool += c.armor
                dmg = roll_hits(c.dice, df)
                if c.effect:
                    c.effect(hero,ctx)
                ctx['enemy_hp'][0]-=dmg
                if ctx['enemy_hp'][0]<=0:
                    ctx['enemy_hp'].pop(0)
                hero.deck.disc.append(c)
            if not ctx['enemy_hp']:
                break
        if ctx['enemy_hp']:
            return False
        hero.deck.cards.extend(RNG.sample(hero.upg_cards,1))
    return True

# Example usage
if __name__ == '__main__':
    wins = 0
    N = 100
    for _ in range(N):
        if fight_one(random.choice(HEROES)):
            wins += 1
    print('Win rate:', wins/N)
