import unittest

from benchmark import run_benchmark
from battleship import CellState, HeadlessMatch, Pal17Engine, PlayerEngine, ShotView


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


class RecordingEngine(PlayerEngine):
    name = "Recording"

    def __init__(self):
        self.views = []

    def choose_shot(self, view):
        self.views.append(view)
        return view.available_targets()[0]


class HeadlessMatchTests(unittest.TestCase):
    def test_headless_match_finishes_without_ui(self):
        result = HeadlessMatch(
            rows=5,
            cols=5,
            fleet=[3, 2],
            engine_a=Pal17Engine(seed=1),
            engine_b=Pal17Engine(seed=2),
            first_player="a",
            seed=3,
        ).play()

        self.assertIn(result.winner, {"a", "b"})
        self.assertGreater(result.winner_shots, 0)
        self.assertEqual(result.total_shots, result.winner_shots + result.loser_shots)

    def test_engines_only_receive_public_shot_view(self):
        engine_a = RecordingEngine()
        engine_b = RecordingEngine()

        HeadlessMatch(
            rows=5,
            cols=5,
            fleet=[3, 2],
            engine_a=engine_a,
            engine_b=engine_b,
            first_player="a",
            seed=4,
        ).play()

        self.assertTrue(engine_a.views)
        self.assertTrue(engine_b.views)
        for view in engine_a.views + engine_b.views:
            self.assertIsInstance(view, ShotView)
            self.assertFalse(hasattr(view, "ship_grid"))
            self.assertFalse(hasattr(view, "ships"))

    def test_benchmark_alternates_first_player(self):
        first_players = []

        run_benchmark(
            games=4,
            rows=5,
            cols=5,
            fleet=[3, 2],
            engine_a_name="random",
            engine_b_name="random",
            seed=5,
            start_policy="alternate",
            result_hook=lambda result: first_players.append(result.first_player),
        )

        self.assertEqual(first_players, ["a", "b", "a", "b"])

    def test_benchmark_seed_is_reproducible(self):
        first = run_benchmark(
            games=5,
            rows=5,
            cols=5,
            fleet=[3, 2],
            engine_a_name="pal17",
            engine_b_name="random",
            seed=6,
            start_policy="alternate",
        )
        second = run_benchmark(
            games=5,
            rows=5,
            cols=5,
            fleet=[3, 2],
            engine_a_name="pal17",
            engine_b_name="random",
            seed=6,
            start_policy="alternate",
        )

        self.assertEqual(first.wins, second.wins)
        self.assertEqual(first.winner_shots, second.winner_shots)


if __name__ == "__main__":
    unittest.main()
