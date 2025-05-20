import unittest
import sim

class TestDiceRolls(unittest.TestCase):
    def test_roll_die_with_reroll(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 4
        result = sim.roll_die(5, hero=hero)
        self.assertEqual(result, 2)
        self.assertEqual(hero.fate, 3)

    def test_roll_die_without_reroll(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 3
        result = sim.roll_die(5, hero=hero)
        self.assertEqual(result, 3)
        self.assertEqual(hero.fate, 3)

class TestMechanics(unittest.TestCase):
    def test_roll_hits_vulnerability(self):
        sim.RNG.seed(1)
        dmg = sim.roll_hits(1, 1, element=sim.Element.BRUTAL,
                             vulnerability=sim.Element.BRUTAL,
                             allow_reroll=False)
        self.assertEqual(dmg, 2)

    def test_fight_one_runs(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hercules", 25, sim.herc_base, sim.herc_pool)
        result = sim.fight_one(hero)
        self.assertIn(result, [True, False])
        self.assertLessEqual(hero.hp, hero.max_hp)
        self.assertGreaterEqual(hero.hp, 0)

class TestAbilities(unittest.TestCase):
    def test_curse_of_torment(self):
        hero = sim.Hero("Test", 5, [])
        sim.curse_of_torment(hero, 1)
        self.assertEqual(hero.hp, 4)
        sim.curse_of_torment(hero, 3)
        self.assertEqual(hero.hp, 4)

    def test_void_barrier(self):
        enemy = sim.Enemy(2, 3, sim.Element.BRUTAL, "void_barrier")
        sim.void_barrier(enemy, sim.Element.DIVINE)
        self.assertEqual(enemy.armor_pool, 1)
        sim.void_barrier(enemy, sim.Element.DIVINE)
        self.assertEqual(enemy.armor_pool, 1)
        sim.void_barrier(enemy, sim.Element.ARCANE)
        self.assertEqual(enemy.armor_pool, 2)

if __name__ == "__main__":
    unittest.main()
