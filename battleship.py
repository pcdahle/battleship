from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


Coord = tuple[int, int]


class CellState(Enum):
    UNKNOWN = "unknown"
    MISS = "miss"
    HIT = "hit"
    SUNK = "sunk"


@dataclass(frozen=True)
class Ship:
    ship_id: int
    length: int
    cells: tuple[Coord, ...]


@dataclass(frozen=True)
class ShotResult:
    row: int
    col: int
    hit: bool
    sunk_ship_id: int | None
    sunk_cells: tuple[Coord, ...]
    already_tried: bool = False

    @property
    def sunk(self) -> bool:
        return self.sunk_ship_id is not None


class ShotView:
    """Read-only information an engine may use when choosing its next shot."""

    def __init__(self, rows: int, cols: int, shots: list[list[CellState]]):
        self.rows = rows
        self.cols = cols
        self._shots = shots

    def state_at(self, row: int, col: int) -> CellState:
        return self._shots[row][col]

    def available_targets(self) -> list[Coord]:
        return [
            (row, col)
            for row in range(self.rows)
            for col in range(self.cols)
            if self._shots[row][col] == CellState.UNKNOWN
        ]


class Board:
    def __init__(
        self,
        rows: int = 10,
        cols: int = 10,
        fleet: Iterable[int] = (5, 4, 4, 3, 3, 3, 3, 3),
        seed: int | None = None,
    ):
        if not (1 <= rows <= 100 and 1 <= cols <= 100):
            raise ValueError("rows and cols must be between 1 and 100")

        self.rows = rows
        self.cols = cols
        self.fleet = list(fleet)
        self.rng = random.Random(seed)
        self.ship_grid: list[list[int | None]] = [
            [None for _ in range(cols)] for _ in range(rows)
        ]
        self.shots: list[list[CellState]] = [
            [CellState.UNKNOWN for _ in range(cols)] for _ in range(rows)
        ]
        self.ships: dict[int, Ship] = {}
        self._hits_by_ship: dict[int, set[Coord]] = {}

        fleet_longest_first = sorted(self.fleet, reverse=True)
        if not self._place_fleet(fleet_longest_first):
            raise ValueError("Could not place the requested fleet on this board.")

    def public_view(self) -> ShotView:
        return ShotView(self.rows, self.cols, self.shots)

    def all_ships_sunk(self) -> bool:
        return all(len(self._hits_by_ship[ship_id]) == ship.length for ship_id, ship in self.ships.items())

    def receive_shot(self, row: int, col: int) -> ShotResult:
        if not self.in_bounds(row, col):
            raise ValueError(f"Shot outside board: {(row, col)}")

        previous = self.shots[row][col]
        if previous != CellState.UNKNOWN:
            return ShotResult(row, col, previous in (CellState.HIT, CellState.SUNK), None, (), True)

        ship_id = self.ship_grid[row][col]
        if ship_id is None:
            self.shots[row][col] = CellState.MISS
            return ShotResult(row, col, False, None, ())

        self.shots[row][col] = CellState.HIT
        self._hits_by_ship[ship_id].add((row, col))
        ship = self.ships[ship_id]

        if len(self._hits_by_ship[ship_id]) == ship.length:
            for ship_row, ship_col in ship.cells:
                self.shots[ship_row][ship_col] = CellState.SUNK
            return ShotResult(row, col, True, ship_id, ship.cells)

        return ShotResult(row, col, True, None, ())

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _place_fleet(self, remaining: list[int], next_ship_id: int = 1) -> bool:
        if not remaining:
            return True

        length = remaining[0]
        candidates = self._candidate_placements(length)
        self.rng.shuffle(candidates)

        for cells in candidates:
            if not self._can_place(cells):
                continue

            self._place_ship(next_ship_id, cells)
            if self._place_fleet(remaining[1:], next_ship_id + 1):
                return True
            self._remove_ship(next_ship_id)

        return False

    def _candidate_placements(self, length: int) -> list[tuple[Coord, ...]]:
        candidates: list[tuple[Coord, ...]] = []
        for row in range(self.rows):
            for col in range(self.cols):
                if col + length <= self.cols:
                    candidates.append(tuple((row, col + offset) for offset in range(length)))
                if row + length <= self.rows:
                    candidates.append(tuple((row + offset, col) for offset in range(length)))
        return candidates

    def _can_place(self, cells: tuple[Coord, ...]) -> bool:
        for row, col in cells:
            if self.ship_grid[row][col] is not None:
                return False
            for neighbor_row in range(row - 1, row + 2):
                for neighbor_col in range(col - 1, col + 2):
                    if self.in_bounds(neighbor_row, neighbor_col):
                        if self.ship_grid[neighbor_row][neighbor_col] is not None:
                            return False
        return True

    def _place_ship(self, ship_id: int, cells: tuple[Coord, ...]) -> None:
        ship = Ship(ship_id=ship_id, length=len(cells), cells=cells)
        self.ships[ship_id] = ship
        self._hits_by_ship[ship_id] = set()
        for row, col in cells:
            self.ship_grid[row][col] = ship_id

    def _remove_ship(self, ship_id: int) -> None:
        ship = self.ships.pop(ship_id)
        self._hits_by_ship.pop(ship_id)
        for row, col in ship.cells:
            self.ship_grid[row][col] = None


