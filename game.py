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




def _generate_cards() -> Dict[int, Card]:
    """Create the seven default cards."""
    cards: Dict[int, Card] = {
        1: Card(1, "Quick Slash", CardType.LightAtk, 1, 1),
        2: Card(2, "Heavy Strike", CardType.HeavyAtk, 4, 3),
        3: Card(3, "Evasive Roll", CardType.Dodge, 2, 1),
        4: Card(4, "Shield Block", CardType.Block, 2, 1),
        5: Card(5, "Riposte", CardType.Parry, 3, 2),
        6: Card(6, "Focus", CardType.Utility, 0, 0, "Draw 1 card"),
        7: Card(7, "Power Lunge", CardType.HeavyAtk, 5, 4),
    }
    return cards


CARDS: Dict[int, Card] = _generate_cards()


def format_card(card_id: int) -> str:
    """Return a user friendly description of the card."""
    card = CARDS[card_id]
    extra = f" - {card.extra_rule}" if card.extra_rule else ""
    return (
        f"{card.id}: {card.name} [{card.card_type.name}] "
        f"Speed {card.speed} | Stamina {card.stamina}{extra}"
    )


class Deck:
    """Deck of Time card IDs managed in a deque."""

    def __init__(self):
        ids = list(CARDS.keys())
        self.cards = deque(ids)

    def draw(self, n: int) -> List[int]:
        result = []
        for _ in range(n):
            if not self.cards:
                break
            result.append(self.cards.popleft())
        return result

    def peek(self, n: int = 3) -> List[int]:
        """Return the next ``n`` card IDs without removing them."""
        return list(self.cards)[:n]

    def return_to_bottom(self, card: int) -> None:
        self.cards.append(card)


class Hero:
    """Hero with HP, armor and a starting hand drawn in order."""

    def __init__(self, deck: Deck):
        self.hp = 15
        self.deck = deck
        self.armor = 1

        # Draw the starting hand
        self.hand = deck.draw(4)

    def draw(self, n):
        self.hand.extend(self.deck.draw(n))

    def use_card(self, card: int) -> None:
        if card in self.hand:
            self.hand.remove(card)
            self.deck.return_to_bottom(card)


class Enemy:
    """Base enemy with name, hp and attack sequence."""

    def __init__(self, name, hp, attacks):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attacks = attacks  # list of (time, dmg)
        self.index = 0

    def next_attack(self):
        return self.attacks[self.index]

    def advance(self):
        self.index = (self.index + 1) % len(self.attacks)


class EnemySamurai(Enemy):
    def __init__(self):
        attacks = [
            (1, 4),  # round 1
            (4, 5),  # round 2
            (6, 4),  # round 3
            (2, 4),  # round 4
            (5, 6),  # round 5
            (7, 4),  # round 6
            (3, 5),  # round 7
        ]
        super().__init__("Samurai", 6, attacks)


class EnemyOni(Enemy):
    def __init__(self):
        attacks = [
            (2, 3),  # round 1
            (4, 5),  # round 2
            (6, 7),  # round 3
            (1, 3),  # round 4
            (5, 5),  # round 5
            (3, 4),  # round 6
            (7, 6),  # round 7
        ]
        super().__init__("Oni", 10, attacks)


def choose_enemy() -> Enemy:
    """Randomly pick an enemy."""
    return random.choice([EnemySamurai(), EnemyOni()])


def main() -> None:
    """Display all default cards."""
    print("Available cards:")
    for cid in sorted(CARDS):
        print(" ", format_card(cid))


if __name__ == "__main__":
    main()
