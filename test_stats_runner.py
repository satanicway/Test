import unittest
import unittest.mock
import sim
import stats_runner

class TestStatsRunner(unittest.TestCase):
    def test_run_stats_small(self):
        sim.RNG.seed(0)
        results = stats_runner.run_stats(num_runs=5)
        hero_names = {h.name for h in sim.HEROES}
        self.assertEqual(set(results.keys()), hero_names)
        for val in results.values():
            self.assertTrue(0 <= val <= 5)

    def test_run_stats_with_hp(self):
        sim.RNG.seed(1)
        wins, damage, hp = stats_runner.run_stats_with_damage(num_runs=1)
        hero_names = {h.name for h in sim.HEROES}
        self.assertEqual(set(hp.keys()), hero_names)
        for vals in hp.values():
            self.assertEqual(len(vals), 8)
            for v in vals:
                self.assertTrue(0 <= v <= 100)

    def test_hp_log_fills_zeros_after_death(self):
        """HP logs should contain zeros after an early death."""
        sim.RNG.seed(0)
        _, _, hp = stats_runner.run_stats_with_damage(num_runs=1)
        vals = hp.get("Hercules")
        self.assertIsNotNone(vals)
        self.assertEqual(len(vals), 8)
        for v in vals:
            self.assertTrue(0 <= v <= 100)
        # hero dies early so later waves should be zero
        self.assertTrue(any(v == 0 for v in vals[1:]))

    def test_fight_one_timeout(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        with self.assertRaises(TimeoutError) as ctx:
            sim.fight_one(hero, timeout=0.0)
        msg = str(ctx.exception)
        self.assertIn("Hercules", msg)
        self.assertIn(sim.ENEMY_WAVES[0][0], msg)

    def test_fight_one_max_exchanges(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        with self.assertRaises(TimeoutError) as ctx:
            sim.fight_one(hero, max_exchanges=0)
        msg = str(ctx.exception)
        self.assertIn("Hercules", msg)
        self.assertIn(sim.ENEMY_WAVES[0][0], msg)

    def test_run_gauntlet_retries_on_timeout(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        calls = {"n": 0}

        def fake_fight(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            if calls["n"] == 1:
                raise TimeoutError("boom")
            return True

        with unittest.mock.patch("sim.fight_one", side_effect=fake_fight):
            result = stats_runner.run_gauntlet(hero, timeout=1)
        self.assertTrue(result)
        self.assertEqual(calls["n"], 2)

    def test_run_gauntlet_passes_max_exchanges(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)

        def fake_fight(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            self.assertEqual(max_exchanges, 42)
            self.assertEqual(wave_timeout, 10.0)
            self.assertIsNone(max_total_exchanges)
            return True

        with unittest.mock.patch("sim.fight_one", side_effect=fake_fight) as m:
            result = stats_runner.run_gauntlet(hero, timeout=1, max_exchanges=42)
        self.assertTrue(result)
        self.assertEqual(m.call_count, 1)

    def test_run_gauntlet_raises_after_many_timeouts(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        calls = {"n": 0}

        def always_timeout(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            raise TimeoutError("boom")

        with unittest.mock.patch("sim.fight_one", side_effect=always_timeout):
            with self.assertRaises(TimeoutError) as ctx:
                stats_runner.run_gauntlet(hero, timeout=1, max_retries=2)
        self.assertIn("failed", str(ctx.exception))
        self.assertEqual(calls["n"], 3)

    def test_run_gauntlet_timeout_after_max_retries(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        calls = {"n": 0}

        def always_timeout(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            raise TimeoutError("boom")

        with unittest.mock.patch("sim.fight_one", side_effect=always_timeout):
            with self.assertRaises(TimeoutError):
                stats_runner.run_gauntlet(hero, timeout=1, max_retries=1)
        self.assertEqual(calls["n"], 2)

    def test_run_gauntlet_aborts_on_wave_timeout_limit(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        calls = {"n": 0}

        def always_timeout(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            self.assertEqual(wave_timeout, 0)
            raise TimeoutError("boom")

        with unittest.mock.patch("sim.fight_one", side_effect=always_timeout):
            with self.assertRaises(TimeoutError):
                stats_runner.run_gauntlet(hero, timeout=1, max_retries=2, wave_timeout=0)
        self.assertEqual(calls["n"], 3)

    def test_run_gauntlet_aborts_on_total_exchange_limit(self):
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        calls = {"n": 0}

        def always_timeout(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            self.assertEqual(max_total_exchanges, 0)
            raise TimeoutError("boom")

        with unittest.mock.patch("sim.fight_one", side_effect=always_timeout):
            with self.assertRaises(TimeoutError):
                stats_runner.run_gauntlet(hero, timeout=1, max_retries=2, max_total_exchanges=0)
        self.assertEqual(calls["n"], 3)

    def test_upgrades_apply_after_timeout(self):
        """Upgrades should apply to the new hero after a timeout."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        initial_len = len(hero.deck.cards)

        calls = {"n": 0, "heroes": []}

        def fake_fight(
            h,
            hp_log=None,
            *,
            timeout=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls["n"] += 1
            calls["heroes"].append(h)
            if calls["n"] == 1:
                raise TimeoutError("boom")
            for _ in range(6):
                h.gain_upgrades()
            return True

        with unittest.mock.patch("sim.fight_one", side_effect=fake_fight):
            result = stats_runner.run_gauntlet(hero, timeout=1)

        self.assertTrue(result)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(len(hero.deck.cards), initial_len)
        new_hero = calls["heroes"][1]
        self.assertIsNot(new_hero, hero)
        self.assertEqual(len(new_hero.deck.cards), len(new_hero.base_cards) + 8)

    def test_run_stats_passes_options(self):
        calls = []

        def fake_run(
            hero,
            hp_log=None,
            *,
            timeout=None,
            max_retries=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls.append(
                (timeout, max_retries, max_exchanges, wave_timeout, max_total_exchanges)
            )
            return True

        with unittest.mock.patch("stats_runner.run_gauntlet",
                                 side_effect=fake_run):
            stats_runner.run_stats(
                num_runs=1,
                timeout=1.5,
                max_retries=7,
                max_exchanges=44,
                wave_timeout=0.5,
                max_total_exchanges=123,
            )

        self.assertEqual(len(calls), len(sim.HEROES))
        for t, r, e, w, m in calls:
            self.assertEqual(t, 1.5)
            self.assertEqual(r, 7)
            self.assertEqual(e, 44)
            self.assertEqual(w, 0.5)
            self.assertEqual(m, 123)

    def test_run_stats_with_damage_passes_options(self):
        calls = []

        def fake_run(
            hero,
            hp_log=None,
            *,
            timeout=None,
            max_retries=None,
            max_exchanges=None,
            wave_timeout=None,
            max_total_exchanges=None,
        ):
            calls.append(
                (timeout, max_retries, max_exchanges, wave_timeout, max_total_exchanges)
            )
            return True

        with unittest.mock.patch("stats_runner.run_gauntlet",
                                 side_effect=fake_run):
            stats_runner.run_stats_with_damage(
                num_runs=1,
                timeout=2.5,
                max_retries=8,
                max_exchanges=55,
                wave_timeout=1.5,
                max_total_exchanges=321,
            )

        self.assertEqual(len(calls), len(sim.HEROES))
        for t, r, e, w, m in calls:
            self.assertEqual(t, 2.5)
            self.assertEqual(r, 8)
            self.assertEqual(e, 55)
            self.assertEqual(w, 1.5)
            self.assertEqual(m, 321)

if __name__ == "__main__":
    unittest.main()
