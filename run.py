#!/usr/bin/env python3
"""Command-line entry point for the Market Data Toolkit.

Examples
    python3 run.py                      # default 10-company universe, 2y
    python3 run.py AAPL MSFT            # custom tickers
    python3 run.py --years 3           # custom window
    python3 run.py --no-rates          # skip FRED macro rates
    python3 run.py --no-credit-model   # data only, skip Merton/KMV
"""

from __future__ import annotations

import argparse
import logging
from typing import Optional, Sequence

from mdtoolkit import RunConfig, run
from mdtoolkit.config import DEFAULT_TICKERS, DEFAULT_YEARS


def parse_args(argv: Optional[Sequence[str]] = None) -> RunConfig:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("tickers", nargs="*", help="Ticker symbols (default: built-in universe)")
    p.add_argument("--years", type=int, default=DEFAULT_YEARS,
                   help=f"History/financials window in years (default {DEFAULT_YEARS})")
    p.add_argument("--no-rates", action="store_true", help="Skip FRED macro-rate download")
    p.add_argument("--no-credit-model", action="store_true",
                   help="Skip the Merton/KMV credit model")
    args = p.parse_args(argv)
    tickers = [t.upper() for t in args.tickers] or list(DEFAULT_TICKERS)
    return RunConfig(tickers=tickers, years=args.years,
                     include_rates=not args.no_rates,
                     run_credit_model=not args.no_credit_model)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )
    run(parse_args())


if __name__ == "__main__":
    main()
