import unittest
from game import (
    Hero,
    create_samurai_deck,
    EnemyOni,
    EnemySamurai,
    apply_enemy_attack,
    apply_hero_card,
    resolve_turn,
    OniPatternDeck,
    SamuraiPatternDeck,
)

DEFAULT_ORDER = list(range(1, 13))

class TestGameMechanics(unittest.TestCase):
    def test_card_play_reduces_stamina_and_enters_cooldown(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        card = hero.hand[0]
        prev_stamina = hero.stamina
        played = hero.play_card(card.id)
        self.assertEqual(hero.stamina, prev_stamina - card.stamina)
        self.assertNotIn(played, hero.hand)
        self.assertIn(played, hero.cooldown[0])

    def test_stamina_refresh_and_cooldown_progression(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        card = hero.play_card(hero.hand[0].id)
        hero.end_round()
        self.assertEqual(hero.stamina, hero.max_stamina)
        self.assertIn(card, hero.cooldown[1])
        hero.end_round()
        # card should be returned to deck and cooldown cleared
        self.assertNotIn(card, hero.cooldown[0])
        self.assertNotIn(card, hero.cooldown[1])
        self.assertIs(hero.deck.cards[-1], card)

    def test_cannot_play_card_without_enough_stamina(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        card = hero.hand[1]
        hero.stamina = 0
        with self.assertRaises(ValueError):
            hero.play_card(card.id)

    def test_enemy_deck_loops(self):
        enemy = EnemyOni()
        first = enemy.telegraph()
        for _ in range(len(enemy.pattern)):
            enemy.advance()
        self.assertEqual(enemy.telegraph(), first)

    def test_rage_roar_drains_stamina(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[2]  # Rage Roar
        prev = hero.stamina
        apply_enemy_attack(hero, hero.hand[0], atk, False, enemy)
        self.assertEqual(hero.stamina, max(0, prev - 1))

    def test_double_swipe_hits_twice(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[3]  # Double Swipe
        hero_card = hero.hand[0]
        hp_before = hero.hp
        apply_enemy_attack(hero, hero_card, atk, False, enemy)
        expected = hp_before - ((atk.damage - hero.armor) * 2)
        self.assertEqual(hero.hp, expected)

    def test_leap_crush_area_on_target(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[1]  # Leap Crush
        hp_before = hero.hp
        apply_enemy_attack(hero, hero.hand[0], atk, False, enemy)
        expected = hp_before - (atk.damage - hero.armor)
        self.assertEqual(hero.hp, expected)

    def test_recuperate_buffs_next_attack(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        recup = OniPatternDeck[5]
        swing = OniPatternDeck[0]
        apply_enemy_attack(hero, hero.hand[0], recup, False, enemy)
        self.assertEqual(enemy.next_damage_bonus, 1)
        hp_before = hero.hp
        apply_enemy_attack(hero, hero.hand[0], swing, False, enemy)
        self.assertEqual(enemy.next_damage_bonus, 0)
        dmg = (swing.damage + 1 - hero.armor)
        self.assertEqual(hero.hp, hp_before - dmg)

    def test_parry_counter_and_focused_stare(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemySamurai()
        parry_counter = SamuraiPatternDeck[3]
        stare = SamuraiPatternDeck[5]
        strike = SamuraiPatternDeck[4]
        apply_enemy_attack(hero, hero.hand[0], parry_counter, False, enemy)
        self.assertEqual(enemy.next_damage_bonus, 4)
        apply_enemy_attack(hero, hero.hand[0], stare, False, enemy)
        self.assertEqual(enemy.index, 0)
        hp_before = hero.hp
        apply_enemy_attack(hero, hero.hand[0], strike, False, enemy)
        expected_dmg = strike.damage + 4 - hero.armor
        self.assertEqual(hero.hp, hp_before - expected_dmg)

    def test_ki_focus_refreshes_cooldown(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()

        used = hero.play_card(hero.hand[0].id)
        self.assertIn(used, hero.cooldown[0])

        hero.draw(4)  # bring Ki Focus (id 8) into hand
        ki_focus = hero.play_card(8)
        apply_hero_card(hero, enemy, ki_focus)

        self.assertNotIn(used, hero.cooldown[0])
        self.assertIs(hero.deck.cards[-1], used)
        self.assertIn(ki_focus, hero.cooldown[0])

    def test_parry_counter_buff_applied_then_used(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemySamurai()

        parry_counter = SamuraiPatternDeck[3]
        strike = SamuraiPatternDeck[4]

        apply_enemy_attack(hero, hero.hand[0], parry_counter, False, enemy)
        self.assertEqual(enemy.next_damage_bonus, 4)

        hp_before = hero.hp
        apply_enemy_attack(hero, hero.hand[0], strike, False, enemy)
        expected_dmg = strike.damage + 4 - hero.armor
        self.assertEqual(hero.hp, hp_before - expected_dmg)
        self.assertEqual(enemy.next_damage_bonus, 0)

    def test_riposte_grants_and_consumes_heavy_bonus(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()

        riposte = next(c for c in hero.hand if c.id == 2)
        atk = OniPatternDeck[3]  # Double Swipe speed 2

        apply_enemy_attack(hero, riposte, atk, True, enemy)
        self.assertEqual(hero.heavy_bonus, 2)

        heavy = hero.deck.card(5)
        hp_before = enemy.hp
        apply_hero_card(hero, enemy, heavy)

        self.assertEqual(enemy.hp, hp_before - 7)
        self.assertEqual(hero.heavy_bonus, 0)

    def test_cross_step_fails_if_still_in_area(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[3]  # Double Swipe 180 deg front arc
        card = next(c for c in hero.hand if c.id == 3)
        resolve_turn(hero, enemy, card, atk)
        self.assertEqual(hero.position.as_tuple(), (-1, 1))
        expected_hp = 15 - ((atk.damage - hero.armor) * 2)
        self.assertEqual(hero.hp, expected_hp)

    def test_cross_step_moves_and_dodges(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[0]  # Club Sweep 90 deg front arc speed 2
        card = next(c for c in hero.hand if c.id == 3)
        resolve_turn(hero, enemy, card, atk)
        # After cross-step hero should have moved left and dodged attack
        self.assertEqual(hero.position.as_tuple(), (-1, 1))
        self.assertEqual(hero.hp, 15)

    def test_shadow_step_teleports_and_dodges(self):
        deck = create_samurai_deck(DEFAULT_ORDER)
        hero = Hero(deck)
        enemy = EnemyOni()
        atk = OniPatternDeck[3]  # Double Swipe 180 deg front arc speed 2
        # Ensure shadow step card is drawn; it is card 9 not in starting hand so draw more
        hero.draw(5)  # draw remaining cards until we get card 9
        card = next(c for c in hero.hand if c.id == 9)
        resolve_turn(hero, enemy, card, atk)
        self.assertEqual(hero.position.as_tuple(), (-1, -1))
        self.assertEqual(hero.hp, 15)

if __name__ == '__main__':
    unittest.main()
