# Experimental parameter sweeper for the board game simulator

from __future__ import annotations

import itertools
from typing import Iterable, Callable, Optional, Any
import time
import random

import sim
import stats_runner


def run_experiments(
    hp_values: Iterable[int],
    damage_multipliers: Iterable[float],
    armor_rules: Optional[Iterable[Callable[[bool], Any]]] = None,
    card_modifiers: Optional[Iterable[Callable[[bool], Any]]] = None,
    stat_modifiers: Optional[Iterable[dict[str, dict[str, float]]]] = None,
    min_damage_values: Iterable[bool] | None = None,
    *,
    num_runs: int = 100,
    progress: bool = False,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
) -> list[dict[str, Any]]:
    """Execute statistics across a range of tuning parameters.

    Parameters
    ----------
    hp_values:
        Iterable of HP values to assign to all heroes.
    damage_multipliers:
        Iterable of multipliers applied to every enemy damage band.
    armor_rules:
        Optional sequence of callables receiving ``True`` to apply and
        ``False`` to revert armor related tweaks.  Built-in helpers include
        :func:`sim.band_reduction_rule`, :func:`sim.total_min_damage_rule`,
        :func:`sim.per_enemy_min_damage_rule`,
        :func:`sim.half_after_first_soak_rule`,
        :func:`sim.armor_cap_rule` and :func:`sim.armor_decay_rule`.
    card_modifiers:
        Optional sequence of callables receiving ``True`` to apply and
        ``False`` to revert card related tweaks.
    stat_modifiers:
        Optional sequence of dictionaries mapping card names to modifier
        information. Each dictionary maps a card name to
        ``{"damage": <mult>, "armor": <mult>}``.
    min_damage_values:
        Iterable of booleans toggling the minimum damage rule.
    num_runs:
        Number of gauntlet simulations per experiment.

    Returns
    -------
    list of dict
        Each dictionary contains the parameters and aggregated results for that
        experiment.
    """

    armor_rules = list(armor_rules) if armor_rules is not None else [None]
    card_modifiers = list(card_modifiers) if card_modifiers is not None else [None]
    stat_modifiers = list(stat_modifiers) if stat_modifiers is not None else [None]
    min_damage_values = list(min_damage_values) if min_damage_values is not None else [False]

    # Preserve original values so they can be restored between runs
    orig_hp = {h.name: h.max_hp for h in sim.HEROES}
    orig_bands = {name: enemy.damage_band[:] for name, enemy in sim.ENEMIES.items()}
    orig_mods = {h.name: h.card_modifiers for h in sim.HEROES}

    results: list[dict[str, Any]] = []

    for hp, mult, armor_fn, card_fn, stat_map, min_dmg in itertools.product(
        hp_values,
        damage_multipliers,
        armor_rules,
        card_modifiers,
        stat_modifiers,
        min_damage_values,
    ):
        # Apply hero HP
        for hero in sim.HEROES:
            hero.max_hp = hp

        # Apply damage multiplier
        for name, enemy in sim.ENEMIES.items():
            base = orig_bands[name]
            enemy.damage_band = [max(0, int(v * mult)) for v in base]

        if armor_fn:
            armor_fn(True)
        if card_fn:
            card_fn(True)
        if stat_map:
            for hero in sim.HEROES:
                hero.card_modifiers = stat_map

        wins, _damage, hp_avgs, hp_thresh = stats_runner.run_stats_with_damage(
            num_runs=num_runs,
            progress=progress,
            timeout=timeout,
            max_retries=max_retries,
            max_exchanges=max_exchanges,
            wave_timeout=wave_timeout,
            max_total_exchanges=max_total_exchanges,
            min_damage=min_dmg,
        )

        result = {
            "hp": hp,
            "mult": mult,
            "armor_rule": getattr(armor_fn, "__name__", None),
            "card_modifier": getattr(card_fn, "__name__", None),
            "stat_mods": stat_map,
            "min_damage": min_dmg,
            "wins": wins,
            "hp_avgs": hp_avgs,
            "hp_thresh": hp_thresh,
        }
        results.append(result)

        # Revert modifications
        if armor_fn:
            armor_fn(False)
        if card_fn:
            card_fn(False)
        if stat_map:
            for hero in sim.HEROES:
                hero.card_modifiers = orig_mods[hero.name]

        for hero in sim.HEROES:
            hero.max_hp = orig_hp[hero.name]
        for name, vals in orig_bands.items():
            sim.ENEMIES[name].damage_band = vals[:]

    # Print summary sorted by overall win rate
    def win_rate(entry: dict[str, Any]) -> float:
        total = sum(entry["wins"].values())
        return total / (len(sim.HEROES) * num_runs)

    for entry in sorted(results, key=win_rate, reverse=True):
        rate = win_rate(entry) * 100
        print(
            f"HP={entry['hp']} mult={entry['mult']} armor={entry['armor_rule']} "
            f"card={entry['card_modifier']} min_dmg={entry['min_damage']} win={rate:.1f}%" 
            f"mods={entry['stat_mods']}"
        )

    return results


