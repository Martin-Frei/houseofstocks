# HouseofStocks.dev — Projektdokumentation

**Erstellt:** 18. März 2026  
**Status:** Beta — Live seit März 2026  
**Domain:** houseofstocks.dev  
**Repository:** https://github.com/Martin-Frei/houseofstocks (privat)  
**Hosting:** Railway (Web) + Supabase (PostgreSQL)

---

## 1. Projektübersicht

HouseofStocks.dev ist eine FinTech-Plattform die zwei bestehende ML-Projekte unter einer gemeinsamen Oberfläche zusammenführt:

- **StockPredict V2** — LSTM + XGBoost Ensemble für 12 Bankaktien
- **Global Market Mood (GMM)** — Stündliche Sentiment-Analyse von tgl. 100.000+ Nachrichtenartikeln

Die Plattform ist als **Umbrella-Site** konzipiert: bestehende Backends bleiben unverändert, HouseofStocks.dev liest Daten und stellt sie dar.

---

## 2. Architektur-Entscheidungen

### 2.1 Ein Django-Projekt, vier Apps

**Entscheidung:** Ein Django-Monolith mit vier Apps statt getrennter Services.

**Begründung:**
- Shared Auth — ein Login gilt für alles
- Shared UserProfile + Tier-System — eine Tabelle steuert Zugriffsrechte
- Ein Deployment auf Railway
- Vertrauter Workflow aus Portfolio-Entwicklung

```
houseofstocks/           ← Django Projekt Root
├── core/                ← Startseite, Landing, Impressum
├── accounts/            ← Signup, Login, UserProfile, Tier
├── stockpredict/        ← Read-only Supabase Results anzeigen
└── marketmood/          ← GMM komplett (Scraping, Sentiment, Anzeige)
```

### 2.2 Supabase als einzige Datenbank

**Entscheidung:** Alles in Supabase PostgreSQL (Projekt: global_market_mood).

**Begründung:**
- GMM Daten (articles, mood_snapshots) bereits dort
- SPV2 Daten auf separatem Supabase Projekt — nur lesend per REST API
- Kein extra Railway Postgres Service nötig
- Django verbindet sich direkt per psycopg2 (DB_HOST: db.djkvuqbirkxskovhhtns.supabase.co)

**Datenstruktur:**
```
Supabase Projekt 1 (portfolio_site):
└── SPV2 Tabellen (predictions, trades) → nur lesend von HoS.dev

Supabase Projekt 2 (global_market_mood):
├── articles (GMM Headlines)
├── mood_snapshots (GMM Stimmungsbilder)
└── Django Tabellen (accounts, sessions, apscheduler) ← neu angelegt
```

### 2.3 Redundanz-Strategie (geplant)

**Entscheidung:** Jetzt Supabase, später AWS als primäres Backend mit Supabase als Fallback.

**Umsetzung:** Service Layer von Anfang an abstrakt gebaut:

```python
# TODO V3: AWS als primäres Backend, Supabase als Fallback
class BaseStorageService:
    def save_headlines(self, data): raise NotImplementedError
    def get_predictions(self): raise NotImplementedError

class SupabaseStorageService(BaseStorageService):
    # V1: vollständig implementiert
    
class AWSStorageService(BaseStorageService):
    # TODO V3: nach AWS Kurs implementieren
```

Flag-gesteuertes Routing via `STORAGE_BACKEND` Environment Variable.

### 2.4 StockPredict V2 — Read-Only

**Entscheidung:** Kein zweites Deployment von SPV2. Nur ein Read-Layer in `stockpredict/services.py`.

```python
# stockpredict/services.py
def get_latest_predictions():
    # Liest direkt aus Supabase REST API
    # Schreiben macht weiterhin das Portfolio-Projekt
```

SPV2 Pipeline läuft unverändert auf Railway (eigenem Service).

---

## 3. Tech-Stack

