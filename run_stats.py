#!/usr/bin/env python3
"""Run the full statistics report for the card game simulator.

Running this module executes :func:`stats_runner.generate_report` with a
default of 50,000 simulated runs.  The number of runs may be overridden via
the ``--runs`` command line argument.
"""

import argparse
import stats_runner


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gauntlet statistics")
    parser.add_argument(
        "--runs", type=int, default=50000,
        help="Number of gauntlet runs to simulate")
    parser.add_argument(
        "--progress", action="store_true",
        help="Display simulation progress")
    parser.add_argument(
        "--timeout", type=float, default=60.0,
        help="Maximum seconds to allow per gauntlet run")
    args = parser.parse_args()

    report = stats_runner.generate_report(num_runs=args.runs,
                                          progress=args.progress,
                                          timeout=args.timeout)
    print(report)


if __name__ == "__main__":
    main()
