#!/usr/bin/env python3
"""Run the full statistics report for the card game simulator.

Running this module executes :func:`stats_runner.generate_report` with a
default of 50,000 simulated runs.  The number of runs may be overridden via
the ``--runs`` command line argument.  Additional options are available to
limit retries and exchanges per wave.
"""

import argparse

import stats_runner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gauntlet statistics")
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