| Komponente | Technologie | Begründung |
|---|---|---|
| Backend | Django 5.2 | Vertraut, schnell, Auth inklusive |
| Auth | django-allauth | Social Login vorbereitet, Email-Login |
| Scheduler | django-apscheduler | In-Process, kein extra Railway Service |
| Datenbank | Supabase PostgreSQL | Bereits vorhanden, GMM Daten dort |
| REST Zugriff | httpx (async) | Für Supabase API Calls |
| Sentiment | VADER + (FinBERT V2) | VADER leicht, FinBERT für V2 |
| Klassifikation | DeepSeek API | Kontextbasiert, ~$29/Monat |
| Static Files | Whitenoise | Kein CDN nötig für V1 |
| Hosting | Railway | Vertraut, einfaches Deployment |
| CSS | Reines CSS (keine Frameworks) | Kein Build-Prozess, einfaches Deployment |
| Fonts | Instrument Serif + DM Mono + Geist | FinTech Premium Ästhetik |

**Bewusst NICHT verwendet:**
- Tailwind CSS → braucht Build-Prozess, unnötige Komplexität für Railway
- React/Vue → Django Templates reichen für V1
- Railway Postgres → Supabase reicht, ein Service weniger

---

## 4. Mitgliedschaftsstufen (Tier-System)

### 4.1 StockPredict V2

| Stufe | Inhalt | Begründung |
|---|---|---|
| **Free** | Gestrige Vorhersagen + Trefferquote | Nützlich genug um zu bleiben |
| **Pro** | Heutige Vorhersagen (normale Signale) | Löst "was passiert heute" |
| **Premium** | Holy Grail Signale (stärkste Signale) | Für ernsthafte Nutzer |

**Wichtig:** Holy Grail = intern ZS ≥ 1.0 — dieser technische Wert wird **nicht** nach außen kommuniziert. Nur "Holy Grail" als Markenbegriff.

Geplante weitere Signal-Typen: Powertrader, Sniper (V2/V3).

### 4.2 Global Market Mood

| Stufe | Inhalt | Begründung |
|---|---|---|
| **Free** | News älter als 12 Stunden | Kontext ohne Echtzeit |
| **Pro** | Aktuelle News in Echtzeit | Live Stimmungsbild |
| **Premium** | Keyword-Suche in der Datenbank | Für eigene Recherche |

### 4.3 Preise (Beta, Stand März 2026)

| Stufe | Monatlich | Jährlich | Ersparnis |
|---|---|---|---|
| Free | €0 | €0 | — |
| Pro | €19 | €199 | 2 Monate gratis |
| Premium | €99 | €990 | 2 Monate gratis |

### 4.4 Django Model

```python
class UserProfile(models.Model):
    TIER_FREE = 'free'
    TIER_PRO = 'pro'  
    TIER_PREMIUM = 'premium'
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    tier = models.CharField(choices=TIER_CHOICES, default='free')
    stripe_customer_id = models.CharField(blank=True)  # TODO V2: Stripe
    
    def is_pro(self):
        return self.tier in ['pro', 'premium']
```

---

## 5. GMM Klassifikations-Entscheidung

### 5.1 Problem mit keyword-basierter Klassifikation

spaCy Keyword-Matching produziert fehlerhafte Ergebnisse:
- "Solaranlagen gestohlen" → landet in **Energy** statt **General/Crime**
- Kontext wird nicht verstanden, nur Keywords gematcht

### 5.2 Entscheidung: DeepSeek für alle Headlines

**Warum nicht nur für "general":**
- Alle 4.000 Headlines/Stunde brauchen korrekte Klassifikation
- DeepSeek versteht Kontext, nicht nur Keywords
- Kosten überschaubar

**Batch-Strategie:**
```python
# 50 Headlines pro API-Call
# 4.000 / 50 = 80 Requests/Stunde
# Async (10 parallel) = ~16 Sekunden/Stunde
```

**Kostenrechnung:**
```
4.000 Headlines × ~15 tokens = 60.000 input tokens/Stunde
DeepSeek-V3: ~$0.038/Stunde → ~$27/Monat
```

### 5.3 Kategorien

```
finance | geopolitics | energy | technology | health | politics | general
```

### 5.4 Langfristige Strategie

```
V1 (jetzt):   DeepSeek klassifiziert → Labels in Supabase speichern
V2 (später):  Embeddings mitspeichern (sentence-transformers → pgvector)
V3:           Eigenes Modell auf ~3 Mio. gelabelten Headlines
              → $0 laufende Klassifikationskosten
```

---

## 6. Job-System

### 6.1 APScheduler (stündlich, in-process)

```python
# marketmood/scheduler.py
scheduler.add_job(
    fetch_and_analyze,
    'interval',
    hours=1,
    id='gmm_hourly',
    replace_existing=True,  # verhindert Duplikate bei Restart
)
```

