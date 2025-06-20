import random
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Set, Tuple


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
class Position:
    """Simple 2D grid position."""

    x: int
    y: int

    def __add__(self, other: Tuple[int, int]) -> "Position":
        return Position(self.x + other[0], self.y + other[1])

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def as_tuple(self) -> Tuple[int, int]:
        return (self.x, self.y)


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


# Relative coordinate sets for basic attack areas (enemy faces +y)
AREA_MAP: Dict[str, Set[Tuple[int, int]]] = {
    "Single hex": {(0, 1)},
    "Single": {(0, 1)},
    "Adjacent hexes": {(0, 1), (1, 0), (-1, 0), (0, -1)},
    "Self": {(0, 0)},
    "90\u00b0 front arc": {(0, 1), (1, 1)},
    "180\u00b0 front arc": {(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0)},
}


def attack_area(enemy: "Enemy", atk: EnemyCard) -> Set[Tuple[int, int]] | None:
    """Return absolute board coordinates affected by ``atk``."""
    if atk.area == "Global":
        return None
    rel = AREA_MAP.get(atk.area, set())
    return {(enemy.position.x + dx, enemy.position.y + dy) for dx, dy in rel}


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


def prompt_deck_order() -> List[int]:
    """Return a deck order chosen by the player or the default order."""
    default_order = list(range(1, 13))
    prompt = (
        "Enter desired card order (1-12 separated by spaces) or press Enter for"
        " default: "
    )
    while True:
        text = input(prompt).strip()
        if not text:
            print("Using default order.\n")
            return default_order
        parts = text.replace(",", " ").split()
        try:
            order = [int(p) for p in parts]
        except ValueError:
            print("Please enter only numbers.\n")
            continue
        if sorted(order) != default_order:
            print("Order must contain numbers 1-12 exactly once.\n")
            continue
        return order


def select_card(hero: "Hero") -> Card:
    """Prompt the player to choose a card from ``hero``'s hand.

    Displays stamina, the current hand and the next few cards in the deck. The
    chosen card is removed from the hand, its stamina cost is paid and it enters
    the cooldown row.
    """

    while True:
        print(f"Stamina: {hero.stamina}")
        print("Hand:")
        for c in hero.hand:
            print("  ", format_card(c))
        upcoming = ", ".join(card.name for card in hero.deck.peek())
        print(f"Upcoming: {upcoming}\n")

        text = input("Choose card id: ")
        try:
            card_id = int(text)
        except ValueError:
            print("Invalid input\n")
            continue
        if not hero.can_play(card_id):
            print("Cannot play that card\n")
            continue
        return hero.play_card(card_id)


class Hero:
    """Hero with HP, armor and a starting hand drawn in order."""

    def __init__(self, deck: Deck):
        self.hp = 15
        self.deck = deck
        self.armor = 1
        self.max_stamina = 6
        self.stamina = 6
        self.position = Position(0, 1)  # start one hex in front of enemy
        self.cooldown: List[List[Card]] = [[], []]
        self.heavy_bonus = 0
        # temporary round flags
        self.was_targeted = False
        self.priority_target = False
        self.damage_reduction = 0

        # Draw the starting hand
        self.hand = deck.draw(4)

    def start_round(self, targeted: bool) -> None:
        """Record whether the hero was targeted this round."""
        self.was_targeted = targeted or self.priority_target
        self.priority_target = False

    def draw(self, n: int) -> None:
        self.hand.extend(self.deck.draw(n))

    def play_card_free(self, card_id: int) -> Card:
        """Play ``card_id`` without paying stamina."""
        for idx, card in enumerate(self.hand):
            if card.id == card_id:
                self.hand.pop(idx)
                self.cooldown[0].append(card)
                return card
        raise ValueError("Card not in hand")

    def can_play(self, card_id: int) -> bool:
        """Return ``True`` if ``card_id`` is in hand and stamina suffices."""
        for card in self.hand:
            if card.id == card_id:
                if card.id == 5 and self.stamina <= 2:
                    return False
                return self.stamina >= card.stamina
        return False

    def play_card(self, card_id: int) -> Card:
        """Remove a card from hand, pay its stamina cost and start cooldown."""
        for idx, card in enumerate(self.hand):
            if card.id == card_id:
                if card.id == 5 and self.stamina <= 2:
                    raise ValueError("Cannot play card")
                if self.stamina < card.stamina:
                    raise ValueError("Cannot play card")
                self.stamina -= card.stamina
                self.hand.pop(idx)
                self.cooldown[0].append(card)
                return card
        raise ValueError("Card not in hand")

    def refresh_cooldown(self) -> None:
        """Return one card from cooldown to the deck if possible."""
        for slot in [1, 0]:
            if self.cooldown[slot]:
                card = self.cooldown[slot].pop(0)
                self.deck.return_to_bottom(card)
                break

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
        self.position = Position(0, 0)
        self.target_token: TargetToken | None = None
        # Buff applied to the next damaging attack
        self.next_damage_bonus = 0

    def telegraph(self) -> EnemyCard:
        """Return the upcoming card without advancing the deck."""
        return self.pattern[self.index]

    def set_target(self, token: TargetToken) -> None:
        """Store which hero is targeted this round."""
        self.target_token = token

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


