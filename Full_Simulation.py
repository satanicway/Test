#!/usr/bin/env python3
"""Unified simulation entry point for the card game."""

import argparse

import stats_runner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full board game simulation statistics"
    )
    parser.add_argument(
        "--runs", type=int, default=50000, help="Number of gauntlet runs to simulate"
    )
    parser.add_argument(
        "--progress", action="store_true", help="Display simulation progress"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Maximum seconds to allow per gauntlet run",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Number of consecutive timeouts to tolerate before aborting",
    )
    parser.add_argument(
        "--max-exchanges",
        type=int,
        default=1000,
        help="Abort a wave after this many exchanges",
    )
    args = parser.parse_args()

    report = stats_runner.generate_report(
        num_runs=args.runs,
        progress=args.progress,
        timeout=args.timeout,
        max_retries=args.max_retries,
        max_exchanges=args.max_exchanges,
    )
    print(report)


if __name__ == "__main__":
    main()
