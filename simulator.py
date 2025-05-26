import random
from dataclasses import dataclass, field
from typing import List, Dict


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

    def roll(self) -> int:
        return roll_dice(self.dice)


@dataclass
class Hero:
    hp: int
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    armor: int = 0
    fate: int = 0

    def draw(self, count: int = 1) -> None:
        for _ in range(count):
            if self.deck:
                self.hand.append(self.deck.pop(0))

    def commit_card(self, index: int) -> Card:
        return self.hand.pop(index)

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


def main():
    deck = [
        Card("Slash", "melee", "1d6", {"damage": 1}),
        Card("Block", "melee", "1d4", {"armor": 2}),
        Card("Arrow", "ranged", "1d6", {"damage": 1}),
    ]
    hero = Hero(hp=20, deck=deck.copy())
    hero.draw(2)

    monster = Monster("Goblin", hp=15, defense=6, type="goblin", abilities=["tough"])
    combat = Combat(hero, monster)
    combat.run()


if __name__ == "__main__":
    main()
