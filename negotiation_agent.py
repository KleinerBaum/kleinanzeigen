import json
import openai
from datetime import datetime

def generate_message(info: dict, selected_segments: list, selected_times: list = None, language: str = "Deutsch", fun_level: int = 0, model: str = "gpt-3.5-turbo") -> str:
    """
    Generiert eine personalisierte Nachricht an den Verkäufer über die OpenAI API.
    Berücksichtigt extrahierte Infos, ausgewählte Textbausteine, optional vorgeschlagene Termine, Sprache und Humor-Stil.
    """
    # Lade Textbausteine entsprechend der Sprache
    templates_file = "text_templates.json" if language.startswith("Deutsch") else "text_templates_en.json"
    try:
        with open(templates_file, "r", encoding="utf-8") as f:
            templates = json.load(f)
    except Exception:
        templates = {}
    segment_texts = []
    for seg in selected_segments:
        if seg in templates:
            snippet = templates[seg]
            # Falls das Template als Objekt mit 'text' hinterlegt ist, extrahiere den Text
            if isinstance(snippet, dict) and "text" in snippet:
                text = snippet["text"]
            else:
                text = snippet if isinstance(snippet, str) else ""
            # Falls Terminvereinbarung und Zeiten vorhanden, füge Zeitvorschläge ein
            if seg.lower().startswith("termin") or seg.lower().startswith("appointment") or seg.lower().startswith("besichtigung"):
                if selected_times:
                    times_formatted = []
                    for t in selected_times[:3]:  # max. 3 Zeitvorschläge
                        if isinstance(t, datetime):
                            if language.startswith("Deutsch"):
                                times_formatted.append(t.strftime("%d.%m.%Y um %H:%M Uhr"))
                            else:
                                times_formatted.append(t.strftime("%B %d, %Y at %I:%M %p").lstrip("0").replace(" 0", " "))
                        else:
                            if language.startswith("Deutsch"):
                                times_formatted.append(t.strftime("%d.%m.%Y"))
                            else:
                                times_formatted.append(t.strftime("%B %d, %Y"))
                    if len(times_formatted) == 1:
                        time_sentence = times_formatted[0]
                    elif len(times_formatted) == 2:
                        time_sentence = f"{times_formatted[0]} oder {times_formatted[1]}" if language.startswith("Deutsch") else f"{times_formatted[0]} or {times_formatted[1]}"
                    else:
                        time_sentence = (f"{', '.join(times_formatted[:-1])} oder {times_formatted[-1]}" 
                                         if language.startswith("Deutsch") else 
                                         f"{', '.join(times_formatted[:-1])}, or {times_formatted[-1]}")
                    if language.startswith("Deutsch"):
                        text = f"Ich könnte am {time_sentence} vorbeikommen."
                    else:
                        text = f"I could meet on {time_sentence}."
            segment_texts.append(text.strip())
    # Begrüßung/Einleitung basierend auf extrahierten Infos
    seller = info.get("seller_name") or ""
    item = info.get("title") or ""
    if language.startswith("Deutsch"):
        greeting = f"Sehr geehrte/r {seller}," if seller and seller != "Unbekannter Verkäufer" else "Guten Tag,"
        intro = f"{greeting}\n\nich habe Ihre Anzeige zu '{item}' gesehen und bin interessiert."
    else:
        greeting = f"Dear {seller}," if seller and seller.lower() not in ["unknown seller", "unbekannter verkäufer"] else "Hello,"
        intro = f"{greeting}\n\nI saw your listing for '{item}' and I am interested."
    body = "\n".join(segment_texts)
    message_content = intro + "\n\n" + body
    # Abschließende Grußformel
    closing = "\n\nMit freundlichen Grüßen" if language.startswith("Deutsch") else "\n\nSincerely"
    message_content += closing
    # Prompt für das Sprachmodell erstellen (System- und Nutzerrolle)
    if language.startswith("Deutsch"):
        if fun_level >= 80:
            tone_instruction = " Verwende einen sehr humorvollen und lockeren Ton."
        elif fun_level <= 20:
            tone_instruction = " Schreibe die Nachricht in einem sehr höflichen und formellen Ton."
        else:
            tone_instruction = " Schreibe die Nachricht höflich und in einem freundlich-lockeren Ton."
        system_prompt = "Du bist ein Assistent, der dabei hilft, Nachrichten für Kleinanzeigen-Kontakte zu formulieren."
        user_prompt = f"Formuliere die folgende Nachricht an den Verkäufer in einen fließenden, natürlich klingenden Text um, der gut strukturiert ist.{tone_instruction}\nNachricht:\n\"\"\"\n{message_content}\n\"\"\""
    else:
        if fun_level >= 80:
            tone_instruction = " Use a very humorous and casual tone."
        elif fun_level <= 20:
            tone_instruction = " Write the message in a very polite and formal tone."
        else:
            tone_instruction = " Write the message politely with a friendly, informal tone."
        system_prompt = "You are an assistant that helps users write messages for online marketplace contacts."
        user_prompt = f"Please rewrite the following message to the seller as a coherent, natural-sounding text with proper structure.{tone_instruction}\nMessage:\n\"\"\"\n{message_content}\n\"\"\""
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        final_message = response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        # Falls die API fehlschlägt, den zusammengesetzten Text ohne Überarbeitung zurückgeben
        final_message = message_content
    return final_message
