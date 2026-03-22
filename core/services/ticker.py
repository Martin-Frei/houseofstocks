
# core/services/ticker.py
# ============================================================
# TICKER SERVICE
# Holt Live-Daten für den Ticker in der Navigation:
# - Aktienkurse aus SPV2 Supabase (neueste verfügbare)
# - Finance News aus GMM Supabase (eine pro Zone, letzte 2h)
# - Globaler GMM Stimmungsscore
# TODO V3: AWS als primäres Backend, Supabase als Fallback
# ============================================================

import httpx
from django.conf import settings
from datetime import datetime, timedelta, timezone

# 28 Zonen → Länder Mapping (gleich wie in marketmood/views.py)
ZONE_COUNTRIES = {
    "DACH":           ["DE", "AT", "CH", "LI"],
    "Western Europe": ["FR", "GB", "NL", "BE", "IE", "LU"],
    "Northern Europe":["SE", "NO", "DK", "FI", "IS"],
    "Southern Europe":["IT", "ES", "PT", "GR", "HR", "CY", "MT"],
    "Eastern Europe": ["PL", "CZ", "HU", "RO", "SK", "BG"],
    "Balkans":        ["RS", "BA", "MK", "AL", "ME", "SI", "XK"],
    "Baltic States":  ["EE", "LV", "LT"],
    "USA":            ["US"],
    "Canada":         ["CA"],
    "Central America":["MX", "GT", "HN", "CR", "PA", "NI", "SV", "BZ"],
    "Caribbean":      ["CU", "DO", "JM", "TT", "HT"],
    "Andean States":  ["CO", "VE", "PE", "EC", "GY", "SR"],
    "Brazil":         ["BR"],
    "Southern Cone":  ["AR", "CL", "UY", "BO", "PY"],
    "China":          ["CN"],
    "Japan":          ["JP"],
    "India":          ["IN"],
    "Southeast Asia": ["SG", "TH", "VN", "MY", "ID", "PH", "BD", "MM", "KH", "LA"],
    "Korea & Taiwan": ["KR", "TW"],
    "Central Asia":   ["KZ", "UZ", "TM", "KG", "TJ", "AF", "PK", "MN", "NP", "LK"],
    "Oceania":        ["AU", "NZ", "PG", "FJ", "SB", "VU", "WS", "TO"],
    "North Africa":   ["EG", "MA", "TN", "DZ", "LY", "SD", "MR"],
    "West Africa":    ["NG", "GH", "SN", "CI", "ML", "CM", "CD", "CG", "GA"],
    "East Africa":    ["ET", "KE", "TZ", "UG", "RW", "SO", "SS", "TD", "BI"],
    "Southern Africa":["ZA", "ZW", "MZ", "ZM", "BW", "AO", "NA", "LS", "SZ", "MG"],
    "Middle East":    ["SA", "AE", "IL", "JO", "LB", "TR", "IR", "IQ", "SY", "PS"],
    "Gulf States":    ["QA", "KW", "BH", "OM", "YE"],
    "Russia & CIS":   ["RU", "UA", "BY", "MD", "GE", "AZ", "AM"],
}

# Symbole für Ticker
TICKER_SYMBOLS = ["AXP", "BAC", "BLK", "C", "COF", "GS", "JPM", "MS", "PNC", "TFC", "USB", "WFC"]
INDEX_SYMBOLS  = ["SPX", "XLF", "VIX", "DXY"]


def get_stock_prices() -> list:
    """
    Holt neueste Aktienkurse aus SPV2 Supabase.
    Gibt Liste von {symbol, price, direction} zurück.
    """
    try:
        r1 = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/predictions",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params={"select": "date_for", "order": "date_for.desc", "limit": "1"},
            timeout=5.0
        )
        print(f"[TICKER] SPV2 Status: {r1.status_code}")
        print(f"[TICKER] SPV2 Response: {r1.text[:200]}")
        
        rows = r1.json()
        if not rows:
            print("[TICKER] SPV2: keine Daten")
            return []

        latest_date = r1.json()[0]['date_for']

        r2 = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/predictions",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params={
                "select": "symbol,last_close,lstm_dir",
                "date_for": f"eq.{latest_date}",
                "limit": "20"
            },
            timeout=5.0
        )
        rows = r2.json() if r2.status_code == 200 else []

        result = []
        for row in rows:
            if row.get('symbol') in TICKER_SYMBOLS + INDEX_SYMBOLS:
                price = row.get('last_close')
                result.append({
                    "type":      "stock",
                    "symbol":    row['symbol'],
                    "value":     f"${price:.2f}" if price else "—",
                    "direction": row.get('lstm_dir', '').upper(),
                    "url":       None,
                })
        return result

    except Exception as e:
        print(f"[TICKER] Stock prices error: {e}")
        return []


