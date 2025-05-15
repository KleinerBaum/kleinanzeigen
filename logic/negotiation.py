from datetime import datetime, timedelta, time
from typing import List, Dict

from data.models import AdInfo
from logic.llm_client import LLMClient
from logic.calendar import load_events_from_ics, find_free_slots

# ------------------------------------------------------------
# Kalender: nächsten freien Slot ermitteln (optional)
try:
    events = load_events_from_ics("data/calendar.ics")
    free_slots = find_free_slots(events)
    next_slot = free_slots[0] if free_slots else None
except Exception:
    next_slot = None
# ------------------------------------------------------------

# Mapping von Zweck → kurze Beschreibung im Prompt
PURPOSE_PROMPT_MAP: Dict[str, str] = {
    "Interesse bekunden (Verfügbarkeit)": "den Verkäufer fragen, ob der Artikel noch verfügbar ist",
    "Preis verhandeln": "einen niedrigeren Preis vorschlagen",
    "Zustand / Qualität erfragen": "nach dem genauen Zustand und möglichen Gebrauchsspuren fragen",
    "Abhol- oder Besichtigungstermin vorschlagen": "einen Termin zur Besichtigung bzw. Abholung vorschlagen",
    "Lieferoptionen anfragen": "nach Versand- oder Liefermöglichkeiten fragen",
    "Zusätzliche Bilder anfordern": "um zusätzliche Bilder des Artikels bitten",
    "Garantie / Rechnung erfragen": "nach Garantie oder Rechnung erkundigen",
    "Mehrere Artikel bündeln (Paketpreis)": "einen Paketpreis für mehrere Artikel anfragen",
    "Standort / Entfernung klären": "nach der genauen Adresse bzw. Entfernung fragen",
    "Zahlungsmethode anfragen": "nach bevorzugter Zahlungsmethode fragen",
}

def _tone_instructions(tone: str):
    """Gibt Begrüßung, Stilhinweis und Grußformel je nach Tonfall zurück."""
    tone_lower = tone.lower()
    if tone_lower.startswith("seriös"):
        return {
            "greeting": "Guten Tag",
            "style": (
                "Schreibe in einem förmlichen, professionellen Stil (Sie-Form). "
                "Achte auf Höflichkeit und klare Formulierungen."
            ),
            "closing": "Mit freundlichen Grüßen",
        }
    elif tone_lower.startswith("ausgewogen"):
        return {
            "greeting": "Hallo",
            "style": (
                "Schreibe in einem freundlichen, professionellen Stil (Du oder Sie je nach Kontext). "
                "Klinge zugänglich, aber nicht zu salopp."
            ),
            "closing": "Beste Grüße",
        }
    else:  # witzig
        return {
            "greeting": "Hallöchen",
            "style": (
                "Schreibe locker, humorvoll und trotzdem respektvoll. "
                "Baue gerne einen kleinen Wortwitz ein, ohne unseriös zu wirken."
            ),
            "closing": "Liebe Grüße",
        }

def generate_message(
    ad_info: AdInfo,
    purposes: List[str],
    tone: str,
    price_offer=None,
    user_name: str = None,
) -> str:
    """Erzeugt die finale Nachricht über das LLM."""
    # --------- Prompt-Bausteine ----------------------------------------------
    tone_cfg = _tone_instructions(tone)

    # Auflistung der gewünschten Punkte
    bullet_points = []
    for purpose in purposes:
        desc = PURPOSE_PROMPT_MAP.get(purpose)
        if desc:
            bullet_points.append(f"- {desc}")
    if price_offer and "Preis verhandeln" not in purposes:
        # falls kein expliziter Zweck gewählt, aber Preis angegeben
        bullet_points.append("- einen niedrigeren Preis vorschlagen")

    # Preisvorschlag formulieren
    price_line = ""
    if price_offer:
        price_line = (
            f"Der Käufer würde gerne **{price_offer} €** anbieten, "
            "falls das für den Verkäufer akzeptabel ist.\n"
        )

    # Terminvorschlag aus Kalender
    date_line = ""
    if next_slot:
        ts = next_slot["start"]
        dt_str = ts.strftime("%A, %d.%m.%Y um %H:%M Uhr")
        date_line = (
            f"Als möglichen Besichtigungs- oder Abholtermin könntest du **{dt_str}** vorschlagen.\n"
        )

    # System- und User-Prompt
    system_msg = (
        "Du bist ein Assistent, der professionelle Nachrichten für Kleinanzeigen verfasst."
    )
    user_prompt = (
        f"{tone_cfg['style']}\n\n"
        f"**Anzeigendetails**\n"
        f"- Titel: {ad_info.title}\n"
        f"- Preis: {ad_info.price}\n"
        f"- Ort: {ad_info.location}\n"
    )
    if ad_info.description:
        user_prompt += f"- Beschreibung: {ad_info.description[:400]}...\n"
    user_prompt += "\n**Anliegen des Käufers**\n"
    user_prompt += "\n".join(bullet_points) + "\n\n"
    if price_line:
        user_prompt += price_line
    if date_line:
        user_prompt += date_line
    user_prompt += (
        f"\nBeginne mit einer passenden Anrede („{tone_cfg['greeting']}“ "
        "und dem (falls bekannten) Namen des Verkäufers). "
        f"Schließe mit „{tone_cfg['closing']}“"
    )
    if user_name:
        user_prompt += f" und signiere mit dem Namen **{user_name}**."

    # --------------- LLM-Aufruf ----------------------------------------------
    llm = LLMClient()
    result = llm.generate_response(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_prompt}]
    )
    return result.strip()
