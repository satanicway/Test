import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


def roll_dice(dice: str) -> int:
    """Parse a dice string like '2d8' and roll it."""
    try:
        count, sides = map(int, dice.lower().split("d"))
    except Exception:
        return 0
    return sum(random.randint(1, sides) for _ in range(count))


def parse_dice(dice: str) -> (int, int):
    """Return (count, sides) for a dice string like '2d8'."""
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
    max_hp: int = 0
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    armor: int = 0
    fate: int = 0
    combat_effects: Dict[str, int] = field(default_factory=dict)
    exchange_effects: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.max_hp == 0:
            self.max_hp = self.hp

    def draw(self, count: int = 1) -> int:
        drawn = 0
        for _ in range(count):
            if not self.deck and self.discard:
                random.shuffle(self.discard)
                self.deck.extend(self.discard)
                self.discard.clear()
            if self.deck:
                self.hand.append(self.deck.pop(0))
                drawn += 1
            if len(self.hand) > 7:
                idx = next((i for i, c in enumerate(self.hand) if not c.upgrade), 0)
                self.discard.append(self.hand.pop(idx))
        return drawn

    def commit_card(self, index: int) -> Card:
        card = self.hand.pop(index)
        self.discard.append(card)
        return card

    def discard_weakest_cards(self, count: int = 2) -> List[Card]:
        """Discard the weakest cards currently in hand and return them."""
        def strength(c: Card) -> int:
            cnt, sides = parse_dice(c.dice)
            return cnt * sides

        removed: List[Card] = []
        for card in sorted(self.hand, key=strength)[:count]:
            self.hand.remove(card)
            self.discard.append(card)
            removed.append(card)
        return removed

    def discard_card(self, index: int) -> Optional[Card]:
        """Discard a card from hand by index if possible."""
        if 0 <= index < len(self.hand):
            return self.commit_card(index)
        return None

    def add_armor(self, amount: int) -> None:
        self.armor += amount

    def reset_armor(self) -> None:
        self.armor = 0

    def apply_damage(self, dmg: int, pierce: bool = False) -> None:
        """Apply ``dmg`` to the hero, optionally ignoring armor."""
        if not pierce:
            block = min(self.armor, dmg)
            self.armor -= block
            dmg -= block
        if dmg > 0:
            self.hp -= dmg


@dataclass(eq=False)
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
    dice_bonus_against: int = 0

    def roll_action(self) -> (int, int, bool, bool, bool, bool):
        """Return (damage, armor, p, dr, s, c) for the exchange using a d8 table."""
        roll = random.randint(1, 8)
        idx = (roll - 1) // 2
        entry = self.action_table[min(idx, len(self.action_table) - 1)]
        damage = entry.get("damage", 0)
        armor = entry.get("armor", 0)
        p = entry.get("p", False)
        dr = entry.get("dr", False)
        s = entry.get("s", False)
        c = entry.get("c", False)
        return damage, armor, p, dr, s, c


# Action tables for each monster. These should reflect the values in
# ``REFERENCE.md``.  The reference format is ambiguous so the numbers
# below still mirror the old generic tables and should be updated when
# clearer data becomes available.

BASIC_SHADOW_SPINNER_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 2},
    {"damage": 1, "armor": 2},
    {"damage": 2, "armor": 0, "p": True},
]

BASIC_VOID_SOLDIER_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 1},
    {"damage": 1, "armor": 0},
    {"damage": 2, "armor": 1},
]

BASIC_PRIEST_OF_OBLIVION_TABLE = [
    {"damage": 0, "armor": 0, "dr": True},
    {"damage": 0, "armor": 0},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 0},
]

BASIC_CORRUPTED_DRYAD_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 1},
    {"damage": 1, "armor": 0, "s": True},
    {"damage": 2, "armor": 0},
]

BASIC_DARK_MINOTAUR_TABLE = [
    {"damage": 0, "armor": 1},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 0, "p": True},
    {"damage": 2, "armor": 0},
]

BASIC_DARK_WIZARD_TABLE = [
    {"damage": 0, "armor": 0, "c": True},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 1},
    {"damage": 2, "armor": 0},
]

BASIC_SHADOW_BANSHEE_TABLE = [
    {"damage": 0, "armor": 3},
    {"damage": 0, "armor": 0, "dr": True},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 0},
]

BASIC_VOID_GRYphon_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 1, "armor": 1},
    {"damage": 2, "armor": 2},
    {"damage": 3, "armor": 0, "p": True},
]

BASIC_VOID_TREANT_TABLE = [
    {"damage": 0, "armor": 3},
    {"damage": 1, "armor": 1},
    {"damage": 1, "armor": 1},
    {"damage": 4, "armor": 0},
]

BASIC_CORRUPTED_ANGEL_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 1, "armor": 0, "p": True},
    {"damage": 2, "armor": 0, "s": True},
    {"damage": 3, "armor": 2},
]

ELITE_SHADOW_SPINNER_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 2},
    {"damage": 2, "armor": 2},
    {"damage": 3, "armor": 0, "p": True},
]

ELITE_VOID_SOLDIER_TABLE = [
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 1},
    {"damage": 1, "armor": 0},
    {"damage": 3, "armor": 1},
]

