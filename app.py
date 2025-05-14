import streamlit as st
import openai
from negotiation_agent import NegotiationAgent
import utils
import json
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(page_title="Kleinanzeigen Chatbot", page_icon="💬", layout="wide")

# Load custom CSS for styling
try:
    with open("style.css") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Initialize OpenAI API key from Streamlit secrets
openai.api_key = st.secrets.get("openai_api_key", None)
if "openai" in st.secrets:
    # If secrets stored under [openai] section
    openai.api_key = st.secrets["openai"].get("api_key", openai.api_key)
if not openai.api_key:
    st.error("OpenAI API key is not set. Please add it to the Streamlit secrets.")
    st.stop()

# Initialize session state for agent, thread, conversation history, favorites
if "agent" not in st.session_state:
    st.session_state.agent = NegotiationAgent(model="gpt-4")
    st.session_state.thread_id = st.session_state.agent.start_new_thread()
    st.session_state.history = []   # list of assistant message strings
    st.session_state.favorites = [] # list of favorite message strings
    st.session_state.last_input = None  # store last listing input to detect changes

st.title("📧 Kleinanzeigen Negotiation Assistant")
st.write("Dieses Tool hilft dabei, höfliche Nachrichten für Kleinanzeigen zu erstellen. Geben Sie eine Anzeigen-URL oder den Anzeigentext ein und wählen Sie aus, welche Aspekte in der Nachricht enthalten sein sollen.")

# Input selection: URL or text
input_mode = st.radio("Eingabeart der Anzeige:", ["URL der Anzeige", "Anzeigentext eingeben"], index=0)
listing_text = ""
listing_input = ""
if input_mode == "URL der Anzeige":
    listing_url = st.text_input("URL der Kleinanzeige", placeholder="https://www.example.com/anzeige123")
    if listing_url:
        try:
            html = utils.fetch_listing_html(listing_url)
            data = utils.parse_listing(html)
            # Combine extracted fields into a text block for the agent
            title = data.get("title") or ""
            price = data.get("price") or ""
            location = data.get("location") or ""
            description = data.get("description") or ""
            listing_parts = []
            if title:
                listing_parts.append(f"Title: {title}")
            if price:
                listing_parts.append(f"Price: {price}")
            if location:
                listing_parts.append(f"Location: {location}")
            if description:
                listing_parts.append(f"Description: {description}")
            listing_text = "\n".join(listing_parts).strip()
            listing_input = listing_url  # for change detection
        except Exception as e:
            st.error(f"Fehler beim Laden der URL: {e}")
            listing_text = ""
elif input_mode == "Anzeigentext eingeben":
    input_area = st.text_area("Anzeigentext", placeholder="Titel, Beschreibung, Preis, Ort,...", height=200)
    if input_area:
        listing_text = input_area.strip()
        listing_input = listing_text[:100]  # use first 100 chars for change detection

# ICS calendar integration (optional)
calendar_content = None
with st.expander("📅 Google-Kalender (ICS) anzeigen/integrieren", expanded=False):
    ics_url = st.text_input("URL zum ICS-Kalender (optional)", placeholder="https://calendar.google.com/calendar/ical/...")
    if ics_url:
        try:
            res = utils.requests.get(ics_url, timeout=10)
            res.raise_for_status()
            calendar_content = res.text
        except Exception as e:
            st.error(f"Konnte Kalender nicht laden: {e}")
    ics_file = st.file_uploader("alternativ ICS-Datei hochladen", type="ics")
    if ics_file:
        try:
            content_bytes = ics_file.read()
            calendar_content = content_bytes.decode("utf-8")
        except Exception as e:
            st.error(f"Fehler beim Lesen der ICS-Datei: {e}")
    if calendar_content:
        events = utils.get_calendar_events(calendar_content, upcoming_days=14)
        if events:
            st.write("**Bevorstehende Termine:**")
            for ev_start, ev_summary in events:
                st.write(f"- {utils.format_event_time(ev_start)}: {ev_summary}")
        else:
            st.write("Keine Termine in den nächsten 14 Tagen.")

# Selection of text template aspects
st.markdown("**Wählen Sie aus, welche Inhalte die Nachricht enthalten soll:**")
template_set = {}
try:
    # Load templates from JSON files
    with open("text_templates_furniture.json", "r", encoding="utf-8") as f:
        templates_furniture = json.load(f)
    with open("text_templates.json", "r", encoding="utf-8") as f:
        templates_general = json.load(f)
    # Decide which template set to use based on listing content (simple heuristic)
    if listing_text:
        # If listing has furniture-specific keywords or dimensions, use furniture set
        if any(word in listing_text.lower() for word in ["cm", "sofa", "tisch", "schrank", "couch", "stuhl"]):
            template_set = templates_furniture
        else:
            template_set = templates_general
    else:
        # Default to general if no listing yet
        template_set = templates_general
