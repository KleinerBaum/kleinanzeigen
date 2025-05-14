import streamlit as st
from utils import extract_info_from_url, analyze_manual_text, parse_ics_highlight, get_free_busy_times, add_calendar_events, find_hotels_near
from negotiation_agent import generate_message
import openai

# Streamlit Seiten-Konfiguration
st.set_page_config(page_title="Kleinanzeigen Kontakt-Assistent", layout="centered")

# Session State Initialisierung
if "model_choice" not in st.session_state:
    st.session_state.model_choice = "gpt-3.5-turbo"
if "language" not in st.session_state:
    st.session_state.language = "Deutsch"
if "fun_level" not in st.session_state:
    st.session_state.fun_level = 0
if "calendar_credentials" not in st.session_state:
    st.session_state.calendar_credentials = None
if "selected_times" not in st.session_state:
    st.session_state.selected_times = []

# OpenAI API-Key aus Secrets laden (muss in secrets.toml gesetzt sein)
if "OPENAI_API_KEY" in st.secrets:
    openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("💬 Kleinanzeigen Kontakt-Assistent")
st.markdown("Dieses Tool hilft dabei, eine Nachricht für einen Kleinanzeigen-Kontakt zu erstellen – inklusive Terminabsprachen und optionaler Hotelsuche.")

# Auswahl des Sprachmodells (GPT-3.5 oder GPT-4)
model = st.selectbox("KI-Modell für Textgenerierung:", ["gpt-3.5-turbo", "gpt-4"], index=0)
st.session_state.model_choice = model

# Auswahl der Nachrichtensprache
language = st.radio("Sprache der Nachricht:", ["Deutsch", "English"], index=0)
st.session_state.language = language

# Eingabemethode für die Anzeigendaten (URL oder manueller Text)
input_method = st.radio("Anzeigendaten eingeben per:", ["URL analysieren", "Text einfügen"], index=0)
extracted_info = {}
if input_method == "URL analysieren":
    url = st.text_input("Kleinanzeigen-URL:", placeholder="https://www.kleinanzeigen.de/...")
    if st.button("Anzeige analysieren"):
        try:
            with st.spinner("Analysiere die Anzeige..."):
                extracted_info = extract_info_from_url(url)
            st.success("Anzeige erfolgreich analysiert!")
            st.json(extracted_info)  # Zeige extrahierte Infos an
        except Exception as e:
            st.error(f"Fehler bei der Analyse: {e}")
elif input_method == "Text einfügen":
    manual_text = st.text_area("Anzeigentext hier einfügen:")
    if manual_text and st.button("Text analysieren"):
        extracted_info = analyze_manual_text(manual_text)
        st.success("Text erfolgreich analysiert!")
        st.json(extracted_info)

