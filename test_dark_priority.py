import unittest
from dark_game_sim import Spot, compute_priority, get_candidates, CLUSTER_MAJOR

class TestDarkGamePriority(unittest.TestCase):
    def setUp(self):
        self.board = {}
        self.dark_map = {c: False for c in CLUSTER_MAJOR}

    def test_priority_dark(self):
        # 5 dark majors triggers dark priority
        for cl in list(CLUSTER_MAJOR.keys())[:5]:
            self.dark_map[cl] = True
        p = compute_priority(5, 0, 0)
        self.assertEqual(p, 'D')
        cands = get_candidates(self.board, self.dark_map, p)
        expected = [CLUSTER_MAJOR[cl] for cl in list(CLUSTER_MAJOR.keys())[:5]]
        self.assertEqual(cands, expected)

    def test_priority_rifts(self):
        # 7 rifts triggers rift priority
        for i in range(1, 8):
            self.board[i] = [Spot('R')]
        p = compute_priority(0, 7, 0)
        self.assertEqual(p, 'R')
        cands = get_candidates(self.board, self.dark_map, p)
        self.assertEqual(cands, list(range(1, 8)))

    def test_priority_monsters(self):
        # 5 monsters triggers monster priority
        for i in range(1, 6):
            self.board[i] = [Spot('M')]
        p = compute_priority(0, 0, 5)
        self.assertEqual(p, 'M')
        cands = get_candidates(self.board, self.dark_map, p)
        self.assertEqual(cands, list(range(1, 6)))

if __name__ == '__main__':
    unittest.main()
