import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from icalendar import Calendar
from googleapiclient.discovery import build
import openai

def extract_info_from_url(url: str) -> dict:
    """
    Ruft die Kleinanzeigen-Seite unter der gegebenen URL ab und extrahiert Titel, Beschreibung, Preis und Ort.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, 'html.parser')
    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
    desc_tag = soup.find('p')
    description = desc_tag.get_text(strip=True) if desc_tag else ""
    price_tag = soup.find('span', class_='price')
    price = price_tag.get_text(strip=True) if price_tag else ""
    location = ""
    loc_tag = soup.find(text=re.compile(r"\d{5}\s"))
    if loc_tag:
        location = loc_tag.strip()
    return {
        "title": title or "N/A",
        "description": description or "N/A",
        "price": price or "N/A",
        "location": location or ""
    }

def analyze_manual_text(text: str) -> dict:
    """
    Analysiert manuell eingegebenen Anzeigentext, um wichtige Informationen zu extrahieren.
    Erwartet werden evtl. Angaben zu Verkäufername, Titel/Artikel, Zustand, PLZ Ort und Beschreibung.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    info = {"seller_name": None, "title": None, "condition": None, "location": None, "description": None}
    for line in lines:
        low = line.lower()
        if ("verkäufer" in low or "seller" in low) and info["seller_name"] is None:
            parts = line.split(":")
            if len(parts) > 1:
                info["seller_name"] = parts[1].strip()
        elif info["title"] is None and len(line) > 20:
            info["title"] = line
        elif ("zustand" in low or "condition" in low) and info["condition"] is None:
            parts = line.split(":")
            if len(parts) > 1:
                info["condition"] = parts[1].strip()
        elif re.match(r"\d{5}\s+\w+", line) and info["location"] is None:
            info["location"] = line
        else:
            if info["description"] is None and line:
                info["description"] = line
    # Fülle Standardwerte, falls nicht gefunden
    info["seller_name"] = info["seller_name"] or "Unbekannter Verkäufer"
    info["title"] = info["title"] or "Kein Titel gefunden"
    info["condition"] = info["condition"] or "Keine Angabe"
    info["location"] = info["location"] or ""
    info["description"] = info["description"] or ""
    return info

def parse_ics_highlight(ics_content: str, ad_location: str):
    """
    Parst den Inhalt einer ICS-Kalenderdatei und findet Daten, an denen der Nutzer sich am Anzeigenort aufhält.
    Gibt eine Liste von Datumsobjekten zurück, die hervorgehoben werden sollen.
    """
    highlight_dates = []
    if not ad_location:
        return highlight_dates
    # Stadt aus dem Anzeigenort extrahieren (z.B. "12345 Berlin" -> "Berlin")
    city = ad_location
    m = re.match(r"\d{5}\s+(.*)", ad_location)
    if m:
        city = m.group(1)
    city = city.strip().lower()
    try:
        cal = Calendar.from_ical(ics_content)
    except Exception:
        return highlight_dates
    for component in cal.walk():
        if component.name == "VEVENT":
            loc = component.get('location')
            summ = component.get('summary')
            text = ""
            if loc:
                text += str(loc)
            if summ:
                text += " " + str(summ)
            text = text.lower()
            if city and city in text:
                # Event beinhaltet den Anzeigenort
                dtstart = component.decoded("dtstart")
                dtend = component.decoded("dtend") if component.get("dtend") else None
                if isinstance(dtstart, datetime):
                    start_date = dtstart.date()
                else:
                    start_date = dtstart  # falls direkt Datum
                if dtend:
                    if isinstance(dtend, datetime):
                        end_date = dtend.date()
                    else:
                        end_date = dtend
                    current = start_date
                    last_date = end_date - timedelta(days=1)  # letztes Datum (inklusive)
                    while current <= last_date:
                        highlight_dates.append(current)
                        current += timedelta(days=1)
                else:
                    highlight_dates.append(start_date)
    return sorted(set(highlight_dates))

