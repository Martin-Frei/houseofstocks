from django.apps import AppConfig
import os
import sys

class MarketmoodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketmood'

    def ready(self):
        if any(cmd in sys.argv for cmd in ['migrate', 'check', 'collectstatic', 'makemigrations']):
            return
        try:
            from .scheduler import start
            start()
            print("[APPS] Scheduler started successfully!")
        except Exception as e:
            print(f"[APPS] Scheduler failed to start: {e}")
            import traceback
            traceback.print_exc()