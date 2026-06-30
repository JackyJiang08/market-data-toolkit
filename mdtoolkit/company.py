"""The in-memory record for one company, passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from . import lineage
from .credit import CreditEstimate


@dataclass
class CompanyData:
    ticker: str
    as_of: str = lineage.RUN_TIMESTAMP
    name: str = ""
    currency: str = ""
    sector: str = ""
    industry: str = ""

    # Point-in-time facts
    market_cap: Optional[float] = None
    shares_traded_class: Optional[float] = None   # yfinance sharesOutstanding
    reference_shares: Optional[float] = None       # one-day method: mktcap / price
    last_close: Optional[float] = None
    dividend_rate: Optional[float] = None
    dividend_yield: Optional[float] = None

    # Time series
    prices: pd.DataFrame = field(default_factory=pd.DataFrame)
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)
    debt_schedule: pd.DataFrame = field(default_factory=pd.DataFrame)
    panel: pd.DataFrame = field(default_factory=pd.DataFrame)  # aligned daily panel

    # Statements
    q_income: pd.DataFrame = field(default_factory=pd.DataFrame)
    q_balance: pd.DataFrame = field(default_factory=pd.DataFrame)
    q_cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_income: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_balance: pd.DataFrame = field(default_factory=pd.DataFrame)
    a_cashflow: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Credit assessment
    credit: Optional[CreditEstimate] = None
