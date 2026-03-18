from django.shortcuts import render, redirect
from django.contrib import messages


def index(request):
    """
    Startseite — HouseofStocks Landing Page
    Ticker-Daten: V1 statisch, TODO V2: Live-Daten aus Supabase
    """
    # TODO V2: Ticker-Daten live aus Supabase fetchen
    ticker_data = []

    return render(request, 'core/index.html', {
        'ticker_data': ticker_data,
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
