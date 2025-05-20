#!/usr/bin/env python3
"""Simplified board game simulator demonstrating card effects and monster
abilities. Not a full implementation of the board game rules but shows how
heroes, fate, vulnerability, and a few special effects interact.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Callable, Optional, Dict, Any, Tuple

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
    hymn: bool = False
    multi: bool = False  # attack targets all enemies


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

FATE_MAX = 10

def roll_hits(
    num_dice: int,
    defense: int,
    mod: int = 0,
    *,
    hero: Optional["Hero"] = None,
    element: "Element" = None,
    vulnerability: "Element" = None,
    enemy: Optional["Enemy"] = None,
    card: Optional[Card] = None,
    ctx: Optional[Dict] = None,
) -> int:
    """Roll ``num_dice`` d8 and count hits against ``defense``.

    Dice that match ``vulnerability`` deal double damage. If ``hero`` is
    supplied, allow rerolls by spending Fate when below the defense threshold.
    Heroes only spend Fate while above 3 points (or 5 for Brynhild).
    """
    dmg = 0
    low = False
    for _ in range(num_dice):
        r = d8()
        # Denied Heaven forces rerolling 8s
        if enemy and enemy.traits.get("ability") == "denied-heaven":
            while r == 8:
                r = d8()
        r = max(1, min(8, r + mod))
        # Aerial Combat penalises melee hits
        if (
            enemy
            and enemy.traits.get("ability") == "aerial-combat"
            and card is not None
            and card.ctype == CardType.MELEE
        ):
            r = max(1, r - 1)
        # hero fate rerolls unless forbidden
        while (
            hero is not None
            and r < defense
            and not (ctx and ctx.get("no_reroll"))
            and hero.fate > (5 if hero.name == "Brynhild" else 3)
            and hero.spend_fate(1)
        ):
            r = d8()
            if enemy and enemy.traits.get("ability") == "denied-heaven":
                while r == 8:
                    r = d8()
            r = max(1, min(8, r + mod))
            if (
                enemy
                and enemy.traits.get("ability") == "aerial-combat"
                and card is not None
                and card.ctype == CardType.MELEE
            ):
                r = max(1, r - 1)
        if r <= 2:
            low = True
        if r >= defense:
            hit = 2 if r == 8 else 1
            if element is not None and element == vulnerability:
                hit *= 2
            dmg += hit
    if ctx is not None:
        if enemy and enemy.traits.get("ability") == "curse-of-torment" and low:
            ctx["torment"] = ctx.get("torment", 0) + 1
        if enemy and enemy.traits.get("ability") == "roots-of-despair" and dmg == 0:
            ctx["roots"] = ctx.get("roots", 0) + 1
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
        self.combat_effects: List[Tuple[Callable[["Hero", Dict], None], Card]] = []
        self.exchange_effects: List[Tuple[Callable[["Hero", Dict], None], Card]] = []
        self.active_hymns: List[Card] = []
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
    if ctx.get("current_target") is not None and ctx["enemies"]:
        ctx["enemies"][0].hp -= 1
        if ctx["enemies"][0].hp <= 0:
            ctx["enemies"].pop(0)

# [Exchange] +1 damage to other attacks

def sky_javelin_fx(hero: Hero, ctx: Dict) -> None:
    ctx["dmg_bonus"] = ctx.get("dmg_bonus", 0) + 1

# Remove all active Hymn effects
def end_hymns_fx(hero: Hero, ctx: Dict) -> None:
    hero.active_hymns.clear()
    hero.combat_effects = [ef for ef in hero.combat_effects if not ef[1].hymn]
    hero.exchange_effects = [ef for ef in hero.exchange_effects if not ef[1].hymn]

# Card constructor

def atk(
    name: str,
    ctype: CardType,
    dice: int,
    element: Element = Element.NONE,
    armor: int = 0,
    effect: Optional[Callable[[Hero, Dict], None]] = None,
    persistent: Optional[str] = None,
    hymn: bool = False,
    multi: bool = False,
) -> Card:
    return Card(name, ctype, dice, element, armor, effect, persistent, hymn, multi)

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
    atk("Spin", CardType.MELEE, 1, Element.PRECISE, multi=True),
    atk("Spin", CardType.MELEE, 1, Element.PRECISE, multi=True),
    atk("Atlas", CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
    atk("Atlas", CardType.UTIL, 0, armor=3, effect=gain_armor(3)),
]
hercules = Hero("Hercules", 25, herc_base, [])

mer_base = [
    atk("Volley", CardType.RANGED, 1, Element.ARCANE, multi=True),
    atk("Volley", CardType.RANGED, 1, Element.ARCANE, multi=True),
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
    atk("Cross", CardType.MELEE, 2, Element.PRECISE, multi=True),
    atk("Cross", CardType.MELEE, 2, Element.PRECISE, multi=True),
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
    atk("Shields", CardType.UTIL, 0, hymn=True, persistent="combat"),
    atk("Shields", CardType.UTIL, 0, hymn=True, persistent="combat"),
    atk("Storms", CardType.UTIL, 0, effect=end_hymns_fx),
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
    ability: Optional[str] = None


@dataclass
class Enemy:
    """Instance of a monster encountered in combat."""

    hp: int
    defense: int
    vulnerability: Element
    traits: Dict[str, Any] = field(default_factory=dict)

def make_wave(enemy: EnemyType, count: int) -> Dict:
    monsters = [
        Enemy(
            hp=enemy.hp,
            defense=enemy.defense,
            vulnerability=enemy.vulnerability,
            traits={"name": enemy.name, "ability": enemy.ability},
        )
        for _ in range(count)
    ]
    return {"enemies": monsters, "enemy_type": enemy}

BASIC_WAVES = [
    (
        EnemyType("Spinner", 1, 4, [1,0,1,0], Element.SPIRITUAL, ability="web-slinger"),
        3,
    ),
    (
        EnemyType("Soldier", 2, 5, [1,1,1,2], Element.PRECISE, ability="dark-phalanx"),
        3,
    ),
    (
        EnemyType("Banshee", 4, 5, [0,0,1,3], Element.DIVINE, ability="banshee-wail"),
        2,
    ),
    (
        EnemyType("Priest", 2, 3, [0,0,1,1], Element.ARCANE, ability="power-of-death"),
        3,
    ),
    (
        EnemyType("Dryad", 2, 4, [0,0,1,1], Element.BRUTAL, ability="cursed-thorns"),
        3,
    ),
    (
        EnemyType("Minotaur", 4, 3, [0,0,1,3], Element.PRECISE, ability="cleaving"),
        2,
    ),
    (
        EnemyType("Wizard", 2, 3, [0,1,1,3], Element.BRUTAL, ability="curse-of-torment"),
        2,
    ),
    (
        EnemyType("Shadow Banshee", 3, 5, [0,0,1,2], Element.DIVINE, ability="ghostly"),
        2,
    ),
    (
        EnemyType("Gryphon", 4, 5, [0,1,3,4], Element.SPIRITUAL, ability="aerial-combat"),
        1,
    ),
    (
        EnemyType("Treant", 7, 6, [0,1,1,4], Element.DIVINE, ability="power-sap"),
        1,
    ),
    (
        EnemyType("Angel", 5, 5, [0,1,2,5], Element.ARCANE, ability="corrupted-destiny"),
        1,
    ),
    (
        EnemyType("Elite Spinner", 2, 5, [0,0,1,4], Element.SPIRITUAL, ability="sticky-web"),
        3,
    ),
    (
        EnemyType("Elite Soldier", 3, 6, [0,0,1,3], Element.PRECISE, ability="spiked-armor"),
        3,
    ),
    (
        EnemyType("Elite Priest", 3, 4, [0,0,1,2], Element.ARCANE, ability="silence"),
        3,
    ),
    (
        EnemyType("Elite Dryad", 2, 5, [0,1,1,2], Element.BRUTAL, ability="disturbed-flow"),
        3,
    ),
    (
        EnemyType("Elite Minotaur", 5, 3, [0,0,2,4], Element.PRECISE, ability="enrage"),
        2,
    ),
    (
        EnemyType("Elite Wizard", 2, 4, [0,2,2,3], Element.BRUTAL, ability="void-barrier"),
        2,
    ),
    (
        EnemyType("Elite Banshee", 4, 5, [0,0,1,3], Element.DIVINE, ability="banshee-wail"),
        2,
    ),
    (
        EnemyType("Elite Gryphon", 5, 5, [0,2,4,6], Element.SPIRITUAL, ability="ephemeral-wings"),
        1,
    ),
    (
        EnemyType("Elite Treant", 8, 7, [0,1,3,5], Element.DIVINE, ability="roots-of-despair"),
        1,
    ),
    (
        EnemyType("Elite Angel", 7, 6, [0,3,3,6], Element.ARCANE, ability="denied-heaven"),
        1,
    ),
]

def apply_persistent(hero: Hero, ctx: Dict) -> None:
    for fx, _ in hero.combat_effects:
        fx(hero, ctx)
    for fx, _ in hero.exchange_effects:
        fx(hero, ctx)

def resolve_attack(hero: Hero, card: Card, ctx: Dict) -> None:
    dmg_bonus = ctx.get("dmg_bonus", 0)
    if not ctx["enemies"]:
        return
    targets = ctx["enemies"][:] if card.multi else [ctx["enemies"][0]]
    for e in targets[:]:
        dmg = roll_hits(
            card.dice,
            e.defense,
            hero=hero,
            element=card.element,
            vulnerability=e.vulnerability,
            enemy=e,
            card=card,
            ctx=ctx,
        ) + dmg_bonus
        if card.multi and e.traits.get("ability") == "dark-phalanx" and sum(1 for m in ctx["enemies"] if m.traits.get("ability") == "dark-phalanx") >= 2:
            dmg = max(1, dmg - 1)
        # apply void barrier armor
        if e.traits.get("ability") == "void-barrier":
            elems = e.traits.setdefault("vb_elems", set())
            if card.element != Element.NONE and card.element not in elems:
                elems.add(card.element)
                e.traits["vb_armor"] = e.traits.get("vb_armor", 0) + 1
            soak = min(e.traits.get("vb_armor", 0), dmg)
            e.traits["vb_armor"] = e.traits.get("vb_armor", 0) - soak
            dmg -= soak
        if ctx.get("gryphon_nullify") and e.traits.get("ability") == "ephemeral-wings":
            ctx["gryphon_nullify"] = False
            dmg = 0
        if dmg > 0 and e.traits.get("ability") == "ephemeral-wings":
            ctx["gryphon_nullify"] = True
        if e.traits.get("ability") == "banshee-wail":
            ctx["banshee_dice"] = ctx.get("banshee_dice", 0) + card.dice
        e.hp -= dmg
        if dmg >= 3 and e.traits.get("ability") == "spiked-armor":
            hero.hp -= 1
        if e.hp <= 0:
            if e.traits.get("ability") == "power-of-death":
                ctx["priests_dead"] = ctx.get("priests_dead", 0) + 1
            ctx["enemies"].remove(e)
    if card.effect:
        ctx["current_target"] = ctx["enemies"][0] if ctx["enemies"] else None
        card.effect(hero, ctx)


def monster_attack(hero: Hero, ctx: Dict) -> None:
    band = ctx["enemy_type"].bands
    total = 0
    for e in ctx["enemies"]:
        dmg = band[(d8()-1)//2]
        if e.traits.get("ability") == "power-of-death":
            dmg += ctx.get("priests_dead", 0)
        total += dmg
    mult = 2 if any(e.traits.get("ability") == "enrage" and e.traits.get("enraged") for e in ctx["enemies"]) else 1
    for _ in range(mult):
        raw = total
        soak = min(hero.armor_pool, raw)
        hero.armor_pool -= soak
        hero.hp -= max(0, raw - soak)

def fight_one(hero: Hero) -> bool:
    hero.reset()
    hero.deck.draw(RNG.choice([3, 4]))
    for enemy, count in BASIC_WAVES:
        ctx = make_wave(enemy, count)
        ctx['banshee_dice'] = 0
        ctx['priests_dead'] = 0
        for exch in range(3):
            hero.exchange_effects.clear()
            hero.armor_pool = 0
            if exch:
                draw = 1
                if ctx['enemy_type'].ability == 'sticky-web':
                    draw = max(0, draw - 1)
                hero.deck.draw(draw)
            if any(e.traits.get('ability') == 'corrupted-destiny' for e in ctx['enemies']):
                hero.fate = max(0, hero.fate - 2)
            if exch == 3 and any(e.traits.get('ability') == 'ghostly' for e in ctx['enemies']):
                ctx['enemies'].clear()
                break
            for e in ctx['enemies']:
                if e.traits.get('ability') == 'void-barrier':
                    e.traits['vb_armor'] = 0
                    e.traits['vb_elems'] = set()
                if e.traits.get('ability') == 'enrage' and e.hp <= 3:
                    e.traits['enraged'] = True
            ctx['no_reroll'] = any(e.traits.get('ability') == 'disturbed-flow' for e in ctx['enemies'])
            ctx.pop("dmg_bonus", None)
            apply_persistent(hero, ctx)
            while True:
                c = hero.deck.pop_first(CardType.UTIL)
                if not c:
                    break
                hero.armor_pool += c.armor
                if c.effect:
                    c.effect(hero, ctx)
                if c.persistent and c.effect and ctx["enemy_type"].ability != "silence":
                    if c.persistent == "combat":
                        hero.combat_effects.append((c.effect, c))
                    elif c.persistent == "exchange":
                        hero.exchange_effects.append((c.effect, c))
                if c.hymn:
                    hero.active_hymns.append(c)
                hero.deck.disc.append(c)
            delayed_ranged: List[Card] = []
            while ctx["enemies"]:
                c = hero.deck.pop_first(CardType.RANGED)
                if not c:
                    break
                if ctx["enemy_type"].ability == "web-slinger":
                    delayed_ranged.append(c)
                    continue
                resolve_attack(hero, c, ctx)
                if c.persistent and c.effect and ctx["enemy_type"].ability != "silence":
                    if c.persistent == "combat":
                        hero.combat_effects.append((c.effect, c))
                    elif c.persistent == "exchange":
                        hero.exchange_effects.append((c.effect, c))
                if c.hymn:
                    hero.active_hymns.append(c)
                hero.deck.disc.append(c)
            if not ctx["enemies"]:
                break
            monster_attack(hero, ctx)
            if hero.hp <= 0:
                return False
            # delayed ranged attacks are executed now if web slinger was active
            for c in delayed_ranged:
                if not ctx["enemies"]:
                    break
                resolve_attack(hero, c, ctx)
                if c.hymn:
                    hero.active_hymns.append(c)
                hero.deck.disc.append(c)
            delayed_ranged.clear()
            while ctx["enemies"]:
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                resolve_attack(hero, c, ctx)
                if c.persistent and c.effect and ctx["enemy_type"].ability != "silence":
                    if c.persistent == "combat":
                        hero.combat_effects.append((c.effect, c))
                    elif c.persistent == "exchange":
                        hero.exchange_effects.append((c.effect, c))
                if c.hymn:
                    hero.active_hymns.append(c)
                hero.deck.disc.append(c)
            if not ctx["enemies"]:
                break
            if ctx.get("torment"):
                hero.hp -= ctx.pop("torment")
                if hero.hp <= 0:
                    return False
            if ctx.get("roots"):
                hero.hp -= ctx.pop("roots")
                if hero.hp <= 0:
                    return False
            if (
                ctx["enemy_type"].ability == "banshee-wail"
                and ctx.get("banshee_dice", 0) >= 3
            ):
                hero.hp -= ctx["banshee_dice"] // 3
                ctx["banshee_dice"] = 0
                if hero.hp <= 0:
                    return False
            if ctx["enemy_type"].ability == "cursed-thorns" and hero.armor_pool > 0:
                hero.hp -= hero.armor_pool
                hero.armor_pool = 0
                if hero.hp <= 0:
                    return False
            if ctx["enemy_type"].ability == "power-sap" and hero.combat_effects:
                hero.combat_effects.pop(RNG.randrange(len(hero.combat_effects)))
                for e in ctx["enemies"]:
                    if e.traits.get("ability") == "power-sap":
                        e.hp += 1
                        break
            for e in ctx["enemies"]:
                if e.traits.get("ability") == "void-barrier":
                    e.traits["vb_armor"] = 0
                    e.traits["vb_elems"] = set()
        if ctx["enemies"] or hero.hp <= 0:
            return False
        hero.gain_fate(1)
        # gain upgrades placeholder
        hero.combat_effects.clear()
        hero.exchange_effects.clear()
        hero.active_hymns.clear()
    return True

if __name__ == "__main__":
    N = 20
    wins = sum(fight_one(random.choice(HEROES)) for _ in range(N))
    print("Win rate", wins/N)
