import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from data.models import AdInfo  # Datenklasse für Anzeigeninformationen

def parse_ad(url: str):
    """
    Ruft die Kleinanzeigen-Seite unter der gegebenen URL ab und extrahiert Titel, Preis, Ort und Beschreibung.
    Gibt ein AdInfo-Objekt mit diesen Informationen zurück (oder ein leeres dict bei Fehler).
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        # Fehler beim Abruf
        return {}

    soup = BeautifulSoup(resp.content, 'html.parser')
    # Titel extrahieren
    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
    # Beschreibung extrahieren (erstes <p>-Element)
    desc_tag = soup.find('p')
    description = desc_tag.get_text(" ", strip=True) if desc_tag else ""
    # Preis extrahieren (erstes Vorkommen im Format "VB", "€", etc.)
    price = ""
    price_tag = soup.find(string=re.compile(r"€"))
    if price_tag:
        price = price_tag.strip()
    # Ort extrahieren (z.B. im Titel des Browser-Fensters oder meta-Daten)
    location = ""
    # Mögliche Stellen zur Ort-Extraktion:
    meta_loc = soup.find('span', {"data-ui-name": "breadcrumb-zip-region"})
    if meta_loc:
        location = meta_loc.get_text(strip=True)
    elif soup.title and soup.title.string:
        # Falls im Titel der Seite ein Ort enthalten ist (nach dem Bindestrich)
        title_text = soup.title.string
        if "-" in title_text:
            loc_part = title_text.split("-")[-1].strip()
            location = loc_part

    # AdInfo-Objekt zurückgeben
    return AdInfo(title=title, price=price, location=location, description=description)
