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
        self.assertIn("30% HP", report)
        self.assertIn("Armor stacking", report)
        self.assertIn("Enemy Appearance Outcomes", report)
        self.assertIn("base:", report)

    def test_format_report_marks_outliers(self):
        wins = {"A": 30, "B": 70}
        hp = {"A": [0] * 8, "B": [0] * 8}
        over = {"A": 0, "B": 30}
        report = stats_runner.format_report(wins, {}, {}, {}, 100, hp, over)
        b_line = next(l for l in report.splitlines() if l.startswith("B:"))
        self.assertTrue(b_line.endswith("*"))
        self.assertIn("Armor stacking", report)

if __name__ == '__main__':
    unittest.main()
