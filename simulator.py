import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional


def roll_dice(dice: str) -> int:
    """Parse a dice string like '2d6' and roll it."""
    try:
        count, sides = map(int, dice.lower().split("d"))
    except Exception:
        return 0
    return sum(random.randint(1, sides) for _ in range(count))


def parse_dice(dice: str) -> (int, int):
    """Return (count, sides) for a dice string like '2d6'."""
    try:
        count, sides = map(int, dice.lower().split("d"))
    except Exception:
        return 0, 0
    return count, sides


@dataclass
class Card:
    """Representation of an ability card."""
    name: str
    type: str  # 'melee' or 'ranged'
    dice: str
    effects: Dict[str, int] = field(default_factory=dict)
    rarity: str = "common"  # 'common', 'uncommon', or 'rare'
    upgrade: bool = False

    def roll(self) -> int:
        return roll_dice(self.dice)


@dataclass
class Hero:
    name: str
    hp: int
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    armor: int = 0
    fate: int = 0

    def draw(self, count: int = 1) -> None:
        for _ in range(count):
            if not self.deck and self.discard:
                random.shuffle(self.discard)
                self.deck.extend(self.discard)
                self.discard.clear()
            if self.deck:
                self.hand.append(self.deck.pop(0))
            if len(self.hand) > 7:
                idx = next((i for i, c in enumerate(self.hand) if not c.upgrade), 0)
                self.discard.append(self.hand.pop(idx))

    def commit_card(self, index: int) -> Card:
        card = self.hand.pop(index)
        self.discard.append(card)
        return card

    def add_armor(self, amount: int) -> None:
        self.armor += amount

    def reset_armor(self) -> None:
        self.armor = 0

    def apply_damage(self, dmg: int) -> None:
        block = min(self.armor, dmg)
        self.armor -= block
        dmg -= block
        if dmg > 0:
            if self.fate > 0:
                dmg -= 1
            if dmg > 0:
                self.hp -= dmg


@dataclass
class Monster:
    name: str
    hp: int
    defense: int
    type: str
    abilities: List[str] = field(default_factory=list)
    action_table: List[Dict[str, int]] = field(default_factory=lambda: [
        {"damage": 1, "armor": 0},
        {"damage": 1, "armor": 1},
        {"damage": 2, "armor": 0},
        {"damage": 3, "armor": 1},
    ])
    armor: int = 0

    def roll_action(self) -> (int, int):
        """Return (damage, armor) for the exchange using a d8 table."""
        roll = random.randint(1, 8)
        idx = (roll - 1) // 2
        entry = self.action_table[min(idx, len(self.action_table) - 1)]
        damage = entry.get("damage", 0)
        armor = entry.get("armor", 0)
        if "tough" in self.abilities:
            armor += 1
        return damage, armor


# Generic action tables used for monsters. Each entry corresponds to
# results for d8 rolls of 1-2, 3-4, 5-6 and 7-8 respectively.
BASIC_ACTION_TABLE = [
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 1},
    {"damage": 2, "armor": 0},
    {"damage": 3, "armor": 1},
]

ELITE_ACTION_TABLE = [
    {"damage": 1, "armor": 1},
    {"damage": 2, "armor": 1},
    {"damage": 3, "armor": 1},
    {"damage": 4, "armor": 2},
]


@dataclass
class EnemyGroup:
    """Collection of identical monsters appearing together."""

    count: int
    monster: Monster


