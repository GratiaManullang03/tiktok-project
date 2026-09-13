import os

# Settings() requires these - set test defaults before any app.core.config import
# so tests don't need a real .env file.
os.environ.setdefault("PGHOST", "localhost")
os.environ.setdefault("PGDATABASE", "tiktok_test")
os.environ.setdefault("PGUSER", "user")
os.environ.setdefault("PGPASSWORD", "password")
os.environ.setdefault("GROQ_API_KEY", "test-key")
