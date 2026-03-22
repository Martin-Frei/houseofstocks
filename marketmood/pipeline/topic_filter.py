# mood/pipeline/topic_filter.py
# ============================================================
# TOPIC CLASSIFICATION — DeepSeek API Batch Classifier
# V1: DeepSeek klassifiziert alle Headlines kontextbasiert
# TODO V2: Eigenes Modell auf DeepSeek-Labels trainieren
#          (pgvector Embeddings in Supabase speichern)
# TODO V3: AWS Lambda Inference Endpoint für FinBERT
# ============================================================

import httpx
import asyncio
import json
import os
from django.conf import settings

CATEGORIES = ["finance", "geopolitics", "energy", "technology", "health", "crime", "politics", "general"]

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
BATCH_SIZE = 50
MAX_CONCURRENT = 10  # parallele Requests


# ============================================================
# DEEPSEEK BATCH CLASSIFIER
# ============================================================

async def _classify_batch_async(headlines: list[str], client: httpx.AsyncClient) -> list[str]:
    print(f"[DEBUG] API Key vorhanden: {bool(settings.DEEPSEEK_API_KEY)}")
    print(f"[DEBUG] Sende {len(headlines)} Headlines an DeepSeek...")
    
    
    """
    Sendet einen Batch von Headlines an DeepSeek.
    Gibt eine Liste von Kategorien zurück (gleiche Reihenfolge).
    """
    
    numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))

    prompt = f"""You are a news classifier. Classify each headline into exactly one category.

Categories and their meaning:
- finance: stock markets, banks, economy, interest rates, earnings, IPO, crypto
- geopolitics: wars, military, sanctions, diplomacy, NATO, international conflicts, trade wars
- energy: oil prices, gas prices, renewable energy markets, OPEC — NOT theft or crime involving energy equipment
- technology: tech companies, AI, software, cybersecurity, semiconductors
- health: diseases, vaccines, pandemics, pharma, medical research, WHO
- crime: theft, fraud, corruption, arrests, murder, terrorism, cyber attacks on individuals
- politics: elections, government, parliament, laws, domestic policy
- general: accidents, sports, culture, local news, anything that doesn't clearly fit above

Critical rules:
- "Solar panels stolen" = crime (theft, not energy market news)
- "Gas pipeline halted by Russia" = geopolitics (conflict, not energy price news)
- "COVID variant detected" = health (always health if about disease)
- "Hacker arrested" = crime (not technology)
- "Local bakery wins award" = general
- When in doubt → general

Respond ONLY with a JSON array of category strings, same order as input.
No explanation, no markdown, just: ["finance","general","health"]

Headlines:
{numbered}"""

    try:
        response = await client.post(
            DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,  # deterministisch
                "max_tokens": 200,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        # JSON Array parsen
        # Sicherheits-Strip falls doch Backticks kommen
        content = content.replace("```json", "").replace("```", "").strip()
        categories = json.loads(content)

        # Validierung: nur erlaubte Kategorien
        validated = []
        for cat in categories:
            cat = cat.lower().strip()
            validated.append(cat if cat in CATEGORIES else "general")

        # Länge sicherstellen
        if len(validated) != len(headlines):
            print(f"[DEEPSEEK] Warning: got {len(validated)} results for {len(headlines)} headlines")
            return ["general"] * len(headlines)

        return validated

    except Exception as e:
        print(f"[DEEPSEEK] Batch error: {e}")
        # Fallback: alles general
        return ["general"] * len(headlines)


async def _classify_all_async(headlines: list[str]) -> list[str]:
    """
    Klassifiziert alle Headlines in Batches mit MAX_CONCURRENT parallelen Requests.
    """
    batches = [headlines[i:i+BATCH_SIZE] for i in range(0, len(headlines), BATCH_SIZE)]
    results = []

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def bounded_classify(batch):
        async with semaphore:
            return await _classify_batch_async(batch, client)

    async with httpx.AsyncClient() as client:
        tasks = [bounded_classify(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks)

    for batch_result in batch_results:
        results.extend(batch_result)

    return results


# ============================================================
# ÖFFENTLICHE INTERFACE — gleich wie vorher
# ============================================================

def classify_topic(text: str, region: str = "DE") -> tuple[str, list]:
    """
    Klassifiziert einen einzelnen Text.
    Interface bleibt identisch zu V1 für Kompatibilität.
    matched_keywords ist leer (DeepSeek braucht keine Keywords).
    """
    # API Key vorhanden?
    if not getattr(settings, "DEEPSEEK_API_KEY", None):
        print("[DEEPSEEK] No API key — fallback to general")
        return "general", []

    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(_classify_all_async([text]))
        return results[0], []
    except Exception as e:
        print(f"[DEEPSEEK] classify_topic error: {e}")
        return "general", []


def enrich_articles(articles: list, region: str = None) -> list:
    if not articles:
        return []

    # DEBUG
    api_key = getattr(settings, "DEEPSEEK_API_KEY", None)
    print(f"[DEBUG] DEEPSEEK_API_KEY = '{api_key}'")
    
    if not api_key:
        print("[DEEPSEEK] No API key — all articles set to general")
        return [{**a, "topic": "general", "matched_keywords": []} for a in articles]

    # API Key Check
    if not getattr(settings, "DEEPSEEK_API_KEY", None):
        print("[DEEPSEEK] No API key — all articles set to general")
        return [{**a, "topic": "general", "matched_keywords": []} for a in articles]

    headlines = [a.get("text", a.get("title", ""))[:300] for a in articles]

    print(f"[DEEPSEEK] Classifying {len(headlines)} headlines in {len(headlines)//BATCH_SIZE + 1} batches...")

    try:
        # Async in sync Context ausführen
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Django/Gunicorn context — neuen Loop
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _classify_all_async(headlines))
                    categories = future.result()
            else:
                categories = loop.run_until_complete(_classify_all_async(headlines))
        except RuntimeError:
            categories = asyncio.run(_classify_all_async(headlines))

    except Exception as e:
        print(f"[DEEPSEEK] enrich_articles error: {e}")
        categories = ["general"] * len(articles)

    # Topic Distribution loggen
    topic_counts = {}
    for cat in categories:
        topic_counts[cat] = topic_counts.get(cat, 0) + 1
    print(f"[DEEPSEEK] Distribution: {topic_counts}")

    enriched = []
    for article, category in zip(articles, categories):
        enriched.append({
            **article,
            "topic": category,
            "matched_keywords": [],  # DeepSeek braucht keine Keywords
        })

    return enriched
