# marketmood/apps.py
from django.apps import AppConfig

class MarketmoodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketmood'

    def ready(self):
        import os
        # Nur starten wenn echter Server läuft
        # nicht bei manage.py check, migrate etc.
        if os.environ.get('RUN_MAIN') or os.environ.get('RAILWAY_ENVIRONMENT'):
            from .scheduler import start
            start()