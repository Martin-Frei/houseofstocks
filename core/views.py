from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
import httpx
from datetime import datetime, timedelta, timezone
from core.services.ticker import get_ticker_data


def index(request):
    from core.services.ticker import get_ticker_data
    data = get_ticker_data()
    print(f"[TICKER DEBUG] Items: {len(data)}")
    if data:
        print(f"[TICKER DEBUG] First: {data[0]}")
    return render(request, 'core/index.html', {
        'ticker_data': data,
    })

def preise(request):
    """
    Preisseite — Free / Pro / Premium
    TODO V2: Stripe Checkout Links einbinden
    """
    return render(request, 'core/preise.html')


def waitlist(request):
    """
    Warteliste — Email eintragen
    TODO V2: Email in Supabase speichern + Resend Bestätigungsmail
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            # TODO V2: Email in Supabase waitlist Tabelle speichern
            # TODO V2: Resend API Bestätigungsmail senden
            messages.success(request, f'Du bist auf der Warteliste! Wir melden uns bei {email}.')
        else:
            messages.error(request, 'Bitte gib eine gültige E-Mail-Adresse ein.')
    return redirect('core:index')


# ============================================================
# HEALTH CHECK — /api/health/
# ============================================================
# Prüft ob die GMM Pipeline aktiv Daten liefert.
# UptimeRobot monitort diesen Endpoint mit Keyword "healthy".
#
# Warum nicht einfach Uptime-Ping:
#   Die Seite kann 200 OK liefern aber ein leeres Dashboard
#   zeigen wenn Supabase nicht antwortet oder die Pipeline
#   hängt. Dieser Endpoint prüft den tatsächlichen Datenfluss.
#
# Warum 4 Stunden Schwelle:
#   Pipeline läuft alle 3h. Mit 1h Puffer erkennen wir eine
#   ausgefallene Runde ohne false positives bei normalem Timing.
# ============================================================

def health_check(request):
    issues = []
    checks = {}
    threshold = datetime.now(timezone.utc) - timedelta(hours=4)
    threshold_iso = threshold.strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}",
    }

    # ── Check 1: mood_snapshots (Pipeline-Output) ──
    try:
        r = httpx.get(
            f"{settings.SUPABASE_URL}/rest/v1/mood_snapshots",
            headers=headers,
            params={
                "select": "created_at",
                "created_at": f"gte.{threshold_iso}",
                "order": "created_at.desc",
                "limit": "1",
            },
            timeout=8.0,
        )
        if r.status_code == 200:
            rows = r.json()
            if rows:
                checks["snapshots"] = "ok"
                checks["latest_snapshot"] = rows[0]["created_at"]
            else:
                checks["snapshots"] = "stale"
                issues.append("Kein mood_snapshot in den letzten 4 Stunden")
        else:
            checks["snapshots"] = "error"
            issues.append(f"Supabase mood_snapshots HTTP {r.status_code}")

    except httpx.TimeoutException:
        checks["snapshots"] = "timeout"
        issues.append("Supabase mood_snapshots Timeout")
    except Exception as e:
        checks["snapshots"] = "error"
        issues.append(f"Supabase mood_snapshots: {str(e)[:100]}")

    # ── Check 2: articles (Feed-Input) ──
    try:
        r = httpx.get(
            f"{settings.SUPABASE_URL}/rest/v1/articles",
            headers=headers,
            params={
                "select": "created_at",
                "created_at": f"gte.{threshold_iso}",
                "order": "created_at.desc",
                "limit": "1",
            },
            timeout=8.0,
        )
        if r.status_code == 200:
            rows = r.json()
            if rows:
                checks["articles"] = "ok"
                checks["latest_article"] = rows[0]["created_at"]
            else:
                checks["articles"] = "stale"
                issues.append("Keine articles in den letzten 4 Stunden")
        else:
            checks["articles"] = "error"
            issues.append(f"Supabase articles HTTP {r.status_code}")

    except httpx.TimeoutException:
        checks["articles"] = "timeout"
        issues.append("Supabase articles Timeout")
    except Exception as e:
        checks["articles"] = "error"
        issues.append(f"Supabase articles: {str(e)[:100]}")

    # ── Response ──
    if issues:
        return JsonResponse(
            {"status": "unhealthy", "issues": issues, "checks": checks},
            status=503,
        )

    return JsonResponse(
        {"status": "healthy", "checks": checks},
        status=200,
    )