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

class TestCorruptedDryadAbilities(unittest.TestCase):
    def test_cursed_thorns(self):
        hero = sim.Hero("Hero", 10, [])
        hero.hp = 10
        hero.armor_pool = 3
        sim.cursed_thorns(hero)
        self.assertEqual(hero.hp, 7)
        self.assertEqual(hero.armor_pool, 0)

    def test_disturbed_flow(self):
        ctx = {}
        sim.disturbed_flow(ctx)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 4
        sim.RNG.seed(1)
        result = sim.roll_die(5, hero=hero, allow_reroll=not ctx.get("no_reroll", False))
        self.assertEqual(result, 3)
        self.assertEqual(hero.fate, 4)

if __name__ == "__main__":
    unittest.main()
