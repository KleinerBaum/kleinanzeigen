import streamlit as st
from logic import parser, negotiation, calendar
from logic.llm_client import LLMClient
from data.models import AdInfo

st.set_page_config(page_title="Kleinanzeigen-Assistent", page_icon="💬", layout="centered")
st.title("📝 Kleinanzeigen Kommunikationsassistent")
st.markdown(
    "Dieses Tool hilft dabei, automatisch eine Nachricht für eine Kleinanzeige zu formulieren. "
    "Gib eine Anzeigen-URL oder den Anzeigentext ein, wähle deine Vorgaben, und lass eine Nachricht erstellen."
)

# Session State initialisieren für Anzeigeninformationen
if "ad_info" not in st.session_state:
    st.session_state.ad_info = None

# **1. Anzeige eingeben**
st.header("1. Anzeige eingeben")
url_input = st.text_input("URL der Kleinanzeige", placeholder="https://www.kleinanzeigen.de/s-anzeige/...")
text_input = st.text_area("Oder Anzeigentext eingeben", placeholder="Anzeigentitel, Preis, Ort, Beschreibung...")

# Button zur Analyse der Anzeige
if st.button("Anzeige analysieren"):
    try:
        if url_input:
            ad_info = parser.parse_from_url(url_input.strip())
        elif text_input:
            ad_info = parser.parse_from_text(text_input.strip())
        else:
            ad_info = None
            st.warning("Bitte gib entweder eine URL oder einen Anzeigentext ein.")
        st.session_state.ad_info = ad_info  # Speichere Ergebnis im Session State
        if ad_info:
            st.success("Anzeigeninformationen erfolgreich extrahiert.")
        else:
            st.error("Konnte keine Informationen extrahieren. Bitte Eingabe prüfen.")
    except Exception as e:
        st.session_state.ad_info = None
        st.error(f"Fehler bei der Analyse: {e}")

# Extrahierte Anzeigeninformationen anzeigen (falls vorhanden)
if st.session_state.ad_info:
    ad_info = st.session_state.ad_info
    st.subheader("Extrahierte Informationen")
    st.write(f"**Titel:** {ad_info.title}")
    st.write(f"**Preis:** {ad_info.price}")
    st.write(f"**Ort:** {ad_info.location}")
    if ad_info.description:
        st.write(f"**Beschreibung:** {ad_info.description[:200]}{'...' if len(ad_info.description) > 200 else ''}")

# **2. Nachricht anpassen** (nur wenn ad_info vorhanden ist)
if st.session_state.ad_info:
    ad_info = st.session_state.ad_info
    st.header("2. Nachricht anpassen")
    # Mehrfachauswahl für den Zweck der Nachricht
    purpose_options = ["Interesse bekunden (Verfügbarkeit)", "Preis verhandeln", "Abholungstermin vorschlagen"]
    purposes = st.multiselect("Nachrichtenzweck (mehrfach wählbar)", purpose_options, default=[purpose_options[0]])
    # Optionaler Preisvorschlag
    price_offer_val = st.number_input("Preisvorschlag (optional)", min_value=0, max_value=1000000, value=0, step=1)
    price_offer = float(price_offer_val) if price_offer_val and price_offer_val != 0 else None
    # Tonfall der Nachricht
    tone = st.selectbox("Tonfall der Nachricht", ["Freundlich", "Förmlich"], index=0)
    # Absender-Name
    name = st.text_input("Dein Name (optional)", placeholder="Max Mustermann")
    # Modellwahl für OpenAI API
    model_choice = st.selectbox("Sprachmodell", ["GPT-4", "GPT-3.5"], index=0)
    model_name = "gpt-4" if model_choice == "GPT-4" else "gpt-3.5-turbo"
    # Button zur Generierung der Nachricht
    if st.button("Nachricht generieren"):
        # Falls Terminwunsch ausgewählt, freie Kalender-Slots finden
        free_slots = []
        if any("Termin" in p or "Abholung" in p for p in purposes):
            try:
                free_slots = calendar.find_free_slots()
            except Exception as e:
                st.warning(f"Kalender konnte nicht geprüft werden: {e}")
        # Prompts für das Sprachmodell aufbauen
        system_prompt, user_prompt = negotiation.build_prompts(ad_info, purposes, tone, price_offer=price_offer, name=name, free_slots=free_slots)
        # Nachricht via OpenAI generieren
        try:
            llm = LLMClient(model=model_name)
            with st.spinner("Generiere Nachricht..."):
                result_message = llm.generate_message(system_prompt, user_prompt)
            st.subheader("3. Generierte Nachricht")
            st.code(result_message, language="text")
        except Exception as e:
            st.error(str(e))