ELITE_PRIEST_OF_OBLIVION_TABLE = [
    {"damage": 0, "armor": 0, "dr": True},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 1},
    {"damage": 2, "armor": 0},
]

ELITE_CORRUPTED_DRYAD_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 1},
    {"damage": 2, "armor": 0, "s": True},
    {"damage": 3, "armor": 0},
]

ELITE_DARK_MINOTAUR_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 2},
    {"damage": 2, "armor": 0, "p": True},
    {"damage": 3, "armor": 0},
]

ELITE_DARK_WIZARD_TABLE = [
    {"damage": 0, "armor": 0, "c": True},
    {"damage": 1, "armor": 0},
    {"damage": 1, "armor": 0, "p": True},
    {"damage": 3, "armor": 0},
]

ELITE_SHADOW_BANSHEE_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 0, "armor": 2},
    {"damage": 1, "armor": 0, "dr": True},
    {"damage": 2, "armor": 0, "p": True},
]

ELITE_VOID_GRYphon_TABLE = [
    {"damage": 0, "armor": 0},
    {"damage": 2, "armor": 3},
    {"damage": 3, "armor": 1},
    {"damage": 4, "armor": 0, "p": True},
]

ELITE_VOID_TREANT_TABLE = [
    {"damage": 0, "armor": 4},
    {"damage": 2, "armor": 2},
    {"damage": 2, "armor": 2},
    {"damage": 5, "armor": 0},
]

ELITE_CORRUPTED_ANGEL_TABLE = [
    {"damage": 0, "armor": 0, "c": True},
    {"damage": 2, "armor": 0, "p": True},
    {"damage": 3, "armor": 0, "s": True},
    {"damage": 5, "armor": 0},
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
                         action_table=BASIC_SHADOW_SPINNER_TABLE)),
    EnemyGroup(3, Monster("Void Soldier", hp=3, defense=5, type="precise",
                          abilities=["Dark Phalanx"],
                         action_table=BASIC_VOID_SOLDIER_TABLE)),
    EnemyGroup(3, Monster("Priest of Oblivion", hp=2, defense=3, type="arcane",
                          abilities=["Power of Death"],
                         action_table=BASIC_PRIEST_OF_OBLIVION_TABLE)),
    EnemyGroup(3, Monster("Corrupted Dryad", hp=3, defense=4, type="brutal",
                          abilities=["Cursed Thorns"],
                         action_table=BASIC_CORRUPTED_DRYAD_TABLE)),
    EnemyGroup(2, Monster("Dark Minotaur", hp=5, defense=3, type="precise",
                          abilities=[],
                         action_table=BASIC_DARK_MINOTAUR_TABLE)),
    EnemyGroup(2, Monster("Dark Wizard", hp=4, defense=3, type="brutal",
                          abilities=["Curse of Torment", "Void Barrier"],
                         action_table=BASIC_DARK_WIZARD_TABLE)),
    EnemyGroup(2, Monster("Shadow Banshee", hp=4, defense=5, type="divine",
                          abilities=["Ghostly"],
                         action_table=BASIC_SHADOW_BANSHEE_TABLE)),
    EnemyGroup(1, Monster("Void Gryphon", hp=5, defense=5, type="spiritual",
                          abilities=["Aerial Combat"],
                         action_table=BASIC_VOID_GRYphon_TABLE)),
    EnemyGroup(1, Monster("Void Treant", hp=7, defense=6, type="divine",
                          abilities=["Power Sap"],
                         action_table=BASIC_VOID_TREANT_TABLE)),
    EnemyGroup(1, Monster("Corrupted Angel", hp=6, defense=5, type="arcane",
                          abilities=["Corrupted Destiny"],
                         action_table=BASIC_CORRUPTED_ANGEL_TABLE)),
]

ELITE_GROUPS: List[EnemyGroup] = [
    EnemyGroup(3, Monster("Shadow Spinner", hp=3, defense=5, type="spiritual",
                          abilities=["Sticky Web"],
                          action_table=ELITE_SHADOW_SPINNER_TABLE)),
    EnemyGroup(3, Monster("Void Soldier", hp=4, defense=6, type="precise",
                          abilities=["Spiked Armor"],
                          action_table=ELITE_VOID_SOLDIER_TABLE)),
    EnemyGroup(3, Monster("Priest of Oblivion", hp=4, defense=4, type="arcane",
                          abilities=["Silence"],
                          action_table=ELITE_PRIEST_OF_OBLIVION_TABLE)),
    EnemyGroup(3, Monster("Corrupted Dryad", hp=4, defense=5, type="brutal",
                          abilities=["Disturbed Flow"],
                          action_table=ELITE_CORRUPTED_DRYAD_TABLE)),
    EnemyGroup(2, Monster("Dark Minotaur", hp=6, defense=3, type="precise",
                          abilities=["Enrage"],
                          action_table=ELITE_DARK_MINOTAUR_TABLE)),
    EnemyGroup(2, Monster("Dark Wizard", hp=3, defense=4, type="brutal",
                          abilities=["Void Barrier"],
                          action_table=ELITE_DARK_WIZARD_TABLE)),
    EnemyGroup(2, Monster("Shadow Banshee", hp=5, defense=5, type="divine",
                          abilities=["Banshee Wail"],
                          action_table=ELITE_SHADOW_BANSHEE_TABLE)),
    EnemyGroup(1, Monster("Void Gryphon", hp=6, defense=5, type="spiritual",
                          abilities=["Ephemeral Wings"],
                          action_table=ELITE_VOID_GRYphon_TABLE)),
    EnemyGroup(1, Monster("Void Treant", hp=8, defense=7, type="divine",
                          abilities=["Roots of Despair"],
                          action_table=ELITE_VOID_TREANT_TABLE)),
    EnemyGroup(1, Monster("Corrupted Angel", hp=7, defense=6, type="arcane",
                          abilities=["Denied Heaven"],
                          action_table=ELITE_CORRUPTED_ANGEL_TABLE)),
]




