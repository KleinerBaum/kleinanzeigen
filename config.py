"""
Globale Konfiguration (Modelle, API-Keys, Zeitzone).
Lädt .env lokal UND Streamlit-Secrets in der Cloud.
"""
import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import openai


openai.api_key = st.secrets.get("openai_api_key", None) or os.getenv("openai_api_key")
if not openai.api_key:
    raise RuntimeError(
        "OpenAI-Modus aktiv, aber kein API-Key gefunden. "
        "Bitte in `.streamlit/secrets.toml` oder als ENV `openai_api_key` setzen "
        "oder `USE_OLLAMA=True` in config.py wählen."
    )
# 2) Key zunächst aus der Umgebung holen
openai_api_key: str | None = os.getenv("openai_api_key")

# 3) Wenn leer → versuchen, aus Streamlit-Secrets zu lesen
try:
    import streamlit as st  # funktioniert nur, wenn Code im Streamlit-Runtime läuft

    if not openai_api_key and "openai_api_key" in st.secrets:
        openai_api_key = st.secrets["openai_api_key"]
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

    if openai_api_key:
        openai.api_key = openai_api_key
except ImportError:
    # openai nicht installiert – z. B. reiner Ollama-Betrieb
    pass
