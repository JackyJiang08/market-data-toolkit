"""The tidy long table: a single flat fact table consolidating every company
and the macro rates, for databases / BI / pivot analysis.

Schema: [Ticker, AsOf, Category, Period, Metric, Value]
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from . import config, lineage
from .company import CompanyData

LOG = logging.getLogger("mdtoolkit.longtable")

LONG_COLUMNS = ["Ticker", "AsOf", "Category", "Period", "Metric", "Value"]


def _melt_statement(df: pd.DataFrame, ticker: str, as_of: str, category: str) -> pd.DataFrame:
    """Melt a statement frame (rows=line items, cols=period dates) to long."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLUMNS)
    t = df.copy()
    # Normalise period-end columns to date strings (keeps parquet/CSV consistent).
    t.columns = pd.to_datetime(t.columns, errors="coerce").strftime("%Y-%m-%d")
    t.index.name = "Metric"
    long = t.reset_index().melt(id_vars="Metric", var_name="Period", value_name="Value")
    long["Ticker"], long["AsOf"], long["Category"] = ticker, as_of, category
    return long[LONG_COLUMNS]


def _melt_timeseries(df: pd.DataFrame, ticker: str, as_of: str, category: str) -> pd.DataFrame:
    """Melt a time-indexed frame (rows=dates, cols=metrics) to long."""
    if df is None or df.empty:
        return pd.DataFrame(columns=LONG_COLUMNS)
    t = df.copy()
    t.index.name = "Period"
    long = t.reset_index().melt(id_vars="Period", var_name="Metric", value_name="Value")
    long["Period"] = pd.to_datetime(long["Period"], errors="coerce").dt.strftime("%Y-%m-%d")
    long["Ticker"], long["AsOf"], long["Category"] = ticker, as_of, category
    return long[LONG_COLUMNS]


def build_long_table(companies: list[CompanyData], rates: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for c in companies:
        snapshot = {
            "MarketCap": c.market_cap,
            "ReferenceShares": c.reference_shares,
            "LastClose": c.last_close,
            "DividendRate": c.dividend_rate,
            "DividendYield": c.dividend_yield,
        }
        parts.append(pd.DataFrame(
            [(c.ticker, c.as_of, "company_info", c.as_of[:10], k, v)
             for k, v in snapshot.items() if v is not None],
            columns=LONG_COLUMNS,
        ))
        parts.append(_melt_timeseries(c.prices, c.ticker, c.as_of, "price"))
        parts.append(_melt_timeseries(c.panel, c.ticker, c.as_of, "aligned_panel"))
        parts.append(_melt_timeseries(c.dividends, c.ticker, c.as_of, "dividend"))
        parts.append(_melt_statement(c.debt_schedule, c.ticker, c.as_of, "debt_schedule"))
        parts.append(_melt_statement(c.q_income, c.ticker, c.as_of, "income_statement (Q)"))
        parts.append(_melt_statement(c.q_balance, c.ticker, c.as_of, "balance_sheet (Q)"))
        parts.append(_melt_statement(c.q_cashflow, c.ticker, c.as_of, "cash_flow (Q)"))
        parts.append(_melt_statement(c.a_income, c.ticker, c.as_of, "income_statement (A)"))
        parts.append(_melt_statement(c.a_balance, c.ticker, c.as_of, "balance_sheet (A)"))
        parts.append(_melt_statement(c.a_cashflow, c.ticker, c.as_of, "cash_flow (A)"))
        if c.credit is not None:
            est = {
                "AssetValue_V0": c.credit.asset_value,
                "AssetVol_sigmaV": c.credit.asset_vol,
                "DistanceToDefault": c.credit.distance_to_default,
                "DefaultProbability": c.credit.default_probability,
            }
            parts.append(pd.DataFrame(
                [(c.ticker, c.as_of, "credit_estimate", c.as_of[:10], k, v)
                 for k, v in est.items() if v is not None],
                columns=LONG_COLUMNS,
            ))

    if rates is not None and not rates.empty:
        r = rates.rename(columns={"Date": "Period"}).copy()
        r["Period"] = pd.to_datetime(r["Period"]).dt.strftime("%Y-%m-%d")
        r_long = r.melt(id_vars="Period", var_name="Metric", value_name="Value")
        r_long["Ticker"], r_long["AsOf"], r_long["Category"] = "MACRO", lineage.RUN_TIMESTAMP, "rate"
        parts.append(r_long[LONG_COLUMNS])

    if not parts:
        return pd.DataFrame(columns=LONG_COLUMNS)
    out = pd.concat(parts, ignore_index=True)
    out["Value"] = pd.to_numeric(out["Value"], errors="coerce")
    out = out.dropna(subset=["Value"])
    return out.sort_values(["Ticker", "Category", "Period", "Metric"]).reset_index(drop=True)


def write_long_table(long_df: pd.DataFrame) -> None:
    if long_df.empty:
        LOG.warning("long table is empty -- nothing written")
        return
    csv_path = os.path.join(config.OUTPUT_DIR, "all_companies_long.csv")
    long_df.to_csv(csv_path, index=False)
    LOG.info("tidy long table -> %s (%d rows)", os.path.basename(csv_path), len(long_df))
    try:
        pq_path = os.path.join(config.OUTPUT_DIR, "all_companies_long.parquet")
        long_df.to_parquet(pq_path, index=False)
        LOG.info("tidy long table -> %s", os.path.basename(pq_path))
    except Exception as exc:  # noqa: BLE001
        LOG.info("parquet skipped (%s); CSV is available", exc)
