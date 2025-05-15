import os
from datetime import datetime
from icalendar import Calendar

ics_path = 
def load_events(ics_path: str):
    """
    Lädt eine ICS-Datei und gibt eine Liste formatierter Zeitfenster (Strings) zurück.
    Nur zukünftige Termine werden berücksichtigt. Wirft eine Exception bei Fehlern.
    """
    # Existenz der Datei prüfen
    if not os.path.exists(ics_path):
        raise FileNotFoundError(f"ICS file not found at {ics_path}")
    # Datei einlesen
    with open(ics_path, "rb") as f:
        ics_data = f.read()
    try:
        cal = Calendar.from_ical(ics_data)
    except Exception as e:
        # Fehler beim Parsen der ICS-Datei
        raise RuntimeError(f"Konnte Kalender nicht einlesen: {e}")
    events = []
    now = datetime.now()
    # Alle Events durchlaufen
    for component in cal.walk("VEVENT"):
        # Startzeitpunkt des Termins auslesen
        start = component.get('dtstart').dt
        # Falls Start ein Datum ohne Zeit ist, überspringen (keine genaue Zeitangabe)
        if not isinstance(start, datetime):
            continue
        # Zeitzone entfernen für Vergleich/Anzeige (Annahme: lokale Zeiten)
        if getattr(start, "tzinfo", None):
            try:
                # In lokale Zeitzone umwandeln und TZ-Info entfernen
                local_dt = start.astimezone(None)  # None = lokale Zeitzone
                start_naive = local_dt.replace(tzinfo=None)
            except Exception:
                start_naive = start.replace(tzinfo=None)
        else:
            start_naive = start
        # Nur zukünftige Termine behalten
        if start_naive < now:
            continue
        # Formatierung des Datums/Zeit (TT.MM.JJJJ HH:MM)
        time_str = start_naive.strftime("%d.%m.%Y %H:%M")
        # Optional den Termin-Titel (Summary) anhängen, falls vorhanden
        summary = component.get('summary')
        if summary:
            summary_text = str(summary).strip()
            if summary_text:
                event_str = f"{time_str} - {summary_text}"
            else:
                event_str = time_str
        else:
            event_str = time_str
        events.append(event_str)
    # Chronologisch sortieren
    events.sort()
    return events
