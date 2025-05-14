import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_random_exponential
import re
import json
import os
import random
import time
from icalendar import Calendar
from datetime import datetime

class ExtractionError(Exception):
    pass

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0 Safari/537.36"
]

@retry(stop=stop_after_attempt(5), wait=wait_random_exponential(min=2, max=6), reraise=True)
def extract_info_from_url(url):
    """
    Extrahiert Titel, Beschreibung, Preis sowie weitere Details aus einer angegebenen Kleinanzeigen-URL.
    """
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        time.sleep(random.uniform(1, 3))  # Verzögerung, um Scraping-Schutz zu minimieren
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        # Basisinformationen
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "Nicht gefunden"
        desc_elem = soup.find('p')
        description = desc_elem.get_text(strip=True) if desc_elem else "Nicht gefunden"
        price_elem = soup.find('span', class_='price')
        price = price_elem.get_text(strip=True) if price_elem else "Nicht gefunden"
        if price:
            # 'VB' entfernen, falls vorhanden
            price = price.replace('VB', '').strip()

        # Weitere Details initialisieren
        seller_name = None
        condition = None
        location = None
        dimensions = None

        # Gesamten Text der Seite durchsuchen
        text = soup.get_text(separator="\n")
        # Ort anhand PLZ (5 Ziffern) erkennen
        loc_match = re.search(r"\d{5}\s+\w+", text)
        if loc_match:
            location = loc_match.group().strip()
        # Zustand finden (falls als Attribut angegeben oder im Text erwähnt)
        cond_dt = soup.find('dt', string=lambda s: s and 'Zustand' in s)
        if cond_dt:
            dd = cond_dt.find_next('dd')
            if dd:
                condition = dd.get_text(strip=True)
        if not condition:
            cond_match = re.search(r"Zustand:?\s*([^\n]+)", text)
            if cond_match:
                cond_val = cond_match.group(1).strip()
                condition = cond_val.split(",")[0]
        # Verkäufername finden (falls angegeben und nicht "Privater/Gewerblicher Anbieter")
        seller_match = re.search(r"Anbieter:?\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)", text)
        if seller_match:
            name = seller_match.group(1).strip()
            if not (name.lower().startswith("privat") or name.lower().startswith("gewerb")):
                seller_name = name
        # Maße (Abmessungen) finden
        dims_match = re.search(r"Maße:?\s*([^\n;]+)", text)
        if dims_match:
            dimensions = dims_match.group(1).strip()

        return {
            "seller_name": seller_name or "Unbekannter Verkäufer",
            "title": title or "Nicht verfügbar",
            "description": description or "Keine Beschreibung verfügbar",
            "price": price or "Nicht gefunden",
            "condition": condition or "Keine Angaben",
            "dimensions": dimensions or "Keine Angaben",
            "location": location or "Keine Adresse gefunden"
        }
    except requests.RequestException as e:
        raise ExtractionError(f"Fehler beim Abrufen der URL: {e}")
    except Exception as e:
        raise ExtractionError(f"Fehler beim Parsen der HTML-Daten: {e}")

def analyze_manual_text(text):
    """
    Analysiert manuell eingefügten Text und extrahiert:
    - Name des Verkäufers
    - Titel/Beschreibung des Artikels
    - Zustand des Artikels
    - PLZ und Ort
    - Maße des Artikels
    - Preis
    """
    lines = text.splitlines()
    extracted_info = {
        "seller_name": None,
        "title": None,
        "condition": None,
        "location": None,
        "description": None,
        "dimensions": None,
        "price": None
    }

    for line in lines:
        line = line.strip()
        if "verkäufer" in line.lower() and not extracted_info["seller_name"]:
            extracted_info["seller_name"] = line.split(":")[-1].strip()
        elif len(line) > 10 and not extracted_info["title"]:
            extracted_info["title"] = line
        elif "zustand" in line.lower() and not extracted_info["condition"]:
            extracted_info["condition"] = line.split(":")[-1].strip()
        elif re.match(r"\d{5}\s+\w+", line) and not extracted_info["location"]:
            extracted_info["location"] = line
        elif "maß" in line.lower() and not extracted_info["dimensions"]:
            extracted_info["dimensions"] = line.split(":")[-1].strip() if ":" in line else line
        elif ("€" in line or "EUR" in line) and not extracted_info["price"]:
            price_match = re.search(r"\d+", line.replace('.', '').replace(',', ''))
            if price_match:
                extracted_info["price"] = price_match.group(0) + " €"
        elif not extracted_info["description"]:
            extracted_info["description"] = line

    return {
        "seller_name": extracted_info["seller_name"] or "Unbekannter Verkäufer",
        "title": extracted_info["title"] or "Nicht verfügbar",
        "condition": extracted_info["condition"] or "Keine Angaben",
        "location": extracted_info["location"] or "Keine Adresse gefunden",
        "description": extracted_info["description"] or "Keine Beschreibung verfügbar",
        "dimensions": extracted_info["dimensions"] or "Keine Angaben",
        "price": extracted_info["price"] or "Nicht gefunden"
    }

CALENDAR_URL = "https://calendar.google.com/calendar/ical/28e712b12a16d77bc2a4dc69c390c04baae21f863d545039dc13f3cb749b5933%40group.calendar.google.com/private-b93473578817edcda74cd976a71090d9/basic.ics"

def fetch_calendar_events():
    """
    Ruft die ICS-Kalenderdatei ab und extrahiert die Termine.
    """
    try:
        response = requests.get(CALENDAR_URL)
        response.raise_for_status()
        calendar = Calendar.from_ical(response.text)

        events = []
        for component in calendar.walk():
            if component.name == "VEVENT":
                event_summary = component.get("summary")
                event_start = component.get("dtstart").dt
                event_end = component.get("dtend").dt
                events.append({
                    "summary": str(event_summary),
                    "start": event_start,
                    "end": event_end
                })
        return sorted(events, key=lambda x: x["start"])
    except requests.RequestException as e:
        return [{"summary": "Fehler beim Laden des Kalenders", "start": None, "end": None}]
