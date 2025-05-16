import openai
import config

def ask_openai(prompt: str, model: str = None) -> str:
    """
    Fragt das OpenAI-Modell (ChatCompletion) mit dem gegebenen Prompt an.
    Nutzt `config.OPENAI_API_KEY` sowie das Modell aus `config.OPENAI_MODEL` (falls kein anderes angegeben).
    """
    if not config.OPENAI_API_KEY:
        raise ValueError("OpenAI API-Key ist nicht gesetzt.")
    openai.api_key = config.OPENAI_API_KEY
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
    openai.api_key = "none"  # Dummy-Key, da Ollama keine Auth verwendet
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
