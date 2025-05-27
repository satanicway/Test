import copy
from typing import List, Dict
import simulator


# Helpers to adjust enemy stats

def scale_table(table: List[Dict[str, int]], factor: float) -> List[Dict[str, int]]:
    """Return a new action table with damage values scaled by ``factor``."""
    new_table: List[Dict[str, int]] = []
    for row in table:
        new_row = row.copy()
        if "damage" in new_row:
            new_row["damage"] = max(0, int(round(new_row["damage"] * factor)))
        new_table.append(new_row)
    return new_table


# Percent changes for basic and elite enemies.
# Each tuple is (hp_factor, damage_factor)
BASIC_MODS: Dict[str, tuple] = {
    "Shadow Spinner": (3.0, 7.8),
    "Void Soldier": (1.3, 2.1),
    "Priest of Oblivion": (1.5, 10.6),
    "Corrupted Dryad": (1.3, 1.2),
    "Dark Minotaur": (1.2, 3.4),
    "Dark Wizard": (1.25, 1.6),
    "Shadow Banshee": (1.25, 8.1),
    "Void Gryphon": (1.2, 1.9),
    "Void Treant": (0.85, 0.84),
    "Corrupted Angel": (1.0, 2.73),
}

ELITE_MODS: Dict[str, tuple] = {
    "Shadow Spinner": (1.3, 1.7),
    "Void Soldier": (1.25, 1.7),
    "Priest of Oblivion": (1.25, 3.88),
    "Corrupted Dryad": (1.25, 2.85),
    "Dark Minotaur": (1.0, 5.67),
    "Dark Wizard": (1.33, 6.1),
    "Shadow Banshee": (1.2, 3.67),
    "Void Gryphon": (1.0, 2.57),
    "Void Treant": (0.88, 0.52),
    "Corrupted Angel": (1.0, 1.45),
}


def adjust_groups(groups: List[simulator.EnemyGroup], mods: Dict[str, tuple]) -> List[simulator.EnemyGroup]:
    """Return a copy of ``groups`` with hp and damage modified."""
    new_list: List[simulator.EnemyGroup] = []
    for g in groups:
        hp_factor, dmg_factor = mods.get(g.monster.name, (1.0, 1.0))
        monster = copy.deepcopy(g.monster)
        monster.hp = int(round(monster.hp * hp_factor))
        monster.action_table = scale_table(monster.action_table, dmg_factor)
        new_list.append(simulator.EnemyGroup(g.count, monster))
    return new_list


BASIC_GROUPS_BALANCED = adjust_groups(simulator.BASIC_GROUPS, BASIC_MODS)
ELITE_GROUPS_BALANCED = adjust_groups(simulator.ELITE_GROUPS, ELITE_MODS)


def run_trials(hero_name: str, n: int) -> None:
    """Run ``simulator.run_trials`` with balanced enemy stats."""
    orig_basic = simulator.BASIC_GROUPS
    orig_elite = simulator.ELITE_GROUPS
    simulator.BASIC_GROUPS = BASIC_GROUPS_BALANCED
    simulator.ELITE_GROUPS = ELITE_GROUPS_BALANCED
    try:
        simulator.run_trials(hero_name, n)
    finally:
        simulator.BASIC_GROUPS = orig_basic
        simulator.ELITE_GROUPS = orig_elite


def main() -> None:
    print("=== Merlin Trials (Balanced) ===")
    run_trials("Merlin", 20000)
    print("=== Hercules Trials (Balanced) ===")
    run_trials("Hercules", 20000)


if __name__ == "__main__":
    main()
