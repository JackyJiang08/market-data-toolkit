"""Credit-risk modelling layer.

This module defines a clean *interface* for turning the aligned data panel into
a credit assessment, plus a working baseline implementation (Merton / KMV).

Background for newcomers
------------------------
A company defaults when it cannot meet its debt. We cannot observe a private
firm's true asset value or how volatile it is -- we only see its **equity**
(market cap), its **debt**, and the **risk-free rate**. The structural insight
(Merton, 1974) is:

    Owning the equity of a levered firm is like holding a *call option* on the
    firm's assets, struck at the debt level. If assets end up above the debt,
    shareholders keep the difference; if below, the firm defaults and they get
    nothing.

So we can apply the Black-Scholes-Merton option formula in reverse: observe the
"option price" (equity) and solve for the two unknowns -- asset value V and
asset volatility sigma_V -- then read off the **probability of default (PD)**.

    E  = V * N(d1) - D * e^{-rT} * N(d2)          (equity as a call)
    d1 = [ln(V/D) + (r + 0.5 sigma_V^2) T] / (sigma_V sqrt(T))
    d2 = d1 - sigma_V sqrt(T)

Two unknowns (V, sigma_V) but one equation, so we iterate (the KMV procedure):
back out a V series from the E series at a trial sigma_V, recompute sigma_V from
V's returns, and repeat until it stops moving. Then:

    Distance to Default  DD = [ln(V/D) + (r - 0.5 sigma_V^2) T] / (sigma_V sqrt(T))
    Probability of Default PD = N(-DD)

This baseline is the structural model the instructor's **TIC** method generalises.
`TICModel` below is a deliberate placeholder: the instructor's universal formula
is taught in later weeks and plugs into the same interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

from . import config

LOG = logging.getLogger("mdtoolkit.credit")


# --------------------------------------------------------------------------- #
# Interface: inputs and outputs
# --------------------------------------------------------------------------- #
@dataclass
class CreditModelInputs:
    """Everything a credit model needs, extracted from the aligned panel."""
    ticker: str
    equity: pd.Series        # daily equity value E (MarketCap_E), indexed by date
    equity_vol: float        # annualised equity volatility sigma_E
    debt: float              # latest default-point debt D (the strike)
    risk_free: float         # latest risk-free rate r (decimal)
    horizon: float = config.HORIZON_YEARS  # T in years

    @property
    def latest_equity(self) -> float:
        return float(self.equity.dropna().iloc[-1])


@dataclass
class CreditEstimate:
    """A model's assessment of one company."""
    ticker: str
    model: str
    asset_value: Optional[float] = None      # V0
    asset_vol: Optional[float] = None        # sigma_V (annualised)
    distance_to_default: Optional[float] = None
    default_probability: Optional[float] = None
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "Ticker": self.ticker,
            "Model": self.model,
            "Equity_E": None,
            "AssetValue_V0": self.asset_value,
            "AssetVol_sigmaV": self.asset_vol,
            "DistanceToDefault": self.distance_to_default,
            "DefaultProbability": self.default_probability,
            "Note": self.note,
        }


class CreditModel(ABC):
    """Strategy interface: any credit model maps inputs -> an estimate."""

    name: str = "abstract"

    @abstractmethod
    def estimate(self, inputs: CreditModelInputs) -> CreditEstimate:
        ...


# --------------------------------------------------------------------------- #
# Inputs builder
# --------------------------------------------------------------------------- #
def build_inputs(ticker: str, panel: pd.DataFrame) -> Optional[CreditModelInputs]:
    """Derive model inputs from a company's aligned panel."""
    if panel is None or panel.empty or "MarketCap_E" not in panel:
        return None
    equity = panel["MarketCap_E"].dropna()
    if equity.empty:
        return None

    rets = panel["EquityLogReturn"].dropna()
    equity_vol = float(rets.std() * np.sqrt(config.TRADING_DAYS_PER_YEAR)) if len(rets) > 5 else float("nan")

    debt = panel["DefaultPointDebt_D"].dropna()
    debt_val = float(debt.iloc[-1]) if not debt.empty else float("nan")
    rf = panel["RiskFree_R"].dropna()
    rf_val = float(rf.iloc[-1]) if not rf.empty else float("nan")

    return CreditModelInputs(ticker=ticker, equity=equity, equity_vol=equity_vol,
                             debt=debt_val, risk_free=rf_val)


