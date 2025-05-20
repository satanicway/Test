#!/usr/bin/env python3
"""Hercules card implementation and simple combat simulation."""
import random
from dataclasses import dataclass, field
from typing import List, Callable, Dict

RNG = random.Random()
d8 = lambda: RNG.randint(1,8)

# ------------------------------------------------------------------
# Utility helpers
# ------------------------------------------------------------------
def roll_hits(dice: int, defense: int, mod: int=0, rerolls: int=0) -> int:
    dmg = 0
    for _ in range(dice):
        r = max(1, min(8, d8()+mod))
        # simple reroll logic
        if r < defense and rerolls:
            rerolls -= 1
            r = max(1, min(8, d8()+mod))
        if r >= defense:
            dmg += 2 if r==8 else 1
    return dmg

@dataclass
class Card:
    name: str
    ctype: str
    dice: int=0
    armor: int=0
    effect: Callable[['Hero','Ctx'], None]=lambda h,c: None

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card]=field(default_factory=list)
    disc: List[Card]=field(default_factory=list)

    def shuffle(self):
        RNG.shuffle(self.cards)

    def draw(self,n:int):
        for _ in range(n):
            if not self.cards:
                RNG.shuffle(self.disc)
                self.cards,self.disc = self.disc,[]
                if not self.cards:
                    break
            self.hand.append(self.cards.pop())

    def pop_first(self,ctype:str):
        for i,c in enumerate(self.hand):
            if c.ctype==ctype:
                return self.hand.pop(i)
        return None

class Ctx(Dict):
    pass

@dataclass
class Hero:
    name: str
    hp: int
    base: List[Card]
    upg: List[Card]
    def reset(self):
        self.cur_hp=self.hp
        self.fate=0
        self.deck=Deck(self.base[:])
        self.deck.shuffle()
        self.armor_pool=0

# ------------------------------------------------------------------
# Hercules card effects
# ------------------------------------------------------------------

def fx_lion_strangler(h:Hero, ctx:Ctx):
    ctx['bleed']=ctx.get('bleed',0)+1

def fx_demigod(h:Hero,ctx:Ctx):
    h.armor_pool+=1

def fx_sky_javelin(h:Hero,ctx:Ctx):
    ctx['ex_dmg']=ctx.get('ex_dmg',0)+1

def fx_horde_bleed(h:Hero,ctx:Ctx):
    ctx['death_splash']=2

def fx_reroll_one(h:Hero,ctx:Ctx):
    ctx['reroll']=1

def fx_strength_from_anger(h:Hero,ctx:Ctx):
    ctx['cb_dmg']=ctx.get('cb_dmg',0)+1

def fx_chiron_training(h:Hero,ctx:Ctx):
    ctx['armor_per_attack']=ctx.get('armor_per_attack',0)+1

def fx_armor2(h:Hero,ctx:Ctx):
    h.armor_pool+=2

def fx_piercing_spear(h:Hero,ctx:Ctx):
    ctx['def_mod']=ctx.get('def_mod',0)-1

def fx_bone_whirl(h:Hero,ctx:Ctx):
    ctx['def_mod']=ctx.get('def_mod',0)-1

# map names to effects for brevity
herc_effects = {
    'Lion Strangler': fx_lion_strangler,
    'Demigodly Heroism': fx_demigod,
    'Sky Javelin': fx_sky_javelin,
    'Horde Breaker': fx_horde_bleed,
    'Guided By The Gods': fx_reroll_one,
    'Strength from Anger': fx_strength_from_anger,
    'Chiron\'s Training': fx_chiron_training,
    'Enduring Wave': fx_armor2,
    'Piercing Spear': fx_piercing_spear,
    'Bone\u2011Splinter Whirl': fx_bone_whirl,
}

# ------------------------------------------------------------------
# Hercules cards
# ------------------------------------------------------------------
herc_base = [
    Card('Pillar-Breaker Blow','Melee',2),
    Card('Pillar-Breaker Blow','Melee',2),
    Card('Lion Strangler','Melee',1,effect=herc_effects['Lion Strangler']),
    Card('Demigodly Heroism','Melee',1,armor=1,effect=herc_effects['Demigodly Heroism']),
    Card('Demigodly Heroism','Melee',1,armor=1,effect=herc_effects['Demigodly Heroism']),
    Card('Sky Javelin','Ranged',2,effect=herc_effects['Sky Javelin']),
    Card('Club Spin','Melee',1),
    Card('Club Spin','Melee',1),
    Card('Atlas Guard','Util',0,armor=3),
    Card('Atlas Guard','Util',0,armor=3),
]

