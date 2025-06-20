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
    """Display all Samurai cards in the provided order."""
    order = list(range(1, 13))
    deck = create_samurai_deck(order)
    print("Available cards:")
    for cid in order:
        print(" ", format_card(deck.card(cid)))


if __name__ == "__main__":
    main()
