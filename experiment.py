# Experimental parameter sweeper for the board game simulator

from __future__ import annotations

import itertools
from typing import Iterable, Callable, Optional, Any

import sim
import stats_runner


def run_experiments(
    hp_values: Iterable[int],
    damage_multipliers: Iterable[float],
    armor_rules: Optional[Iterable[Callable[[bool], Any]]] = None,
    card_modifiers: Optional[Iterable[Callable[[bool], Any]]] = None,
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
        ``False`` to revert armor related tweaks.
    card_modifiers:
        Optional sequence of callables receiving ``True`` to apply and
        ``False`` to revert card related tweaks.
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

    # Preserve original values so they can be restored between runs
    orig_hp = {h.name: h.max_hp for h in sim.HEROES}
    orig_bands = {name: enemy.damage_band[:] for name, enemy in sim.ENEMIES.items()}

    results: list[dict[str, Any]] = []

    for hp, mult, armor_fn, card_fn in itertools.product(
        hp_values, damage_multipliers, armor_rules, card_modifiers
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

        wins, _damage, hp_avgs, _hp_thresh = stats_runner.run_stats_with_damage(
            num_runs=num_runs,
            progress=progress,
            timeout=timeout,
            max_retries=max_retries,
            max_exchanges=max_exchanges,
            wave_timeout=wave_timeout,
            max_total_exchanges=max_total_exchanges,
        )

        result = {
            "hp": hp,
            "mult": mult,
            "armor_rule": getattr(armor_fn, "__name__", None),
            "card_modifier": getattr(card_fn, "__name__", None),
            "wins": wins,
            "hp_avgs": hp_avgs,
        }
        results.append(result)

        # Revert modifications
        if armor_fn:
            armor_fn(False)
        if card_fn:
            card_fn(False)

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
            f"card={entry['card_modifier']} win={rate:.1f}%"
        )

    return results


if __name__ == "__main__":
    # Example usage with trivial ranges
    run_experiments(range(20, 26, 2), [1.0, 1.2])
