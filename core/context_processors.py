# core/context_processors.py
from django.core.cache import cache
from core.services.ticker import get_ticker_data

from django.core.cache import cache
from core.services.ticker import get_ticker_data

def ticker(request):
    data = cache.get('ticker_data')
    if data is None:
        data = get_ticker_data()
        cache.set('ticker_data', data, 300)
    return {'ticker_data': data}