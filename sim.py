#!/usr/bin/env python3
"""Minimal board game simulator showing fate, armor, vulnerability and
persistent effects.
This version rewrites the broken previous script with a compact
implementation that still demonstrates the same mechanics."""

from __future__ import annotations
import random
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple, Set

RNG = random.Random()

# ``AUTO_MODE`` remains for backward compatibility but no longer affects
# gameplay because all interactive prompts have been removed.
AUTO_MODE = False

# When ``MIN_DAMAGE`` is ``True`` monsters always inflict at least 1 HP
# of damage after armor so long as the attack dealt positive damage.
MIN_DAMAGE = False

# Each enemy template stores its own damage band so the old per-wave
# ``BANDS`` table is no longer required.  Enemy lookups below provide the
# appropriate values for each wave.

def d8() -> int:
    return RNG.randint(1, 8)

# ---------------------------------------------------------------------------
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
    max_targets: Optional[int] = None
    dmg_per_hymn: int = 0
    pre: bool = False
    before_ranged: bool = False
    hit_mod: int = 0

@dataclass
class Deck:
    cards: List[Card]
    hand: List[Card] = field(default_factory=list)
    disc: List[Card] = field(default_factory=list)
    MAX_HAND: int = 7
    owner: Optional["Hero"] = field(default=None, repr=False)

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
            card = self.cards.pop()
            self.hand.append(card)
            if self.owner is not None and hasattr(self.owner, "combat_record"):
                self.owner.combat_record["drawn"][card.name] += 1

    def pop_first(self, ctype: CardType) -> Optional[Card]:
        for i, c in enumerate(self.hand):
            if c.ctype == ctype:
                return self.hand.pop(i)
        return None

# ---------------------------------------------------------------------------
# Hero and Enemy definitions
# ---------------------------------------------------------------------------
FATE_MAX = 10
ATTACK_DEPTH_LIMIT = 10

@dataclass
class Hero:
    """Playable character with a deck and persistent state.

    ``combat_effects`` and ``exchange_effects`` hold tuples ``(fx, source)``
    for persistent triggers. ``source`` is usually a :class:`Card` but may be
    any object.
    """
    name: str
    max_hp: int
    base_cards: List[Card]
    upg_pool: List[Card] = field(default_factory=list)
    _orig_pool: List[Card] = field(init=False, repr=False)
    card_modifiers: Dict[str, Dict[str, float]] = field(default_factory=dict, repr=False)

    # dynamic state
    fate: int = 0
    armor_pool: int = 0
    deck: Deck = field(init=False)
    combat_effects: List[Tuple[Callable[["Hero", Dict], None], object]] = field(
        default_factory=list
    )  # active for the whole combat; second item may not be a Card
    exchange_effects: List[Tuple[Callable[["Hero", Dict], None], object]] = field(
        default_factory=list
    )  # active for the current exchange only
    active_hymns: List[Card] = field(default_factory=list)
    card_rarity: Dict[str, str] = field(default_factory=dict, repr=False)
    combat_record: Dict[str, Counter] = field(default_factory=lambda: {
        "drawn": Counter(),
        "played": Counter(),
    }, repr=False)

    def __post_init__(self) -> None:
        # store a copy of the original upgrade pool so ``reset`` can
        # restore it for subsequent runs
        self._orig_pool = self.upg_pool[:]
        if self.name in HERO_RARITY_MAPS:
            self.card_rarity = HERO_RARITY_MAPS[self.name]
        else:
            self.card_rarity = {c.name: "base" for c in self.base_cards}
        self.reset()

    def _mod_card(self, card: Card) -> Card:
        """Return a copy of ``card`` applying any configured modifiers."""
        mod = self.card_modifiers.get(card.name)
        dmg = card.dice
        arm = card.armor
        if mod:
            dmg = int(round(dmg * mod.get("damage", 1.0)))
            arm = int(round(arm * mod.get("armor", 1.0)))
        return Card(
            card.name,
            card.ctype,
            dmg,
            card.element,
            arm,
            card.effect,
            card.persistent,
            card.hymn,
            card.multi,
            card.max_targets,
            card.dmg_per_hymn,
            card.pre,
            card.before_ranged,
            card.hit_mod,
        )

    def reset(self) -> None:
        # restore upgrade pool to the original state
        self.upg_pool = self._orig_pool[:]
        self.hp = self.max_hp
        self.fate = 0
        self.armor_pool = 0
        cards = [self._mod_card(c) for c in self.base_cards]
        self.deck = Deck(cards, owner=self)
        self.deck.shuffle()
        self.combat_effects.clear()
        self.exchange_effects.clear()
        self.active_hymns.clear()
        self.combat_record = {"drawn": Counter(), "played": Counter()}

    def gain_fate(self, n: int = 1) -> None:
        """Increase ``fate`` but never above ``FATE_MAX``."""
        self.fate = min(FATE_MAX, self.fate + n)

    def gain_upgrades(self, n: int = 1) -> None:
        """Draw ``n`` upgrades from the weighted pool into the deck."""
        for _ in range(n):
            if not self.upg_pool:
                break
            card = RNG.choice(self.upg_pool)
            self.upg_pool.remove(card)
            self.deck.cards.append(self._mod_card(card))

    def spend_fate(self, n: int = 1) -> bool:
        """Spend ``n`` fate if above the hero specific threshold."""
        thresh = 5 if self.name == "Brynhild" else 3
        if self.fate > thresh and self.fate >= n:
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
    rolled_dice: int = 0  # dice rolled against this enemy in the current exchange
    attack_mod: Optional[Callable[[Hero, Card, Dict[str, object], int], int]] = None
    start_fx: Optional[Callable[[Dict[str, object]], None]] = None
    end_fx: Optional[Callable[[Hero, Dict[str, object], "Enemy"], None]] = None

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def roll_die(defense: int, mod: int = 0, *, hero: Optional[Hero] = None,
             allow_reroll: bool = True) -> int:
    """Roll a single d8 with optional fate based rerolls."""
    r = max(1, min(8, d8() + mod))
    if not allow_reroll or hero is None:
        return r
    while r < defense and hero.spend_fate(1):
        r = max(1, min(8, d8() + mod))
    return r


def roll_hits(num_dice: int, defense: int, mod: int = 0, *,
              hero: Optional[Hero] = None,
              element: Element = Element.NONE,
              vulnerability: Element = Element.NONE,
              allow_reroll: bool = True,
              enemy: Optional[Enemy] = None,
              free_rerolls: int = 0,
              ctx: Optional[Dict[str, object]] = None) -> int:
    bonus = 0
    if ctx:
        bonus = ctx.pop('bonus_dice', 0)
    total_dice = num_dice + bonus
    dmg = 0
    misses = 0
    reroll_hits = 0
    i = 0
    while i < total_dice:
        # initial roll without automatic rerolls
        r = roll_die(defense, mod, hero=hero, allow_reroll=False)
        rerolled = False
        if r < defense and ctx and ctx.get('reroll_misses_once'):
            r = max(1, min(8, d8() + mod))
            rerolled = True
        while r < defense and free_rerolls:
            free_rerolls -= 1
            r = max(1, min(8, d8() + mod))
            rerolled = True
        if r < defense and allow_reroll and hero and enemy:
            remain = enemy.hp - dmg
            max_hit = 4 if element != Element.NONE and element == vulnerability else 2
            if remain <= max_hit:
                while r < defense and hero.spend_fate(1):
                    r = max(1, min(8, d8() + mod))
                    rerolled = True
        if enemy and enemy.ability == "denied-heaven":
            r = denied_heaven(r, mod)
        if enemy and enemy.ability == "curse-of-torment" and hero:
            curse_of_torment(hero, r)
        if ctx and ctx.get('die_hooks'):
            for hook in ctx['die_hooks']:
                new = hook(hero, r)
                if isinstance(new, int):
                    r = new
        if r >= defense:
            hit = 2 if r == 8 else 1
            if element != Element.NONE and element == vulnerability:
                hit *= 2
            if rerolled:
                reroll_hits += 1
            dmg += hit
        else:
            misses += 1
        if ctx:
            extra = ctx.pop('bonus_dice', 0)
            total_dice += extra
        i += 1
    if ctx is not None:
        ctx['last_misses'] = misses
        ctx['reroll_hits'] = ctx.get('reroll_hits', 0) + reroll_hits
    return dmg

# persistent effect application

def apply_persistent(hero: Hero, ctx: Dict[str, object]) -> None:
    """Invoke all persistent effects registered on ``hero``.

    Entries in ``hero.combat_effects`` or ``hero.exchange_effects`` are tuples
    ``(fx, marker)``. ``marker`` identifies the originating card or other
    source and is not used when calling the effect.
    """
    if ctx.get("silenced"):
        return
    for fx, _ in hero.combat_effects:
        fx(hero, ctx)
    for fx, _ in hero.exchange_effects:
        fx(hero, ctx)

def _add_persistent(
    effects: List[Tuple[Callable[["Hero", Dict[str, object]], None], object]],
    fx: Callable[["Hero", Dict[str, object]], None],
    marker: object,
) -> None:
    """Append ``(fx, marker)`` to ``effects`` if ``marker`` isn't already present."""
    if marker not in [m for _, m in effects]:
        effects.append((fx, marker))

def remove_enemy(ctx: Dict[str, object], enemy: Enemy) -> None:
    """Remove ``enemy`` from combat and store it for later placement."""
    if enemy in ctx.get('enemies', []):
        ctx['enemies'].remove(enemy)
    ctx.setdefault('adjacent_enemies', []).append(enemy)

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

