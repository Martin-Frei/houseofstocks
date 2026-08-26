# HouseofStocks.dev

> **FinTech platform for global market sentiment and stock predictions**  
> Live: [houseofstocks.dev](https://houseofstocks.dev) · Status: Beta · Since March 2026

---

## What is HouseofStocks?

HouseofStocks is a Django monolith that brings together two independent ML projects under a shared interface:

**Global Market Mood (GMM)** — An hourly NLP pipeline that fetches, classifies, and analyzes sentiment from over 100,000 news articles across ~100 countries every day. The result: an interactive world map showing whether market sentiment in a region is currently bullish, neutral, or bearish.

**StockPredict V2 (SPV2)** — An LSTM + XGBoost ensemble model for 12 bank stocks. HouseofStocks reads the daily predictions from a separate database and displays them based on tier level. The SPV2 pipeline itself runs unchanged on its own Railway service.

---

## Architecture

```
houseofstocks.dev (Railway — EU West)
│
├── core/          Homepage, Landing, Disclaimer, Health Check
├── accounts/      Login, Signup, UserProfile, Tier System
├── marketmood/    GMM Pipeline + Dashboard + World Map  ← Main Project
└── stockpredict/  SPV2 Read-Only Viewer
         │
         ├── Supabase (global_market_mood)   ← GMM writes & reads here
         │   ├── articles          (Headlines, max. 20 days)
         │   ├── mood_snapshots    (hourly sentiment snapshot per region)
         │   └── Django Tables     (accounts, sessions, apscheduler_jobs)
         │
         └── Supabase (portfolio_site)        ← SPV2 read-only
             └── predictions       (daily predictions, 12 bank stocks)
```

**Why a monolith instead of microservices:**  
Shared authentication and a unified tier system (`free/pro/premium`) apply to both main features. One user, one login, one database table — with separate services, this would be significantly more complex to build and maintain.

---

## GMM Pipeline — How It Works

The pipeline runs automatically every 3 hours via APScheduler (in-process, no extra service).

```
RSS Feeds (~200 sources, ~100 countries)
        ↓
[1] fetcher.py         Fetch & normalize headlines
        ↓              feedparser, socket timeout 15s, deduplication by title
[2] topic_filter.py    Context-based classification with DeepSeek
        ↓              50 headlines/batch, 10 parallel requests, ~16 sec/round
[3] sentiment.py       Sentiment analysis with VADER + Finance Lexicon
        ↓              Compound score -1.0 to +1.0, bullish/neutral/bearish
[4] supabase_client.py Save articles to Supabase (upsert on_conflict="url")
        ↓
[5] aggregator.py      Calculate score per region (Option B: topic-weighted)
        ↓              → mood_snapshots INSERT
Dashboard + World Map
```

### The Most Important Design Decision: Option B Aggregation

Instead of calculating the simple average of all articles (Option A), the aggregator first calculates a score per topic area (finance, geopolitics, energy, ...) and then averages these topic scores.

**Why:** If 40 articles appear on one topic and only 5 on another, Option A would overweight the more frequent topic. Option B gives each topic equal weight — regardless of article count.

### Topic Classification: DeepSeek Instead of spaCy

The predecessor used spaCy keyword matching. This produced systematic errors because keywords don't understand context:

```
spaCy:   "Solar panels stolen"        → energy     ❌
DeepSeek: "Solar panels stolen"       → crime      ✅

spaCy:   "Russia halts gas pipeline"  → finance    ❌
DeepSeek: "Russia halts gas pipeline" → geopolitics ✅
```

### Sentiment: VADER + Custom Finance Lexicon

VADER is trained on social media and doesn't know financial terms with the correct weightings. The custom lexicon adds:

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

**Why not FinBERT:** FinBERT is more precise but requires GPU inference. At 4,000 articles/hour, that's not practical. FinBERT is planned for V2 — then only for the top 3 headlines per region.

---

## Tech Stack

| Component | Technology | Why |
|---|---|---|
| Backend | Django 5.2 | Familiar, Auth + Admin included |
| Authentication | django-allauth | Email verification, Social Login prepared |
| Scheduler | APScheduler + django-apscheduler | In-process, no extra service/costs |
| Database | Supabase PostgreSQL | GMM data already there, REST API included |
| Async HTTP | httpx | For DeepSeek batch calls |
| Feed Parser | feedparser | RSS 1.0/2.0/Atom out-of-the-box |
| Sentiment | vaderSentiment | Milliseconds/article, deterministic |
| Classification | DeepSeek API | Context-based, ~$19/month |
| ORM Connector | psycopg2-binary | PostgreSQL direct |
| Static Files | Whitenoise | No CDN needed for V1 |
| Hosting | Railway (EU West) | Simple deployment, familiar platform |
| Monitoring | UptimeRobot | HTTP + Keyword monitoring, free tier |
| CSS | Pure CSS | No build process (no Tailwind, no Webpack) |
| Fonts | Instrument Serif + DM Mono + Geist | FinTech premium aesthetics |

**Deliberately not used:**
- Celery/Redis → APScheduler is sufficient, one less service
- Tailwind CSS → requires build process, unnecessary complexity for Railway
- React/Vue → Django Templates are sufficient for V1
- Railway Postgres → Supabase already in place

---

## Tier System

A `UserProfile` with `OneToOneField` to the Django `User` controls access:

| Tier | GMM | StockPredict V2 | Price |
|---|---|---|---|
| **Free** | News > 12h old | Yesterday's predictions + hit rate | €0 |
| **Pro** | Live News | Today's predictions | €19/month |
| **Premium** | Live + Keyword Search | Holy Grail Signals (ZS ≥ 1.0) | €99/month |

Every new user automatically receives `tier='free'` via Django Signal (`post_save`). Stripe integration is prepared for V2 (`stripe_customer_id` field already in schema).

---

## Job System

```
APScheduler (in-process, background thread)
├── run_pipeline      every 3 hours
│   ├── fetch_all_sources()     RSS worldwide
│   ├── enrich_articles()       DeepSeek classification
│   ├── analyze_all()           VADER sentiment
│   ├── save_articles()         → Supabase articles (upsert)
│   └── run_aggregator()        → Supabase mood_snapshots (insert)
│
└── cleanup_articles   daily at 02:00 UTC
    └── Delete articles older than 20 days

SPV2 Pipeline (separate Railway service)
└── Alpha Routine     daily at 00:00 UTC (LSTM + XGBoost, writes to portfolio_site)
```

**Retention Strategy:** 20 days — enough for trend analysis, prevents unlimited DB growth on the Supabase free tier.

**Manual Pipeline Trigger** via Railway CLI:
```bash
railway run python manage.py shell -c "from marketmood.scheduler import run_pipeline; run_pipeline()"
```

---

## Monitoring & Health Check

The site can be reachable and still show no data — if Supabase doesn't respond or the pipeline is stuck, Django delivers an empty dashboard with HTTP 200. A simple uptime check won't detect this.

### Health Endpoint

`GET /api/health/` checks the actual data flow:

| Check | What is verified | Threshold |
|-------|-----------------|----------|
| `snapshots` | Latest `mood_snapshot` in Supabase | < 4 hours old |
| `articles` | Latest article in Supabase | < 4 hours old |

**Why 4 hours:** The pipeline runs every 3 hours. 4h provides a one-hour buffer — a missed run is detected without generating false positives during normal timing.

**Why SERVICE_KEY:** Supabase RLS blocks the ANON_KEY on filtered queries (`WHERE created_at >= ...`), even though unfiltered queries work. The health check therefore uses the SERVICE_KEY — this is safe because the endpoint only reads `created_at`, writes nothing, and the key is only referenced (`settings.SUPABASE_SERVICE_KEY`) in the code, not hardcoded as a value.

```json
// Healthy (200)
{
  "status": "healthy",
  "checks": {
    "snapshots": "ok",
    "latest_snapshot": "2026-08-24T19:56:19.16038+00:00",
    "articles": "ok",
    "latest_article": "2026-08-24T19:55:31.884918+00:00"
  }
}

// Unhealthy (503)
{
  "status": "unhealthy",
  "issues": ["No mood_snapshot in the last 4 hours"],
  "checks": {
    "snapshots": "stale",
    "articles": "ok",
    "latest_article": "2026-08-24T17:58:44Z"
  }
}
```

### UptimeRobot Configuration

Two monitors run in parallel:

| Monitor | Type | URL | Checks |
|---------|------|-----|--------|
| www.houseofstocks.dev | HTTP(s) | `https://houseofstocks.dev` | Site reachable? |
| HoS Health Check | Keyword | `https://houseofstocks.dev/api/health/` | Data fresh? |

The Keyword Monitor searches for `"healthy"` in the response. If the word is missing (503, timeout, or broken response) → alert via email/push.

### Monitoring Architecture

```
UptimeRobot (every 5 min)
    │
    ├── Monitor 1: HTTP(s)
    │   └── GET houseofstocks.dev → Site reachable?
    │
    ├── Monitor 2: Keyword
    │   └── GET /api/health/
    │       ├── Supabase mood_snapshots  → fresh? ✓/✗
    │       └── Supabase articles        → fresh? ✓/✗
    │       (SERVICE_KEY due to RLS)
    │
    ├── "healthy" exists   → all good
    └── "healthy" missing  → Alert via email/push

Railway Notifications (Settings → Notifications)
└── Failed builds/deploys → Email alert
```

---

## Project Structure

```
houseofstocks/
├── houseofstocks/          Django Project Root
│   ├── settings.py         Configuration (Supabase, DeepSeek, APScheduler)
│   ├── urls.py             URL routing
│   └── wsgi.py
│
├── core/                   Homepage, Pricing Page, Disclaimer, Health Check
│   ├── views.py                index, pricing, waitlist, health_check
│   ├── urls.py                 / + /pricing/ + /waitlist/ + /api/health/
│   ├── context_processors.py   Ticker data for all templates
│   └── services/
│       └── ticker.py           Live ticker (stocks + news + GMM score)
│
├── accounts/               Auth extension
│   └── models.py           UserProfile + Tier System + Django Signals
│
├── marketmood/             GMM — Main Project
│   ├── pipeline/
│   │   ├── api_sources.py      ~200 RSS feeds for ~100 countries
│   │   ├── fetcher.py          Feed fetching & normalization
│   │   ├── topic_filter.py     DeepSeek batch classification
│   │   ├── sentiment.py        VADER + Finance Lexicon
│   │   ├── aggregator.py       Score calculation (Option B)
│   │   └── supabase_client.py  DB layer (read + write)
│   ├── scheduler.py            APScheduler jobs
│   └── apps.py                 Scheduler startup via ready()
│
├── stockpredict/           SPV2 Read-Only
│   └── services.py             Supabase REST API read layer
│
└── templates/
    ├── marketmood/
    │   ├── dashboard.html      GMM Dashboard
    │   └── world_map.html      Interactive world map (jsVectorMap)
    └── stockpredict/
        └── dashboard.html      SPV2 predictions view
```

---

## Supabase Database Structure

### `articles` (GMM Headlines)

| Column | Type | Description |
|---|---|---|
| `source` | text | Feed name (e.g. "DW Business") |
| `source_region` | text | ISO country code (e.g. "DE") |
| `title` | text | Headline |
| `topic` | text | DeepSeek classification (finance, geopolitics, ...) |
| `vader_compound` | float | Sentiment score (-1.0 to +1.0) |
| `vader_label` | text | bullish / neutral / bearish |
| `url` | text | Unique key for upsert |
| `published` | timestamp | Publication date |
| `finbert_compound` | float | V2: FinBERT score (currently null) |
| `spacy_entities` | jsonb | V3: Named entities (currently []) |

### `mood_snapshots` (Hourly Sentiment Snapshot)

| Column | Type | Description |
|---|---|---|
| `region` | text | ISO country code |
| `final_score` | float | Weighted topic score |
| `final_label` | text | bullish / neutral / bearish |
| `score_finance` | float | Topic score Finance |
| `score_geopolitics` | float | Topic score Geopolitics |
| `score_energy` | float | Topic score Energy |
| `article_count` | int | Number of articles for this snapshot |
| `top_headlines` | jsonb | Top 3 headlines with score and URL |
| `created_at` | timestamp | Timestamp of the snapshot |

---

## Costs (Monthly)

| Service | Cost |
|---|---|
| Railway Web Service | ~$5 |
| DeepSeek Classification | ~$19 |
| Supabase (Free Tier) | $0 |
| UptimeRobot (Free Tier) | $0 |
| Domain houseofstocks.dev | ~$1 |
| **Total** | **~$25/month** |

**Break-even:** Two free-to-pro upgrades (2 × €19 = €38) cover the entire running costs.

---

## Local Setup

```bash
# 1. Clone repository
git clone https://github.com/Martin-Frei/houseofstocks
cd houseofstocks

# 2. Virtual environment (Python 3.11)
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env
cp .env.example .env
# Fill in fields (see below)

# 5. Run database migrations
python manage.py migrate

# 6. Start development server
python manage.py runserver
```

### Required Environment Variables

```env
# Django
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase GMM (global_market_mood project)
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=
DB_HOST=
DB_PORT=5432

# Supabase SPV2 (portfolio_site project)
SPV2_SUPABASE_URL=
SPV2_SUPABASE_ANON_KEY=

# DeepSeek API
DEEPSEEK_API_KEY=
```

**Important:** `SUPABASE_SERVICE_KEY` is required for server-side access (bypasses Row-Level Security). Used for both pipeline write operations and the health check endpoint. Never commit to Git.

---

## Deployment (Railway)

```
Region:   EU West (Amsterdam)
Builder:  Railpack (auto-detect)
Start:    gunicorn houseofstocks.wsgi --bind 0.0.0.0:$PORT
```

DNS via Namecheap → Railway CNAME.  
UptimeRobot pings every 5 minutes — prevents Railway cold starts and monitors pipeline freshness via `/api/health/`.

### Railway CLI

```bash
railway login          # Browser login
railway link           # Link project
railway run <command>  # Run command on Railway
```

---

## Roadmap

### V1 — Beta (March 2026) ✅
- GMM Pipeline live (RSS → DeepSeek → VADER → Supabase)
- World map with jsVectorMap
- Tier system (Free/Pro/Premium)
- SPV2 read layer
- Health check endpoint + UptimeRobot monitoring

### V2 — Post-Launch
- Stripe integration for paid tiers
- FinBERT for top 3 headlines per region
- Email notifications (Resend API)
- Embeddings in Supabase via pgvector (foundation for custom model)
- Social login (Google/LinkedIn via allauth)

### V3 — After AWS Course
- AWS as primary backend (Elastic Beanstalk or ECS)
- Supabase as fallback
- Custom classification model trained on ~3M DeepSeek-labeled headlines → $0 classification costs
- FinBERT as AWS Lambda + SageMaker inference endpoint

---

## Legal Notice

All content, signals, and analyses presented on HouseofStocks.dev are for informational and educational purposes only. They do not constitute investment advice and are not intended as a solicitation to buy or sell securities within the meaning of the German Securities Trading Act (WpHG). Past results are not a reliable indicator of future performance.

Before launching paid trading signals: Legal consultation for FinTech/capital markets law (BaFin compliance).

---

*Repository: private · Last updated: August 2026*