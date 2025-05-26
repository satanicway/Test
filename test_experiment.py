import unittest
import unittest.mock
import experiment
import stats_runner
import sim


class TestExperimentRunner(unittest.TestCase):
    def test_armor_rule_invocation_and_results(self):
        calls = []

        def rule1(apply: bool) -> None:
            calls.append(("rule1", apply))

        def rule2(apply: bool) -> None:
            calls.append(("rule2", apply))

        def fake_run_stats_with_damage(*args, **kwargs):
            return (
                {h.name: 0 for h in sim.HEROES},
                {},
                {h.name: [] for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage",
            side_effect=fake_run_stats_with_damage,
        ) as m:
            results = experiment.run_experiments(
                hp_values=[20],
                damage_multipliers=[1.0],
                armor_rules=[rule1, rule2],
                num_runs=1,
            )

        self.assertEqual(m.call_count, 2)
        expected_calls = [
            ("rule1", True),
            ("rule1", False),
            ("rule2", True),
            ("rule2", False),
        ]
        self.assertEqual(calls, expected_calls)

        self.assertEqual(len(results), 2)
        for entry, name in zip(results, ["rule1", "rule2"]):
            self.assertEqual(entry["armor_rule"], name)
            for key in [
                "hp",
                "mult",
                "armor_rule",
                "card_modifier",
                "stat_mods",
                "min_damage",
                "wins",
                "hp_avgs",
                "hp_thresh",
            ]:
                self.assertIn(key, entry)

    def test_band_reduction_rule_effect(self):
        sim.RNG.seed(0)

        orig_bands = {n: e.damage_band[:] for n, e in sim.ENEMIES.items()}

        def fake_run_stats_with_rule(*args, **kwargs):
            self.assertTrue(sim.BAND_REDUCTION)
            for name, vals in orig_bands.items():
                expected = [max(0, int(v * 0.5)) for v in vals]
                self.assertEqual(sim.ENEMIES[name].damage_band, expected)
            return (
                {h.name: 1 for h in sim.HEROES},
                {},
                {h.name: [100] * 8 for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage",
            side_effect=fake_run_stats_with_rule,
        ):
            results_rule = experiment.run_experiments(
                hp_values=[20],
                damage_multipliers=[0.5],
                armor_rules=[sim.band_reduction_rule],
                num_runs=1,
            )

        self.assertFalse(sim.BAND_REDUCTION)
        for name, vals in orig_bands.items():
            self.assertEqual(sim.ENEMIES[name].damage_band, vals)

        def fake_run_stats_no_rule(*args, **kwargs):
            self.assertFalse(sim.BAND_REDUCTION)
            for name, vals in orig_bands.items():
                expected = [max(0, int(v * 0.5)) for v in vals]
                self.assertEqual(sim.ENEMIES[name].damage_band, expected)
            return (
                {h.name: 0 for h in sim.HEROES},
                {},
                {h.name: [50] * 8 for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage",
            side_effect=fake_run_stats_no_rule,
        ):
            results_no_rule = experiment.run_experiments(
                hp_values=[20],
                damage_multipliers=[0.5],
                num_runs=1,
            )

        self.assertNotEqual(results_rule[0]["wins"], results_no_rule[0]["wins"])
        self.assertNotEqual(results_rule[0]["hp_avgs"], results_no_rule[0]["hp_avgs"])

    def test_min_damage_rules(self):
        """total_min_damage_rule and per_enemy_min_damage_rule differ."""

        outcomes = []

        def fake_run_stats(*args, **kwargs):
            flag = kwargs.get("min_damage", False)
            hero = sim.Hero("Hero", 5, [])
            hero.armor_pool = 5
            e1 = sim.Enemy("G1", 1, 1, sim.Element.NONE, [1, 1, 1, 1])
            e2 = sim.Enemy("G2", 1, 1, sim.Element.NONE, [1, 1, 1, 1])
            ctx = {"enemies": [e1, e2]}
            sim.RNG.seed(0)
            sim.monster_attack([hero], ctx)
            dmg = hero.max_hp - hero.hp
            outcomes.append((flag, dmg, sim.MIN_DAMAGE, sim.TOTAL_MIN_DAMAGE))
            win = 1 if sim.TOTAL_MIN_DAMAGE else 2
            return (
                {h.name: win for h in sim.HEROES},
                {},
                {h.name: [0] * 8 for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats
        ):
            results_total = experiment.run_experiments(
                hp_values=[20],
                damage_multipliers=[1.0],
                armor_rules=[sim.total_min_damage_rule],
                num_runs=1,
            )

        flag, dmg, min_flag, total_flag = outcomes.pop(0)
        self.assertFalse(flag)
        self.assertFalse(min_flag)
        self.assertTrue(total_flag)
        self.assertEqual(dmg, 1)
        self.assertEqual(results_total[0]["wins"], {h.name: 1 for h in sim.HEROES})
        self.assertFalse(sim.MIN_DAMAGE)
        self.assertFalse(sim.TOTAL_MIN_DAMAGE)

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats
        ):
            results_per = experiment.run_experiments(
                hp_values=[20],
                damage_multipliers=[1.0],
                armor_rules=[sim.per_enemy_min_damage_rule],
                num_runs=1,
            )

        flag, dmg, min_flag, total_flag = outcomes.pop(0)
        self.assertFalse(flag)
        self.assertTrue(min_flag)
        self.assertFalse(total_flag)
        self.assertEqual(dmg, 2)
        self.assertEqual(results_per[0]["wins"], {h.name: 2 for h in sim.HEROES})
        self.assertFalse(sim.MIN_DAMAGE)
        self.assertFalse(sim.TOTAL_MIN_DAMAGE)

        self.assertNotEqual(results_total[0]["wins"], results_per[0]["wins"])

    def test_half_after_first_rule_effect(self):
        outcomes = []

        def fake_run_stats(*args, **kwargs):
            hero = sim.Hero("Hero", 10, [])
            hero.armor_pool = 4
            e1 = sim.Enemy("G1", 1, 1, sim.Element.NONE, [2, 2, 2, 2])
            e2 = sim.Enemy("G2", 1, 1, sim.Element.NONE, [2, 2, 2, 2])
            ctx = {"enemies": [e1, e2]}
            sim.monster_attack([hero], ctx)
            outcomes.append((hero.hp, hero.armor_pool, sim.HALF_AFTER_FIRST))
            return (
                {h.name: 0 for h in sim.HEROES},
                {},
                {h.name: [0] for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats
        ):
            results = experiment.run_experiments(
                hp_values=[10],
                damage_multipliers=[1.0],
                armor_rules=[sim.half_after_first_soak_rule],
                num_runs=1,
            )

        hp, armor, flag = outcomes.pop()
        self.assertTrue(flag)
        self.assertEqual(hp, 9)
        self.assertEqual(armor, 0)
        self.assertEqual(results[0]["armor_rule"], "half_after_first_soak_rule")
        self.assertFalse(sim.HALF_AFTER_FIRST)

    def test_armor_cap_rule_effect(self):
        outcomes = []

        def fake_run_stats(*args, **kwargs):
            hero = sim.Hero("Hero", 10, [])
            hero.armor_pool = 5
            enemy = sim.Enemy("Goblin", 1, 1, sim.Element.NONE, [5, 5, 5, 5])
            ctx = {"enemies": [enemy]}
            sim.monster_attack([hero], ctx)
            outcomes.append((hero.hp, hero.armor_pool, sim.ARMOR_CAP))
            return (
                {h.name: 0 for h in sim.HEROES},
                {},
                {h.name: [0] for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats
        ):
            results = experiment.run_experiments(
                hp_values=[10],
                damage_multipliers=[1.0],
                armor_rules=[sim.armor_cap_rule],
                num_runs=1,
            )

        hp, armor, cap = outcomes.pop()
        self.assertEqual(cap, 3)
        self.assertEqual(hp, 8)
        self.assertEqual(armor, 2)
        self.assertEqual(results[0]["armor_rule"], "armor_cap_rule")
        self.assertEqual(sim.ARMOR_CAP, 0)

    def test_armor_decay_rule_effect(self):
        outcomes = []

        def fake_run_stats(*args, **kwargs):
            hero = sim.Hero("Hero", 10, [])
            hero.armor_pool = 1
            enemy = sim.Enemy("Goblin", 1, 1, sim.Element.NONE, [0, 0, 0, 0])
            ctx = {"enemies": [enemy]}
            sim.monster_attack([hero], ctx)
            outcomes.append((hero.hp, hero.armor_pool, sim.ARMOR_DECAY))
            return (
                {h.name: 0 for h in sim.HEROES},
                {},
                {h.name: [0] for h in sim.HEROES},
                {h.name: 0 for h in sim.HEROES},
            )

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats
        ):
            results = experiment.run_experiments(
                hp_values=[10],
                damage_multipliers=[1.0],
                armor_rules=[sim.armor_decay_rule],
                num_runs=1,
            )

        hp, armor, flag = outcomes.pop()
        self.assertTrue(flag)
        self.assertEqual(hp, 10)
        self.assertEqual(armor, 0)
        self.assertEqual(results[0]["armor_rule"], "armor_decay_rule")
        self.assertFalse(sim.ARMOR_DECAY)


if __name__ == "__main__":
    unittest.main()