def void_soldier_mod(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
    """Reduce multi-target damage if at least two Void Soldiers remain."""
    if card.multi and sum(1 for e in ctx.get("enemies", []) if e.ability == "void-soldier") >= 2:
        return max(0, dmg - 1)
    return dmg

def end_cursed_thorns(hero: Hero, ctx: Dict[str, object], _: Enemy) -> None:
    cursed_thorns(hero)

def end_banshee_wail(hero: Hero, ctx: Dict[str, object], enemy: Enemy) -> None:
    banshee_wail(ctx["heroes"], enemy.rolled_dice)

def end_power_sap(hero: Hero, ctx: Dict[str, object], enemy: Enemy) -> None:
    power_sap(ctx, enemy)

# map ability names to helper functions
ABILITY_FUNCS = {
    "dark-phalanx": dark_phalanx,
    "spiked-armor": spiked_armor,
    "void-soldier": void_soldier_mod,
}

# simple card effects ---------------------------------------------------------

def gain_armor(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += n
    return _fx

def gain_armor_self_or_ally(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Grant ``n`` Armor to the hero or the first ally in ``ctx``."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        allies = [x for x in ctx.get('heroes', [h]) if x is not h]
        target = allies[0] if allies else h
        target.armor_pool += n
    return _fx

def draw_cards(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.deck.draw(n)
    return _fx

def draw_for_all(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Each hero in ``ctx`` draws ``n`` cards."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        heroes = ctx.get('heroes', [h])
        for hero in heroes:
            hero.deck.draw(n)
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

def add_rerolls(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Grant ``n`` free rerolls to the next attack."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['extra_rerolls'] = ctx.get('extra_rerolls', 0) + n
    return _fx

def global_reroll_fx() -> Callable[[Hero, Dict[str, object]], None]:
    """Reroll each die that misses once for this exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['reroll_misses_once'] = True
    return _fx

def reroll_per_attack_fx(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Grant ``n`` free rerolls on every attack for this combat."""
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['global_reroll'] = c.get('global_reroll', 0) + n
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['global_reroll'] = ctx.get('global_reroll', 0) + n
        if (per_exchange, n) not in h.combat_effects:
            h.combat_effects.append((per_exchange, n))
    return _fx

def reroll_per_attack_all_fx(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Grant all heroes ``n`` free rerolls on every attack for this combat."""

    def per_exchange(_h: Hero, c: Dict[str, object]) -> None:
        c['global_reroll'] = c.get('global_reroll', 0) + n

    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['global_reroll'] = ctx.get('global_reroll', 0) + n
        heroes = ctx.get('heroes', [h])
        for hero in heroes:
            if (per_exchange, n) not in hero.combat_effects:
                hero.combat_effects.append((per_exchange, n))

    return _fx

def armor_allies(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Give ``n`` armor to all heroes in the context."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        for hero in ctx.get('heroes', [h]):
            hero.armor_pool += n
    return _fx

def heal(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Heal ``amount`` HP up to ``hero.max_hp``."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.hp = min(h.max_hp, h.hp + amount)
    return _fx

# backward compatible alias
heal_fx = heal

def discard_for_fate(discard_n: int, gain: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Discard ``discard_n`` random cards then gain ``gain`` Fate."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        for _ in range(min(discard_n, len(h.deck.hand))):
            i = RNG.randrange(len(h.deck.hand))
            h.deck.disc.append(h.deck.hand.pop(i))
        h.gain_fate(gain)
    return _fx

def discard_for_area_damage(mult: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Discard all cards to add ``mult`` damage per card to all enemies."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        count = len(h.deck.hand)
        for _ in range(count):
            i = RNG.randrange(len(h.deck.hand))
            h.deck.disc.append(h.deck.hand.pop(i))
        if count:
            ctx['area_damage'] = ctx.get('area_damage', 0) + mult * count
    return _fx

def discard_bonus_damage(mult: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Discard any number of cards for ``mult`` bonus damage per card."""

    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        if not h.deck.hand:
            return
        enemy = ctx.get('last_target')
        if not isinstance(enemy, Enemy):
            enemies = ctx.get('enemies', [])
            enemy = enemies[0] if enemies else None
        if not isinstance(enemy, Enemy):
            return
        need = math.ceil(enemy.hp / mult)
        n = min(len(h.deck.hand), need)
        for _ in range(n):
            i = RNG.randrange(len(h.deck.hand))
            h.deck.disc.append(h.deck.hand.pop(i))
        if n:
            bonus = mult * n
            ctx['bonus_damage'] = ctx.get('bonus_damage', 0) + bonus
            enemy.hp -= bonus
            if enemy.hp <= 0 and enemy in ctx.get('enemies', []):
                remove_enemy(ctx, enemy)
    return _fx

def heal_self_or_ally(self_amt: int, ally_amt: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Heal hero or an ally if present."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        allies = [x for x in ctx.get('heroes', [h]) if x is not h]
        if allies:
            target = allies[0]
            target.hp = min(target.max_hp, target.hp + ally_amt)
        else:
            h.hp = min(h.max_hp, h.hp + self_amt)
    return _fx

def extra_die_on_eight() -> Callable[[Hero, Dict[str, object]], None]:
    """Roll an additional die whenever an 8 appears."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        def hook(_h: Hero, roll: int) -> int:
            if roll == 8:
                ctx['bonus_dice'] = ctx.get('bonus_dice', 0) + 1
            return roll
        def cleanup(_h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
            if 'die_hooks' in c and hook in c['die_hooks']:
                c['die_hooks'].remove(hook)
            return dmg
        ctx.setdefault('die_hooks', []).append(hook)
        ctx.setdefault('attack_hooks', []).append(cleanup)
    return _fx

def mark_target_plus_die(enemy: Enemy) -> Callable[[Hero, Dict[str, object]], None]:
    """Give +1 die against ``enemy`` for the rest of combat."""
    def hook(_h: Hero, _c: Card, c: Dict[str, object], tgt: Enemy, _e: Element, _v: Element) -> int:
        if tgt is enemy:
            c['bonus_dice'] = c.get('bonus_dice', 0) + 1
        return 0
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('pre_attack_hooks', []).append(hook)
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('pre_attack_hooks', []).append(hook)
        marker = ctx.get('_src_card', hook)
        _add_persistent(h.combat_effects, per_exchange, marker)
    return _fx

def glyph_mark_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    enemy = ctx.get('last_target')
    if isinstance(enemy, Enemy):
        mark_target_plus_die(enemy)(hero, ctx)

def veil_rain_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    n = len(ctx.get('enemies', []))
    ctx['area_damage'] = ctx.get('area_damage', 0) + n

def modify_enemy_defense(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Adjust enemy defense for the rest of the exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['enemy_defense_mod'] = ctx.get('enemy_defense_mod', 0) + amount
    return _fx

def cleave_all(hero_list: List[Hero], dmg: int) -> None:
    """Apply ``dmg`` to every hero in ``hero_list`` ignoring order."""
    for h in hero_list:
        soak = min(h.armor_pool, dmg)
        h.armor_pool -= soak
        taken = max(0, dmg - soak)
        if MIN_DAMAGE and dmg > 0 and taken == 0:
            taken = 1
        h.hp -= taken

def enrage(enemy: Enemy) -> bool:
    """Return True if ``enemy`` is enraged and attacks twice."""
    return enemy.hp <= 3

def end_hymns_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    hero.active_hymns.clear()
    hero.combat_effects = [
        p
        for p in hero.combat_effects
        if not (isinstance(p[1], Card) and p[1].hymn)
    ]
    hero.exchange_effects = [
        p
        for p in hero.exchange_effects
        if not (isinstance(p[1], Card) and p[1].hymn)
    ]

def hymn_count(hero: Hero) -> int:
    """Return the number of active hymns on ``hero``."""
    return len(hero.active_hymns)

def armor_from_hymns(hero: Hero, n: int) -> int:
    """Armor bonus equal to ``n`` times active hymns."""
    return n * hymn_count(hero)

def damage_from_hymns(hero: Hero, n: int) -> int:
    """Damage bonus equal to ``n`` times active hymns."""
    return n * hymn_count(hero)

def hymn_armor(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Gain ``n`` armor per active Hymn."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += armor_from_hymns(h, n)
    return _fx

def hymn_damage(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Deal ``n`` extra damage per active Hymn for the exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        bonus = damage_from_hymns(h, n)
        ctx["hymn_damage"] = ctx.get("hymn_damage", 0) + bonus
    return _fx

def hp_for_damage(cost: int, bonus: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Spend ``cost`` HP to gain ``bonus`` damage on the next attack."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        if h.hp > cost:
            h.hp -= cost
            ctx["bonus_damage"] = ctx.get("bonus_damage", 0) + bonus
    return _fx

def fate_for_bonus(cost: int, *, damage: int = 0, armor: int = 0) -> Callable[[Hero, Dict[str, object]], None]:
    """Spend ``cost`` Fate to gain damage or armor bonuses."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        if h.fate >= cost:
            h.fate -= cost
            if damage:
                ctx["bonus_damage"] = ctx.get("bonus_damage", 0) + damage
            if armor:
                h.armor_pool += armor
    return _fx

def defense_down(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Reduce enemy defense for the rest of the exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['enemy_defense_mod'] = ctx.get('enemy_defense_mod', 0) - n
    return _fx

def multi_bonus(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Grant ``n`` bonus damage when attacking multiple targets."""
    def hook(hero: Hero, card: Card, ctx2: Dict[str, object], dmg: int) -> int:
        if card.multi:
            return dmg + n
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

# additional helper effects used by Musashi ---------------------------------
def combine_effects(*fxs: Callable[[Hero, Dict[str, object]], None]) -> Callable[[Hero, Dict[str, object]], None]:
    """Combine multiple simple effects into one."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        for f in fxs:
            f(h, ctx)
    return _fx

def vulnerability_bonus(elem: Element, bonus: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Add ``bonus`` damage when target vulnerability matches ``elem``."""
    def hook(hero: Hero, card: Card, ctx2: Dict[str, object], dmg: int) -> int:
        check = elem if elem != Element.NONE else card.element
        enemies = ctx2.get('enemies', [])
        if enemies and enemies[0].vulnerability == check:
            return dmg + bonus
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def change_element(elem: Element) -> Callable[[Hero, Dict[str, object]], None]:
    """Force the next attack to use ``elem`` as its element."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['next_element'] = elem
    return _fx

def choose_element() -> Callable[[Hero, Dict[str, object]], None]:
    """Automatically choose an element for the next attack."""

    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        elem = None
        vuln = None
        if ctx.get('enemies'):
            vuln = ctx['enemies'][0].vulnerability

        options = ctx.get('played_attacks', [])
        if options:
            elems = [e for _n, e in options]
            if vuln is not None:
                for e in elems:
                    if e == vuln:
                        elem = e
                        break
            if elem is None:
                elem = RNG.choice(elems)
        elif vuln is not None and vuln is not Element.NONE:
            elem = vuln
        if elem is None:
            choices = [e for e in Element if e is not Element.NONE]
            elem = RNG.choice(choices)
        ctx['next_element'] = elem

    return _fx

def auto_element(*elems: Element) -> Callable[[Hero, Dict[str, object]], None]:
    """Pick the first element in ``elems`` matching enemy vulnerability."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        if not ctx.get('enemies'):
            return
        vuln = ctx['enemies'][0].vulnerability
        for e in elems:
            if e == vuln:
                ctx['next_element'] = e
                return
        ctx['next_element'] = elems[0]
    return _fx

def bonus_if_vulnerable(elem: Element, bonus: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Deal extra damage when the target's vulnerability matches ``elem``."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        if ctx.get('enemies') and ctx['enemies'][0].vulnerability == elem:
            enemy = ctx['enemies'][0]
            enemy.hp -= bonus
            if enemy.hp <= 0:
                remove_enemy(ctx, enemy)
    return _fx

def armor_damage_bonus(mult: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Add damage equal to ``hero.armor_pool`` times ``mult`` on future attacks."""
    def hook(hero: Hero, card: Card, ctx2: Dict[str, object], dmg: int) -> int:
        return dmg + mult * hero.armor_pool
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def double_attack(card: Card) -> Callable[[Hero, Dict[str, object]], None]:
    """Perform a second attack using ``card`` after it resolves."""
    def _fx(hero: Hero, ctx: Dict[str, object]) -> None:
        temp = Card(card.name, card.ctype, card.dice, card.element,
                    card.armor)
        resolve_attack(hero, temp, ctx)
    return _fx

def hp_for_damage_scaled(max_bonus: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Spend up to ``max_bonus`` HP to gain the same damage on this attack."""
    def hook(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
        spend = min(max_bonus, hero.hp - 1)
        if spend > 0:
            hero.hp -= spend
            return dmg + spend
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def per_attack_hp_loss(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Enemies lose ``amount`` HP each time you resolve an attack."""
    def hook(hero: Hero, card: Card, ctx2: Dict[str, object], dmg: int) -> int:
        enemies = ctx2.get('enemies', [])
        if card.multi:
            for e in enemies:
                e.hp -= amount
        elif enemies:
            enemies[0].hp -= amount
        return dmg
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('post_attack_hooks', []).append(hook)
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
        marker = ctx.get('_src_card', hook)
        _add_persistent(h.combat_effects, per_exchange, marker)
    return _fx

def damage_bonus_per_enemy(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Add ``amount`` damage for each enemy in combat."""
    def hook(hero: Hero, card: Card, ctx2: Dict[str, object], dmg: int) -> int:
        return dmg + amount * len(ctx2.get('enemies', []))
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def gain_fate_per_enemy(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.gain_fate(len(ctx.get('enemies', [])) * amount)
    return _fx

def armor_per_enemy(base: int = 0) -> Callable[[Hero, Dict[str, object]], None]:
    """Gain armor equal to ``base`` plus one per enemy."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += base + len(ctx.get('enemies', []))
    return _fx

def armor_per_hit(mult: int = 1) -> Callable[[Hero, Dict[str, object]], None]:
    """Gain ``mult`` armor for each hit you deal on this attack."""
    def hook(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
        hero.armor_pool += dmg * mult
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def gain_fate_from_attacks() -> Callable[[Hero, Dict[str, object]], None]:
    """Gain Fate equal to the number of previous attacks this exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.gain_fate(ctx.get('attacks_used', 0))
    return _fx

def gain_fate_per_kill(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Gain Fate for each enemy killed by the last attack."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.gain_fate(ctx.get('killed_count', 0) * amount)
    return _fx

def double_rerolls_fx() -> Callable[[Hero, Dict[str, object]], None]:
    """Allow free rerolls to be applied twice for the next attack."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['double_rerolls'] = True
    return _fx

def heal_on_kill(amount: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Heal hero or an ally whenever an enemy dies."""
    def apply(h: Hero, c: Dict[str, object]) -> None:
        count = c.get('killed_count', 0)
        if count:
            allies = [x for x in c.get('heroes', [h]) if x is not h]
            target = allies[0] if allies else h
            target.hp = min(target.max_hp, target.hp + amount * count)

    def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
        apply(hero, c)

    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        apply(h, ctx)
        if (per_exchange, None) not in h.combat_effects:
            h.combat_effects.append((per_exchange, None))
    return _fx

def horde_breaker_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] When an enemy dies, others lose 2 HP."""
    def hook(h: Hero, c: Dict[str, object]) -> None:
        prev = c.get('_hb_prev', len(c.get('enemies', [])))
        curr = len(c.get('enemies', []))
        diff = prev - curr
        if diff > 0:
            enemies = c.get('enemies', [])
            for e in enemies[:]:
                e.hp -= 2 * diff
            c['enemies'] = [e for e in enemies if e.hp > 0]
        c['_hb_prev'] = len(c.get('enemies', []))

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['_hb_prev'] = len(c.get('enemies', []))
        c.setdefault('post_attack_hooks', []).append(hook)

    ctx['_hb_prev'] = len(ctx.get('enemies', []))
    ctx.setdefault('post_attack_hooks', []).append(hook)
    if (per_exchange, None) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, None))

def ally_damage_bonus(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Give an ally +``n`` damage to all attacks for this combat."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        allies = [x for x in ctx.get('heroes', [h]) if x is not h]
        if not allies:
            return
        target = allies[0]

        def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
            if hero is target:
                c['exchange_bonus'] = c.get('exchange_bonus', 0) + n

        if (per_exchange, None) not in target.combat_effects:
            target.combat_effects.append((per_exchange, None))
    return _fx

def guard_from_beyond_fx() -> Callable[[Hero, Dict[str, object]], None]:
    """Grant an ally 5 Armor and draw all enemy attacks to them this exchange."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        allies = [x for x in ctx.get('heroes', [h]) if x is not h]
        target = allies[0] if allies else h
        target.armor_pool += 5
        ctx['forced_target'] = target
        def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
            c['forced_target'] = target
        if (per_exchange, target) not in h.exchange_effects:
            h.exchange_effects.append((per_exchange, target))
    return _fx

def spiritual_gifts_fx() -> Callable[[Hero, Dict[str, object]], None]:
    """Discard 1 to let an ally gain 2 Fate and draw 1."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        allies = [x for x in ctx.get('heroes', [h]) if x is not h]
        if not allies or not h.deck.hand:
            return
        i = RNG.randrange(len(h.deck.hand))
        h.deck.disc.append(h.deck.hand.pop(i))
        target = allies[0]
        target.gain_fate(2)
        target.deck.draw(1)
    return _fx

def crits_are_four() -> Callable[[Hero, Dict[str, object]], None]:
    """[Combat] Critical hits deal 4 damage instead of 2."""
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        def die_hook(_h: Hero, roll: int) -> int:
            if roll == 8:
                ctx['crits'] = ctx.get('crits', 0) + 1
            return roll

        def atk_hook(_h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
            bonus = c.pop('crits', 0)
            return dmg + bonus * 2

        def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
            c.setdefault('die_hooks', []).append(die_hook)
            c.setdefault('attack_hooks', []).append(atk_hook)

        ctx.setdefault('die_hooks', []).append(die_hook)
        ctx.setdefault('attack_hooks', []).append(atk_hook)
        if (per_exchange, None) not in h.combat_effects:
            h.combat_effects.append((per_exchange, None))
    return _fx

def fate_for_damage_scaled(max_amt: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Spend up to ``max_amt`` Fate for equal bonus damage on this attack."""
    def hook(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
        spend = min(max_amt, hero.fate)
        if spend:
            hero.fate -= spend
            return dmg + spend
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def fate_for_damage_mult(mult: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Spend all Fate for ``mult`` times that much bonus damage."""
    def hook(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
        spend = hero.fate
        if spend:
            hero.fate = 0
            return dmg + spend * mult
        return dmg
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
    return _fx

def armor_from_miss_pairs() -> Callable[[Hero, Dict[str, object]], None]:
    """Gain 1 Armor for each two dice that miss while in combat."""
    def hook(hero: Hero, card: Card, ctx: Dict[str, object], dmg: int) -> int:
        misses = ctx.get('last_misses', 0)
        hero.armor_pool += misses // 2
        return dmg
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('attack_hooks', []).append(hook)
        marker = ctx.get('_src_card', hook)
        _add_persistent(h.combat_effects, per_exchange, marker)
    return _fx

def hymn_of_blood_end(hero: Hero, ctx: Dict[str, object], _enemy: Optional[Enemy]) -> None:
    if not ctx.get('enemies'):
        hero.hp = min(hero.max_hp, hero.hp + hymn_count(hero))

def hymn_of_blood_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx.setdefault('end_hooks', []).append((hymn_of_blood_end, None))
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('end_hooks', []).append((hymn_of_blood_end, None))
    if (per_exchange, hymn_of_blood_fx) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, hymn_of_blood_fx))

def tempestuous_finale_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    bonus = damage_from_hymns(hero, 2)
    ctx['bonus_damage'] = ctx.get('bonus_damage', 0) + bonus
    end_hymns_fx(hero, ctx)

def piercer_of_fates_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    if hero.fate <= 3:
        ctx['hit_mod'] = ctx.get('hit_mod', 0) - 1
    elif hero.fate >= 8:
        ctx['hit_mod'] = ctx.get('hit_mod', 0) + 1

def armor_on_high_roll() -> Callable[[Hero, Dict[str, object]], None]:
    """[Combat] Gain 1 Armor whenever you roll a 7 or 8."""
    def make_hook(hero: Hero):
        def hook(_h: Hero, roll: int) -> Optional[int]:
            if roll >= 7:
                hero.armor_pool += 1
            return roll
        return hook
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        hook = make_hook(h)
        ctx.setdefault('die_hooks', []).append(hook)
        def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
            c.setdefault('die_hooks', []).append(hook)
        marker = ctx.get('_src_card', hook)
        _add_persistent(h.combat_effects, per_exchange, marker)
    return _fx

def ones_are_eights() -> Callable[[Hero, Dict[str, object]], None]:
    """Treat rolls of 1 as 8 for the rest of combat."""
    def hook(_h: Hero, roll: int) -> int:
        return 8 if roll == 1 else roll
    def per_exchange(hero: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('die_hooks', []).append(hook)
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx.setdefault('die_hooks', []).append(hook)
        if (per_exchange, None) not in h.combat_effects:
            h.combat_effects.append((per_exchange, None))
    return _fx

def dice_plus_one_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Exchange] Treat all of ``hero``'s dice results as 1 higher (max 8)."""

    def hook(h: Hero, roll: int) -> int:
        if h is hero:
            return 8 if roll >= 8 else roll + 1
        return roll

    def per_exchange(_h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('die_hooks', []).append(hook)

    ctx.setdefault('die_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.exchange_effects, per_exchange, marker)

def armor_each_exchange_per_enemy() -> Callable[[Hero, Dict[str, object]], None]:
    """Gain armor equal to number of enemies once each exchange."""
    def per_exchange(hero: Hero, c: Dict[str, object]) -> None:
        hero.armor_pool += len(c.get('enemies', []))
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        h.armor_pool += len(ctx.get('enemies', []))
        if (per_exchange, None) not in h.combat_effects:
            h.combat_effects.append((per_exchange, None))
    return _fx

def exchange_damage_bonus(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    """Increase damage of future attacks this exchange by ``n``."""
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['exchange_bonus'] = c.get('exchange_bonus', 0) + n
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['exchange_bonus'] = ctx.get('exchange_bonus', 0) + n
        if (per_exchange, None) not in h.exchange_effects:
            h.exchange_effects.append((per_exchange, None))
    return _fx

def conflux_lance_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Reduce enemy defense by 2 per other hero for this attack."""
    allies = [x for x in ctx.get('heroes', [hero]) if x is not hero]
    mod = -2 * len(allies)

    def hook(_h: Hero, _c: Card, _ctx: Dict[str, object], _e: Enemy,
             _el: Element, _v: Element) -> int:
        return mod

    def cleanup(_h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        if 'pre_attack_hooks' in c and hook in c['pre_attack_hooks']:
            c['pre_attack_hooks'].remove(hook)
        return dmg

    ctx.setdefault('pre_attack_hooks', []).append(hook)
    ctx.setdefault('attack_hooks', []).append(cleanup)

def echoes_of_guidance_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Repeat the last card played by an ally this exchange."""
    allies = [x for x in ctx.get('heroes', [hero]) if x is not hero]
    if not allies:
        return
    target = allies[0]
    if not target.deck.disc:
        return
    card = target.deck.disc[-1]
    temp = Card(card.name, card.ctype, card.dice, card.element,
                card.armor, card.effect, card.persistent, card.hymn,
                card.multi, card.max_targets, card.dmg_per_hymn,
                card.pre, card.before_ranged, card.hit_mod)
    resolve_attack(target, temp, ctx)

def chains_of_morrigan_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Exchange] +1 hit per target on all attacks."""

    def hook(_h: Hero, card: Card, c: Dict[str, object], _enemy: Enemy,
             _el: Element, _v: Element) -> int:
        if c.get('_chains_applied'):
            return 0
        enemies = c.get('enemies', [])
        if card.multi:
            count = len(enemies) if card.max_targets is None else min(len(enemies), card.max_targets)
        else:
            count = 1 if enemies else 0
        c['hit_mod'] = c.get('hit_mod', 0) + count
        c['_chains_applied'] = True
        return 0

    def cleanup(_h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        c.pop('_chains_applied', None)
        return dmg

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('pre_attack_hooks', []).append(hook)
        c.setdefault('attack_hooks', []).append(cleanup)

    ctx.setdefault('pre_attack_hooks', []).append(hook)
    ctx.setdefault('attack_hooks', []).append(cleanup)
    if (per_exchange, None) not in hero.exchange_effects:
        hero.exchange_effects.append((per_exchange, None))

# Brynhild uncommon card helpers --------------------------------------------

def hymn_of_fate_end(hero: Hero, ctx: Dict[str, object], _enemy: Optional[Enemy]) -> None:
    hero.gain_fate(hymn_count(hero))

def hymn_of_fate_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx.setdefault('end_hooks', []).append((hymn_of_fate_end, None))
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('end_hooks', []).append((hymn_of_fate_end, None))
    if (per_exchange, hymn_of_fate_fx) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, hymn_of_fate_fx))


def echoes_of_gungnir_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    def hook(h: Hero, card: Card, c: Dict[str, object], dmg: int) -> int:
        bonus = c.get('prev_misses', 0)
        c['prev_misses'] = c.get('last_misses', 0)
        return dmg + bonus
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)
    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def overflowing_grace_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    if hasattr(hero, '_overflowing_grace'):
        return
    orig = hero.gain_fate
    def patched(n: int = 1) -> None:
        total = hero.fate + n
        if total > FATE_MAX:
            hero.fate = FATE_MAX
            hero.hp = min(hero.max_hp, hero.hp + total - FATE_MAX)
        else:
            hero.fate = total
    hero.gain_fate = patched
    hero._overflowing_grace = orig
    def cleanup(h: Hero, _c: Dict[str, object]) -> None:
        if hasattr(h, '_overflowing_grace'):
            h.gain_fate = h._overflowing_grace  # type: ignore[attr-defined]
            delattr(h, '_overflowing_grace')
    hero.combat_effects.append((cleanup, None))


def misfortunes_muse_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    if ctx.get('last_misses', 0) >= 4:
        hero.deck.draw(1)


def tyrs_choice_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Automatically gain 2 Fate (default choice)."""
    hero.gain_fate(2)

def fortunes_throw_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Gain 2 Fate if possible; otherwise gain 2 Armor."""
    if hero.fate <= FATE_MAX - 2:
        hero.gain_fate(2)
    else:
        hero.armor_pool += 2


def norns_gambit_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx['hit_mod'] = ctx.get('hit_mod', 0) - 2
    ctx['bonus_damage'] = ctx.get('bonus_damage', 0) + 4


def hymn_hit_bonus(n: int) -> Callable[[Hero, Dict[str, object]], None]:
    def _fx(h: Hero, ctx: Dict[str, object]) -> None:
        ctx['hit_mod'] = ctx.get('hit_mod', 0) + n
    return _fx


def triumphant_blow_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    if ctx.get('killed'):
        hero.gain_fate(2)


# Brynhild rare card helpers ---------------------------------------------------

def hymn_all_father_end(hero: Hero, ctx: Dict[str, object], _enemy: Optional[Enemy]) -> None:
    gain = 1 + hymn_count(hero)
    hero.armor_pool += min(4, gain)


def hymn_all_father_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx.setdefault('end_hooks', []).append((hymn_all_father_end, None))
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('end_hooks', []).append((hymn_all_father_end, None))
    if (per_exchange, hymn_all_father_fx) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, hymn_all_father_fx))


def lokis_trickery_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    def hook(h: Hero, card: Card, c: Dict[str, object], dmg: int) -> int:
        bonus = c.pop('reroll_hits', 0)
        return dmg + bonus
    ctx.setdefault('attack_hooks', []).append(hook)


def ragnarok_call_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['exchange_bonus'] = c.get('exchange_bonus', 0) + 2
        c['hit_mod'] = c.get('hit_mod', 0) - 1
    ctx['exchange_bonus'] = ctx.get('exchange_bonus', 0) + 2
    ctx['hit_mod'] = ctx.get('hit_mod', 0) - 1
    if (per_exchange, None) not in hero.exchange_effects:
        hero.exchange_effects.append((per_exchange, None))


def storms_thunderlance_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx['hit_mod'] = ctx.get('hit_mod', 0) + hymn_count(hero)


def freyjas_command_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    def hook(h: Hero, card: Card, c: Dict[str, object], dmg: int) -> int:
        return dmg + h.fate
    ctx.setdefault('attack_hooks', []).append(hook)


def blessing_of_balder_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    spend = hero.fate
    if spend:
        hero.fate = 0
        hero.armor_pool += spend * 2


def storms_rhyme_crash_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ended = hymn_count(hero)
    if ended:
        ctx['bonus_damage'] = ctx.get('bonus_damage', 0) + 2 * ended
    end_hymns_fx(hero, ctx)


def fate_severer_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    spend = hero.fate
    if spend:
        hero.fate = 0
        ctx['bonus_damage'] = ctx.get('bonus_damage', 0) + 3 * spend


def chance_seizing_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Pay 1 Fate to triple vulnerability damage for this combat."""
    if hero.fate >= 1:
        hero.fate -= 1

        def hook(_h: Hero, card: Card, c: Dict[str, object], dmg: int) -> int:
            enemies = c.get('enemies', [])
            if enemies and card.element != Element.NONE and enemies[0].vulnerability == card.element:
                return dmg + dmg // 2
            return dmg

        def per_exchange(h: Hero, c: Dict[str, object]) -> None:
            c.setdefault('attack_hooks', []).append(hook)

        ctx.setdefault('attack_hooks', []).append(hook)
        marker = ctx.get('_src_card', hook)
        _add_persistent(hero.combat_effects, per_exchange, marker)


def susanoo_cut_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Add damage equal to hero armor // 2."""

    def hook(h: Hero, card: Card, c: Dict[str, object], dmg: int) -> int:
        return dmg + h.armor_pool // 2

    ctx.setdefault('attack_hooks', []).append(hook)


def water_mirror_split_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Next single-target attack hits two enemies."""
    ctx['split_next'] = True


def iron_will_guard_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Gain 3 armor or pay 1 Fate for 5."""
    if hero.fate >= 1:
        hero.fate -= 1
        hero.armor_pool += 5
    else:
        hero.armor_pool += 3


def dual_moon_guard_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """End of exchange, gain Armor 1 + half damage dealt this exchange."""

    key = object()
    ctx[key] = 0

    def hook(h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        if h is hero:
            c[key] = c.get(key, 0) + dmg
        return dmg

    def end_fx(h: Hero, c: Dict[str, object], _e: Optional[Enemy]) -> None:
        total = c.pop(key, 0)
        h.armor_pool += 1 + total // 2

    ctx.setdefault('attack_hooks', []).append(hook)
    ctx.setdefault('end_hooks', []).append((end_fx, None))


def ghost_step_slash_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Repeat attack on another enemy if one was killed."""
    if ctx.get('attack_depth', 0) >= ATTACK_DEPTH_LIMIT:
        return
    if ctx.get('killed') and ctx.get('enemies') and not ctx.get('ghost_step'):
        ctx['ghost_step'] = True
        temp = Card('Ghost-Step Slash', CardType.MELEE, 3, Element.DIVINE)
        resolve_attack(hero, temp, ctx)
        ctx.pop('ghost_step', None)


def heavenly_dragon_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Lock element of all attacks for the rest of the exchange."""
    elem = ctx.get('last_element', Element.ARCANE)
    options = ctx.get('played_attacks', [])
    if options:
        # automatically use the last played attack's element
        elem = options[-1][1]

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['next_element'] = elem

    ctx['next_element'] = elem
    if (per_exchange, elem) not in hero.exchange_effects:
        hero.exchange_effects.append((per_exchange, elem))


def crescent_guard_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Pay 1 Fate to gain 2 Armor per previous card this exchange."""
    if hero.fate >= 1:
        hero.fate -= 1
        hero.armor_pool += 2 * ctx.get('attacks_used', 0)


def mountain_stance_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] -1 enemy DEF when attacking their vulnerability."""
    def hook(_h: Hero, _c: Card, c: Dict[str, object], enemy: Enemy,
             elem: Element, _vuln: Element) -> int:
        return -1 if elem != Element.NONE and elem == enemy.vulnerability else 0

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('pre_attack_hooks', []).append(hook)

    ctx.setdefault('pre_attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def mirror_flow_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] +3 damage when exactly two enemies are present."""
    def hook(_h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        return dmg + 3 if len(c.get('enemies', [])) == 2 else dmg

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)

    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def heaven_defying_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] Gain 1 Fate when using the enemy's vulnerability."""
    def hook(h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        elem = c.get('last_element', Element.NONE)
        for e in c.get('enemies', []):
            if elem != Element.NONE and elem == e.vulnerability:
                h.gain_fate(1)
                break
        return dmg

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)

    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def ascending_veng_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] Enemies lose HP when your armor absorbs damage."""
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['ascending_veng'] = True

    ctx['ascending_veng'] = True
    if (per_exchange, None) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, None))


def menacing_step_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Remove the first enemy from combat and store it for later placement."""
    if ctx.get('enemies'):
        enemy = ctx['enemies'].pop(0)
        ctx.setdefault('adjacent_enemies', []).append(enemy)


def iron_shell_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] If armor fully blocks damage, attacker loses 2 HP."""
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c['iron_shell'] = True

    ctx['iron_shell'] = True
    if (per_exchange, None) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, None))


def five_ring_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] Future attacks use the element of a played attack."""
    elem = ctx.get('last_element', Element.NONE)
    for c in reversed(hero.deck.disc):
        if c.element != Element.NONE:
            elem = c.element
            break
    if elem == Element.NONE:
        return

    def per_exchange(_h: Hero, c: Dict[str, object]) -> None:
        c['next_element'] = elem

    ctx['next_element'] = elem
    if (per_exchange, elem) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, elem))


def wanderer_blade_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] Future attacks use the element of a played attack."""
    five_ring_fx(hero, ctx)


def formless_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] +1 hit and +1 damage on all attacks."""

    def hook(_h: Hero, _c: Card, _ctx: Dict[str, object], dmg: int) -> int:
        return dmg + 1

    def per_exchange(_h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)
        c['hit_mod'] = c.get('hit_mod', 0) + 1

    ctx.setdefault('attack_hooks', []).append(hook)
    ctx['hit_mod'] = ctx.get('hit_mod', 0) + 1
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def stone_lotus_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Add damage equal to current armor."""

    def hook(h: Hero, _c: Card, _ctx: Dict[str, object], dmg: int) -> int:
        return dmg + h.armor_pool

    ctx.setdefault('attack_hooks', []).append(hook)


def twin_dragon_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Next single-target attack hits two enemies."""
    ctx['split_next'] = True


def edge_harmony_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Gain 3 Armor."""
    hero.armor_pool += 3


def two_strikes_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """If one targeted enemy dies, the other does too."""
    if ctx.get('killed') and ctx.get('enemies'):
        enemy = ctx['enemies'][0]
        enemy.hp = 0
        remove_enemy(ctx, enemy)


def moment_perf_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Gain 4 Armor or pay 2 Fate to double current armor."""
    if hero.fate >= 2:
        hero.fate -= 2
        hero.armor_pool *= 2
    else:
        hero.armor_pool += 4


def fortifying_attack_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Gain Armor equal to half damage dealt to the chosen enemy this exchange."""
    if not ctx.get('enemies'):
        return
    target = ctx['enemies'][0]
    ctx['fortify_dmg'] = 0

    def hook(h: Hero, _c: Card, c: Dict[str, object], dmg: int) -> int:
        if c.get('last_target') is target:
            c['fortify_dmg'] = c.get('fortify_dmg', 0) + dmg
        return dmg

    def end_fx(h: Hero, c: Dict[str, object], _e: Optional[Enemy]) -> None:
        gain = c.pop('fortify_dmg', 0) // 2
        if gain:
            h.armor_pool += gain

    ctx.setdefault('attack_hooks', []).append(hook)
    ctx.setdefault('end_hooks', []).append((end_fx, None))


def chiron_training_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] Gain 1 Armor each time an attack resolves."""
    hero.armor_pool += 1

    def hook(h: Hero, _c: Card, _ct: Dict[str, object], dmg: int) -> int:
        h.armor_pool += 1
        return dmg

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)

    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def once_isnt_enough_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """The next attack card is executed twice."""
    ctx['double_next'] = True


def strength_from_anger_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """[Combat] All attacks deal +1 damage."""

    def hook(_h: Hero, _c: Card, _ctx: Dict[str, object], dmg: int) -> int:
        return dmg + 1

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)

    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def true_might_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Deal 8 extra Brutal damage if no dice card was played this exchange."""
    if not ctx.get('dice_played'):
        def hook(_h: Hero, _c: Card, _ctx: Dict[str, object], dmg: int) -> int:
            return dmg + 8

        ctx.setdefault('attack_hooks', []).append(hook)


def athenas_guidance_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Discard 1 card then double all damage for this combat."""
    if hero.deck.hand:
        i = RNG.randrange(len(hero.deck.hand))
        hero.deck.disc.append(hero.deck.hand.pop(i))

    def hook(_h: Hero, _c: Card, _ctx: Dict[str, object], dmg: int) -> int:
        return dmg * 2

    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault('attack_hooks', []).append(hook)

    ctx.setdefault('attack_hooks', []).append(hook)
    marker = ctx.get('_src_card', hook)
    _add_persistent(hero.combat_effects, per_exchange, marker)


def apollos_sunburst_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Discard hand to add area damage."""
    count = len(hero.deck.hand)
    for _ in range(count):
        i = RNG.randrange(len(hero.deck.hand))
        hero.deck.disc.append(hero.deck.hand.pop(i))
    if count:
        ctx['area_damage'] = ctx.get('area_damage', 0) + 3 * count


def nike_desire_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Draw 1 or pay 1 Fate to draw 2."""
    if hero.fate >= 1:
        hero.fate -= 1
        hero.deck.draw(3)
    else:
        hero.deck.draw(1)


def hermes_delivery_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Draw a card and immediately play it as an attack."""
    if ctx.get('attack_depth', 0) >= ATTACK_DEPTH_LIMIT:
        return
    hero.deck.draw(1)
    if hero.deck.hand:
        card = hero.deck.hand.pop()
        resolve_attack(hero, card, ctx)


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


def ghostly(ctx: Dict[str, object]) -> None:
    """Remove all banshees at the start of the fourth exchange."""
    if ctx.get("exchange", 0) >= 3:
        ctx["enemies"].clear()


def banshee_wail(heroes: List[Hero], dice_count: int) -> None:
    """Deal 1 damage to every hero per 3 dice rolled."""
    dmg = dice_count // 3
    if dmg:
        cleave_all(heroes, dmg)

def power_sap(ctx: Dict[str, object], treant: Enemy) -> None:
    """Remove one combat effect and heal the treant if successful."""
    hero = ctx["heroes"][0]
    if hero.combat_effects:
        hero.combat_effects.pop(RNG.randrange(len(hero.combat_effects)))
        treant.hp += 1

def roots_of_despair(hero: Hero, miss: bool) -> None:
    """Punish complete attack misses."""
    if miss:
        hero.hp -= 1

def corrupted_destiny(hero: Hero) -> None:
    """Remove two fate from ``hero``."""
    hero.fate = max(0, hero.fate - 2)

def denied_heaven(roll: int, mod: int = 0) -> int:
    """Force rerolls of 8 until another value appears."""
    while roll == 8:
        roll = max(1, min(8, d8() + mod))
    return roll

# ---------------------------------------------------------------------------
# Card helpers to create attack cards
# ---------------------------------------------------------------------------
def atk(name: str, ctype: CardType, dice: int, element: Element = Element.NONE,
        armor: int = 0, effect: Optional[Callable[[Hero, Dict], None]] = None,
        persistent: Optional[str] = None, hymn: bool = False,
        multi: bool = False, max_targets: Optional[int] = None,
        dmg_per_hymn: int = 0, *, pre: bool = False,
        before_ranged: bool = False, hit_mod: int = 0) -> Card:
    return Card(name, ctype, dice, element, armor, effect,
                persistent, hymn, multi, max_targets, dmg_per_hymn,
                pre, before_ranged, hit_mod)

def weighted_pool(common: List[Card], uncommon: List[Card], rare: List[Card]) -> List[Card]:
    pool: List[Card] = []
    for c in common:
        pool.extend([c] * 3)
    for c in uncommon:
        pool.extend([c] * 2)
    pool.extend(rare)
    return pool

def build_rarity_map(base: List[Card], common: List[Card],
                     uncommon: List[Card], rare: List[Card]) -> Dict[str, str]:
    """Return mapping of card name to rarity bucket."""
    mapping: Dict[str, str] = {}
    for c in base:
        mapping[c.name] = "base"
    for c in common:
        mapping[c.name] = "common"
    for c in uncommon:
        mapping[c.name] = "uncommon"
    for c in rare:
        mapping[c.name] = "rare"
    return mapping

HERO_RARITY_MAPS: Dict[str, Dict[str, str]] = {}

# sample hero decks -----------------------------------------------------------
herc_base = [
    atk("Pillar-Breaker Blow", CardType.MELEE, 2, Element.BRUTAL),
    atk("Pillar-Breaker Blow", CardType.MELEE, 2, Element.BRUTAL),
    atk("Lion Strangler", CardType.MELEE, 1, Element.BRUTAL,
        effect=per_attack_hp_loss(1), persistent="combat"),
    atk("Demigodly Heroism", CardType.MELEE, 1, Element.DIVINE,
        armor=1),
    atk("Demigodly Heroism", CardType.MELEE, 1, Element.DIVINE,
        armor=1),
    atk("Sky Javelin", CardType.RANGED, 2, Element.DIVINE,
        effect=exchange_damage_bonus(1), persistent="exchange"),
    atk("Club Spin", CardType.MELEE, 1, Element.PRECISE, multi=True),
    atk("Club Spin", CardType.MELEE, 1, Element.PRECISE, multi=True),
    atk("Atlas Guard", CardType.RANGED, 0, effect=gain_armor(3)),
    atk("Atlas Guard", CardType.RANGED, 0, effect=gain_armor(3)),
]
herc_common_upg = [
    atk(
        "Bondless Effort",
        CardType.MELEE,
        3,
        Element.BRUTAL,
        effect=discard_bonus_damage(3),
        pre=True,
    ),
    atk("Colossus Smash", CardType.MELEE, 3, Element.BRUTAL, armor=1),
    atk("Olympian Call", CardType.MELEE, 1, Element.DIVINE,
        effect=reroll_per_attack_fx(1), persistent="combat"),
    atk("Divine Resilience", CardType.MELEE, 1, Element.DIVINE,
        armor=1, effect=armor_per_enemy()),
    atk("Horde Breaker", CardType.MELEE, 2, Element.DIVINE,
        effect=horde_breaker_fx, persistent="combat"),
    atk("Disorienting Blow", CardType.MELEE, 2, Element.PRECISE,
        effect=modify_enemy_defense(-3), persistent="exchange"),
    atk("Piercing Spear", CardType.RANGED, 2, Element.PRECISE,
        effect=modify_enemy_defense(-1), persistent="combat"),
    atk("Fated War", CardType.MELEE, 2, Element.SPIRITUAL, multi=True,
        effect=gain_fate_per_enemy(1)),
    atk("Fortune's Throw", CardType.RANGED, 2, Element.SPIRITUAL,
        effect=fortunes_throw_fx),
]
pain_strike = atk("Pain Strike", CardType.MELEE, 4, Element.BRUTAL,
                   effect=hp_for_damage_scaled(6), pre=True)
ares_will = atk("Ares' Will", CardType.MELEE, 1, Element.BRUTAL,
                effect=per_attack_hp_loss(2), persistent="combat", pre=True)
herc_uncommon_upg = [
    pain_strike,
    atk(
        "Fortifying Attack",
        CardType.MELEE,
        1,
        Element.BRUTAL,
        effect=fortifying_attack_fx,
        pre=True,
    ),
    atk("Bone-Splinter Whirl", CardType.MELEE, 3, Element.BRUTAL, multi=True,
        effect=defense_down(1), persistent="combat"),
    atk("Glorious Uproar", CardType.MELEE, 1, Element.DIVINE, multi=True,
        effect=damage_bonus_per_enemy(1)),
    atk("Guided By The Gods", CardType.MELEE, 1, Element.DIVINE,
        effect=reroll_per_attack_fx(1), persistent="combat"),
    atk(
        "Chiron's Training",
        CardType.MELEE,
        1,
        Element.PRECISE,
        effect=chiron_training_fx,
        persistent="combat",
    ),
    atk(
        "Once Isn't Enough",
        CardType.MELEE,
        0,
        effect=once_isnt_enough_fx,
    ),
    atk(
        "Strength from Anger",
        CardType.MELEE,
        1,
        Element.SPIRITUAL,
        effect=strength_from_anger_fx,
        persistent="combat",
    ),
    atk("Enduring Wave", CardType.MELEE, 2, Element.SPIRITUAL, multi=True,
        armor=2, effect=gain_armor(2)),
]
herc_rare_upg = [
    atk("Zeus' Wrath", CardType.MELEE, 4, Element.BRUTAL, multi=True),
    ares_will,
    atk(
        "True Might of Hercules",
        CardType.MELEE,
        4,
        Element.BRUTAL,
        effect=true_might_fx,
        pre=True,
    ),
    atk(
        "Athena's Guidance",
        CardType.MELEE,
        0,
        Element.DIVINE,
        effect=athenas_guidance_fx,
        persistent="combat",
    ),
    atk(
        "Apollo's Sunburst",
        CardType.RANGED,
        3,
        Element.DIVINE,
        multi=True,
        effect=apollos_sunburst_fx,
        pre=True,
    ),
    atk(
        "Nike's Desire",
        CardType.MELEE,
        1,
        Element.DIVINE,
        effect=nike_desire_fx,
    ),
    atk("Blessing of Hephaestus", CardType.RANGED, 0, effect=gain_armor(5)),
    atk(
        "Hermes' Delivery",
        CardType.MELEE,
        3,
        Element.PRECISE,
        effect=hermes_delivery_fx,
    ),
    atk(
        "Eris' Pandemonium",
        CardType.MELEE,
        0,
        effect=damage_bonus_per_enemy(1),
        persistent="exchange",
    ),
]
herc_pool = weighted_pool(herc_common_upg, herc_uncommon_upg, herc_rare_upg)
HERO_RARITY_MAPS["Hercules"] = build_rarity_map(
    herc_base, herc_common_upg, herc_uncommon_upg, herc_rare_upg
)
hercules = Hero("Hercules", 25, herc_base, herc_pool)

# Brynhild cards --------------------------------------------------------------
valkyrie_descent = atk(
    "Valkyrie's Descent", CardType.MELEE, 1, Element.SPIRITUAL,
    dmg_per_hymn=1,
)

hymn_shields = atk("Hymn of Shields", CardType.UTIL, 0, hymn=True)

def _hymn_shields_end(hero: Hero, ctx: Dict[str, object], _enemy: Optional[Enemy]) -> None:
    """Grant all heroes armor equal to active Hymns (capped at 3)."""
    gain = min(3, hymn_count(hero))
    for h in ctx.get("heroes", [hero]):
        h.armor_pool += gain

def _hymn_shields_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx.setdefault("end_hooks", []).append((_hymn_shields_end, None))
    def per_exchange(h: Hero, c: Dict[str, object]) -> None:
        c.setdefault("end_hooks", []).append((_hymn_shields_end, None))
    if (per_exchange, hymn_shields) not in hero.combat_effects:
        hero.combat_effects.append((per_exchange, hymn_shields))

hymn_shields.effect = _hymn_shields_fx

hymn_storms = atk("Hymn of Storms", CardType.UTIL, 0,
                  hymn=True, persistent="combat")

def _hymn_storms_end(hero: Hero, ctx: Dict[str, object],
                     _enemy: Optional[Enemy]) -> None:
    """Deal 3 D damage per active Hymn at exchange end."""
    if not ctx.get("enemies"):
        return
    dmg = 3 * hymn_count(hero)
    if dmg <= 0:
        return
    target = ctx["enemies"][0]
    target.hp -= dmg
    if target.hp <= 0:
        remove_enemy(ctx, target)

def _hymn_storms_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    ctx['hit_mod'] = ctx.get('hit_mod', 0) - 1
    ctx.setdefault('end_hooks', []).append((_hymn_storms_end, None))

hymn_storms.effect = _hymn_storms_fx

def sky_piercer_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    if ctx.get("last_misses", 0) >= 1:
        hero.gain_fate(3)
    else:
        hero.gain_fate(1)


def spear_aesir_fx(hero: Hero, ctx: Dict[str, object]) -> None:
    """Grant Armor and Fate equal to missed dice for this exchange."""
    misses = ctx.get("last_misses", 0)
    if misses:
        hero.armor_pool += misses
        hero.gain_fate(misses)

    def hook(h: Hero, _card: Card, c: Dict[str, object], dmg: int) -> int:
        m = c.get("last_misses", 0)
        if m:
            h.armor_pool += m
            h.gain_fate(m)
        return dmg

    ctx.setdefault("attack_hooks", []).append(hook)

sky_piercer = atk(
    "Sky-Piercer", CardType.RANGED, 1, Element.SPIRITUAL,
    effect=sky_piercer_fx,
)
rally = atk("Rally", CardType.UTIL, 0, effect=draw_cards(1))
spear_aesir = atk(
    "Spear of the \u00C6sir", CardType.MELEE, 1, Element.BRUTAL,
    effect=spear_aesir_fx,
)

bryn_base = [
    valkyrie_descent, valkyrie_descent,
    hymn_shields, hymn_shields,
    hymn_storms, hymn_storms,
    sky_piercer, sky_piercer,
    rally, rally,
    spear_aesir, spear_aesir,
]
_b_c = [
    atk("Lightning Crash", CardType.MELEE, 7, Element.SPIRITUAL, hit_mod=-2),
    atk("Hymn of Blades", CardType.MELEE, 0, hymn=True, persistent="combat",
        effect=exchange_damage_bonus(2)),
    atk("Favorable Winds", CardType.MELEE, 1, Element.DIVINE,
        effect=global_reroll_fx(), persistent="exchange"),
    atk("Skald's Favor", CardType.MELEE, 0,
        effect=combine_effects(gain_fate_fx(2), gain_armor(2))),
    atk("Hymn of Blood", CardType.MELEE, 0, hymn=True, persistent="combat",
        effect=hymn_of_blood_fx),
    atk("Ward of the Fallen", CardType.MELEE, 3, Element.PRECISE,
        effect=armor_from_miss_pairs(), persistent="combat"),
    atk("Spear Dive", CardType.MELEE, 2, Element.PRECISE,
        effect=fate_for_damage_mult(2)),
    atk("Tempestuous Finale", CardType.MELEE, 3, Element.BRUTAL,
        effect=tempestuous_finale_fx),
    atk("Piercer of Fates", CardType.MELEE, 4, Element.BRUTAL,
        effect=piercer_of_fates_fx),
]
_b_u = [
    atk("Hymn of Fate", CardType.MELEE, 0, hymn=True, persistent="combat", effect=hymn_of_fate_fx),
    atk("Echoes of Gungnir", CardType.MELEE, 0, effect=echoes_of_gungnir_fx, persistent="combat"),
    atk("Overflowing Grace", CardType.MELEE, 0, effect=overflowing_grace_fx, persistent="combat"),
    atk("Misfortune's Muse", CardType.MELEE, 4, Element.DIVINE, effect=misfortunes_muse_fx),
    atk("Tyr's Choice", CardType.MELEE, 2, Element.DIVINE, effect=tyrs_choice_fx),
    atk("Chorus Throw", CardType.RANGED, 4, Element.PRECISE, dmg_per_hymn=1),
    atk("Norn's Gambit", CardType.MELEE, 4, Element.PRECISE, effect=norns_gambit_fx),
    atk("Hymn of Thunder", CardType.MELEE, 0, hymn=True, persistent="combat", effect=hymn_hit_bonus(1)),
    atk("Triumphant Blow", CardType.MELEE, 4, Element.BRUTAL, effect=triumphant_blow_fx),
]
thrust_of_destiny = atk("Thrust of Destiny", CardType.MELEE, 2, Element.DIVINE, dmg_per_hymn=1)
_b_r = [
    atk("Hymn of the All-Father", CardType.MELEE, 0, hymn=True,
        persistent="combat", effect=hymn_all_father_fx),
    atk("Loki's Trickery", CardType.MELEE, 3, Element.SPIRITUAL,
        effect=lokis_trickery_fx, pre=True),
    atk("Ragnarok Call", CardType.MELEE, 4, Element.SPIRITUAL,
        effect=ragnarok_call_fx, persistent="exchange"),
    atk("Storm's Thunderlance", CardType.RANGED, 5, Element.DIVINE,
        effect=storms_thunderlance_fx, pre=True),
    atk("Freyja's Command", CardType.MELEE, 1, Element.DIVINE,
        effect=freyjas_command_fx, pre=True),
    atk("Meteor Skyfall", CardType.MELEE, 7, Element.PRECISE,
        hit_mod=-2, multi=True),
    atk("Blessing of Balder", CardType.MELEE, 0, effect=blessing_of_balder_fx),
    atk("Storm's Rhyme Crash", CardType.MELEE, 4, Element.BRUTAL,
        multi=True, effect=storms_rhyme_crash_fx, pre=True),
    atk("The Fate-Severer", CardType.MELEE, 3, Element.BRUTAL,
        effect=fate_severer_fx, pre=True),
]
b_pool = weighted_pool(_b_c, _b_u, _b_r)
HERO_RARITY_MAPS["Brynhild"] = build_rarity_map(bryn_base, _b_c, _b_u, _b_r)
brynhild = Hero("Brynhild", 18, bryn_base, b_pool)

# --- Merlin ---------------------------------------------------------------
arcane_volley = atk("Arcane Volley", CardType.RANGED, 1, Element.ARCANE, multi=True)
ladys_warden = atk(
    "Lady's Warden", CardType.MELEE, 1, Element.ARCANE,
    effect=gain_armor_self_or_ally(2)
)
weaver_of_fate = atk("Weaver of Fate", CardType.RANGED, 1, Element.DIVINE, effect=add_rerolls(2))
crystal_staff = atk(
    "Crystal Cave's Staff", CardType.MELEE, 1, Element.PRECISE,
    effect=armor_on_high_roll(), persistent="combat")
mists_of_time = atk(
    "Mists of Time", CardType.RANGED, 1, Element.SPIRITUAL,
    effect=dice_plus_one_fx, persistent="exchange")
circle_of_avalon = atk(
    "Circle of Avalon", CardType.RANGED, 1, Element.SPIRITUAL,
    effect=reroll_per_attack_all_fx(1), persistent="combat")

merlin_base = [
    arcane_volley, arcane_volley,
    ladys_warden, ladys_warden,
    weaver_of_fate, weaver_of_fate,
    crystal_staff,
    mists_of_time, mists_of_time,
    circle_of_avalon,
]

_mer_common = [
    atk("Runic Ray", CardType.RANGED, 2, Element.ARCANE, multi=True,
        effect=discard_for_area_damage(2), pre=True),
    atk("Crystal-Shot Volley", CardType.RANGED, 3, Element.ARCANE,
        effect=extra_die_on_eight(), pre=True),
    atk("Glyph-Marking Bolt", CardType.RANGED, 1, Element.ARCANE,
        effect=glyph_mark_fx, persistent="combat"),
    atk("Voice of Destiny", CardType.RANGED, 3, Element.DIVINE,
        effect=add_rerolls(2)),
    atk("Druidic Ways", CardType.RANGED, 2, Element.DIVINE,
        effect=heal_self_or_ally(1, 2)),
    atk("Protective Mists", CardType.RANGED, 0, effect=armor_per_enemy(1)),
    atk("Mark of Fated Fall", CardType.MELEE, 1, Element.ARCANE,
        effect=modify_enemy_defense(-2), persistent="combat"),
    atk("Veil-Rain of Chaos", CardType.RANGED, 1, Element.SPIRITUAL,
        multi=True, effect=veil_rain_fx, pre=True),
    atk("Oracle of Avalon", CardType.RANGED, 0, effect=gain_fate_fx(3)),
]

_mer_uncommon = [
    atk("Waves of Destiny", CardType.RANGED, 3, Element.ARCANE, multi=True,
        effect=gain_fate_per_kill(1), persistent="exchange"),
    atk("Ancestral Echoes", CardType.RANGED, 3, Element.ARCANE, multi=True,
        effect=double_rerolls_fx(), pre=True),
    atk("Whispers of the Wyrd", CardType.RANGED, 0,
        persistent="combat", effect=ally_damage_bonus(2)),
    atk("Nature's Rebuke", CardType.RANGED, 2, Element.DIVINE, multi=True,
        effect=heal_on_kill(1), persistent="combat"),
    atk("Guard from Beyond", CardType.RANGED, 0,
        effect=guard_from_beyond_fx(), persistent="exchange"),
    atk("Sage's Alacrity", CardType.RANGED, 2, Element.PRECISE,
        effect=reroll_per_attack_fx(2), persistent="combat"),
    atk("Charged Spirits", CardType.RANGED, 2, Element.SPIRITUAL, multi=True,
        effect=fate_for_damage_scaled(5), pre=True),
    atk("Avalon's Light", CardType.RANGED, 3, Element.SPIRITUAL,
        persistent="combat", effect=crits_are_four()),
    atk("Spiritual Gifts", CardType.RANGED, 4, Element.SPIRITUAL,
        effect=spiritual_gifts_fx()),
]

_mer_rare = [
    atk("Rune Shatter", CardType.RANGED, 3, Element.ARCANE, multi=True,
        effect=modify_enemy_defense(-1), persistent="exchange"),
    atk("Sigil of Final Fate", CardType.RANGED, 0,
        persistent="combat", effect=ones_are_eights()),
    atk("Conflux Lance", CardType.RANGED, 5, Element.ARCANE,
        effect=conflux_lance_fx, pre=True),
    atk("Echoes of Guidance", CardType.RANGED, 0,
        effect=echoes_of_guidance_fx, pre=True),
    atk("Mercury Guard", CardType.RANGED, 0, persistent="combat",
        effect=armor_each_exchange_per_enemy()),
    atk("Old-Ways Shillelagh", CardType.MELEE, 3, Element.PRECISE,
        effect=armor_per_hit(1)),
    atk("Favor of the Druids", CardType.RANGED, 1, Element.SPIRITUAL,
        effect=draw_for_all(1)),
    atk("Chains of Morrígan", CardType.RANGED, 0,
        effect=chains_of_morrigan_fx, persistent="exchange"),
    atk("Spirits of the Lands", CardType.RANGED, 4, Element.SPIRITUAL,
        effect=gain_fate_from_attacks()),
]

merlin_pool = weighted_pool(_mer_common, _mer_uncommon, _mer_rare)
HERO_RARITY_MAPS["Merlin"] = build_rarity_map(
    merlin_base, _mer_common, _mer_uncommon, _mer_rare
)
merlin = Hero("Merlin", 15, merlin_base, merlin_pool)

# --- Musashi ---------------------------------------------------------------
swallow_cut = atk(
    "Swallow-Cut", CardType.MELEE, 1, Element.PRECISE,
    effect=vulnerability_bonus(Element.PRECISE, 2), pre=True
)
cross_river = atk(
    "Cross-River Strike", CardType.MELEE, 2, Element.PRECISE,
    multi=True, max_targets=2
)
heaven_earth = atk(
    "Heaven-and-Earth Slash", CardType.MELEE, 2, Element.BRUTAL,
    effect=choose_element(), pre=True
)
flowing_water = atk(
    "Flowing Water Parry", CardType.MELEE, 1, Element.SPIRITUAL,
    armor=1, before_ranged=True
)
dual_moon_guard = atk(
    "Dual-Moon Guard", CardType.MELEE, 1, Element.DIVINE,
    effect=dual_moon_guard_fx, pre=True
)
wind_read = atk(
    "Wind-Reading Focus", CardType.MELEE, 1, Element.ARCANE,
    effect=choose_element()
)

musashi_base = [
    swallow_cut, swallow_cut,
    cross_river, cross_river,
    heaven_earth, heaven_earth,
    flowing_water, flowing_water,
    dual_moon_guard,
    wind_read,
]

battojutsu_strike = atk(
    "Battojutsu Strike", CardType.MELEE, 2, Element.PRECISE,
    armor=1, before_ranged=True
)
scroll_cut_slash = atk(
    "Scroll-Cut Slash", CardType.MELEE, 3, Element.PRECISE,
    multi=True, max_targets=2
)
chance_seizing = atk("Chance-Seizing Blade", CardType.MELEE, 1, Element.BRUTAL,
    effect=chance_seizing_fx)
susanoo_cut = atk("Susanoo-Descent Cut", CardType.MELEE, 3, Element.BRUTAL,
    effect=susanoo_cut_fx)
water_mirror_split = atk("Water-Mirror Split", CardType.MELEE, 0,
    effect=water_mirror_split_fx)
spirit_cleaver = atk(
    "Spirit-Cleaver", CardType.MELEE, 2, Element.SPIRITUAL,
    effect=choose_element()
)
iron_will_guard = atk("Iron-Will Guard", CardType.RANGED, 0,
    effect=iron_will_guard_fx)
ghost_step_slash = atk("Ghost-Step Slash", CardType.MELEE, 3, Element.DIVINE,
    effect=ghost_step_slash_fx)
heavenly_dragon = atk("Heavenly-Dragon Stance", CardType.MELEE, 2,
    Element.ARCANE, effect=heavenly_dragon_fx)

_m_common = [
    battojutsu_strike,
    scroll_cut_slash,
    chance_seizing,
    susanoo_cut,
    water_mirror_split,
    spirit_cleaver,
    iron_will_guard,
    ghost_step_slash,
    heavenly_dragon,
]

seizing_dragon = atk(
    "Seizing-Dragon Slice", CardType.MELEE, 3, Element.PRECISE,
    effect=vulnerability_bonus(Element.PRECISE, 4), pre=True
)
two_heaven_blitz = atk(
    "Two-Heaven Blitz", CardType.MELEE, 4, Element.PRECISE,
    multi=True, max_targets=2
)
crescent_guard = atk("Crescent-Moon Guard", CardType.RANGED, 0,
    effect=crescent_guard_fx)
mountain_stance = atk("Mountain-Strike Stance", CardType.MELEE, 0,
    persistent="combat", effect=mountain_stance_fx)
mirror_flow = atk("Mirror-Flow Style", CardType.MELEE, 0,
    persistent="combat", effect=mirror_flow_fx)
heaven_defying = atk("Heaven-Defying Blade", CardType.MELEE, 0,
    persistent="combat", effect=heaven_defying_fx)
ascending_veng = atk("Ascending Vengeance", CardType.MELEE, 0,
    persistent="combat", effect=ascending_veng_fx)
menacing_step = atk("Menacing Step", CardType.MELEE, 0,
    effect=menacing_step_fx)
iron_shell = atk("Iron-Shell Posture", CardType.MELEE, 0,
    persistent="combat", effect=iron_shell_fx)

_m_uncommon = [
    seizing_dragon,
    two_heaven_blitz,
    crescent_guard,
    mountain_stance,
    mirror_flow,
    heaven_defying,
    ascending_veng,
    menacing_step,
    iron_shell,
]

final_dragon = atk(
    "Final-Dragon Slash", CardType.MELEE, 2, Element.PRECISE,
    effect=vulnerability_bonus(Element.PRECISE, 7), pre=True
)
five_ring = atk(
    "Five-Ring Convergence", CardType.MELEE, 2, Element.PRECISE,
    effect=five_ring_fx, persistent="combat"
)
wanderer_blade = atk(
    "The Wanderer's Blade", CardType.MELEE, 2, Element.BRUTAL,
    effect=wanderer_blade_fx, persistent="combat"
)
formless = atk(
    "Formless Principle", CardType.MELEE, 0,
    effect=formless_fx, persistent="combat"
)
stone_lotus = atk(
    "Stone-Lotus Slash", CardType.MELEE, 4, Element.SPIRITUAL,
    effect=stone_lotus_fx
)
twin_dragon = atk(
    "Twin-Dragon Descent", CardType.MELEE, 0, multi=True,
    effect=twin_dragon_fx, persistent="exchange"
)
edge_harmony = atk(
    "Edge of Harmony", CardType.MELEE, 4, Element.DIVINE,
    effect=edge_harmony_fx
)
two_strikes = atk(
    "Two-Strikes as One", CardType.MELEE, 3, Element.DIVINE,
    multi=True, max_targets=2, effect=two_strikes_fx
)
moment_perf = atk(
    "Moment of Perfection", CardType.RANGED, 0,
    effect=moment_perf_fx
)

_m_rare = [
    final_dragon,
    five_ring,
    wanderer_blade,
    formless,
    stone_lotus,
    twin_dragon,
    edge_harmony,
    two_strikes,
    moment_perf,
]

musashi_pool = weighted_pool(_m_common, _m_uncommon, _m_rare)
HERO_RARITY_MAPS["Musashi"] = build_rarity_map(
    musashi_base, _m_common, _m_uncommon, _m_rare
)
musashi = Hero("Musashi", 20, musashi_base, musashi_pool)


HEROES = [hercules, brynhild, merlin, musashi]

# track total damage each enemy inflicts on heroes across simulations
MONSTER_DAMAGE: Dict[Tuple[str, str], int] = defaultdict(int)

# track how often each enemy type appears in a run and whether that run wins
# the mapping is hero -> enemy base name -> variant -> win/loss counts
ENEMY_RUN_COUNTS: Dict[str, Dict[str, Dict[str, Dict[str, int]]]] = defaultdict(
    lambda: defaultdict(lambda: {
        "common": {"win": 0, "loss": 0},
        "elite": {"win": 0, "loss": 0},
    })
)

# accumulate win/loss stats for card usage
CARD_CORRELATIONS: Dict[str, Dict[str, Dict[str, Dict[str, int]]]] = defaultdict(
    lambda: {
        "base": defaultdict(lambda: {"win": 0, "loss": 0}),
        "common": defaultdict(lambda: {"win": 0, "loss": 0}),
        "uncommon": defaultdict(lambda: {"win": 0, "loss": 0}),
        "rare": defaultdict(lambda: {"win": 0, "loss": 0}),
    }
)

from collections import Counter

def _record_run_result(hero: Hero, won: bool) -> None:
    stats = CARD_CORRELATIONS[hero.name]
    result_key = "win" if won else "loss"
    counts = Counter(hero.combat_record.get("drawn", {}))
    counts.update(hero.combat_record.get("played", {}))
    for name, n in counts.items():
        rarity = hero.card_rarity.get(name, "base")
        stats[rarity][name][result_key] += n

def get_card_correlations() -> Dict[str, Dict[str, Dict[str, Dict[str, int]]]]:
    """Return aggregated card win/loss counts for each hero."""
    return CARD_CORRELATIONS


def _record_enemy_run(hero_name: str, names: List[str], won: bool) -> None:
    """Update enemy appearance counts for a completed run."""
    result_key = "win" if won else "loss"
    for name in set(names):
        variant = "elite" if name.startswith("Elite ") else "common"
        base = name[6:] if variant == "elite" else name
        ENEMY_RUN_COUNTS[hero_name][base][variant][result_key] += 1


def get_enemy_run_counts() -> Dict[str, Dict[str, Dict[str, Dict[str, int]]]]:
    """Return aggregated win/loss counts for enemy appearances."""
    return ENEMY_RUN_COUNTS


def get_monster_damage() -> Dict[Tuple[str, str], int]:
    """Return total damage dealt by each enemy to each hero."""
    return MONSTER_DAMAGE

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
    "Spinner": Enemy("Spinner", 1, 4, Element.SPIRITUAL, [1, 0, 1, 0], web_slinger),
    "Soldier": Enemy("Soldier", 2, 5, Element.PRECISE, [0, 0, 0, 2], "dark-phalanx"),
    "Void Soldier": Enemy("Void Soldier", 2, 5, Element.PRECISE, [0, 0, 0, 2], "void-soldier", attack_mod=void_soldier_mod),
    "Banshee": Enemy("Banshee", 4, 5, Element.DIVINE, [0, 0, 1, 3], "banshee-wail", end_fx=end_banshee_wail),
    "Priest": Enemy("Priest", 2, 3, Element.ARCANE, [0, 0, 1, 1], power_of_death),
    "Dryad": Enemy("Dryad", 2, 4, Element.BRUTAL, [0, 0, 1, 1], "cursed-thorns", end_fx=end_cursed_thorns),
    "Minotaur": Enemy("Minotaur", 4, 3, Element.PRECISE, [0, 0, 1, 3], "cleave_all"),
    "Wizard": Enemy("Wizard", 2, 3, Element.BRUTAL, [0, 1, 1, 3], "curse-of-torment"),
    "Shadow Banshee": Enemy(
        "Shadow Banshee", 3, 5, Element.DIVINE, [0, 0, 1, 2],
        ability=None, start_fx=ghostly
    ),
    "Gryphon": Enemy("Gryphon", 4, 5, Element.SPIRITUAL, [0, 1, 3, 4], "aerial-combat"),
    "Treant": Enemy("Treant", 7, 6, Element.DIVINE, [0, 1, 1, 4], "power-sap", end_fx=end_power_sap),
    "Angel": Enemy("Angel", 5, 5, Element.ARCANE, [0, 1, 2, 5], "corrupted-destiny"),
    "Elite Spinner": Enemy("Elite Spinner", 2, 5, Element.SPIRITUAL, [0, 0, 1, 4], "sticky-web"),
    "Elite Soldier": Enemy("Elite Soldier", 3, 6, Element.PRECISE, [0, 0, 1, 3], "spiked-armor"),
    "Elite Priest": Enemy("Elite Priest", 3, 4, Element.ARCANE, [0, 0, 1, 2], silence),
    "Elite Dryad": Enemy("Elite Dryad", 2, 5, Element.BRUTAL, [0, 1, 1, 2], "disturbed-flow"),
    "Elite Minotaur": Enemy("Elite Minotaur", 5, 3, Element.PRECISE, [0, 0, 2, 4], "enrage"),
    "Elite Wizard": Enemy("Elite Wizard", 2, 4, Element.BRUTAL, [0, 2, 2, 3], "void-barrier"),
    "Elite Banshee": Enemy("Elite Banshee", 4, 5, Element.DIVINE, [0, 0, 1, 3], "banshee-wail", end_fx=end_banshee_wail),
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
                armor_pool=0,
                barrier_elems=set(),
                rolled_dice=0,
                attack_mod=tmpl.attack_mod,
                start_fx=tmpl.start_fx,
                end_fx=tmpl.end_fx,
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
    ("Gryphon", 1),
    ("Treant", 1),
    ("Angel", 1),
    ("Elite Spinner", 3),
    ("Elite Soldier", 3),
    ("Elite Priest", 3),
    ("Elite Dryad", 3),
    ("Elite Minotaur", 2),
    ("Elite Wizard", 2),
    ("Elite Banshee", 2),
    ("Elite Gryphon", 1),
    ("Elite Treant", 1),
    ("Elite Angel", 1),
]


# ---------------------------------------------------------------------------
# Combat helpers
# ---------------------------------------------------------------------------
def resolve_attack(hero: Hero, card: Card, ctx: Dict[str, object]) -> None:
    """Resolve ``card`` against current enemies in ``ctx``."""
    depth = ctx.get('attack_depth', 0)
    if depth >= ATTACK_DEPTH_LIMIT:
        return
    ctx['attack_depth'] = depth + 1

    enemies: List[Enemy] = ctx["enemies"]
    if not enemies:
        if depth == 0:
            ctx.pop('attack_depth', None)
        else:
            ctx['attack_depth'] = depth
        return
    if hasattr(hero, "combat_record"):
        hero.combat_record["played"][card.name] += 1

    repeat = ctx.pop('double_next', False)
    orig_card = card
    if ctx.pop('split_next', False) and not card.multi:
        card = Card(card.name, card.ctype, card.dice, card.element,
                    card.armor, card.effect, card.persistent, card.hymn,
                    True, 2, card.dmg_per_hymn, card.pre, card.before_ranged,
                    card.hit_mod)

    blocks = ctx.setdefault("ephemeral_block", set())
    if card.effect and not ctx.get("silenced") and card.pre:
        prev_marker = ctx.get('_src_card')
        ctx['_src_card'] = orig_card
        card.effect(hero, ctx)
        if card.persistent:
            if card.persistent == "combat":
                _add_persistent(hero.combat_effects, card.effect, orig_card)
            elif card.persistent == "exchange":
                _add_persistent(hero.exchange_effects, card.effect, orig_card)
        if prev_marker is None:
            ctx.pop('_src_card', None)
        else:
            ctx['_src_card'] = prev_marker
        enemies = ctx["enemies"]
        if not enemies:
            if depth == 0:
                ctx.pop('attack_depth', None)
            else:
                ctx['attack_depth'] = depth
            return
    if card.multi:
        if card.max_targets is None:
            targets = enemies[:]
        else:
            targets = enemies[:card.max_targets]
    else:
        targets = [enemies[0]]
    if targets:
        ctx['last_target'] = targets[0]
    allow_reroll = not ctx.get("no_reroll", False)
    rer_bonus = ctx.pop('extra_rerolls', 0)
    if ctx.get('double_rerolls'):
        rer_bonus *= 2
    g_reroll = ctx.get('global_reroll')
    if g_reroll:
        if g_reroll is True:
            rer_bonus += card.dice
        else:
            rer_bonus += int(g_reroll)
    killed_any = False
    killed_count = 0
    for e in targets[:]:
        actual_type = CardType.MELEE if ctx.get("ranged_to_melee") and card.ctype == CardType.RANGED else card.ctype
        mod = -1 if (actual_type == CardType.MELEE and e.ability == "aerial-combat") else 0
        mod += ctx.pop('hit_mod', 0)
        mod += card.hit_mod
        if e.ability == "banshee-wail":
            e.rolled_dice += card.dice
        vuln = ctx.pop("temp_vuln", e.vulnerability)
        elem = ctx.pop('next_element', card.element)
        ctx['last_element'] = elem
        def_mod = 0
        for hook in ctx.get('pre_attack_hooks', []):
            new = hook(hero, card, ctx, e, elem, vuln)
            if isinstance(new, int):
                def_mod += new
        hits = roll_hits(
            card.dice,
            e.defense + ctx.get("enemy_defense_mod", 0) + def_mod,
            mod,
            hero=hero,
            element=elem,
            vulnerability=vuln,
            enemy=e,
            free_rerolls=rer_bonus,
            ctx=ctx,
        )
        if e.ability == "roots-of-despair":
            roots_of_despair(hero, card.dice > 0 and hits == 0)
        dmg = hits
        for fx in ctx.get("attack_hooks", []):
            dmg = fx(hero, card, ctx, dmg)
        blocked = False
        if id(e) in blocks and e.ability == "ephemeral-wings":
            dmg = 0
            blocks.remove(id(e))
            blocked = True
        if card.multi and e.ability == "dark-phalanx":
            dmg = dark_phalanx(enemies, dmg)
        area = ctx.pop("area_damage", 0)
        dmg += area
        dmg += ctx.pop("bonus_damage", 0)
        if card.dmg_per_hymn:
            dmg += damage_from_hymns(hero, card.dmg_per_hymn)
        dmg += ctx.get("hymn_damage", 0)
        dmg += ctx.get("exchange_bonus", 0)
        soak = min(e.armor_pool, dmg)
        e.armor_pool -= soak
        dmg -= soak
        e.hp -= dmg
        if e.ability == "void-barrier":
            void_barrier(e, elem)
        if e.ability == "spiked-armor":
            spiked_armor(hero, dmg)
        if e.ability == "ephemeral-wings":
            blocks.add(id(e))

        if e.hp <= 0:
            remove_enemy(ctx, e)
            if e.ability == "power-of-death" or e.ability is power_of_death:
                ctx["dead_priests"] = ctx.get("dead_priests", 0) + 1
                ctx["priest_bonus"] = ctx["dead_priests"]
            killed_any = True
            killed_count += 1
    ctx.setdefault('played_attacks', []).append((orig_card.name, elem))
    if card.effect and not ctx.get("silenced") and not card.pre:
        ctx['killed'] = killed_any
        ctx['killed_count'] = killed_count
        prev_marker = ctx.get('_src_card')
        ctx['_src_card'] = orig_card
        card.effect(hero, ctx)
        for fx in ctx.get('post_attack_hooks', []):
            fx(hero, ctx)
        ctx.pop('killed', None)
        ctx.pop('killed_count', None)
        if card.persistent:
            if card.persistent == "combat":
                _add_persistent(hero.combat_effects, card.effect, orig_card)
            elif card.persistent == "exchange":
                _add_persistent(hero.exchange_effects, card.effect, orig_card)
        if prev_marker is None:
            ctx.pop('_src_card', None)
        else:
            ctx['_src_card'] = prev_marker
    if not card.effect or card.pre:
        for fx in ctx.get('post_attack_hooks', []):
            fx(hero, ctx)
    if card.hymn:
        hero.active_hymns.append(card)
    hero.deck.disc.append(orig_card)
    ctx['attacks_used'] = ctx.get('attacks_used', 0) + 1
    if orig_card.dice > 0:
        ctx['dice_played'] = True
    ctx.pop('double_rerolls', None)

    if repeat and ctx.get('enemies') and hero.hp > 0:
        temp = Card(
            card.name,
            card.ctype,
            card.dice,
            card.element,
            card.armor,
            card.effect,
            card.persistent,
            card.hymn,
            card.multi,
            card.max_targets,
            card.dmg_per_hymn,
            card.pre,
            card.before_ranged,
            card.hit_mod,
        )
        resolve_attack(hero, temp, ctx)

    if depth == 0:
        ctx.pop('attack_depth', None)
    else:
        ctx['attack_depth'] = depth


def monster_attack(heroes: List[Hero], ctx: Dict[str, object]) -> None:
    """Resolve monster attacks for the current wave."""

    def apply(hero: Hero, enemy: Optional[Enemy], dmg: int) -> None:
        soak = min(hero.armor_pool, dmg)
        hero.armor_pool -= soak
        taken = max(0, dmg - soak)
        if MIN_DAMAGE and dmg > 0 and taken == 0:
            taken = 1
        hero.hp -= taken
        if enemy:
            MONSTER_DAMAGE[(hero.name, enemy.name)] += taken
        if enemy:
            if ctx.get('iron_shell') and soak >= dmg:
                enemy.hp -= 2
            if ctx.get('ascending_veng') and soak > 0:
                enemy.hp -= soak // 2
            if enemy.hp <= 0:
                remove_enemy(ctx, enemy)

    bonus = ctx.get("priest_bonus", 0)
    for e in ctx["enemies"][:]:
        attacks = 2 if e.ability == "enrage" and enrage(e) else 1
        for _ in range(attacks):
            band = e.damage_band
            dmg = band[(d8() - 1) // 2]
            if e.ability == "cleave_all":
                cleave_all(heroes, dmg)
            else:
                target = ctx.get('forced_target', heroes[0])
                apply(target, e, dmg)

    if bonus:
        target = ctx.get('forced_target', heroes[0])
        apply(target, None, bonus)

# very small fight simulation -------------------------------------------------

def fight_one(
    hero: Hero,
    hp_log: list[int] | None = None,
    *,
    timeout: float | None = None,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = None,
    max_total_exchanges: int | None = None,
) -> bool:
    """Run one full gauntlet for ``hero``.

    Parameters
    ----------
    hero:
        The :class:`Hero` to run through the gauntlet.
    hp_log:
        Optional list that, if provided, receives the hero's remaining hit
        points after each completed wave.
    max_exchanges:
        Abort a wave with :class:`TimeoutError` if this many exchanges are
        reached. The default of ``1000`` serves as a safeguard against runaway
        loops.
    wave_timeout:
        Abort the current wave with :class:`TimeoutError` if it runs longer
        than this many seconds.
    max_total_exchanges:
        Abort the gauntlet with :class:`TimeoutError` once this many exchanges
        have occurred across all waves.
    """

    MONSTER_DAMAGE.clear()
    hero.reset()
    hero.deck.start_combat()
    start = time.time()
    total_exchanges = 0
    run_waves = [name for name, _ in ENEMY_WAVES]

    for name, count in ENEMY_WAVES:
        ctx = make_wave(name, count)
        ctx["heroes"] = [hero]
        exch = 0
        wave_start = time.time()
        ctx["next_draw"] = 1
        while True:
            if max_exchanges is not None and exch >= max_exchanges:
                raise TimeoutError(
                    f"{hero.name} timed out on wave {name}")
            if max_total_exchanges is not None and total_exchanges >= max_total_exchanges:
                raise TimeoutError(
                    f"{hero.name} timed out on wave {name}")
            if timeout is not None and time.time() - start > timeout:
                raise TimeoutError(
                    f"{hero.name} timed out on wave {name}")
            if wave_timeout is not None and time.time() - wave_start > wave_timeout:
                raise TimeoutError(
                    f"{hero.name} timed out on wave {name}")
            if not hero.deck.hand and ctx.get("next_draw", 1) == 0:
                break
            ctx["exchange"] = exch
            # remove any lingering exchange effects and hymns from the previous
            # round before applying persistent buffs
            if hero.exchange_effects:
                hero.exchange_effects.clear()
            if hero.active_hymns:
                hero.active_hymns = [h for h in hero.active_hymns
                                     if h.persistent == "combat"]
            for e in ctx["enemies"]:
                e.rolled_dice = 0
                if e.ability == "corrupted-destiny":
                    corrupted_destiny(hero)
            if any((e.ability == "silence" or e.ability is silence) for e in ctx["enemies"]):
                if not ctx.get("silenced"):
                    ctx["silenced"] = True
                    hero.combat_effects.clear()
                    hero.exchange_effects.clear()
                    hero.active_hymns.clear()
            ctx["ranged_to_melee"] = False
            ctx["draw_penalty"] = 0
            ctx["enemy_defense_mod"] = 0
            ctx["hymn_damage"] = 0
            ctx["extra_rerolls"] = 0
            ctx["global_reroll"] = False
            ctx["reroll_misses_once"] = False
            ctx["exchange_bonus"] = 0
            ctx["attacks_used"] = 0
            ctx["dice_played"] = False
            ctx["played_attacks"] = []
            apply_persistent(hero, ctx)
            ctx["attack_hooks"] = []
            ctx["start_hooks"] = []
            ctx["end_hooks"] = []
            ctx["post_attack_hooks"] = []
            for e in ctx["enemies"]:
                if e.start_fx:
                    ctx["start_hooks"].append((e.start_fx, e))
                if callable(e.ability):
                    e.ability(ctx)
                if e.attack_mod and e.attack_mod not in ctx["attack_hooks"]:
                    ctx["attack_hooks"].append(e.attack_mod)
                if e.end_fx:
                    ctx["end_hooks"].append((e.end_fx, e))

            if ctx.get("start_hooks"):
                for fx, enemy in ctx["start_hooks"]:
                    fx(ctx)

            # utilities first
            c = hero.deck.pop_first(CardType.UTIL)
            if c:
                resolve_attack(hero, c, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            # melee cards that resolve before ranged
            while ctx["enemies"]:
                if timeout is not None and time.time() - start > timeout:
                    raise TimeoutError(
                        f"{hero.name} timed out on wave {name}")
                pre_card = None
                for i, card in enumerate(hero.deck.hand):
                    if card.ctype == CardType.MELEE and card.before_ranged:
                        pre_card = hero.deck.hand.pop(i)
                        break
                if not pre_card:
                    break
                resolve_attack(hero, pre_card, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            delayed: List[Card] = []
            while ctx["enemies"]:
                if timeout is not None and time.time() - start > timeout:
                    raise TimeoutError(
                        f"{hero.name} timed out on wave {name}")
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
                if timeout is not None and time.time() - start > timeout:
                    raise TimeoutError(
                        f"{hero.name} timed out on wave {name}")
                monster_attack([hero], ctx)
                if hero.hp <= 0:
                    return False

            for card in delayed:
                if timeout is not None and time.time() - start > timeout:
                    raise TimeoutError(
                        f"{hero.name} timed out on wave {name}")
                if not ctx["enemies"]:
                    break
                resolve_attack(hero, card, ctx)

            while ctx["enemies"]:
                if timeout is not None and time.time() - start > timeout:
                    raise TimeoutError(
                        f"{hero.name} timed out on wave {name}")
                c = hero.deck.pop_first(CardType.MELEE)
                if not c:
                    break
                resolve_attack(hero, c, ctx)
                if hero.hp <= 0 or not ctx["enemies"]:
                    break

            # end-of-exchange abilities
            if ctx.get("end_hooks"):
                for fx, enemy in ctx["end_hooks"]:
                    fx(hero, ctx, enemy)


            if not ctx["enemies"]:
                break

            draw_amt = max(
                0,
                ctx.get("attacks_used", 0) - 1 - ctx.get("draw_penalty", 0),
            )
            if draw_amt:
                hero.deck.draw(draw_amt)
            ctx["next_draw"] = draw_amt
            exch += 1
            total_exchanges += 1

        if ctx["enemies"] or hero.hp <= 0:
            _record_run_result(hero, False)
            _record_enemy_run(hero.name, run_waves, False)
            return False

        if hp_log is not None:
            hp_log.append(hero.hp)

        hero.gain_upgrades(1)
        hero.gain_fate(1)
        hero.deck.draw(3)
        hero.combat_effects.clear()
        hero.exchange_effects.clear()
        hero.active_hymns.clear()

    win = hero.hp > 0
    _record_run_result(hero, win)
    _record_enemy_run(hero.name, run_waves, win)
    return win

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    N = 20
    wins = sum(fight_one(random.choice(HEROES)) for _ in range(N))
    print("Win rate", wins / N)
