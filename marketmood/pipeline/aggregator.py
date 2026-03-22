


# mood/pipeline/aggregator.py
from datetime import datetime, timezone
from marketmood.pipeline.supabase_client import get_client

def _score_to_label(score: float) -> str:
    if score >= 0.05:  return "bullish"
    if score <= -0.05: return "bearish"
    return "neutral"

def _topic_scores(articles: list) -> dict:
    """
    Option B — Gewichteter Durchschnitt nach Topic.
    Jedes Topic wird einmal gezählt — egal wie viele Artikel.
    Verhindert dass Iran (10 Artikel) den Score dominiert.
    """
    topics = ["finance", "geopolitics", "energy", "technology",
              "health", "crime", "politics", "general"]
    scores = {}

    for topic in topics:
        bucket = [a["vader_compound"] for a in articles if a.get("topic") == topic]
        scores[topic] = round(sum(bucket) / len(bucket), 4) \
                        if len(bucket) >= 3 else None

    return scores

def _final_score(topic_scores: dict) -> float:
    """
    Durchschnitt der Topic-Scores (nicht der Artikel).
    Nur Topics mit Artikeln werden gewertet.
    """
    valid = [v for v in topic_scores.values() if v is not None]
    return round(sum(valid) / len(valid), 4) if valid else 0.0

def _top_headlines(articles: list, n: int = 3) -> list:
    """Top N — nur relevante Topics, nach absolutem Score."""
    relevant = [
        a for a in articles
        if a.get("topic") in ["finance", "geopolitics", "energy", "politics"]
    ]
    pool = relevant if len(relevant) >= n else articles

    sorted_articles = sorted(
        pool,
        key=lambda a: abs(a.get("vader_compound", 0)),
        reverse=True
    )
    return [
        {
            "title":  a["title"],
            "url":    a["url"],
            "score":  a["vader_compound"],
            "label":  a["vader_label"],
            "source": a["source"],
        }
        for a in sorted_articles[:n]
    ]

def build_snapshot(articles: list, region: str) -> dict:
    """
    Baut einen Mood-Snapshot aus Artikeln einer Region.
    Verwendet Option B — gewichteter Durchschnitt nach Topic.
    """
    regional = [a for a in articles if a.get("region") == region]

    if not regional:
        print(f"[AGGREGATOR] No articles for region {region}")
        return None

    topic_scores = _topic_scores(regional)
    final        = _final_score(topic_scores)
    label        = _score_to_label(final)
    headlines    = _top_headlines(regional)

    bullish = sum(1 for a in regional if a.get("vader_label") == "bullish")
    bearish = sum(1 for a in regional if a.get("vader_label") == "bearish")
    neutral = sum(1 for a in regional if a.get("vader_label") == "neutral")

    snapshot = {
    "region":            region,
    "final_score":       final,
    "final_label":       label,
    "score_finance":     topic_scores.get("finance"),
    "score_geopolitics": topic_scores.get("geopolitics"),
    "score_energy":      topic_scores.get("energy"),
    "score_politics":    topic_scores.get("politics"),
    "score_general":     topic_scores.get("general"),
    "score_technology":  topic_scores.get("technology"),
    "score_health":      topic_scores.get("health"),
    "score_crime":       topic_scores.get("crime"),
    "article_count":     len(regional),
    "bullish_count":     bullish,
    "bearish_count":     bearish,
    "neutral_count":     neutral,
    "top_headlines":     headlines,
}

    print(f"[AGGREGATOR] [{region}] Score: {final} | {label} | "
          f"Topics: {topic_scores}")
    return snapshot

def save_snapshot(snapshot: dict) -> bool:
    """Snapshot in mood_snapshots Tabelle speichern."""
    if not snapshot:
        return False
    try:
        get_client().table("mood_snapshots").insert(snapshot).execute()
        print(f"[AGGREGATOR] Snapshot saved for {snapshot['region']}")
        return True
    except Exception as e:
        print(f"[AGGREGATOR] Error saving snapshot: {e}")
        return False

def run_aggregator(articles: list, regions: list = None) -> list:
    if regions is None:
        regions = sorted({a.get("region") for a in articles if a.get("region")})

    snapshots = []
    for reg in regions:
        snapshot = build_snapshot(articles, reg)
        if snapshot:
            save_snapshot(snapshot)
            snapshots.append(snapshot)

    return snapshots
