import unittest
import sim

class TestBasicMechanics(unittest.TestCase):
    def test_roll_die_range(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 0
        r = sim.roll_die(5, hero=hero)
        self.assertTrue(1 <= r <= 8)

    def test_fate_reroll_spent(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 4
        result = sim.roll_die(6, hero=hero)
        self.assertEqual(result, 2)
        self.assertEqual(hero.fate, 3)

    def test_vulnerability_doubles_damage(self):
        sim.RNG.seed(2)
        dmg = sim.roll_hits(1, 1, element=sim.Element.BRUTAL,
                             vulnerability=sim.Element.BRUTAL,
                             allow_reroll=False)
        self.assertEqual(dmg, 2)

    def test_simple_combat(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        result = sim.fight_one(hero)
        self.assertIn(result, [True, False])

if __name__ == "__main__":
    unittest.main()
