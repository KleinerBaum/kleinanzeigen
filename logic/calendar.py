import os
import logging
from datetime import datetime, date, timezone
from zoneinfo import ZoneInfo
from icalendar import Calendar

# Datenverzeichnis ermitteln (Ordner "data" neben dem Ordner "logic")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_ICS_PATH = os.path.join(DATA_DIR, "Kalender.ics")

def load_calendar_with_status(ics_path: str = None):
    """
    Lädt die ICS-Datei und gibt `(calendar_object, status)` zurück.

    Mögliche status-Werte:
    - 'ok': Kalender erfolgreich geladen 
    - 'not_found': Datei nicht gefunden 
    - 'empty_file': Datei existiert, ist aber leer 
    - 'parse_error': Fehler beim Parsen (Format ungültig)

    Bei Fehlern wird das Calendar-Objekt None, aber status ungleich 'ok' zurückgegeben.
    """
    path = ics_path or DEFAULT_ICS_PATH

    # Datei vorhanden?
    if not os.path.isfile(path):
        logging.warning(f"ICS file not found at {path}")
        return None, "not_found"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception as e:
        logging.error(f"Fehler beim Öffnen der Kalenderdatei: {e}")
        return None, "not_found"
    if not data or data.strip() == b"":
        # Datei ist leer
        return None, "empty_file"
    try:
        cal = Calendar.from_ical(data)
        return cal, "ok"
    except Exception as e:
        logging.error(f"Fehler beim Parsen des Kalenders: {e}")
        return None, "parse_error"

def get_available_appointments(cal: Calendar, timezone_str: str = "UTC"):
    """
    Extrahiert zukünftige Termine (VEVENTs) aus dem Calendar-Objekt und gibt eine
    Liste von formatierten Strings zurück (sortiert nach Startzeit).
    """
    if not cal:
        return []
    # Gewünschte Zeitzone laden (Fallback UTC)
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = timezone.utc

    slots = []
    now = datetime.now(tz)
    # Alle Events im Kalender prüfen
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart_prop = component.get('dtstart')
            if not dtstart_prop:
                continue
            # Start und Endzeit ermitteln 
            dtstart = dtstart_prop.dt
            dtend_prop = component.get('dtend')
            duration_prop = component.get('duration')

            # dtstart in datetime umwandeln (falls Datum ohne Zeit, wird das als datetime interpretiert)
            if isinstance(dtstart, datetime):
                start_dt = dtstart.astimezone(tz) if dtstart.tzinfo else dtstart.replace(tzinfo=tz)
            elif isinstance(dtstart, date):
                # Wenn dtstart ein Datum (ohne Uhrzeit) ist, Start 00:00 annehmen
                start_dt = datetime(dtstart.year, dtstart.month, dtstart.day, 0, 0, tzinfo=tz)
            else:
                # Unerwarteter Typ für dtstart – Event überspringen
                continue

            # dtend ermitteln 
            if dtend_prop:
                dtend = dtend_prop.dt
            elif duration_prop:
                # Dauer angegeben statt Endzeit
                dur = getattr(duration_prop, 'dt', duration_prop)
                dtend = start_dt + dur
            else:
                # Keine Endzeit oder Dauer – Endzeit = Startzeit
                dtend = start_dt

            # Endzeit ggf. auf Ende des Tages setzen, falls ganztaegig
            if isinstance(dtend, date) and not isinstance(dtend, datetime):
                end_date = dtend
            else:
                end_date = dtend.date() if isinstance(dtend, datetime) else dtend
            end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=tz)

            # Nur zukünftige Termine berücksichtigen 
            if end_dt < now:
                continue

            # Zeitraumformat erstellen (z.B. "15.05.2025 10:00 - 11:00")
            try:
                start_str = start_dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                start_str = str(start_dt)
            try:
                if isinstance(end_dt, datetime):
                    end_str = end_dt.strftime("%d.%m.%Y %H:%M")
                else:
                    end_str = str(end_dt)
            except Exception:
                end_str = str(end_dt)
            slot_str = f"{start_str} - {end_str}"
            slots.append(slot_str)

    # Nach Datum sortieren
    slots.sort()
    return slots
