import simulator
from copy import deepcopy

# HP modifiers: percent change (e.g., +10% -> 0.10, -15% -> -0.15)
BASIC_HP_MOD = {
    "Shadow Spinner": 0.10,
    "Void Soldier": 0.0,
    "Priest of Oblivion": -0.15,
    "Corrupted Dryad": 0.10,
    "Dark Minotaur": -0.20,
    "Dark Wizard": 0.0,
    "Shadow Banshee": 0.50,
    "Corrupted Angel": -0.15,
    "Void Gryphon": 0.0,
    "Void Treant": 0.15,
}

ELITE_HP_MOD = {
    "Shadow Spinner": 0.10,
    "Void Soldier": 0.0,
    "Priest of Oblivion": 0.0,
    "Corrupted Dryad": 0.0,
    "Dark Minotaur": -0.25,
    "Dark Wizard": 0.20,
    "Shadow Banshee": -0.10,
    "Corrupted Angel": -0.05,
    "Void Gryphon": 0.05,
    "Void Treant": 0.25,
}

# Damage multipliers from proposal.
BASIC_DMG_FACTOR = {
    "Shadow Spinner": 0.8,
    "Void Soldier": 1.2,
    "Priest of Oblivion": 1.8,
    "Corrupted Dryad": 0.85,
    "Dark Minotaur": 1.6,
    "Dark Wizard": 1.15,
    "Shadow Banshee": 0.55,
    "Corrupted Angel": 1.4,
    "Void Gryphon": 1.1,
    "Void Treant": 0.85,
}

ELITE_DMG_FACTOR = {
    "Shadow Spinner": 1.15,
    "Void Soldier": 1.25,
    "Priest of Oblivion": 1.4,
    "Corrupted Dryad": 1.3,
    "Dark Minotaur": 1.6,
    "Dark Wizard": 0.6,
    "Shadow Banshee": 1.8,
    "Corrupted Angel": 1.2,
    "Void Gryphon": 1.2,
    "Void Treant": 0.6,
}


def _scale_damage(mult: float) -> float:
    """Return multiplier applying half of any increase (>1)."""
    if mult > 1:
        return 1 + (mult - 1) / 2
    return mult


def _scale_groups():
    new_basic = []
    for g in simulator.BASIC_GROUPS:
        m = deepcopy(g.monster)
        hp_mod = BASIC_HP_MOD.get(m.name, 0)
        m.hp = int(round(m.hp * (1 + hp_mod)))
        dmg_mult = _scale_damage(BASIC_DMG_FACTOR.get(m.name, 1.0))
        m.action_table = [
            {**entry, "damage": int(round(entry["damage"] * dmg_mult))}
            for entry in m.action_table
        ]
        new_basic.append(simulator.EnemyGroup(g.count, m))

    new_elite = []
    for g in simulator.ELITE_GROUPS:
        m = deepcopy(g.monster)
        hp_mod = ELITE_HP_MOD.get(m.name, 0)
        m.hp = int(round(m.hp * (1 + hp_mod)))
        dmg_mult = _scale_damage(ELITE_DMG_FACTOR.get(m.name, 1.0))
        m.action_table = [
            {**entry, "damage": int(round(entry["damage"] * dmg_mult))}
            for entry in m.action_table
        ]
        new_elite.append(simulator.EnemyGroup(g.count, m))
    return new_basic, new_elite


def run_trials(hero_name: str, n: int) -> None:
    """Run trials using scaled enemy stats."""
    old_basic, old_elite = simulator.BASIC_GROUPS, simulator.ELITE_GROUPS
    simulator.BASIC_GROUPS, simulator.ELITE_GROUPS = _scale_groups()
    try:
        simulator.run_trials(hero_name, n)
    finally:
        simulator.BASIC_GROUPS, simulator.ELITE_GROUPS = old_basic, old_elite


if __name__ == "__main__":
    run_trials("Merlin", 1)
