from data.models import AdInfo
from datetime import datetime

def build_prompts(ad_info: AdInfo, purposes: list, tone: str, price_offer: float = None, name: str = "", free_slots: list = None):
    """Erstellt System- und User-Prompts für die OpenAI API basierend auf Anzeige und Nutzerangaben."""
    if free_slots is None:
        free_slots = []
    # Nachrichtenzwecke beschreiben
    purpose_desc = []
    if any("Interesse" in p or "Verfügbarkeit" in p for p in purposes):
        purpose_desc.append("möchte sich erkundigen, ob der Artikel noch verfügbar ist")
    if any("Preis" in p or "verhandeln" in p for p in purposes):
        if price_offer and price_offer > 0:
            purpose_desc.append(f"möchte einen Preis von {int(price_offer)} € vorschlagen")
        else:
            purpose_desc.append("möchte über den Preis verhandeln")
    if any("Termin" in p or "Abholung" in p for p in purposes):
        purpose_desc.append("möchte einen Termin zur Abholung vereinbaren")
    # Zusammenführen der Zwecke in einem Satz
    if purpose_desc:
        if len(purpose_desc) == 1:
            purpose_text = purpose_desc[0]
        elif len(purpose_desc) == 2:
            purpose_text = purpose_desc[0] + " und " + purpose_desc[1]
        else:
            purpose_text = ", ".join(purpose_desc[:-1]) + " und " + purpose_desc[-1]
    else:
        purpose_text = "hat keine speziellen Anliegen angegeben"
    # Tonalität berücksichtigen
    tone_instruction = ""
    if tone.lower().startswith("freundlich"):
        tone_instruction = "Die Nachricht soll freundlich und eher informell klingen."
    elif tone.lower().startswith("förmlich"):
        tone_instruction = "Die Nachricht soll förmlich und höflich formuliert sein (Sie-Ansprache)."
    else:
        tone_instruction = f"Die Nachricht soll in einem {tone}-Ton verfasst werden."
    # Terminvorschläge einbauen, falls vorhanden
    appointment_text = ""
    if free_slots:
        weekday_names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        month_names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        suggestions = []
        for dt in free_slots[:2]:
            day_name = weekday_names[dt.weekday()]
            day = dt.day
            month_name = month_names[dt.month - 1]
            time_str = dt.strftime("%H:%M")
            if dt.year != datetime.now().year:
                date_str = f"{day_name}, {day}. {month_name} {dt.year} um {time_str} Uhr"
            else:
                date_str = f"{day_name}, {day}. {month_name} um {time_str} Uhr"
            suggestions.append(date_str)
        if suggestions:
            if len(suggestions) == 1:
                appointment_text = f"Der Interessent ist am {suggestions[0]} verfügbar."
            else:
                appointment_text = f"Der Interessent könnte am {suggestions[0]} oder am {suggestions[1]} Zeit haben."
    # Name des Absenders einbauen, falls angegeben
    name_text = ""
    if name:
        name_text = f"Der Name des Absenders ist {name}. Bitte baue diesen am Ende der Nachricht ein."
    # System-Prompt (Rolle des Assistenten)
    system_prompt = (
        "Du bist ein Assistent, der Nutzern hilft, Nachrichten für Kleinanzeigen zu schreiben.\n"
        "Du formulierst basierend auf der gegebenen Anzeige und den Angaben des Nutzers eine passende Nachricht an den Verkäufer.\n"
        "Achte auf Höflichkeit und passe den Ton der Nachricht entsprechend den Wünschen an.\n"
    )
    # User-Prompt mit Anzeige und Nutzerwunsch
    user_prompt = (
        f"Kleinanzeige:\n"
        f"- Titel: {ad_info.title}\n"
        f"- Preis: {ad_info.price}\n"
        f"- Ort: {ad_info.location}\n"
    )
    if ad_info.description:
        desc_text = ad_info.description.strip()
        if len(desc_text) > 500:
            desc_text = desc_text[:500] + "..."
        user_prompt += f"- Beschreibung: {desc_text}\n"
    user_prompt += (
        f"Anliegen: Der Nutzer {purpose_text}.\n"
        f"{tone_instruction}\n"
    )
    if appointment_text:
        user_prompt += appointment_text + "\n"
    if name_text:
        user_prompt += name_text + "\n"
    user_prompt += "Schreibe nun eine entsprechende Nachricht in seinem Namen."
    return system_prompt, user_prompt