def apply_enemy_attack(
    hero: "Hero", hero_card: Card, atk: EnemyCard, hero_first: bool, enemy: Enemy
) -> None:
    """Resolve the enemy's attack against ``hero`` given the played card."""

    # Oni and Samurai utility cards can modify upcoming attacks or the deck
    if enemy.name == "Oni":
        if atk.attack == "Rage Roar":
            hero.stamina = max(0, hero.stamina - 1)
            print("Oni's roar drains your stamina!")
            return
        if atk.attack == "Recuperate":
            enemy.next_damage_bonus += 1
            print("Oni gathers strength for its next strike.")
            return
    if enemy.name == "Samurai":
        if atk.attack == "Parry Counter":
            enemy.next_damage_bonus += 4
            print("Samurai prepares a lethal counter.")
            return
        if atk.attack == "Focused Stare":
            enemy.index = 0
            print("Samurai resets its stance.")
            return

    hits = 2 if atk.attack == "Double Swipe" else 1

    # Consume any stored damage bonus on the first hit only
    base_damage = atk.damage + enemy.next_damage_bonus
    enemy.next_damage_bonus = 0

    # Handle defensive card effects
    damage_reduction = hero.damage_reduction
    hero.damage_reduction = 0

    area = attack_area(enemy, atk)
    in_area = True if area is None else hero.position.as_tuple() in area

    if hero_card.card_type == CardType.Dodge and hero_card.speed >= atk.speed:
        if not in_area:
            print("You dodge the attack!")
            return
        print("Dodge failed!")

    if area is not None and not in_area:
        print("Enemy attack misses you.")
        return

    parry_card = hero_card.card_type == CardType.Parry or (
        hero_card.id == 6 and hero_first
    )
    if parry_card:
        if hero_card.speed == atk.speed:
            print("Parry successful!")
            hero.heavy_bonus += 2
            return
        if hero_card.card_type == CardType.Parry or hero_card.id == 6:
            print("Parry failed!")

    block_reduction = 2 if hero_card.card_type == CardType.Block else 0

    total = 0
    for i in range(hits):
        dmg = base_damage if i == 0 else atk.damage
        dmg = max(0, dmg - hero.armor)
        if damage_reduction:
            dmg = max(0, dmg - damage_reduction)
            damage_reduction = 0
        if block_reduction:
            dmg = max(0, dmg - block_reduction)
            block_reduction = 0
        hero.hp -= dmg
        total += dmg

    print(f"Enemy hits you for {total} damage. HP now {hero.hp}")


def apply_hero_card(hero: "Hero", enemy: Enemy, card: Card) -> None:
    """Apply the effects of ``card`` when used by ``hero``."""
    if card.card_type == CardType.HeavyAtk:
        base = 4
        if card.id == 5:
            base = 5
        dmg = base + hero.heavy_bonus
        hero.heavy_bonus = 0
        enemy.hp -= dmg
        print(f"You hit enemy for {dmg} damage. Enemy HP {enemy.hp}")
    elif card.card_type == CardType.LightAtk:
        dmg = 2
        if card.id == 1 and not hero.was_targeted:
            dmg += 1
        enemy.hp -= dmg
        print(f"You hit enemy for {dmg} damage. Enemy HP {enemy.hp}")
        if card.id == 4:
            # Twin Strikes chain
            for c in hero.hand:
                if c.id == 6:
                    chained = hero.play_card_free(6)
                    apply_hero_card(hero, enemy, chained)
                    break
    elif card.card_type in (CardType.Dodge, CardType.Parry):
        action = "dodge" if card.card_type == CardType.Dodge else "parry"
        print(f"You attempt a {action}...")
        if card.id == 3:
            # Cross-Step moves one hex to the left before resolving
            hero.position = hero.position + (-1, 0)
        if card.id == 9:
            # Shadow Step teleports to a back hex (behind enemy)
            hero.position = enemy.position + (-1, -1)
        if card.id == 7:
            hero.damage_reduction = 2
    elif card.card_type == CardType.Block:
        hero.damage_reduction = 2
        print("You brace for impact...")
    elif card.card_type == CardType.Utility:
        if card.id == 8:
            hero.refresh_cooldown()
            print("You center your ki and refresh a card.")
        elif card.id == 10:
            hero.priority_target = True
            enemy.hp -= 2  # base light attack effect
            print("You flaunt your skill, drawing aggro.")
            print(f"Enemy HP {enemy.hp}")
        elif card.id == 11:
            hero.stamina = min(hero.max_stamina, hero.stamina + 1)
            print("You breathe and regain stamina, skipping your attack.")
        else:
            print("You perform the action.")
    else:
        print("You perform the action.")


def resolve_turn(hero: "Hero", enemy: Enemy, card: Card, atk: EnemyCard) -> None:
    """Resolve one turn comparing ``card`` speed against ``atk`` speed."""
    hero_first = card.speed >= atk.speed
    if hero_first:
        apply_hero_card(hero, enemy, card)
        if enemy.hp > 0:
            apply_enemy_attack(hero, card, atk, True, enemy)
    else:
        apply_enemy_attack(hero, card, atk, False, enemy)
        if hero.hp > 0:
            apply_hero_card(hero, enemy, card)


def battle() -> None:
    """Simple command line battle following the five-phase loop."""
    order = prompt_deck_order()
    hero = Hero(create_samurai_deck(order))
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
        enemy.set_target(token)
        hero.start_round(True)
        print(f"Target token drawn: {token.value}. You are targeted.")

        # Phase 3: hero selects a card
        card = select_card(hero)

        # Phase 4: resolve actions
        resolve_turn(hero, enemy, card, atk)

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
