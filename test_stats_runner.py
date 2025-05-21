import unittest
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

if __name__ == "__main__":
    unittest.main()
