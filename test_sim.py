import unittest
import unittest.mock
import sim

class TestDiceRolls(unittest.TestCase):
    def test_roll_die_with_reroll(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 4
        result = sim.roll_die(5, hero=hero)
        self.assertEqual(result, 2)
        self.assertEqual(hero.fate, 3)

    def test_roll_hits_reroll_for_kill(self):
        """roll_hits should spend fate when a reroll can kill."""
        sim.RNG.seed(3)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 5
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        dmg = sim.roll_hits(1, enemy.defense, hero=hero,
                             enemy=enemy, allow_reroll=True)
        self.assertEqual(dmg, 1)
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

    def test_temp_vulnerability_effect(self):
        """Cards can grant temporary vulnerability for the next attack."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        buff = sim.atk("Buff", sim.CardType.UTIL, 0,
                       effect=sim.temp_vuln(sim.Element.DIVINE))
        attack = sim.atk("Smite", sim.CardType.MELEE, 1, sim.Element.DIVINE)
        enemy = sim.Enemy("Dummy", 2, 5, sim.Element.PRECISE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, buff, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 0)

    def test_multi_target_limit(self):
        """Cards may hit only a subset of enemies."""
        sim.RNG.seed(9)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Sweep", sim.CardType.MELEE, 2, multi=True, max_targets=2)
        enemies = [
            sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
            for _ in range(3)
        ]
        ctx = {"enemies": enemies}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(ctx["enemies"]), 1)
        self.assertEqual(ctx["enemies"][0].hp, 1)

    def test_fight_one_runs(self):
        sim.RNG.seed(9)
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
        g1 = sim.Enemy("Elite Gryphon", 5, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "ephemeral-wings")
        g2 = sim.Enemy("Elite Gryphon", 5, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "ephemeral-wings")
        ctx = {"enemies": [g1, g2]}

        # first hit damages g1 and sets its block
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(g1.hp, 4)

        # hitting g2 should not consume g1's block
        ctx["enemies"] = [g2, g1]
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(g2.hp, 4)

        # next attacks are absorbed by the respective gryphon that set the block
        ctx["enemies"] = [g1, g2]
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(g1.hp, 4)

        ctx["enemies"] = [g2, g1]
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(g2.hp, 4)

class TestSpinnerAbilities(unittest.TestCase):
    def test_web_slinger_converts_ranged(self):
        sim.RNG.seed(5)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Shot", sim.CardType.RANGED, 1)
        enemy = sim.Enemy("Gryphon", 4, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "aerial-combat")
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 3)

        sim.RNG.seed(5)
        enemy2 = sim.Enemy("Gryphon", 4, 5, sim.Element.SPIRITUAL, [0, 0, 0, 0], "aerial-combat")
        ctx = {"enemies": [enemy2], "ranged_to_melee": True}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy2.hp, 4)

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

    def test_void_soldier_multi_penalty(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Split", sim.CardType.MELEE, 4, multi=True)
        enemy = sim.Enemy("Void Soldier", 2, 5, sim.Element.PRECISE, [0, 0, 0, 2], "void-soldier", attack_mod=sim.void_soldier_mod)
        ctx = {"enemies": [enemy], "attack_hooks": [enemy.attack_mod]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, -1)

    def test_void_soldier_dark_phalanx_two(self):
        """Damage is reduced when two Void Soldiers remain."""
        sim.RNG.seed(5)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Test", sim.CardType.MELEE, 2, multi=True)
        enemies = [
            sim.Enemy("Void Soldier", 2, 5, sim.Element.PRECISE,
                      [0, 0, 0, 2], "void-soldier", attack_mod=sim.void_soldier_mod)
            for _ in range(2)
        ]
        ctx = {"enemies": enemies, "attack_hooks": [enemies[0].attack_mod]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(ctx["enemies"]), 2)
        self.assertTrue(all(e.hp == 1 for e in ctx["enemies"]))


class TestWizardAbilities(unittest.TestCase):
    def test_curse_of_torment_triggers(self):
        sim.RNG.seed(2)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy(
            "Wizard", 2, 3, sim.Element.BRUTAL, [0, 1, 1, 3], "curse-of-torment"
        )
        sim.roll_hits(1, enemy.defense, hero=hero, enemy=enemy, allow_reroll=False)
        self.assertEqual(hero.hp, 9)

    def test_void_barrier_stacks_by_element(self):
        enemy = sim.Enemy(
            "Elite Wizard", 2, 4, sim.Element.BRUTAL, [0, 2, 2, 3], "void-barrier"
        )
        sim.void_barrier(enemy, sim.Element.BRUTAL)
        self.assertEqual(enemy.armor_pool, 1)
        sim.void_barrier(enemy, sim.Element.BRUTAL)
        self.assertEqual(enemy.armor_pool, 1)
        sim.void_barrier(enemy, sim.Element.PRECISE)
        self.assertEqual(enemy.armor_pool, 2)

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


class TestMinotaurAbilities(unittest.TestCase):
    def test_cleave_all_hits_every_hero(self):
        sim.RNG.seed(0)
        heroes = [sim.Hero("H1", 10, []), sim.Hero("H2", 10, [])]
        enemy = sim.Enemy("Minotaur", 4, 3, sim.Element.PRECISE,
                          [0, 0, 1, 3], "cleave_all")
        ctx = {"enemies": [enemy]}
        sim.monster_attack(heroes, ctx)
        self.assertEqual(heroes[0].hp, 7)
        self.assertEqual(heroes[1].hp, 7)

    def test_enrage_double_attack(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Elite Minotaur", 3, 3, sim.Element.PRECISE,
                          [0, 0, 2, 4], "enrage")
        ctx = {"enemies": [enemy]}
        sim.monster_attack([hero], ctx)
        self.assertEqual(hero.hp, 2)


class TestMonsterDamageTracking(unittest.TestCase):
    def test_damage_logged(self):
        sim.MONSTER_DAMAGE.clear()
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Goblin", 1, 1, sim.Element.NONE, [1, 1, 1, 1])
        ctx = {"enemies": [enemy]}
        sim.monster_attack([hero], ctx)
        self.assertEqual(sim.MONSTER_DAMAGE[(hero.name, enemy.name)], 1)

    def test_counters_reset_between_runs(self):
        sim.MONSTER_DAMAGE.clear()
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 1, 1, sim.Element.NONE, [1, 1, 1, 1])
        ctx = {"enemies": [enemy]}
        sim.monster_attack([hero], ctx)
        self.assertIn((hero.name, enemy.name), sim.MONSTER_DAMAGE)
        sim.fight_one(sim.Hero("Hero", 10, []))
        self.assertNotIn((hero.name, enemy.name), sim.MONSTER_DAMAGE)


class TestBansheeAbilities(unittest.TestCase):
    def test_ghostly_clears_on_fourth_exchange(self):
        enemy = sim.Enemy(
            "Shadow Banshee", 3, 5, sim.Element.DIVINE, [0, 0, 0, 0],
            ability=None, start_fx=sim.ghostly
        )
        ctx = {"enemies": [enemy], "exchange": 3}
        enemy.start_fx(ctx)
        self.assertFalse(ctx["enemies"])

    def test_banshee_wail_damage(self):
        hero = sim.Hero("Hero", 10, [])
        sim.banshee_wail([hero], 7)
        self.assertEqual(hero.hp, 8)


class TestTreantAbilities(unittest.TestCase):
    def test_power_sap_removes_effect(self):
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Song", sim.CardType.UTIL, 0, effect=sim.gain_fate_fx(1),
                       persistent="combat")
        hero.combat_effects.append((card.effect, card))
        treant = sim.Enemy("Treant", 7, 6, sim.Element.DIVINE, [0, 1, 1, 4],
                           "power-sap")
        ctx = {"heroes": [hero], "enemies": [treant]}
        sim.power_sap(ctx, treant)
        self.assertFalse(hero.combat_effects)
        self.assertEqual(treant.hp, 8)

    def test_roots_of_despair_triggers_on_miss(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Strike", sim.CardType.MELEE, 1)
        treant = sim.Enemy("Elite Treant", 8, 7, sim.Element.DIVINE,
                           [0, 1, 3, 5], "roots-of-despair")
        ctx = {"enemies": [treant]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.hp, 9)


class TestAngelAbilities(unittest.TestCase):
    def test_corrupted_destiny(self):
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 5
        sim.corrupted_destiny(hero)
        self.assertEqual(hero.fate, 3)

    def test_denied_heaven_rerolls_eight(self):
        sim.RNG.seed(9)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Elite Angel", 7, 6, sim.Element.ARCANE,
                          [0, 0, 0, 0], "denied-heaven")
        dmg = sim.roll_hits(1, 1, hero=hero, enemy=enemy, allow_reroll=False)
        self.assertEqual(dmg, 1)


class TestPersistentEffects(unittest.TestCase):
    def test_exchange_effect_expires(self):
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Chant", sim.CardType.UTIL, 0,
                       effect=sim.gain_fate_fx(1), persistent="exchange")
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(hero.exchange_effects), 1)
        # start next exchange: clear effects
        hero.exchange_effects.clear()
        hero.active_hymns = [h for h in hero.active_hymns if h.persistent == "combat"]
        sim.apply_persistent(hero, ctx)
        self.assertEqual(len(hero.exchange_effects), 0)
        self.assertEqual(hero.fate, 1)

    def test_combat_effect_persists(self):
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Bless", sim.CardType.UTIL, 0,
                       effect=sim.gain_fate_fx(1), persistent="combat")
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.fate, 1)
        sim.apply_persistent(hero, ctx)
        self.assertEqual(hero.fate, 2)
        # end combat clears effects
        hero.combat_effects.clear()
        sim.apply_persistent(hero, ctx)
        self.assertEqual(hero.fate, 2)


class TestNewCardEffects(unittest.TestCase):
    def test_modify_enemy_defense_effect(self):
        sim.RNG.seed(5)
        hero = sim.Hero("Hero", 10, [])
        debuff = sim.atk("Expose", sim.CardType.UTIL, 0,
                         effect=sim.modify_enemy_defense(-1), persistent="exchange")
        attack = sim.atk("Strike", sim.CardType.MELEE, 1)
        enemy = sim.Enemy("Dummy", 1, 6, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, debuff, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 0)

    def test_discard_for_fate(self):
        hero = sim.Hero("Hero", 10, [])
        hero.deck.hand = [sim.atk("A", sim.CardType.MELEE, 1) for _ in range(3)]
        fx = sim.discard_for_fate(2, 1)
        fx(hero, {})
        self.assertEqual(len(hero.deck.disc), 2)
        self.assertEqual(hero.fate, 1)

    def test_rage_hp_for_damage(self):
        hero = sim.Hero("Hero", 10, [])
        rage = sim.atk("Rage", sim.CardType.UTIL, 0, effect=sim.hp_for_damage(2, 2))
        attack = sim.atk("Hit", sim.CardType.MELEE, 0)
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, rage, ctx)
        self.assertEqual(hero.hp, 8)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 1)

    def test_crushing_impact_multi_bonus(self):
        hero = sim.Hero("Hero", 10, [])
        buff = sim.atk("Crushing Impact", sim.CardType.UTIL, 0,
                       effect=sim.multi_bonus(2), persistent="exchange")
        attack = sim.atk("Sweep", sim.CardType.MELEE, 0, multi=True)
        enemies = [sim.Enemy("E", 2, 1, sim.Element.NONE, [0, 0, 0, 0]) for _ in range(2)]
        ctx = {"enemies": enemies}
        sim.resolve_attack(hero, buff, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertTrue(all(e.hp == 0 for e in enemies))

    def test_global_reroll_fx(self):
        """Missed dice are rerolled once for the exchange."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 10, 6, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.global_reroll_fx()(hero, ctx)
        dmg = sim.roll_hits(4, enemy.defense, hero=hero, enemy=enemy, ctx=ctx, allow_reroll=False)
        self.assertEqual(dmg, 4)

    def test_choose_element_effect(self):
        """Next attack uses enemy vulnerability when available."""
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.DIVINE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        fx = sim.choose_element()
        fx(hero, ctx)
        attack = sim.atk("Strike", sim.CardType.MELEE, 1)
        sim.resolve_attack(hero, attack, ctx)
        self.assertFalse(ctx["enemies"])  # vulnerability damage

    def test_menacing_step_moves_enemy(self):
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 3, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.menacing_step_fx(hero, ctx)
        self.assertNotIn(enemy, ctx["enemies"])
        self.assertIn(enemy, ctx.get("adjacent_enemies", []))

class TestHymnMechanics(unittest.TestCase):
    def test_hymn_armor_scaling(self):
        hero = sim.Hero("Hero", 10, [])
        shield = sim.atk("Shields", sim.CardType.UTIL, 0, hymn=True,
                          persistent="combat", effect=sim.hymn_armor(1))
        prayer = sim.atk("Prayer", sim.CardType.UTIL, 0, hymn=True,
                          persistent="combat", effect=sim.hymn_armor(1))
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, shield, ctx)
        sim.apply_persistent(hero, ctx)
        self.assertEqual(hero.armor_pool, 1)

        sim.resolve_attack(hero, prayer, ctx)
        hero.armor_pool = 0
        hero.active_hymns = [h for h in hero.active_hymns if h.persistent == "combat"]
        sim.apply_persistent(hero, ctx)
        self.assertEqual(hero.armor_pool, 4)

    def test_hymn_damage_scaling(self):
        sim.RNG.seed(1)
        hero = sim.Hero("Hero", 10, [])
        aria = sim.atk("Aria", sim.CardType.UTIL, 0, hymn=True,
                        persistent="combat", effect=sim.hymn_damage(1))
        attack = sim.atk("Hit", sim.CardType.MELEE, 1)
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, aria, ctx)
        sim.apply_persistent(hero, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 1)

    def test_hymn_end_card(self):
        hero = sim.Hero("Hero", 10, [])
        shield = sim.atk("Shields", sim.CardType.UTIL, 0, hymn=True,
                          persistent="combat", effect=sim.hymn_armor(1))
        ender = sim.atk("Storms", sim.CardType.UTIL, 0, effect=sim.end_hymns_fx)
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, shield, ctx)
        self.assertTrue(hero.active_hymns)
        sim.resolve_attack(hero, ender, ctx)
        self.assertFalse(hero.active_hymns)

    def test_damage_scales_with_hymns(self):
        hero = sim.Hero("Hero", 10, [])
        hymn1 = sim.atk("Choir", sim.CardType.UTIL, 0, hymn=True,
                        persistent="combat")
        hymn2 = sim.atk("Ballad", sim.CardType.UTIL, 0, hymn=True,
                        persistent="combat")
        attack = sim.atk("Strike", sim.CardType.MELEE, 0, dmg_per_hymn=1)
        enemy = sim.Enemy("Dummy", 2, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, hymn1, ctx)
        sim.resolve_attack(hero, hymn2, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 0)

    def test_exchange_hymn_expires(self):
        hero = sim.Hero("Hero", 10, [])
        exhymn = sim.atk("Song", sim.CardType.UTIL, 0, hymn=True,
                         persistent="exchange")
        combathymn = sim.atk("Prayer", sim.CardType.UTIL, 0, hymn=True,
                             persistent="combat")
        attack = sim.atk("Smite", sim.CardType.MELEE, 0, dmg_per_hymn=1)
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, exhymn, ctx)
        sim.resolve_attack(hero, combathymn, ctx)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 1)  # two hymns => dmg 2
        # start next exchange
        hero.exchange_effects.clear()
        hero.active_hymns = [h for h in hero.active_hymns if h.persistent == "combat"]
        ctx["hymn_damage"] = 0
        sim.apply_persistent(hero, ctx)
        enemy2 = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx["enemies"] = [enemy2]
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy2.hp, 2)  # only combat hymn remains


