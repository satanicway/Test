import unittest
import sim
import stats_runner

class TestReporting(unittest.TestCase):
    def test_generate_report(self):
        sim.RNG.seed(0)
        report = stats_runner.generate_report(num_runs=1)
        self.assertIsInstance(report, str)
        for hero in [h.name for h in sim.HEROES]:
            self.assertIn(hero, report)
        self.assertIn("Hero Win Rates", report)
        self.assertIn("Enemy Appearance Outcomes", report)
        self.assertIn("base:", report)

if __name__ == '__main__':
    unittest.main()
