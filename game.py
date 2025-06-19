import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Action:
    time: int
    actor: str  # 'hero' or 'enemy'
    kind: str
    damage: int = 0
    times: Optional[List[int]] = None


@dataclass
class Card:
    """Defines what actions a card can perform at which times."""

    id: int
    actions: Dict[str, List[int]]


def _generate_cards() -> Dict[int, Card]:
    """Manually construct the seven default cards."""
    cards: Dict[int, Card] = {}

    cards[1] = Card(1, {
        "strong": [1, 2, 3],
        "quick": [1],
        "dodge": [1, 2, 3],
        "parry": [3],
    })

    cards[2] = Card(2, {
        "strong": [2, 3, 4],
        "quick": [2],
        "dodge": [2, 3, 4],
        "parry": [1],
    })

    cards[3] = Card(3, {
        "strong": [3, 4, 5],
        "quick": [3],
        "dodge": [3, 4, 5],
        "parry": [2],
    })

    cards[4] = Card(4, {
        "strong": [4, 5, 6],
        "quick": [4],
        "dodge": [4, 5, 6],
        "parry": [4],
    })

    cards[5] = Card(5, {
        "strong": [5, 6, 7],
        "quick": [5],
        "dodge": [5, 6, 7],
        "parry": [5],
    })

    cards[6] = Card(6, {
        "strong": [6, 7, 1],
        "quick": [6],
        "dodge": [6, 7, 1],
        "parry": [6],
    })

    cards[7] = Card(7, {
        "strong": [7, 1, 2],
        "quick": [7],
        "dodge": [7, 1, 2],
        "parry": [7],
    })

    return cards


CARDS: Dict[int, Card] = _generate_cards()


def format_card(card_id: int) -> str:
    """Return a user friendly description of the card's actions."""
    card = CARDS[card_id]

    ability_names = [
        ("A", "Heavy Attack", "strong"),
        ("B", "Quick Attack", "quick"),
        ("C", "Dodge", "dodge"),
        ("D", "Parry", "parry"),
    ]

    parts = []
    for letter, display, key in ability_names:
        times = "-".join(str(t) for t in card.actions[key])
        parts.append(f"{letter}) {display} ({times})")

    return f"{card_id}: " + " ".join(parts)


class Deck:
    """Deck of Time card IDs managed in a deque."""

    def __init__(self):
        ids = list(CARDS.keys())
        random.shuffle(ids)
        self.cards = deque(ids)

    def draw(self, n: int) -> List[int]:
        result = []
        for _ in range(n):
            if not self.cards:
                break
            result.append(self.cards.popleft())
        return result

    def return_to_bottom(self, card: int) -> None:
        self.cards.append(card)


class Hero:
    """Hero with HP, armor and a fixed starting hand."""

    def __init__(self, deck: Deck):
        self.hp = 15
        self.deck = deck
        # Start with the first set of cards in order
        self.hand = list(range(1, 8))
        self.armor = 1

        # The deck should contain a shuffled second set of cards
        deck.cards = deque(random.sample(list(CARDS.keys()), len(CARDS)))

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
            (1, 4),
            (3, 5),
            (4, 6),
            (6, 5),
            (7, 4),
        ]
        super().__init__("Samurai", 6, attacks)


class EnemyOni(Enemy):
    def __init__(self):
        attacks = [
            (1, 2),
            (3, 4),
            (5, 6),
            (7, 8),
        ]
        super().__init__("Oni", 10, attacks)


def choose_enemy():
    return random.choice([EnemySamurai(), EnemyOni()])


def parse_action(cmd):
    """Parse an action in the form '<card>-<letter>'."""
    if "-" not in cmd:
        return None
    card_str, option = cmd.split("-", 1)
    if not card_str.isdigit():
        return None
    option = option.strip().upper()
    mapping = {
        "A": "strong",
        "B": "quick",
        "C": "dodge",
        "D": "parry",
    }
    if option not in mapping:
        return None
    return mapping[option], int(card_str)


