from django.apps import AppConfig
import os

class MarketmoodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketmood'

    def ready(self):
        # Scheduler nur starten wenn Railway Umgebung
        # UND nicht während migrate/check läuft
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            import sys
            if 'migrate' not in sys.argv and 'check' not in sys.argv:
                from .scheduler import start
                start()