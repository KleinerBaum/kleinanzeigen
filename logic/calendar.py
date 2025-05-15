from datetime import datetime, timedelta, time
from icalendar import Calendar
import streamlit as st
import requests

@st.cache_data
def load_calendar():
    """Lädt den ICS-Kalender-Feed (aus st.secrets) und gibt die Event-Komponenten zurück."""
    ics_url = st.secrets.get("calendar_ics_url")
    if not ics_url:
        return []
    try:
        response = requests.get(ics_url, timeout=5)
        if response.status_code != 200:
            st.warning(f"Konnte Kalender nicht laden (Status {response.status_code}).")
            return []
    except Exception as e:
        st.warning(f"Konnte Kalender nicht geladen werden: {e}")
        return []
    cal = Calendar.from_ical(response.content)
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    return events

def find_free_slots(max_slots=2, slot_duration_minutes=60):
    """Findet bis zu `max_slots` freie Termine (Dauer jeweils `slot_duration_minutes` Minuten) in den nächsten 7 Tagen."""
    events = load_calendar()
    free_slots = []
    if not events:
        return free_slots
    now = datetime.now()
    # Versuche Zeitzone aus dem ersten Event zu übernehmen (falls vorhanden)
    tzinfo = None
    if events:
        evt_dt = events[0].get('dtstart').dt
        if hasattr(evt_dt, 'tzinfo'):
            tzinfo = evt_dt.tzinfo
    if tzinfo:
        now = datetime.now(tzinfo)
    # Startzeit auf die nächste halbe Stunde nach der nächsten Stunde runden
    start_time = now + timedelta(hours=1)
    if start_time.minute >= 30:
        start_time = start_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        start_time = start_time.replace(minute=30, second=0, microsecond=0)
    # Arbeitszeitfenster (z.B. 9-20 Uhr) definieren
    work_start = time(9, 0)
    work_end = time(20, 0)
    end_horizon = now + timedelta(days=7)
    # Alle belegten Intervalle aus Kalender-Events sammeln
    busy_intervals = []
    for event in events:
        dt_start = event.get('dtstart').dt
        dt_end = event.get('dtend').dt if event.get('dtend') else None
        # Falls ganztägiges Event (dt_start als Datum ohne Uhrzeit)
        if not isinstance(dt_start, datetime):
            dt_start = datetime.combine(dt_start, time(0, 0))
            dt_end = datetime.combine(event.get('dtend').dt, time(23, 59)) if event.get('dtend') else dt_start
        # Zeitzone anpassen, falls nötig
        if tzinfo:
            if dt_start.tzinfo is None:
                dt_start = tzinfo.localize(dt_start)
            if dt_end and dt_end.tzinfo is None:
                dt_end = tzinfo.localize(dt_end)
        else:
            # Falls keine Zeitzone im Event, verwende naive Zeit (lokal)
            if isinstance(dt_start, datetime) and dt_start.tzinfo:
                dt_start = dt_start.replace(tzinfo=None)
            if dt_end and isinstance(dt_end, datetime) and dt_end.tzinfo:
                dt_end = dt_end.replace(tzinfo=None)
        # Nur relevante Events innerhalb des 7-Tage-Horizonts berücksichtigen
        if dt_end and dt_end < now:
            continue
        if dt_start > end_horizon:
            continue
        busy_intervals.append((dt_start, dt_end or (dt_start + timedelta(minutes=slot_duration_minutes))))
    busy_intervals.sort(key=lambda x: x[0])
    current_time = start_time
    # Suche nach freien Slots iterativ
    while current_time < end_horizon and len(free_slots) < max_slots:
        current_date = current_time.date()
        day_start = datetime.combine(current_date, work_start)
        day_end = datetime.combine(current_date, work_end)
        if tzinfo:
            day_start = tzinfo.localize(day_start)
            day_end = tzinfo.localize(day_end)
        # Falls aktueller Zeitpunkt vor Arbeitszeit beginnt, setze auf work_start
        if current_time < day_start:
            current_time = day_start
        # Wenn außerhalb der Arbeitszeit, springe auf nächsten Tag
        if current_time >= day_end:
            current_time = datetime.combine(current_date + timedelta(days=1), work_start)
            if tzinfo:
                current_time = tzinfo.localize(current_time)
            continue
        # Prüfe auf Überschneidungen mit bestehenden Terminen
        conflict_found = False
        for (evt_start, evt_end) in busy_intervals:
            if evt_end is None:
                evt_end = evt_start + timedelta(minutes=slot_duration_minutes)
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            # Konflikt: Event überschneidet sich mit vorgeschlagenem Slot
            if evt_start < slot_end and evt_end > current_time:
                conflict_found = True
                current_time = evt_end  # Springe hinter das Ende des Konflikt-Events
                break
        if conflict_found:
            continue
        # Kein Konflikt: Slot als frei betrachten, wenn innerhalb Arbeitszeit
        slot_end = current_time + timedelta(minutes=slot_duration_minutes)
        if slot_end <= day_end:
            free_slots.append(current_time)
            # Nächsten Slot-Kandidaten etwas später ansetzen (z.B. 30 Min Puffer)
            current_time = slot_end + timedelta(minutes=30)
        else:
            # Am aktuellen Tag kein Platz mehr, auf nächsten Tag gehen
            current_time = datetime.combine(current_date + timedelta(days=1), work_start)
            if tzinfo:
                current_time = tzinfo.localize(current_time)
    return free_slots
