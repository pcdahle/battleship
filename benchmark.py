from __future__ import annotations

import argparse
import random
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from battleship import HeadlessMatch, MatchResult, Pal17Engine, PlayerEngine, RandomEngine


DEFAULT_FLEET = (5, 4, 4, 3, 3, 3, 3, 3)
ENGINE_TYPES: dict[str, type[PlayerEngine]] = {
    "random": RandomEngine,
    "pal17": Pal17Engine,
}


@dataclass(frozen=True)
class BenchmarkSummary:
    games: int
    wins: Counter[str]
    winner_shots: list[int]
    elapsed_seconds: float

    @property
    def games_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return float("inf")
        return self.games / self.elapsed_seconds


def parse_fleet(value: str) -> list[int]:
    fleet = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not fleet or any(length <= 0 for length in fleet):
        raise argparse.ArgumentTypeError("fleet must be a comma-separated list of positive integers")
    return fleet


def percentile(sorted_values: list[int], percent: float) -> float:
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    position = (len(sorted_values) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def create_engine(engine_name: str, seed: int) -> PlayerEngine:
    try:
        engine_type = ENGINE_TYPES[engine_name]
    except KeyError as exc:
        choices = ", ".join(sorted(ENGINE_TYPES))
        raise ValueError(f"unknown engine '{engine_name}'. Choose one of: {choices}") from exc
    return engine_type(seed=seed)


def run_benchmark(
    games: int,
    rows: int,
    cols: int,
    fleet: list[int],
    engine_a_name: str,
    engine_b_name: str,
    seed: int | None,
    start_policy: str,
    result_hook: Callable[[MatchResult], None] | None = None,
    progress_every: int = 0,
) -> BenchmarkSummary:
    if games <= 0:
        raise ValueError("games must be greater than zero")

    rng = random.Random(seed)
    wins: Counter[str] = Counter()
    winner_shots: list[int] = []
    started = time.perf_counter()

    for game_index in range(games):
        if start_policy == "alternate":
            first_player = "a" if game_index % 2 == 0 else "b"
        elif start_policy == "random":
            first_player = rng.choice(("a", "b"))
        else:
            first_player = "a"

        match_seed = rng.randrange(2**32)
        engine_a = create_engine(engine_a_name, rng.randrange(2**32))
        engine_b = create_engine(engine_b_name, rng.randrange(2**32))
        match = HeadlessMatch(
            rows=rows,
            cols=cols,
            fleet=fleet,
            engine_a=engine_a,
            engine_b=engine_b,
            first_player=first_player,
            seed=match_seed,
        )
        result = match.play()
        wins[result.winner] += 1
        winner_shots.append(result.winner_shots)
        if result_hook:
            result_hook(result)
        games_played = game_index + 1
        if progress_every > 0 and games_played % progress_every == 0:
            mean_shots = statistics.fmean(winner_shots)
            print(
                f"Progress: {games_played}/{games} games, "
                f"mean winner shots: {mean_shots:.2f}",
                flush=True,
            )

    elapsed = time.perf_counter() - started
    return BenchmarkSummary(
        games=games,
        wins=wins,
        winner_shots=winner_shots,
        elapsed_seconds=elapsed,
    )


def format_summary(summary: BenchmarkSummary, engine_a_name: str, engine_b_name: str) -> str:
    shots = summary.winner_shots
    sorted_shots = sorted(shots)
    stdev = statistics.pstdev(shots) if len(shots) > 1 else 0.0

    return "\n".join(
        [
            f"Games: {summary.games}",
            f"Engine A ({engine_a_name}) wins: {summary.wins['a']}",
            f"Engine B ({engine_b_name}) wins: {summary.wins['b']}",
            "Winner shots:",
            f"  mean: {statistics.fmean(shots):.2f}",
            f"  median: {statistics.median(shots):.0f}",
            f"  min: {min(shots)}",
            f"  max: {max(shots)}",
            f"  stdev: {stdev:.2f}",
            f"  p10: {percentile(sorted_shots, 10):.2f}",
            f"  p90: {percentile(sorted_shots, 90):.2f}",
            f"Elapsed: {summary.elapsed_seconds:.3f}s",
            f"Throughput: {summary.games_per_second:.1f} games/s",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run headless Battleship engine benchmarks.")
    parser.add_argument("--games", type=int, default=1000)
    parser.add_argument("--engine-a", choices=sorted(ENGINE_TYPES), default="pal17")
    parser.add_argument("--engine-b", choices=sorted(ENGINE_TYPES), default="random")
    parser.add_argument("--rows", type=int, default=10)
    parser.add_argument("--cols", type=int, default=10)
    parser.add_argument("--fleet", type=parse_fleet, default=list(DEFAULT_FLEET))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print running mean after this many games. Use 0 to disable.",
    )
    parser.add_argument(
        "--start-policy",
        choices=("alternate", "random", "a"),
        default="alternate",
        help="Who starts each game. Alternate avoids first-move bias in same-engine matches.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_benchmark(
        games=args.games,
        rows=args.rows,
        cols=args.cols,
        fleet=args.fleet,
        engine_a_name=args.engine_a,
        engine_b_name=args.engine_b,
        seed=args.seed,
        start_policy=args.start_policy,
        progress_every=args.progress_every,
    )
    print(format_summary(summary, args.engine_a, args.engine_b))


if __name__ == "__main__":
    main()
