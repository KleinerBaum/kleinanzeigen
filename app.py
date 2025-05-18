import streamlit as st
import config  # enthält OPENAI_API_KEY, OPENAI_MODEL, OLLAMA_MODEL, TIMEZONE
from logic.calendar import load_calendar_with_status, get_available_appointments
from logic.calendar import calendar_logic
from logic.parser import extract_data_from_url
from logic import llm_client
from logic import negotiation  # Import vorhanden (derzeit nicht für Textgenerierung genutzt)

# ----- Seiteneinstellungen -----
st.set_page_config(
    page_title="Kleinanzeigen Verhandlungs-Assistent",
    page_icon="",
    layout="centered"
)

st.title("Kleinanzeigen Verhandlungs-Assistent")
st.write(
    "Geben Sie die URL der Kleinanzeige ein, wählen Sie gewünschte Optionen "
    "und lassen Sie das LLM eine Nachricht formulieren."
)

# ----- Modellauswahl in der Sidebar -----
model_choice = st.sidebar.radio("Modell-Auswahl", ["OpenAI (ChatGPT API)", "Lokales LLM (Ollama)"])
use_openai = model_choice.startswith("OpenAI")
if not use_openai:
    st.sidebar.warning("Lokales Modell (Ollama) erfordert eine laufende Ollama-Installation (http://localhost:11434)")

# ----- Textbausteine: 15 vordefinierte Optionen -----
text_modules = [
    "Interesse bekunden",
    "Preisvorschlag machen",
    "Preis verhandelbar erfragen",
    "Nach Zustand fragen",
    "Verfügbarkeit prüfen",
    "Versand/Lieferung anfragen",
    "Garantie erfragen",
    "Abholungstermin vorschlagen",
    "Besichtigung erbitten",
    "Zubehör/Umfang erfragen",
    "Weitere Bilder anfragen",
    "Grund des Verkaufs erfragen",
    "Zahlungsmethode klären",
    "Reservierung erbitten",
    "Bundle-Angebot vorschlagen",
]
selected_modules = st.multiselect("Wähle gewünschte Textbausteine aus:", text_modules)

# Erläuterung für Auswahl der Optionen
st.write("Wähle die Optionen, die in deiner Nachricht berücksichtigt werden sollen:")

# Beispiel: Wenn "Preisvorschlag machen" ausgewählt ist, zusätzlichen Input anfordern 
offered_price = None
if "Preisvorschlag machen" in selected_modules:
    offered_price = st.number_input("Ihr Preisvorschlag (EUR)", min_value=1, step=1)

# ----- Inputs zum Artikel (Kleinanzeigen-URL) -----
ad_url = st.text_input("Kleinanzeigen-URL", placeholder="https://www.kleinanzeigen.de/s-anzeige/beispiel...")

# Kalender laden und verfügbare Termine anzeigen (falls Kalender vorhanden)
calendar_obj, calendar_status = calendar_logic.load_calendar_with_status()
appointments = calendar_logic.get_available_appointments(calendar_obj, timezone_str=config.TIMEZONE)
selected_slots = []
if appointments:
    selected_slots = st.multiselect("Verfügbare Termine auswählen (Abholung/Besichtigung):", appointments)
else:
    # Hinweis, falls Kalender geladen wurde, aber keine Termine vorhanden sind
    if calendar_obj is not None:
        st.info("Kalender geladen, aber keine Termine gefunden.")

# Zusätzliche Hinweise, falls beim Laden des Kalenders Fehler auftraten
if calendar_status == "not_found":
    st.warning("Kalenderdatei nicht gefunden.")
elif calendar_status == "empty_file":
    st.info("Kalenderdatei ist leer.")
elif calendar_status == "parse_error":
    st.error("Kalender konnte nicht geladen werden (Formatfehler).")