# Wenn Anzeigendaten extrahiert wurden, nächste Schritte anzeigen
if extracted_info:
    # Optional: ICS-Datei mit Reiseplan hochladen zur Hervorhebung bestimmter Tage
    ics_file = st.file_uploader("Reiseplan als ICS-Datei hochladen (optional):", type="ics")
    highlight_dates = []
    if ics_file is not None:
        try:
            ics_content = ics_file.read().decode('utf-8', errors='ignore')
            # Aus ICS die Tage ermitteln, an denen man in der Nähe des Anzeigeortes ist
            highlight_dates = parse_ics_highlight(ics_content, extracted_info.get("location", ""))
            if highlight_dates:
                st.info(f"Tage, an denen Sie sich in der Nähe von **{extracted_info.get('location')}** befinden: " +
                        ", ".join([d.strftime('%Y-%m-%d') for d in highlight_dates]))
            else:
                st.info("Keine besonderen Reisetage für den Anzeigenort im Kalender gefunden.")
        except Exception as e:
            st.error(f"ICS-Datei konnte nicht verarbeitet werden: {e}")
    # Schritt 2: Textbausteine auswählen
    st.subheader("Schritt 2: Textbausteine auswählen")
    # Lade Textbaustein-Vorlagen je nach Sprache
    templates_file = "text_templates.json" if st.session_state.language == "Deutsch" else "text_templates_en.json"
    try:
        import json
        with open(templates_file, "r", encoding="utf-8") as f:
            templates_data = json.load(f)
    except FileNotFoundError:
        st.error("Textbaustein-Datei nicht gefunden.")
        templates_data = {}
    template_options = list(templates_data.keys())
    # Voreinstellung: beim ersten Kontakt einen Begrüßungsbaustein standardmäßig auswählen
    default_selection = []
    if st.session_state.language == "Deutsch":
        if "Erstkontakt" in template_options:
            default_selection.append("Erstkontakt")
    else:
        if "Initial Contact" in template_options:
            default_selection.append("Initial Contact")
    selected_options = st.multiselect("Textbausteine für die Nachricht:", options=template_options, default=default_selection)
    # Wenn Terminvereinbarung ausgewählt wurde, Kalenderintegration anzeigen
    if any(opt.lower().startswith("termin") or opt.lower().startswith("appointment") for opt in selected_options):
        st.subheader("📅 Terminvereinbarung")
        # Google-Kalender Login (OAuth) wenn noch nicht erfolgt
        if st.session_state.calendar_credentials is None:
            if st.button("Mit Google Kalender anmelden"):
                # Starte OAuth2 Flow für Google (Client-ID/-Secret aus secrets.toml)
                try:
                    from google_auth_oauthlib import get_user_credentials
                    creds = get_user_credentials(
                        client_id=st.secrets["client_id"],
                        client_secret=st.secrets["client_secret"],
                        scopes=["https://www.googleapis.com/auth/calendar.events"],
                        minimum_port=9000,
                        maximum_port=9001
                    )
                    st.session_state.calendar_credentials = creds
                    st.success("Google-Kalender erfolgreich verbunden!")
                except Exception as e:
                    st.error(f"Kalender-Login fehlgeschlagen: {e}")
        # Wenn eingeloggt, verfügbare freie Zeiten abrufen und Auswahl ermöglichen
        if st.session_state.calendar_credentials:
            free_options = get_free_busy_times(st.session_state.calendar_credentials, highlight_dates=highlight_dates)
            if free_options:
                slot_str_mapping = {slot['display']: slot for slot in free_options}
                choices = list(slot_str_mapping.keys())
                selected_times_display = st.multiselect("Verfügbare Zeitvorschläge wählen (mehrere möglich):", choices)
                # Speichere ausgewählte Zeiten (datetime-Objekte) in Session State
                st.session_state.selected_times = [slot_str_mapping[s]["start"] for s in selected_times_display]
            else:
                st.error("Keine freien Termine in Ihrem Kalender gefunden.")
    # Schieberegler für Humorstil
    fun_level = st.slider("Humor-Stil der Nachricht:", min_value=0, max_value=100, value=st.session_state.fun_level, help="0 = sehr förmlich, 100 = sehr humorvoll")
    st.session_state.fun_level = fun_level
    # Button zur Generierung der Nachricht mit KI
    if st.button("🤖 Nachricht generieren"):
        if not selected_options:
            st.warning("Bitte wählen Sie mindestens einen Textbaustein aus.")
        else:
            with st.spinner("Generiere Nachricht mit KI..."):
                try:
                    message = generate_message(extracted_info, selected_options, st.session_state.selected_times, language=st.session_state.language, fun_level=st.session_state.fun_level, model=st.session_state.model_choice)
                except Exception as e:
                    st.error(f"Fehler bei der Nachrichtenerzeugung: {e}")
                    message = ""
            if message:
                st.subheader("Generierte Nachricht:")
                st.text_area("", value=message, height=300)
                # Automatisch ausgewählte Termine zum Kalender hinzufügen
                if st.session_state.calendar_credentials and st.session_state.selected_times:
                    try:
                        add_calendar_events(st.session_state.calendar_credentials, st.session_state.selected_times, extracted_info)
                        st.success("Vorgeschlagene Termine im Google Kalender eingetragen.")
                    except Exception as e:
                        st.error(f"Termin konnte nicht im Kalender eingetragen werden: {e}")
    # Hotelsuche-Funktion (optional)
    if extracted_info.get("location") and st.button("🏨 Hotels in der Nähe suchen"):
        with st.spinner("Suche nach Hotels..."):
            try:
                hotels_result = find_hotels_near(extracted_info["location"], model=st.session_state.model_choice, language=st.session_state.language)
            except Exception as e:
                hotels_result = f"Fehler bei der Hotelsuche: {e}"
        st.subheader(f"Hotels in der Nähe von {extracted_info.get('location')}:")
        if hotels_result:
            st.markdown(hotels_result)
