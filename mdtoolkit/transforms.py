"""Pure data transformations (no I/O): statement parsing, the debt schedule,
the default-point debt rule, and the reference share count.

Every function here is deterministic and unit-testable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import pandas as pd

from . import config


def _norm(s: object) -> str:
    """Normalise a label for fuzzy matching (lowercase, no whitespace)."""
    return "".join(str(s).lower().split())


def pick_row(frame: pd.DataFrame, candidates: Iterable[str]) -> Optional[pd.Series]:
    """Return the first frame row whose index matches a candidate label."""
    if frame is None or frame.empty:
        return None
    norm_index = {_norm(idx): idx for idx in frame.index}
    for cand in candidates:
        hit = norm_index.get(_norm(cand))
        if hit is not None:
            return frame.loc[hit]
    return None


def trim_to_window(frame: pd.DataFrame, cutoff: datetime) -> pd.DataFrame:
    """Keep statement columns (period-end dates) within the trailing window.

    Always retains at least the two most recent periods so a sparse company
    never yields an empty statement.
    """
    if frame is None or frame.empty:
        return pd.DataFrame()
    cols = list(frame.columns)
    try:
        keep = [c for c in cols if pd.to_datetime(c) >= pd.Timestamp(cutoff)]
    except Exception:  # noqa: BLE001
        keep = cols
    if len(keep) < 2:
        keep = cols[:2]
    return frame[keep]


def build_debt_schedule(balance: pd.DataFrame) -> pd.DataFrame:
    """Extract the six requested debt & liability line items as a time series
    (metrics as rows, period-end dates as ISO-string columns).
    """
    if balance is None or balance.empty:
        return pd.DataFrame()
    rows: dict[str, pd.Series] = {}
    for metric, candidates in config.BALANCE_SHEET_MAP.items():
        series = pick_row(balance, candidates)
        if series is not None:
            rows[metric] = series
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).T
    out.columns = [pd.to_datetime(c).strftime("%Y-%m-%d") for c in out.columns]
    return out


def reference_shares(market_cap: Optional[float], last_close: Optional[float],
                     fallback: Optional[float]) -> Optional[float]:
    """Shares outstanding via the instructor's one-day method.

    Pick one day (the latest), shares = market cap / price, then hold this
    constant when computing daily market cap = shares x price. For dual-class
    names (e.g. DELL) this recovers the *total* shares so market cap reconciles,
    which a single share-class figure would not.
    """
    if market_cap and last_close:
        return market_cap / last_close
    return fallback


def split_term_debt(balance: pd.DataFrame) -> pd.DataFrame:
    """Short-term and long-term debt per period, with robust fallbacks.

    Returns a frame indexed by period-end Timestamp with columns
    ['ShortTermDebt', 'LongTermDebt']. Some issuers (and all banks) do not
    report a clean current/non-current split, so:
      - missing short-term debt  -> max(Total Debt - Long-term Debt, 0)
      - missing long-term debt   -> max(Total Debt - Short-term Debt, 0)
    """
    if balance is None or balance.empty:
        return pd.DataFrame(columns=["ShortTermDebt", "LongTermDebt"])

    total = pick_row(balance, config.BALANCE_SHEET_MAP["Total Debt"])
    short = pick_row(balance, config.BALANCE_SHEET_MAP["Short-term / Current Debt"])
    long_ = pick_row(balance, config.BALANCE_SHEET_MAP["Long-term Debt"])

    periods = balance.columns
    st = short.reindex(periods) if short is not None else pd.Series(index=periods, dtype=float)
    lt = long_.reindex(periods) if long_ is not None else pd.Series(index=periods, dtype=float)
    tot = total.reindex(periods) if total is not None else pd.Series(index=periods, dtype=float)

    st = st.where(st.notna(), (tot - lt).clip(lower=0))
    lt = lt.where(lt.notna(), (tot - st).clip(lower=0))

    out = pd.DataFrame({"ShortTermDebt": st, "LongTermDebt": lt})
    out.index = pd.to_datetime(out.index)
    return out.sort_index()


def default_point_debt(short_term: pd.Series, long_term: pd.Series) -> pd.Series:
    """D = 100% short-term debt + 50% long-term debt (the model's strike)."""
    return (config.SHORT_TERM_DEBT_WEIGHT * short_term.fillna(0)
            + config.LONG_TERM_DEBT_WEIGHT * long_term.fillna(0))
