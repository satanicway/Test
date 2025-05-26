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
                self.fate -= 1
            if dmg > 0:
                self.hp -= dmg


@dataclass
class Monster:
    name: str
    hp: int
    defense: int
    type: str
    abilities: List[str] = field(default_factory=list)
    armor: int = 0

    def roll_action(self) -> (int, int):
        """Return (damage, armor) for the exchange."""
        damage = random.randint(1, self.defense)
        armor = 0
        if "tough" in self.abilities:
            armor += 1
        return damage, armor


class Combat:
    """Run a combat between a hero and a monster."""

    def __init__(self, hero: Hero, monster: Monster):
        self.hero = hero
        self.monster = monster

    def exchange(self) -> bool:
        """Run a single exchange. Return True if both combatants live."""
        ranged = [c for c in self.hero.hand if c.type == "ranged"]
        melee = [c for c in self.hero.hand if c.type == "melee"]
        self.hero.hand.clear()
        order = ranged + melee

        for card in order:
            roll = card.roll()
            dmg = roll + card.effects.get("damage", 0)
            arm = card.effects.get("armor", 0)
            self.hero.add_armor(arm)
            actual = max(0, dmg - self.monster.armor)
            self.monster.armor = max(0, self.monster.armor - dmg)
            self.monster.hp -= actual
            self.hero.discard.append(card)

        dmg, arm = self.monster.roll_action()
        self.monster.armor += arm
        if self.monster.hp > 0:
            self.hero.apply_damage(dmg)
            if "poison" in self.monster.abilities:
                self.hero.apply_damage(1)

        self.hero.reset_armor()
        self.monster.armor = 0
        return self.hero.hp > 0 and self.monster.hp > 0

    def run(self) -> None:
        round_num = 1
        while self.hero.hp > 0 and self.monster.hp > 0:
            print(f"-- Round {round_num} --")
            self.hero.draw(1)
            print("Hero plays:", ", ".join(c.name for c in self.hero.hand))
            alive = self.exchange()
            print(f"Hero HP: {self.hero.hp}")
            print(f"Monster HP: {self.monster.hp}\n")
            if not alive:
                break
            round_num += 1
        if self.hero.hp <= 0:
            print(f"{self.hero} was defeated by {self.monster.name}!")
        else:
            print(f"{self.monster.name} was defeated!")


