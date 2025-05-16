import requests
import config

def ollama_available() -> bool:
    """
    Prüft, ob Ollama (lokales LLM) installiert und erreichbar ist.
    Einfacher Test: Versuche eine GET-Anfrage an localhost:11434
    """
    try:
        resp = requests.get("http://localhost:11434/version", timeout=1)
        return resp.status_code == 200
    except:
        return False

def ask_openai(prompt: str, model: str = None) -> str:
    """
    Fragt das OpenAI-Modell über ChatCompletion an.
    Nutzt config.OPENAI_API_KEY und optional config.OPENAI_MODEL, falls model=None.
    """
    import openai
    if not config.OPENAI_API_KEY:
        raise ValueError("OpenAI API-Key ist nicht gesetzt.")
    openai.api_key = config.OPENAI_API_KEY
    chosen_model = model or config.OPENAI_MODEL

    response = openai.ChatCompletion.create(
        model=chosen_model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def ask_ollama(prompt: str, model: str = None) -> str:
    """
    Fragt das lokale LLM (Ollama) an (OpenAI-kompatibles Interface).
    Wir setzen openai.api_base auf http://localhost:11434/v1.
    """
    import openai
    openai.api_base = "http://localhost:11434/v1"
    openai.api_key = "unused"  # Dient nur als Platzhalter

    chosen_model = model or config.OLLAMA_MODEL
    # Da Ollama ab ChatCompletion v1 Schnittstelle (kompatibel) kann, tun wir Folgendes:
    response = openai.ChatCompletion.create(
        model=chosen_model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()