MERLIN_UPGRADES = [
    # Common upgrades
    Card("Runic Ray", "ranged", "2d8", {"aoe": True, "discard_damage_per_card": 2}, "common", True),
    Card("Crystal-Shot Volley", "ranged", "3d8", {"extra_dice_on_8": 1}, "common", True),
    Card("Glyph-Marking Bolt", "ranged", "1d8", {"combat_target_dice_plus": 1}, "common", True),
    Card("Voice of Destiny", "ranged", "3d8", {"exchange_reroll": 2}, "common", True),
    Card("Druidic Ways", "ranged", "2d8", {"heal": 1}, "common", True),
    Card("Protective Mists", "ranged", "0d8", {"armor": 1, "per_enemy_armor": 1}, "common", True),
    Card("Mark of Fated Fall", "melee", "1d8", {"combat_target_def_minus": 2}, "common", True),
    Card("Veil-Rain of Chaos", "ranged", "1d8", {"aoe": True, "extra_dice_per_enemy": 1}, "common", True),
    Card("Oracle of Avalon", "ranged", "0d8", {"gain_fate": 3}, "common", True),

    # Uncommon upgrades
    Card("Waves of Destiny", "ranged", "3d8", {"aoe": True, "fate_on_kill": 1}, "uncommon", True),
    Card("Ancestral Echoes", "ranged", "3d8", {"aoe": True, "exchange_reroll": 2}, "uncommon", True),
    Card("Whispers of the Wyrd", "ranged", "0d8", {"combat_damage_bonus": 2}, "uncommon", True),
    Card("Nature’s Rebuke", "ranged", "2d8", {"aoe": True, "heal_on_kill": 1}, "uncommon", True),
    Card("Guard from Beyond", "ranged", "0d8", {"armor": 5}, "uncommon", True),
    Card("Sage's Alacrity", "ranged", "2d8", {"combat_reroll": 2}, "uncommon", True),
    Card("Charged Spirits", "ranged", "2d8", {"aoe": True, "fate_bonus_damage": 1}, "uncommon", True),
    Card("Avalon's Light", "ranged", "3d8", {"combat_crit_damage": 4}, "uncommon", True),
    Card("Spiritual Gifts", "ranged", "4d8", {"discard_gain_fate": 2, "discard_draw": 1}, "uncommon", True),

    # Rare upgrades
    Card("Rune Shatter", "ranged", "3d8", {"aoe": True, "exchange_target_def_minus": 1}, "rare", True),
    Card("Sigil of Final Fate", "ranged", "0d8", {"combat_ones_to_eights": 1}, "rare", True),
    Card("Conflux Lance", "ranged", "5d8", {}, "rare", True),
    Card("Echoes of Guidance", "ranged", "0d8", {"execute_twice_next": 1}, "rare", True),
    Card("Mercury Guard", "ranged", "0d8", {"combat_mercury_guard": 1}, "rare", True),
    Card("Old-Ways Shillelagh", "melee", "3d8", {"armor_per_hit": 1}, "rare", True),
    Card("Favor of the Druids", "ranged", "1d8", {"draw": 1}, "rare", True),
    Card("Chains of Morrígan", "ranged", "0d8", {"exchange_dice_plus_targets": 1}, "rare", True),
    Card("Spirits of the Lands", "ranged", "4d8", {"gain_fate_per_card": 1}, "rare", True),
]

