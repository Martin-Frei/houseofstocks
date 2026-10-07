# core/migrations/0001_site_houseofstocks.py
"""
Daten-Migration: Site id=1 auf houseofstocks.dev setzen (Audit F-33).

Workflow:
    `migrate` (Railway Pre-deploy bzw. lokal) -> set_site() schreibt den Datensatz
    django_site id=1. update_or_create macht die Migration idempotent: Sie funktioniert
    auf einer frischen DB (example.com), auf der lokalen DB (bereits korrigiert) und
    auf der Live-DB (vorher evtl. schon über /admin/ korrigiert).

Funktionen:
    set_site(apps, schema_editor) -- setzt domain/name von Site id=1

Abhängigkeiten:
    django.contrib.sites (Migration 0002_alter_domain_unique), settings.SITE_ID = 1

Start/Test:
    python manage.py migrate core
    python manage.py shell -c "from django.contrib.sites.models import Site; print(Site.objects.get(id=1))"
"""
from django.db import migrations

SITE_DOMAIN = "houseofstocks.dev"
SITE_NAME = "HouseofStocks"


def set_site(apps, schema_editor):
    # Historisches Model über apps.get_model, nicht direkt importieren:
    # Die Migration muss auch noch funktionieren, wenn sich das Model später ändert.
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=1,
        defaults={"domain": SITE_DOMAIN, "name": SITE_NAME},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("sites", "0002_alter_domain_unique"),
        # Falls core schon Migrationen hat: letzte core-Migration hier ergänzen
        # und die Datei entsprechend nummerieren.
    ]

    operations = [
        # Rückwärts bewusst noop: "example.com" wiederherzustellen hätte keinen Nutzen.
        migrations.RunPython(set_site, migrations.RunPython.noop),
    ]