class TestMusashiCards(unittest.TestCase):
    def test_vulnerability_bonus(self):
        sim.RNG.seed(5)
        hero = sim.Hero("Musashi", 20, [])
        card = sim.swallow_cut
        enemy = sim.Enemy("Dummy", 3, 5, sim.Element.PRECISE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertFalse(ctx["enemies"])  # enemy defeated by bonus

    def test_util_before_ranged(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Musashi", 20, [])
        parry = sim.flowing_water
        attack = sim.atk("Arrow", sim.CardType.RANGED, 1)
        enemy = sim.Enemy("Dummy", 2, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        # emulate fight ordering: parry before ranged
        hero.deck.hand = [parry, attack]
        while True:
            pre = None
            for i, c in enumerate(hero.deck.hand):
                if c.ctype == sim.CardType.MELEE and c.before_ranged:
                    pre = hero.deck.hand.pop(i)
                    break
            if not pre:
                break
            sim.resolve_attack(hero, pre, ctx)
        sim.resolve_attack(hero, hero.deck.hand.pop(), ctx)
        self.assertFalse(ctx["enemies"])  # parry resolved before ranged

    def test_dual_moon_guard_armor_gain(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Musashi", 20, [])
        guard = sim.dual_moon_guard
        attack = sim.atk("Strike", sim.CardType.MELEE, 2)
        enemy = sim.Enemy("Dummy", 10, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, guard, ctx)
        sim.resolve_attack(hero, attack, ctx)
        for fx, e in ctx.get("end_hooks", []):
            fx(hero, ctx, e)
        self.assertEqual(hero.armor_pool, 2)


class TestMerlinCards(unittest.TestCase):
    def test_arcane_damage_card(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("Arcane Bolt", sim.CardType.RANGED, 1, sim.Element.ARCANE)
        enemy = sim.Enemy("Dummy", 2, 5, sim.Element.ARCANE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertFalse(ctx["enemies"])  # vulnerability doubled damage

    def test_heal_effect(self):
        hero = sim.Hero("Hero", 10, [])
        hero.hp = 5
        heal = sim.atk("Heal", sim.CardType.UTIL, 0, effect=sim.heal(3))
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, heal, ctx)
        self.assertEqual(hero.hp, 8)

    def test_heal_capped(self):
        hero = sim.Hero("Hero", 10, [])
        hero.hp = 9
        heal = sim.atk("Heal", sim.CardType.UTIL, 0, effect=sim.heal(5))
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, heal, ctx)
        self.assertEqual(hero.hp, 10)

    def test_fate_for_bonus_damage(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 1
        buff = sim.atk("Buff", sim.CardType.UTIL, 0, effect=sim.fate_for_bonus(1, damage=2))
        attack = sim.atk("Strike", sim.CardType.MELEE, 1)
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, buff, ctx)
        self.assertEqual(hero.fate, 0)
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(enemy.hp, 0)

    def test_area_damage_spell(self):
        sim.RNG.seed(9)
        hero = sim.Hero("Hero", 10, [])
        card = sim.arcane_volley
        enemies = [
            sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
            for _ in range(3)
        ]
        ctx = {"enemies": enemies}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(ctx["enemies"]), 0)

    def test_ally_armor_support(self):
        hero1 = sim.Hero("H1", 10, [])
        hero2 = sim.Hero("H2", 10, [])
        card = sim.atk("Ward", sim.CardType.UTIL, 0, effect=sim.armor_allies(2))
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy], "heroes": [hero1, hero2]}
        sim.resolve_attack(hero1, card, ctx)
        self.assertEqual(hero1.armor_pool, 2)
        self.assertEqual(hero2.armor_pool, 2)


class TestBrynhildCards(unittest.TestCase):
    def test_hymn_shields_armor_cap(self):
        hero = sim.Hero("Hero", 10, [])
        card = sim.hymn_shields
        enemy = sim.Enemy("Dummy", 1, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        for fx, e in ctx.get("end_hooks", []):
            fx(hero, ctx, e)
        self.assertEqual(hero.armor_pool, 1)
        for _ in range(4):
            ctx["end_hooks"] = []
            sim.apply_persistent(hero, ctx)
            for fx, e in ctx.get("end_hooks", []):
                fx(hero, ctx, e)
        self.assertEqual(hero.armor_pool, 5)

    def test_valkyries_descent_hymn_bonus(self):
        hero = sim.Hero("Hero", 10, [])
        hymn = sim.atk("Prayer", sim.CardType.UTIL, 0, hymn=True, persistent="combat")
        enemy = sim.Enemy("Dummy", 3, 8, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, hymn, ctx)
        sim.resolve_attack(hero, sim.valkyrie_descent, ctx)
        self.assertEqual(enemy.hp, 2)

    def test_thrust_of_destiny_bonus(self):
        hero = sim.Hero("Hero", 10, [])
        hymns = [sim.atk("Prayer", sim.CardType.UTIL, 0, hymn=True, persistent="combat") for _ in range(3)]
        enemy = sim.Enemy("Dummy", 5, 8, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        for h in hymns:
            sim.resolve_attack(hero, h, ctx)
        sim.resolve_attack(hero, sim.thrust_of_destiny, ctx)
        self.assertEqual(enemy.hp, 2)

    def test_hymn_storms_effect(self):
        hero = sim.Hero("Hero", 10, [])
        extra = sim.atk("Prayer", sim.CardType.UTIL, 0, hymn=True, persistent="combat")
        enemy = sim.Enemy("Dummy", 7, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, extra, ctx)
        sim.resolve_attack(hero, sim.hymn_storms, ctx)
        self.assertEqual(ctx["hit_mod"], -1)
        for fx, e in ctx.get("end_hooks", []):
            fx(hero, ctx, e)
        self.assertEqual(enemy.hp, 1)

        next_enemy = sim.Enemy("Dummy", 6, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx2 = {"enemies": [next_enemy]}
        hero.exchange_effects.clear()
        hero.active_hymns = [h for h in hero.active_hymns if h.persistent == "combat"]
        sim.apply_persistent(hero, ctx2)
        self.assertEqual(ctx2["hit_mod"], -1)
        for fx, e in ctx2.get("end_hooks", []):
            fx(hero, ctx2, e)
        self.assertEqual(next_enemy.hp, 0)


class TestHerculesCards(unittest.TestCase):
    def test_pain_strike_hp_bonus(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 7, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, sim.pain_strike, ctx)
        self.assertLess(hero.hp, 10)
        self.assertFalse(ctx["enemies"])  # enemy defeated

    def test_ares_will_persistent(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        enemy = sim.Enemy("Dummy", 5, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, sim.ares_will, ctx)
        self.assertEqual(enemy.hp, 2)
        attack = sim.atk("Strike", sim.CardType.MELEE, 1)
        sim.resolve_attack(hero, attack, ctx)
        self.assertFalse(ctx["enemies"])  # extra HP loss killed enemy

    def test_bondless_effort_discard_bonus(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hero.deck.hand = [sim.atk("a", sim.CardType.UTIL, 0) for _ in range(2)]
        card = sim.atk("Bondless Effort", sim.CardType.MELEE, 0,
                       effect=sim.discard_bonus_damage(3))
        enemy = sim.Enemy("Dummy", 6, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 0)
        self.assertEqual(len(hero.deck.hand), 0)

    def test_bondless_effort_partial_discard(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hero.deck.hand = [sim.atk("a", sim.CardType.UTIL, 0) for _ in range(3)]
        card = sim.atk("Bondless Effort", sim.CardType.MELEE, 0,
                       effect=sim.discard_bonus_damage(3))
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(enemy.hp, 0)
        self.assertEqual(len(hero.deck.hand), 2)

    def test_pre_effect_kills_enemy(self):
        """Pre effects that kill should end the attack without errors."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hero.deck.hand = [sim.atk("a", sim.CardType.UTIL, 0)]
        card = sim.atk("Prep", sim.CardType.MELEE, 1,
                       effect=sim.discard_bonus_damage(3), pre=True)
        enemy = sim.Enemy("Dummy", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertFalse(ctx["enemies"])  # enemy defeated by pre effect

    def test_horde_breaker_death_trigger(self):
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        hb = sim.atk("Horde Breaker", sim.CardType.MELEE, 0,
                      effect=sim.horde_breaker_fx, persistent="combat")
        e1 = sim.Enemy("E1", 1, 1, sim.Element.NONE, [0, 0, 0, 0])
        e2 = sim.Enemy("E2", 3, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [e1, e2]}
        sim.resolve_attack(hero, hb, ctx)
        kill = sim.atk("Strike", sim.CardType.MELEE, 1)
        sim.resolve_attack(hero, kill, ctx)
        self.assertEqual(e2.hp, 1)

    def test_fortunes_throw_choice(self):
        hero = sim.Hero("Hero", 10, [])
        hero.fate = 0
        card = sim.atk("Fortune", sim.CardType.RANGED, 0,
                       effect=sim.fortunes_throw_fx)
        enemy = sim.Enemy("Dummy", 1, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.fate, 2)
        self.assertEqual(hero.armor_pool, 0)

    def test_fortunes_throw_armor_choice(self):
        hero = sim.Hero("Hero", 10, [])
        hero.fate = sim.FATE_MAX
        card = sim.atk("Fortune", sim.CardType.RANGED, 0,
                       effect=sim.fortunes_throw_fx)
        enemy = sim.Enemy("Dummy", 1, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(hero.fate, sim.FATE_MAX)
        self.assertEqual(hero.armor_pool, 2)

    def test_true_might_first_dice_attack_bonus(self):
        """True Might deals 8 bonus damage when played before any dice cards."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        card = sim.atk("True Might", sim.CardType.MELEE, 4, sim.Element.BRUTAL,
                       effect=sim.true_might_fx, pre=True)
        enemy = sim.Enemy("Dummy", 20, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, card, ctx)
        # four hits plus bonus 8 damage => 12 total
        self.assertEqual(enemy.hp, 8)

    def test_true_might_no_bonus_after_dice_card(self):
        """True Might bonus does not trigger if another dice card was played."""
        sim.RNG.seed(0)
        hero = sim.Hero("Hero", 10, [])
        first = sim.atk("Strike", sim.CardType.MELEE, 1)
        mighty = sim.atk("True Might", sim.CardType.MELEE, 4, sim.Element.BRUTAL,
                         effect=sim.true_might_fx, pre=True)
        enemy = sim.Enemy("Dummy", 20, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, first, ctx)
        sim.resolve_attack(hero, mighty, ctx)
        # first attack hits for 1, second for 5 with no bonus => total 6
        self.assertEqual(enemy.hp, 14)


class TestRepeatedAttackGuard(unittest.TestCase):
    def test_once_isnt_enough_triggers_repeat(self):
        hero = sim.Hero("Hero", 10, [])
        buff = sim.atk("Once", sim.CardType.UTIL, 0, effect=sim.once_isnt_enough_fx)
        attack = sim.atk("Jab", sim.CardType.MELEE, 0)
        enemy = sim.Enemy("Dummy", 5, 1, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        sim.resolve_attack(hero, buff, ctx)
        ctx["attacks_used"] = 0
        sim.resolve_attack(hero, attack, ctx)
        self.assertEqual(ctx["attacks_used"], 2)

    def test_hermes_delivery_depth_guard(self):
        hero = sim.Hero("Hero", 10, [])
        hermes = sim.atk("Hermes", sim.CardType.MELEE, 0,
                         effect=sim.hermes_delivery_fx)
        total = sim.ATTACK_DEPTH_LIMIT + 5
        hero.deck.cards = [hermes for _ in range(total)]
        enemy = sim.Enemy("Dummy", 20, 5, sim.Element.NONE, [0, 0, 0, 0])
        ctx = {"enemies": [enemy]}
        card = hero.deck.cards.pop()
        sim.resolve_attack(hero, card, ctx)
        self.assertEqual(len(hero.deck.disc), sim.ATTACK_DEPTH_LIMIT)
        self.assertEqual(len(hero.deck.cards), 5)

if __name__ == "__main__":
    unittest.main()