class PlayerEngine:
    """Interface for computer players.

    Implement choose_shot(view) in subclasses. The UI and game controller never
    need to know how the engine picks a coordinate.
    """

    name = "Engine"

    def new_game(self, rows: int, cols: int, fleet: list[int]) -> None:
        pass

    def choose_shot(self, view: ShotView) -> Coord:
        raise NotImplementedError

    def observe_result(self, result: ShotResult, view: ShotView) -> None:
        pass


class RandomEngine(PlayerEngine):
    name = "Random"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_shot(self, view: ShotView) -> Coord:
        targets = view.available_targets()
        if not targets:
            raise RuntimeError("No available targets left.")
        return self.rng.choice(targets)


class Pal17Engine(PlayerEngine):
    name = "Pal17"

    ORTHOGONAL_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_shot(self, view: ShotView) -> Coord:
        scores = self.score_targets(view)
        if not scores:
            raise RuntimeError("No available targets left.")
        best_score = max(scores.values())
        best_targets = [
            coord for coord, score in scores.items()
            if score == best_score
        ]
        return self.rng.choice(best_targets)

    def score_targets(self, view: ShotView) -> dict[Coord, int]:
        scores = {
            coord: 0
            for coord in view.available_targets()
            if self._is_allowed_target(view, coord)
        }

        for component in self._hit_components(view):
            if len(component) == 1:
                self._score_single_hit_extensions(view, scores, component[0])
            else:
                self._score_line_extensions(view, scores, component)

        return scores

    def _score_single_hit_extensions(
        self,
        view: ShotView,
        scores: dict[Coord, int],
        hit: Coord,
    ) -> None:
        row, col = hit
        for row_delta, col_delta in self.ORTHOGONAL_DIRECTIONS:
            coord = (row + row_delta, col + col_delta)
            if coord in scores:
                scores[coord] = max(scores[coord], 10)

    def _score_line_extensions(
        self,
        view: ShotView,
        scores: dict[Coord, int],
        component: list[Coord],
    ) -> None:
        rows = {row for row, _col in component}
        cols = {col for _row, col in component}

        if len(rows) == 1:
            row = next(iter(rows))
            line_cols = sorted(cols)
            if self._is_contiguous(line_cols):
                for coord in ((row, line_cols[0] - 1), (row, line_cols[-1] + 1)):
                    if coord in scores:
                        scores[coord] = max(scores[coord], 20)
            return

        if len(cols) == 1:
            col = next(iter(cols))
            line_rows = sorted(rows)
            if self._is_contiguous(line_rows):
                for coord in ((line_rows[0] - 1, col), (line_rows[-1] + 1, col)):
                    if coord in scores:
                        scores[coord] = max(scores[coord], 20)

    def _hit_components(self, view: ShotView) -> list[list[Coord]]:
        remaining = {
            (row, col)
            for row in range(view.rows)
            for col in range(view.cols)
            if view.state_at(row, col) == CellState.HIT
        }
        components: list[list[Coord]] = []

        while remaining:
            start = remaining.pop()
            stack = [start]
            component = [start]

            while stack:
                row, col = stack.pop()
                for row_delta, col_delta in self.ORTHOGONAL_DIRECTIONS:
                    neighbor = (row + row_delta, col + col_delta)
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        stack.append(neighbor)
                        component.append(neighbor)

            components.append(component)

        return components

    def _is_allowed_target(self, view: ShotView, coord: Coord) -> bool:
        row, col = coord
        if not (0 <= row < view.rows and 0 <= col < view.cols):
            return False
        if view.state_at(row, col) != CellState.UNKNOWN:
            return False

        for neighbor_row in range(row - 1, row + 2):
            for neighbor_col in range(col - 1, col + 2):
                if 0 <= neighbor_row < view.rows and 0 <= neighbor_col < view.cols:
                    if view.state_at(neighbor_row, neighbor_col) == CellState.SUNK:
                        return False

        return True

    def _is_contiguous(self, values: list[int]) -> bool:
        return all(
            current + 1 == next_value
            for current, next_value in zip(values, values[1:])
        )
