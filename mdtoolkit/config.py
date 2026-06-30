"""Central configuration: the data universe, source parameters, financial
statement label mappings, and credit-model assumptions.

Keeping every tunable constant in one module is an enterprise convention: the
rest of the package imports from here, so behaviour changes live in a single,
reviewable place.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------- #
# Company universe (the 10 assigned tickers)
# --------------------------------------------------------------------------- #
DEFAULT_TICKERS: tuple[str, ...] = (
    "COST", "KO", "DELL", "ORCL", "PNC",
    "WMT", "INTU", "AMZN", "T", "KHC",
)

# --------------------------------------------------------------------------- #
# Macro rates (FRED series id -> human label). Same data as the Federal
# Reserve H.15 release. DGS1 is the risk-free benchmark used by the model.
# --------------------------------------------------------------------------- #
FRED_SERIES: dict[str, str] = {
    "DGS1": "1-Year Treasury Constant Maturity Rate (%)",
    "SOFR": "Secured Overnight Financing Rate (%)",
}
RISK_FREE_SERIES = "DGS1"  # the series fed into the credit model as r

# --------------------------------------------------------------------------- #
# Balance-sheet line-item resolution. yfinance row labels drift between
# versions and companies, so each metric maps to candidate labels tried in
# priority order (case- and whitespace-insensitive).
# --------------------------------------------------------------------------- #
BALANCE_SHEET_MAP: dict[str, tuple[str, ...]] = {
    "Total Debt": ("Total Debt",),
    "Total Liabilities": (
        "Total Liabilities Net Minority Interest",
        "Total Liab",
        "Total Liabilities",
    ),
    "Short-term / Current Debt": (
        "Current Debt And Capital Lease Obligation",
        "Current Debt",
        "Short Term Debt",
        "Short Long Term Debt",
    ),
    "Short-term / Current Liabilities": (
        "Current Liabilities",
        "Total Current Liabilities",
    ),
    "Long-term Debt": (
        "Long Term Debt And Capital Lease Obligation",
        "Long Term Debt",
    ),
    "Long-term Liabilities": (
        "Total Non Current Liabilities Net Minority Interest",
        "Total Non Current Liabilities",
        "Non Current Liabilities",
    ),
}

# --------------------------------------------------------------------------- #
# Credit-model assumptions
# --------------------------------------------------------------------------- #
# "Default point" debt = the liability a firm must service to avoid default
# within the horizon. The instructor's rule: a firm defaulting within a year
# is unlikely to repay all long-term debt, so weight it at 50%.
SHORT_TERM_DEBT_WEIGHT = 1.0
LONG_TERM_DEBT_WEIGHT = 0.5

HORIZON_YEARS = 1.0        # T: the 1-year credit horizon (matches the 1Y T-bill)
TRADING_DAYS_PER_YEAR = 252  # for annualising daily volatility

# --------------------------------------------------------------------------- #
# Network politeness / resilience (Yahoo rate-limits heavy use)
# --------------------------------------------------------------------------- #
MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0
INTER_TICKER_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT = 20

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")

DEFAULT_YEARS = 2  # trailing window for prices and financials
