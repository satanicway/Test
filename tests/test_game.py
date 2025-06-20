import unittest
from game import Hero, create_samurai_deck, EnemyOni

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

if __name__ == '__main__':
    unittest.main()
