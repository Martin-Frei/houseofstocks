# tests/core/test_index.py
"""
Tests für die Startseite (core.views.index) und den Ticker-Context-Processor.

Startseite:        rendert, Ticker-Daten kommen im HTML an, leerer Ticker ≠ Absturz.
Context-Processor: Cache-Miss → einmal holen und 300 s speichern, Cache-Treffer → kein Aufruf,
                   auch ein leeres Ergebnis wird gecacht.
Ist-Zustand F-19:  index() holt den Ticker selbst (ungecacht) und überschreibt den Processor.
"""
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse

from core.context_processors import ticker as ticker_processor

INDEX_URL = reverse("core:index")


# --- Startseite -----------------------------------------------------------

def test_index_renders_with_its_template(client, ticker):
    response = client.get(INDEX_URL)

    assert response.status_code == 200
    assert "core/index.html" in [t.name for t in response.templates]


def test_ticker_item_appears_in_page(client, ticker):
    response = client.get(INDEX_URL)

    # base.html rendert den Ticker zweimal: Original + Duplikat für nahtloses Scrollen
    assert response.content.count(b"TESTBANK") == 2


def test_index_renders_with_empty_ticker(client, ticker):
    """Supabase down → ticker.py liefert [] → Platzhalter aus {% empty %} in base.html."""
    ticker.view.return_value = []
    ticker.processor.return_value = []

    response = client.get(INDEX_URL)

    assert response.status_code == 200
    assert b"TESTBANK" not in response.content
    assert b"WIRD GELADEN" in response.content  # Fallback aus base.html


def test_view_overrides_processor_and_skips_cache_current_state_f19(client, ticker):
    """Dokumentiert den Ist-Zustand aus F-19. Wird mit dem F-19-Fix bewusst angepasst."""
    view_items = [{**ticker.items[0], "symbol": "FROMVIEW"}]
    processor_items = [{**ticker.items[0], "symbol": "FROMCACHE"}]
    ticker.view.return_value = view_items
    ticker.processor.return_value = processor_items

    client.get(INDEX_URL)
    response = client.get(INDEX_URL)

    assert response.context["ticker_data"] == view_items  # View gewinnt
    assert ticker.view.call_count == 2                     # ungecacht: jeder Aufruf
    assert ticker.processor.call_count == 1                # gecacht: nur der erste


# --- Context-Processor ----------------------------------------------------

def test_processor_fetches_and_caches_on_miss(rf, ticker):
    result = ticker_processor(rf.get("/"))

    assert result == {"ticker_data": ticker.items}
    ticker.processor.assert_called_once_with()
    assert cache.get("ticker_data") == ticker.items


def test_processor_uses_cache_on_hit(rf, ticker):
    cached = [{"type": "stock", "symbol": "CACHED"}]
    cache.set("ticker_data", cached, 300)

    result = ticker_processor(rf.get("/"))

    assert result == {"ticker_data": cached}
    ticker.processor.assert_not_called()


def test_processor_caches_for_300_seconds(rf, ticker):
    with patch("core.context_processors.cache.set", wraps=cache.set) as spy:
        ticker_processor(rf.get("/"))

    spy.assert_called_once_with("ticker_data", ticker.items, 300)


def test_processor_caches_empty_result(rf, ticker):
    """`is None` statt `not data`: auch [] wird 300 s gecacht."""
    ticker.processor.return_value = []

    ticker_processor(rf.get("/"))
    ticker_processor(rf.get("/"))

    ticker.processor.assert_called_once_with()