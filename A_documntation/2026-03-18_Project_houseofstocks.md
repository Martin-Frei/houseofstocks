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