HERCULES_UPGRADES = [
    # Common upgrades
    Card("Bondless Effort", "melee", "3d8", {"discard_damage_per_card": 3}, "common", True),
    Card("Colossus Smash", "melee", "3d8", {"armor": 1}, "common", True),
    Card("Olympian Call", "melee", "1d8", {"combat_reroll": 1}, "common", True),
    Card("Divine Resilience", "melee", "1d8", {"armor": 1, "per_enemy_armor": 1}, "common", True),
    Card("Horde Breaker", "melee", "2d8", {"combat_enemy_hp_loss_on_death": 2}, "common", True),
    Card("Disorienting Blow", "melee", "2d8", {"exchange_target_def_minus_next": 3}, "common", True),
    Card("Piercing Spear", "ranged", "2d8", {"combat_target_def_minus": 1}, "common", True),
    Card("Fated War", "melee", "2d8", {"aoe": True, "gain_fate_per_enemy": 1}, "common", True),
    Card("Fortune's Throw", "ranged", "2d8", {"gain_fate": 2, "armor": 2}, "common", True),

    # Uncommon upgrades
    Card("Pain Strike", "melee", "4d8", {"hp_for_damage": 6}, "uncommon", True),
    Card("Fortifying Attack", "melee", "0d8", {"armor": 2}, "uncommon", True),
    Card("Bone-Splinter Whirl", "melee", "3d8", {"aoe": True, "combat_enemy_def_minus": 1}, "uncommon", True),
    Card("Glorious Uproar", "melee", "1d8", {"aoe": True, "bonus_damage_per_enemy": 1}, "uncommon", True),
    Card("Guided By The Gods", "melee", "2d8", {"combat_reroll": 1}, "uncommon", True),
    Card("Chiron's Training", "melee", "1d8", {"combat_armor_per_attack": 1}, "uncommon", True),
    Card("Once Isn't Enough", "melee", "0d8", {"execute_twice_next": 1}, "uncommon", True),
    Card("Strength from Anger", "melee", "1d8", {"combat_damage_bonus": 1}, "uncommon", True),
    Card("Enduring Wave", "melee", "2d8", {"aoe": True, "armor": 2}, "uncommon", True),

    # Rare upgrades
    Card("Zeus' Wrath", "melee", "4d8", {"aoe": True}, "rare", True),
    Card("Ares' Will", "melee", "1d8", {"combat_enemy_hp_loss": 2}, "rare", True),
    Card("True Might of Hercules", "melee", "8d8", {}, "rare", True),
    Card("Athena's Guidance", "melee", "0d8", {"combat_double_damage": 1}, "rare", True),
    Card("Apollo's Sunburst", "ranged", "3d8", {"aoe": True, "discard_damage_per_card": 3}, "rare", True),
    Card("Nike's Desire", "melee", "1d8", {"draw": 1, "bonus_draw_if_fate": 1}, "rare", True),
    Card("Blessing of Hephaestus", "ranged", "0d8", {"armor": 5}, "rare", True),
    Card("Hermes’ Delivery", "melee", "3d8", {"play_drawn_attack_immediately": 1}, "rare", True),
    Card("Eris' Pandemonium", "melee", "0d8", {"exchange_bonus_damage_per_enemy": 1}, "rare", True),
]

def merlin_base_deck() -> List[Card]:
    """Return Merlin's starting deck of ten cards."""
    return [
        Card("Arcane Volley", "ranged", "1d8", {"aoe": True}),
        Card("Arcane Volley", "ranged", "1d8", {"aoe": True}),
        Card("Lady’s Warden", "melee", "1d8", {"armor": 2}),
        Card("Lady’s Warden", "melee", "1d8", {"armor": 2}),
        Card("Weaver of Fate", "ranged", "1d8", {"exchange_reroll": 2}),
        Card("Weaver of Fate", "ranged", "1d8", {"exchange_reroll": 2}),
        Card("Crystal Cave's Staff", "melee", "1d8", {"combat_armor_per_high": 1}),
        Card("Mists of Time", "ranged", "1d8", {"exchange_dice_plus": 1}),
        Card("Mists of Time", "ranged", "1d8", {"exchange_dice_plus": 1}),
        Card("Circle of Avalon", "ranged", "1d8", {"combat_reroll": 1}),
    ]


