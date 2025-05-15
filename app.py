import os
import streamlit as st

# Import configuration and logic modules
import config
from logic import calendar, llm_client, negotiation, parser

st.set_page_config(page_title="Kleinanzeigen Assistant", layout="wide")

# Sidebar: Model selection
st.sidebar.title("LLM-Auswahl")
# Determine available options: Only show local model option if Ollama is installed
model_options = ["OpenAI API"]
if llm_client.ollama_available():  # check if Ollama binary is in PATH:contentReference[oaicite:0]{index=0}
    model_options.append("Lokales LLaMA (Ollama)")
model_choice = st.sidebar.radio("Wähle das Sprachmodell:", model_options)

# Handle model selection fallback: if user chose local but it's not actually available
use_openai = True
if model_choice == "Lokales LLaMA (Ollama)":
    if not llm_client.ollama_available():
        st.sidebar.error("Lokales Modell nicht verfügbar – es wird OpenAI genutzt.")
    else:
        use_openai = False

# OpenAI API key handling
openai_api_key = config.OPENAI_API_KEY or None
# Also check Streamlit secrets (useful on Streamlit Cloud)
if not openai_api_key:
    try:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        openai_api_key = None

if use_openai:
    if not openai_api_key:
        # Prompt user for API key if not provided in config or secrets
        openai_api_key_input = st.sidebar.text_input("OpenAI API Key eingeben:", type="password")
        if openai_api_key_input:
            # Save key to session state for reuse
            st.session_state["OPENAI_API_KEY"] = openai_api_key_input
            openai_api_key = openai_api_key_input
    else:
        # If key exists, store in session for consistency
        st.session_state["OPENAI_API_KEY"] = openai_api_key

# Main interface with tabs for different functionalities
st.title("🤖 Kleinanzeigen Assistant")
tabs = st.tabs(["🏨 Hotelsuche", "🤝 Verhandlung", "📅 Kalender"])
tab_hotels, tab_negotiation, tab_calendar = tabs

# Tab 1: Hotelsuche (Hotel search via LLM-based "web" search)
with tab_hotels:
    st.header("Hotelsuche")
    st.write("Geben Sie einen Ort oder eine Suche ein, um Hotels zu finden:")
    query = st.text_input("Suche nach Hotels in ...")  # user query input
    search_btn = st.button("Hotels suchen")
    if search_btn:
        if query.strip() == "":
            st.warning("Bitte geben Sie einen Ort oder Suchbegriff ein.")
        else:
            # Determine which provider to use for LLM (OpenAI or Ollama)
            provider = "openai" if use_openai else "ollama"
            # If using OpenAI, ensure we have an API key
            if provider == "openai" and not openai_api_key:
                st.error("OpenAI API Key fehlt. Bitte Key eingeben oder lokales Modell wählen.")
            else:
                # Perform the LLM-based hotel search
                with st.spinner("Suche nach Hotels..."):
                    try:
                        # Use parser to preprocess query if needed (currently just returns the same query)
                        search_query = parser.parse_search_input(query)
                        result = llm_client.generate_response(
                            f"Liste mir einige empfehlenswerte Hotels in {search_query} mit einer kurzen Beschreibung.", 
                            provider=provider, 
                            openai_api_key=openai_api_key
                        )
                        # Display the LLM result (which may contain a list of hotels)
                        st.markdown(result)
                    except Exception as e:
                        # Handle errors (e.g., no internet, API failure) with placeholder output
                        st.warning("Hotelsuche fehlgeschlagen – zeige Platzhalter-Ergebnisse.")
                        placeholder_result = "- **Hotel Adler** – Beispielhotel in " + (query or "der Stadt") + "\n"
                        placeholder_result += "- **Hotel Beispiel** – Ein weiteres empfohlenes Hotel\n"
                        st.markdown(placeholder_result)

# Tab 2: Verhandlung (Negotiation helper)
with tab_negotiation:
    st.header("Verhandlung")
    st.write("Geben Sie Ihren Preisrahmen ein, um eine Verhandlungs-Nachricht zu generieren:")
    col1, col2 = st.columns(2)
    with col1:
        min_price = st.number_input("Min. Preis (EUR)", min_value=0, value=0, step=1)
    with col2:
        max_price = st.number_input("Max. Preis (EUR)", min_value=0, value=0, step=1)
    generate_btn = st.button("Nachricht generieren")
    if generate_btn:
        if min_price == 0 and max_price == 0:
            st.info("Bitte geben Sie einen gültigen Preisrahmen an.")
        elif min_price > max_price:
            st.error("Der minimale Preis darf nicht höher als der maximale sein.")
        else:
            try:
                message = negotiation.generate_message(int(min_price), int(max_price))
                st.success("Generierte Verhandlungs-Nachricht:")
                st.write(message)
            except Exception as e:
                st.error(f"Fehler bei der Generierung der Nachricht: {e}")

# Tab 3: Kalender (Calendar display)
with tab_calendar:
    st.header("Kalender")
    try:
        calendar_content = calendar.load_calendar("data/Kalender.ics")
        st.text(calendar_content)  # Display raw ICS content for now
        st.caption("Kalenderdaten (ICS-Datei) – derzeit unformatiert angezeigt.")
    except Exception as e:
        st.error(f"Kalender konnte nicht geladen werden: {e}")
