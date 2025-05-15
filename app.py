import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

# Eigene Module importieren
import config
from logic import calendar

# Seiteneinstellungen
st.set_page_config(page_title="Kleinanzeigen Nachrichten-Assistent", layout="centered")

st.title("📝 Kleinanzeigen Nachrichten-Assistent")
st.write("Geben Sie eine Kleinanzeigen-URL ein und erhalten Sie einen Nachrichtenvorschlag. Wählen Sie bei Bedarf Textbausteine und Terminvorschläge aus:")

# Eingabefeld für Kleinanzeigen-URL
ad_url = st.text_input("Kleinanzeigen-URL", placeholder="https://www.kleinanzeigen.de/s-anzeige/beispiel-anzeige/1234567890")

# Auswahl der Textbausteine (Mehrfachauswahl)
module_options = list(config.TEXT_MODULES.values())
selected_modules = st.multiselect("Textbausteine auswählen", module_options)

# Falls "Preisvorschlag" gewählt wurde, Eingabefeld für Preis anzeigen
proposed_price = None
if config.TEXT_MODULES.get("price") in selected_modules:
    proposed_price = st.number_input("Preisvorschlag (EUR)", min_value=1, value=1, step=1)
    # Hinweis: 0 EUR wird ausgeschlossen; min_value=1 erzwingt gültigen Betrag

# Kalendertermine laden und zur Auswahl anbieten
calendar_events = []
calendar_error = False
try:
    calendar_events = calendar.load_events(config.ICS_FILE)
except FileNotFoundError:
    st.error("Kalenderdatei wurde nicht gefunden. Termine können nicht geladen werden.")
    calendar_error = True
except Exception as e:
    st.error(f"Kalender konnte nicht geladen werden: {e}")
    calendar_error = True

selected_times = []
if calendar_events:
    selected_times = st.multiselect("Verfügbare Termine für Vorschlag (Abholung/Besichtigung)", options=calendar_events)
elif not calendar_error:
    # Kalender ist leer (keine zukünftigen Termine)
    st.info("Aktuell sind keine zukünftigen Termine im Kalender eingetragen.")

# Auswahl des KI-Modells
model_choice = st.selectbox("Modell für die Nachrichtenerstellung", ["OpenAI ChatGPT", "Lokales LLM (LLaMA/Ollama)"])

# OpenAI API-Key behandeln (wenn nötig)
openai_api_key = config.OPENAI_API_KEY or (st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else "")
if model_choice.startswith("OpenAI") and not openai_api_key:
    # Passwort-Feld zur Eingabe des API-Schlüssels
    openai_api_key = st.text_input("OpenAI API-Key eingeben", type="password")

# Session-State für generierte Nachricht initialisieren
if "generated_message" not in st.session_state:
    st.session_state["generated_message"] = ""