Startet automatisch via `MarketmoodConfig.ready()` wenn Django hochfährt.

**Warum kein Railway Cron:** APScheduler läuft im selben Prozess, kein extra Service, keine extra Kosten. Railway Cron nur für schwere ML-Pipelines nötig.

### 6.2 Supabase Cron (täglich, server-seitig)

```sql
-- Läuft täglich um 02:00 UTC
-- Löscht Headlines älter als 20 Tage
select cron.schedule(
    'delete-old-headlines',
    '0 2 * * *',
    $$ delete from articles where created_at < now() - interval '20 days'; $$
);
```

**Retention-Entscheidung:** 20 Tage — guter Kompromiss zwischen Datenmenge und Nutzwert.

### 6.3 Railway Cron (täglich, SPV2 — unverändert)

```
Alpha Routine: täglich 00:00 UTC
Beta Routine:  wöchentlich (Modell-Updates)
```

Bleibt auf eigenem Railway Service, wird von HoS.dev nur gelesen.

### 6.4 Übersicht

```
APScheduler (stündlich):
├── RSS Feeds fetchen
├── Duplikate filtern  
├── DeepSeek Batch-Klassifikation (async, 50er Batches)
├── VADER Sentiment
└── Supabase write (articles)

Supabase Cron (täglich 02:00 UTC):
└── DELETE articles WHERE created_at < now() - 20 days

Railway Cron SPV2 (unverändert):
└── Alpha Routine 00:00 UTC
```

---

## 7. Kosten-Übersicht (monatlich)

| Service | Kosten |
|---|---|
| Railway Web Service | ~$5 |
| DeepSeek Klassifikation | ~$27 |
| Supabase Pro (wenn nötig) | $25 |
| Domain houseofstocks.dev | ~$1 |
| **Gesamt** | **~$58/Monat** |

**Break-Even:** Ein einziger Pro-User (€19) deckt fast die gesamten laufenden Kosten.

---

## 8. Navigation & URL-Struktur

```
/                   → core:index      (Startseite)
/preise/            → core:preise     (Mitgliedschaftsstufen)
/waitlist/          → core:waitlist   (Email eintragen, POST)
/stimmung/          → mood:index      (GMM — TODO)
/prognosen/         → stockpredict:index (SPV2 — TODO)
/accounts/          → allauth URLs    (Login, Signup, Logout)
/admin/             → Django Admin
```

---

## 9. Design-Entscheidungen

### 9.1 Dark/Light Theme

- Default: Dark (Bloomberg-Stil)
- Toggle: Hell/Dunkel Button in Navigation
- Persistenz: localStorage (TODO V3: in Supabase wenn eingeloggt)

### 9.2 Farb-Palette

```css
--gold:     #c9a84c   /* Primärakzent, CTAs */
--gold2:    #e8c97a   /* Hover-Zustand */
--gold-dim: #7a6230   /* Tags, Labels */
--bg:       #0a0a08   /* Hintergrund Dark */
--text:     #e8e6df   /* Text Dark */
```

### 9.3 Ticker

Scrollender Kursticker oben auf der Startseite — V1 statisch, V2 Live-Daten aus Supabase.

---

## 10. Rechtliche Überlegungen

### 10.1 Disclaimer (eingebaut)

Auf allen Seiten sichtbar:

> Alle auf HouseofStocks.dev dargestellten Inhalte, Signale und Analysen dienen ausschließlich zu Informations- und Bildungszwecken. Sie stellen keine Anlageberatung, Vermögensverwaltung oder Aufforderung zum Kauf oder Verkauf von Wertpapieren im Sinne des Wertpapierhandelsgesetzes (WpHG) dar. Vergangene Ergebnisse sind kein verlässlicher Indikator für zukünftige Entwicklungen.

### 10.2 BaFin-Risiko

**GMM:** Unkritisch — Nachrichten-Sentiment ist reine Information.

**StockPredict bezahlte Signale:** Potenziell kritisch. Bezahlte Handelssignale könnten von der BaFin als Anlageberatung nach WpHG eingestuft werden.

**Maßnahmen:**
- Disclaimer auf allen Seiten (erledigt)
- Vor Paid Launch: Rechtsanwalt für FinTech/Kapitalmarktrecht
- Budget: einmalig ~€500-1.500 für rechtssichere AGB + Disclaimer

