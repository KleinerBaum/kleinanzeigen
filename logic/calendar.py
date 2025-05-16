import os
import logging
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo

try:
    from icalendar import Calendar
except ImportError as e:
    raise ImportError("icalendar library is required for calendar parsing. Please install it.") from e

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_ICS_PATH = os.path.join(DATA_DIR, "Kalender.ics")

def load_calendar_with_status(ics_path: str = None):
    """
    Lädt die ICS-Datei und gibt (calendar_object, status) zurück.
    Mögliche status-Werte:
      - 'ok'           : Kalender erfolgreich geladen
      - 'not_found'    : Datei nicht gefunden
      - 'empty_file'   : Datei existiert, ist aber leer
      - 'parse_error'  : Fehler beim Parsen (Format ungültig)
    Bei Fehlern wird der Kalender None, aber status ungleich 'ok' zurückgegeben.
    """
    path = ics_path or DEFAULT_ICS_PATH
    if not os.path.isfile(path):
        return None, "not_found"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception as e:
        logging.error(f"Fehler beim Öffnen der Kalenderdatei: {e}")
        return None, "not_found"

    if not data or data.strip() == b"":
        return None, "empty_file"

    try:
        cal = Calendar.from_ical(data)
        return cal, "ok"
    except Exception as e:
        logging.error(f"Fehler beim Parsen des Kalenders: {e}")
        return None, "parse_error"

def get_available_appointments(cal: "Calendar", timezone_str: str = "UTC"):
    """
    Extrahiert zukünftige Termine (VEVENTs) aus dem Calendar-Objekt und gibt eine
    Liste von formatierten Strings zurück. Sortiert nach Startzeit.
    """
    if not cal:
        return []
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = timezone.utc

    slots = []
    now = datetime.now(tz)
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart_prop = component.get('dtstart')
            if not dtstart_prop:
                continue
            dtend_prop = component.get('dtend')
            duration_prop = component.get('duration')

            # Konvertiere dtstart, dtend zu datetime
            dtstart = dtstart_prop.dt
            if dtend_prop:
                dtend = dtend_prop.dt
            elif duration_prop:
                # dtend aus dtstart + duration ableiten
                dur = getattr(duration_prop, 'dt', duration_prop)
                dtend = dtstart + dur
            else:
                dtend = dtstart

            # Falls dtstart nur ein Datum ohne Uhrzeit ist, Ganz-Tages-Event
            if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                # Ganztägiges Event: 00:00 bis 23:59
                start_dt = datetime(dtstart.year, dtstart.month, dtstart.day, 0, 0, tzinfo=tz)
                # dtend analog
                if isinstance(dtend, date) and not isinstance(dtend, datetime):
                    end_date = dtend
                else:
                    end_date = dtend.date() if isinstance(dtend, datetime) else dtend
                end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=tz)
            else:
                if isinstance(dtstart, datetime):
                    start_dt = dtstart.astimezone(tz) if dtstart.tzinfo else dtstart.replace(tzinfo=tz)
                else:
                    continue

                if isinstance(dtend, datetime):
                    end_dt = dtend.astimezone(tz) if dtend.tzinfo else dtend.replace(tzinfo=tz)
                elif isinstance(dtend, date):
                    end_dt = datetime(dtend.year, dtend.month, dtend.day, 23, 59, tzinfo=tz)
                else:
                    end_dt = start_dt

            # Vergangene Termine filtern
            if end_dt < now:
                continue
            # Falls bereits begonnen, aber noch nicht zu Ende, start_dt an 'now' anpassen
            if start_dt < now < end_dt:
                start_dt = now

            # Formatierter String
            slot_str = format_timeslot(start_dt, end_dt)
            slots.append(slot_str)

    # Sortierung nach Startzeit ist in der Formatierung nicht trivial,
    # da wir nur Strings zurückgeben. Evtl. Hilfsstruktur nötig.
    # Hier vereinfachter Ansatz: wir hängen (start_dt, slot_str) in eine Liste
    # und sortieren nach start_dt, dann extrahieren slot_str:
    sorted_slots = []
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart_prop = component.get('dtstart')
            if dtstart_prop:
                dtstart_val = dtstart_prop.dt
                if isinstance(dtstart_val, datetime):
                    dtstart_val = dtstart_val.astimezone(tz)
                elif isinstance(dtstart_val, date):
                    dtstart_val = datetime(dtstart_val.year, dtstart_val.month, dtstart_val.day, 0, 0, tzinfo=tz)
                # Gleiche Formatierung wie oben
                dtend_val = component.get('dtend').dt if component.get('dtend') else dtstart_val
                slot_str = format_timeslot(dtstart_val, dtend_val if dtend_val else dtstart_val)
                # Check if end is in the future
                if dtend_val and isinstance(dtend_val, datetime):
                    if dtend_val.astimezone(tz) >= now:
                        sorted_slots.append((dtstart_val, slot_str))
                else:
                    # Wenn dtend z.B. nur ein Datum
                    if datetime(dtend_val.year, dtend_val.month, dtend_val.day, 23, 59, tzinfo=tz) >= now:
                        sorted_slots.append((dtstart_val, slot_str))

    sorted_slots = sorted(sorted_slots, key=lambda x: x[0])
    # extrahieren nur die Strings, die in der Zukunft liegen
    final_list = [s[1] for s in sorted_slots if s[0] >= now]
    return final_list

def format_timeslot(start_dt: datetime, end_dt: datetime) -> str:
    """
    Erstellt einen ansprechenden Text wie:
    "Montag, 21.11.2025, 10:00 - 11:00"
    oder "(ganztägig)" wenn 0-23:59
    """
    # Deutsche Wochentags- & Monatsnamen
    german_days = {
        "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
        "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"
    }
    german_months = {
        "January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai",
        "June": "Juni", "July": "Juli", "August": "August", "September": "September",
        "October": "Oktober", "November": "November", "December": "Dezember"
    }

    day_str = start_dt.strftime("%A")
    day_name = german_days.get(day_str, day_str)
    month_str = start_dt.strftime("%B")
    month_name = german_months.get(month_str, month_str)

    # Ganztägiges Event (00:00 - 23:59)
    if (start_dt.hour == 0 and start_dt.minute == 0) and (end_dt.hour == 23 and end_dt.minute == 59):
        return f"{day_name}, {start_dt.day}. {month_name} {start_dt.year} (ganztägig)"
    # Gleicher Tag
    if start_dt.date() == end_dt.date():
        return (
            f"{day_name}, {start_dt.day}. {month_name} {start_dt.year}, "
            f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
        )
    else:
        # Mehrtägig oder über Mitternacht
        end_day_str = end_dt.strftime("%A")
        end_day_name = german_days.get(end_day_str, end_day_str)
        end_month_str = end_dt.strftime("%B")
        end_month_name = german_months.get(end_month_str, end_month_str)
        return (
            f"{day_name}, {start_dt.day}. {month_name} {start_dt.year}, {start_dt.strftime('%H:%M')} - "
            f"{end_day_name}, {end_dt.day}. {end_month_name} {end_dt.year}, {end_dt.strftime('%H:%M')}"
        )
