"""
refresh_bookkeeping.py — pull the latest P&L from the Google Sheet and rewrite
data/bookkeeping.json so the dashboard's stat cards stay current.

First run: pops a browser to sign you in (uses credentials.json).
Subsequent runs: silent; uses cached token.json.

Usage:
    cd ~/Documents/agentic-os-dashboard
    python3 refresh_bookkeeping.py
"""

import json
from datetime import date
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SHEET_ID = "1q_vg0pXLQjiji3W3a63UPZiK5ej2yQWvVe05f2TbQQI"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

ROOT = Path(__file__).parent
CREDENTIALS = ROOT / "credentials.json"
TOKEN = ROOT / "token.json"
OUT = ROOT / "data" / "bookkeeping.json"

MONTHS = ["January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"]


def authenticate() -> Credentials:
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS.exists():
                raise SystemExit(
                    f"\nMissing {CREDENTIALS}.\n"
                    "Download an OAuth client JSON (Desktop app) from\n"
                    "Google Cloud Console → Credentials and save it as that path.\n"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return creds


def parse_money(s) -> float:
    s = str(s or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if s in ("", "-", "—"):
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return 0.0


def parse_int(s) -> int:
    s = str(s or "").strip().replace(",", "")
    if s in ("", "-", "—"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def parse_pct(s):
    s = str(s or "").strip().replace("%", "").replace(",", "").replace("\\", "")
    if s in ("", "-", "—", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def find_row(rows, label):
    target = label.lower().strip()
    for row in rows:
        if row and str(row[0]).lower().strip() == target:
            return row
    return []


def main():
    creds = authenticate()
    service = build("sheets", "v4", credentials=creds)

    # Biz P&L → company-level financials (post admin expenses + taxes).
    # Matches the spreadsheet's TOTAL NET INCOME row.
    biz_rows = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="'Biz P&L'!A1:Q60",
    ).execute().get("values", [])

    # Dashboard tab → Total Orders (not tracked in Biz P&L).
    dash_rows = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="'Dashboard'!A1:Z100",
    ).execute().get("values", [])

    if not biz_rows or not dash_rows:
        raise SystemExit("Sheet returned empty. Check SHEET_ID and that the account has access.")

    gross    = find_row(biz_rows, "GROSS INCOME")
    expenses = find_row(biz_rows, "TOTAL ADMIN. EXPENSES")
    net      = find_row(biz_rows, "TOTAL NET INCOME")
    orders   = find_row(dash_rows, "Total Orders")

    def margin_for(g_val, n_val):
        return round((n_val / g_val) * 100, 2) if g_val else None

    # Columns: 0=label, 1-12=Jan-Dec, 13=Total
    monthly = {}
    for i, name in enumerate(MONTHS, start=1):
        get = lambda r: r[i] if i < len(r) else ""
        g = parse_money(get(gross))
        n = parse_money(get(net))
        monthly[name] = {
            "gross":      g,
            "expenses":   parse_money(get(expenses)),
            "net":        n,
            "orders":     parse_int(get(orders)),
            "margin_pct": margin_for(g, n),
        }

    ytd_idx = 13
    get_ytd = lambda r: r[ytd_idx] if ytd_idx < len(r) else ""
    g_ytd = parse_money(get_ytd(gross))
    n_ytd = parse_money(get_ytd(net))
    ytd = {
        "gross":      g_ytd,
        "expenses":   parse_money(get_ytd(expenses)),
        "net":        n_ytd,
        "orders":     parse_int(get_ytd(orders)),
        "margin_pct": margin_for(g_ytd, n_ytd),
    }

    today = date.today()
    cur_name = MONTHS[today.month - 1]
    last_full_name = MONTHS[(today.month - 2) % 12]

    out = {
        "source": "Wild Oak Trail P&L (Google Sheet)",
        "sheet_id": SHEET_ID,
        "year": today.year,
        "as_of": today.isoformat(),
        "monthly": monthly,
        "ytd": ytd,
        "current_month_name": cur_name,
        "last_full_month_name": last_full_name,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT}")
    print(f"YTD net: ${ytd['net']:,.2f}  ·  YTD orders: {ytd['orders']}")


if __name__ == "__main__":
    main()
