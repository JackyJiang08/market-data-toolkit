# Market Data Toolkit

A small, professional data pipeline that pulls a curated set of **equity** and
**macro-rate** market data for any list of companies and writes
analyst-friendly Excel workbooks plus a machine-readable tidy dataset.

Equity data comes from [Yahoo Finance](https://finance.yahoo.com) via
`yfinance`; interest rates come from [FRED](https://fred.stlouisfed.org/) (the
St. Louis Fed's distribution of the Federal Reserve **H.15** release).

---

## Features

- **Per-company workbooks** (`output/<TICKER>_data.xlsx`) — one tab per data type
- **Master roll-up** (`output/_MASTER_summary.xlsx`) — cross-company comparison
- **Tidy long table** (`output/all_companies_long.{csv,parquet}`) — one flat
  fact table for databases, BI, and pivot analysis
- **Macro rates** — daily 1-Year Treasury (`DGS1`) and SOFR
- **Data provenance** — every record carries an extraction timestamp (`AsOf`)
  and its source, so a pull is reproducible and auditable
- **Resilient** — exponential-backoff retries for Yahoo rate-limiting, and
  per-ticker error isolation (one bad symbol never aborts the run)

## What it collects

**Per company** — `output/<TICKER>_data.xlsx`

| Tab | Contents |
| --- | --- |
| Summary | Market Cap, Shares Outstanding (traded class + implied total), Last Close, Dividend (rate & yield), sector/industry, provenance |
| Debt & Liabilities | Total Debt, Total Liabilities, Short-term/Current Debt, Short-term/Current Liabilities, Long-term Debt, Long-term Liabilities (time series) |
| Price History | Daily OHLC, Volume, Adj Close, and the dividend/split adjustment factor |
| MarketCap History | Estimated market cap over time |
| Dividends | Dividend cash events |
| Q / Annual statements | Income Statement, Balance Sheet, Cash Flow (quarterly and annual) |

**Master roll-up** — `output/_MASTER_summary.xlsx`: `Company Summary`,
`Debt & Liab (latest)`, `Macro Rates`.

**Tidy long table** — `output/all_companies_long.{csv,parquet}` with columns
`Ticker, AsOf, Category, Period, Metric, Value`.

## Installation

```bash
pip3 install -r requirements.txt
```

Requires Python 3.8+.

## Usage

```bash
python3 stock_data_pipeline.py                 # default universe, 2y
python3 stock_data_pipeline.py AAPL MSFT       # custom tickers
python3 stock_data_pipeline.py --years 3       # custom window
python3 stock_data_pipeline.py --no-rates      # skip macro-rate download
```

| Flag | Meaning |
| --- | --- |
| `--years` | Years of price history & financials (default `2`) |
| `--no-rates` | Skip the FRED 1Y-Treasury / SOFR download |

macOS users can also double-click **`Download Stocks.command`**, which prompts
for tickers and a window, runs the pipeline, and opens the output folder.

## Data sources

| Data | Source |
| --- | --- |
| Equity (prices, financials, market cap, dividends) | Yahoo Finance via `yfinance` |
| 1-Year Treasury (`DGS1`), SOFR | FRED — same data as the Federal Reserve H.15 release |

## Known limitations

These are upstream/source realities, not pipeline bugs:

- Non-dividend payers (e.g. **AMZN**) have blank dividend fields.
- Banks (e.g. **PNC**) don't report a current/non-current balance-sheet split,
  so some debt-schedule rows are unavailable.
- Yahoo's free tier returns only ~5–7 quarters of quarterly statements, so the
  quarterly window is as deep as the source allows; annual covers 2 fiscal years.
- Dual-class names (e.g. **DELL**) report `sharesOutstanding` for the traded
  class only; the toolkit also surfaces the implied total so market cap reconciles.

## License

[MIT](LICENSE)
