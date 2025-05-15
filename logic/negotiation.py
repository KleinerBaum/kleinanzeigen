# logic/negotiation.py  (Kopfbereich)

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

def generate_message(min_price: int, max_price: int) -> str:
    """
    Generate a negotiation message given a minimum and maximum price range.
    Returns a polite inquiry message in German proposing a price.
    """
    if min_price > max_price:
        raise ValueError("min_price cannot be greater than max_price")

    # Decide on an offer price (use midpoint of range as a starting offer)
    if min_price == max_price:
        offer_price = min_price
    else:
        offer_price = (min_price + max_price) // 2

    # Construct a polite negotiation message in German
    message = (
        f"Hallo, ich interessiere mich sehr für den Artikel. "
        f"Wären Sie bereit, ihn mir für etwa **{offer_price} €** zu verkaufen? "
        f"Ich könnte zwischen {min_price} € und {max_price} € bezahlen."
    )
    return message