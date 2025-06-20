import openai
import config
import os
import ollama
import streamlit as st

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

def ask_ollama(prompt: str, model: str = "llama3.2") -> str:
    """
    Sendet eine Anfrage an das lokal laufende Ollama-Modell und gibt die Antwort zurück.

    :param prompt: Die Eingabeaufforderung für das Modell.
    :param model: Der Name des zu verwendenden Modells.
    :return: Die Antwort des Modells als Zeichenkette.
    """
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content']
    except Exception as e:
        raise RuntimeError(f"Fehler bei der Anfrage an Ollama: {e}")
