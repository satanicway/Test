#!/usr/bin/env python3
"""Mass gauntlet simulator."""

from __future__ import annotations

from typing import Dict

import sim

# use sim.RNG for determinism across modules
RNG = sim.RNG

# helper to choose waves -------------------------------------------------------

def _select_waves() -> list[tuple[str, int]]:
    """Pick 4 normal and 4 elite groups at random."""
    normals = [w for w in sim.ENEMY_WAVES if not w[0].startswith("Elite")]
    elites = [w for w in sim.ENEMY_WAVES if w[0].startswith("Elite")]
    waves = RNG.sample(normals, 4) + RNG.sample(elites, 4)
    RNG.shuffle(waves)
    return waves

# single run ------------------------------------------------------------------

def run_gauntlet(hero: sim.Hero) -> bool:
    """Run one gauntlet for ``hero`` using random waves and upgrade schedule."""
    original_waves = sim.ENEMY_WAVES[:]
    sim.ENEMY_WAVES = _select_waves()

    # track upgrade calls to add bonuses after 3rd and 6th fights
    orig_gain = hero.gain_upgrades
    counter = {"idx": 0}

    def patched(n: int = 1) -> None:
        counter["idx"] += 1
        extra = 1 if counter["idx"] in (3, 6) else 0
        orig_gain(n + extra)

    hero.gain_upgrades = patched
    try:
        return sim.fight_one(hero)
    finally:
        hero.gain_upgrades = orig_gain
        sim.ENEMY_WAVES = original_waves

# bulk stats ------------------------------------------------------------------

def run_stats(num_runs: int = 50000) -> Dict[str, int]:
    """Run ``num_runs`` gauntlets for each hero and return win counts."""
    results: Dict[str, int] = {h.name: 0 for h in sim.HEROES}
    sim.AUTO_MODE = True
    try:
        for proto in sim.HEROES:
            for _ in range(num_runs):
                hero = sim.Hero(proto.name, proto.max_hp, proto.base_cards[:],
                                proto._orig_pool[:])
                if run_gauntlet(hero):
                    results[proto.name] += 1
    finally:
        sim.AUTO_MODE = False
    return results

if __name__ == "__main__":
    wins = run_stats()
    for name, count in wins.items():
        print(f"{name}: {count}")
