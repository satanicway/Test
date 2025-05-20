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

    def test_aerial_combat_modifier(self):
        sim.RNG.seed(5)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Strike", sim.CardType.MELEE, 1)
        enemy = sim.Enemy("Gryphon", 4, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "aerial-combat")
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 4)

    def test_ephemeral_wings_block(self):
        sim.RNG.seed(5)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Strike", sim.CardType.MELEE, 1)
        enemy = sim.Enemy("Elite Gryphon", 5, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "ephemeral-wings")
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 4)
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 4)

class TestSoldierAbilities(unittest.TestCase):
    def test_dark_phalanx_multi_reduction(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Cleave", sim.CardType.MELEE, 2, multi=True)
        ctx = {"enemies": [
            sim.Enemy("Soldier", 2, 5, sim.Element.PRECISE, [0, 0, 0, 2], "dark-phalanx") for _ in range(2)
        ]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(ctx["enemies"]), 2)
        self.assertTrue(all(e.hp == 1 for e in ctx["enemies"]))

    def test_spiked_armor_triggers(self):
        sim.RNG.seed(9)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Smash", sim.CardType.MELEE, 3)
        enemy = sim.Enemy("Elite Soldier", 3, 6, sim.Element.PRECISE, [0, 0, 1, 3], "spiked-armor")
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.hp, 9)
        self.assertEqual(enemy.hp, 0)

class TestPriestAbilities(unittest.TestCase):
    def test_power_of_death_bonus_damage(self):
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Priest", 2, 3, sim.Element.ARCANE, [0, 0, 0, 0], sim.power_of_death)
        ctx = {"enemies": [enemy], "dead_priests": 2}
        enemy.ability(ctx)
        sim.monster_attack([hero], ctx)
        self.assertEqual(hero.hp, 8)

    def test_silence_blocks_effects(self):
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Bless", sim.CardType.UTIL, 0, effect=sim.gain_fate_fx(1), persistent="combat")
        enemy = sim.Enemy("Elite Priest", 3, 4, sim.Element.ARCANE, [0, 0, 0, 0], sim.silence)
        ctx = {"enemies": [enemy]}
        enemy.ability(ctx)
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.fate, 0)
        self.assertFalse(hero.combat_effects)

if __name__ == "__main__":
    unittest.main()
