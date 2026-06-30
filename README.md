# Market Data Toolkit

A professional data pipeline that collects **equity** and **macro-rate** market
data for a universe of companies, aligns it onto a single daily timeline, and
runs a structural **credit-risk model** (Merton / KMV) to estimate each firm's
distance to default and probability of default.

It is the data-and-modelling foundation for building credit ratings with the
instructor's **TIC (Time-Consistent Credit)** model. New to quantitative
finance? Start with **[`docs/GLOSSARY.md`](docs/GLOSSARY.md)** — it explains
every term and the *why* behind each step — and **[`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md)**
for how the code maps to the project requirements.

Equity data comes from [Yahoo Finance](https://finance.yahoo.com) via
`yfinance`; interest rates come from [FRED](https://fred.stlouisfed.org/), the
St. Louis Fed's distribution of the Federal Reserve **H.15** release.

---

## What it produces

For 10 assigned companies — `COST KO DELL ORCL PNC WMT INTU AMZN T KHC` — over a
trailing window (default 2 years):

**Per-company workbook** — `output/<TICKER>_data.xlsx`

| Tab | Contents |
| --- | --- |
| Summary | Market cap, shares outstanding, last close, dividend (rate & yield), provenance |
| **Credit Inputs & Estimate** | E, default-point debt D, risk-free r, T, equity & asset volatility, distance to default, **PD** |
| **Aligned Panel** | The date-aligned daily model table (prices + debt + rate on one row) |
| Debt & Liabilities | Total Debt, Total Liabilities, Short/Current Debt, Short/Current Liabilities, Long-term Debt, Long-term Liabilities |
| Price History | Daily OHLC, Volume, **Adjusted Close**, dividend/split adjustment factor |
| Dividends | Dividend cash events |
| Q / Annual statements | Income Statement, Balance Sheet, Cash Flow (quarterly + annual) |

**Master workbook** — `output/_MASTER_summary.xlsx`: `Company Summary`,
`Credit Summary` (all firms ranked), `Debt & Liab (latest)`, `Macro Rates`.

**Tidy long table** — `output/all_companies_long.{csv,parquet}`, one flat fact
table (`Ticker, AsOf, Category, Period, Metric, Value`) for databases / BI.

## The key data requirements (and how they are implemented)

| Requirement | Implementation |
| --- | --- |
| **Shares outstanding** — pick one day, `mktcap / price`, hold constant for daily market cap | `transforms.reference_shares`; daily `MarketCap_E = Shares × Close` in the panel |
| **Adjusted close** — use Yahoo's adjusted close (auto-adjusts dividends & splits) | `Adj Close` column; equity returns/volatility computed from it |
| **Debt** — total debt, total liability, short-term debt, current liability, long-term | `transforms.build_debt_schedule` (6-line schedule) |
| **Default-point debt** — `100% short-term + 50% long-term` | `transforms.default_point_debt` → `DefaultPointDebt_D` |
| **1-Year Treasury** — risk-free benchmark, 1-year horizon | FRED `DGS1` → `RiskFree_R` (decimal) |
| **Date alignment** — match stock dates, statement dates, rate dates | `alignment.build_panel` via as-of (no look-ahead) joins |
| **Automatic calculation + interface** | `credit.CreditModel` interface + `MertonKMVModel` baseline |

See [`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md) for the full mapping and the
finance reasoning behind each.

## Installation

```bash
pip3 install -r requirements.txt   # Python 3.8+
```

## Usage

```bash
python3 run.py                      # default 10-company universe, 2y
python3 run.py AAPL MSFT            # custom tickers
python3 run.py --years 3           # custom window
python3 run.py --no-rates          # skip FRED macro rates
python3 run.py --no-credit-model   # data only, skip Merton/KMV
```

macOS users can double-click **`Download Stocks.command`**, which prompts for
tickers and a window, runs the pipeline, and opens the output folder.

Programmatic use:

```python
from mdtoolkit import RunConfig, run
companies = run(RunConfig(tickers=["KO", "WMT"], years=2))
```

## Architecture

```
mdtoolkit/
├── config.py      # universe, FRED series, label maps, model assumptions
├── lineage.py     # provenance (extraction timestamp + sources)
├── sources.py     # Yahoo + FRED adapters (retry/backoff)  ← only network layer
├── transforms.py  # debt schedule, default-point debt, reference shares
├── alignment.py   # fuse stock/statement/rate calendars into one daily panel
├── credit.py      # CreditModel interface + Merton/KMV baseline + TIC stub
├── company.py     # the per-company data container
├── excel.py       # formatted workbooks
├── longtable.py   # tidy long table (CSV/Parquet)
└── pipeline.py    # orchestration: fetch → transform → align → model → write
run.py             # command-line entry point
```

## Data sources

| Data | Source |
| --- | --- |
| Equity (prices, financials, market cap, dividends) | Yahoo Finance via `yfinance` |
| 1-Year Treasury (`DGS1`), SOFR | FRED — same data as the Federal Reserve H.15 release |

## Known limitations

Upstream/source realities, not pipeline bugs (see the glossary for context):

- Non-dividend payers (e.g. **AMZN**) have blank dividend fields.
- Banks (e.g. **PNC**) don't report a clean current/non-current split; the
  toolkit falls back to `Total Debt − Long-term Debt` for short-term debt.
- Yahoo's free tier returns ~5–7 quarters of quarterly statements; annual
  covers 2 fiscal years.
- Dual-class names (e.g. **DELL**): the one-day reference-share method recovers
  the *total* share count so market cap reconciles.
- The **Merton/KMV** model is a transparent baseline; the instructor's **TIC**
  model (`credit.TICModel`, currently a stub) is the eventual method and reuses
  the same interface. Probabilities for large investment-grade firms are
  legitimately near zero — read the **distance to default** to compare them.

## License

[MIT](LICENSE)
