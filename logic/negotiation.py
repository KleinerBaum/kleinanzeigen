# Optionales Verhandlungs-Modul (derzeit nicht direkt in Benutzung, da LLM die Nachricht generiert)

from logic import llm_client
from data.models import AdInfo

def generate_message(ad_info: AdInfo, text_options: list, chosen_model="openai") -> str:
    """
    Beispiel: generiert eine Nachricht basierend auf AdInfo,
    einer Liste von ausgewählten Textoptionen und dem gewählten Modell.
    Hier könnte man das LLM ansprechen oder eine regelbasierte Logik implementieren.
    (Derzeit als Platzhalter.)
    """
    # Prompt aus AdInfo und Optionen zusammenbauen (nur Platzhalter-Implementierung)
    prompt = f"Artikel: {ad_info.title} (Preis: {ad_info.price})\n"
    prompt += "Ausgewählte Optionen:\n" + ", ".join(text_options)
    # LLM je nach Modelltyp ansprechen
    if chosen_model.lower() == "openai":
        try:
            return llm_client.ask_openai(prompt)
        except Exception as e:
            raise
    else:
        try:
            return llm_client.ask_ollama(prompt)
        except Exception as e:
            raise
