#!/usr/bin/env python3
"""Unified simulation entry point for the card game."""

import argparse
import stats_runner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full board game simulation statistics")
    parser.add_argument(
        "--runs", type=int, default=50000,
        help="Number of gauntlet runs to simulate")
    parser.add_argument(
        "--progress", action="store_true",
        help="Display simulation progress")
    args = parser.parse_args()

    report = stats_runner.generate_report(num_runs=args.runs, progress=args.progress)
    print(report)


if __name__ == "__main__":
    main()

