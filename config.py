"""
config.py – zentrale Konfigurationsdatei für Gabis Kleinanzeigen Assistent.

Hier stellst du per Flag um, ob lokal (Ollama) oder via OpenAI-API
gearbeitet wird – sowie die wichtigsten Modell- und Temperatur­parameter.
"""

# ---------------------------------------------------------------------------
# Umschalten zwischen OpenAI-Cloud und lokalem Ollama-Server
# ---------------------------------------------------------------------------
# False  →  OpenAI ChatCompletion (API-Key in st.secrets["openai_api_key"])
# True   →  lokales Modell über laufenden Ollama-Daemon (http://127.0.0.1:11434)
USE_OLLAMA: bool = False

# ---------------------------------------------------------------------------
# OpenAI-Einstellungen  (nur relevant wenn USE_OLLAMA == False)
# ---------------------------------------------------------------------------
OPENAI_MODEL: str = "gpt-4"      # z. B. "gpt-4" oder "gpt-3.5-turbo"
OPENAI_TEMPERATURE: float = 0.7  # 0.0 = deterministisch, 1.0 = kreativ

# ---------------------------------------------------------------------------
# Ollama-Einstellungen  (nur relevant wenn USE_OLLAMA == True)
# ---------------------------------------------------------------------------
OLLAMA_HOST: str = "http://127.0.0.1:11434"   # URL des lokalen Ollama-Servers
OLLAMA_MODEL: str = "llama3.2:3b"             # Modellbezeichnung in Ollama
OLLAMA_TEMPERATURE: float = 0.7               # Matching OpenAI-Temperature

# ---------------------------------------------------------------------------
# Weitere globale Konstanten (falls später benötigt)
# ---------------------------------------------------------------------------
# Beispiel: maximale Tokenzahl, Standard-Kalenderpfad, etc.
MAX_OUTPUT_TOKENS: int = 500
ICS_PATH: str = "data/calendar.ics"
