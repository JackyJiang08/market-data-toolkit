# Glossary & Concepts — for newcomers to quantitative credit

Plain-language explanations of every concept this toolkit uses. Read top to
bottom and the project will make sense even with no finance background.

---

## 1. The big picture: what is a credit rating?

A **credit rating** answers one question: *how likely is this borrower to fail
to pay back its debt?* A higher risk of non-payment → a worse rating.

- **Agencies.** Three government-designated agencies — **Moody's, S&P, Fitch** —
  rate the bonds of public companies (an effective monopoly). Any company
  issuing a bond generally needs a rating from one of them.
- **Banks** must also rate their *commercial customers* (mostly private firms,
  far more numerous than public ones). Banks typically use ~20 internal grades,
  similar in spirit to Moody's/S&P's ~22.
- **Consumers** are scored differently (FICO and similar).

### Why existing ratings are problematic
- Different agencies use different methods, so the **same company gets different
  ratings**.
- Converting between systems (e.g. S&P "B" → a bank's internal grade 10 or 11)
  is very hard.
- Ratings are often **point-in-time** (a short-term snapshot), but banks need a
  **5-year horizon** — hard to reconcile.
- **A rating is not the same as a default probability (PD).** Moody's B-rated
  firms have shown historical 1-year PDs ranging from ~0% (2007) to ~9.8%,
  despite carrying the *same* letter rating — a big inconsistency.
- In 2012 the SEC told Congress it was effectively "impossible" to standardize
  credit ratings across all methods.

The instructor's **TIC model** is a response to exactly this (see §9).

---

## 2. Equity-side terms

- **Share / stock.** A unit of ownership in a company.
- **Shares outstanding.** The total number of shares that exist. Market cap =
  shares × price. *This toolkit fixes shares to one day's value* (`market cap ÷
  price`) and reuses it, so daily market cap moves only with price.
- **Market capitalization (market cap), `E`.** The total market value of a
  company's equity = shares × price. We call it `E` because, in the credit
  model, equity is the observable quantity.
- **Closing price (`Close`).** The last traded price of the day.
- **Adjusted close (`Adj Close`).** The closing price rewritten so that past
  prices already account for **dividends** and **stock splits**. Use it to
  compute returns; it represents *total return*, not just price change.
- **Dividend.** Cash a company pays shareholders (e.g. ~$0.50/share each
  quarter). **Dividend rate** = annual cash per share. **Dividend yield** =
  dividend rate ÷ price (a percentage return from dividends alone).
- **Stock split.** Re-denominating shares (a $20 share "2-for-1 splits" into two
  $10 shares). It changes the price but not the company's value — adjusted close
  handles it for you.
- **Volatility (σ).** How much a price bounces around, expressed as an
  annualized standard deviation of returns. Higher σ = riskier.

---

## 3. Debt vs. liabilities (they are not the same)

- **Debt** = *borrowed money* — bank loans and bonds the firm must repay with
  interest.
- **Liabilities** = *everything the firm owes* — debt **plus** accounts payable
  (money owed to suppliers), taxes owed, deferred revenue, etc.
- So **debt is a subset of liabilities**; total liabilities ≥ total debt.

Split by when it is due:

| | Due within 1 year | Due after 1 year |
| --- | --- | --- |
| **Debt** | Short-term / current debt | Long-term debt |
| **Liabilities** | Short-term / current liabilities | Long-term (non-current) liabilities |

Identities that should hold:
`Total Debt = Short-term Debt + Long-term Debt` and
`Total Liabilities = Current Liabilities + Non-current Liabilities`.

These six numbers come from the **balance sheet**, which companies publish once
per quarter (the "statement date").

---

## 4. The default point — "100% short-term + 50% long-term"

The credit model needs a single **debt threshold** `D`: the amount whose
non-payment triggers default within the year. The rule is:

```
D = 100% × short-term debt + 50% × long-term debt
```

**Intuition.** A firm that defaults within a year must cover its short-term debt
in full (it is due now). But it will *not* have to repay all of its long-term
debt in that year — much of it is due later, and a defaulting firm often won't
pay it at all. Weighting long-term debt at 50% captures "some, but not all, of
it matters over a 1-year horizon." This is the model's **strike price** (§7).

---

## 5. Interest rates: the risk-free benchmark

- **Risk-free rate (`r`).** The return you can earn with (effectively) zero risk.
  In the US this is a **US Treasury** yield. Any risky investment should be
  expected to earn *at least* this baseline.
- **1-Year Treasury (FRED `DGS1`).** The risk-free rate for a **one-year**
  horizon — matching our 1-year credit horizon. This is the `r` in the model.
- **SOFR.** The Secured Overnight Financing Rate — a benchmark for *overnight*
  borrowing. Collected for context; not the model's `r`.
- Source: **FRED** (St. Louis Fed), which republishes the Federal Reserve
  **H.15** release. Programmatic and reliable, unlike scraping web pages.

---

## 6. Date alignment & no look-ahead

The three data streams live on different calendars: prices (trading days),
balance sheets (quarterly), rates (business days with their own holidays). To do
any calculation we need them on **one row per trading day**.

We use an **as-of (backward) join**: each trading day takes the *most recent*
statement and rate available **on or before** that day. This mirrors what an
analyst actually knew in real time — using a future statement to "explain" a
past price would be **look-ahead bias**, a classic and serious modelling error.

The result is the **Aligned Panel**: the model-ready daily table.

---

## 7. The structural credit model (Merton / KMV)

The core problem: we want the firm's **asset value** and **asset volatility**,
but we can't see them. We can only see equity (`E`), debt (`D`), and `r`.

**Merton's insight (1974):** owning the equity of a company with debt is like
holding a **call option on the firm's assets**, with the **debt as the strike
price**:
- If assets end up **above** the debt, shareholders keep the surplus.
- If assets end up **below** the debt, the firm defaults; shareholders get zero.

So we apply the Nobel-winning **Black-Scholes-Merton** option formula *in
reverse*: we know the "option price" (equity) and solve for the hidden asset
value `V` and asset volatility `σ_V`.

```
E  = V · N(d1) − D · e^(−rT) · N(d2)
d1 = [ln(V/D) + (r + ½σ_V²)·T] / (σ_V·√T)
d2 = d1 − σ_V·√T            (N = standard normal CDF)
```

Two unknowns, one equation → we **iterate** (the KMV procedure): guess `σ_V`,
back out a `V` series from the `E` series, recompute `σ_V` from `V`'s returns,
repeat until it stops changing.

Then the two headline numbers:
- **Distance to Default (DD)** — how many standard deviations the assets sit
  above the default point. Bigger = safer.
  `DD = [ln(V/D) + (r − ½σ_V²)·T] / (σ_V·√T)`
- **Probability of Default (PD)** — `PD = N(−DD)`.

**Reading the output.** For large investment-grade firms, PD is legitimately
*near zero*, so compare them with **DD** instead (e.g. in this universe COST's
DD ≈ 22 is much safer than ORCL's ≈ 3.7, which carries far more debt).

> Note: `σ_V` (asset volatility) is always **below** `σ_E` (equity volatility),
> because debt leverages equity — a real check that the model is behaving.

---

## 8. Why we can't just look up the answer

For consumer credit (mortgages, credit cards) there is abundant data, so simple
statistical models work. For **companies**, true default data is scarce — most
firms never default, and you can't observe the default probability of, say,
SpaceX directly. That is exactly why we need **structural models**: they *imply*
default risk from observable market and balance-sheet data plus theory.

---

## 9. The TIC model (where this is heading)

The instructor's **Time-Consistent Credit (TIC)** model is the eventual method:

- **One universal formula** that reproduces Moody's, S&P, bank-internal, and
  KMV/Merton ratings as *special cases*.
- Driven by **two factors**: one for **expected loss** (default probability) and
  one for **unexpected loss** (credit deterioration) — analogous to *life
  expectancy* and *health deterioration*.
- Key metric **CCM** (Credit Core Correlation Measure); the TIC rating ≈
  `CCM / (life expectancy)^Q`, and a **risk score = TIC rating × 100** for
  readability.
- Designed to be **consistent over time** (it fixes the point-in-time vs.
  through-the-cycle problem) and to clearly separate AAA/AA/A — which Moody's
  cannot, since their PDs there are all ~0.
- Published at the World Finance Conference (2021) and NYU (2019).

In this repo, `credit.TICModel` is a **stub** that already conforms to the
`CreditModel` interface; the formula is filled in once it's covered in class.

---

## 10. Quick reference — columns in the Aligned Panel

| Column | Meaning |
| --- | --- |
| `Close` / `AdjClose` | Raw / dividend-&-split-adjusted closing price |
| `Shares` | Constant reference share count (one-day method) |
| `MarketCap_E` | Equity value `E` = Shares × Close |
| `EquityLogReturn` | `ln(AdjClose_t / AdjClose_{t-1})` — for volatility |
| `ShortTermDebt`, `LongTermDebt` | From the balance sheet, as-of each day |
| `DefaultPointDebt_D` | `D` = 100% short-term + 50% long-term |
| `RiskFree_R` | 1-Year Treasury as a decimal (e.g. 0.0394) |
| `Horizon_T` | Credit horizon in years (1.0) |