def get_zone_news() -> list:
    """
    Holt neueste Finance News pro Zone aus GMM Supabase.
    Letzte 6 Stunden, eine pro Zone, alphabetisch nach Zone.
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()

        response = httpx.get(
            f"{settings.SUPABASE_URL}/rest/v1/articles",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
            },
            params={
                "select": "title,url,source_region,topic,created_at",
                "topic":  "eq.finance",
                "created_at": f"gte.{since}",
                "order": "created_at.desc",
                "limit": "500"
            },
            timeout=8.0
        )
        articles = response.json() if response.status_code == 200 else []

        # Länder → Zone Mapping umkehren
        country_to_zone = {}
        for zone, countries in ZONE_COUNTRIES.items():
            for country in countries:
                country_to_zone[country] = zone

        # Eine News pro Zone (neueste)
        zone_news = {}
        for article in articles:
            region = article.get('source_region', '')
            zone   = country_to_zone.get(region)
            if zone and zone not in zone_news:
                zone_news[zone] = {
                    "type":   "news",
                    "symbol": zone.upper(),
                    "value":  article['title'][:80] + ('…' if len(article['title']) > 80 else ''),
                    "url":    article.get('url'),
                    "direction": "",
                }

        # Alphabetisch sortiert
        return [zone_news[z] for z in sorted(zone_news.keys()) if z in zone_news]

    except Exception as e:
        print(f"[TICKER] Zone news error: {e}")
        return []


def get_global_mood() -> dict:
    """Holt globalen GMM Score."""
    try:
        response = httpx.get(
            f"{settings.SUPABASE_URL}/rest/v1/mood_snapshots",
            headers={
                "apikey": settings.SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
            },
            params={
                "select": "final_score,final_label",
                "order": "created_at.desc",
                "limit": "50"
            },
            timeout=5.0
        )
        rows = response.json() if response.status_code == 200 else []
        if not rows:
            return {}

        scores = [r['final_score'] for r in rows if r.get('final_score') is not None]
        avg    = sum(scores) / len(scores) if scores else 0
        label  = "bullish" if avg >= 0.05 else "bearish" if avg <= -0.05 else "neutral"

        return {
            "type":      "mood",
            "symbol":    "GLOBAL",
            "value":     f"{'+' if avg >= 0 else ''}{avg:.2f}",
            "direction": label.upper(),
            "url":       None,
        }
    except Exception as e:
        print(f"[TICKER] Global mood error: {e}")
        return {}


def get_index_prices() -> list:
    """Holt Index Kurse aus ohlcv_data Tabelle (SPX, XLF, VIX, DXY)"""
    try:
        r = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/ohlcv_data",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params={
                "select": "Symbol,Close,Date",
                "Symbol": "in.(SPX,XLF,VIX,DXY)",
                "order": "Date.desc",
                "limit": "8"  # 2 pro Symbol für neuestes Datum
            },
            timeout=5.0
        )
        rows = r.json() if r.status_code == 200 else []

        # Neuesten Wert pro Symbol
        seen = {}
        for row in rows:
            sym = row.get('Symbol')
            if sym and sym not in seen:
                price = row.get('Close')
                seen[sym] = {
                    "type":      "stock",
                    "symbol":    sym,
                    "value":     f"${price:.2f}" if price else "—",
                    "direction": "",
                    "url":       None,
                }
        return list(seen.values())

    except Exception as e:
        print(f"[TICKER] Index prices error: {e}")
        return []


def get_ticker_data() -> list:
    stocks = get_stock_prices() + get_index_prices()  # ← Indizes dazu
    news   = get_zone_news()
    mood   = get_global_mood()

    ticker = []
    stock_iter = iter(stocks)

    for i, news_item in enumerate(news):
        if i % 3 == 0:
            for _ in range(2):
                try:
                    ticker.append(next(stock_iter))
                except StopIteration:
                    pass
        ticker.append(news_item)
        if i == 4 and mood:
            ticker.append(mood)

    ticker.extend(list(stock_iter))
    return ticker