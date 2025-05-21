#!/usr/bin/env python3
"""Command line interface for stats_runner.generate_report."""

import argparse
import stats_runner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gauntlet statistics")
    parser.add_argument(
        "--runs", type=int, default=50000,
        help="Number of gauntlet runs to simulate")
    args = parser.parse_args()

    report = stats_runner.generate_report(num_runs=args.runs)
    print(report)


if __name__ == "__main__":
    main()
