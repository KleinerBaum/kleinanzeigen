import os
import streamlit as st

# 1. Zuerst versuchen wir, den Key aus den Umgebungsvariablen zu lesen 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 2. Falls keiner in der Umgebung, aus den Streamlit Secrets laden 
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    except Exception:
        OPENAI_API_KEY = None

# Optional: weitere Konfigurationsvariablen 
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Berlin")

# Wenn OpenAI installiert ist und wir einen API-Key haben, setzen wir ihn direkt 
try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except ImportError:
    # openai-Bibliothek evtl. nicht installiert (wenn nur lokales LLM genutzt wird)
    pass
