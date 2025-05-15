# logic/calendar.py
# -----------------------------------------------------------
#  Kalenderfunktionen – lesen lokale ICS-Datei und freie Slots
# -----------------------------------------------------------
from datetime import datetime, timedelta, time
from icalendar import Calendar
from pathlib import Path

# Standard-Pfad:  data/Kalender.ics   (gross-/Kleinschreibung egal)
DEFAULT_ICS_PATH = Path("data/Kalender.ics")

# -----------------------------------------------------------------
def load_events_from_ics(ics_path: Path | str = DEFAULT_ICS_PATH):
    """
    Lädt alle VEVENT-Einträge aus einer lokalen ICS-Datei und gibt sie
    als Liste zurück.  Jedes Listenelement ist das VEVENT-Objekt selbst.
    """
    ics_path = Path(ics_path)
    if not ics_path.exists():
        # Keine Datei → leere Liste zurückgeben
        return []

    with ics_path.open("rb") as f:
        cal = Calendar.from_ical(f.read())

    events = [comp for comp in cal.walk() if comp.name == "VEVENT"]
    return events

# -----------------------------------------------------------------
def find_free_slots(events, max_slots: int = 2, slot_duration_minutes: int = 60):
    """
    Ermittelt bis zu `max_slots` freie Zeitfenster in den nächsten 7 Tagen,
    die mindestens `slot_duration_minutes` dauern.  Rückgabe: Liste
    von datetime-Startwerten.
    """
    free_slots = []
    if not events:
        return free_slots

    now = datetime.now()
    horizon = now + timedelta(days=7)

    # Busy-Liste aufbauen
    busy = []
    for evt in events:
        start = evt.get("dtstart").dt
        end   = evt.get("dtend").dt
        if not isinstance(start, datetime):
            start = datetime.combine(start, time.min)
        if not isinstance(end, datetime):
            end = datetime.combine(end, time.max)
        busy.append((start, end))
    busy.sort(key=lambda x: x[0])

    # Suche nach Lücken
    cursor = now
    while cursor < horizon and len(free_slots) < max_slots:
        # Kollisionsprüfung
        conflict = None
        for bstart, bend in busy:
            if bstart <= cursor < bend:
                conflict = bend
                break
        if conflict:
            cursor = conflict  # hinter das Event springen
            continue

        # Slot frei – passt er in den Arbeitstag 9-20 Uhr?
        day_end = cursor.replace(hour=20, minute=0, second=0, microsecond=0)
        if cursor.hour < 9:
            cursor = cursor.replace(hour=9, minute=0, second=0, microsecond=0)

        slot_end = cursor + timedelta(minutes=slot_duration_minutes)
        if slot_end <= day_end:
            free_slots.append(cursor)
            cursor = slot_end + timedelta(minutes=15)  # 15-min-Puffer
        else:
            # nächsten Tag 9 Uhr
            cursor = (cursor + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    return free_slots
