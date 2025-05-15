import streamlit as st
from logic import parser, negotiation
from data.models import AdInfo

st.set_page_config(page_title="Gabis Kleinanzeigen Assistent", page_icon="🤖", layout="centered")
st.title("Gabis Kleinanzeigen Assistent")

st.write(
    "Analysiere eine Kleinanzeige und erstelle automatisch eine passende Nachricht "
    "– mit dem gewünschten Tonfall, Preisvorschlag und weiteren Optionen."
)

# -------- Eingabe  -----------------------------------------------------------
ad_url = st.text_input("Anzeige-URL", placeholder="https://www.kleinanzeigen.de/s-anzeige/…")
ad_text = st.text_area(
    "Anzeige-Text (Alternative zur URL)",
    placeholder="Anzeigentitel, Preis, Ort und Beschreibung hier einfügen …",
    height=150,
)

# --- 10 Nachrichtenzwecke -----------------------------------------------------
purpose_options = [
    "Interesse bekunden (Verfügbarkeit)",
    "Preis verhandeln",
    "Zustand / Qualität erfragen",
    "Abhol- oder Besichtigungstermin vorschlagen",
    "Lieferoptionen anfragen",
    "Zusätzliche Bilder anfordern",
    "Garantie / Rechnung erfragen",
    "Mehrere Artikel bündeln (Paketpreis)",
    "Standort / Entfernung klären",
    "Zahlungsmethode anfragen",
]
purposes = st.multiselect(
    "Was soll die Nachricht beinhalten?  (Mehrfachauswahl möglich)",
    purpose_options,
    default=[purpose_options[0]],
)

# ------------ Tonfall-Auswahl -------------------------------------------------
tone_selection = st.selectbox(
    "Tonfall der Nachricht",
    [
        "Seriös – förmlich (Sie-Form, „Guten Tag Herr/Frau …“)",
        "Ausgewogen – freundlich („Hallo …“, professionell)",
        "Witzig – locker + humorvoll",
    ],
)

# ---------------- Zusatzfelder ------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    price_input = st.text_input("Preisvorschlag (optional, €)", placeholder="z. B. 30")
with col2:
    user_name = st.text_input("Ihr Name (optional)", placeholder="Vor- oder Nachname")

# ----------------- Button -----------------------------------------------------
if st.button("Nachricht generieren"):
    if not ad_url and not ad_text:
        st.error("Bitte gib entweder eine Anzeige-URL **oder** einen Anzeige-Text ein.")
        st.stop()

    # --- Anzeige analysieren --------------------------------------------------
    try:
        ad_info: AdInfo
        if ad_url:
            ad_info = parser.parse_ad(url=ad_url.strip())
        else:
            ad_info = parser.parse_ad(text=ad_text.strip())
    except Exception as e:
        st.error(f"Fehler bei der Analyse der Anzeige: {e}")
        st.stop()

    # --- Anzeigeinformationen anzeigen ---------------------------------------
    st.subheader("Analysierte Anzeige")
    if ad_info.title:
        st.markdown(f"**Titel:** {ad_info.title}")
    if ad_info.price:
        st.markdown(f"**Preis:** {ad_info.price}")
    if ad_info.location:
        st.markdown(f"**Ort:** {ad_info.location}")
    if ad_info.description:
        if len(ad_info.description) > 400:
            with st.expander("Beschreibung anzeigen"):
                st.write(ad_info.description)
        else:
            st.markdown("**Beschreibung:**")
            st.write(ad_info.description)

    # --- Preisvorschlag aufbereiten ------------------------------------------
    price_offer = None
    if price_input:
        cleaned = price_input.replace("€", "").strip()
        try:
            price_offer = float(cleaned)
            if price_offer.is_integer():
                price_offer = int(price_offer)
        except ValueError:
            price_offer = cleaned  # Freitext (z. B. „VB 25“)

    # --- Nachricht generieren -------------------------------------------------
    with st.spinner("Generiere Nachricht …"):
        message = negotiation.generate_message(
            ad_info=ad_info,
            purposes=purposes,
            tone=tone_selection,
            price_offer=price_offer,
            user_name=user_name.strip() or None,
        )

    st.subheader("Generierte Nachricht")
    st.code(message, language="")
    st.info("Tipp: Markiere den Text und kopiere ihn mit Strg+C / ⌘+C.")