---

## 11. Deployment

### 11.1 Railway

```
Service:    houseofstocks (Web)
Region:     EU West (Amsterdam)
Builder:    Railpack
Start:      gunicorn houseofstocks.wsgi --bind 0.0.0.0:$PORT
```

### 11.2 Environment Variables (Railway)

```
SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=houseofstocks.up.railway.app,houseofstocks.dev,www.houseofstocks.dev
CSRF_TRUSTED_ORIGINS=https://houseofstocks.up.railway.app,https://houseofstocks.dev,https://www.houseofstocks.dev
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=***
DB_HOST=db.djkvuq.supabase.co
DB_PORT=5432
SUPABASE_URL=https://djkvuq.supabase.co
SUPABASE_ANON_KEY=***
SUPABASE_SERVICE_KEY=***
DEEPSEEK_API_KEY=*** (ausstehend)
```

### 11.3 DNS (Namecheap → Railway)

```
Type     Host              Value
CNAME    @                 ik.up.railway.app
CNAME    www               ik.up.railway.app
TXT      _railway-verify   railway-verify=f9dc14755b68...
```

### 11.4 UptimeRobot

Monitor: https://www.houseofstocks.dev  
Interval: alle 5 Minuten  
Zweck: Railway Cold Starts verhindern

---

## 12. TODO Backlog

### V1 (unmittelbar)

- [ ] GMM Code aus `market_mood_globe/` nach `marketmood/` migrieren
- [ ] DeepSeek Batch-Classifier implementieren
- [ ] APScheduler in `marketmood/apps.py` aktivieren
- [ ] Supabase Cron für 20-Tage Cleanup anlegen
- [ ] `stockpredict/services.py` Read-Layer implementieren
- [ ] Impressum + Datenschutz Seiten anlegen
- [ ] spaCy Englisches Modell (`en_core_web_sm`) in requirements

### V2 (nach Launch)

- [ ] Stripe Integration für Paid Tiers
- [ ] Email Notifications via Resend API
- [ ] Live Ticker-Daten aus Supabase
- [ ] FinBERT für Top-3 Headlines pro Batch
- [ ] Google/LinkedIn Social Login (Allauth)
- [ ] DeepSeek API Key besorgen

### V3 (nach AWS Kurs)

- [ ] AWS als primäres Backend (Elastic Beanstalk oder ECS)
- [ ] Supabase als Fallback/Mirror
- [ ] Flag-gesteuertes Storage Routing implementieren
- [ ] FinBERT als AWS Lambda + SageMaker Inference Endpoint
- [ ] pgvector Embeddings in Supabase für eigenes Klassifikationsmodell
- [ ] LinkedIn Post: "Migration von Railway auf AWS"

---

## 13. LinkedIn Build-in-Public

HouseofStocks.dev wird im bestehenden Build-in-Public Format dokumentiert.

**Geplante Posts:**
- Launch-Ankündigung
- Architektur-Entscheidungen (ein Projekt vs. Microservices)
- DeepSeek Klassifikation: Warum Keywords nicht reichen
- Tier-System Design: Wie man Mehrwert schichtweise aufbaut
- AWS Migration (V3)

---

*Dokumentation wird laufend aktualisiert.*  
*Letztes Update: 18. März 2026*


# 1. venv mit Python 3.11
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. pip updaten
pip install --upgrade pip

# 3. Django Projekt anlegen
pip install django
django-admin startproject houseofstocks .

# 4. Apps anlegen
python manage.py startapp core
python manage.py startapp accounts
python manage.py startapp stockpredict
python manage.py startapp marketmood

# 5. Alle Dependencies
pip install django-allauth django-apscheduler httpx supabase `
            python-dotenv whitenoise gunicorn psycopg2-binary `
            requests feedparser spacy vaderSentiment `
            sentence-transformers

# 6. requirements.txt
pip freeze > requirements.txt


# Englisches Modell
python -m spacy download en_core_web_sm

# pip updaten
python.exe -m pip install --upgrade pip


✅ manage.py
✅ houseofstocks/     (Projekt-Root mit settings.py)
✅ core/
✅ accounts/
✅ stockpredict/
✅ marketmood/
✅ requirements.txt

# .env Datei anlegen
New-Item .env
New-Item .gitignore