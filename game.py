import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List


class CardType(Enum):
    """Enumeration of possible card types."""

    LightAtk = auto()
    HeavyAtk = auto()
    Dodge = auto()
    Parry = auto()
    Block = auto()
    Utility = auto()


@dataclass
class Card:
    """Single action card."""

    id: int
    name: str
    card_type: CardType
    speed: int
    stamina: int
    extra_rule: str = ""


@dataclass
class EnemyCard:
    """Single enemy pattern card."""

    name: str
    speed: int
    dmg: int


def format_card(card: Card) -> str:
    """Return a user friendly description of the card."""
    extra = f" - {card.extra_rule}" if card.extra_rule else ""
    return (
        f"{card.id}: {card.name} [{card.card_type.name}] "
        f"Speed {card.speed} | Stamina {card.stamina}{extra}"
    )


class Deck:
    """Deck of card IDs managed in a deque."""

    def __init__(self, order: List[int], cards: Dict[int, Card]):
        self.cards = deque(order)
        self.card_defs = cards

    def draw(self, n: int) -> List[int]:
        result = []
        for _ in range(n):
            if not self.cards:
                break
            result.append(self.cards.popleft())
        return result

    def card(self, card_id: int) -> Card:
        return self.card_defs[card_id]

    def peek(self, n: int = 3) -> List[int]:
        """Return the next ``n`` card IDs without removing them."""
        return list(self.cards)[:n]

    def return_to_bottom(self, card: int) -> None:
        self.cards.append(card)


def create_samurai_deck(order: List[int]) -> Deck:
    """Return a Deck with Samurai cards in the specified order."""
    cards: Dict[int, Card] = {
        1: Card(1, "Iaijutsu Cut", CardType.LightAtk, 3, 1,
                "+1 dmg if you were un-targeted this round."),
        2: Card(2, "Riposte", CardType.Parry, 2, 2, "Next Heavy +2 dmg."),
        3: Card(3, "Cross-Step", CardType.Dodge, 3, 1, "Move 1 before resolving."),
        4: Card(4, "Twin Strikes", CardType.LightAtk, 2, 1,
                "Chain: you may immediately play card #6 at 0 Stamina."),
        5: Card(5, "Great Kesa", CardType.HeavyAtk, 1, 3,
                "5 dmg; unusable if Stamina <= 2."),
        6: Card(6, "Draw Cut", CardType.LightAtk, 3, 1,
                "Counts as Parry if resolving before an attack."),
        7: Card(7, "Guarded Stance", CardType.Block, 1, 1,
                "Reduce next hit by 2."),
        8: Card(8, "Ki Focus", CardType.Utility, 0, 0, "Refresh 1 cooldown slot."),
        9: Card(9, "Shadow Step", CardType.Dodge, 3, 1,
                "Teleport to any adjacent back-hex."),
        10: Card(10, "Flourish", CardType.LightAtk, 2, 1,
                 "Pull aggro: you become priority target next round."),
        11: Card(11, "Zen Recovery", CardType.Utility, 0, 0,
                 "Gain 1 Stamina; skip attack."),
        12: Card(12, "Crescent Moon", CardType.HeavyAtk, 1, 3,
                 "4 dmg in 180\u00b0 front arc."),
    }
    return Deck(order, cards)


def parse_action(hero: 'Hero', text: str) -> Card:
    """Parse a user's card selection and return the ``Card`` object."""
    card_id = int(text)
    card = hero.play_card(card_id)
    return card


class Hero:
    """Hero with HP, armor and a starting hand drawn in order."""

    def __init__(self, deck: Deck):
        self.hp = 15
        self.deck = deck
        self.armor = 1
        self.max_stamina = 6
        self.stamina = 6
        self.cooldown: List[List[int]] = [[], []]

        # Draw the starting hand
        self.hand = deck.draw(4)

    def draw(self, n: int) -> None:
        self.hand.extend(self.deck.draw(n))

    def play_card(self, card_id: int) -> Card:
        """Remove a card from hand and pay its stamina cost."""
        if card_id not in self.hand:
            raise ValueError("Card not in hand")
        card = self.deck.card(card_id)
        if self.stamina < card.stamina:
            raise ValueError("Not enough stamina")
        self.stamina -= card.stamina
        self.hand.remove(card_id)
        return card

    def end_round(self, played: List[int]) -> None:
        """Advance cooldown slots and redraw to a hand of 4."""
        expired = self.cooldown.pop(0)
        for cid in expired:
            self.deck.return_to_bottom(cid)
        self.cooldown.append(played)
        self.draw(4 - len(self.hand))


class Enemy:
    """Enemy using a deterministic pattern deck."""

    def __init__(self, name: str, hp: int, pattern: List[EnemyCard]):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.pattern = pattern
        self.index = 0

    def next_attack(self) -> EnemyCard:
        return self.pattern[self.index]

    def advance(self) -> None:
        self.index = (self.index + 1) % len(self.pattern)


class EnemySamurai(Enemy):
    def __init__(self):
        pattern = [
            EnemyCard("Iaido Draw", 3, 4),
            EnemyCard("Feint & Thrust", 2, 3),
            EnemyCard("Whirlwind Slashes", 2, 2),
            EnemyCard("Parry Counter", 3, 0),
            EnemyCard("Rising Strike", 1, 6),
            EnemyCard("Focused Stare", 0, 0),
        ]
        super().__init__("Samurai", 6, pattern)


class EnemyOni(Enemy):
    def __init__(self):
        pattern = [
            EnemyCard("Club Sweep", 2, 4),
            EnemyCard("Leap Crush", 1, 6),
            EnemyCard("Rage Roar", 3, 0),
            EnemyCard("Double Swipe", 2, 3),
            EnemyCard("Overhead Smash", 1, 8),
            EnemyCard("Recuperate", 0, 0),
        ]
        super().__init__("Oni", 10, pattern)


def choose_enemy() -> Enemy:
    """Randomly pick an enemy."""
    return random.choice([EnemySamurai(), EnemyOni()])


def battle() -> None:
    """Simple command line battle showcasing card resolution by speed."""
    hero = Hero(create_samurai_deck(list(range(1, 13))))
    enemy = choose_enemy()

    print(f"An enemy {enemy.name} approaches!\n")

    round_no = 1
    while hero.hp > 0 and enemy.hp > 0:
        print(f"-- Round {round_no} --")
        atk = enemy.next_attack()
        print(f"Enemy plays: {atk.name} (Speed {atk.speed}, Dmg {atk.dmg})")

        print(f"Stamina: {hero.stamina}")
        print("Hand:")
        for cid in hero.hand:
            print("  ", format_card(hero.deck.card(cid)))

        choice = input("Choose card id: ")
        try:
            card = parse_action(hero, choice)
        except Exception as exc:
            print(f"Invalid card: {exc}\n")
            continue

        if card.speed >= atk.speed:
            first, second = card.name, atk.name
        else:
            first, second = atk.name, card.name
        print(f"Resolution order: {first} then {second}\n")

        hero.end_round([card.id])
        enemy.advance()
        round_no += 1

    print("Battle ended.")


def main() -> None:
    """Run a minimal battle demo."""
    battle()


if __name__ == "__main__":
    main()