# Enemy groups from the design reference
BASIC_GROUPS: List[EnemyGroup] = [
    EnemyGroup(3, Monster("Shadow Spinner", hp=1, defense=4, type="spiritual",
                          abilities=["Web Slinger"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(3, Monster("Void Soldier", hp=2, defense=5, type="precise",
                          abilities=["Dark Phalanx"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(3, Monster("Priest of Oblivion", hp=2, defense=3, type="arcane",
                          abilities=["Power of Death"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(3, Monster("Corrupted Dryad", hp=2, defense=4, type="brutal",
                          abilities=["Cursed Thorns"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(2, Monster("Dark Minotaur", hp=4, defense=3, type="precise",
                          abilities=["Cleaving and Stomping"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(2, Monster("Dark Wizard", hp=2, defense=3, type="brutal",
                          abilities=["Curse of Torment"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(2, Monster("Shadow Banshee", hp=3, defense=5, type="divine",
                          abilities=["Ghostly"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(1, Monster("Void Gryphon", hp=4, defense=5, type="spiritual",
                          abilities=["Aerial Combat"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(1, Monster("Void Treant", hp=7, defense=6, type="divine",
                          abilities=["Power Sap"],
                          action_table=BASIC_ACTION_TABLE)),
    EnemyGroup(1, Monster("Corrupted Angel", hp=5, defense=5, type="arcane",
                          abilities=["Corrupted Destiny"],
                          action_table=BASIC_ACTION_TABLE)),
]

ELITE_GROUPS: List[EnemyGroup] = [
    EnemyGroup(3, Monster("Shadow Spinner", hp=2, defense=5, type="spiritual",
                          abilities=["Sticky Web"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(3, Monster("Void Soldier", hp=3, defense=6, type="precise",
                          abilities=["Spiked Armor"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(3, Monster("Priest of Oblivion", hp=3, defense=4, type="arcane",
                          abilities=["Silence"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(3, Monster("Corrupted Dryad", hp=2, defense=5, type="brutal",
                          abilities=["Disturbed Flow"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(2, Monster("Dark Minotaur", hp=5, defense=3, type="precise",
                          abilities=["Enrage"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(2, Monster("Dark Wizard", hp=2, defense=4, type="brutal",
                          abilities=["Void Barrier"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(2, Monster("Shadow Banshee", hp=4, defense=5, type="divine",
                          abilities=["Banshee Wail"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(1, Monster("Void Gryphon", hp=5, defense=5, type="spiritual",
                          abilities=["Ephemeral Wings"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(1, Monster("Void Treant", hp=8, defense=7, type="divine",
                          abilities=["Roots of Despair"],
                          action_table=ELITE_ACTION_TABLE)),
    EnemyGroup(1, Monster("Corrupted Angel", hp=7, defense=6, type="arcane",
                          abilities=["Denied Heaven"],
                          action_table=ELITE_ACTION_TABLE)),
]


class Combat:
    """Run a combat between a hero and a monster."""

    def __init__(self, hero: Hero, monster: Monster):
        self.hero = hero
        self.monster = monster
        self.round = 0

    def exchange(self) -> bool:
        """Run a single exchange. Return True if both combatants live."""
        draw_seq = [3, 2, 1, 0]
        draw_amt = draw_seq[self.round] if self.round < len(draw_seq) else 0
        if "Sticky Web" in self.monster.abilities:
            draw_amt = max(0, draw_amt - 1)
        if "Corrupted Destiny" in self.monster.abilities:
            self.hero.fate = max(0, self.hero.fate - 2)
        if "Ghostly" in self.monster.abilities and self.round >= 3:
            return False
        if self.round < len(draw_seq):
            self.hero.draw(draw_amt)
        self.round += 1

        is_web = "Web Slinger" in self.monster.abilities

        ranged = [c for c in self.hero.hand if c.type == "ranged"]
        melee = [c for c in self.hero.hand if c.type == "melee"]
        order = melee + ranged if is_web else ranged + melee
        # remaining cards are processed sequentially and can be removed by
        # abilities like Disrupt
        # use the same list so discarded cards disappear from the hand
        self.hero.hand = order

        cancel_next = "cancel" in self.monster.abilities

        dice_count = 0
        skip_next = False

        # Process cards sequentially
        while order:
            card = order.pop(0)
            if cancel_next:
                cancel_next = False
                self.hero.discard.append(card)
                continue

            if "disrupt" in self.monster.abilities and order:
                idx = random.randrange(len(order))
                self.hero.discard.append(order.pop(idx))

            dmg = 0
            count, sides = parse_dice(card.dice)
            dice_count += count
            rerolls = 0
            hits = 0
            target_def = self.monster.defense
            card_type = card.type
            if is_web and card.type == "ranged":
                card_type = "melee"
            if "Aerial Combat" in self.monster.abilities and card_type == "melee":
                target_def += 1
            card_rerolls = card.effects.get("reroll", 0)
            for _ in range(count):
                result = random.randint(1, sides)
                while "Denied Heaven" in self.monster.abilities and result == 8:
                    result = random.randint(1, sides)
                while (result < target_def and card_rerolls > 0 and
                       "Disturbed Flow" not in self.monster.abilities):
                    card_rerolls -= 1
                    result = random.randint(1, sides)
                    while "Denied Heaven" in self.monster.abilities and result == 8:
                        result = random.randint(1, sides)
                while (result < target_def and self.hero.fate > 0 and
                       rerolls < 2 and self.monster.hp <= 2 and
                       "Disturbed Flow" not in self.monster.abilities):
                    self.hero.fate -= 1
                    rerolls += 1
                    result = random.randint(1, sides)
                    while "Denied Heaven" in self.monster.abilities and result == 8:
                        result = random.randint(1, sides)
                if result in (1, 2) and "Curse of Torment" in self.monster.abilities:
                    self.hero.apply_damage(1)
                if result >= target_def:
                    hit = 2 if random.random() < 0.2 else 1
                    dmg += hit
                    hits += 1
            if hits == 0 and "Roots of Despair" in self.monster.abilities:
                self.hero.apply_damage(1)

            if "Silence" not in self.monster.abilities:
                dmg += card.effects.get("damage", 0)
                arm = card.effects.get("armor", 0)
                per_hit = card.effects.get("armor_per_hit", 0)
            else:
                arm = 0
                per_hit = 0
            self.hero.add_armor(arm + per_hit * hits)
            self.hero.fate += card.effects.get("fate", 0)

            if skip_next:
                dmg = 0
                skip_next = False

            actual = max(0, dmg - self.monster.armor)
            self.monster.armor = max(0, self.monster.armor - dmg)
            self.monster.hp -= actual

            if "Spiked Armor" in self.monster.abilities and actual >= 3:
                self.hero.apply_damage(1)

            if "shot" in self.monster.abilities and card_type == "ranged" and self.monster.hp > 0:
                self.hero.apply_damage(1)

            if "Ephemeral Wings" in self.monster.abilities and actual > 0:
                skip_next = True

            self.hero.discard.append(card)

        if "Banshee Wail" in self.monster.abilities:
            self.hero.apply_damage(dice_count // 3)

        dmg, arm = self.monster.roll_action()
        if "Enrage" in self.monster.abilities and self.monster.hp <= 3:
            extra_dmg, extra_arm = self.monster.roll_action()
            dmg += extra_dmg
            arm += extra_arm
        self.monster.armor += arm
        if self.monster.hp > 0:
            if "pierce" in self.monster.abilities:
                saved = self.hero.armor
                self.hero.armor = 0
                self.hero.apply_damage(dmg)
                self.hero.armor = saved
            else:
                self.hero.apply_damage(dmg)
            if "poison" in self.monster.abilities:
                self.hero.apply_damage(1)

        leftover = self.hero.armor
        self.hero.reset_armor()
        self.monster.armor = 0
        if "Cursed Thorns" in self.monster.abilities and leftover > 0:
            self.hero.apply_damage(leftover)
        return self.hero.hp > 0 and self.monster.hp > 0

    def run(self) -> None:
        while self.hero.hp > 0 and self.monster.hp > 0:
            alive = self.exchange()
            if not alive:
                break


MERLIN_UPGRADES = [
    # Common upgrades
    Card("Runic Ray", "ranged", "1d6", {"damage": 1}, "common", True),
    Card("Crystal-Shot Volley", "ranged", "1d6", {"damage": 1, "reroll": 1}, "common", True),
    Card("Glyph-Marking Bolt", "ranged", "1d6", {"damage": 1, "armor": 1}, "common", True),
    Card("Voice of Destiny", "ranged", "1d6", {"fate": 1}, "common", True),
    Card("Druidic Ways", "ranged", "1d6", {"armor": 2}, "common", True),
    Card("Protective Mists", "ranged", "1d6", {"armor": 1}, "common", True),
    Card("Mark of Fated Fall", "melee", "1d6", {"damage": 1, "fate": 1}, "common", True),
    Card("Veil-Rain of Chaos", "ranged", "1d6", {"damage": 2}, "common", True),
    Card("Oracle of Avalon", "ranged", "1d6", {"reroll": 1, "fate": 1}, "common", True),

    # Uncommon upgrades
    Card("Waves of Destiny", "ranged", "1d6", {"damage": 2, "reroll": 1}, "uncommon", True),
    Card("Ancestral Echoes", "ranged", "1d6", {"damage": 1, "armor": 1, "fate": 1}, "uncommon", True),
    Card("Whispers of the Wyrd", "ranged", "1d6", {"reroll": 2}, "uncommon", True),
    Card("Nature’s Rebuke", "ranged", "1d6", {"damage": 1, "armor": 2}, "uncommon", True),
    Card("Guard from Beyond", "ranged", "1d6", {"armor": 3}, "uncommon", True),
    Card("Sage's Alacrity", "ranged", "1d6", {"damage": 1, "reroll": 2}, "uncommon", True),
    Card("Charged Spirits", "ranged", "1d6", {"damage": 2, "fate": 1}, "uncommon", True),
    Card("Avalon's Light", "ranged", "1d6", {"armor": 2, "fate": 1}, "uncommon", True),
    Card("Spiritual Gifts", "ranged", "1d6", {"reroll": 1, "fate": 2}, "uncommon", True),

    # Rare upgrades
    Card("Rune Shatter", "ranged", "1d6", {"damage": 3}, "rare", True),
    Card("Sigil of Final Fate", "ranged", "1d6", {"damage": 2, "fate": 2}, "rare", True),
    Card("Conflux Lance", "ranged", "1d6", {"damage": 2, "reroll": 2}, "rare", True),
    Card("Echoes of Guidance", "ranged", "1d6", {"reroll": 3}, "rare", True),
    Card("Mercury Guard", "ranged", "1d6", {"armor": 3, "fate": 1}, "rare", True),
    Card("Old-Ways Shillelagh", "melee", "1d6", {"damage": 2, "armor": 1}, "rare", True),
    Card("Favor of the Druids", "ranged", "1d6", {"damage": 1, "armor": 2, "fate": 1}, "rare", True),
    Card("Chains of Morrígan", "ranged", "1d6", {"damage": 2, "armor": 2}, "rare", True),
    Card("Spirits of the Lands", "ranged", "1d6", {"damage": 1, "reroll": 1, "fate": 2}, "rare", True),
]

HERCULES_UPGRADES = [
    # Common upgrades
    Card("Bondless Effort", "melee", "1d6", {"damage": 1, "armor": 1}, "common", True),
    Card("Colossus Smash", "melee", "1d6", {"damage": 2}, "common", True),
    Card("Olympian Call", "melee", "1d6", {"damage": 1, "fate": 1}, "common", True),
    Card("Divine Resilience", "melee", "1d6", {"armor": 2}, "common", True),
    Card("Horde Breaker", "melee", "1d6", {"damage": 1, "reroll": 1}, "common", True),
    Card("Disorienting Blow", "melee", "1d6", {"damage": 1, "armor": 1}, "common", True),
    Card("Piercing Spear", "ranged", "1d6", {"damage": 2}, "common", True),
    Card("Fated War", "melee", "1d6", {"damage": 1, "fate": 1}, "common", True),
    Card("Fortune's Throw", "ranged", "1d6", {"damage": 1, "reroll": 1}, "common", True),

    # Uncommon upgrades
    Card("Pain Strike", "melee", "1d6", {"damage": 2}, "uncommon", True),
    Card("Fortifying Attack", "melee", "1d6", {"damage": 1, "armor": 2}, "uncommon", True),
    Card("Bone-Splinter Whirl", "melee", "1d6", {"damage": 2, "reroll": 1}, "uncommon", True),
    Card("Glorious Uproar", "melee", "1d6", {"damage": 1, "fate": 1, "reroll": 1}, "uncommon", True),
    Card("Guided By The Gods", "melee", "1d6", {"reroll": 2, "fate": 1}, "uncommon", True),
    Card("Chiron's Training", "melee", "1d6", {"damage": 1, "armor": 1, "reroll": 1}, "uncommon", True),
    Card("Once Isn't Enough", "melee", "1d6", {"damage": 2, "fate": 1}, "uncommon", True),
    Card("Strength from Anger", "melee", "1d6", {"damage": 1, "armor": 1, "fate": 1}, "uncommon", True),
    Card("Enduring Wave", "melee", "1d6", {"armor": 3}, "uncommon", True),

    # Rare upgrades
    Card("Zeus' Wrath", "melee", "1d6", {"damage": 3}, "rare", True),
    Card("Ares' Will", "melee", "1d6", {"damage": 2, "armor": 1}, "rare", True),
    Card("True Might of Hercules", "melee", "1d6", {"damage": 2, "armor": 1, "reroll": 1}, "rare", True),
    Card("Athena's Guidance", "melee", "1d6", {"reroll": 3}, "rare", True),
    Card("Apollo's Sunburst", "ranged", "1d6", {"damage": 2, "fate": 2}, "rare", True),
    Card("Nike's Desire", "melee", "1d6", {"damage": 1, "reroll": 2, "fate": 1}, "rare", True),
    Card("Blessing of Hephaestus", "ranged", "1d6", {"damage": 2, "armor": 2}, "rare", True),
    Card("Hermes’ Delivery", "melee", "1d6", {"damage": 2, "reroll": 1}, "rare", True),
    Card("Eris' Pandemonium", "melee", "1d6", {"damage": 2, "fate": 1, "reroll": 1}, "rare", True),
]


def merlin_base_deck() -> List[Card]:
    """Return Merlin's starting deck of ten cards."""
    return [
        Card("Arcane Volley", "ranged", "1d6", {"damage": 1}),
        Card("Arcane Volley", "ranged", "1d6", {"damage": 1}),
        Card("Lady’s Warden", "melee", "1d6", {"damage": 1, "armor": 2}),
        Card("Lady’s Warden", "melee", "1d6", {"damage": 1, "armor": 2}),
        Card("Weaver of Fate", "ranged", "1d6", {"damage": 1, "reroll": 2}),
        Card("Weaver of Fate", "ranged", "1d6", {"damage": 1, "reroll": 2}),
        Card("Crystal Cave's Staff", "melee", "1d6", {"damage": 1, "armor": 1}),
        Card("Mists of Time", "ranged", "1d6", {"damage": 1}),
        Card("Mists of Time", "ranged", "1d6", {"damage": 1}),
        Card("Circle of Avalon", "ranged", "1d6", {"damage": 1, "reroll": 1}),
    ]


def hercules_base_deck() -> List[Card]:
    """Return Hercules' starting deck of ten cards."""
    return [
        # Crushing attack drawing on Hercules' immense strength
        Card("Pillar-Breaker Blow", "melee", "1d6", {"damage": 2}),
        Card("Pillar-Breaker Blow", "melee", "1d6", {"damage": 2}),

        # Grappling technique used on the Nemean Lion
        Card("Lion Strangler", "melee", "1d6", {"damage": 1}),
        Card("Lion Strangler", "melee", "1d6", {"damage": 1}),

        # Brief surge of heroic resilience
        Card("Demigodly Heroism", "melee", "1d6", {"damage": 1, "armor": 1}),
        Card("Demigodly Heroism", "melee", "1d6", {"damage": 1, "armor": 1}),

        # Ranged spear toss
        Card("Herculean Throw", "ranged", "1d6", {"damage": 1}),
        Card("Herculean Throw", "ranged", "1d6", {"damage": 1}),

        # Defensive stance channeling godly endurance
        Card("Olympian Guard", "melee", "1d6", {"armor": 2}),
    ]


RARITY_WEIGHT = {"common": 3, "uncommon": 2, "rare": 1}


def draw_upgrade(hero: Hero) -> Card:
    """Draw three upgrade cards and keep the highest rarity."""
    pool = MERLIN_UPGRADES if hero.name.lower() == "merlin" else HERCULES_UPGRADES
    weights = [RARITY_WEIGHT[c.rarity] for c in pool]
    cards = random.choices(pool, weights, k=3)
    order = {"common": 0, "uncommon": 1, "rare": 2}
    top = max(cards, key=lambda c: order[c.rarity]).rarity
    finalists = [c for c in cards if c.rarity == top]
    chosen = random.choice(finalists)
    return Card(chosen.name, chosen.type, chosen.dice, chosen.effects.copy(), chosen.rarity, True)


def run_encounter(hero: Hero, encounters: List[Monster]) -> None:
    """Run a sequence of combats applying upgrade logic."""
    hero.deck = hero.deck[:10]
    hero.hand.clear()
    hero.discard.clear()
    hero.draw(4)

    for idx, monster in enumerate(encounters):
        hero.fate += 1
        combat = Combat(hero, monster)
        combat.run()
        if hero.hp <= 0:
            break
        if idx < len(encounters) - 1:
            upgrade = draw_upgrade(hero)
            hero.deck.append(upgrade)
            hero.hand.append(upgrade)
            hero.draw(3)


def run_trials(hero_name: str, n: int) -> None:
    """Run ``n`` full encounters consisting of six combats each.

    Statistics collected:
    - Final hero HP after each run and the overall average.
    - Hero HP after every combat round and the overall average HP.
    - Average total damage dealt and armor gained by the hero.
    - Average damage taken from and armor gained by each enemy type.
    - Percentage of runs where the hero defeated the final foe while alive.
    """

    base_deck_fn = merlin_base_deck if hero_name.lower() == "merlin" else hercules_base_deck

    def encounter_list() -> List[Monster]:
        """Pick three basic and three elite enemy groups for this run."""

        basic = random.sample(BASIC_GROUPS, 3)
        elite = random.sample(ELITE_GROUPS, 3)
        groups = basic + elite

        encounters: List[Monster] = []
        for g in groups:
            # single representative monster per group
            encounters.append(Monster(
                g.monster.name,
                g.monster.hp,
                g.monster.defense,
                g.monster.type,
                g.monster.abilities.copy(),
                g.monster.action_table[:],
            ))
        return encounters

    def run_combat(h: Hero, m: Monster) -> Dict[str, int]:
        """Simulate a combat without printing and return statistics."""
        stats = {"hero_damage": 0, "hero_armor": 0, "enemy_damage": 0, "enemy_armor": 0}
        round_num = 0
        hero_hp: List[int] = []
        while h.hp > 0 and m.hp > 0:
            draw_seq = [3, 2, 1, 0]
            draw_amt = draw_seq[round_num] if round_num < len(draw_seq) else 0
            if "Sticky Web" in m.abilities:
                draw_amt = max(0, draw_amt - 1)
            if round_num < len(draw_seq):
                h.draw(draw_amt)
            if "Corrupted Destiny" in m.abilities:
                h.fate = max(0, h.fate - 2)
            if "Ghostly" in m.abilities and round_num >= 3:
                break
            round_num += 1

            is_web = "Web Slinger" in m.abilities

            ranged = [c for c in h.hand if c.type == "ranged"]
            melee = [c for c in h.hand if c.type == "melee"]
            order = melee + ranged if is_web else ranged + melee
            h.hand = order

            cancel_next = "cancel" in m.abilities

            dice_count = 0
            skip_next = False

            while order:
                card = order.pop(0)
                if cancel_next:
                    cancel_next = False
                    h.discard.append(card)
                    continue

                if "disrupt" in m.abilities and order:
                    idx = random.randrange(len(order))
                    h.discard.append(order.pop(idx))

                dmg = 0
                count, sides = parse_dice(card.dice)
                dice_count += count
                rerolls = 0
                hits = 0
                target_def = m.defense
                card_type = card.type
                if is_web and card.type == "ranged":
                    card_type = "melee"
                if "Aerial Combat" in m.abilities and card_type == "melee":
                    target_def += 1
                card_rerolls = card.effects.get("reroll", 0)
                for _ in range(count):
                    result = random.randint(1, sides)
                    while "Denied Heaven" in m.abilities and result == 8:
                        result = random.randint(1, sides)
                    while (result < target_def and card_rerolls > 0 and
                           "Disturbed Flow" not in m.abilities):
                        card_rerolls -= 1
                        result = random.randint(1, sides)
                        while "Denied Heaven" in m.abilities and result == 8:
                            result = random.randint(1, sides)
                    while (result < target_def and h.fate > 0 and rerolls < 2 and
                           m.hp <= 2 and "Disturbed Flow" not in m.abilities):
                        h.fate -= 1
                        rerolls += 1
                        result = random.randint(1, sides)
                        while "Denied Heaven" in m.abilities and result == 8:
                            result = random.randint(1, sides)
                    if result in (1, 2) and "Curse of Torment" in m.abilities:
                        prev = h.hp
                        h.apply_damage(1)
                        stats["enemy_damage"] += prev - h.hp
                    if result >= target_def:
                        hit = 2 if random.random() < 0.2 else 1
                        dmg += hit
                        hits += 1
                if hits == 0 and "Roots of Despair" in m.abilities:
                    prev = h.hp
                    h.apply_damage(1)
                    stats["enemy_damage"] += prev - h.hp

                if "Silence" not in m.abilities:
                    dmg += card.effects.get("damage", 0)
                    arm = card.effects.get("armor", 0)
                    per_hit = card.effects.get("armor_per_hit", 0)
                else:
                    arm = 0
                    per_hit = 0
                gained = arm + per_hit * hits
                h.add_armor(gained)
                h.fate += card.effects.get("fate", 0)
                stats["hero_armor"] += gained

                if skip_next:
                    dmg = 0
                    skip_next = False

                actual = max(0, dmg - m.armor)
                m.armor = max(0, m.armor - dmg)
                m.hp -= actual
                stats["hero_damage"] += actual

                if "Spiked Armor" in m.abilities and actual >= 3:
                    prev = h.hp
                    h.apply_damage(1)
                    stats["enemy_damage"] += prev - h.hp

                if "shot" in m.abilities and card_type == "ranged" and m.hp > 0:
                    prev_hp = h.hp
                    h.apply_damage(1)
                    stats["enemy_damage"] += prev_hp - h.hp

                if "Ephemeral Wings" in m.abilities and actual > 0:
                    skip_next = True

                h.discard.append(card)

            if "Banshee Wail" in m.abilities:
                prev_hp = h.hp
                h.apply_damage(dice_count // 3)
                stats["enemy_damage"] += prev_hp - h.hp

            dmg, arm = m.roll_action()
            if "Enrage" in m.abilities and m.hp <= 3:
                extra_dmg, extra_arm = m.roll_action()
                dmg += extra_dmg
                arm += extra_arm
            m.armor += arm
            stats["enemy_armor"] += arm
            if m.hp > 0:
                prev_hp = h.hp
                if "pierce" in m.abilities:
                    saved = h.armor
                    h.armor = 0
                    h.apply_damage(dmg)
                    h.armor = saved
                else:
                    h.apply_damage(dmg)
                if "poison" in m.abilities:
                    h.apply_damage(1)
                stats["enemy_damage"] += prev_hp - h.hp

            leftover = h.armor
            h.reset_armor()
            m.armor = 0
            if "Cursed Thorns" in m.abilities and leftover > 0:
                prev_hp = h.hp
                h.apply_damage(leftover)
                stats["enemy_damage"] += prev_hp - h.hp
            hero_hp.append(h.hp)
        stats["hero_hp"] = hero_hp
        return stats

    final_hps: List[int] = []
    round_hps: List[int] = []
    hero_damage_total = 0
    hero_armor_total = 0
    enemy_totals: Dict[str, Dict[str, float]] = {}
    success = 0

    for _ in range(n):
        hero = Hero(name=hero_name, hp=20,
                    deck=[Card(c.name, c.type, c.dice, c.effects.copy(), c.rarity, c.upgrade)
                          for c in base_deck_fn()])
        encounters = [Monster(m.name, m.hp, m.defense, m.type,
                              m.abilities.copy(), m.action_table[:])
                      for m in encounter_list()]

        hero.deck = hero.deck[:10]
        hero.hand.clear()
        hero.discard.clear()
        hero.draw(4)

        last_alive = False
        for idx, monster in enumerate(encounters):
            hero.fate += 1
            stats = run_combat(hero, monster)
            hero_damage_total += stats["hero_damage"]
            hero_armor_total += stats["hero_armor"]
            round_hps.extend(stats["hero_hp"])

            et = monster.type
            if et not in enemy_totals:
                enemy_totals[et] = {"damage": 0, "armor": 0, "count": 0}
            enemy_totals[et]["damage"] += stats["enemy_damage"]
            enemy_totals[et]["armor"] += stats["enemy_armor"]
            enemy_totals[et]["count"] += 1

            if hero.hp <= 0:
                last_alive = False
                break
            last_alive = monster.hp <= 0
            if idx < len(encounters) - 1:
                upgrade = draw_upgrade(hero)
                hero.deck.append(upgrade)
                hero.hand.append(upgrade)
                hero.draw(3)

        final_hps.append(hero.hp)
        if last_alive and hero.hp > 0:
            success += 1

    avg_hp = sum(final_hps) / n if n else 0
    avg_round_hp = sum(round_hps) / len(round_hps) if round_hps else 0
    print(f"Average final HP: {avg_hp:.2f}")
    print(f"Average HP per round: {avg_round_hp:.2f}\n")

    print("Average hero totals per run:")
    print(f"  Damage dealt: {hero_damage_total / n:.2f}")
    print(f"  Armor gained: {hero_armor_total / n:.2f}\n")

    print("Enemy type averages:")
    for etype, vals in enemy_totals.items():
        count = vals["count"] or 1
        dmg = vals["damage"] / count
        arm = vals["armor"] / count
        print(f"  {etype}: dealt {dmg:.2f} dmg, gained {arm:.2f} armor")

    rate = (success / n) * 100 if n else 0
    print(f"\nSuccess rate: {rate:.2f}%\n")


def main() -> None:
    """Run aggregated simulations for Merlin and Hercules."""
    print("=== Merlin Trials ===")
    run_trials("Merlin", 20000)
    print("=== Hercules Trials ===")
    run_trials("Hercules", 20000)


if __name__ == "__main__":
    main()
