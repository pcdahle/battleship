import unittest

from battleship import CellState, Pal17Engine, ShotView


def make_view(rows, cols, states=None):
    shots = [
        [CellState.UNKNOWN for _col in range(cols)]
        for _row in range(rows)
    ]
    for coord, state in (states or {}).items():
        row, col = coord
        shots[row][col] = state
    return ShotView(rows, cols, shots)


class Pal17EngineTests(unittest.TestCase):
    def test_unknown_targets_start_at_zero(self):
        view = make_view(3, 3)

        scores = Pal17Engine(seed=1).score_targets(view)

        self.assertEqual(set(scores.values()), {0})
        self.assertEqual(len(scores), 9)

    def test_single_unsunk_hit_scores_orthogonal_unknown_neighbors_as_ten(self):
        view = make_view(3, 3, {(1, 1): CellState.HIT})

        scores = Pal17Engine(seed=1).score_targets(view)

        self.assertEqual(scores[(0, 1)], 10)
        self.assertEqual(scores[(1, 0)], 10)
        self.assertEqual(scores[(1, 2)], 10)
        self.assertEqual(scores[(2, 1)], 10)
        self.assertEqual(scores[(0, 0)], 0)

    def test_contiguous_line_of_hits_scores_open_ends_as_twenty(self):
        view = make_view(5, 5, {(2, 1): CellState.HIT, (2, 2): CellState.HIT})

        scores = Pal17Engine(seed=1).score_targets(view)

        self.assertEqual(scores[(2, 0)], 20)
        self.assertEqual(scores[(2, 3)], 20)
        self.assertEqual(scores[(1, 1)], 0)
        self.assertEqual(scores[(3, 2)], 0)

    def test_targets_touching_sunk_ship_are_not_allowed(self):
        view = make_view(4, 4, {(1, 1): CellState.SUNK})

        scores = Pal17Engine(seed=1).score_targets(view)

        self.assertNotIn((0, 0), scores)
        self.assertNotIn((0, 1), scores)
        self.assertNotIn((1, 0), scores)
        self.assertIn((3, 3), scores)


if __name__ == "__main__":
    unittest.main()
