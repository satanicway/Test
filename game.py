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

    for cid in range(1, 8):
        actions: Dict[str, List[int]] = {}

        # Each card has a two-slot quick window starting at its ID
        actions["quick"] = [cid, (cid % 7) + 1]

        if cid % 2 == 1:  # odd cards use parry and have strong attacks
            actions["parry"] = [cid]
            actions["strong"] = [
                cid,
                (cid % 7) + 1,
                ((cid + 1) % 7) + 1,
            ]
        else:  # even cards use dodge
            actions["dodge"] = [cid]

        cards[cid] = Card(cid, actions)

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
        times = card.actions.get(key)
        if not times:
            continue  # this card lacks the ability
        parts.append(f"{letter}) {display} ({'-'.join(map(str, times))})")

    return f"{card_id}: " + " ".join(parts)


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
        hero.draw(max(0, 4 - len(hero.hand)))
        print("Hand (max 4 cards):")
        for cid in sorted(hero.hand):
            print(" ", format_card(cid))
        e_time, e_dmg = enemy.next_attack()
        print(f"Enemy will attack at time {e_time} for {e_dmg} damage")

        actions = []  # list of (card_id, ability, times)
        times_used = set()
        while True:
            cmd = input("Action (<card>-<option> | rest | done): ").strip()
            if cmd == "done":
                break
            if cmd == "rest":
                if actions:
                    print("Cannot rest after selecting other actions")
                    continue
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

        bonus_heavy = False
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
                    bonus_heavy = True
                    print("Hero parries! Next heavy attack will deal double damage")
                else:
                    dmg = max(act.damage - hero.armor, 0)
                    enemy_damage += dmg
                    print(f"Hero takes {dmg} damage (after armor)")

            # Resolve hero attacks after defenses
            for act in hero_attacks:
                dmg = act.damage
                if act.kind == "strong":
                    if bonus_heavy:
                        dmg *= 2
                        bonus_heavy = False
                        print("Hero's strong attack deals double damage!")
                    hero_damage += dmg
                    print(f"Hero strong attacks for {dmg} damage")
                else:
                    hero_damage += dmg
                    print(f"Hero quick attacks for {dmg} damage")

            # Apply damage simultaneously
            enemy.hp -= hero_damage
            hero.hp -= enemy_damage

            # Stop round early if someone dies
            if hero.hp <= 0 or enemy.hp <= 0:
                break

        bonus_heavy = False

        # Refill the hero's hand to four cards
        hero.draw(max(0, 4 - len(hero.hand)))
        enemy.advance()

        if enemy.hp <= 0:
            print(f"Enemy {enemy.name} defeated!")
            hero.draw(max(0, 4 - len(hero.hand)))
            enemy = choose_enemy()
            print(f"A new {enemy.name} appears!")

    print("Hero has fallen. Game over.")


if __name__ == "__main__":
    main()