def auto_optimize(
    hp_values: Iterable[int],
    damage_multipliers: Iterable[float],
    min_damage_values: Iterable[bool] | None = None,
    *,
    num_runs: int = 100,
    progress: bool = False,
    timeout: float = 60.0,
    max_retries: int = 5,
    max_exchanges: int | None = 1000,
    wave_timeout: float | None = 10.0,
    max_total_exchanges: int | None = None,
    time_limit: float = 4 * 60 * 60,
    print_every: int = 10,
) -> Optional[dict[str, Any]]:
    """Search parameter space for a balanced configuration.

    The search iterates through ``hp_values`` and ``damage_multipliers``
    combinations until ``time_limit`` seconds have elapsed. A dictionary
    describing the best configuration is returned or ``None`` if no
    acceptable parameters were found. Progress messages are printed every
    ``print_every`` iterations when ``progress`` is ``True``.
    """

    min_damage_values = list(min_damage_values) if min_damage_values is not None else [False]

    combos = list(itertools.product(hp_values, damage_multipliers, min_damage_values))
    random.shuffle(combos)

    orig_hp = {h.name: h.max_hp for h in sim.HEROES}
    orig_bands = {name: e.damage_band[:] for name, e in sim.ENEMIES.items()}

    best: Optional[dict[str, Any]] = None
    best_score: float | None = None
    start = time.time()
    count = 0

    for hp, mult, min_dmg in combos:
        if time.time() - start >= time_limit:
            break

        for hero in sim.HEROES:
            hero.max_hp = hp
        for name, enemy in sim.ENEMIES.items():
            base = orig_bands[name]
            enemy.damage_band = [max(0, int(v * mult)) for v in base]

        wins, _damage, hp_avgs, hp_thresh = stats_runner.run_stats_with_damage(
            num_runs=num_runs,
            progress=False,
            timeout=timeout,
            max_retries=max_retries,
            max_exchanges=max_exchanges,
            wave_timeout=wave_timeout,
            max_total_exchanges=max_total_exchanges,
            min_damage=min_dmg,
        )

        for hero in sim.HEROES:
            hero.max_hp = orig_hp[hero.name]
        for name, vals in orig_bands.items():
            sim.ENEMIES[name].damage_band = vals[:]

        win_rates = {h: wins[h] / num_runs for h in wins}
        over_rates = {h: hp_thresh[h] / num_runs for h in hp_thresh}
        overall_over = sum(hp_thresh.values()) / (num_runs * len(sim.HEROES))

        good_rates = all(0.40 <= r <= 0.60 for r in win_rates.values())
        good_hp = all(v <= 0.20 for v in over_rates.values()) and overall_over <= 0.20

        if good_rates and good_hp:
            score = sum((r - 0.5) ** 2 for r in win_rates.values())
            if best_score is None or score < best_score:
                best_score = score
                best = {
                    "hp": hp,
                    "mult": mult,
                    "min_damage": min_dmg,
                    "wins": wins,
                    "hp_avgs": hp_avgs,
                    "hp_thresh": hp_thresh,
                }

        count += 1
        if progress and count % print_every == 0:
            elapsed = int(time.time() - start)
            print(f"Tried {count}/{len(combos)} configs - elapsed {elapsed}s")

    if progress:
        if best is not None:
            print("Best configuration found:")
            print(best)
        else:
            print("No configuration satisfied constraints")

    return best


if __name__ == "__main__":
    # Example usage with trivial ranges
    run_experiments(range(20, 26, 2), [1.0, 1.2])