def main():
    deck = Deck()
    hero = Hero(deck)
    enemy = choose_enemy()

    while hero.hp > 0:
        print(f"\nHero HP: {hero.hp}\tEnemy {enemy.name} HP: {enemy.hp}")
        print("Hand:")
        for cid in sorted(hero.hand):
            print(" ", format_card(cid))
        e_time, e_dmg = enemy.next_attack()
        print(f"Enemy will attack at time {e_time} for {e_dmg} damage")

        actions = []  # list of (card_id, ability, times)
        times_used = set()
        resting = False
        while True:
            cmd = input("Action (<card>-<option> | rest | done): ").strip()
            if cmd == "done":
                break
            if cmd == "rest":
                if actions:
                    print("Cannot rest after selecting other actions")
                    continue
                resting = True
                break
            parsed = parse_action(cmd)
            if not parsed:
                print("Invalid command")
                continue
            ability, card_id = parsed
            if card_id not in hero.hand:
                print("You don't have that card")
                continue
            card = CARDS[card_id]
            if ability not in card.actions:
                print("That card can't perform that ability")
                continue
            times = card.actions[ability]
            conflict = sorted(t for t in times if t in times_used)
            if conflict:
                print(f"Time conflict at {conflict}")
                continue
            times_used.update(times)
            hero.use_card(card_id)
            actions.append((card_id, ability, times))

            # Show state after selection
            print("Remaining cards:")
            for cid in sorted(hero.hand):
                print(" ", format_card(cid))

            pending_temp = []
            for _, ab, ts in actions:
                if ab == "quick":
                    pending_temp.append((ts[0], "Quick Attack"))
                elif ab == "strong":
                    pending_temp.append((ts[-1], "Heavy Attack"))
                elif ab == "dodge":
                    pending_temp.append((ts[-1], "Dodge"))
                elif ab == "parry":
                    pending_temp.append((ts[0], "Parry"))
            pending_temp.sort(key=lambda x: x[0])
            sequence = ", ".join(f"{name} @ {t}" for t, name in pending_temp)
            print("Current sequence:", sequence or "(none)")

        dodge_times = set()
        parry_times = set()
        pending = []
        for _, kind, times in actions:
            if kind == "quick":
                pending.append(Action(times[0], "hero", "quick", 1, times=times))
            elif kind == "strong":
                pending.append(Action(times[-1], "hero", "strong", 4, times=times))
            elif kind == "dodge":
                dodge_times.update(times[-2:])
                pending.append(Action(times[-1], "hero", "dodge", times=times))
            elif kind == "parry":
                parry_times.add(times[0])
                pending.append(Action(times[0], "hero", "parry", times=times))
        pending.append(Action(e_time, "enemy", "attack", e_dmg, times=[e_time]))
        pending.sort(key=lambda a: a.time)

        double_next = False
        i = 0
        while i < len(pending):
            t = pending[i].time
            group = []
            while i < len(pending) and pending[i].time == t:
                group.append(pending[i])
                i += 1

            hero_defenses = [a for a in group if a.actor == "hero" and a.kind in {"dodge", "parry"}]
            hero_attacks = [a for a in group if a.actor == "hero" and a.kind in {"quick", "strong"}]
            enemy_actions = [a for a in group if a.actor == "enemy"]

            # Announce hero defensive moves
            for act in hero_defenses:
                if act.kind == "dodge":
                    print(f"Hero prepares to dodge ending at {act.time}")
                else:
                    print(f"Hero prepares to parry at {act.time}")

            hero_damage = 0
            enemy_damage = 0

            # Evaluate enemy attacks with defenses active
            for act in enemy_actions:
                print(f"Enemy attacks for {act.damage} damage at {act.time}")
                if act.time in dodge_times:
                    print("Hero dodges and avoids the attack")
                elif act.time in parry_times:
                    double_next = True
                    print("Hero parries! Next attack will deal double damage")
                else:
                    dmg = max(act.damage - hero.armor, 0)
                    enemy_damage += dmg
                    print(f"Hero takes {dmg} damage (after armor)")

            # Resolve hero attacks after defenses
            for act in hero_attacks:
                dmg = act.damage
                if double_next:
                    dmg *= 2
                    double_next = False
                    print("Hero's attack deals double damage!")
                hero_damage += dmg
                if act.kind == "quick":
                    print(f"Hero quick attacks for {dmg} damage")
                else:
                    print(f"Hero strong attacks for {dmg} damage")

            # Apply damage simultaneously
            enemy.hp -= hero_damage
            hero.hp -= enemy_damage

            # Stop round early if someone dies
            if hero.hp <= 0 or enemy.hp <= 0:
                break

        double_next = False

        # Draw new cards at the end of the round
        if resting:
            hero.draw(5)
        else:
            hero.draw(2)
        enemy.advance()

        if enemy.hp <= 0:
            print(f"Enemy {enemy.name} defeated!")
            hero.draw(3)
            enemy = choose_enemy()
            print(f"A new {enemy.name} appears!")

    print("Hero has fallen. Game over.")


if __name__ == "__main__":
    main()
