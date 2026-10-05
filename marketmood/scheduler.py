# marketmood/scheduler.py
# PHASE 1 (F-02): Übergangsversion. Wird in Phase 3 gelöscht, sobald Railway-Cron läuft.
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore

logger = logging.getLogger(__name__)


def run_pipeline():
    """
    Wrapper für den Scheduler-Thread. try/except bleibt HIER bewusst:
    Eine Exception darf den BackgroundScheduler-Thread nicht beenden.
    Die eigentliche Logik liegt in marketmood/pipeline/runner.py.
    """
    try:
        from marketmood.pipeline.runner import run_pipeline as _run
        summary = _run()
        logger.warning(f"[SCHEDULER] Pipeline complete: {summary}")
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
        cleanup_articles,
        'cron',
        hour=2,
        minute=0,
        id='cleanup_articles_daily',
        replace_existing=True,
        jobstore='default'
    )

    scheduler.start()
    logger.info("[SCHEDULER] Started — running every three hours.")
    return scheduler