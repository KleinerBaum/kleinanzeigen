import streamlit as st
from utils import extract_info_from_url, analyze_manual_text, fetch_calendar_events, ExtractionError
from negotiation import generate_personal_message
import openai
import pyperclip

st.set_page_config(page_title="Möbelkauf-Assistent", layout="wide", page_icon="🪑")

# OpenAI API-Schlüssel aus den Streamlit Secrets laden
openai.api_key = st.secrets["openai_api_key"]

# Optional: Custom CSS laden (Design beibehalten)
try:
    with open("style.css") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Session State Initialisierung
if "selected_tone" not in st.session_state:
    st.session_state.selected_tone = "freundlich"
if "history" not in st.session_state:
    st.session_state.history = []
if "favorites" not in st.session_state:
    st.session_state.favorites = []

def main():
    st.title("🪑 Möbelkauf-Assistent")
    st.markdown("Analysieren Sie Anzeigen oder fügen Sie manuell Text ein, um eine Nachricht zu erstellen.")

    # Modellwahl: GPT-3.5 oder GPT-4
    model_choice = st.radio("KI-Modell wählen:", ["GPT-3.5-turbo", "GPT-4"], index=0)
    model_name = "gpt-3.5-turbo" if model_choice == "GPT-3.5-turbo" else "gpt-4"

    # Eingabemethode: URL oder manueller Text
    input_method = st.radio("Input-Methode wählen:", ["URL analysieren", "Text einfügen"])
    extracted_info = {}

    if input_method == "URL analysieren":
        url = st.text_input("Kleinanzeigen-URL:", placeholder="https://www.kleinanzeigen.de/...")
        if st.button("Anzeige analysieren"):
            try:
                with st.spinner("Analysiere die Anzeige..."):
                    extracted_info = extract_info_from_url(url)
                st.success("Anzeige erfolgreich analysiert!")
                st.json(extracted_info)
            except ExtractionError as e:
                st.error(f"Fehler bei der Analyse: {e}")
            except Exception as e:
                st.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
    elif input_method == "Text einfügen":
        manual_text = st.text_area("Fügen Sie den Text hier ein:")
        if manual_text:
            extracted_info = analyze_manual_text(manual_text)
            st.success("Text erfolgreich analysiert!")
            st.json(extracted_info)

    if extracted_info:
        show_text_options(extracted_info, model_name)

def show_text_options(extracted_info, model_name):
    st.subheader("Schritt 2: Wählen Sie Textbausteine aus")
    st.write("Anzeigendetails:")
    st.json(extracted_info)

    selected_options = st.multiselect(
        "Welche Textbausteine möchten Sie verwenden?",
        options=["Erstkontakt", "Preisverhandlung", "Zustandsabfrage", "Terminvereinbarung"],
        default=["Erstkontakt"]
    )

    # Kalenderanzeige, falls Terminvereinbarung gewählt
    if "Terminvereinbarung" in selected_options:
        show_calendar()

    # Nachricht generieren mit KI
    if st.button("Nachricht generieren"):
        try:
            with st.spinner("Generiere Nachricht mit KI..."):
                message, usage = generate_personal_message(extracted_info, selected_options, model_name)
            # Nachricht und Tokenverbrauch anzeigen
            st.session_state.history.append(message)
            st.text_area("Generierte Nachricht:", value=message, height=300)
            st.markdown(f"*Token-Verbrauch:* Prompt {usage.get('prompt_tokens', 0)}, Completion {usage.get('completion_tokens', 0)}, Gesamt {usage.get('total_tokens', 0)}")
            # Kopieren- und Favorisieren-Buttons
            col1, col2 = st.columns(2)
            if col1.button("📋 Kopieren"):
                try:
                    pyperclip.copy(message)
                    st.success("Nachricht in die Zwischenablage kopiert!")
                except Exception:
                    st.warning("Kopieren nicht möglich. Bitte manuell kopieren.")
            if col2.button("⭐ Favorisieren"):
                st.session_state.favorites.append(message)
                st.success("Nachricht zu Favoriten hinzugefügt!")
        except Exception as e:
            st.error(f"Fehler bei der KI-Generierung: {e}")

    # Nachrichten-Historie anzeigen
    if st.session_state.history:
        st.subheader("Nachrichten-Historie")
        for i, msg in enumerate(st.session_state.history, start=1):
            st.write(f"{i}. {msg}")
    # Favoriten anzeigen
    if st.session_state.favorites:
        st.subheader("Favoriten")
        for i, fav in enumerate(st.session_state.favorites, start=1):
            st.write(f"{i}. {fav}")

def show_calendar():
    st.subheader("📅 Verfügbare Termine im Google-Kalender")
    events = fetch_calendar_events()
    if not events or "Fehler" in events[0]["summary"]:
        st.error("Kalender konnte nicht geladen werden.")
        return
    for event in events:
        start_time = event["start"].strftime("%d.%m.%Y %H:%M") if event["start"] else "Unbekannt"
        end_time = event["end"].strftime("%d.%m.%Y %H:%M") if event["end"] else "Unbekannt"
        st.markdown(f"**{event['summary']}**\n🕑 {start_time} - {end_time}")

if __name__ == "__main__":
    main()