def get_free_busy_times(credentials, highlight_dates=None):
    """
    Ermittelt freie Zeitfenster im Google-Kalender des Nutzers innerhalb der nächsten 14 Tage (ggf. erweitert bis zum nächsten Highlight-Datum).
    Gibt eine Liste von Vorschlägen zurück (Dict mit 'start', 'end', 'display').
    """
    service = build('calendar', 'v3', credentials=credentials)
    now = datetime.utcnow()
    range_days = 14
    end_range = now + timedelta(days=range_days)
    # Falls Highlight-Daten existieren, ggf. Zeitraum verlängern bis zum ersten relevanten Highlight-Tag
    if highlight_dates:
        future_highlights = [d for d in highlight_dates if datetime.combine(d, datetime.min.time()) >= now]
        if future_highlights:
            first_hl = future_highlights[0]
            if first_hl > (now.date() + timedelta(days=range_days)):
                end_range = datetime.combine(first_hl + timedelta(days=1), datetime.min.time())
    body = {
        "timeMin": now.isoformat() + "Z",
        "timeMax": end_range.isoformat() + "Z",
        "timeZone": "Europe/Berlin",
        "items": [{"id": "primary"}]
    }
    eventsResult = service.freebusy().query(body=body).execute()
    busy_periods = eventsResult.get('calendars', {}).get('primary', {}).get('busy', [])
    # Busy-Intervalle (datetime Tupel) erstellen
    busy_intervals = []
    for period in busy_periods:
        start_str = period.get('start')
        end_str = period.get('end')
        if start_str and end_str:
            try:
                start_dt = datetime.fromisoformat(start_str)
            except Exception:
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            try:
                end_dt = datetime.fromisoformat(end_str)
            except Exception:
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            busy_intervals.append((start_dt, end_dt))
    busy_intervals.sort(key=lambda x: x[0])
    suggestions = []
    current_date = now.date()
    end_date = end_range.date()
    # Für jeden Tag im Zeitraum freie Zeit suchen
    while current_date < end_date and len(suggestions) < 5:
        day_start = datetime.combine(current_date, datetime.min.time()).replace(hour=9, minute=0)
        day_end = datetime.combine(current_date, datetime.min.time()).replace(hour=18, minute=0)
        free_start = day_start.replace(hour=10, minute=0)
        if free_start < datetime.utcnow():
            # Startzeit nicht in der Vergangenheit
            free_start = datetime.utcnow().replace(second=0, microsecond=0)
            if free_start.minute != 0:
                free_start = free_start.replace(minute=0) + timedelta(hours=1)
        # Relevante Busy-Intervalle für diesen Tag sammeln
        day_busy = []
        for (b_start, b_end) in busy_intervals:
            if b_start.date() <= current_date <= b_end.date():
                start_clamped = max(b_start, day_start)
                end_clamped = min(b_end, day_end)
                if start_clamped < end_clamped:
                    day_busy.append((start_clamped, end_clamped))
        day_busy.sort(key=lambda x: x[0])
        # Überlappende Busy-Zeiten mergen
        merged_busy = []
        for interval in day_busy:
            if not merged_busy or interval[0] > merged_busy[-1][1]:
                merged_busy.append(interval)
            else:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], interval[1]))
        meet_start = None
        last_end = free_start
        for (bs, be) in merged_busy:
            if bs > last_end and (bs - last_end) >= timedelta(hours=1):
                meet_start = last_end
                break
            if be > last_end:
                last_end = be
        if meet_start is None:
            if day_end - last_end >= timedelta(hours=1):
                meet_start = last_end
        if meet_start:
            meet_start = meet_start.replace(minute=0, second=0, microsecond=0)
            meet_end = meet_start + timedelta(hours=1)
            star = "⭐" if highlight_dates and current_date in highlight_dates else ""
            if language := "de":  # (hier vereinfachend Standard Deutsch)
                date_str = meet_start.strftime("%d.%m.%Y")
                display = f"{star}{date_str} um {meet_start.strftime('%H:%M')} Uhr"
            else:
                date_str = meet_start.strftime("%b %d, %Y")
                display = f"{star}{date_str} at {meet_start.strftime('%I:%M %p')}"
            suggestions.append({"start": meet_start, "end": meet_end, "display": display})
        current_date += timedelta(days=1)
    return suggestions

def add_calendar_events(credentials, times: list, info: dict):
    """
    Erstellt Kalendereinträge (1h Dauer) im Primärkalender des Nutzers für die angegebenen Startzeiten.
    """
    service = build('calendar', 'v3', credentials=credentials)
    results = []
    title = info.get("title", "Kleinanzeige")
    seller = info.get("seller_name", "")
    loc = info.get("location", "")
    for start_time in times:
        start_dt = start_time if isinstance(start_time, datetime) else datetime.combine(start_time, datetime.min.time()).replace(hour=10)
        end_dt = start_dt + timedelta(hours=1)
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        if seller and seller != "Unbekannter Verkäufer":
            summary = f"Treffen mit {seller} zu '{title}'"
        else:
            summary = f"Treffen zu '{title}'"
        event = {
            'summary': summary,
            'location': loc,
            'start': {'dateTime': start_iso, 'timeZone': 'Europe/Berlin'},
            'end': {'dateTime': end_iso, 'timeZone': 'Europe/Berlin'}
        }
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        results.append(created_event.get('id'))
    return results

def find_hotels_near(location: str, model: str = "gpt-3.5-turbo", language: str = "Deutsch") -> str:
    """
    Verwendet die OpenAI-API, um eine Liste von Hotels in der Nähe des gegebenen Orts zu finden.
    Rückgabe als Markdown-Liste mit Hotels (Name, Telefonnummer falls verfügbar, Google-Maps-Link).
    """
    loc_query = re.sub(r"^\d{5}\s*", "", location).strip()
    if language.startswith("Deutsch"):
        user_prompt = (f"Finde 3 günstige Hotels in der Nähe von {loc_query} für eine Übernachtung. "
                       "Gib für jedes Hotel den Namen, eine Telefonnummer (falls verfügbar) und einen Google Maps Link an. "
                       "Antworte als Markdown-Liste mit Stichpunkten.")
    else:
        user_prompt = (f"Find 3 affordable hotels near {loc_query} for an overnight stay. "
                       "For each hotel, provide the name, a phone number if available, and a Google Maps link. "
                       "Respond with a bullet-point list in Markdown.")
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.7,
        max_tokens=300
    )
    hotels_text = response["choices"][0]["message"]["content"]
    return hotels_text