# Hilfsfunktion: Kleinanzeigen-Seite abrufen und Inhalte parsen
def fetch_ad_details(url: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Fehler beim Abrufen der URL: {e}")
    html = resp.text
    # Prüfen, ob die Seite evtl. JavaScript erfordert (Noscript-Hinweis)
    if "JavaScript aktivieren" in html or "Browser aktualisieren" in html:
        raise RuntimeError("Die Seite konnte nicht geladen werden (evtl. ist eine Anmeldung oder aktiviertes JavaScript erforderlich).")
    soup = BeautifulSoup(html, "html.parser")
    title = desc = price = ""

    # Titel aus Meta-Tag oder Überschrift extrahieren
    meta_title = soup.find("meta", property="og:title")
    if meta_title and meta_title.get("content"):
        title = meta_title["content"]
        # Eventuelle Zusätze (z.B. " - Kleinanzeigen") entfernen
        title = title.split("|")[0].split(" - ")[0].strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text().strip()

    # Preis aus der Anzeige extrahieren
    price_tag = soup.find(attrs={"class": re.compile(r"price|Price|preis|PREIS")})
    if price_tag:
        price = price_tag.get_text().strip()
    else:
        # Fallback: nach Euro-Zeichen im Text suchen
        price_text = soup.find(text=lambda t: t and "€" in t)
        if price_text:
            price = price_text.strip()

    # Beschreibungstext extrahieren
    desc_tag = soup.find("p", attrs={"class": re.compile(r"description|Description|beschreibung|Beschreibung")})
    if not desc_tag:
        desc_tag = soup.find(attrs={"id": re.compile(r"escription")})
    if desc_tag:
        desc = desc_tag.get_text().strip()
    else:
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            desc = meta_desc["content"].strip()

    # Wenn weder Titel noch Beschreibung gefunden wurden, Fehler werfen
    if title == "" and desc == "":
        raise RuntimeError("Angebotsdetails konnten nicht ausgelesen werden.")
    return title, desc, price

# Button zum Generieren der Nachricht
if st.button("💬 Nachricht generieren"):
    # Grundlegende Eingabevalidierungen
    if not ad_url:
        st.error("Bitte geben Sie zunächst eine Kleinanzeigen-URL ein.")
    elif model_choice.startswith("OpenAI") and not openai_api_key:
        st.error("Bitte tragen Sie Ihren OpenAI API-Key ein, um ChatGPT nutzen zu können.")
    elif config.TEXT_MODULES.get("price") in selected_modules and proposed_price is not None and proposed_price <= 0:
        st.error("Bitte geben Sie einen gültigen Preisvorschlag (> 0) ein.")
    else:
        # 1. Kleinanzeigen-Details parsen
        try:
            title, description, price_info = fetch_ad_details(ad_url)
        except Exception as e:
            st.error(f"Konnte die Angebotsdaten nicht verarbeiten: {e}")
        else:
            # 2. Prompt für LLM zusammenstellen
            system_role = ("Du bist ein hilfreicher Assistent, der dem Nutzer hilft, " 
                           "eine freundliche, höfliche Nachricht auf Deutsch zu verfassen.")
            user_content = f"**Angebotstitel:** {title}\n"
            if description:
                user_content += f"**Angebotsbeschreibung:** {description}\n"
            if price_info:
                user_content += f"**Angebotspreis:** {price_info}\n"
            user_content += "\nDer Nutzer möchte dem Verkäufer eine Nachricht schicken, die Folgendes beinhaltet:\n"
            if config.TEXT_MODULES.get("interest") in selected_modules:
                user_content += "- Interesse am Artikel bekunden.\n"
            if config.TEXT_MODULES.get("condition") in selected_modules:
                user_content += "- Eine Frage zum Zustand des Artikels stellen.\n"
            if config.TEXT_MODULES.get("price") in selected_modules and proposed_price:
                user_content += f"- Einen Preis von {int(proposed_price)}€ vorschlagen (als Gegenangebot).\n"
            if selected_times:
                times_list = "; ".join(selected_times)
                user_content += f"- Terminvorschlag für Abholung/Besichtigung: {times_list}.\n"
            user_content += "\nFormuliere daraus eine höfliche Nachricht in meinem Namen. Antworte **nur** mit dem ausformulierten Nachrichtentext (ohne zusätzliche Erklärungen)."

            # Nachrichten im Chat-Format vorbereiten
            messages = [
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content}
            ]

            result_text = None
            # 3. LLM-Modell aufrufen (OpenAI oder lokal)
            if model_choice.startswith("OpenAI"):
                try:
                    import openai
                    openai.api_key = openai_api_key
                    openai.api_base = "https://api.openai.com/v1"
                    with st.spinner("Frage ChatGPT..."):
                        response = openai.ChatCompletion.create(model=config.OPENAI_MODEL, messages=messages)
                    # Antwort extrahieren
                    result_text = response.choices[0].message.content.strip()
                except Exception as e:
                    st.error(f"Fehler bei der OpenAI-Anfrage: {e}")
            else:
                # Lokales LLM über Ollama
                try:
                    import requests
                    payload = {"model": config.LOCAL_MODEL, "messages": messages}
                    with st.spinner("Frage lokales LLM..."):
                        resp = requests.post(f"{config.OLLAMA_API_URL}/chat/completions", json=payload, timeout=60)
                    if resp.status_code != 200:
                        raise RuntimeError(f"Ollama API-Fehler (Status {resp.status_code})")
                    data = resp.json()
                    # Ergebnis-Text extrahieren
                    result_text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if result_text == "":
                        raise RuntimeError("Lokales Modell lieferte keine Antwort.")
                except Exception as e:
                    # Fallback auf OpenAI
                    st.warning(f"Lokales Modell nicht verfügbar: {e} – Wechsle zu OpenAI.")
                    if not openai_api_key:
                        st.error("OpenAI API-Key erforderlich, um stattdessen ChatGPT zu nutzen.")
                        result_text = None
                    else:
                        try:
                            import openai
                            openai.api_key = openai_api_key
                            openai.api_base = "https://api.openai.com/v1"
                            with st.spinner("Frage ChatGPT statt dessen..."):
                                response = openai.ChatCompletion.create(model=config.OPENAI_MODEL, messages=messages)
                            result_text = response.choices[0].message.content.strip()
                        except Exception as e2:
                            st.error(f"Fehler bei der OpenAI-Anfrage: {e2}")
                            result_text = None

            # 4. Ergebnis anzeigen, falls erfolgreich
            if result_text:
                st.session_state["generated_message"] = result_text

# Generierte Nachricht (falls vorhanden) anzeigen
if st.session_state.get("generated_message"):
    st.subheader("Vorgeschlagene Nachricht:")
    st.markdown(st.session_state["generated_message"])
