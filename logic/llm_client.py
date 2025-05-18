import openai
import config
import os

openai.api_key = st.secrets.get("openai_api_key", None) or os.getenv("openai_api_key")
if not openai.api_key:
    raise RuntimeError(
        "OpenAI-Modus aktiv, aber kein API-Key gefunden. "
        "Bitte in `.streamlit/secrets.toml` oder als ENV `openai_api_key` setzen "
        "oder `USE_OLLAMA=True` in config.py wählen."
    )
    
def ask_openai(prompt: str, model: str = None) -> str:
    """
    Fragt das OpenAI-Modell (ChatCompletion) mit dem gegebenen Prompt an.
    Nutzt `config.openai_api_key` sowie das Modell aus `config.OPENAI_MODEL` (falls kein anderes angegeben).
    """
    if not config.openai_api_key:
        raise ValueError("openai_api_key ist nicht gesetzt.")
    openai.api_key = config.openai_api_key
    chosen_model = model or config.OPENAI_MODEL
    try:
        response = openai.ChatCompletion.create(
            model=chosen_model,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        # Fehler bei API-Anfrage weitergeben
        raise
    return response.choices[0].message.content.strip()

def ask_ollama(prompt: str, model: str = None) -> str:
    """
    Fragt das lokale LLM (Ollama) an (OpenAI-kompatibles API-Format).
    Setzt die OpenAI-API Base URL auf http://127.0.0.1:11434/v1.
    """
    openai.api_base = "http://127.0.0.1:11434/v1"
   # openai.api_key = "none"  # Dummy-Key, da Ollama keine Auth verwendet
    chosen_model = model or config.OLLAMA_MODEL
    try:
        response = openai.ChatCompletion.create(
            model=chosen_model,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        # Fehler bei lokaler LLM-Anfrage weitergeben
        raise
    return response.choices[0].message.content.strip()
