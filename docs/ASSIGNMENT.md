# Assignment — Credit Rating Data & Model

This document restates the project (from the Meeting 3 briefing) and maps each
requirement to the code that implements it. If a term is unfamiliar, see
[`GLOSSARY.md`](GLOSSARY.md).

## Project goal

Build a tool that collects and calculates financial data for **10 publicly
traded companies** and ultimately produces **credit ratings** using the
instructor's **TIC (Time-Consistent Credit)** model. The tool can be simple or
elaborate — what matters is that it *works* and produces the *correct outputs*.
The practical aim: learn a credit-rating method that is genuinely useful (and
demonstrable in a bank interview for a credit-risk role).

**Companies:** COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, KHC.

## This week's action items

| # | Task | Status in this repo |
| --- | --- | --- |
| 1 | Read the instructor's updated TIC theory article | (your reading — posted to WeChat) |
| 2 | Watch the pre-recorded lecture | (your reading — link in WeChat) |
| 3 | **Program the tool to auto-calculate the required metrics and define the interface** | ✅ `mdtoolkit` package + `credit.CreditModel` interface |
| 4 | **Collect the required data for the 10 companies** | ✅ `run.py` (default universe) |
| 5 | Send questions to WeChat / email | — |

## Data requirements → implementation

### 1. Market cap & shares outstanding
> Pick one day, `shares outstanding = market cap ÷ stock price`, then use this
> **constant** share count for daily market cap calculations.

- `transforms.reference_shares(market_cap, last_close, fallback)` computes it.
- The aligned panel then sets `MarketCap_E = Shares × Close` for **every** day.
- **Why constant shares?** Share count changes slowly (buybacks/issuance), while
  price changes every day. Holding shares fixed isolates the price effect and
  keeps a clean daily equity series for the model. For dual-class firms (DELL)
  this recovers the *total* shares, so market cap reconciles.

### 2. Adjusted close price
> Use Yahoo's "adjusted close" column — it already adjusts for dividends and
> stock splits, so no manual adjustment is needed.

- Stored as `AdjClose` in the panel and `Adj Close` in Price History.
- Equity **returns and volatility** are computed from `AdjClose` (total return),
  while **market cap** uses the raw `Close × Shares` (actual traded value).

### 3. Debt data
> Collect total debt, total liability, short-term debt, and current liability
> from the balance sheet. For calculations use **100% short-term debt + 50%
> long-term debt** (a firm defaulting within a year likely won't repay all of
> its long-term debt).

- The 6-line **Debt & Liabilities** schedule: `transforms.build_debt_schedule`.
- The model's **default point** `D = 1.0·ST + 0.5·LT`:
  `transforms.default_point_debt`, surfaced as `DefaultPointDebt_D`.
- Robust fallbacks (`transforms.split_term_debt`) handle issuers/banks that
  don't report a clean current/non-current split.

### 4. One-year Treasury bill rate
> The risk-free baseline/benchmark, reflecting a one-year investment horizon.

- FRED `DGS1`, stored as `RiskFree_R` (converted from percent to a decimal).
- **Why one year?** The whole analysis uses a 1-year credit horizon (`T = 1`),
  so the matching risk-free tenor is the 1-year Treasury. Any investment should
  at least earn this baseline; it is also the discount rate `r` in the model.

### 5. Date alignment
> Calculations must match stock trading dates, quarterly balance-sheet statement
> dates, and interest-rate observation dates.

- `alignment.build_panel` fuses the three calendars with **as-of (backward)**
  joins: each trading day takes the most recent statement and rate known *on or
  before* that day — no look-ahead bias.
- Output: the **Aligned Panel** sheet, the model-ready daily table.

## From data to a credit rating (the modelling arc)

The collected inputs feed a **structural credit model**. We only observe equity
(E), debt (D), and the risk-free rate (r); the firm's true asset value and asset
volatility are hidden. The Merton/KMV approach treats **equity as a call option
on the firm's assets** (strike = debt) and solves for the hidden values, then
reads off the **distance to default** and **probability of default**.

- Interface: `credit.CreditModel` (`estimate(inputs) → CreditEstimate`).
- Baseline: `credit.MertonKMVModel` (iterative KMV procedure).
- Instructor's method: `credit.TICModel` — a documented **stub** that plugs into
  the same interface, to be implemented when the TIC formula is taught.

See [`GLOSSARY.md`](GLOSSARY.md) for the full intuition and formulas.

## Logistics (from the meeting)

- The instructor posts the updated TIC article + pre-recorded lecture to WeChat.
- Next meeting: Saturday evening next week; attendance optional (lecture is
  pre-recorded).
- The instructor may have intermittent Gmail/GitHub access while traveling in
  China — plan around that for sharing.
