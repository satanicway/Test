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


if __name__ == "__main__":
    unittest.main()
