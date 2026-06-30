#!/bin/bash
# ===========================================================================
#  Market Data Toolkit  --  double-click launcher
# ===========================================================================
#  Produces, into the "output" folder:
#    - per-company workbooks: prices, dividends, market cap, debt &
#      liabilities, the date-aligned model panel, quarterly + annual
#      financials, and a Merton/KMV credit estimate
#    - a master workbook: company + credit + debt summaries and macro rates
#    - a tidy long table (CSV/Parquet) for analysis
# ===========================================================================

cd "$(dirname "$0")" || exit 1

# --- locate a Python interpreter -------------------------------------------
PY="/Users/jackyjiang/opt/anaconda3/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"
if [ -z "$PY" ]; then
    echo "ERROR: python3 not found. Install Python 3, then try again."
    echo "Press Enter to close."; read; exit 1
fi

clear
echo "============================================================"
echo "   MARKET DATA TOOLKIT"
echo "   prices + market cap + debt/liabilities + financials"
echo "   + 1Y Treasury & SOFR + Merton/KMV credit model"
echo "============================================================"
echo
echo "Default universe (press Enter to use):"
echo "   COST KO DELL ORCL PNC WMT INTU AMZN T KHC"
echo
read -p "Ticker symbol(s), or Enter for the default 10: " TICKERS
read -p "Years of history/financials [2]: " YEARS
YEARS="${YEARS:-2}"

echo
echo "------------------------------------------------------------"
"$PY" run.py $TICKERS --years "$YEARS"
STATUS=$?
echo "------------------------------------------------------------"
if [ $STATUS -eq 0 ]; then
    echo "Finished. Opening the output folder..."
    open output
else
    echo "Finished with errors (exit $STATUS). See messages above."
fi
echo
echo "Press Enter to close this window."
read
