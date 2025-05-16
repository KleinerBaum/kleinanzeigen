from data.models import AdInfo
from logic.llm_client import ask_openai, ask_ollama
from logic.calendar import load_calendar_with_status, get_available_appointments

# ------------------------------------------------------------
# Beispielhafter Code, falls du hier etwas aus der alten
# "Verhandlungs-Logik" übernehmen willst.
# Momentan wird alles durch das LLM generiert,
# daher ist dieses Modul optional oder könnte entfernt werden.
# ------------------------------------------------------------

def generate_message(ad_info: AdInfo, text_options: list, chosen_model="openai"):
    """
    Beispiel: generiert eine Nachricht basierend auf AdInfo,
    einer Liste von ausgewählten Textoptionen und dem gewählten Modell.
    Hier könnte man das LLM ansprechen oder man behält eine
    Mini-Regel-Logik. Derzeit nicht aktiv genutzt in `app.py`.
    """
    # Placeholder
    prompt = f"Artikel: {ad_info.title} (Preis: {ad_info.price})\n"
    prompt += "Ausgewählte Optionen:\n" + ", ".join(text_options)

    if chosen_model.lower() == "openai":
        return ask_openai(prompt)
    else:
        return ask_ollama(prompt)
