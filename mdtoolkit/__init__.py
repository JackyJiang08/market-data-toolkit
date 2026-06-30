"""Market Data Toolkit -- equity & macro-rate data pipeline with a structural
credit-risk model.

Public API:
    from mdtoolkit import RunConfig, run
    run(RunConfig(tickers=["KO", "WMT"], years=2))
"""

from __future__ import annotations

from .pipeline import RunConfig, run

__version__ = "0.2.0"
__all__ = ["RunConfig", "run", "__version__"]
