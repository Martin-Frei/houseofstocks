from django.shortcuts import render, redirect
from django.contrib import messages
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
