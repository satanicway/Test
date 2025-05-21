#!/usr/bin/env python3
"""Mass gauntlet simulator."""

from __future__ import annotations

from typing import Dict
import argparse

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

def run_gauntlet(hero: sim.Hero, hp_log: list[int] | None = None) -> bool:
    """Run one gauntlet for ``hero`` using random waves and upgrade schedule.

    Parameters
    ----------
    hero:
        The hero instance to run through the gauntlet.
    hp_log:
        Optional list that receives the hero's hit points after each fight.
    """
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
        return sim.fight_one(hero, hp_log)
    finally:
        hero.gain_upgrades = orig_gain
        sim.ENEMY_WAVES = original_waves

# bulk stats ------------------------------------------------------------------

def run_stats(num_runs: int = 50000) -> Dict[str, int]:
    """Run ``num_runs`` gauntlets for each hero and return win counts."""
    sim.CARD_CORRELATIONS.clear()
    sim.ENEMY_RUN_COUNTS.clear()
    sim.MONSTER_DAMAGE.clear()
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


def run_stats_with_damage(num_runs: int = 50000) -> tuple[Dict[str, int], dict, dict]:
    """Run gauntlets collecting win counts, damage and HP progression.

    When aggregating HP values, uncompleted waves are counted as 0 HP.
    """
    from collections import defaultdict

    results: Dict[str, int] = {h.name: 0 for h in sim.HEROES}
    damage: dict = defaultdict(int)
    hp_totals: dict[str, list[int]] = {h.name: [0]*8 for h in sim.HEROES}
    hp_counts: dict[str, list[int]] = {h.name: [0]*8 for h in sim.HEROES}

    sim.CARD_CORRELATIONS.clear()
    sim.ENEMY_RUN_COUNTS.clear()
    sim.MONSTER_DAMAGE.clear()

    sim.AUTO_MODE = True
    try:
        for proto in sim.HEROES:
            for _ in range(num_runs):
                hero = sim.Hero(proto.name, proto.max_hp, proto.base_cards[:],
                                proto._orig_pool[:])
                hp_log: list[int] = []
                if run_gauntlet(hero, hp_log):
                    results[proto.name] += 1
                for idx in range(8):
                    hp = hp_log[idx] if idx < len(hp_log) else 0
                    hp_totals[proto.name][idx] += hp
                    hp_counts[proto.name][idx] += 1
                for key, val in sim.get_monster_damage().items():
                    damage[key] += val
    finally:
        sim.AUTO_MODE = False
    sim.MONSTER_DAMAGE.clear()

    hp_avgs: dict[str, list[float]] = {}
    for proto in sim.HEROES:
        totals = hp_totals[proto.name]
        counts = hp_counts[proto.name]
        percents: list[float] = []
        for idx in range(8):
            if counts[idx]:
                pct = totals[idx] / (counts[idx] * proto.max_hp) * 100
            else:
                pct = 0.0
            percents.append(pct)
        hp_avgs[proto.name] = percents

    return results, damage, hp_avgs


def format_report(wins: Dict[str, int], card_data: dict, damage: dict,
                  enemy_data: dict, num_runs: int, hp_avgs: dict) -> str:
    """Create a human readable report from aggregated statistics."""
    from collections import defaultdict

    lines: list[str] = []

    lines.append("=== Hero Win Rates ===")
    for hero in sorted(wins):
        rate = (wins[hero] / num_runs) * 100 if num_runs else 0.0
        lines.append(f"{hero}: {rate:.1f}% ({wins[hero]}/{num_runs})")
        hp_vals = hp_avgs.get(hero, [0.0] * 8)
        hp_str = "/".join(f"{v:.0f}%" for v in hp_vals)
        lines.append(f"  HP after fights: {hp_str}")

    lines.append("\n=== Card Correlations ===")
    for hero in sorted(card_data):
        lines.append(f"{hero}:")
        for rarity in ("base", "common", "uncommon", "rare"):
            cards = card_data[hero].get(rarity, {})
            if not cards:
                continue
            lines.append(f"  {rarity}:")
            for card, counts in sorted(cards.items()):
                total = counts["win"] + counts["loss"]
                if total == 0:
                    continue
                pct = counts["win"] / total * 100
                lines.append(
                    f"    {card}: {pct:.1f}% ({counts['win']}/{total})")

    lines.append("\n=== Damage Taken ===")
    dmg_map: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (hero, enemy), val in damage.items():
        dmg_map[hero].append((enemy, val))
    for hero in sorted(dmg_map):
        lines.append(f"{hero}:")
        for enemy, val in sorted(dmg_map[hero]):
            lines.append(f"  {enemy}: {val}")

    lines.append("\n=== Enemy Appearance Outcomes ===")
    for hero in sorted(enemy_data):
        lines.append(f"{hero}:")
        for enemy in sorted(enemy_data[hero]):
            lines.append(f"  {enemy}:")
            for variant in ("common", "elite"):
                stats = enemy_data[hero][enemy][variant]
                total = stats["win"] + stats["loss"]
                pct = (stats["win"] / total * 100) if total else 0.0
                lines.append(
                    f"    {variant}: {pct:.1f}% win ({stats['win']}/{total})")

    return "\n".join(lines)


def generate_report(num_runs: int = 100) -> str:
    """Run gauntlets and return a formatted statistics report."""
    wins, damage, hp = run_stats_with_damage(num_runs)
    card_data = sim.get_card_correlations()
    enemy_data = sim.get_enemy_run_counts()
    return format_report(wins, card_data, damage, enemy_data, num_runs, hp)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run gauntlet statistics")
    parser.add_argument(
        "--report", action="store_true",
        help="Print a formatted report instead of win counts")
    parser.add_argument(
        "--runs", type=int, default=50000,
        help="Number of gauntlet runs to simulate")
    args = parser.parse_args()

    if args.report:
        print(generate_report(num_runs=args.runs))
    else:
        wins = run_stats(num_runs=args.runs)
        for name, count in wins.items():
            print(f"{name}: {count}")
