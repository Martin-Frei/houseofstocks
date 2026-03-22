from django.apps import AppConfig
import os
import sys

class MarketmoodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketmood'

    def ready(self):
        # Nicht starten bei Management Commands
        if 'migrate' in sys.argv or 'check' in sys.argv or 'collectstatic' in sys.argv:
            return
        # Lokal: nur im Hauptprozess (nicht StatReloader)
        # Railway: immer starten
        if os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RUN_MAIN'):
            from .scheduler import start
            start()