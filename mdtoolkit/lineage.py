"""Data provenance / lineage.

Financial data is restated over time and market values change every second, so
a pull is only meaningful if you know *when* it was taken and *where* it came
from. Every record the toolkit emits carries this stamp, which is what makes a
run reproducible and auditable.
"""

from __future__ import annotations

from datetime import datetime

try:
    import yfinance as yf
    _YF_VERSION = getattr(yf, "__version__", "?")
except Exception:  # pragma: no cover
    _YF_VERSION = "?"

# Captured once at import so every record in a single run shares one stamp.
RUN_TIMESTAMP: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

EQUITY_SOURCE: str = f"Yahoo Finance (yfinance {_YF_VERSION})"
RATES_SOURCE: str = "FRED / Federal Reserve H.15 (DGS1, SOFR)"
