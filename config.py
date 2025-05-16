"""
Globale Konfiguration (Modelle, API-Keys, Zeitzone).
Lädt .env lokal UND Streamlit-Secrets in der Cloud.
"""

import os
from pathlib import Path

# 1) .env einlesen (nur lokal relevant)
try:
    from dotenv import load_dotenv

    # .env im Projekt­root suchen
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=False)
except ImportError:
    # python-dotenv nicht installiert → ignorieren
    pass

# 2) Key zunächst aus der Umgebung holen
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# 3) Wenn leer → versuchen, aus Streamlit-Secrets zu lesen
try:
    import streamlit as st  # funktioniert nur, wenn Code im Streamlit-Runtime läuft

    if not OPENAI_API_KEY and "OPENAI_API_KEY" in st.secrets:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except ModuleNotFoundError:
    # Streamlit nicht importierbar (z. B. bei reinem CLI-Script) → ignorieren
    pass

# 4) Weitere Defaults
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

# 5) Optional sofort in openai-SDK registrieren
try:
    import openai

    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    # openai nicht installiert – z. B. reiner Ollama-Betrieb
    pass
