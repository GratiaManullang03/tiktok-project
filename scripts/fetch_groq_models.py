"""Fetch the current Groq model catalog and save it to docs/models.json.

Run with: python scripts/fetch_groq_models.py
Use this to re-check GROQ_MODEL is still valid whenever Groq updates their lineup.
"""
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY tidak ditemukan di file .env")

response = requests.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=30,
)
response.raise_for_status()

output_path = Path(__file__).resolve().parent.parent / "docs" / "models.json"
output_path.write_text(json.dumps(response.json(), indent=2))
print(f"Saved {len(response.json().get('data', []))} models to {output_path}")
