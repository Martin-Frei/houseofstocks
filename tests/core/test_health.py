# tests/core/test_health.py
"""
Tests für den Health-Check /api/health/ (F-07).

Der View fragt zwei Supabase-Tabellen per httpx ab. respx ersetzt beide
Requests; echte Aufrufe sind durch settings_test.py und --disable-socket
ohnehin unmöglich.

Falle: Der View fängt mit `except Exception` JEDE Exception – auch die eines
vergessenen Mocks. Deshalb prüft jeder Fehlerfall die komplette issues-Liste,
nicht nur status == "unhealthy".
"""
import httpx
import pytest

HEALTH_URL = "/api/health/"  # Pfad wie bei UptimeRobot, nicht über reverse()
SUPABASE_HOST = "supabase.invalid"
FRESH_ROW = [{"created_at": "2026-10-13T09:00:00Z"}]


@pytest.fixture
def supabase(respx_mock):
    """Beide Tabellen antworten gesund. Einzelne Tests überschreiben eine Route."""
    return {
        "snapshots": respx_mock.get(
            host=SUPABASE_HOST, path="/rest/v1/mood_snapshots"
        ).mock(return_value=httpx.Response(200, json=FRESH_ROW)),
        "articles": respx_mock.get(
            host=SUPABASE_HOST, path="/rest/v1/articles"
        ).mock(return_value=httpx.Response(200, json=FRESH_ROW)),
    }


def test_healthy_when_both_tables_have_fresh_rows(client, supabase):
    response = client.get(HEALTH_URL)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"] == {
        "snapshots": "ok",
        "latest_snapshot": "2026-10-13T09:00:00Z",
        "articles": "ok",
        "latest_article": "2026-10-13T09:00:00Z",
    }


def test_unhealthy_when_no_fresh_snapshot(client, supabase):
    supabase["snapshots"].mock(return_value=httpx.Response(200, json=[]))

    response = client.get(HEALTH_URL)

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["snapshots"] == "stale"
    assert data["checks"]["articles"] == "ok"
    assert data["issues"] == ["Kein mood_snapshot in den letzten 4 Stunden"]


def test_unhealthy_on_supabase_http_error(client, supabase):
    supabase["articles"].mock(return_value=httpx.Response(500))

    response = client.get(HEALTH_URL)

    assert response.status_code == 503
    data = response.json()
    assert data["checks"]["snapshots"] == "ok"
    assert data["checks"]["articles"] == "error"
    assert data["issues"] == ["Supabase articles HTTP 500"]


def test_unhealthy_on_timeout(client, supabase):
    supabase["snapshots"].mock(side_effect=httpx.ConnectTimeout("timeout"))

    response = client.get(HEALTH_URL)

    assert response.status_code == 503
    data = response.json()
    assert data["checks"]["snapshots"] == "timeout"
    assert data["checks"]["articles"] == "ok"
    assert data["issues"] == ["Supabase mood_snapshots Timeout"]
    