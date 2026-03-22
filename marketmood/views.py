import json
from django.shortcuts import render
from marketmood.pipeline.supabase_client import get_client
from django.http import HttpResponse
from datetime import datetime, timezone, timedelta

# Create your views here.


ZONE_CONFIG = {
    # Europe
    "DACH": {
        "countries": ["DE", "AT", "CH", "LI"],
        "label": "DACH",
    },
    "Western Europe": {
        "countries": ["FR", "GB", "NL", "BE", "IE", "LU"],
        "label": "Western Europe",
    },
    "Northern Europe": {
        "countries": ["SE", "NO", "DK", "FI", "IS"],
        "label": "Northern Europe",
    },
    "Southern Europe": {
        "countries": ["IT", "ES", "PT", "GR", "HR", "CY", "MT", "MC", "SM", "AD"],
        "label": "Southern Europe",
    },
    "Eastern Europe": {
        "countries": ["PL", "CZ", "HU", "RO", "SK", "BG"],
        "label": "Eastern Europe",
    },
    "Balkans": {
        "countries": ["RS", "BA", "MK", "AL", "ME", "SI", "XK"],
        "label": "Balkans",
    },
    "Baltic States": {
        "countries": ["EE", "LV", "LT"],
        "label": "Baltic States",
    },
    # Americas
    "USA": {
        "countries": ["US"],
        "label": "USA",
    },
    "Canada": {
        "countries": ["CA"],
        "label": "Canada",
    },
    "Central America": {
        "countries": ["MX", "GT", "HN", "CR", "PA", "NI", "SV", "BZ"],
        "label": "Central America",
    },
    "Caribbean": {
        "countries": ["CU", "DO", "JM", "TT", "HT"],
        "label": "Caribbean",
    },
    "Andean States": {
        "countries": ["CO", "VE", "PE", "EC", "GY", "SR"],
        "label": "Andean States",
    },
    "Brazil": {
        "countries": ["BR"],
        "label": "Brazil",
    },
    "Southern Cone": {
        "countries": ["AR", "CL", "UY", "BO", "PY"],
        "label": "Southern Cone",
    },
    # Asia & Oceania
    "China": {
        "countries": ["CN"],
        "label": "China",
    },
    "Japan": {
        "countries": ["JP"],
        "label": "Japan",
    },
    "India": {
        "countries": ["IN"],
        "label": "India",
    },
    "Southeast Asia": {
        "countries": ["SG", "TH", "VN", "MY", "ID", "PH", "BD", "MM", "KH", "LA"],
        "label": "Southeast Asia",
    },
    "Korea & Taiwan": {
        "countries": ["KR", "TW"],
        "label": "Korea & Taiwan",
    },
    "Central Asia": {
        "countries": ["KZ", "UZ", "TM", "KG", "TJ", "AF", "PK", "MN", "NP", "LK"],
        "label": "Central Asia",
    },
    "Oceania": {
        "countries": ["AU", "NZ", "PG", "FJ", "SB", "VU", "WS", "TO"],
        "label": "Oceania",
    },
    # Africa & Middle East
    "North Africa": {
        "countries": ["EG", "MA", "TN", "DZ", "LY", "SD", "MR"],
        "label": "North Africa",
    },
    "West Africa": {
        "countries": ["NG", "GH", "SN", "CI", "ML", "CM", "CD", "CG", "GA", "GQ", "LR", "SL", "GN", "BJ", "TG", "BF", "NE"],
        "label": "West Africa",
    },
    "East Africa": {
        "countries": ["ET", "KE", "TZ", "UG", "RW", "SO", "SS", "TD", "BI", "DJ", "ER"],
        "label": "East Africa",
    },
    "Southern Africa": {
        "countries": ["ZA", "ZW", "MZ", "ZM", "BW", "AO", "NA", "LS", "SZ", "MG"],
        "label": "Southern Africa",
    },
    "Middle East": {
        "countries": ["SA", "AE", "IL", "JO", "LB", "TR", "IR", "IQ", "SY", "PS"],
        "label": "Middle East",
    },
    "Gulf States": {
        "countries": ["QA", "KW", "BH", "OM", "YE"],
        "label": "Gulf States",
    },
    "Russia & CIS": {
        "countries": ["RU", "UA", "BY", "MD", "GE", "AZ", "AM"],
        "label": "Russia & CIS",
    },
}


def _get_latest_snapshots() -> dict:
    """Holt den neuesten Snapshot pro Region aus Supabase."""
    client = get_client()
    result = (
        client.table("mood_snapshots")
        .select("*")
        .order("created_at", desc=True)
        .limit(200)
        .execute()
    )

    # Neuesten Snapshot pro Region
    latest = {}
    for row in result.data:
        region = row["region"]
        if region not in latest:
            latest[region] = row
    return latest