MERLIN_UPGRADES = [
    Card("Runic Ray", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Crystal-Shot Volley", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Glyph-Marking Bolt", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Voice of Destiny", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Druidic Ways", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Protective Mists", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Mark of Fated Fall", "melee", "1d6", rarity="common", upgrade=True),
    Card("Veil-Rain of Chaos", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Oracle of Avalon", "ranged", "1d6", rarity="common", upgrade=True),

    Card("Waves of Destiny", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Ancestral Echoes", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Whispers of the Wyrd", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Nature’s Rebuke", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Guard from Beyond", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Sage's Alacrity", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Charged Spirits", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Avalon's Light", "ranged", "1d6", rarity="uncommon", upgrade=True),
    Card("Spiritual Gifts", "ranged", "1d6", rarity="uncommon", upgrade=True),

    Card("Rune Shatter", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Sigil of Final Fate", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Conflux Lance", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Echoes of Guidance", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Mercury Guard", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Old-Ways Shillelagh", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Favor of the Druids", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Chains of Morrígan", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Spirits of the Lands", "ranged", "1d6", rarity="rare", upgrade=True),
]

HERCULES_UPGRADES = [
    Card("Bondless Effort", "melee", "1d6", rarity="common", upgrade=True),
    Card("Colossus Smash", "melee", "1d6", rarity="common", upgrade=True),
    Card("Olympian Call", "melee", "1d6", rarity="common", upgrade=True),
    Card("Divine Resilience", "melee", "1d6", rarity="common", upgrade=True),
    Card("Horde Breaker", "melee", "1d6", rarity="common", upgrade=True),
    Card("Disorienting Blow", "melee", "1d6", rarity="common", upgrade=True),
    Card("Piercing Spear", "ranged", "1d6", rarity="common", upgrade=True),
    Card("Fated War", "melee", "1d6", rarity="common", upgrade=True),
    Card("Fortune's Throw", "ranged", "1d6", rarity="common", upgrade=True),

    Card("Pain Strike", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Fortifying Attack", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Bone-Splinter Whirl", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Glorious Uproar", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Guided By The Gods", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Chiron's Training", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Once Isn't Enough", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Strength from Anger", "melee", "1d6", rarity="uncommon", upgrade=True),
    Card("Enduring Wave", "melee", "1d6", rarity="uncommon", upgrade=True),

    Card("Zeus' Wrath", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Ares' Will", "melee", "1d6", rarity="rare", upgrade=True),
    Card("True Might of Hercules", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Athena's Guidance", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Apollo's Sunburst", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Nike's Desire", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Blessing of Hephaestus", "ranged", "1d6", rarity="rare", upgrade=True),
    Card("Hermes’ Delivery", "melee", "1d6", rarity="rare", upgrade=True),
    Card("Eris' Pandemonium", "melee", "1d6", rarity="rare", upgrade=True),
]


def merlin_base_deck() -> List[Card]:
    """Return Merlin's starting deck of ten cards."""
    return [
        Card("Arcane Bolt", "ranged", "1d6", {"damage": 1}),
        Card("Arcane Bolt", "ranged", "1d6", {"damage": 1}),
        Card("Arcane Bolt", "ranged", "1d6", {"damage": 1}),
        Card("Arcane Bolt", "ranged", "1d6", {"damage": 1}),
        Card("Mystic Barrier", "ranged", "1d4", {"armor": 2}),
        Card("Mystic Barrier", "ranged", "1d4", {"armor": 2}),
        Card("Staff Strike", "melee", "1d6"),
        Card("Staff Strike", "melee", "1d6"),
        Card("Staff Strike", "melee", "1d6"),
        Card("Staff Strike", "melee", "1d6"),
    ]


def hercules_base_deck() -> List[Card]:
    """Return Hercules' starting deck of ten cards."""
    return [
        Card("Slash", "melee", "1d6", {"damage": 1}),
        Card("Slash", "melee", "1d6", {"damage": 1}),
        Card("Slash", "melee", "1d6", {"damage": 1}),
        Card("Slash", "melee", "1d6", {"damage": 1}),
        Card("Block", "melee", "1d4", {"armor": 2}),
        Card("Block", "melee", "1d4", {"armor": 2}),
        Card("Block", "melee", "1d4", {"armor": 2}),
        Card("Block", "melee", "1d4", {"armor": 2}),
        Card("Javelin", "ranged", "1d6", {"damage": 1}),
        Card("Javelin", "ranged", "1d6", {"damage": 1}),
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
    - Average total damage dealt and armor gained by the hero.
    - Average damage taken from and armor gained by each enemy type.
    - Percentage of runs where the hero defeated the final foe while alive.
    """

    base_deck_fn = merlin_base_deck if hero_name.lower() == "merlin" else hercules_base_deck

    def encounter_list() -> List[Monster]:
        return [
            Monster("Goblin", hp=8, defense=6, type="goblin"),
            Monster("Orc", hp=10, defense=6, type="orc", abilities=["tough"]),
            Monster("Skeleton", hp=10, defense=5, type="undead", abilities=["poison"]),
            Monster("Wolf", hp=12, defense=5, type="beast"),
            Monster("Troll", hp=12, defense=7, type="troll", abilities=["tough"]),
            Monster("Dragonling", hp=14, defense=8, type="dragon", abilities=["tough"]),
        ]

    def run_combat(h: Hero, m: Monster) -> Dict[str, int]:
        """Simulate a combat without printing and return statistics."""
        stats = {"hero_damage": 0, "hero_armor": 0, "enemy_damage": 0, "enemy_armor": 0}
        round_num = 1
        while h.hp > 0 and m.hp > 0:
            h.draw(1)
            ranged = [c for c in h.hand if c.type == "ranged"]
            melee = [c for c in h.hand if c.type == "melee"]
            h.hand.clear()
            order = ranged + melee
            for card in order:
                roll = card.roll()
                dmg = roll + card.effects.get("damage", 0)
                arm = card.effects.get("armor", 0)
                h.add_armor(arm)
                stats["hero_armor"] += arm
                actual = max(0, dmg - m.armor)
                m.armor = max(0, m.armor - dmg)
                m.hp -= actual
                stats["hero_damage"] += actual
                h.discard.append(card)
            dmg, arm = m.roll_action()
            m.armor += arm
            stats["enemy_armor"] += arm
            if m.hp > 0:
                prev_hp = h.hp
                h.apply_damage(dmg)
                if "poison" in m.abilities:
                    h.apply_damage(1)
                stats["enemy_damage"] += prev_hp - h.hp
            h.reset_armor()
            m.armor = 0
            round_num += 1
        return stats

    final_hps: List[int] = []
    hero_damage_total = 0
    hero_armor_total = 0
    enemy_totals: Dict[str, Dict[str, float]] = {}
    success = 0

    for _ in range(n):
        hero = Hero(name=hero_name, hp=20,
                    deck=[Card(c.name, c.type, c.dice, c.effects.copy(), c.rarity, c.upgrade)
                          for c in base_deck_fn()])
        encounters = [Monster(m.name, m.hp, m.defense, m.type, m.abilities.copy())
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
    print("Final HP per run:")
    for i, hp in enumerate(final_hps, 1):
        print(f"  Run {i}: {hp}")
    print(f"Average final HP: {avg_hp:.2f}\n")

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
