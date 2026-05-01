# marketmood/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)

def run_pipeline():
    try:
        logger.info("[SCHEDULER] Pipeline starting...")
        from marketmood.pipeline.fetcher import fetch_all_sources
        from marketmood.pipeline.topic_filter import enrich_articles
        from marketmood.pipeline.sentiment import analyze_all
        from marketmood.pipeline.supabase_client import save_articles
        from marketmood.pipeline.aggregator import run_aggregator

        articles = fetch_all_sources()
        logger.info(f"[SCHEDULER] Fetched: {len(articles)} articles")
        enriched = enrich_articles(articles)
        logger.info(f"[SCHEDULER] Enriched: {len(enriched)} articles")
        analyzed = analyze_all(enriched)
        logger.info(f"[SCHEDULER] Analyzed: {len(analyzed)} articles")
        save_articles(analyzed)
        run_aggregator(analyzed)
        logger.info("[SCHEDULER] Pipeline complete.")

    except Exception as e:
        logger.error(f"[SCHEDULER] Pipeline failed: {e}", exc_info=True)


def cleanup_articles():
    """Täglicher Cleanup — löscht Articles älter als 20 Tage"""
    from django.core.management import call_command
    call_command('cleanup_articles')


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        run_pipeline,
        'interval',
        hours=3,
        id='gmm_hourly',
        replace_existing=True,
        jobstore='default'
    )

    scheduler.add_job(
        cleanup_articles,          # ← echte Funktion statt lambda
        'cron',
        hour=2,
        minute=0,
        id='cleanup_articles_daily',
        replace_existing=True,
        jobstore='default'
    )

    scheduler.start()
    logger.info("[SCHEDULER] Started — running three hour.")
    return scheduler