def _build_zone_data(snapshots: dict) -> dict:
    zones = {}
    for zone_key, config in ZONE_CONFIG.items():
        countries_data = []
        scores = []

        for country in config["countries"]:
            snap = snapshots.get(country)
            if snap:
                countries_data.append(
                    {
                        "code": country,
                        "score": snap["final_score"],  # ← Aggregator Option B Score!
                        "label": snap["final_label"],
                        "article_count": snap["article_count"],
                        "top_headlines": snap["top_headlines"],
                        "score_finance": snap.get("score_finance"),
                        "score_geopolitics": snap.get("score_geopolitics"),
                        "score_energy": snap.get("score_energy"),
                        "score_politics": snap.get("score_politics"),
                        "score_general": snap.get("score_general"),
                    }
                )
                scores.append(snap["final_score"])  # ← Option B Score
            else:
                countries_data.append(
                    {
                        "code": country,
                        "score": None,
                        "label": "no_data",
                    }
                )

        zone_score = round(sum(scores) / len(scores), 4) if scores else None
        zone_label = "no_data"
        if zone_score is not None:
            if zone_score >= 0.05:
                zone_label = "bullish"
            elif zone_score <= -0.05:
                zone_label = "bearish"
            else:
                zone_label = "neutral"

        zones[zone_key] = {
            "label": config["label"],
            "score": zone_score,
            "mood": zone_label,
            "countries": countries_data,
            "active": len(scores) > 0,
        }

    return zones


def _get_chart_data(region: str) -> dict:
    """Holt Chart-Daten für eine Region."""
    client = get_client()

    # Heute stündlich
    from datetime import datetime, timezone, timedelta

    since_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    since_14d = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    today = (
        client.table("mood_snapshots")
        .select("created_at, final_score, final_label")
        .eq("region", region)
        .gte("created_at", since_24h)
        .order("created_at", desc=False)
        .execute()
    )

    days14 = (
        client.table("mood_snapshots")
        .select("created_at, final_score")
        .eq("region", region)
        .gte("created_at", since_14d)
        .order("created_at", desc=False)
        .execute()
    )

    return {
        "today": today.data,
        "days14": days14.data,
    }


def dashboard(request):
    import json
    snapshots  = _get_latest_snapshots()
    zones      = _build_zone_data(snapshots)

    context = {
        "zones":        zones,
        "zones_json":   json.dumps(zones),  # ← neu für Weltkarte
        "default_zone": "DACH",
        "active_zones": [k for k, v in zones.items() if v["active"]],
    }
    return render(request, "marketmood/dashboard.html", context)

def _get_country_news(country_code: str, days: int = 14) -> dict:
    
    client = get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    print(f"[NEWS] ← CALLED for {country_code}")  # ← ganz oben VOR result!

    result = client.table("articles")\
        .select("title, url, topic, vader_compound, vader_label, source, created_at, published")\
        .eq("source_region", country_code)\
        .gte("created_at", since)\
        .order("published", desc=True)\
        .limit(100)\
        .execute()

    print(f"[NEWS] Result count: {len(result.data)}")  # ← NACH result!
    if result.data:
        print(f"[NEWS] First keys: {list(result.data[0].keys())}")

    # Gruppieren nach Topic
    by_topic = {}
    topics = ["finance", "geopolitics", "energy", "technology",
              "health", "crime", "politics", "general"]
    for topic in topics:
        by_topic[topic] = [
            a for a in result.data
            if a["topic"] == topic
        ]
    return by_topic


def zone_detail(request, zone_key: str):
    """HTMX Partial — Zone-Detail Panel."""
    print(f"[ZONE_DETAIL] ← CALLED for {zone_key}") 
    

    snapshots = _get_latest_snapshots()
    zones     = _build_zone_data(snapshots)
    zone      = zones.get(zone_key)

    if not zone:
        return HttpResponse("Zone not found", status=404)

    # Chart-Daten für aktive Länder
    charts = {}
    news   = {}
    for country in zone["countries"]:
        if country["label"] != "no_data":
            charts[country["code"]] = _get_chart_data(country["code"])
            try:
                news[country["code"]] = _get_country_news(country["code"])
                print(f"[ZONE] News loaded for {country['code']}: {len(news[country['code']]['finance'])} finance articles")
            except Exception as e:
                print(f"[ZONE] Error loading news for {country['code']}: {e}")
                news[country["code"]] = {}

    context = {
    "zone":       zone,
    "zone_key":   zone_key,
    "charts":     json.dumps(charts),
    "news":       json.dumps(news),
    "news_topics": ["finance", "geopolitics", "energy", "technology", 
                    "health", "crime", "politics", "general"],
}
    return render(request, "marketmood/partials/zone_panel.html", context)

def _get_country_news(country_code: str, days: int = 14) -> dict:
    """Holt Artikel der letzten 14 Tage pro Topic."""
    from datetime import datetime, timezone, timedelta
    client = get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = client.table("articles")\
        .select("title, url, topic, vader_compound, vader_label, source, created_at, published")\
        .eq("source_region", country_code)\
        .gte("created_at", since)\
        .order("published", desc=True)\
        .limit(100)\
        .execute()

    # Gruppieren nach Topic
    by_topic = {}
    topics = ["finance", "geopolitics", "energy", "technology", 
              "health", "crime", "politics", "general"]
    for topic in topics:
        by_topic[topic] = [
            a for a in result.data 
            if a["topic"] == topic
        ]
    return by_topic
