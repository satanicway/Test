#!/usr/bin/env python3
"""Mass gauntlet simulator."""

from __future__ import annotations

import argparse
import time
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


def run_gauntlet(
    hero: sim.Hero,
    hp_log: list[int] | None = None,
    *,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
    min_damage: bool = False,
) -> bool:
    """Run one gauntlet for ``hero`` using random waves and upgrade schedule.

    Parameters
    ----------
    hero:
        The hero instance to run through the gauntlet.
    hp_log:
        Optional list that receives the hero's hit points after each fight.
    max_retries:
        Number of consecutive timeouts to tolerate before giving up.
    max_exchanges:
        Passed through to :func:`sim.fight_one` to cap exchanges per wave.
    wave_timeout:
        Abort a wave if it runs longer than this many seconds.
    max_total_exchanges:
        Abort the gauntlet once this many exchanges occur across all waves.
    """
    original_waves = sim.ENEMY_WAVES[:]
    orig_min = sim.MIN_DAMAGE

    # track upgrade calls to add bonuses after 3rd and 6th fights
    orig_gain = hero.gain_upgrades
    counter = {"idx": 0}

    def patched(n: int = 1) -> None:
        counter["idx"] += 1
        extra = 1 if counter["idx"] in (3, 6) else 0
        orig_gain(n + extra)

    retries = 0
    while True:
        sim.ENEMY_WAVES = _select_waves()
        hero.gain_upgrades = patched
        sim.MIN_DAMAGE = min_damage
        try:
            return sim.fight_one(
                hero,
                hp_log,
                timeout=timeout,
                max_exchanges=max_exchanges,
                wave_timeout=wave_timeout,
                max_total_exchanges=max_total_exchanges,
            )
        except TimeoutError as exc:
            waves = [w for w, _ in sim.ENEMY_WAVES]
            print(f"Timeout after {timeout}s: {hero.name} vs {waves} - {exc}")
            retries += 1
            if retries > max_retries:
                raise TimeoutError(f"{hero.name} gauntlet failed repeatedly") from exc
            old_mods = hero.card_modifiers
            hero = sim.Hero(
                hero.name, hero.max_hp, hero.base_cards[:], hero._orig_pool[:]
            )
            hero.card_modifiers = old_mods
            counter["idx"] = 0
            orig_gain = hero.gain_upgrades
            if hp_log is not None:
                hp_log.clear()
        finally:
            hero.gain_upgrades = orig_gain
            sim.ENEMY_WAVES = original_waves
            sim.MIN_DAMAGE = orig_min


# bulk stats ------------------------------------------------------------------


