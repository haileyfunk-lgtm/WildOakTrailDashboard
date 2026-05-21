"""
Data sources for the Agentic OS Dashboard.

Currently file-based. Set up a refresh job (or OAuth + Sheets API) later
to keep these in sync automatically. For now `bookkeeping.json` is a manual
export of the P&L sheet — re-run the parser when numbers change.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_bookkeeping() -> dict:
    f = DATA_DIR / "bookkeeping.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text())
