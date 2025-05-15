import os
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo

try:
    from icalendar import Calendar
except ImportError as e:
    # If icalendar library is not installed, raise an error with guidance
    raise ImportError("icalendar library is required for calendar parsing. Please install it.") from e

# Determine base path for the data directory (assuming this file is in a package)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DEFAULT_ICS_PATH = os.path.join(DATA_DIR, "Kalender.ics")

def load_calendar(ics_path: str = None):
    """
    Load and parse an ICS calendar file. Returns an icalendar Calendar object.
    """
    path = ics_path or DEFAULT_ICS_PATH
    if not os.path.isfile(path):
        # Return None if file not found
        print(f"ICS file not found at {path}")
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
        cal = Calendar.from_ical(data)
        return cal
    except Exception as e:
        # If parsing fails, log the error and return None
        print(f"Failed to parse ICS file: {e}")
        return None

def get_available_appointments(cal: "Calendar" = None, timezone_str: str = "UTC"):
    """
    Extract upcoming available appointment slots from a Calendar object.
    Returns a list of formatted time slot strings for display.
    If no Calendar is provided or no slots available, returns an empty list.
    """
    if cal is None:
        # Load default calendar if none provided
        cal = load_calendar()
        if cal is None:
            return []
    # Use given timezone for output formatting
    try:
        tz = ZoneInfo(timezone_str)
    except Exception:
        tz = timezone.utc
    slots = []
    now = datetime.now(tz)
    # Iterate over all events in the calendar
    for component in cal.walk():
        if component.name == "VEVENT":
            dtstart_prop = component.get('dtstart')
            if not dtstart_prop:
                continue
            dtstart = dtstart_prop.dt
            # Get end or derive from duration
            dtend_prop = component.get('dtend')
            duration_prop = component.get('duration')
            if dtend_prop:
                dtend = dtend_prop.dt
            elif duration_prop:
                # If duration is provided instead of dtend
                try:
                    dur = duration_prop.dt  # this is a datetime.timedelta
                except:
                    dur = duration_prop
                if isinstance(dtstart, datetime):
                    dtend = dtstart + dur
                elif isinstance(dtstart, date):
                    # Add days for date (timedelta in days likely)
                    dtend = dtstart + dur
                else:
                    dtend = dtstart
            else:
                # No dtend or duration given, assume zero-length event
                dtend = dtstart
            # Ensure dtstart and dtend are datetime for uniform handling
            if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                # Treat all-day event: from start date at 00:00 to end date at 23:59 of the same day (if end is same date)
                # We'll interpret availability as the whole day
                start_dt = datetime(dtstart.year, dtstart.month, dtstart.day, 0, 0, tzinfo=tz)
                # If dtend is date, assume inclusive end of that day
                if isinstance(dtend, date) and not isinstance(dtend, datetime):
                    end_date = dtend
                else:
                    # if dtend is datetime or date combined, get date part
                    end_date = dtend.date() if isinstance(dtend, datetime) else dtend
                end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, tzinfo=tz)
            else:
                # If dtstart has no tz, assume it is in given timezone
                if isinstance(dtstart, datetime):
                    if dtstart.tzinfo is None:
                        start_dt = dtstart.replace(tzinfo=tz)
                    else:
                        start_dt = dtstart.astimezone(tz)
                else:
                    # dtstart might be something unusual, skip if not datetime or date
                    continue
                # do similar for dtend
                if isinstance(dtend, datetime):
                    if dtend.tzinfo is None:
                        end_dt = dtend.replace(tzinfo=tz)
                    else:
                        end_dt = dtend.astimezone(tz)
                elif isinstance(dtend, date):
                    # if dtend is date but dtstart had time, just assign end at end of that day
                    end_dt = datetime(dtend.year, dtend.month, dtend.day, 23, 59, tzinfo=tz)
                else:
                    end_dt = start_dt
            # Filter out past events (end time before now or start time before now)
            if end_dt < now:
                continue
            if start_dt < now:
                # If start is in the past but end is future (ongoing event), adjust start to now for availability
                start_dt = now
            # Format the slot for display
            # We'll display as "Weekday, dd. Month yyyy, HH:MM - HH:MM" or "(ganztägig)" if all-day
            if start_dt.date() == end_dt.date():
                # same day
                day_str = start_dt.strftime("%A")
                # Try to get locale in German if timezone_str is a locale, but probably not. Use manual mapping for German days/months if needed.
                # We will manually map to German names if the output is in English, for user-friendliness.
                german_days = {
                    "Monday": "Montag", "Tuesday": "Dienstag", "Wednesday": "Mittwoch",
                    "Thursday": "Donnerstag", "Friday": "Freitag", "Saturday": "Samstag", "Sunday": "Sonntag"
                }
                german_months = {
                    "January": "Januar", "February": "Februar", "March": "März", "April": "April", "May": "Mai",
                    "June": "Juni", "July": "Juli", "August": "August", "September": "September", "October": "Oktober",
                    "November": "November", "December": "Dezember"
                }
                day_name = german_days.get(day_str, day_str)
                month_str = start_dt.strftime("%B")
                month_name = german_months.get(month_str, month_str)
                if start_dt.time() == time(0,0) and end_dt.hour == 23 and end_dt.minute == 59:
                    # All-day event
                    slot_str = f"{day_name}, {start_dt.day}. {month_name} {start_dt.year} (ganzt\u00e4gig)"
                else:
                    slot_str = (f"{day_name}, {start_dt.day}. {month_name} {start_dt.year}, "
                                f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}")
            else:
                # Multi-day event or spans midnight
                start_day_str = start_dt.strftime("%A")
                end_day_str = end_dt.strftime("%A")
                start_day_name = german_days.get(start_day_str, start_day_str)
                end_day_name = german_days.get(end_day_str, end_day_str)
                start_month_str = start_dt.strftime("%B")
                end_month_str = end_dt.strftime("%B")
                start_month_name = german_months.get(start_month_str, start_month_str)
                end_month_name = german_months.get(end_month_str, end_month_str)
                slot_str = (f"{start_day_name}, {start_dt.day}. {start_month_name} {start_dt.year}, {start_dt.strftime('%H:%M')} - "
                            f"{end_day_name}, {end_dt.day}. {end_month_name} {end_dt.year}, {end_dt.strftime('%H:%M')}")
            slots.append(slot_str)
    # Sort slots by starting time for display
    slots.sort()
    return slots
