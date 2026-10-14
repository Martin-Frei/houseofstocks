# tests/conftest.py
"""
Gemeinsame Fixtures für alle Tests.

clear_cache: autouse – LocMemCache überlebt sonst von Test zu Test (Learning 8).
ticker:      Pflicht für jeden Test, der eine Seite rendert (Teil 2, Abschnitt 10).
             Bewusst NICHT autouse: Tests für core/services/ticker.py sollen den
             echten Service sehen.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.cache import cache

# Eindeutiger Wert, der im HTML wiederzufinden ist
TICKER_ITEMS = [
    {"type": "stock", "symbol": "TESTBANK", "value": "$123.45", "direction": "UP", "url": None},
]


@pytest.fixture(autouse=True)
def clear_cache():
    """Leerer Cache vor und nach jedem Test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def ticker():
    """Ersetzt den Ticker-Service an BEIDEN Stellen, an denen er nachgeschlagen wird.

    core.context_processors.get_ticker_data: Import auf Modulebene, beim Import gebunden.
    core.services.ticker.get_ticker_data:    index() importiert IN der Funktion und
                                             schlägt bei jedem Aufruf im Service-Modul nach.
    Normalfall: beide liefern dieselben Daten (übersteht den F-19-Fix).
    """
    with (
        patch("core.context_processors.get_ticker_data", return_value=TICKER_ITEMS) as processor,
        patch("core.services.ticker.get_ticker_data", return_value=TICKER_ITEMS) as view,
    ):
        yield SimpleNamespace(processor=processor, view=view, items=TICKER_ITEMS)
        
@pytest.fixture(autouse=True)
def fail_on_blocked_socket(recwarn):
    """Netzsperre ausgelöst = vergessener Mock, auch wenn der Code den Fehler schluckt.

    pytest-socket warnt bei jedem Versuch. Code mit `except Exception` (ticker.py,
    Health-Check, Fetcher) fängt die Sperre ab, der Test bliebe sonst grün.
    """
    yield
    blocked = [w for w in recwarn if "tried to use socket" in str(w.message)]
    assert not blocked, f"Netzsperre ausgelöst – Mock vergessen?"