# ----- Button: Nachricht generieren -----
if st.button("Nachricht generieren"):
    if not ad_url:
        st.error("Bitte geben Sie eine URL zur Kleinanzeige ein.")
        st.stop()

    # Kleinanzeigen-Daten abrufen & parsen
    try:
        ad_data = extract_data_from_url(ad_url)
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Kleinanzeige: {e}")
        st.stop()

    if not ad_data:
        st.warning("Konnte keine Daten aus der Anzeige extrahieren.")
        st.stop()

    # Titel, Preis, Beschreibung extrahieren
    # (Wenn parse_ad ein AdInfo-Objekt liefert, Attribute nutzen; ansonsten Dictionary)
    if hasattr(ad_data, "title"):
        ad_title = ad_data.title or ""
        ad_price = ad_data.price or ""
        ad_desc = getattr(ad_data, "description", "") or ""
    else:
        ad_title = ad_data.get("title", "")
        ad_price = ad_data.get("price", "")
        ad_desc = ad_data.get("description", "")

    # Prompt erstellen
    prompt_parts = []
    if ad_title:
        prompt_parts.append(f"**Angebotstitel:** {ad_title}")
    if ad_desc:
        prompt_parts.append(f"**Angebotsbeschreibung:** {ad_desc}")
    if ad_price:
        prompt_parts.append(f"**Angebotspreis laut Anzeige:** {ad_price}")

    # Ausgewählte Textbausteine in den Prompt integrieren
    if "Interesse bekunden" in selected_modules:
        prompt_parts.append("Du willst dein Interesse am Artikel bekunden.")
    if "Preisvorschlag machen" in selected_modules and offered_price:
        prompt_parts.append(f"Du möchtest einen Preisvorschlag von {int(offered_price)} Euro unterbreiten.")
    if "Preis verhandelbar erfragen" in selected_modules:
        prompt_parts.append("Du fragst, ob der Preis noch verhandelbar ist.")
    if "Nach Zustand fragen" in selected_modules:
        prompt_parts.append("Du möchtest mehr über den Zustand des Artikels erfahren.")
    if "Verfügbarkeit prüfen" in selected_modules:
        prompt_parts.append("Du fragst, ob der Artikel noch verfügbar ist.")
    if "Versand/Lieferung anfragen" in selected_modules:
        prompt_parts.append("Du fragst, ob Versand oder Lieferung möglich ist.")
    if "Garantie erfragen" in selected_modules:
        prompt_parts.append("Du fragst nach eventuell bestehender Garantie.")
    if "Abholungstermin vorschlagen" in selected_modules and selected_slots:
        prompt_parts.append(f"Du möchtest an folgenden Terminen abholen: {', '.join(selected_slots)}.")
    if "Besichtigung erbitten" in selected_modules:
        prompt_parts.append("Du möchtest den Artikel vor dem Kauf besichtigen.")
    if "Zubehör/Umfang erfragen" in selected_modules:
        prompt_parts.append("Du fragst, ob sämtliches Zubehör (z.B. Kabel, Verpackung) dabei ist.")
    if "Weitere Bilder anfragen" in selected_modules:
        prompt_parts.append("Du möchtest weitere Bilder vom Artikel sehen.")
    if "Grund des Verkaufs erfragen" in selected_modules:
        prompt_parts.append("Du erkundigst dich nach dem Grund des Verkaufs.")
    if "Zahlungsmethode klären" in selected_modules:
        prompt_parts.append("Du möchtest wissen, welche Zahlungsmethode bevorzugt wird.")
    if "Reservierung erbitten" in selected_modules:
        prompt_parts.append("Du fragst, ob der Artikel bis zu einem bestimmten Datum reserviert werden kann.")
    if "Bundle-Angebot vorschlagen" in selected_modules:
        prompt_parts.append("Du fragst, ob es einen Rabatt gibt, falls du mehrere Artikel kaufst.")

    # Finale Bitte an das LLM (Abschluss des Prompts)
    prompt_parts.append(
        "Bitte schreibe eine freundliche, höfliche Nachricht auf Deutsch an den Anbieter, "
        "in der alle oben genannten Punkte eingebunden werden."
    )
    final_prompt = "\n".join(prompt_parts)

    # Zeige den zusammengestellten Prompt (Debug/Info)
    st.write("**Gesammelter Prompt:**")
    st.code(final_prompt, language="markdown")

    # LLM aufrufen 
    if use_openai:
        # OpenAI API über llm_client aufrufen
        try:
            generated_text = llm_client.ask_openai(final_prompt, model=config.OPENAI_MODEL)
            st.subheader("Generierte Nachricht (OpenAI):")
            st.write(generated_text)
        except Exception as e:
            st.error(f"Fehler bei der OpenAI-Anfrage: {e}")
    else:
        # Lokales LLM (Ollama) aufrufen
        try:
            generated_text = llm_client.ask_ollama(final_prompt, model=config.OLLAMA_MODEL)
            st.subheader("Generierte Nachricht (Lokales LLM):")
            st.write(generated_text)
        except Exception as e:
            # Fallback auf OpenAI, falls das lokale Modell nicht verfügbar ist
            st.warning(f"Lokales Modell nicht verfügbar. Fallback auf OpenAI: {e}")
            if not config.OPENAI_API_KEY:
                st.error("OpenAI API-Key ist nicht gesetzt. Generierung nicht möglich.")
            else:
                try:
                    generated_text = llm_client.ask_openai(final_prompt, model=config.OPENAI_MODEL)
                    st.subheader("Generierte Nachricht (Fallback OpenAI):")
                    st.write(generated_text)
                except Exception as e2:
                    st.error(f"Fehler bei der OpenAI-Anfrage (Fallback): {e2}")
