

# mood/pipeline/sentiment.py
# ============================================================
# SENTIMENT ANALYSIS — VADER + custom finance lexicon
# V1: VADER only | V2: VADER + FinBERT hybrid
# ============================================================

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

# ============================================================
# FINANCE LEXICON — words VADER doesn't know
# Extends VADER with finance-specific sentiment weights
# ============================================================

FINANCE_LEXICON = {
    # Positive — Markets
    "profit_growth":        2.5,
    "record_profit":        2.5,
    "profit_surge":         2.5,
    "earnings_beat":        2.5,
    "revenue_growth":       2.0,
    "dividend_increase":    2.0,
    "market_rally":         2.0,
    "economic_recovery":    2.0,
    "rate_cut":             1.5,
    "acquisition":          1.5,
    "ipo":                  1.5,

    # Negative — Markets
    "profit_warning":      -2.5,
    "profit_slump":        -2.5,
    "market_crash":        -2.5,
    "recession":           -2.5,
    "insolvency":          -3.0,
    "bankruptcy":          -3.0,
    "mass_layoffs":        -2.5,
    "inflation_shock":     -2.5,
    "rate_hike":           -1.5,
    "sanctions":           -1.5,
    "trade_embargo":       -2.0,
    "economic_crisis":     -2.5,
    "debt_crisis":         -2.5,
    "market_selloff":      -2.0,
    "stock_plunge":        -2.5,

    # Negative — Geopolitics
    "war":                 -2.5,
    "military_offensive":  -2.5,
    "airstrike":           -2.0,
    "conflict":            -1.5,
    "ceasefire_collapse":  -2.0,
}


# ============================================================
# FUNCTIONS
# ============================================================

def enhance_analyzer():
    """Inject finance lexicon into VADER"""
    for word, score in FINANCE_LEXICON.items():
        analyzer.lexicon[word] = score


def get_label(compound: float) -> str:
    """Map compound score to sentiment label"""
    if compound >= 0.05:
        return "bullish"
    elif compound <= -0.05:
        return "bearish"
    else:
        return "neutral"


def analyze_article(article: dict) -> dict:
    """Analyze a single article — returns article + sentiment scores"""
    text = article.get("text", "")
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]

    return {
        **article,
        "vader_compound": round(compound, 4),
        "vader_label":    get_label(compound),
    }


def analyze_all(articles: list) -> list:
    """Analyze all articles — returns enriched list"""
    enhance_analyzer()
    results = []

    bullish = 0
    bearish = 0
    neutral = 0

    for article in articles:
        analyzed = analyze_article(article)
        results.append(analyzed)

        label = analyzed["vader_label"]
        if label == "bullish":   bullish += 1
        elif label == "bearish": bearish += 1
        else:                    neutral += 1

    total = len(results)
    print(f"[SENTIMENT] Bullish: {bullish} | Neutral: {neutral} | Bearish: {bearish} | Total: {total}")
    return results


def get_top_articles(articles: list, n: int = 3) -> list:
    """
    Top N articles by absolute compound score
    Used in V2 for FinBERT analysis on most impactful headlines
    """
    return sorted(
        articles,
        key=lambda x: abs(x.get("vader_compound", 0)),
        reverse=True
    )[:n]