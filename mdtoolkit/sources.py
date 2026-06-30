"""Data-source adapters: Yahoo Finance (equities) and FRED (macro rates).

This layer is the only place that talks to the network. It returns plain
pandas objects so the rest of the pipeline is testable without I/O.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from io import StringIO
from typing import Callable, Optional

import pandas as pd
import requests
import yfinance as yf

from . import config

LOG = logging.getLogger("mdtoolkit.sources")


# --------------------------------------------------------------------------- #
# Resilience: retry Yahoo calls with exponential backoff
# --------------------------------------------------------------------------- #
def with_retry(label: str) -> Callable:
    """Decorate a network call to retry with exponential backoff."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, config.MAX_RETRIES + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentional broad catch
                    last_exc = exc
                    wait = config.BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
                    LOG.warning("%s failed (attempt %d/%d): %s -- retry in %.0fs",
                                label, attempt, config.MAX_RETRIES, exc, wait)
                    time.sleep(wait)
            LOG.error("%s permanently failed: %s", label, last_exc)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# --------------------------------------------------------------------------- #
# Yahoo Finance (equities)
# --------------------------------------------------------------------------- #
@with_retry("Ticker.info")
def get_info(tk: yf.Ticker) -> dict:
    return tk.info or {}


@with_retry("Ticker.history")
def get_history(tk: yf.Ticker, start: datetime) -> pd.DataFrame:
    """Daily OHLC + Adj Close + dividend/split actions from `start` onward."""
    return tk.history(start=start.strftime("%Y-%m-%d"),
                      auto_adjust=False, actions=True)


@with_retry("Ticker.statements")
def get_statements(tk: yf.Ticker) -> dict[str, pd.DataFrame]:
    """Quarterly and annual income, balance-sheet, and cash-flow statements."""
    return {
        "q_income": tk.quarterly_income_stmt,
        "q_balance": tk.quarterly_balance_sheet,
        "q_cashflow": tk.quarterly_cashflow,
        "a_income": tk.income_stmt,
        "a_balance": tk.balance_sheet,
        "a_cashflow": tk.cashflow,
    }


# --------------------------------------------------------------------------- #
# FRED (macro rates) -- official CSV API, no key required
# --------------------------------------------------------------------------- #
def fetch_fred_series(series_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Download one FRED series as a tidy [Date, <series_id>] frame."""
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start:%Y-%m-%d}&coed={end:%Y-%m-%d}"
    )
    resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    date_col = df.columns[0]  # 'observation_date' or 'DATE'
    df = df.rename(columns={date_col: "Date"})
    df["Date"] = pd.to_datetime(df["Date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df.dropna(subset=[series_id]).reset_index(drop=True)


def fetch_rates(years: int) -> pd.DataFrame:
    """Combined daily frame of all configured FRED series, columns = series ids."""
    end = datetime.now()
    start = end - timedelta(days=365 * years + 7)
    merged: Optional[pd.DataFrame] = None
    for series_id in config.FRED_SERIES:
        try:
            df = fetch_fred_series(series_id, start, end)
            merged = df if merged is None else merged.merge(df, on="Date", how="outer")
            LOG.info("FRED %s: %d observations", series_id, len(df))
        except Exception as exc:  # noqa: BLE001
            LOG.error("FRED %s failed: %s", series_id, exc)
    if merged is None:
        return pd.DataFrame()
    return merged.sort_values("Date").reset_index(drop=True)
