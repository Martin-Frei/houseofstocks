# tests/test_settings.py
"""
Tests für houseofstocks/settings.py (F-07 Schritt 4, Bezug F-09).

settings.py entscheidet beim Import (SECRET_KEY-Prüfung, if not DEBUG-Block).
Im normalen Testlauf ist diese Entscheidung längst gefallen. Deshalb wird
settings.py hier mit runpy in einem frischen Namensraum erneut ausgeführt –
ohne das echte Modul in sys.modules zu verändern.
"""
import importlib.util
import runpy

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware

SETTINGS_PATH = importlib.util.find_spec("houseofstocks.settings").origin

# Werte, die SecurityMiddleware und request.is_secure() lesen
SECURITY_SETTINGS = (
    "SECURE_SSL_REDIRECT",
    "SECURE_REDIRECT_EXEMPT",
    "SECURE_PROXY_SSL_HEADER",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def load_settings(monkeypatch):
    """Führt settings.py frisch aus, mit der Umgebung, die der Test vorgibt.

    load_dotenv wird stillgelegt: Sonst füllt die lokale .env gelöschte
    Variablen wieder auf (PowerShell-Falle aus F-09), und der Test verhielte
    sich lokal anders als in der CI.
    """
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)

    def _load(**env):
        for key, value in env.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)
        return runpy.run_path(SETTINGS_PATH)

    return _load


@pytest.fixture
def prod(load_settings):
    """Namensraum von settings.py, geladen wie auf Railway."""
    return load_settings(DEBUG="False", SECRET_KEY="test-only-not-a-secret")


@pytest.fixture
def security_middleware(settings, prod):
    """SecurityMiddleware mit den Produktionswerten statt der Test-Rücknahme.

    Muss NACH dem Setzen gebaut werden: Die Middleware liest die Settings
    in __init__.
    """
    for name in SECURITY_SETTINGS:
        setattr(settings, name, prod[name])
    return SecurityMiddleware(lambda request: HttpResponse("ok"))


# ── SECRET_KEY (F-09) ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "secret_key",
    ["", "   ", None],
    ids=["leer", "nur-leerzeichen", "fehlt"],
)
def test_production_without_secret_key_refuses_to_start(load_settings, secret_key):
    with pytest.raises(ImproperlyConfigured, match="SECRET_KEY fehlt"):
        load_settings(DEBUG="False", SECRET_KEY=secret_key)


def test_debug_without_secret_key_uses_dev_fallback(load_settings):
    ns = load_settings(DEBUG="True", SECRET_KEY="")

    assert ns["SECRET_KEY"] == "django-insecure-local-dev-only"
    assert ns["ACCOUNT_DEFAULT_HTTP_PROTOCOL"] == "http"
    assert "SECURE_SSL_REDIRECT" not in ns  # if not DEBUG-Block lief nicht


# ── Produktionswerte (F-09) ───────────────────────────────────────────────────

def test_production_enables_https_settings(prod):
    assert prod["SECURE_SSL_REDIRECT"] is True
    assert prod["SESSION_COOKIE_SECURE"] is True
    assert prod["CSRF_COOKIE_SECURE"] is True
    assert prod["ACCOUNT_DEFAULT_HTTP_PROTOCOL"] == "https"


# ── Verhalten der Middleware mit diesen Werten ────────────────────────────────

def test_plain_http_request_is_redirected_to_https(security_middleware, rf):
    response = security_middleware(rf.get("/stocks/"))

    assert response.status_code == 301
    assert response["Location"] == "https://testserver/stocks/"


def test_request_via_railway_proxy_is_not_redirected(security_middleware, rf):
    # Railway: Browser --HTTPS--> Proxy --HTTP + X-Forwarded-Proto--> Gunicorn
    request = rf.get("/", headers={"X-Forwarded-Proto": "https"})

    response = security_middleware(request)

    assert response.status_code == 200  # keine Redirect-Schleife
    assert response["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def test_health_check_is_exempt_from_redirect(security_middleware, rf):
    response = security_middleware(rf.get("/api/health/"))

    assert response.status_code == 200