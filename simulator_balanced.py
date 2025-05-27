import simulator
from copy import deepcopy
from typing import List, Dict

# HP modifiers as percent changes
BASIC_HP_MOD: Dict[str, float] = {
    "Shadow Spinner": 0.0,
    "Void Soldier": 0.0,
    "Priest of Oblivion": 0.0,
    "Corrupted Dryad": 0.0,
    "Dark Minotaur": 0.0,
    "Dark Wizard": 0.0,
    "Shadow Banshee": 0.0,
    "Corrupted Angel": 0.0,
    "Void Gryphon": 0.0,
    "Void Treant": 0.0,
}

ELITE_HP_MOD: Dict[str, float] = {
    "Shadow Spinner": -0.33,
    "Void Soldier": 0.25,
    "Priest of Oblivion": -0.25,
    "Corrupted Dryad": 0.25,
    "Dark Minotaur": 0.33,
    "Dark Wizard": 1.00,
    "Shadow Banshee": 0.20,
    "Corrupted Angel": 0.29,
    "Void Gryphon": 0.33,
    "Void Treant": 0.38,
}

# Damage multipliers from proposal
BASIC_DMG_FACTOR: Dict[str, float] = {
    "Shadow Spinner": 1.67,
    "Void Soldier": 1.67,
    "Priest of Oblivion": 3.0,
    "Corrupted Dryad": 1.67,
    "Dark Minotaur": 1.0,
    "Dark Wizard": 1.0,
    "Shadow Banshee": 3.0,
    "Corrupted Angel": 0.67,
    "Void Gryphon": 0.67,
    "Void Treant": 0.67,
}

ELITE_DMG_FACTOR: Dict[str, float] = {
    "Shadow Spinner": 3.0,
    "Void Soldier": 3.0,
    "Priest of Oblivion": 5.0,
    "Corrupted Dryad": 3.0,
    "Dark Minotaur": 2.0,
    "Dark Wizard": 2.0,
    "Shadow Banshee": 5.0,
    "Corrupted Angel": 1.0,
    "Void Gryphon": 1.0,
    "Void Treant": 1.0,
}


def _scale_damage(mult: float) -> float:
    """Return multiplier applying half of any increase (>1)."""
    if mult > 1:
        return 1 + (mult - 1) / 2
    return mult


def _scale_groups() -> (List[simulator.EnemyGroup], List[simulator.EnemyGroup]):
    new_basic: List[simulator.EnemyGroup] = []
    for g in simulator.BASIC_GROUPS:
        m = deepcopy(g.monster)
        hp_mod = BASIC_HP_MOD.get(m.name, 0.0)
        m.hp = int(round(m.hp * (1 + hp_mod)))
        dmg_mult = _scale_damage(BASIC_DMG_FACTOR.get(m.name, 1.0))
        m.action_table = [
            {**entry, "damage": int(round(entry["damage"] * dmg_mult))}
            for entry in m.action_table
        ]
        new_basic.append(simulator.EnemyGroup(g.count, m))

    new_elite: List[simulator.EnemyGroup] = []
    for g in simulator.ELITE_GROUPS:
        m = deepcopy(g.monster)
        hp_mod = ELITE_HP_MOD.get(m.name, 0.0)
        m.hp = int(round(m.hp * (1 + hp_mod)))
        dmg_mult = _scale_damage(ELITE_DMG_FACTOR.get(m.name, 1.0))
        m.action_table = [
            {**entry, "damage": int(round(entry["damage"] * dmg_mult))}
            for entry in m.action_table
        ]
        new_elite.append(simulator.EnemyGroup(g.count, m))

    return new_basic, new_elite


def run_trials(hero_name: str, n: int) -> None:
    """Run ``simulator.run_trials`` with balanced enemy stats."""
    orig_basic, orig_elite = simulator.BASIC_GROUPS, simulator.ELITE_GROUPS
    simulator.BASIC_GROUPS, simulator.ELITE_GROUPS = _scale_groups()
    try:
        simulator.run_trials(hero_name, n)
    finally:
        simulator.BASIC_GROUPS, simulator.ELITE_GROUPS = orig_basic, orig_elite


def main() -> None:
    print("=== Merlin Trials (Balanced) ===")
    run_trials("Merlin", 20000)
    print("=== Hercules Trials (Balanced) ===")
    run_trials("Hercules", 20000)


if __name__ == "__main__":
    main()
