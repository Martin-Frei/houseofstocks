# marketmood/management/commands/run_pipeline.py
"""
Startet die GMM-Pipeline einmal und beendet sich danach.
Gedacht für Railway-Cron (z. B. '0 */3 * * *').

Exit-Code 0 = Erfolg, != 0 = Fehler  → Railway zeigt fehlgeschlagene Läufe an.
"""
import time

from django.core.management.base import BaseCommand

from marketmood.pipeline.runner import run_pipeline


class Command(BaseCommand):
    help = "Führt die GMM-Pipeline einmal aus (fetch → enrich → analyze → save → aggregate)."

    def handle(self, *args, **options):
        self.stdout.write("[PIPELINE] Start")
        start = time.monotonic()

        try:
            summary = run_pipeline()
        except Exception:
            duration = time.monotonic() - start
            self.stderr.write(f"[PIPELINE] FAILED nach {duration:.0f} s")
            raise  # Original-Exception mit vollem Traceback → Exit-Code 1

        duration = time.monotonic() - start
        self.stdout.write(
            f"[PIPELINE] Fertig in {duration:.0f} s | "
            f"fetched={summary['fetched']} "
            f"enriched={summary['enriched']} "
            f"analyzed={summary['analyzed']} "
            f"saved={summary['saved']} "
            f"save_errors={summary['save_errors']} "
            f"snapshots={summary['snapshots']}"
        )