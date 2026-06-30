"""Date alignment: fuse three calendars into one model-ready daily panel.

The three series live on different calendars:
  - stock prices       -> trading days (weekdays minus holidays)
  - balance sheets     -> one statement date per quarter
  - interest rates     -> business days, with their own holiday gaps

The credit model needs them on a single row per trading day. We use as-of
(backward) joins: each trading day takes the *most recent* statement and rate
known on or before that day -- exactly how an analyst would have seen the data
in real time (no look-ahead).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, transforms


def build_panel(prices: pd.DataFrame,
                reference_shares: float | None,
                balance: pd.DataFrame,
                risk_free: pd.Series | None) -> pd.DataFrame:
    """Construct the aligned daily panel for one company.

    Columns
        Close, AdjClose          : raw and dividend/split-adjusted close
        Shares                   : constant reference share count
        MarketCap_E              : equity value E = Shares x Close
        EquityLogReturn          : ln(AdjClose_t / AdjClose_{t-1})
        ShortTermDebt, LongTermDebt
        DefaultPointDebt_D       : 1.0*ST + 0.5*LT  (model strike)
        RiskFree_R               : 1Y Treasury as a decimal (e.g. 0.0498)
        Horizon_T                : credit horizon in years (1.0)
    """
    if prices is None or prices.empty:
        return pd.DataFrame()

    panel = pd.DataFrame(index=prices.index.copy())
    panel.index.name = "Date"
    panel["Close"] = prices["Close"]
    panel["AdjClose"] = prices.get("Adj Close", prices["Close"])

    # Equity value E using the constant one-day share count.
    panel["Shares"] = reference_shares
    panel["MarketCap_E"] = (panel["Shares"] * panel["Close"]
                            if reference_shares else np.nan)

    # Equity returns from the adjusted close (captures total return).
    panel["EquityLogReturn"] = np.log(panel["AdjClose"] / panel["AdjClose"].shift(1))

    # --- as-of join the quarterly debt onto trading days ---
    term = transforms.split_term_debt(balance)
    if not term.empty:
        term = term.reset_index().rename(columns={"index": "Date"})
        term["Date"] = pd.to_datetime(term["Date"])
        left = panel.reset_index()[["Date"]].sort_values("Date")
        merged = pd.merge_asof(left, term.sort_values("Date"),
                               on="Date", direction="backward")
        merged = merged.set_index("Date")
        panel["ShortTermDebt"] = merged["ShortTermDebt"]
        panel["LongTermDebt"] = merged["LongTermDebt"]
        panel["DefaultPointDebt_D"] = transforms.default_point_debt(
            panel["ShortTermDebt"], panel["LongTermDebt"])
    else:
        panel["ShortTermDebt"] = np.nan
        panel["LongTermDebt"] = np.nan
        panel["DefaultPointDebt_D"] = np.nan

    # --- as-of join the risk-free rate onto trading days ---
    if risk_free is not None and not risk_free.empty:
        rf = risk_free.rename("RiskFree_R").reset_index()
        rf.columns = ["Date", "RiskFree_R"]
        rf["Date"] = pd.to_datetime(rf["Date"])
        rf["RiskFree_R"] = rf["RiskFree_R"] / 100.0  # percent -> decimal
        left = panel.reset_index()[["Date"]].sort_values("Date")
        merged = pd.merge_asof(left, rf.sort_values("Date"),
                               on="Date", direction="backward")
        panel["RiskFree_R"] = merged.set_index("Date")["RiskFree_R"]
    else:
        panel["RiskFree_R"] = np.nan

    panel["Horizon_T"] = config.HORIZON_YEARS
    return panel
