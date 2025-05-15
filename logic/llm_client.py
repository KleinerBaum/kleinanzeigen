import openai
import streamlit as st
import shutil
import config


def ollama_available() -> bool:
    """
    Check if Ollama (for local LLaMA) is installed by looking for the 'ollama' executable.
    Returns True if available, False otherwise.
    """
    return shutil.which("ollama") is not None  # Path to 'ollama' exists if installed:contentReference[oaicite:3]{index=3}

def generate_response(prompt: str, provider: str = "openai", openai_api_key: str = None) -> str:
    """
    Generate a response from the specified language model provider using the given prompt.
    provider: "openai" for OpenAI API, "ollama" for local LLaMA via Ollama.
    openai_api_key: Required if using OpenAI provider (ignored for ollama).
    Returns the generated response text.
    """
    # Use OpenAI's Python SDK for both providers (Ollama supports OpenAI API format:contentReference[oaicite:4]{index=4}).
    try:
        import openai
    except ImportError as e:
        raise ImportError("OpenAI Python library is not installed. Please install 'openai' to use LLM features.") from e

    if provider == "openai":
        # Ensure the OpenAI API key is set
        openai.api_base = "https://api.openai.com/v1"
        openai.api_key = openai_api_key or ""
        if openai.api_key == "":
            raise ValueError("OpenAI API key is not provided.")
        model_name = config.OPENAI_MODEL
        # Call OpenAI ChatCompletion API
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        # Return the assistant's reply text
        return response.choices[0].message.content.strip()

    elif provider == "ollama":
        # Use Ollama's local API (OpenAI-compatible):contentReference[oaicite:5]{index=5}
        openai.api_base = "http://localhost:11434/v1"
        openai.api_key = "unused-api-key"  # Ollama doesn't require a real key, but SDK needs one
        model_name = config.OLLAMA_MODEL
        # Call the local model via Ollama's API
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    else:
        raise ValueError(f"Unknown provider: {provider}")
    
class LLMClient:
    """Client für die Kommunikation mit der OpenAI Chat API."""
    def __init__(self, model: str = "gpt-4"):
        # OpenAI API-Key aus den Secrets laden
        openai.api_key = st.secrets.get("openai_api_key", None) or os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            raise RuntimeError(
                "OpenAI-Modus aktiv, aber kein API-Key gefunden. "
                "Bitte in `.streamlit/secrets.toml` oder als ENV `OPENAI_API_KEY` setzen "
                "oder `USE_OLLAMA=True` in config.py wählen."
            )
        self.model = model
    
    def generate_message(self, system_prompt: str, user_prompt: str) -> str:
        """Generiert eine Nachricht basierend auf den Prompts mittels OpenAI ChatCompletion API."""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
        except Exception as e:
            raise Exception(f"Fehler bei der Anfrage an das Sprachmodell: {e}")
        # Antworttext extrahieren und zurückgeben
        message = response["choices"][0]["message"]["content"]
        return message.strip()
