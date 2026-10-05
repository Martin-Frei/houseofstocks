# marketmood/pipeline/runner.py
"""
Orchestrierung der GMM-Pipeline: ruft die fünf Schritte in fester Reihenfolge auf.

Bewusst OHNE try/except: Fehler gehen an den Aufrufer (Management-Command
oder Scheduler). Der Aufrufer entscheidet, was im Fehlerfall passiert.
"""
from marketmood.pipeline.fetcher import fetch_all_sources
from marketmood.pipeline.topic_filter import enrich_articles
from marketmood.pipeline.sentiment import analyze_all
from marketmood.pipeline.supabase_client import save_articles
from marketmood.pipeline.aggregator import run_aggregator


def run_pipeline() -> dict:
    """
    Führt die komplette Pipeline aus und gibt eine Zusammenfassung zurück.

    Raises:
        RuntimeError: wenn keine Artikel geholt wurden (alle Feeds down /
                      Netzwerkproblem) — sonst würden leere Snapshots entstehen.
    """
    articles = fetch_all_sources()
    if not articles:
        raise RuntimeError("Fetcher returned 0 articles — aborting before enrich/save.")

    enriched = enrich_articles(articles)
    analyzed = analyze_all(enriched)
    save_result = save_articles(analyzed)      # {"saved": int, "errors": int}
    snapshots = run_aggregator(analyzed)       # list[dict]

    return {
        "fetched": len(articles),
        "enriched": len(enriched),
        "analyzed": len(analyzed),
        "saved": save_result.get("saved", 0),
        "save_errors": save_result.get("errors", 0),
        "snapshots": len(snapshots),
    }