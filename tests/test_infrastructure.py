# tests/test_infrastructure.py
"""
Test 0 – Leitplanken (F-07).

Prüft, dass die Testumgebung abgeschottet ist, BEVOR andere Tests laufen:
SQLite statt Supabase-DB, nur Dummy-Werte statt echter Schlüssel,
Netzwerk gesperrt. Wird hier etwas rot, sind alle anderen Tests unsicher.
"""
import os
import socket

import httpx
import pytest
from django.conf import settings
from django.db import connection
from pytest_socket import SocketBlockedError


def test_settings_module_is_test_settings():
    assert settings.SETTINGS_MODULE == "houseofstocks.settings_test"


def test_database_is_sqlite():
    # Nur Engine und Host prüfen, nicht NAME: pytest-django ersetzt ":memory:"
    # beim Anlegen der Test-DB durch einen eigenen Namen → reihenfolgeabhängig.
    # HOST existiert immer: Django ergänzt fehlende Schlüssel mit Standardwerten.
    assert connection.vendor == "sqlite"
    assert settings.DATABASES["default"]["HOST"] == ""


@pytest.mark.parametrize(
    "name", ["SUPABASE_URL", "SPV2_SUPABASE_URL", "DEEPSEEK_API_URL"]
)
def test_external_urls_point_to_invalid(name):
    host = httpx.URL(getattr(settings, name)).host
    assert host.endswith(".invalid"), f"{name} zeigt auf {host}"


@pytest.mark.parametrize(
    "name",
    [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY",
        "SPV2_SUPABASE_URL",
        "SPV2_SUPABASE_ANON_KEY",
        "DEEPSEEK_API_KEY",
        "BREVO_API_KEY",
    ],
)
def test_environment_holds_no_real_secrets(name):
    # os.environ statt settings: Pipeline-Module könnten os.getenv() direkt lesen.
    value = os.environ[name]
    assert value.startswith("test-") or ".invalid" in value, f"{name} sieht echt aus"


def test_secret_key_is_test_key():
    assert settings.SECRET_KEY == "test-only-not-a-secret"


def test_settings_were_loaded_like_production():
    # settings.DEBUG zu prüfen wäre wertlos: Djangos Test-Setup setzt es immer
    # auf False. Dieser Wert wird aber beim Import aus DEBUG berechnet und
    # beweist, dass settings.py wie in Produktion (und in der CI) geladen wurde.
    assert settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL == "https"


def test_email_backend_is_locmem():
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"


# Die beiden Tests lösen die Netzsperre absichtlich aus. In jedem anderen Test
# macht fail_on_blocked_socket (tests/conftest.py) daraus einen Error.
def test_raw_socket_is_blocked():
    # pytest.warns außen: fängt die Warnung ab (fail_on_blocked_socket sieht sie nicht)
    # und prüft, dass pytest-socket überhaupt warnt – davon hängt der Wächter ab.
    with (
        pytest.warns(UserWarning, match="tried to use socket"),
        pytest.raises(SocketBlockedError),
    ):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def test_httpx_request_is_blocked():
    # IP statt Hostname: kein DNS-Lookup, der Versuch trifft direkt den Socket.
    with (
        pytest.warns(UserWarning, match="tried to use socket"),
        pytest.raises(SocketBlockedError),
    ):
        httpx.get("http://127.0.0.1:9/", timeout=1)