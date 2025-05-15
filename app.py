import streamlit as st
from config import OPENAI_API_KEY, OPENAI_MODEL, OLLAMA_MODEL, TIMEZONE
from logic import calendar as calendar_logic
import parser  # module for parsing the advertisement
import llm_client  # module for LLM interactions (OpenAI API or Ollama)
import negotiation  # negotiation module (no rule-based text generation, handled by LLM)

# Set Streamlit page configuration
st.set_page_config(page_title="LLM Kleinanzeigen Assistent", page_icon="💬", layout="centered")

st.title("Kleinanzeigen Verhandlungs-Assistent")
st.write("Geben Sie die URL der Kleinanzeige ein, wählen Sie gewünschte Optionen und lassen Sie das LLM eine Nachricht formulieren.")

# Sidebar model selection
model_choice = st.sidebar.radio("Modell-Auswahl", ["OpenAI (ChatGPT API)", "Lokales LLM (Ollama)"])
use_openai = model_choice.startswith("OpenAI")

# API Key check (if OpenAI selected)
if use_openai and not OPENAI_API_KEY:
    st.sidebar.error("⚠️ Kein OpenAI API-Key gefunden. Bitte API-Key in der .env-Datei oder den Streamlit Secrets hinterlegen.")

# Input fields for the main form
ad_url = st.text_input("Kleinanzeigen-URL", placeholder="https://www.kleinanzeigen.de/s-anzeige/beispiel...")
include_interest = st.checkbox("Interesse bekunden", value=True)
include_price = st.checkbox("Preisvorschlag machen")
offered_price = None
if include_price:
    offered_price = st.number_input("Ihr Preisvorschlag (€)", min_value=1, step=1)
include_condition = st.checkbox("Nach Zustand fragen")

# Load available appointment slots from calendar (ICS)
calendar_obj = calendar_logic.load_calendar()
if calendar_obj:
    available_slots = calendar_logic.get_available_appointments(calendar_obj, timezone_str=TIMEZONE)
else:
    available_slots = []
if available_slots:
    selected_slots = st.multiselect("Verfügbare Termine auswählen", available_slots)
else:
    # Show a message if no times are available or calendar couldn't be loaded
    st.info("ℹ️ Keine verfügbaren Termine gefunden oder Kalender nicht geladen.")
    selected_slots = []

# Button to generate the message
if st.button("Nachricht generieren"):
    # Basic validation for URL
    if not ad_url:
        st.warning("Bitte geben Sie eine URL der Kleinanzeige ein.")
        st.stop()
    # Parse the advertisement details from the URL
    try:
        ad_data = parser.parse_ad(ad_url)
    except Exception as e:
        st.error(f"Konnte die Anzeige nicht abrufen: {e}")
        st.stop()
    if not ad_data:
        st.error("Es konnten keine Daten aus der Kleinanzeige gelesen werden. Bitte prüfen Sie die URL.")
        st.stop()
    # Extract relevant details from ad_data
    ad_title = ""
    ad_price = ""
    ad_description = ""
    if isinstance(ad_data, dict):
        ad_title = ad_data.get("title", "") or ad_data.get("headline", "")
        ad_price = ad_data.get("price", "")
        ad_description = ad_data.get("description", "") or ad_data.get("desc", "")
    elif isinstance(ad_data, str):
        # If parser returns raw text (description), use it as description
        ad_description = ad_data
    else:
        # If ad_data is an object with attributes
        ad_title = getattr(ad_data, "title", "") or getattr(ad_data, "headline", "") or ""
        ad_price = getattr(ad_data, "price", "") or ""
        ad_description = getattr(ad_data, "description", "") or getattr(ad_data, "desc", "") or ""
    # Construct prompt for the LLM
    prompt_parts = []
    if ad_title:
        prompt_parts.append(f"Die Kleinanzeige hat den Titel: \"{ad_title}\".")
    if ad_description:
        prompt_parts.append(f"Beschreibung: {ad_description}")
    if ad_price:
        prompt_parts.append(f"Der Preis in der Anzeige beträgt {ad_price}.")
    # Add user intentions based on selections
    if include_interest:
        prompt_parts.append("Der Nutzer ist an dem Artikel interessiert.")
    if include_price and offered_price and offered_price > 0:
        prompt_parts.append(f"Er möchte einen Preis von {int(offered_price)} Euro vorschlagen.")
    if include_condition:
        prompt_parts.append("Er möchte nach dem Zustand des Artikels fragen.")
    if selected_slots:
        if len(selected_slots) == 1:
            prompt_parts.append(f"Der Nutzer ist am {selected_slots[0]} verfügbar.")
        else:
            slots_text = "; ".join(selected_slots)
            prompt_parts.append(f"Der Nutzer ist zu folgenden Zeiten verfügbar: {slots_text}.")
    # Final instruction for message generation
    prompt_parts.append("Bitte formulieren Sie eine freundliche und höfliche Nachricht auf Deutsch an den Anbieter, die alle diese Punkte berücksichtigt.")
    # Combine prompt parts into one prompt string
    prompt_text = " \n".join(prompt_parts)
    # Generate message using the selected model
    generated_message = None
    if use_openai:
        # Ensure API key is set
        if not OPENAI_API_KEY:
            st.error("OpenAI API-Key ist nicht gesetzt. Generierung nicht möglich.")
        else:
            try:
                # Use ChatGPT via OpenAI API
                # Assuming llm_client has a function to call OpenAI ChatCompletion
                generated_message = llm_client.ask_openai(prompt_text, model=OPENAI_MODEL)
            except Exception as e:
                st.error(f"Fehler bei der OpenAI API-Anfrage: {e}")
    else:
        # Use local LLM via Ollama
        try:
            generated_message = llm_client.ask_ollama(prompt_text, model=OLLAMA_MODEL)
        except Exception as e:
            # Fallback to OpenAI if local model is not available
            st.info("⚠️ Lokales Modell nicht verfügbar. Es wird stattdessen OpenAI genutzt.")
            if not OPENAI_API_KEY:
                st.error("OpenAI API-Key ist nicht gesetzt. Generierung nicht möglich.")
            else:
                try:
                    generated_message = llm_client.ask_openai(prompt_text, model=OPENAI_MODEL)
                except Exception as e2:
                    st.error(f"Fehler bei der OpenAI API-Anfrage: {e2}")
    # Display the generated message
    if generated_message:
        st.subheader("Generierte Nachricht:")
        st.write(generated_message)
