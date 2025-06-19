import random
from dataclasses import dataclass


@dataclass
class Action:
    time: int
    actor: str  # 'hero' or 'enemy'
    kind: str
    damage: int = 0


class Deck:
    """Deck of Time cards 1..7 with discard and reshuffle."""

    def __init__(self):
        self.cards = list(range(1, 8))
        random.shuffle(self.cards)
        self.discard_pile = []

    def reshuffle(self):
        if self.discard_pile:
            self.cards = self.discard_pile
            self.discard_pile = []
            random.shuffle(self.cards)

    def draw(self, n):
        result = []
        for _ in range(n):
            if not self.cards:
                self.reshuffle()
                if not self.cards:
                    break
            result.append(self.cards.pop())
        return result

    def discard(self, cards):
        self.discard_pile.extend(cards)


class Hero:
    """Hero with HP, armor and a hand of Time cards."""

    def __init__(self, deck: Deck):
        self.hp = 15
        self.deck = deck
        self.hand = deck.draw(7)
        self.armor = 1

    def draw(self, n):
        self.hand.extend(self.deck.draw(n))

    def discard_used(self, cards):
        for c in cards:
            if c in self.hand:
                self.hand.remove(c)
        self.deck.discard(cards)


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
        attacks = [(2, 3), (4, 4), (6, 5)]
        super().__init__("Samurai", 10, attacks)


class EnemyOni(Enemy):
    def __init__(self):
        attacks = [(3, 4), (5, 6), (7, 6)]
        super().__init__("Oni", 12, attacks)


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

        used = []
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

            if not all(t in hero.hand and t not in used for t in times):
                print("You don't have those cards or they're already used")
                continue
            used.extend(times)
            actions.append((kind, times))

        pending = []
        for kind, times in actions:
            if kind == "fast":
                pending.append(Action(times[0], "hero", "fast", 1))
            elif kind == "strong":
                pending.append(Action(times[-1], "hero", "strong", 4))
            elif kind == "roll":
                pending.append(Action(times[-2], "hero", "roll"))
                pending.append(Action(times[-1], "hero", "roll"))
            elif kind == "parry":
                pending.append(Action(times[0], "hero", "parry"))
        pending.append(Action(e_time, "enemy", "attack", e_dmg))
        pending.sort(key=lambda a: (a.time, 0 if (a.actor == "hero" and a.kind in {"roll", "parry"}) else 1))

        roll_times = set()
        parry_times = set()
        double_next = False
        for act in pending:
            if act.actor == "hero":
                if act.kind == "fast":
                    dmg = act.damage
                    if double_next:
                        dmg *= 2
                        double_next = False
                        print("Hero's attack deals double damage!")
                    enemy.hp -= dmg
                    print(f"Hero fast attacks for {dmg} damage")
                elif act.kind == "strong":
                    dmg = act.damage
                    if double_next:
                        dmg *= 2
                        double_next = False
                        print("Hero's attack deals double damage!")
                    enemy.hp -= dmg
                    print(f"Hero strong attacks for {dmg} damage")
                elif act.kind == "roll":
                    roll_times.add(act.time)
                    print(f"Hero prepares to roll at {act.time}")
                elif act.kind == "parry":
                    parry_times.add(act.time)
                    print(f"Hero prepares to parry at {act.time}")
            else:  # enemy action
                if enemy.hp <= 0:
                    continue
                print(f"Enemy attacks for {act.damage} damage at {act.time}")
                if act.time in roll_times:
                    print("Hero rolls and avoids the attack")
                elif act.time in parry_times:
                    double_next = True
                    print("Hero parries! Next attack will deal double damage")
                else:
                    dmg = max(act.damage - hero.armor, 0)
                    hero.hp -= dmg
                    print(f"Hero takes {dmg} damage (after armor)")

        double_next = False

        hero.discard_used(used)
        hero.draw(len(used))
        enemy.advance()

        if enemy.hp <= 0:
            print(f"Enemy {enemy.name} defeated!")
            hero.draw(3)
            enemy = choose_enemy()
            print(f"A new {enemy.name} appears!")

    print("Hero has fallen. Game over.")


if __name__ == "__main__":
    main()