def hercules_base_deck() -> List[Card]:
    """Return Hercules' starting deck of ten cards."""
    return [
        # Crushing attack drawing on Hercules' immense strength
        Card("Pillar-Breaker Blow", "melee", "2d8", {}),
        Card("Pillar-Breaker Blow", "melee", "2d8", {}),

        # Grappling technique used on the Nemean Lion
        Card("Lion Strangler", "melee", "1d8", {"combat_enemy_hp_loss": 1}),

        # Brief surge of heroic resilience
        Card("Demigodly Heroism", "melee", "1d8", {"armor": 1}),
        Card("Demigodly Heroism", "melee", "1d8", {"armor": 1}),

        # Divine spear
        Card("Sky Javelin", "ranged", "2d8", {"exchange_damage_bonus": 1}),

        # Sweeping attack
        Card("Club Spin", "melee", "1d8", {"aoe": True}),
        Card("Club Spin", "melee", "1d8", {"aoe": True}),

        # Defensive stance channeling godly endurance
        Card("Atlas Guard", "ranged", "0d8", {"armor": 3}),
        Card("Atlas Guard", "ranged", "0d8", {"armor": 3}),
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

    def encounter_list() -> List[Tuple[List[Monster], str]]:
        """Pick three basic and three elite enemy groups for this run.

        Each group spawns ``EnemyGroup.count`` identical ``Monster`` instances
        that will be fought simultaneously in a single combat.  The returned
        list pairs each monster group with the string ``"basic"`` or ``"elite"``
        indicating its type."""

        basic = random.sample(BASIC_GROUPS, 3)
        elite = random.sample(ELITE_GROUPS, 3)
        groups: List[Tuple[EnemyGroup, str]] = [
            (g, "basic") for g in basic
        ] + [
            (g, "elite") for g in elite
        ]

        encounters: List[Tuple[List[Monster], str]] = []
        for g, kind in groups:
            monsters = [
                Monster(
                    g.monster.name,
                    g.monster.hp,
                    g.monster.defense,
                    g.monster.type,
                    g.monster.abilities.copy(),
                    g.monster.action_table[:],
                )
                for _ in range(g.count)
            ]
            encounters.append((monsters, kind))
        return encounters

    def run_combat(h: Hero, monsters: List[Monster], run_idx: int, combat_idx: int) -> Dict[str, int]:
        """Simulate a combat against multiple monsters and return statistics.

        ``run_idx`` and ``combat_idx`` are only used for progress output.
        """

        print(f"  Run {run_idx+1}: starting combat {combat_idx+1} against {monsters[0].name} x{len(monsters)}")

        stats = {"hero_damage": 0, "hero_armor": 0, "enemy_damage": 0, "enemy_armor": 0}
        round_num = 0
        hero_hp: List[int] = []
        no_draw_streak = 0
        h.combat_effects.clear()
        alive = [m for m in monsters if m.hp > 0]
        no_draw_turns = 0
        while alive:
            if no_draw_turns >= 2:
                prev_hp = h.hp
                h.apply_damage(h.max_hp // 2)
                stats["enemy_damage"] += prev_hp - h.hp
                for mm in alive:
                    mm.hp = 0
                hero_hp.append(h.hp)
                break
            h.exchange_effects = {"cards_played": 0}
            draw_seq = [3, 2, 1, 0]
            draw_amt = draw_seq[round_num] if round_num < len(draw_seq) else 0
            if any("Sticky Web" in m.abilities for m in alive):
                draw_amt = max(0, draw_amt - 1)
            for m in alive:
                if "Corrupted Destiny" in m.abilities:
                    h.fate = max(0, h.fate - 2)
            if any("Ghostly" in m.abilities for m in alive) and round_num >= 3:
                break
            if "combat_mercury_guard" in h.combat_effects:
                h.add_armor(len(alive) * h.combat_effects["combat_mercury_guard"])
            round_num += 1
            print(f"    Exchange {round_num}: hero HP {h.hp}, fate {h.fate}, monster HPs {[m.hp for m in alive]}")

            is_web = any("Web Slinger" in m.abilities for m in alive)

            ranged = [c for c in h.hand if c.type == "ranged"]
            melee = [c for c in h.hand if c.type == "melee"]
            order = melee + ranged if is_web else ranged + melee
            h.hand = order

            dice_count = 0
            skip_next = False
            enemy_actions = {}
            for m in alive:
                if "Void Barrier" in m.abilities:
                    m.allowed_type = None
                dmg, arm, p, dr, s, c = m.roll_action()
                if "Enrage" in m.abilities and m.hp <= 3:
                    extra_dmg, extra_arm, *_ = m.roll_action()
                    dmg += extra_dmg
                    arm += extra_arm
                if "Power of Death" in m.abilities:
                    dead = sum(1 for p in monsters if "Power of Death" in p.abilities and p.hp <= 0)
                    dmg += dead
                enemy_actions[m] = (dmg, arm, p, dr, s, c)

            # Determine which enemy rolled the highest damage for this exchange
            max_dmg = 0
            preferred_target = None
            if enemy_actions:
                max_dmg = max(v[0] for v in enemy_actions.values())
                top = [m for m, vals in enemy_actions.items() if vals[0] == max_dmg and m.hp > 0]
                if top:
                    preferred_target = random.choice(top)

            while order:
                card = order.pop(0)
                if card.effects.get("execute_twice_next"):
                    h.exchange_effects["execute_twice_next"] = True
                    h.discard.append(card)
                    continue
                repeat = 2 if h.exchange_effects.pop("execute_twice_next", False) else 1

                # Apply persistent effects from the card
                if card.effects.get("exchange_dice_plus"):
                    h.exchange_effects["exchange_dice_plus"] = (
                        h.exchange_effects.get("exchange_dice_plus", 0)
                        + card.effects["exchange_dice_plus"]
                    )
                if card.effects.get("exchange_reroll"):
                    h.exchange_effects["exchange_reroll"] = (
                        h.exchange_effects.get("exchange_reroll", 0)
                        + card.effects["exchange_reroll"]
                    )
                if card.effects.get("exchange_target_def_minus") is not None:
                    h.exchange_effects["exchange_target_def_minus"] = card.effects[
                        "exchange_target_def_minus"
                    ]
                if card.effects.get("exchange_dice_plus_targets"):
                    h.exchange_effects["dice_plus_targets"] = card.effects[
                        "exchange_dice_plus_targets"
                    ]

                if card.effects.get("combat_enemy_hp_loss_on_death"):
                    h.combat_effects["enemy_hp_loss_on_death"] = card.effects[
                        "combat_enemy_hp_loss_on_death"
                    ]
                for ck, cv in card.effects.items():
                    if ck.startswith("combat_") and ck not in (
                        "combat_target_def_minus",
                        "combat_target_dice_plus",
                        "combat_double_damage",
                        "combat_enemy_hp_loss_on_death",
                    ):
                        h.combat_effects[ck] = cv

                for _ in range(repeat):
                    dmg = 0
                    count, sides = parse_dice(card.dice)
                    count += card.effects.get("extra_dice_per_enemy", 0) * len(alive)
                    rerolls = 0
                    hits = 0
                    target = preferred_target if preferred_target is not None else next((mm for mm in alive if mm.hp > 0), None)
                    if target is None:
                        break
                    target_def = target.defense - h.combat_effects.get("combat_enemy_def_minus", 0) - h.exchange_effects.get("exchange_target_def_minus", 0)
                    target_def -= h.exchange_effects.pop("target_def_minus_next", 0)
                    card_type = card.type
                    if is_web and card.type == "ranged":
                        card_type = "melee"
                    if "Aerial Combat" in target.abilities and card_type == "melee":
                        target_def += 1
                    card_rerolls = card.effects.get("reroll", 0)
                    card_rerolls += h.combat_effects.get("combat_reroll", 0)
                    card_rerolls += h.exchange_effects.get("exchange_reroll", 0)
                    dice_plus = h.exchange_effects.get("exchange_dice_plus", 0)
                    dice_plus += h.exchange_effects.get("dice_plus_targets", 0) * (
                        len(alive) if card.effects.get("aoe") else 1
                    )
                    dice_plus += getattr(target, "dice_bonus_against", 0)
                    rolled = 0
                    while rolled < count:
                        dice_count += 1
                        result = random.randint(1, sides)
                        if h.combat_effects.get("combat_ones_to_eights") and result == 1:
                            result = 8
                        result = min(8, result + dice_plus)
                        while "Denied Heaven" in target.abilities and result == 8:
                            result = random.randint(1, sides)
                            result = min(8, result + dice_plus)
                        while (result < target_def and card_rerolls > 0 and "Disturbed Flow" not in target.abilities):
                            card_rerolls -= 1
                            result = random.randint(1, sides)
                            if h.combat_effects.get("combat_ones_to_eights") and result == 1:
                                result = 8
                            result = min(8, result + dice_plus)
                        while (result < target_def and h.fate > 0 and rerolls < 2 and
                               target.hp <= 2 and "Disturbed Flow" not in target.abilities):
                            h.fate -= 1
                            rerolls += 1
                            result = random.randint(1, sides)
                            if h.combat_effects.get("combat_ones_to_eights") and result == 1:
                                result = 8
                            result = min(8, result + dice_plus)
                            while "Denied Heaven" in target.abilities and result == 8:
                                result = random.randint(1, sides)
                                result = min(8, result + dice_plus)
                        if result in (1, 2) and "Curse of Torment" in target.abilities:
                            prev = h.hp
                            h.apply_damage(1)
                            stats["enemy_damage"] += prev - h.hp
                        if result >= target_def:
                            if result == 8:
                                hit = 2
                            else:
                                hit = 2 if random.random() < 0.2 else 1
                            if result == 8 and h.combat_effects.get("combat_crit_damage"):
                                hit = h.combat_effects["combat_crit_damage"]
                            dmg += hit
                            hits += 1
                            if card.effects.get("extra_dice_on_8") and result == 8:
                                count += 1
                            if result >= 7:
                                h.add_armor(h.combat_effects.get("armor_per_high", 0))
                        rolled += 1
                    if hits == 0 and any("Roots of Despair" in mm.abilities for mm in alive):
                        prev = h.hp
                        h.apply_damage(1)
                        stats["enemy_damage"] += prev - h.hp

                    if "Silence" not in target.abilities:
                        dmg += card.effects.get("damage", 0)
                        arm = card.effects.get("armor", 0)
                        per_hit = card.effects.get("armor_per_hit", 0)
                        arm += card.effects.get("per_enemy_armor", 0) * len(alive)
                        if card.effects.get("armor_per_high"):
                            arm += card.effects["armor_per_high"] * hits
                    else:
                        arm = 0
                        per_hit = 0
                    gained = arm + per_hit * hits
                    h.add_armor(gained)
                    if card.effects.get("heal"):
                        h.hp += card.effects["heal"]
                    if card.effects.get("gain_fate"):
                        h.fate += card.effects["gain_fate"]
                    if card.effects.get("discard_gain_fate"):
                        if h.hand:
                            h.discard_weakest_cards(1)
                            h.fate += card.effects["discard_gain_fate"]
                            if card.effects.get("discard_draw"):
                                h.draw(card.effects["discard_draw"])
                    stats["hero_armor"] += gained

                    dmg += h.combat_effects.get("combat_damage_bonus", 0) + h.exchange_effects.get("exchange_damage_bonus", 0)
                    dmg += card.effects.get("bonus_damage_per_enemy", 0) * len(alive)
                    dmg += h.exchange_effects.get("exchange_bonus_damage_per_enemy", 0) * len(alive)

                    if card.effects.get("hp_for_damage"):
                        spend = min(h.hp - 1, card.effects["hp_for_damage"])
                        if spend > 0:
                            h.hp -= spend
                            dmg += spend

                    if card.effects.get("fate_bonus_damage"):
                        spend = min(h.fate, 5)
                        h.fate -= spend
                        dmg += spend * card.effects["fate_bonus_damage"]

                    if card.effects.get("discard_damage_per_card"):
                        discarded = h.discard_weakest_cards()
                        dmg += len(discarded) * card.effects["discard_damage_per_card"]

                    if card.effects.get("combat_double_damage"):
                        h.discard_weakest_cards(1)
                        h.combat_effects["combat_double_damage"] = 1

                    if skip_next:
                        dmg = 0
                        skip_next = False

                    if card.effects.get("gain_fate_per_enemy"):
                        h.fate += len(alive) * card.effects["gain_fate_per_enemy"]
                    targets = alive if card.effects.get("aoe") else [target]
                    for mm in targets:
                        actual = max(0, dmg - mm.armor)
                        mm.armor = max(0, mm.armor - dmg)
                        local_def = mm.defense
                        if "Void Barrier" in mm.abilities:
                            if getattr(mm, "allowed_type", None) is None and actual > 0:
                                mm.allowed_type = card_type
                            elif (getattr(mm, "allowed_type", None) is not None and card_type != mm.allowed_type):
                                actual = 0
                        if "Dark Phalanx" in mm.abilities and card.effects.get("aoe") and actual > 0:
                            if sum(1 for x in alive if "Dark Phalanx" in x.abilities and x.hp > 0) > 1:
                                actual = max(1, actual - 1)
                        if h.combat_effects.get("combat_double_damage"):
                            actual *= 2
                        prev_hp_t = mm.hp
                        mm.hp -= actual
                        stats["hero_damage"] += actual
                        if h.combat_effects.get("combat_enemy_hp_loss"):
                            if mm.hp > 0:
                                mm.hp -= h.combat_effects["combat_enemy_hp_loss"]
                        if prev_hp_t > 0 and mm.hp <= 0:
                            if card.effects.get("fate_on_kill"):
                                h.fate += card.effects["fate_on_kill"]
                            if card.effects.get("heal_on_kill"):
                                h.hp += card.effects["heal_on_kill"]
                            if h.combat_effects.get("enemy_hp_loss_on_death"):
                                for oth in alive:
                                    if oth is not mm and oth.hp > 0:
                                        oth.hp -= h.combat_effects["enemy_hp_loss_on_death"]

                        if "Spiked Armor" in mm.abilities and actual >= 3:
                            prev = h.hp
                            h.apply_damage(1)
                            stats["enemy_damage"] += prev - h.hp
                        if "Ephemeral Wings" in mm.abilities and actual > 0:
                            skip_next = True

                        if card.effects.get("combat_target_def_minus"):
                            mm.defense = max(0, mm.defense - card.effects["combat_target_def_minus"])

                        if card.effects.get("combat_target_dice_plus"):
                            mm.dice_bonus_against += card.effects["combat_target_dice_plus"]

                    h.exchange_effects["cards_played"] += 1
                if card.effects.get("exchange_target_def_minus_next"):
                    h.exchange_effects["target_def_minus_next"] = card.effects["exchange_target_def_minus_next"]
                if card.effects.get("gain_fate_per_card"):
                    h.fate += card.effects["gain_fate_per_card"] * (h.exchange_effects["cards_played"] - 1)
                h.discard.append(card)
                if card.effects.get("draw"):
                    h.draw(card.effects["draw"])
                if card.effects.get("bonus_draw_if_fate") and h.fate >= 1:
                    h.fate -= 1
                    h.draw(card.effects["bonus_draw_if_fate"])
                if card.effects.get("play_drawn_attack_immediately"):
                    h.draw(1)
                    if h.hand:
                        order.insert(0, h.hand.pop())

            for mm in alive:
                if "Banshee Wail" in mm.abilities and mm.hp > 0:
                    prev_hp = h.hp
                    h.apply_damage(dice_count // 3)
                    stats["enemy_damage"] += prev_hp - h.hp

            for mm in alive:
                dmg, arm, p, dr, s, c = enemy_actions.get(mm, (0, 0, False, False, False, False))
                mm.armor += arm
                stats["enemy_armor"] += arm
                if mm.hp > 0:
                    if dr and h.hand:
                        idx = random.randrange(len(h.hand))
                        h.discard.append(h.hand.pop(idx))
                    if c:
                        keys = [k for k in list(h.exchange_effects.keys()) + list(h.combat_effects.keys()) if k != "cards_played"]
                        if keys:
                            k = random.choice(keys)
                            if k in h.exchange_effects:
                                del h.exchange_effects[k]
                            else:
                                del h.combat_effects[k]
                    attack_type = "ranged" if s else "melee"
                    if "Web Slinger" in mm.abilities:
                        attack_type = "melee"
                    prev_hp = h.hp
                    h.apply_damage(dmg, pierce=p)
                    stats["enemy_damage"] += prev_hp - h.hp
            leftover = h.armor
            for mm in alive:
                if "Power Sap" in mm.abilities and mm.hp > 0:
                    if h.combat_effects:
                        key = next(iter(h.combat_effects))
                        del h.combat_effects[key]
                        mm.hp += 1
            drawn = 0
            if round_num <= len(draw_seq):
                drawn = h.draw(draw_amt)
            else:
                drawn = 0
            if drawn == 0 and not h.hand and not h.deck and not h.discard:
                no_draw_turns += 1
            else:
                no_draw_turns = 0
            h.reset_armor()
            for mm in alive:
                mm.armor = 0
            if any("Cursed Thorns" in mm.abilities for mm in alive) and leftover > 0:
                prev_hp = h.hp
                h.apply_damage(leftover)
                stats["enemy_damage"] += prev_hp - h.hp

            if round_num >= 5:
                prev_hp = h.hp
                h.apply_damage(h.max_hp // 2)
                stats["enemy_damage"] += prev_hp - h.hp
                for mm in alive:
                    mm.hp = 0
                alive = [mm for mm in alive if mm.hp > 0]
                hero_hp.append(h.hp)
                break

            if no_draw_streak >= 2:
                prev_hp = h.hp
                damage = h.hp // 2
                h.apply_damage(damage)
                stats["enemy_damage"] += prev_hp - h.hp
                for mm in alive:
                    mm.hp = 0
                alive = [mm for mm in alive if mm.hp > 0]
                hero_hp.append(h.hp)
                break

            alive = [mm for mm in alive if mm.hp > 0]
            hero_hp.append(h.hp)

        stats["hero_hp"] = hero_hp
        print(f"  Combat {combat_idx+1} complete. Hero HP now {h.hp}")
        return stats

    final_hps: List[int] = []
    combat_hps: List[List[int]] = [[] for _ in range(6)]
    round_hp_lists: List[List[int]] = []
    hero_damage_total = 0
    hero_armor_total = 0
    enemy_totals_basic: Dict[str, Dict[str, float]] = {}
    enemy_totals_elite: Dict[str, Dict[str, float]] = {}
    success = 0

    for run_idx in range(n):
        if run_idx % 100 == 0:
            print(f"Starting run {run_idx+1}/{n}")
        if hero_name.lower() == "merlin":
            start_hp = 15
        elif hero_name.lower() == "hercules":
            start_hp = 25
        else:
            start_hp = 20
        hero = Hero(name=hero_name, hp=start_hp,
                    deck=[Card(c.name, c.type, c.dice, c.effects.copy(), c.rarity, c.upgrade)
                          for c in base_deck_fn()])
        encounters = [
            (
                [
                    Monster(
                        mon.name,
                        mon.hp,
                        mon.defense,
                        mon.type,
                        mon.abilities.copy(),
                        mon.action_table[:],
                    )
                    for mon in group
                ],
                kind,
            )
            for group, kind in encounter_list()
        ]

        hero.deck = hero.deck[:10]
        hero.hand.clear()
        hero.discard.clear()
        random.shuffle(hero.deck)
        hero.draw(4)

        last_alive = False
        for idx, (group, kind) in enumerate(encounters):
            hero.fate += 1
            stats = run_combat(hero, group, run_idx, idx)
            hero_damage_total += stats["hero_damage"]
            hero_armor_total += stats["hero_armor"]
            hero_hp_data = stats["hero_hp"]
            for i, val in enumerate(hero_hp_data):
                while len(round_hp_lists) <= i:
                    round_hp_lists.append([])
                round_hp_lists[i].append(val)
            if idx < len(combat_hps):
                combat_hps[idx].append(hero.hp)

            ename = group[0].name
            target_totals = (
                enemy_totals_basic if kind == "basic" else enemy_totals_elite
            )
            if ename not in target_totals:
                target_totals[ename] = {
                    "damage": 0,
                    "armor": 0,
                    "count": 0,
                    "monsters": 0,
                }
            target_totals[ename]["damage"] += stats["enemy_damage"]
            target_totals[ename]["armor"] += stats["enemy_armor"]
            target_totals[ename]["count"] += 1
            target_totals[ename]["monsters"] += len(group)

            if hero.hp <= 0:
                last_alive = False
            else:
                last_alive = all(m.hp <= 0 for m in group)
            if idx < len(encounters) - 1:
                upgrade = draw_upgrade(hero)
                hero.deck.append(upgrade)
                hero.hand.append(upgrade)
                hero.draw(3)

        final_hps.append(hero.hp)
        print(f"Finished run {run_idx+1}/{n} with HP {hero.hp}")
        if last_alive and hero.hp > 0:
            success += 1

    avg_hp = sum(final_hps) / n if n else 0
    print(f"Average final HP: {avg_hp:.2f}")
    for idx, lst in enumerate(combat_hps, 1):
        if lst:
            avg = sum(lst) / len(lst)
        else:
            avg = 0
        print(f"  After combat {idx}: {avg:.2f}")
    print()

    print("Average HP per round:")
    for idx, lst in enumerate(round_hp_lists, 1):
        avg = sum(lst) / len(lst) if lst else 0
        print(f"  Exchange {idx}: {avg:.2f}")
    print()

    print("Average hero totals per run:")
    print(f"  Damage dealt: {hero_damage_total / n:.2f}")
    print(f"  Armor gained: {hero_armor_total / n:.2f}\n")

    print("Enemy type averages (basic):")
    for ename, vals in enemy_totals_basic.items():
        monsters = vals["monsters"] or 1
        dmg = vals["damage"] / monsters
        arm = vals["armor"] / monsters
        print(f"  {ename}: dealt {dmg:.2f} dmg, gained {arm:.2f} armor")

    print("Enemy type averages (elite):")
    for ename, vals in enemy_totals_elite.items():
        monsters = vals["monsters"] or 1
        dmg = vals["damage"] / monsters
        arm = vals["armor"] / monsters
        print(f"  {ename}: dealt {dmg:.2f} dmg, gained {arm:.2f} armor")

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
