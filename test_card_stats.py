import unittest
import sim

class TestCardStats(unittest.TestCase):
    def test_correlation_tracking(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        sim.fight_one(hero)
        data = sim.get_card_correlations()
        self.assertIn("Hercules", data)
        buckets = data["Hercules"]
        self.assertTrue(any(buckets[r] for r in buckets))
        total = sum(v["win"] + v["loss"] for cat in buckets.values() for v in cat.values())
        self.assertGreater(total, 0)

if __name__ == "__main__":
    unittest.main()
