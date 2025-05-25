import unittest
import random
from collections import defaultdict
from unittest.mock import patch
import dark_game_sim as dgs

class TestEndOfRoundSpawning(unittest.TestCase):
    def test_monsters_spawn_from_all_rifts(self):
        dgs.board = defaultdict(list)
        dgs.board[5].append(dgs.Spot('R'))
        with patch('dark_game_sim.random.sample', return_value=[6]), \
             patch('dark_game_sim.random.random', return_value=0.0), \
             patch('dark_game_sim.random.choice', side_effect=[1, 2]):
            dgs.spawn_end_of_round(1)
        rift_locs = [loc for loc, spots in dgs.board.items() if any(s.t == 'R' for s in spots)]
        mons_at = [loc for loc, spots in dgs.board.items() if any(s.t == 'M' for s in spots)]
        self.assertCountEqual(rift_locs, [5, 6])
        self.assertCountEqual(mons_at, [1, 2])

class TestPlayGameDoom(unittest.TestCase):
    def test_doom_before_spawning(self):
        random.seed(0)
        def fake_spawn_end_of_round(rnd, verbose=False):
            dgs.board[1].append(dgs.Spot('M'))
        with patch.object(dgs, 'HERO_SPEED', 0), \
             patch.object(dgs, 'TOTAL_ROUNDS', 3), \
             patch('dark_game_sim.spawn_end_of_round', side_effect=fake_spawn_end_of_round):
            res = dgs.play_game(return_loss_detail=True)
        self.assertEqual(res['end_mons'], 4)
        self.assertEqual(res['end_doom'], 5)

if __name__ == '__main__':
    unittest.main()
