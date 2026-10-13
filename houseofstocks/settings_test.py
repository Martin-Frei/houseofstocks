# houseofstocks/settings_test.py
"""
Settings für pytest (F-07). Nie in Produktion verwenden.

Ziel: Tests laufen lokal und in GitHub Actions identisch und erreichen
weder eine echte Datenbank noch Supabase, DeepSeek oder Brevo.
"""
import os

# ── 1. Umgebung festlegen, BEVOR settings.py geladen wird ─────────────────────
# settings.py prüft SECRET_KEY und wertet DEBUG schon beim Import aus (F-09).
# load_dotenv() überschreibt bereits gesetzte Variablen nicht, deshalb
# gewinnen diese Werte gegen die lokale .env.
# Bewusst direkte Zuweisung statt setdefault: Tests nutzen nie echte Werte.
_TEST_ENV = {
    "DEBUG": "False",  # wie Produktion; lokal und CI gleich
    "SECRET_KEY": "test-only-not-a-secret",
    "SUPABASE_URL": "https://supabase.invalid",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_KEY": "test-service-key",
    "SPV2_SUPABASE_URL": "https://spv2.invalid",
    "SPV2_SUPABASE_ANON_KEY": "test-spv2-key",
    "DEEPSEEK_API_KEY": "test-deepseek-key",
    "BREVO_API_KEY": "test-brevo-key",
    "EMAIL_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
}
os.environ.update(_TEST_ENV)

from .settings import *  # noqa: E402,F401,F403

# ── 2. Datenbank: SQLite im Arbeitsspeicher ───────────────────────────────────
# Das ganze Dict ersetzen, damit OPTIONS {"sslmode": ...} verschwindet –
# SQLite kennt die Option nicht.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ── 3. Werte, die nicht aus der Umgebung kommen ──────────────────────────────
DEEPSEEK_API_URL = "https://deepseek.invalid/v1/chat/completions"

# Der Test-Client spricht HTTP. Mit Redirect bekäme jeder Request 301.
# Den Redirect selbst prüft ein eigener Test mit dem settings-Fixture.
SECURE_SSL_REDIRECT = False

# Schnelleres Hashing: Passwörter in Tests müssen nicht sicher sein.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]