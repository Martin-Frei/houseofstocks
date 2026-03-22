# stockpredict/views.py
import httpx
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from datetime import datetime, date

def get_predictions(tier: str) -> list:
    """
    Liest Predictions aus Supabase (Portfolio Projekt).
    Free:         einen Tag vor neuesten Daten (verzögert)
    Pro/Premium:  neueste verfügbare Daten
    TODO V3: AWS als primäres Backend, Supabase als Fallback
    """
    try:
        # Schritt 1: neuestes verfügbares Datum holen
        r1 = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/predictions",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params={"select": "date_for", "order": "date_for.desc", "limit": "1"},
            timeout=10.0
        )
        rows = r1.json()
        if not rows:
            return []

        latest_date = rows[0]['date_for']

        # Schritt 2: Daten je nach Tier holen
        if tier == 'free':
            # Free: einen Tag vor dem neuesten Datum
            params = {
                "select": "*",
                "order": "date_for.desc",
                "limit": "12",
                "date_for": f"lt.{latest_date}"
            }
        else:
            # Pro/Premium: neuestes Datum
            params = {
                "select": "*",
                "order": "date_for.desc",
                "limit": "12",
                "date_for": f"eq.{latest_date}"
            }

        r2 = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/predictions",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params=params,
            timeout=10.0
        )
        return r2.json() if r2.status_code == 200 else []

    except Exception as e:
        print(f"[STOCKPREDICT] Supabase error: {e}")
        return []

def get_sweet_spot(request):
    from django.http import JsonResponse
    if not request.user.is_authenticated or not request.user.profile.is_premium():
        return JsonResponse({'success': False, 'error': 'Premium required'}, status=403)

    try:
        today = date.today().isoformat()
        response = httpx.get(
            f"{settings.SPV2_SUPABASE_URL}/rest/v1/predictions",
            headers={
                "apikey": settings.SPV2_SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {settings.SPV2_SUPABASE_ANON_KEY}",
            },
            params={
                "select": "symbol,lstm_dir,xgb_dir,xgb_conf,xlf_zscore",
                "date_for": f"eq.{today}",
            },
            timeout=10.0
        )
        rows = response.json() if response.status_code == 200 else []

        # Holy Grail = MATCH + xlf_zscore >= 1.0
        holy_grail = [
            {'symbol': r['symbol']}
            for r in rows
            if r.get('lstm_dir') == r.get('xgb_dir')        # MATCH
            and (r.get('xlf_zscore') or 0) >= 1.0           # ZS >= 1.0
        ]

        return JsonResponse({'success': True, 'stocks': holy_grail})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
def normalize_stock(row: dict) -> dict:
    return {
        'Symbol':           row.get('symbol'),
        'LSTM_Prediction':  row.get('lstm_dir', '—').upper(),
        'XGB_Prediction':   row.get('xgb_dir', '—').upper(),
        'confidence':       round((row.get('xgb_conf', 0) or 0) * 100, 1),
        'prediction_date':  row.get('date_for'),
        'prev_close':       row.get('last_close'),
        'prev_date':        row.get('timestamp'),
        'prev_volume':      '—',
        'z_score':          row.get('xlf_zscore'),
    }

def dashboard(request):
    """
    StockPredict Dashboard
    Tier-basierter Zugriff auf Predictions
    """
    # Tier bestimmen    
    if request.user.is_authenticated:
        tier = request.user.profile.tier
    else:
        tier = 'free'

    raw = get_predictions(tier)
    stocks = [normalize_stock(r) for r in raw]
    last_update = stocks[0].get('prediction_date', '—') if stocks else '—'

    return render(request, 'stockpredict/dashboard.html', {
        'stocks':     stocks,
        'last_update': last_update,
        'is_premium': tier == 'premium',
        'tier':       tier,
    })
    
