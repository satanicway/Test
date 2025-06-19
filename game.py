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
    """Generate the seven default cards with rotating times."""
    cards: Dict[int, Card] = {}
    for i in range(1, 8):
        strong = [((i + j - 1) % 7) + 1 for j in range(3)]
        quick = [i]
        dodge = strong.copy()
        parry = [strong[-1]]
        cards[i] = Card(i, {
            "strong": strong,
            "quick": quick,
            "dodge": dodge,
            "parry": parry,
        })
    return cards


CARDS: Dict[int, Card] = _generate_cards()


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
    parts = cmd.split()
    if not parts:
        return None
    kind = parts[0]
    try:
        times = list(map(int, parts[1:]))
    except ValueError:
        return None
    return kind, times


def main():
    deck = Deck()
    hero = Hero(deck)
    enemy = choose_enemy()

    while hero.hp > 0:
        print(f"\nHero HP: {hero.hp}\tEnemy {enemy.name} HP: {enemy.hp}")
        print("Hand:", " ".join(map(str, sorted(hero.hand))))
        e_time, e_dmg = enemy.next_attack()
        print(f"Enemy will attack at time {e_time} for {e_dmg} damage")

        actions = []
        while True:
            cmd = input("Action (fast x | strong x y z | roll x y z | parry x | done): ").strip()
            if cmd == "done":
                break
            parsed = parse_action(cmd)
            if not parsed:
                print("Invalid command")
                continue
            kind, times = parsed
            if kind == "strong":
                if len(times) != 3:
                    print("Strong attack requires exactly three time cards")
                    continue
                times.sort()
                if any(times[i] + 1 != times[i+1] for i in range(2)):
                    print("Strong attack requires three consecutive times")
                    continue
            elif kind == "roll":
                if len(times) != 3:
                    print("Roll requires exactly three time cards")
                    continue
                times.sort()
                if any(times[i] + 1 != times[i+1] for i in range(2)):
                    print("Roll requires three consecutive times")
                    continue
            elif kind in {"fast", "parry"}:
                if len(times) != 1:
                    print("This action uses exactly one time card")
                    continue
            else:
                print("Unknown action")
                continue

            if not all(t in hero.hand for t in times):
                print("You don't have those cards")
                continue
            for t in times:
                hero.use_card(t)
            actions.append((kind, times))

        roll_times = set()
        parry_times = set()
        pending = []
        for kind, times in actions:
            if kind == "fast":
                pending.append(Action(times[0], "hero", "fast", 1, times=times))
            elif kind == "strong":
                pending.append(Action(times[-1], "hero", "strong", 4, times=times))
            elif kind == "roll":
                roll_times.update(times[-2:])
                pending.append(Action(times[-1], "hero", "roll", times=times))
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

            # Resolve hero defensive moves first
            for act in group:
                if act.actor == "hero" and act.kind == "roll":
                    print(f"Hero prepares to roll ending at {act.time}")
                elif act.actor == "hero" and act.kind == "parry":
                    print(f"Hero prepares to parry at {act.time}")

            hero_damage = 0
            enemy_damage = 0

            # Collect hero attacks
            for act in group:
                if act.actor == "hero" and act.kind in {"fast", "strong"}:
                    dmg = act.damage
                    if double_next:
                        dmg *= 2
                        double_next = False
                        print("Hero's attack deals double damage!")
                    hero_damage += dmg
                    if act.kind == "fast":
                        print(f"Hero fast attacks for {dmg} damage")
                    else:
                        print(f"Hero strong attacks for {dmg} damage")

            # Collect enemy attacks
            for act in group:
                if act.actor == "enemy":
                    print(f"Enemy attacks for {act.damage} damage at {act.time}")
                    if act.time in roll_times:
                        print("Hero rolls and avoids the attack")
                    elif act.time in parry_times:
                        double_next = True
                        print("Hero parries! Next attack will deal double damage")
                    else:
                        dmg = max(act.damage - hero.armor, 0)
                        enemy_damage += dmg
                        print(f"Hero takes {dmg} damage (after armor)")

            # Apply damage simultaneously
            enemy.hp -= hero_damage
            hero.hp -= enemy_damage

            # Stop round early if someone dies
            if hero.hp <= 0 or enemy.hp <= 0:
                break

        double_next = False

        # Draw two new cards at the end of the round
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
