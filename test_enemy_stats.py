import unittest
import sim

class TestEnemyRunStats(unittest.TestCase):
    def test_run_counts(self):
        old_auto = sim.AUTO_MODE
        sim.AUTO_MODE = True
        sim.ENEMY_RUN_COUNTS.clear()
        # add easy enemies
        sim.ENEMIES['Easy'] = sim.Enemy('Easy', 1, 1, sim.Element.NONE, [0,0,0,0])
        sim.ENEMIES['Elite Easy'] = sim.Enemy('Elite Easy', 1, 1, sim.Element.NONE, [0,0,0,0])
        original = sim.ENEMY_WAVES
        try:
            sim.ENEMY_WAVES = [('Easy',1), ('Elite Easy',1)]
            hero = sim.Hero('Hero', 10, [sim.atk('Hit', sim.CardType.MELEE, 5)], [])
            sim.RNG.seed(0)
            self.assertTrue(sim.fight_one(hero))

            sim.ENEMY_WAVES = [('Elite Easy',1)]
            hero2 = sim.Hero('Hero', 1, [sim.atk('Hit', sim.CardType.MELEE, 0)], [])
            sim.RNG.seed(0)
            self.assertFalse(sim.fight_one(hero2))
        finally:
            sim.ENEMY_WAVES = original
            sim.AUTO_MODE = old_auto

        stats = sim.get_enemy_run_counts()
        self.assertEqual(stats['Hero']['Easy']['common']['win'], 1)
        self.assertEqual(stats['Hero']['Easy']['common']['loss'], 0)
        self.assertEqual(stats['Hero']['Easy']['elite']['win'], 1)
        self.assertEqual(stats['Hero']['Easy']['elite']['loss'], 1)

if __name__ == '__main__':
    unittest.main()