except Exception as e:
    # Fallback: no templates loaded
    template_set = {}
    st.warning("Textbausteine konnten nicht geladen werden.")
selected_aspects = []
if template_set:
    options = list(template_set.keys())
    selected_aspects = st.multiselect("Aspekte für die Nachricht:", options)
else:
    st.text("Keine Textbausteine verfügbar.")

# Button to generate message
generate_btn = st.button("💡 Nachricht generieren", type="primary", disabled=(not listing_text))

if generate_btn and listing_text:
    # If the listing input changed from the last time, start a new thread for a new context
    if st.session_state.last_input and listing_input and listing_input != st.session_state.last_input:
        st.session_state.thread_id = st.session_state.agent.start_new_thread()
        st.session_state.history.clear()
    st.session_state.last_input = listing_input
    # Construct the user prompt content
    prompt = "Bitte formulieren Sie eine höfliche Nachricht zu folgender Anzeige.\n"
    if selected_aspects:
        # List the selected aspects in the prompt to guide the assistant
        prompt += "Die Nachricht soll folgende Punkte ansprechen: "
        prompt += ", ".join(selected_aspects) + ".\n"
    if calendar_content and any(term for term in ["Termin", "Besichtigung"] if term in " ".join(selected_aspects)):
        # If calendar is provided and appointment scheduling is selected, include availability hint
        free_slot = None
        events = utils.get_calendar_events(calendar_content, upcoming_days=7)
        # find next day at 18:00 that is free
        for i in range(1, 8):
            candidate = datetime.now() + timedelta(days=i)
            candidate = candidate.replace(hour=18, minute=0, second=0, microsecond=0)
            busy = False
            for ev_start, ev_summary in events:
                if abs((ev_start - candidate).total_seconds()) < 3600:
                    busy = True
                    break
            if not busy:
                free_slot = candidate
                break
        if free_slot:
            prompt += f"Der Nutzer könnte am {free_slot.strftime('%A, %d.%m.%Y um %H:%M Uhr')} für einen Termin zur Verfügung stehen.\n"
    prompt += "Anzeigendetails:\n" + listing_text
    # Send user message to agent and run assistant
    with st.spinner("Generiere Nachricht..."):
        try:
            st.session_state.agent.add_user_message(prompt)
            assistant_response = st.session_state.agent.run_assistant()
        except Exception as e:
            st.error(f"Fehler bei der Nachrichtenerzeugung: {e}")
            assistant_response = ""
    if assistant_response:
        # Save the new message to history (at top of list)
        st.session_state.history.insert(0, assistant_response)

# Display history of generated messages (if any)
if st.session_state.history:
    st.markdown("**Nachrichten-Historie:**")
    for idx, msg in enumerate(st.session_state.history, start=1):
        st.write(f"**Nachricht {idx}:**")
        st.code(msg, language="", line_numbers=False)
        token_count = utils.count_tokens(msg, model="gpt-4")
        st.caption(f"Tokens: {token_count}")
        # Favorite button for each message
        if msg in st.session_state.favorites:
            st.button("✔️ Favorit", key=f"fav_hist_{idx}_disabled", disabled=True)
        else:
            if st.button("⭐ Favorit speichern", key=f"fav_hist_{idx}"):
                st.session_state.favorites.append(msg)
                st.success("Zur Favoritenliste hinzugefügt.")
        st.divider()

# Display favorites section
if st.session_state.favorites:
    st.markdown("**⭐ Meine Favoriten:**")
    for fid, fav in enumerate(st.session_state.favorites, start=1):
        st.write(f"**Favorit {fid}:**")
        st.code(fav, language="", line_numbers=False)
        st.caption(f"Tokens: {utils.count_tokens(fav, model='gpt-4')}") 
        st.divider()

# Reset conversation button in sidebar
if st.sidebar.button("🔄 Neue Konversation starten"):
    # Start a fresh thread (preserve favorites and agent)
    try:
        st.session_state.agent.start_new_thread()
    except Exception:
        # In case agent was cleared, reinitialize it
        st.session_state.agent = NegotiationAgent(model="gpt-4")
        st.session_state.agent.start_new_thread()
    st.session_state.history.clear()
    st.session_state.last_input = None
    st.sidebar.info("Neue Unterhaltung gestartet.")
