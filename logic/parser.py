import re
import requests
from bs4 import BeautifulSoup
from data.models import AdInfo

def parse_from_url(url: str) -> AdInfo:
    """Parst eine Kleinanzeigen-Anzeige von der gegebenen URL und gibt die extrahierten Informationen zurück."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Fehler beim Laden der URL (Status {resp.status_code}).")
    soup = BeautifulSoup(resp.text, "html.parser")
    # Titel finden (meist in <h1>)
    title_tag = soup.find("h1")
    if not title_tag:
        raise Exception("Titel der Anzeige konnte nicht gefunden werden.")
    title = title_tag.get_text(strip=True)
    # Preis finden: Suche nach typischen Mustern (€, VB, Festpreis, Zu verschenken)
    price = ""
    price_tag = None
    for tag in soup.find_all(["h2", "div", "span"]):
        text = tag.get_text(strip=True)
        if text:
            if ("€" in text or "VB" in text or "Festpreis" in text or "Zu verschenken" in text):
                # Offensichtliche Überschriften überspringen
                if text.strip().startswith("Beschreibung") or text.strip().startswith("Anzeigen-ID"):
                    continue
                price_tag = tag
                price = text
                break
    if not price:
        price = "Unbekannt"
    # Ort/Standort finden (PLZ + Ortsname)
    location = ""
    full_text = soup.get_text(separator="\n")
    loc_match = re.search(r"\b\d{5}\b\s*.*", full_text)
    if loc_match:
        location = loc_match.group(0).strip()
        # Falls Datum in dieser Zeile enthalten, abtrennen (Datum i.d.R. TT.MM.JJJJ)
        date_match = re.search(r"\d{2}\.\d{2}\.\d{4}", location)
        if date_match:
            location = location[:date_match.start()].strip()
    if not location:
        location = "Unbekannt"
    # Beschreibung finden (nach "Beschreibung" Überschrift)
    description = ""
    desc_header = soup.find(lambda tag: tag.name in ["h2", "h3"] and "Beschreibung" in tag.text)
    if desc_header:
        desc_container = desc_header.find_next()  # nächstes Tag nach "Beschreibung"
        if desc_container:
            description = desc_container.get_text("\n", strip=True)
    else:
        # Heuristik: Längsten Textblock als Beschreibung annehmen
        all_text = soup.get_text("\n", strip=True)
        paragraphs = all_text.split("\n")
        longest = max(paragraphs, key=len) if paragraphs else ""
        description = longest.strip()
    return AdInfo(title=title, price=price, location=location, description=description)

def parse_from_text(text: str) -> AdInfo:
    """Extrahiert Titel, Preis, Ort und Beschreibung heuristisch aus einem freien Anzeigentext."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise Exception("Kein Text für die Analyse bereitgestellt.")
    title = lines[0]
    price = ""
    location = ""
    description = ""
    # Suche nach Abschnitt "Beschreibung"
    desc_index = None
    for i, line in enumerate(lines):
        if line.lower().startswith("beschreibung"):
            desc_index = i
            break
    # Teile den Text in Meta-Infos und Beschreibung auf
    if desc_index is not None:
        meta_lines = lines[:desc_index]
        desc_lines = lines[desc_index+1:]
    else:
        # Falls kein "Beschreibung" explizit vorhanden: ab dritter Zeile Beschreibung annehmen
        meta_lines = lines[:3]
        desc_lines = lines[3:]
    if desc_lines:
        description = "\n".join(desc_lines).strip()
    # In Meta-Infos nach Preis und Ort suchen
    for line in meta_lines:
        if not price and ("€" in line or "VB" in line or "Festpreis" in line or "Zu verschenken" in line):
            price = line.strip()
            continue
        if not location and re.match(r"\d{5}", line):
            loc_line = line
            # Datum abtrennen, falls in gleicher Zeile
            date_idx = re.search(r"\d{2}\.\d{2}\.\d{4}", loc_line)
            if date_idx:
                loc_line = loc_line[:date_idx.start()].strip()
            location = loc_line.strip()
            continue
    # Falls der Titel irrtümlich als Preis erkannt wurde (z.B. € im Titel)
    if price == title:
        price = ""
    # Falls kein Preis gefunden: evtl. zweite Zeile ist der Preis
    if not price and len(meta_lines) > 1:
        second_line = meta_lines[1]
        if "€" in second_line or "VB" in second_line or "Festpreis" in second_line or "Zu verschenken" in second_line:
            price = second_line.strip()
    # Falls Ort noch leer: letzte Meta-Zeile als Ort annehmen (sofern plausibel)
    if not location and meta_lines:
        potential_location = meta_lines[-1]
        # Prüfe auf mindestens ein Alphabet-Zeichen (zur Unterscheidung von reinem Preis)
        if re.search(r"[A-Za-z]", potential_location):
            location = potential_location.strip()
    if not price:
        price = "Unbekannt"
    if not location:
        location = "Unbekannt"
    return AdInfo(title=title, price=price, location=location, description=description)
