import os

# OpenAI API key: Set this or use an environment variable for security.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# Default model names for OpenAI and Ollama
OPENAI_MODEL = "gpt-3.5-turbo"     # ChatGPT model to use via OpenAI API
OPENAI_TEMPERATURE: float = 0.7  # 0.0 = deterministisch, 1.0 = kreativ

# ---------------------------------------------------------------------------
# Ollama-Einstellungen  (nur relevant wenn USE_OLLAMA == True)
# ---------------------------------------------------------------------------
OLLAMA_MODEL = "llama3.2:3b"      # Local LLaMA model (via Ollama)
OLLAMA_HOST: str = "http://127.0.0.1:11434"   # URL des lokalen Ollama-Servers
OLLAMA_TEMPERATURE: float = 0.7               # Matching OpenAI-Temperature

# ---------------------------------------------------------------------------
# Weitere globale Konstanten (falls später benötigt)
# ---------------------------------------------------------------------------
# Beispiel: maximale Tokenzahl, Standard-Kalenderpfad, etc.
MAX_OUTPUT_TOKENS: int = 500
ICS_PATH: str = "data/Kalender.ics"
