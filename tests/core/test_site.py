# tests/core/test_site.py
"""
Tests für den Site-Datensatz (F-33, F-07).

allauth baut Links in Bestätigungs- und Passwort-Mails aus Site id=1.
Die Daten-Migration core/0001_site_houseofstocks setzt diesen Datensatz.
Lehre aus F-33: Ein OK auf einer DB, die schon richtig war, beweist nichts –
deshalb wird zusätzlich der Live-Fall (example.com) nachgestellt.
"""
import importlib

import pytest
from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site

# Gilt für jeden Test in dieser Datei.
pytestmark = pytest.mark.django_db

# Der Modulname beginnt mit einer Ziffer → mit "import" nicht ladbar.
migration = importlib.import_module("core.migrations.0001_site_houseofstocks")


@pytest.fixture(autouse=True)
def clear_site_cache():
    """get_current() merkt sich die Site im Speicher – vor und nach jedem Test leeren."""
    Site.objects.clear_cache()
    yield
    Site.objects.clear_cache()


def test_migration_creates_houseofstocks_site():
    site = Site.objects.get(id=1)
    assert site.domain == "houseofstocks.dev"
    assert site.name == "HouseofStocks"


def test_no_default_example_site_is_added():
    # django.contrib.sites legt nach migrate per post_migrate "example.com" an –
    # aber nur, wenn noch gar keine Site existiert.
    assert Site.objects.count() == 1


def test_current_site_is_houseofstocks():
    # Genau diesen Weg benutzt allauth für Mail-Links.
    assert settings.SITE_ID == 1
    assert Site.objects.get_current().domain == "houseofstocks.dev"


def test_migration_corrects_live_case_example_com():
    # Live-Fall aus F-33 nachstellen: Datensatz steht auf example.com.
    Site.objects.filter(id=1).update(domain="example.com", name="example.com")

    migration.set_site(apps, schema_editor=None)

    site = Site.objects.get(id=1)
    assert site.domain == "houseofstocks.dev"
    assert site.name == "HouseofStocks"