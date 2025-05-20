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

    def test_roots_of_despair_triggers(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Weak", sim.CardType.MELEE, 1)
        hero.deck = sim.Deck([card])
        ctx = {"enemies": [sim.Enemy(8, 7, sim.Element.DIVINE, "roots_of_despair")]} 
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.hp, 9)

    def test_power_sap_removes_effect(self):
        sim.RNG.seed(2)
        hero = sim.Hero("Hero", 10, [])
        dummy_card = sim.atk("X", sim.CardType.UTIL, 0)
        hero.combat_effects.append((lambda h, c: None, dummy_card))
        enemy = sim.Enemy(7, 6, sim.Element.DIVINE, "power_sap")
        ctx = {"hero": hero, "enemies": [enemy]}
        sim.power_sap(ctx)
        self.assertEqual(len(hero.combat_effects), 0)
        self.assertEqual(enemy.hp, 8)

if __name__ == "__main__":
    unittest.main()
