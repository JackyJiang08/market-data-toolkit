"""Orchestration: fetch -> transform -> align -> model -> write.

`run(RunConfig)` is the single entry point used by the CLI and the launcher.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Sequence

import pandas as pd
import yfinance as yf

from . import alignment, config, credit, excel, longtable, sources, transforms
from .company import CompanyData

LOG = logging.getLogger("mdtoolkit.pipeline")


@dataclass
class RunConfig:
    tickers: Sequence[str]
    years: int = config.DEFAULT_YEARS
    include_rates: bool = True
    run_credit_model: bool = True

    @property
    def cutoff_date(self) -> datetime:
        return datetime.now() - timedelta(days=365 * self.years + 7)


def fetch_company(ticker: str, cfg: RunConfig, rates: pd.DataFrame) -> Optional[CompanyData]:
    ticker = ticker.strip().upper()
    if not ticker:
        return None
    LOG.info("=== %s ===", ticker)
    tk = yf.Ticker(ticker)
    data = CompanyData(ticker=ticker)

    # --- company info ---
    try:
        info = sources.get_info(tk)
    except Exception:  # noqa: BLE001
        info = {}
    data.name = info.get("longName") or info.get("shortName") or ticker
    data.currency = info.get("currency", "")
    data.sector = info.get("sector", "")
    data.industry = info.get("industry", "")
    data.market_cap = info.get("marketCap")
    data.shares_traded_class = info.get("sharesOutstanding")
    data.dividend_rate = info.get("dividendRate")
    data.dividend_yield = info.get("dividendYield")

    # --- prices ---
    try:
        prices = sources.get_history(tk, cfg.cutoff_date)
    except Exception:  # noqa: BLE001
        prices = pd.DataFrame()
    if not prices.empty:
        prices.index = prices.index.tz_localize(None)
        if "Adj Close" in prices and "Close" in prices:
            prices["Div/Split Adj Factor"] = (prices["Adj Close"] / prices["Close"]).round(6)
        data.prices = prices
        data.last_close = float(prices["Close"].iloc[-1])
        LOG.info("  prices: %d rows (%s -> %s)", len(prices),
                 prices.index.min().date(), prices.index.max().date())

    # Reference shares via the one-day method (mktcap / price).
    data.reference_shares = transforms.reference_shares(
        data.market_cap, data.last_close, data.shares_traded_class)

    # --- dividends ---
    if not prices.empty and "Dividends" in prices:
        divs = prices.loc[prices["Dividends"] > 0, ["Dividends"]].copy()
        if not divs.empty:
            divs.index.name = "Date"
            data.dividends = divs

    # --- statements ---
    try:
        stmts = sources.get_statements(tk)
    except Exception:  # noqa: BLE001
        stmts = {}
    data.q_income = transforms.trim_to_window(stmts.get("q_income"), cfg.cutoff_date)
    data.q_balance = transforms.trim_to_window(stmts.get("q_balance"), cfg.cutoff_date)
    data.q_cashflow = transforms.trim_to_window(stmts.get("q_cashflow"), cfg.cutoff_date)
    data.a_income = transforms.trim_to_window(stmts.get("a_income"), cfg.cutoff_date)
    data.a_balance = transforms.trim_to_window(stmts.get("a_balance"), cfg.cutoff_date)
    data.a_cashflow = transforms.trim_to_window(stmts.get("a_cashflow"), cfg.cutoff_date)

    balance_for_debt = data.q_balance if not data.q_balance.empty else data.a_balance
    data.debt_schedule = transforms.build_debt_schedule(balance_for_debt)
    if not data.debt_schedule.empty:
        LOG.info("  debt schedule: %d metrics x %d periods", *data.debt_schedule.shape)

    # --- date-aligned model panel ---
    rf_series = None
    if rates is not None and not rates.empty and config.RISK_FREE_SERIES in rates:
        rf_series = rates.set_index("Date")[config.RISK_FREE_SERIES]
    data.panel = alignment.build_panel(
        data.prices, data.reference_shares, balance_for_debt, rf_series)

    # --- credit model ---
    if cfg.run_credit_model and not data.panel.empty:
        inputs = credit.build_inputs(ticker, data.panel)
        if inputs is not None:
            try:
                data.credit = credit.MertonKMVModel().estimate(inputs)
                LOG.info("  credit: PD=%s, DD=%s",
                         _fmt(data.credit.default_probability),
                         _fmt(data.credit.distance_to_default))
            except Exception as exc:  # noqa: BLE001
                LOG.warning("  credit model failed: %s", exc)
    return data


def _fmt(x: Optional[float]) -> str:
    return f"{x:.4f}" if x is not None and pd.notna(x) else "n/a"


def run(cfg: RunConfig) -> list[CompanyData]:
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    LOG.info("Universe: %s | window: %dy | rates: %s | credit-model: %s",
             ", ".join(cfg.tickers), cfg.years, cfg.include_rates, cfg.run_credit_model)

    rates = sources.fetch_rates(cfg.years) if cfg.include_rates else pd.DataFrame()

    companies: list[CompanyData] = []
    for i, ticker in enumerate(cfg.tickers):
        try:
            data = fetch_company(ticker, cfg, rates)
            if data is not None:
                excel.write_company_workbook(data, cfg.years)
                companies.append(data)
        except Exception as exc:  # noqa: BLE001
            LOG.error("Ticker %s aborted: %s", ticker, exc)
        if i < len(cfg.tickers) - 1:
            time.sleep(config.INTER_TICKER_DELAY_SECONDS)

    if companies:
        excel.write_master_workbook(companies, rates)
        longtable.write_long_table(longtable.build_long_table(companies, rates))

    LOG.info("Done. %d/%d companies succeeded. Output: %s",
             len(companies), len(cfg.tickers), config.OUTPUT_DIR)
    return companies
