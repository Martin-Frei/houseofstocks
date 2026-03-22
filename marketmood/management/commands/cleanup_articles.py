# marketmood/management/commands/cleanup_articles.py
from django.core.management.base import BaseCommand
from django.conf import settings
import httpx
from datetime import datetime, timedelta, timezone

class Command(BaseCommand):
    help = 'Löscht Articles älter als 20 Tage'

    def handle(self, *args, **kwargs):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
        
        response = httpx.delete(
            f"{settings.SUPABASE_URL}/rest/v1/articles",
            headers={
                "apikey": settings.SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            },
            params={"created_at": f"lt.{cutoff}"}
        )
        self.stdout.write(f"Cleanup Status: {response.status_code}")