#!/bin/bash
# ===========================================================================
#  Equity & Rates Data Pipeline  --  double-click launcher
# ===========================================================================
#  Downloads, into the "output" folder:
#    - per-company workbooks: prices, dividends, market cap, debt &
#      liabilities, quarterly + annual financials
#    - a master workbook: company summary, debt snapshot, and macro rates
#      (1-Year Treasury + SOFR)
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
echo "   EQUITY & RATES DATA PIPELINE"
echo "   prices + dividends + market cap + debt/liabilities"
echo "   + quarterly/annual financials + 1Y Treasury & SOFR"
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
"$PY" stock_data_pipeline.py $TICKERS --years "$YEARS"
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
