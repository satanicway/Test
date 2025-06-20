import io
import unittest
from unittest.mock import patch

import game

class TestBattleOutcome(unittest.TestCase):
    def test_battle_player_victory_message(self):
        def dummy_enemy():
            e = game.EnemyOni()
            e.hp = 0
            return e

        with patch('game.prompt_deck_order', return_value=list(range(1, 13))), \
             patch('game.choose_enemy', dummy_enemy), \
             patch('sys.stdout', new_callable=io.StringIO) as fake_out:
            game.battle()
            output = fake_out.getvalue()

        self.assertIn('You defeated the', output)
        self.assertIn('Battle ended.', output)

    def test_battle_player_defeat_message(self):
        class DummyHero(game.Hero):
            def __init__(self, deck):
                super().__init__(deck)
                self.hp = 0

        with patch('game.Hero', DummyHero), \
             patch('game.prompt_deck_order', return_value=list(range(1, 13))), \
             patch('sys.stdout', new_callable=io.StringIO) as fake_out:
            # enemy will be created normally
            with patch('game.choose_enemy', return_value=game.EnemyOni()):
                game.battle()
            output = fake_out.getvalue()

        self.assertIn('You were defeated.', output)
        self.assertIn('Battle ended.', output)

if __name__ == '__main__':
    unittest.main()
