import unittest
import unittest.mock
import experiment
import stats_runner
import sim
import io
import contextlib


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

    def test_half_after_first_cap_and_decay_rules(self):
        """half_after_first_soak_rule, armor_cap_rule and armor_decay_rule toggle globals."""

        rules = [
            (sim.half_after_first_soak_rule, "HALF_AFTER_FIRST", True, False),
            (sim.armor_cap_rule, "ARMOR_CAP", 3, 0),
            (sim.armor_decay_rule, "ARMOR_DECAY", True, False),
        ]

        for rule, attr, enabled, disabled in rules:
            def fake_run_stats_with_rule(*args, **kwargs):
                self.assertEqual(getattr(sim, attr), enabled)
                return (
                    {h.name: 1 for h in sim.HEROES},
                    {},
                    {h.name: [100] * 8 for h in sim.HEROES},
                    {h.name: 0 for h in sim.HEROES},
                )

            with unittest.mock.patch(
                "stats_runner.run_stats_with_damage", side_effect=fake_run_stats_with_rule
            ):
                results_rule = experiment.run_experiments(
                    hp_values=[20],
                    damage_multipliers=[1.0],
                    armor_rules=[rule],
                    num_runs=1,
                )

            self.assertEqual(getattr(sim, attr), disabled)

            def fake_run_stats_no_rule(*args, **kwargs):
                self.assertEqual(getattr(sim, attr), disabled)
                return (
                    {h.name: 0 for h in sim.HEROES},
                    {},
                    {h.name: [50] * 8 for h in sim.HEROES},
                    {h.name: 0 for h in sim.HEROES},
                )

            with unittest.mock.patch(
                "stats_runner.run_stats_with_damage", side_effect=fake_run_stats_no_rule
            ):
                results_no_rule = experiment.run_experiments(
                    hp_values=[20],
                    damage_multipliers=[1.0],
                    num_runs=1,
                )

            entry = results_rule[0]
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

            self.assertNotEqual(results_rule[0]["wins"], results_no_rule[0]["wins"])
            self.assertNotEqual(
                results_rule[0]["hp_avgs"], results_no_rule[0]["hp_avgs"]
            )

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

    def test_summary_report_for_multiple_rules(self):
        """Run several armor rules and verify the formatted summary output.

        The test simulates three simplified armor rules representing a balanced
        configuration, an overpowered option and an underpowered option.  The
        printed summary should flag rules whose win rates fall outside the
        40-60% band or whose heroes finish over 30% HP more than 20% of the
        time.
        """

        # Placeholder armor rules.  They don't modify the simulation state but
        # allow run_experiments() to record which rule produced which results.
        def rule_balanced(apply: bool) -> None:
            pass

        def rule_overpowered(apply: bool) -> None:
            pass

        def rule_underpowered(apply: bool) -> None:
            pass

        # Predetermined win counts and >30% HP outcomes for each rule above.
        # The tuples are (wins_per_hero, high_hp_count) across two runs.  The
        # values simulate whether the rule meets the target thresholds.
        outcomes = [
            (1, 0),  # balanced: 50% win rate, 0% high-HP
            (2, 1),  # overpowered: 100% win rate, 50% high-HP
            (0, 0),  # underpowered: 0% win rate, 0% high-HP
        ]

        def fake_run_stats_with_damage(*args, **kwargs):
            idx = fake_run_stats_with_damage.calls
            fake_run_stats_with_damage.calls += 1
            wins_per_hero, over_count = outcomes[idx]
            return (
                {h.name: wins_per_hero for h in sim.HEROES},
                {},
                {h.name: [0] * 8 for h in sim.HEROES},
                {h.name: over_count for h in sim.HEROES},
            )

        fake_run_stats_with_damage.calls = 0

        with unittest.mock.patch(
            "stats_runner.run_stats_with_damage", side_effect=fake_run_stats_with_damage
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                results = experiment.run_experiments(
                    hp_values=[20],
                    damage_multipliers=[1.0],
                    armor_rules=[rule_balanced, rule_overpowered, rule_underpowered],
                    num_runs=2,
                )
                for entry in results:
                    print(entry["armor_rule"])
                    report = stats_runner.format_report(
                        entry["wins"],
                        {},
                        {},
                        {},
                        2,
                        entry["hp_avgs"],
                        entry["hp_thresh"],
                    )
                    print(report)
            summary = buf.getvalue()

        # Balanced rule should not be flagged
        self.assertIn("rule_balanced", summary)
        self.assertIn("Hercules: 50.0% (1/2)", summary)
        self.assertIn(">30% HP: 0.0% (0/2)", summary)
        self.assertNotIn("50.0% (1/2) *", summary)

        # Overpowered rule should be flagged for high win rate and HP
        self.assertIn("rule_overpowered", summary)
        self.assertIn("Hercules: 100.0% (2/2) *", summary)
        self.assertIn(">30% HP: 50.0% (1/2)", summary)

        # Underpowered rule should be flagged for low win rate
        self.assertIn("rule_underpowered", summary)
        self.assertIn("Hercules: 0.0% (0/2) *", summary)

if __name__ == "__main__":
    unittest.main()
