import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from icalendar import Calendar
import re
import tiktoken

def fetch_listing_html(url: str) -> str:
    """
    Fetch the HTML content of a listing page given its URL.
    Returns the HTML text if successful, or raises an exception if failed.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text

def parse_listing(html: str) -> dict:
    """
    Parse the HTML content of a listing to extract main fields:
    title, price, description, location.
    Returns a dictionary with these fields (some may be None if not found).
    """
    soup = BeautifulSoup(html, 'html.parser')
    result = {
        "title": None,
        "price": None,
        "location": None,
        "description": None
    }
    # Attempt to find title in a header tag
    title_tag = soup.find(['h1', 'h2'])
    if title_tag:
        result["title"] = title_tag.get_text(strip=True)
    # Price might be indicated by a euro symbol or specific class
    price_text = None
    price_elem = soup.find(text=re.compile("€"))
    if price_elem:
        price_text = price_elem.strip()
    if price_text:
        # Remove common annotations like 'VB' (Verhandlungsbasis) for clarity
        price_text = price_text.replace("VB", "").strip()
        result["price"] = price_text
    # Location: try to find by known class or pattern (e.g., postal code and city)
    location_tag = soup.find(lambda tag: tag.name in ["span", "div", "p"] and "location" in (tag.get("class") or []))
    if location_tag:
        result["location"] = location_tag.get_text(strip=True)
    else:
        text = soup.get_text()
        loc_match = re.search(r'\b\d{5}\s+([A-ZÄÖÜ][\w-]+\s*[A-ZÄÖÜ]?[a-zäöüß]+)', text)
        if loc_match:
            result["location"] = loc_match.group(0).strip()
    # Description: find main descriptive text (in <article> or a specific container)
    description = ""
    desc_container = soup.find('article')
    if not desc_container:
        desc_container = soup.find('p', attrs={"class": "description"})
    if desc_container:
        description = desc_container.get_text(separator="\n", strip=True)
    else:
        # Fallback: get a chunk of body text minus title/location
        body_text = soup.get_text(separator="\n")
        if result["title"]:
            body_text = body_text.replace(result["title"], "")
        if result["location"]:
            body_text = body_text.replace(result["location"], "")
        description = "\n".join(body_text.splitlines()[:50])
    result["description"] = description.strip()
    return result

def get_calendar_events(ics_content: str, upcoming_days: int = 14) -> list[tuple[datetime, str]]:
    """
    Gibt eine Liste kommender Events (start_datetime, summary) für die nächsten `upcoming_days` Tage zurück.
    Zeigt nur Events an, die ein gültiges Start-Datum haben.
    """
    events: list[tuple[datetime, str]] = []
    try:
        cal = Calendar.from_ical(ics_content)
    except Exception:
        return events  # Parsing fehlgeschlagen → leer zurück

    now = datetime.now()
    future = now + timedelta(days=upcoming_days)

    for comp in cal.walk():
        if comp.name != "VEVENT":
            continue

        dtstart_prop = comp.get("dtstart")
        if dtstart_prop is None:        # ➜ Termin ohne Start‐Datum überspringen
            continue

        start = dtstart_prop.dt
        if not isinstance(start, datetime):
            # Bei reinen Datumseinträgen (type 'date') → Mitternacht setzen
            start = datetime.combine(start, datetime.min.time())

        # In lokale Zeit umwandeln & tz-Info entfernen
        try:
            if start.tzinfo is not None:
                start = start.astimezone(tz=None).replace(tzinfo=None)
        except Exception:
            pass

        if now <= start <= future:
            summary = str(comp.get("summary", "")).strip()
            events.append((start, summary or "(Ohne Titel)"))

    events.sort(key=lambda tup: tup[0])
    return events

def format_event_time(dt: datetime) -> str:
    """
    Format a datetime to a readable string (e.g., "Mo 15.05.2025 18:00").
    """
    weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    try:
        wday = weekdays[dt.weekday()]
    except Exception:
        wday = dt.strftime("%a")
    return f"{wday} {dt.strftime('%d.%m.%Y %H:%M')}"

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the approximate number of tokens in the given text for the specified model.
    Uses tiktoken encoding.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    return len(tokens)
