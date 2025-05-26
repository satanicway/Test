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


if __name__ == "__main__":
    unittest.main()
