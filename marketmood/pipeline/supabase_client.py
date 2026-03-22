

# mood/pipeline/supabase_client.py
# ============================================================
# SUPABASE CLIENT — read and write articles
# V1: articles table | V2: + mood_snapshots table
# ============================================================

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# CLIENT
# ============================================================

def get_client() -> Client:
    """Initialize and return Supabase client"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError("[SUPABASE] Missing SUPABASE_URL or SUPABASE_KEY in .env")

    return create_client(url, key)


# ============================================================
# WRITE
# ============================================================

def save_articles(articles: list) -> dict:
    """
    Save list of analyzed articles to Supabase
    V1 fields filled — V2/V3 fields set to empty/None
    """
    if not articles:
        print("[SUPABASE] No articles to save")
        return {"saved": 0, "errors": 0}

    client = get_client()
    saved  = 0
    errors = 0

    for article in articles:
        try:
            row = {
                # V1 — active
                "source":           article.get("source"),
                "source_region":    article.get("region"),
                "title":            article.get("title"),
                "description":      article.get("description"),
                "url":              article.get("url"),
                "published":        article.get("published"),
                "topic":            article.get("topic"),
                "matched_keywords": article.get("matched_keywords", []),
                "vader_compound":   article.get("vader_compound"),
                "vader_label":      article.get("vader_label"),

                # V2 — prepared, empty for now
                "matched_companies": [],
                "company_regions":   [],
                "mentioned_regions": [],
                "finbert_compound":  None,
                "finbert_label":     None,

                # V3 — prepared, empty for now
                "translation":       None,
                "original_language": article.get("language", "EN"),
                "spacy_entities":    [],
            }

            client.table("articles").upsert(row, on_conflict="url").execute()
            saved += 1

        except Exception as e:
            print(f"[SUPABASE] Error saving '{article.get('title', '?')}': {e}")
            errors += 1

    print(f"[SUPABASE] Saved: {saved} | Errors: {errors}")
    return {"saved": saved, "errors": errors}


# ============================================================
# READ
# ============================================================

def get_articles(region: str = "DE", limit: int = 50) -> list:
    """Fetch latest articles from Supabase for a given region"""
    client = get_client()

    response = client.table("articles")\
        .select("*")\
        .eq("source_region", region)\
        .order("created_at", desc=True)\
        .limit(limit)\
        .execute()

    return response.data


def get_latest_mood(region: str = "DE") -> dict:
    """
    Calculate average mood from latest 50 articles
    Returns mood score, label and article count
    """
    articles = get_articles(region, limit=50)

    if not articles:
        return {
            "region":    region,
            "avg_score": 0.0,
            "label":     "neutral",
            "count":     0,
        }

    scores = [
        a["vader_compound"]
        for a in articles
        if a["vader_compound"] is not None
    ]

    avg = round(sum(scores) / len(scores), 4) if scores else 0.0

    if avg >= 0.05:
        label = "bullish"
    elif avg <= -0.05:
        label = "bearish"
    else:
        label = "neutral"

    return {
        "region":    region,
        "avg_score": avg,
        "label":     label,
        "count":     len(scores),
    }