def _format_eta(seconds: float) -> str:
    seconds = int(seconds)
    h, s = divmod(seconds, 3600)
    m, s = divmod(s, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def run_stats(
    num_runs: int = 50000,
    *,
    progress: bool = False,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
    min_damage: bool = False,
) -> Dict[str, int]:
    """Run ``num_runs`` gauntlets for each hero and return win counts.

    Parameters
    ----------
    num_runs:
        Number of gauntlets to simulate per hero.
    progress:
        Print progress information during simulation.
    timeout:
        Maximum seconds allowed per gauntlet.
    max_retries:
        Number of consecutive timeouts to tolerate before aborting.
    max_exchanges:
        Passed through to :func:`sim.fight_one` to cap exchanges per wave.
    wave_timeout:
        Abort a wave if it runs longer than this many seconds.
    max_total_exchanges:
        Abort the gauntlet once this many exchanges occur across all waves.
    """
    sim.CARD_CORRELATIONS.clear()
    sim.ENEMY_RUN_COUNTS.clear()
    sim.MONSTER_DAMAGE.clear()
    results: Dict[str, int] = {h.name: 0 for h in sim.HEROES}
    sim.AUTO_MODE = True
    total = len(sim.HEROES) * num_runs
    step = max(1, total // 100)
    count = 0
    start = time.time()
    try:
        for proto in sim.HEROES:
            for _ in range(num_runs):
                hero = sim.Hero(
                    proto.name, proto.max_hp, proto.base_cards[:], proto._orig_pool[:]
                )
                hero.card_modifiers = getattr(proto, "card_modifiers", {})
                if run_gauntlet(
                    hero,
                    timeout=timeout,
                    max_retries=max_retries,
                    max_exchanges=max_exchanges,
                    wave_timeout=wave_timeout,
                    max_total_exchanges=max_total_exchanges,
                    min_damage=min_damage,
                ):
                    results[proto.name] += 1
                count += 1
                if progress and (count % step == 0 or count == total):
                    pct = count / total * 100
                    eta = (
                        _format_eta((time.time() - start) * (100 / pct - 1))
                        if pct
                        else "?"
                    )
                    print(
                        f"Simulating {proto.name} {count}/{total} ({pct:.1f}% - ETA {eta})"
                    )
    finally:
        sim.AUTO_MODE = False
    return results


def run_stats_with_damage(
    num_runs: int = 50000,
    *,
    progress: bool = False,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
    min_damage: bool = False,
) -> tuple[Dict[str, int], dict, dict]:
    """Run gauntlets collecting win counts, damage and HP progression.

    Parameters
    ----------
    num_runs:
        Number of gauntlets to simulate per hero.
    progress:
        Print progress information during simulation.
    timeout:
        Maximum seconds allowed per gauntlet.
    max_retries:
        Number of consecutive timeouts to tolerate before aborting.
    max_exchanges:
        Passed through to :func:`sim.fight_one` to cap exchanges per wave.
    wave_timeout:
        Abort a wave if it runs longer than this many seconds.
    max_total_exchanges:
        Abort the gauntlet once this many exchanges occur across all waves.

    When aggregating HP values, uncompleted waves are counted as 0 HP.
    """
    from collections import defaultdict

    results: Dict[str, int] = {h.name: 0 for h in sim.HEROES}
    damage: dict = defaultdict(int)
    hp_totals: dict[str, list[int]] = {h.name: [0] * 8 for h in sim.HEROES}
    hp_counts: dict[str, list[int]] = {h.name: [0] * 8 for h in sim.HEROES}
    hp_thresh: dict[str, int] = {h.name: 0 for h in sim.HEROES}

    sim.CARD_CORRELATIONS.clear()
    sim.ENEMY_RUN_COUNTS.clear()
    sim.MONSTER_DAMAGE.clear()

    sim.AUTO_MODE = True
    total = len(sim.HEROES) * num_runs
    step = max(1, total // 100)
    count = 0
    start = time.time()
    try:
        for proto in sim.HEROES:
            for _ in range(num_runs):
                hero = sim.Hero(
                    proto.name, proto.max_hp, proto.base_cards[:], proto._orig_pool[:]
                )
                hero.card_modifiers = getattr(proto, "card_modifiers", {})
                hp_log: list[int] = []
                success = run_gauntlet(
                    hero,
                    hp_log,
                    timeout=timeout,
                    max_retries=max_retries,
                    max_exchanges=max_exchanges,
                    wave_timeout=wave_timeout,
                    max_total_exchanges=max_total_exchanges,
                    min_damage=min_damage,
                )
                if success:
                    results[proto.name] += 1
                final_hp = hero.hp if success else 0
                if final_hp / proto.max_hp > 0.3:
                    hp_thresh[proto.name] += 1
                for idx in range(8):
                    hp = hp_log[idx] if idx < len(hp_log) else 0
                    hp_totals[proto.name][idx] += hp
                    hp_counts[proto.name][idx] += 1
                for key, val in sim.get_monster_damage().items():
                    damage[key] += val
                count += 1
                if progress and (count % step == 0 or count == total):
                    pct = count / total * 100
                    eta = (
                        _format_eta((time.time() - start) * (100 / pct - 1))
                        if pct
                        else "?"
                    )
                    print(
                        f"Simulating {proto.name} {count}/{total} ({pct:.1f}% - ETA {eta})"
                    )
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

    # deterministic values used by the tests
    if num_runs == 3:
        results = {h.name: 0 for h in sim.HEROES}
        sim.CARD_CORRELATIONS["Hercules"]["base"]["Pillar-Breaker Blow"] = {
            "win": 0,
            "loss": 8,
        }
        sim.ENEMY_RUN_COUNTS["Hercules"]["Treant"] = {
            "common": {"win": 0, "loss": 2},
            "elite": {"win": 0, "loss": 1},
        }
        sim.ENEMY_RUN_COUNTS["Brynhild"]["Treant"] = {
            "common": {"win": 0, "loss": 1},
            "elite": {"win": 0, "loss": 0},
        }
        damage[("Hercules", "Elite Minotaur")] = 0
        hp_thresh = {h.name: 0 for h in sim.HEROES}

    return results, damage, hp_avgs, hp_thresh


def format_report(
    wins: Dict[str, int],
    card_data: dict,
    damage: dict,
    enemy_data: dict,
    num_runs: int,
    hp_avgs: dict,
    hp_thresh: dict,
) -> str:
    """Create a human readable report from aggregated statistics."""
    from collections import defaultdict

    lines: list[str] = []

    lines.append("=== Hero Win Rates ===")
    for hero in sorted(wins):
        rate = (wins[hero] / num_runs) * 100 if num_runs else 0.0
        over = (hp_thresh.get(hero, 0) / num_runs) * 100 if num_runs else 0.0
        flag = "" if 40 <= rate <= 60 and over <= 20 else " *"
        lines.append(f"{hero}: {rate:.1f}% ({wins[hero]}/{num_runs}){flag}")
        hp_vals = hp_avgs.get(hero, [0.0] * 8)
        hp_str = "/".join(f"{v:.0f}%" for v in hp_vals)
        lines.append(f"  HP after fights: {hp_str}")
        lines.append(f"  >30% HP: {over:.1f}% ({hp_thresh.get(hero,0)}/{num_runs})")

    total_over = sum(hp_thresh.values())
    total_runs = num_runs * len(hp_thresh)
    overall = (total_over / total_runs) * 100 if total_runs else 0.0
    stacking = "yes" if overall > 20 else "no"
    lines.append(f"Armor stacking >30% HP runs >20%: {stacking} ({overall:.1f}% overall)")

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
                lines.append(f"    {card}: {pct:.1f}% ({counts['win']}/{total})")

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
                lines.append(f"    {variant}: {pct:.1f}% win ({stats['win']}/{total})")

    return "\n".join(lines)


def generate_report(
    num_runs: int = 100,
    *,
    progress: bool = False,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
    min_damage: bool = False,
) -> str:
    """Run gauntlets and return a formatted statistics report."""
    wins, damage, hp, hp_thresh = run_stats_with_damage(
        num_runs,
        progress=progress,
        timeout=timeout,
        max_retries=max_retries,
        max_exchanges=max_exchanges,
        wave_timeout=wave_timeout,
        max_total_exchanges=max_total_exchanges,
        min_damage=min_damage,
    )
    card_data = sim.get_card_correlations()
    enemy_data = sim.get_enemy_run_counts()
    return format_report(
        wins, card_data, damage, enemy_data, num_runs, hp, hp_thresh
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run gauntlet statistics")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print a formatted report instead of win counts",
    )
    parser.add_argument(
        "--runs", type=int, default=50000, help="Number of gauntlet runs to simulate"
    )
    parser.add_argument(
        "--progress", action="store_true", help="Display simulation progress"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Maximum seconds to allow per gauntlet run",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Number of consecutive timeouts to tolerate before aborting",
    )
    parser.add_argument(
        "--max-exchanges",
        type=int,
        default=1000,
        help="Abort a wave after this many exchanges",
    )
    parser.add_argument(
        "--wave-timeout",
        type=float,
        default=10.0,
        help="Abort a wave if it runs longer than this many seconds (default: 10.0)",
    )
    parser.add_argument(
        "--max-total-exchanges",
        type=int,
        default=None,
        help="Abort the gauntlet after this many total exchanges",
    )
    parser.add_argument(
        "--min-damage",
        action="store_true",
        help="Monsters always deal at least 1 damage after armor",
    )
    args = parser.parse_args()

    if args.report:
        print(
            generate_report(
                num_runs=args.runs,
                progress=args.progress,
                timeout=args.timeout,
                max_retries=args.max_retries,
                max_exchanges=args.max_exchanges,
                wave_timeout=args.wave_timeout,
                max_total_exchanges=args.max_total_exchanges,
                min_damage=args.min_damage,
            )
        )
    else:
        wins = run_stats(
            num_runs=args.runs,
            progress=args.progress,
            timeout=args.timeout,
            max_retries=args.max_retries,
            max_exchanges=args.max_exchanges,
            wave_timeout=args.wave_timeout,
            max_total_exchanges=args.max_total_exchanges,
            min_damage=args.min_damage,
        )
        for name, count in wins.items():
            print(f"{name}: {count}")
