# tests/marketmood/test_commands.py
"""
Tests für die Management-Commands der Pipeline (F-02, F-24).

run_pipeline:     Vertrag mit Railway-Cron. Erfolg → Zusammenfassung in stdout,
                  Fehler → dieselbe Exception (Exit-Code ≠ 0) + FAILED in stderr.
cleanup_articles: DELETE auf articles nur für Zeilen älter als 20 Tage,
                  Service-Key, 60 s Timeout, 4xx/5xx und Netzfehler → Exception.
"""
from datetime import datetime, timedelta, timezone
from io import StringIO
from unittest.mock import patch

import httpx
import pytest
from django.core.management import call_command

# Ort des Nachschlagens: Modul run_pipeline, darin der Name run_pipeline
RUN_PIPELINE = "marketmood.management.commands.run_pipeline.run_pipeline"

# Absichtlich verschiedene Zahlen: jede verrät ihre Herkunft (Learning 16)
SUMMARY = {
    "fetched": 50,
    "enriched": 48,
    "analyzed": 47,
    "saved": 44,
    "save_errors": 3,
    "snapshots": 91,
}

# Werte aus settings_test.py
SUPABASE_HOST = "supabase.invalid"
ARTICLES_PATH = "/rest/v1/articles"
SERVICE_KEY = "test-service-key"
RETENTION = timedelta(days=20)


@pytest.fixture
def pipeline():
    """Ersetzt den Runner im Namensraum des Commands, nach dem Test zurück."""
    with patch(RUN_PIPELINE) as mock:
        yield mock


@pytest.fixture
def streams():
    """stdout/stderr des Commands auffangen (auch wenn er eine Exception wirft)."""
    return StringIO(), StringIO()


@pytest.fixture
def articles_delete(respx_mock):
    """Normalfall: Supabase bestätigt das DELETE mit 204 No Content.

    Route über host + path, weil der Query-Parameter bei jedem Lauf anders ist.
    """
    return respx_mock.delete(host=SUPABASE_HOST, path=ARTICLES_PATH).mock(
        return_value=httpx.Response(204)
    )


def sent_filter(route):
    """Liest den gesendeten Filter aus: ("lt", "2026-…+00:00")."""
    value = route.calls.last.request.url.params["created_at"]
    operator, _, cutoff = value.partition(".")  # nur am ersten Punkt trennen
    return operator, cutoff


# ═══ run_pipeline ═════════════════════════════════════════════════════════════

# --- Erfolg ---------------------------------------------------------------

def test_success_prints_all_six_numbers_from_runner(pipeline, streams):
    pipeline.return_value = SUMMARY
    out, err = streams

    call_command("run_pipeline", stdout=out, stderr=err)

    pipeline.assert_called_once_with()
    assert (
        "fetched=50 enriched=48 analyzed=47 saved=44 save_errors=3 snapshots=91"
        in out.getvalue()
    )
    assert err.getvalue() == ""


def test_success_reports_start_then_finish(pipeline, streams):
    pipeline.return_value = SUMMARY
    out, err = streams

    call_command("run_pipeline", stdout=out, stderr=err)

    lines = out.getvalue().splitlines()
    assert lines[0] == "[PIPELINE] Start"
    assert lines[1].startswith("[PIPELINE] Fertig in ")
    assert len(lines) == 2


# --- Fehler ---------------------------------------------------------------

@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("Fetcher returned 0 articles — aborting before enrich/save."),
        httpx.ConnectTimeout("supabase timeout"),
        KeyError("score"),
    ],
    ids=["no-articles", "timeout", "bug"],
)
def test_error_propagates_unchanged(pipeline, streams, error):
    pipeline.side_effect = error
    out, err = streams

    with pytest.raises(type(error)) as excinfo:
        call_command("run_pipeline", stdout=out, stderr=err)

    assert excinfo.value is error  # dasselbe Objekt, nicht nur derselbe Typ
    pipeline.assert_called_once_with()


def test_error_writes_failed_to_stderr_and_no_finish(pipeline, streams):
    pipeline.side_effect = RuntimeError("boom")
    out, err = streams

    with pytest.raises(RuntimeError):
        call_command("run_pipeline", stdout=out, stderr=err)

    assert err.getvalue().startswith("[PIPELINE] FAILED nach ")
    assert out.getvalue().splitlines() == ["[PIPELINE] Start"]


# ═══ cleanup_articles ═════════════════════════════════════════════════════════

# --- Request --------------------------------------------------------------

def test_sends_one_delete_with_service_key(articles_delete, streams):
    out, err = streams

    call_command("cleanup_articles", stdout=out, stderr=err)

    assert articles_delete.call_count == 1
    request = articles_delete.calls.last.request
    assert request.method == "DELETE"
    assert request.headers["apikey"] == SERVICE_KEY
    assert request.headers["Authorization"] == f"Bearer {SERVICE_KEY}"


def test_filter_deletes_only_rows_older_than_20_days(articles_delete, streams):
    out, err = streams

    before = datetime.now(timezone.utc) - RETENTION
    call_command("cleanup_articles", stdout=out, stderr=err)
    after = datetime.now(timezone.utc) - RETENTION

    operator, cutoff = sent_filter(articles_delete)
    assert operator == "lt"  # gt würde die NEUESTEN Artikel löschen
    # Fenster statt fester Zeit: wiederholbar ohne Zeit einzufrieren.
    # Naiver Cutoff (ohne Zeitzone) → TypeError beim Vergleich → rot.
    assert before <= datetime.fromisoformat(cutoff) <= after


def test_plus_in_cutoff_is_url_encoded(articles_delete, streams):
    out, err = streams

    call_command("cleanup_articles", stdout=out, stderr=err)

    raw_query = articles_delete.calls.last.request.url.query  # bytes, unkodiert
    assert b"%2B" in raw_query  # "+00:00" als %2B, sonst liest der Server ein Leerzeichen
    assert b"+" not in raw_query


def test_request_uses_60s_timeout(articles_delete, streams):
    out, err = streams

    call_command("cleanup_articles", stdout=out, stderr=err)

    timeout = articles_delete.calls.last.request.extensions["timeout"]
    assert timeout == {"connect": 60, "read": 60, "write": 60, "pool": 60}


def test_success_prints_status_and_sent_cutoff(articles_delete, streams):
    out, err = streams

    call_command("cleanup_articles", stdout=out, stderr=err)

    _, cutoff = sent_filter(articles_delete)
    assert out.getvalue() == f"Cleanup Status: 204 (cutoff {cutoff})\n"
    assert err.getvalue() == ""


# --- Fehler ---------------------------------------------------------------

@pytest.mark.parametrize(
    "status",
    [400, 401, 500, 503],
    ids=["bad-filter", "wrong-key", "server-error", "unavailable"],
)
def test_http_error_raises(articles_delete, streams, status):
    articles_delete.return_value = httpx.Response(status)
    out, err = streams

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        call_command("cleanup_articles", stdout=out, stderr=err)

    assert excinfo.value.response.status_code == status
    assert out.getvalue() == ""  # keine Erfolgsmeldung


def test_network_error_propagates_unchanged(articles_delete, streams):
    error = httpx.ConnectTimeout("supabase timeout")
    articles_delete.side_effect = error
    out, err = streams

    with pytest.raises(httpx.ConnectTimeout) as excinfo:
        call_command("cleanup_articles", stdout=out, stderr=err)

    assert excinfo.value is error
    assert articles_delete.called