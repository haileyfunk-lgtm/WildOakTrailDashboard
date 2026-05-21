"""
Shopify Admin API client for the dashboard.

Reads credentials from .streamlit/secrets.toml:
    [shopify]
    shop_domain = "wild-oak-trail.myshopify.com"
    access_token = "shpat_..."
    api_version = "2026-04"

All fetchers are cached for 5 minutes via st.cache_data so the dashboard
doesn't hammer the API on every rerun.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import streamlit as st


SHOP_TZ = ZoneInfo("America/Winnipeg")


def _cfg():
    s = st.secrets.get("shopify", {})
    return {
        "shop": s.get("shop_domain"),
        "token": s.get("access_token"),
        "version": s.get("api_version", "2026-04"),
    }


def is_configured() -> bool:
    c = _cfg()
    return bool(c["shop"] and c["token"])


def _headers():
    c = _cfg()
    return {
        "X-Shopify-Access-Token": c["token"],
        "Content-Type": "application/json",
    }


def _rest(path: str, params: dict | None = None) -> dict:
    c = _cfg()
    url = f"https://{c['shop']}/admin/api/{c['version']}/{path}"
    r = requests.get(url, headers=_headers(), params=params or {}, timeout=15)
    r.raise_for_status()
    return r.json()


def _gql(query: str, variables: dict | None = None) -> dict:
    c = _cfg()
    url = f"https://{c['shop']}/admin/api/{c['version']}/graphql.json"
    r = requests.post(
        url,
        headers=_headers(),
        json={"query": query, "variables": variables or {}},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        raise RuntimeError(f"Shopify GraphQL errors: {body['errors']}")
    return body["data"]


def _today_bounds() -> tuple[str, str]:
    now = datetime.now(SHOP_TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), now.isoformat()


def _mtd_bounds() -> tuple[str, str]:
    now = datetime.now(SHOP_TZ)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start.isoformat(), now.isoformat()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_revenue_window(start_iso: str, end_iso: str) -> dict:
    """Sum order count + gross/net revenue between two ISO timestamps."""
    query = """
    query Orders($q: String!, $cursor: String) {
      orders(first: 250, query: $q, after: $cursor, sortKey: CREATED_AT) {
        pageInfo { hasNextPage endCursor }
        nodes {
          createdAt
          currentTotalPriceSet { shopMoney { amount currencyCode } }
          subtotalPriceSet { shopMoney { amount } }
          displayFinancialStatus
          test
        }
      }
    }
    """
    q = f"created_at:>='{start_iso}' AND created_at:<='{end_iso}' AND test:false"
    cursor = None
    orders = 0
    gross = 0.0
    subtotal = 0.0
    while True:
        data = _gql(query, {"q": q, "cursor": cursor})
        page = data["orders"]
        for o in page["nodes"]:
            if o.get("test"):
                continue
            orders += 1
            try:
                gross += float(o["currentTotalPriceSet"]["shopMoney"]["amount"])
                subtotal += float(o["subtotalPriceSet"]["shopMoney"]["amount"])
            except (TypeError, KeyError):
                pass
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    aov = (gross / orders) if orders else 0.0
    return {
        "orders": orders,
        "gross": round(gross, 2),
        "subtotal": round(subtotal, 2),
        "aov": round(aov, 2),
    }


def fetch_today() -> dict:
    s, e = _today_bounds()
    return fetch_revenue_window(s, e)


def fetch_mtd() -> dict:
    s, e = _mtd_bounds()
    return fetch_revenue_window(s, e)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recent_orders(limit: int = 10) -> list[dict]:
    """Most recent N orders."""
    query = """
    query Recent($n: Int!) {
      orders(first: $n, sortKey: CREATED_AT, reverse: true, query: "test:false") {
        nodes {
          name
          createdAt
          displayFinancialStatus
          displayFulfillmentStatus
          customer { firstName lastName }
          currentTotalPriceSet { shopMoney { amount currencyCode } }
        }
      }
    }
    """
    data = _gql(query, {"n": limit})
    out = []
    for o in data["orders"]["nodes"]:
        c = o.get("customer") or {}
        first = c.get("firstName") or ""
        last = c.get("lastName") or ""
        name = (first + " " + last).strip() or "—"
        out.append({
            "order": o.get("name", ""),
            "customer": name,
            "total": float(o["currentTotalPriceSet"]["shopMoney"]["amount"]),
            "currency": o["currentTotalPriceSet"]["shopMoney"]["currencyCode"],
            "financial": (o.get("displayFinancialStatus") or "").lower(),
            "fulfillment": (o.get("displayFulfillmentStatus") or "").lower(),
            "created_at": o.get("createdAt"),
        })
    return out


@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_landing_pages_7d(limit: int = 5) -> list[dict]:
    """Top landing pages by sessions over the last 7 days, via ShopifyQL."""
    shopifyql = (
        f"FROM sessions "
        f"SHOW sessions "
        f"GROUP BY landing_page_url "
        f"SINCE -7d UNTIL today "
        f"ORDER BY sessions DESC "
        f"LIMIT {int(limit)}"
    )
    query = """
    query Lp($q: String!) {
      shopifyqlQuery(query: $q) {
        parseErrors
        tableData {
          columns { name dataType }
          rows
        }
      }
    }
    """
    data = _gql(query, {"q": shopifyql})
    resp = data.get("shopifyqlQuery") or {}
    tbl = resp.get("tableData")
    if not tbl:
        return []
    out = []
    for record in tbl.get("rows") or []:
        # ShopifyQL returns rows as dicts keyed by column name.
        if isinstance(record, list):
            cols = [c["name"] for c in tbl.get("columns") or []]
            record = dict(zip(cols, record))
        url = record.get("landing_page_url") or ""
        path = url
        if "://" in url:
            try:
                path = "/" + url.split("://", 1)[1].split("/", 1)[1]
            except IndexError:
                path = "/"
        out.append({
            "url": url,
            "path": path or "/",
            "sessions": int(record.get("sessions") or 0),
        })
    return out


@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_products_mtd(limit: int = 5) -> list[dict]:
    """Top products this month by gross revenue from line items."""
    s, e = _mtd_bounds()
    query = """
    query Sales($q: String!, $cursor: String) {
      orders(first: 250, query: $q, after: $cursor, sortKey: CREATED_AT) {
        pageInfo { hasNextPage endCursor }
        nodes {
          lineItems(first: 50) {
            nodes {
              title
              quantity
              originalTotalSet { shopMoney { amount } }
            }
          }
        }
      }
    }
    """
    q = f"created_at:>='{s}' AND created_at:<='{e}' AND test:false"
    cursor = None
    totals: dict[str, dict] = {}
    while True:
        data = _gql(query, {"q": q, "cursor": cursor})
        page = data["orders"]
        for o in page["nodes"]:
            for li in o["lineItems"]["nodes"]:
                title = li.get("title") or "(unknown)"
                qty = int(li.get("quantity") or 0)
                amount = float(li["originalTotalSet"]["shopMoney"]["amount"])
                slot = totals.setdefault(title, {"title": title, "units": 0, "revenue": 0.0})
                slot["units"] += qty
                slot["revenue"] += amount
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    rows = sorted(totals.values(), key=lambda r: r["revenue"], reverse=True)
    for r in rows:
        r["revenue"] = round(r["revenue"], 2)
    return rows[:limit]
