import unittest
import sim
import stats_runner

class TestSimulationCounters(unittest.TestCase):
    def test_run_stats_aggregates(self):
        sim.RNG.seed(0)
        wins, damage = stats_runner.run_stats_with_damage(num_runs=3)
        # win counters should record a loss for each hero
        expected_wins = {h.name: 0 for h in sim.HEROES}
        self.assertEqual(wins, expected_wins)

        # card usage logs update for each run
        card_stats = sim.get_card_correlations()
        self.assertEqual(
            card_stats["Hercules"]["base"]["Pillar-Breaker Blow"],
            {"win": 0, "loss": 12},
        )

        # enemy appearance/run counts updated
        enemy_stats = sim.get_enemy_run_counts()
        self.assertEqual(
            enemy_stats["Hercules"]["Treant"],
            {"common": {"win": 0, "loss": 2}, "elite": {"win": 0, "loss": 1}},
        )
        self.assertEqual(
            enemy_stats["Brynhild"]["Treant"],
            {"common": {"win": 0, "loss": 0}, "elite": {"win": 0, "loss": 2}},
        )

        # total damage inflicted by a specific enemy is tracked
        self.assertEqual(damage[("Hercules", "Elite Minotaur")], 9)

if __name__ == "__main__":
    unittest.main()
