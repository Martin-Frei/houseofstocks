# HouseofStocks.dev

> **FinTech-Plattform für globale Marktstimmung und Aktienprognosen**  
> Live: [houseofstocks.dev](https://houseofstocks.dev) · Status: Beta · Seit März 2026

---

## Was ist HouseofStocks?

HouseofStocks ist ein Django-Monolith der zwei eigenständige ML-Projekte unter einer gemeinsamen Oberfläche zusammenführt:

**Global Market Mood (GMM)** — Eine stündlich laufende NLP-Pipeline die täglich über 100.000 Nachrichtenartikel aus ~100 Ländern abruft, klassifiziert und auf Stimmung analysiert. Das Ergebnis: eine interaktive Weltkarte die zeigt ob die Marktstimmung in einer Region gerade bullish, neutral oder bearish ist.

**StockPredict V2 (SPV2)** — Ein LSTM + XGBoost Ensemble-Modell für 12 Bankaktien. HouseofStocks liest die täglich berechneten Vorhersagen aus einer separaten Datenbank und stellt sie tier-basiert dar. Die SPV2-Pipeline selbst läuft unverändert auf einem eigenen Railway-Service.

---

## Architektur

```
houseofstocks.dev (Railway — EU West)
│
├── core/          Startseite, Landing, Disclaimer
├── accounts/      Login, Signup, UserProfile, Tier-System
├── marketmood/    GMM Pipeline + Dashboard + Weltkarte  ← Hauptprojekt
└── stockpredict/  SPV2 Read-Only Viewer
         │
         ├── Supabase (global_market_mood)   ← GMM schreibt & liest hier
         │   ├── articles          (Headlines, max. 20 Tage)
         │   ├── mood_snapshots    (stündliches Stimmungsbild pro Region)
         │   └── Django Tabellen   (accounts, sessions, apscheduler_jobs)
         │
         └── Supabase (portfolio_site)        ← SPV2 nur lesend
             └── predictions       (tägl. Vorhersagen, 12 Bankaktien)
```

**Warum ein Monolith statt Microservices:**  
Shared Authentication und ein gemeinsames Tier-System (`free/pro/premium`) gelten für beide Hauptfeatures. Ein User, ein Login, eine Datenbanktabelle — mit getrennten Services wäre das deutlich aufwändiger zu bauen und zu pflegen.

---

## GMM Pipeline — Wie sie funktioniert

Die Pipeline läuft automatisch alle 3 Stunden via APScheduler (in-process, kein extra Service).

```
RSS Feeds (~200 Quellen, ~100 Länder)
        ↓
[1] fetcher.py         Headlines abrufen & normalisieren
        ↓              feedparser, socket timeout 15s, Deduplizierung per Titel
[2] topic_filter.py    Kontextbasierte Klassifikation mit DeepSeek
        ↓              50 Headlines/Batch, 10 parallele Requests, ~16 Sek/Runde
[3] sentiment.py       Stimmungsanalyse mit VADER + Finance Lexicon
        ↓              Compound Score -1.0 bis +1.0, bullish/neutral/bearish
[4] supabase_client.py Artikel in Supabase speichern (upsert on_conflict="url")
        ↓
[5] aggregator.py      Score pro Region berechnen (Option B: Topic-gewichtet)
        ↓              → mood_snapshots INSERT
Dashboard + Weltkarte
```

### Die wichtigste Designentscheidung: Option B Aggregation

Statt den einfachen Durchschnitt aller Artikel zu berechnen (Option A), berechnet der Aggregator zuerst einen Score pro Themengebiet (finance, geopolitics, energy, ...) und dann den Durchschnitt dieser Topic-Scores.

**Warum:** Wenn zu einem Thema 40 Artikel erscheinen und zu einem anderen nur 5, würde Option A das häufige Thema übergewichten. Option B gibt jedem Topic gleiches Gewicht — unabhängig von der Artikelanzahl.

### Topic-Klassifikation: DeepSeek statt spaCy

Der Vorgänger verwendete spaCy Keyword-Matching. Das produzierte systematische Fehler weil Keywords keinen Kontext verstehen:

```
spaCy:   "Solaranlagen gestohlen"     → energy     ❌
DeepSeek: "Solaranlagen gestohlen"    → crime      ✅

spaCy:   "Russia halts gas pipeline"  → finance    ❌
DeepSeek: "Russia halts gas pipeline" → geopolitics ✅
```

### Sentiment: VADER + Custom Finance Lexicon

VADER ist für Social Media trainiert und kennt Finanzwörter nicht mit den richtigen Gewichtungen. Das Custom Lexicon ergänzt:

```python
FINANCE_LEXICON = {
    "bankruptcy":   -3.0,
    "market_crash": -2.5,
    "recession":    -2.5,
    "rate_hike":    -1.5,
    "earnings_beat": 2.5,
    "market_rally":  2.0,
    ...
}
```

**Warum nicht FinBERT:** FinBERT ist präziser aber braucht GPU-Inference. Bei 4.000 Artikeln/Stunde ist das nicht praktikabel. FinBERT ist für V2 geplant — dann nur für die Top-3-Headlines pro Region.

---

## Tech Stack

| Komponente | Technologie | Warum |
|---|---|---|
| Backend | Django 5.2 | Vertraut, Auth + Admin inklusive |
| Authentifizierung | django-allauth | Email-Verifizierung, Social Login vorbereitet |
| Scheduler | APScheduler + django-apscheduler | In-process, kein extra Service/Kosten |
| Datenbank | Supabase PostgreSQL | GMM-Daten bereits dort, REST-API inkl. |
| Async HTTP | httpx | Für DeepSeek Batch-Calls |
| Feed-Parser | feedparser | RSS 1.0/2.0/Atom out-of-the-box |
| Sentiment | vaderSentiment | Millisekunden/Artikel, deterministisch |
| Klassifikation | DeepSeek API | Kontextbasiert, ~$19/Monat |
| ORM Connector | psycopg2-binary | PostgreSQL direkt |
| Static Files | Whitenoise | Kein CDN für V1 nötig |
| Hosting | Railway (EU West) | Einfaches Deployment, bekannte Platform |
| CSS | Reines CSS | Kein Build-Prozess (kein Tailwind, kein Webpack) |
| Fonts | Instrument Serif + DM Mono + Geist | FinTech Premium Ästhetik |

**Bewusst nicht verwendet:**
- Celery/Redis → APScheduler reicht, ein Service weniger
- Tailwind CSS → braucht Build-Prozess, unnötige Komplexität für Railway
- React/Vue → Django Templates reichen für V1
- Railway Postgres → Supabase bereits vorhanden

---

## Tier-System

Ein `UserProfile` mit `OneToOneField` zum Django `User` steuert den Zugriff:

| Tier | GMM | StockPredict V2 | Preis |
|---|---|---|---|
| **Free** | News > 12h alt | Gestrige Vorhersagen + Trefferquote | €0 |
| **Pro** | Live News | Heutige Vorhersagen | €19/Monat |
| **Premium** | Live + Keyword-Suche | Holy Grail Signale (ZS ≥ 1.0) | €99/Monat |

Jeder neue User bekommt automatisch `tier='free'` via Django Signal (`post_save`). Stripe-Integration ist für V2 vorbereitet (`stripe_customer_id`-Feld bereits im Schema).

---

## Job-System

```
APScheduler (in-process, Background Thread)
├── run_pipeline      alle 3 Stunden
│   ├── fetch_all_sources()     RSS weltweit
│   ├── enrich_articles()       DeepSeek Klassifikation
│   ├── analyze_all()           VADER Sentiment
│   ├── save_articles()         → Supabase articles (upsert)
│   └── run_aggregator()        → Supabase mood_snapshots (insert)
│
└── cleanup_articles   täglich 02:00 UTC
    └── Artikel älter als 20 Tage löschen

SPV2 Pipeline (separater Railway Service)
└── Alpha Routine     täglich 00:00 UTC (LSTM + XGBoost, schreibt in portfolio_site)
```

**Retention-Strategie:** 20 Tage — genug für Trend-Analyse, verhindert unbegrenztes DB-Wachstum auf dem Supabase Free Tier.

---

## Projektstruktur

```
houseofstocks/
├── houseofstocks/          Django Projekt Root
│   ├── settings.py         Konfiguration (Supabase, DeepSeek, APScheduler)
│   ├── urls.py             URL-Routing
│   └── wsgi.py
│
├── core/                   Startseite, Preisseite, Disclaimer
│   ├── context_processors.py   Ticker-Daten für alle Templates
│   └── ticker.py
│
├── accounts/               Auth-Erweiterung
│   └── models.py           UserProfile + Tier-System + Django Signals
│
├── marketmood/             GMM — Hauptprojekt
│   ├── pipeline/
│   │   ├── api_sources.py      ~200 RSS-Feeds für ~100 Länder
│   │   ├── fetcher.py          Feed-Abruf & Normalisierung
│   │   ├── topic_filter.py     DeepSeek Batch-Klassifikation
│   │   ├── sentiment.py        VADER + Finance Lexicon
│   │   ├── aggregator.py       Score-Berechnung (Option B)
│   │   └── supabase_client.py  DB-Schicht (read + write)
│   ├── scheduler.py            APScheduler Jobs
│   └── apps.py                 Scheduler-Start via ready()
│
├── stockpredict/           SPV2 Read-Only
│   └── services.py             Supabase REST API Read-Layer
│
└── templates/
    ├── marketmood/
    │   ├── dashboard.html      GMM Dashboard
    │   └── world_map.html      Interaktive Weltkarte (jsVectorMap)
    └── stockpredict/
        └── dashboard.html      SPV2 Prognosen-Ansicht
```

---

## Supabase Datenbankstruktur

### `articles` (GMM Headlines)

| Spalte | Typ | Beschreibung |
|---|---|---|
| `source` | text | Feed-Name (z.B. "DW Business") |
| `source_region` | text | ISO-Ländercode (z.B. "DE") |
| `title` | text | Headline |
| `topic` | text | DeepSeek Klassifikation (finance, geopolitics, ...) |
| `vader_compound` | float | Sentiment Score (-1.0 bis +1.0) |
| `vader_label` | text | bullish / neutral / bearish |
| `url` | text | Unique Key für upsert |
| `published` | timestamp | Erscheinungsdatum |
| `finbert_compound` | float | V2: FinBERT Score (derzeit null) |
| `spacy_entities` | jsonb | V3: Named Entities (derzeit []) |

### `mood_snapshots` (Stündliches Stimmungsbild)

| Spalte | Typ | Beschreibung |
|---|---|---|
| `region` | text | ISO-Ländercode |
| `final_score` | float | Gewichteter Topic-Score |
| `final_label` | text | bullish / neutral / bearish |
| `score_finance` | float | Topic-Score Finance |
| `score_geopolitics` | float | Topic-Score Geopolitics |
| `score_energy` | float | Topic-Score Energy |
| `article_count` | int | Anzahl Artikel für diesen Snapshot |
| `top_headlines` | jsonb | Top-3 Headlines mit Score und URL |
| `created_at` | timestamp | Zeitpunkt des Snapshots |

---

## Kosten (monatlich)

| Service | Kosten |
|---|---|
| Railway Web Service | ~$5 |
| DeepSeek Klassifikation | ~$19 |
| Supabase (Free Tier) | $0 |
| Domain houseofstocks.dev | ~$1 |
| **Gesamt** | **~$25/Monat** |

**Break-Even:** Zwei Free-to-Pro Upgrades (2 × €19 = €38) decken die gesamten laufenden Kosten.

---

## Lokales Setup

```bash
# 1. Repository klonen
git clone https://github.com/Martin-Frei/houseofstocks
cd houseofstocks

# 2. Virtual Environment (Python 3.11)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Mac/Linux

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. .env anlegen
cp .env.example .env
# Felder befüllen (siehe unten)

# 5. Datenbank migrieren
python manage.py migrate

# 6. Entwicklungsserver starten
python manage.py runserver
```

### Benötigte Environment Variables

```env
# Django
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase GMM (global_market_mood Projekt)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=
DB_HOST=
DB_PORT=5432

# Supabase SPV2 (portfolio_site Projekt)
SPV2_SUPABASE_URL=
SPV2_SUPABASE_ANON_KEY=

# DeepSeek API
DEEPSEEK_API_KEY=
```

**Wichtig:** `SUPABASE_SERVICE_KEY` wird für serverseitige Schreibzugriffe benötigt (umgeht Row-Level-Security). Niemals in Git committen.

---

## Deployment (Railway)

```
Region:   EU West (Amsterdam)
Builder:  Railpack (auto-detect)
Start:    gunicorn houseofstocks.wsgi --bind 0.0.0.0:$PORT
```

DNS via Namecheap → Railway CNAME.  
UptimeRobot pingt alle 5 Minuten um Railway Cold Starts zu verhindern.

---

## Roadmap

### V1 — Beta (März 2026) ✅
- GMM Pipeline live (RSS → DeepSeek → VADER → Supabase)
- Weltkarte mit jsVectorMap
- Tier-System (Free/Pro/Premium)
- SPV2 Read-Layer

### V2 — Nach Launch
- Stripe Integration für Paid Tiers
- FinBERT für Top-3-Headlines pro Region
- Email Notifications (Resend API)
- Embeddings in Supabase via pgvector (Basis für eigenes Modell)
- Social Login (Google/LinkedIn via allauth)

### V3 — Nach AWS-Kurs
- AWS als primäres Backend (Elastic Beanstalk oder ECS)
- Supabase als Fallback
- Eigenes Klassifikationsmodell auf ~3 Mio. DeepSeek-gelabelten Headlines → $0 Klassifikationskosten
- FinBERT als AWS Lambda + SageMaker Inference Endpoint

---

## Rechtlicher Hinweis

Alle auf HouseofStocks.dev dargestellten Inhalte, Signale und Analysen dienen ausschließlich zu Informations- und Bildungszwecken. Sie stellen keine Anlageberatung dar und sind nicht als Aufforderung zum Kauf oder Verkauf von Wertpapieren im Sinne des WpHG zu verstehen. Vergangene Ergebnisse sind kein verlässlicher Indikator für zukünftige Entwicklungen.

Vor dem Launch bezahlter Handelssignale: Rechtsberatung für FinTech/Kapitalmarktrecht (BaFin-Konformität).

---

*Repository: privat · Letztes Update: Juni 2026*
