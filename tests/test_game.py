import unittest
from game import (
    Hero,
    create_samurai_deck,
    EnemyOni,
    EnemySamurai,
    apply_enemy_attack,
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

if __name__ == '__main__':
    unittest.main()
