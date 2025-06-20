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


class TargetToken(Enum):
    """Possible targeting tokens used by the enemy."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


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

    attack: str
    speed: int
    damage: int
    area: str
    target_logic: str


# Pre-built enemy pattern decks following the design document
OniPatternDeck: List[EnemyCard] = [
    EnemyCard("Club Sweep", 2, 4, "90° front arc", "Random hero in arc"),
    EnemyCard("Leap Crush", 1, 6, "Impact hex + adj.", "Farthest hero ≤ 3"),
    EnemyCard("Rage Roar", 3, 0, "Global", "All heroes lose 1 Stamina"),
    EnemyCard("Double Swipe", 2, 3, "180° front arc", "Two random heroes hit once"),
    EnemyCard("Overhead Smash", 1, 8, "Single hex", "Random hero ≤ 1"),
    EnemyCard("Recuperate", 0, 0, "", "Oni gains +1 dmg next card"),
]

SamuraiPatternDeck: List[EnemyCard] = [
    EnemyCard("Iaido Draw", 3, 4, "Single", "Hero with most HP"),
    EnemyCard("Feint & Thrust", 2, 3, "Single", "Random hero ≤ 2"),
    EnemyCard("Whirlwind Slashes", 2, 2, "Adjacent hexes", "All adjacent heroes"),
    EnemyCard("Parry Counter", 3, 0, "Self", "Gains 'next attack +4 dmg'"),
    EnemyCard("Rising Strike", 1, 6, "Single", "Target from Parry buff"),
    EnemyCard("Focused Stare", 0, 0, "", "Switch stance → restart at 1"),
]


def format_card(card: Card) -> str:
    """Return a user friendly description of the card."""
    extra = f" - {card.extra_rule}" if card.extra_rule else ""
    return (
        f"{card.id}: {card.name} [{card.card_type.name}] "
        f"Speed {card.speed} | Stamina {card.stamina}{extra}"
    )


class Deck:
    """Deck of :class:`Card` objects managed in a deque."""

    def __init__(self, ordered_cards: List[Card]):
        """Create a deck from ``ordered_cards``.

        The list order is preserved so callers can define an exact card cycle.
        """
        self.cards = deque(ordered_cards)
        self.card_defs = {card.id: card for card in ordered_cards}

    def draw(self, n: int) -> List[Card]:
        """Remove and return up to ``n`` cards from the top of the deck."""
        result: List[Card] = []
        for _ in range(n):
            if not self.cards:
                break
            result.append(self.cards.popleft())
        return result

    def card(self, card_id: int) -> Card:
        return self.card_defs[card_id]

    def peek(self, n: int = 3) -> List[Card]:
        """Return the next ``n`` cards without removing them."""
        return list(self.cards)[:n]

    def return_to_bottom(self, card: Card) -> None:
        """Place ``card`` on the bottom of the deck."""
        self.cards.append(card)


def create_samurai_deck(order: List[int]) -> Deck:
    """Return a :class:`Deck` with Samurai cards in ``order``."""
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
    ordered_cards = [cards[i] for i in order]
    return Deck(ordered_cards)


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
        self.cooldown: List[List[Card]] = [[], []]
        self.heavy_bonus = 0

        # Draw the starting hand
        self.hand = deck.draw(4)

    def draw(self, n: int) -> None:
        self.hand.extend(self.deck.draw(n))

    def can_play(self, card_id: int) -> bool:
        """Return ``True`` if ``card_id`` is in hand and stamina suffices."""
        for card in self.hand:
            if card.id == card_id:
                return self.stamina >= card.stamina
        return False

    def play_card(self, card_id: int) -> Card:
        """Remove a card from hand, pay its stamina cost and start cooldown."""
        for idx, card in enumerate(self.hand):
            if card.id == card_id:
                if self.stamina < card.stamina:
                    raise ValueError("Cannot play card")
                self.stamina -= card.stamina
                self.hand.pop(idx)
                self.cooldown[0].append(card)
                return card
        raise ValueError("Card not in hand")

    def end_round(self) -> None:
        """Advance cooldown slots, refresh stamina and redraw up to 4 cards."""
        expired = self.cooldown.pop()
        for card in expired:
            self.deck.return_to_bottom(card)
        self.cooldown.insert(0, [])
        self.stamina = self.max_stamina
        self.draw(4 - len(self.hand))


class Enemy:
    """Enemy using a deterministic pattern deck."""

    def __init__(self, name: str, hp: int, pattern: List[EnemyCard]):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.pattern = pattern
        self.index = 0

    def telegraph(self) -> EnemyCard:
        """Return the upcoming card without advancing the deck."""
        return self.pattern[self.index]

    def advance(self) -> None:
        """Move to the next card, looping back to the start when needed."""
        self.index = (self.index + 1) % len(self.pattern)


class EnemySamurai(Enemy):
    def __init__(self):
        super().__init__("Samurai", 6, SamuraiPatternDeck)


class EnemyOni(Enemy):
    def __init__(self):
        super().__init__("Oni", 10, OniPatternDeck)


def choose_enemy() -> Enemy:
    """Randomly pick an enemy."""
    return random.choice([EnemySamurai(), EnemyOni()])


def draw_target() -> TargetToken:
    """Randomly choose a target token each round."""
    return random.choice(list(TargetToken))


def battle() -> None:
    """Simple command line battle following the five-phase loop."""
    hero = Hero(create_samurai_deck(list(range(1, 13))))
    enemy = choose_enemy()

    print(f"An enemy {enemy.name} approaches!\n")

    MAX_ROUNDS = 10
    round_no = 1
    while hero.hp > 0 and enemy.hp > 0 and round_no <= MAX_ROUNDS:
        print(f"-- Round {round_no} --")

        # Phase 1: telegraph the next enemy card
        atk = enemy.telegraph()
        print(
            f"Enemy plays: {atk.attack} (Speed {atk.speed}, Dmg {atk.damage})"
        )

        # Phase 2: draw a target token
        token = draw_target()
        print(f"Target token drawn: {token.value}")

        # Phase 3: hero selects a card
        print(f"Stamina: {hero.stamina}")
        print("Hand:")
        for card in hero.hand:
            print("  ", format_card(card))

        choice = input("Choose card id: ")
        try:
            card_id = int(choice)
        except ValueError:
            print("Invalid input\n")
            continue
        if not hero.can_play(card_id):
            print("Cannot play that card\n")
            continue
        card = hero.play_card(card_id)

        # Phase 4: resolve by speed
        hero_first = card.speed >= atk.speed
        damage = max(0, atk.damage - hero.armor)

        def resolve_enemy() -> None:
            nonlocal damage
            if card.card_type == CardType.Dodge and card.speed >= atk.speed:
                moved = input("Did you move out of the danger area? (y/n): ")
                if moved.lower().startswith("y"):
                    print("You dodge the attack!")
                    return
                print("Dodge failed!")
            if card.card_type == CardType.Parry:
                if card.speed == atk.speed:
                    print("Parry successful!")
                    hero.heavy_bonus += 2
                    return
                print("Parry failed!")
            actual = damage
            if card.card_type == CardType.Block:
                actual = max(0, actual - 2)
            hero.hp -= actual
            print(f"Enemy hits you for {actual} damage. HP now {hero.hp}")

        def resolve_hero() -> None:
            if card.card_type == CardType.HeavyAtk:
                dmg = 4 + hero.heavy_bonus
                hero.heavy_bonus = 0
                enemy.hp -= dmg
                print(f"You hit enemy for {dmg} damage. Enemy HP {enemy.hp}")
            elif card.card_type == CardType.LightAtk:
                enemy.hp -= 2
                print(f"You hit enemy for 2 damage. Enemy HP {enemy.hp}")
            elif card.card_type == CardType.Dodge:
                print("You attempt a dodge...")
            elif card.card_type == CardType.Parry:
                print("You attempt a parry...")
            else:
                print("You perform the action.")

        if hero_first:
            resolve_hero()
            if enemy.hp > 0:
                resolve_enemy()
        else:
            resolve_enemy()
            if hero.hp > 0:
                resolve_hero()

        print()

        # Phase 5: cooldown and draw
        hero.end_round()
        enemy.advance()
        round_no += 1

    print("Battle ended.")


def main() -> None:
    """Run a minimal battle demo."""
    battle()


if __name__ == "__main__":
    main()
