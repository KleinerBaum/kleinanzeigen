import openai
import streamlit as st

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
