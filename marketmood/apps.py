from django.apps import AppConfig
import os
import sys

class MarketmoodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketmood'

    def ready(self):
        # Nicht starten bei Management Commands
        if any(cmd in sys.argv for cmd in ['migrate', 'check', 'collectstatic', 'makemigrations']):
            return
        # Immer starten – lokal und auf Railway
        from .scheduler import start
        start()