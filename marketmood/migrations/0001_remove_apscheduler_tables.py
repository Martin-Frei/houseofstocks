# marketmood/migrations/0001_remove_apscheduler_tables.py
"""
Entfernt die Tabellen von django_apscheduler (Audit F-02, Phase 4).

Workflow:
    `migrate` (Railway Pre-deploy bzw. lokal) -> RunSQL löscht die beiden Tabellen
    der App und ihre Einträge in django_migrations. Seit F-02 Phase 1 laufen
    Pipeline und Cleanup als Railway-Cron-Services; der In-Process-Scheduler und
    damit django_apscheduler werden nicht mehr gebraucht.

Warum nicht `migrate django_apscheduler zero`:
    Migration 0005_migrate_name_to_id des Pakets ist irreversibel (RunPython ohne
    Rückweg). `zero` bricht dort ab und hinterlässt einen halb zurückgebauten Zustand.
    Außerdem führt Railway beim Deploy nur `migrate` vorwärts aus – diese Migration
    läuft dagegen automatisch auf jeder DB.

Funktionen:
    keine (nur RunSQL)

Abhängigkeiten:
    keine. Die App django_apscheduler darf NICHT mehr in INSTALLED_APPS stehen,
    sonst würde das nächste `migrate` ihre Tabellen neu anlegen.

Start/Test:
    python manage.py migrate marketmood --plan
    python manage.py migrate marketmood
"""
from django.db import migrations

DROP_APSCHEDULER = """
DROP TABLE IF EXISTS "django_apscheduler_djangojobexecution" CASCADE;
DROP TABLE IF EXISTS "django_apscheduler_djangojob" CASCADE;
DELETE FROM django_migrations WHERE app = 'django_apscheduler';
"""


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        # IF EXISTS: idempotent – läuft auch auf DBs, die die Tabellen nie hatten.
        # Rückweg noop: Wer den Scheduler zurück will, installiert die App neu,
        # dann legt deren eigene 0001 die Tabellen wieder an.
        migrations.RunSQL(DROP_APSCHEDULER, reverse_sql=migrations.RunSQL.noop),
    ]
    