# upgrade pool
upg_common = [
    Card('Bondless Effort','Melee',3),
    Card('Colossus Smash','Melee',3,armor=1),
    Card('Olympian Call','Melee',1,effect=fx_reroll_one),
    Card('Divine Resilience','Melee',1,armor=1),
    Card('Horde Breaker','Melee',2,effect=fx_horde_bleed),
    Card('Disorienting Blow','Melee',2),
    Card('Piercing Spear','Ranged',2,effect=fx_piercing_spear),
    Card('Fated War','Melee',2,effect=lambda h,c: h.__setattr__('fate',min(10,h.fate+len(c['enemy_hp'])))),
    Card("Fortune's Throw",'Ranged',2,armor=2,effect=lambda h,c: None),
]
upg_uncommon=[
    Card('Pain Strike','Melee',4),
    Card('Fortifying Attack','Melee',3),
    Card('Bone\u2011Splinter Whirl','Melee',3,effect=fx_bone_whirl),
    Card('Glorious Uproar','Melee',1),
    Card('Guided By The Gods','Melee',1,effect=fx_reroll_one),
    Card("Chiron's Training",'Melee',1,effect=fx_chiron_training),
    Card("Once Isn't Enough",'Melee',1),
    Card('Strength from Anger','Melee',1,effect=fx_strength_from_anger),
    Card('Enduring Wave','Melee',2,armor=2,effect=fx_armor2),
]
upg_rare=[
    Card("Zeus' Wrath",'Melee',4),
    Card("Ares' Will",'Melee',1,effect=lambda h,c: c.__setitem__('bleed',2)),
    Card('True Might of Hercules','Melee',8),
    Card("Athena's Guidance",'Melee',1),
    Card("Apollo's Sunburst",'Ranged',3),
    Card("Nike's Desire",'Melee',1),
    Card('Blessing of Hephaestus','Ranged',0,armor=5),
    Card("Hermes' Delivery",'Melee',3),
    Card("Eris' Pandemonium",'Melee',0),
]
herc_upg = upg_common*3 + [c for c in upg_uncommon for _ in range(2)] + upg_rare
hercules = Hero('Hercules',25,herc_base,herc_upg)

HEROES=[hercules]

# ------------------------------------------------------------------
# Combat engine (simplified for demo)
# ------------------------------------------------------------------
GROUP=[1,1]
HP0=[3,3]
DEF0=[4,5]
BANDS=[[2,2,2,2],[2,2,2,2]]


def apply_damage(ctx:Ctx, dmg:int, target:int=0, all_targets:bool=False):
    if all_targets:
        for i in range(len(ctx['enemy_hp'])):
            ctx['enemy_hp'][i]-=dmg
        ctx['enemy_hp']=[hp for hp in ctx['enemy_hp'] if hp>0]
    else:
        if ctx['enemy_hp']:
            ctx['enemy_hp'][target]-=dmg
            if ctx['enemy_hp'][target]<=0:
                ctx['enemy_hp'].pop(target)


def attack_card(hero:Hero, card:Card, ctx:Ctx):
    # compute rerolls
    rer=ctx.get('reroll',0)
    dmg=roll_hits(card.dice, ctx['def']+ctx.get('def_mod',0), rerolls=rer)
    dmg+=ctx.get('cb_dmg',0)+ctx.get('ex_dmg',0)
    if card.name=='Club Spin':
        apply_damage(ctx,dmg,all_targets=True)
    elif card.name in ('Fated War','Enduring Wave','Bone\u2011Splinter Whirl','Zeus\' Wrath','Apollo\'s Sunburst'):
        apply_damage(ctx,dmg,all_targets=True)
    else:
        apply_damage(ctx,dmg)
    if ctx.get('bleed') and ctx['enemy_hp']:
        ctx['enemy_hp'][0]-=ctx['bleed']
        if ctx['enemy_hp'][0]<=0:
            ctx['enemy_hp'].pop(0)
    if card.effect:
        card.effect(hero,ctx)


def fight_one(hero:Hero):
    hero.reset()
    hero.deck.draw(4)
    for g,hp,df,band in zip(GROUP,HP0,DEF0,BANDS):
        ctx=Ctx({'enemy_hp':[hp]*g,'def':df})
        for exch in range(3):
            hero.armor_pool=0
            ctx['ex_dmg']=0
            hero.deck.draw(1 if exch else 0)
            # util cards
            while True:
                c=hero.deck.pop_first('Util')
                if not c: break
                hero.armor_pool+=c.armor
                if c.effect: c.effect(hero,ctx)
                hero.deck.disc.append(c)
            # ranged
            while True:
                c=hero.deck.pop_first('Ranged')
                if not c: break
                attack_card(hero,c,ctx)
                hero.deck.disc.append(c)
                if not ctx['enemy_hp']: break
            if not ctx['enemy_hp']: break
            # monster strike
            raw=band[(d8()-1)//2]*len(ctx['enemy_hp'])
            soak=min(raw,hero.armor_pool)
            hero.armor_pool-=soak
            hero.cur_hp-=max(0,raw-soak)
            if hero.cur_hp<=0: return False
            # melee
            while True:
                c=hero.deck.pop_first('Melee')
                if not c: break
                hero.armor_pool+=c.armor
                attack_card(hero,c,ctx)
                hero.deck.disc.append(c)
                if not ctx['enemy_hp']: break
            if not ctx['enemy_hp']: break
        if ctx['enemy_hp']:
            return False
        hero.deck.cards.extend(RNG.sample(hero.upg,1))
    return True

if __name__=='__main__':
    wins=0
    for _ in range(100):
        if fight_one(hercules):
            wins+=1
    print('Win rate:',wins/100)