# --------------------------------------------------------------------------- #
# Baseline implementation: Merton / KMV
# --------------------------------------------------------------------------- #
def _bs_equity(V: float, D: float, r: float, sigma: float, T: float) -> float:
    """Black-Scholes value of equity as a call on assets V struck at D."""
    if sigma <= 0 or T <= 0 or V <= 0:
        return max(V - D * np.exp(-r * T), 0.0)
    d1 = (np.log(V / D) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return V * norm.cdf(d1) - D * np.exp(-r * T) * norm.cdf(d2)


def _invert_asset_value(E: float, D: float, r: float, sigma: float, T: float) -> float:
    """Solve E = BS_equity(V) for V at fixed sigma (equity is increasing in V)."""
    if E <= 0:
        return float("nan")
    lo, hi = E, E + D * np.exp(-r * T) + 1.0
    # Expand the upper bracket until it straddles the root.
    for _ in range(64):
        if _bs_equity(hi, D, r, sigma, T) >= E:
            break
        hi *= 2.0
    try:
        return brentq(lambda V: _bs_equity(V, D, r, sigma, T) - E, lo, hi, maxiter=200)
    except Exception:  # noqa: BLE001
        return E + D * np.exp(-r * T)  # graceful fallback: V ~ E + PV(debt)


class MertonKMVModel(CreditModel):
    """Iterative Merton/KMV structural default model (the standard baseline)."""

    name = "Merton/KMV (baseline)"

    def __init__(self, max_iter: int = 50, tol: float = 1e-4):
        self.max_iter = max_iter
        self.tol = tol

    def estimate(self, inputs: CreditModelInputs) -> CreditEstimate:
        E = inputs.equity
        D, r, T = inputs.debt, inputs.risk_free, inputs.horizon
        out = CreditEstimate(ticker=inputs.ticker, model=self.name)

        if not np.isfinite(D) or D <= 0:
            out.default_probability = 0.0
            out.note = "No positive default-point debt -> PD treated as ~0."
            out.asset_value = inputs.latest_equity
            return out
        if not np.isfinite(r) or not np.isfinite(inputs.equity_vol) or len(E) < 30:
            out.note = "Insufficient data (rate / volatility / history) to solve."
            return out

        sigma_v = inputs.equity_vol * inputs.latest_equity / (inputs.latest_equity + D)
        sigma_v = max(sigma_v, 1e-3)
        E_vals = E.to_numpy()

        for _ in range(self.max_iter):
            V_vals = np.array([_invert_asset_value(e, D, r, sigma_v, T) for e in E_vals])
            log_ret = np.diff(np.log(V_vals[V_vals > 0]))
            new_sigma = float(np.std(log_ret) * np.sqrt(config.TRADING_DAYS_PER_YEAR))
            if not np.isfinite(new_sigma) or new_sigma <= 0:
                break
            if abs(new_sigma - sigma_v) < self.tol:
                sigma_v = new_sigma
                break
            sigma_v = new_sigma

        V0 = float(V_vals[-1])
        dd = (np.log(V0 / D) + (r - 0.5 * sigma_v ** 2) * T) / (sigma_v * np.sqrt(T))
        pd_ = float(norm.cdf(-dd))

        out.asset_value = V0
        out.asset_vol = sigma_v
        out.distance_to_default = float(dd)
        out.default_probability = pd_
        out.note = "Converged" if np.isfinite(pd_) else "Did not converge"
        return out


class TICModel(CreditModel):
    """Placeholder for the instructor's Time-Consistent Credit (TIC) model.

    The TIC method is a single universal formula (taught in later weeks) that
    reproduces Moody's, S&P, bank-internal, and KMV ratings as special cases,
    driven by two behavioural factors (expected loss and credit deterioration).
    It plugs into this same interface; implement `estimate` once the formula is
    covered in class.
    """

    name = "TIC (instructor model)"

    def estimate(self, inputs: CreditModelInputs) -> CreditEstimate:  # pragma: no cover
        raise NotImplementedError(
            "TICModel is a stub. The instructor's universal TIC formula will be "
            "implemented here in a later week and reuse the CreditModel interface."
        )
