


# mood/pipeline/fetcher.py
# ============================================================
# RSS FEED FETCHER — parse and normalize articles
# Supports all RSS feeds defined in api_sources.py
# V1: RSS only | V2: + NewsAPI adapter
# ============================================================

import feedparser
import re
from datetime import datetime, timezone
from .api_sources import FEED_SOURCES

import socket
socket.setdefaulttimeout(15)


# ============================================================
# HELPERS
# ============================================================

def clean_text(text: str) -> str:
    """Remove HTML tags, CDATA and extra whitespace"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ============================================================
# CORE FUNCTIONS
# ============================================================

def fetch_feed(source: dict) -> list:
    articles = []
    try:
        feed = feedparser.parse(source["url"])
        for entry in feed.entries:
            title       = clean_text(entry.get("title", ""))
            description = clean_text(entry.get("summary", ""))
            link        = entry.get("link", "")
            
            # ← alles eingerückt innerhalb for loop!
            published_parsed = (
                entry.get("published_parsed") or
                entry.get("updated_parsed") or
                None
            )
            if published_parsed:
                published = datetime(*published_parsed[:6]).isoformat()
            else:
                published = datetime.now(timezone.utc).isoformat()

            text = f"{title}. {description}".strip()

            if title:
                articles.append({
                    "source":      source["name"],
                    "region":      source["region"],
                    "language":    source.get("language", "EN"),
                    "category":    source["category"],
                    "title":       title,
                    "description": description,
                    "url":         link,
                    "published":   published,
                    "text":        text,
                })

    except Exception as e:
        print(f"[FETCHER] Error fetching {source['name']}: {e}")

    return articles


def fetch_all_sources(region: str = None) -> list:
    """
    Fetch all active feeds, optional region filter.
    If region is None → fetch all active feeds (DACH).
    Deduplicates by title — one article per unique headline.
    """
    all_articles = []
    seen_titles  = set()

    sources = [s for s in FEED_SOURCES if s["active"]]
    if region:
        sources = [s for s in sources if s["region"] == region]

    print(f"[FETCHER] Found {len(sources)} active feeds"
          + (f" for region {region}" if region else " (all regions)"))

    for source in sources:
        articles = fetch_feed(source)
        print(f"[FETCHER] [{source['region']}] {source['name']}: {len(articles)} articles")

        for article in articles:
            if article["title"] not in seen_titles:
                seen_titles.add(article["title"])
                all_articles.append(article)

    print(f"[FETCHER] Total: {len(all_articles)} unique articles")
    return all_articles