import re
import requests
from bs4 import BeautifulSoup
from data.models import AdInfo  # Datenklasse für Anzeigeninformationen

def extract_data_from_url(url):
    try:
        # HTTP-Anfrage an die URL senden und den HTML-Inhalt abrufen
        response = requests.get(url)
        response.raise_for_status()  # Exception bei Fehlerstatuscodes
        
        # HTML-Inhalt mit BeautifulSoup parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titel extrahieren
        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Preis extrahieren – erstes <span> mit „€” suchen
        price_tag = soup.find(lambda tag: tag.name == "span" and "€" in tag.get_text())
        price = price_tag.get_text(strip=True) if price_tag else ""

        # Beschreibung extrahieren – ab "Beschreibung"-Überschrift, alle folgenden <p>
        desc_section = soup.find(lambda tag: tag.name in ["h2", "div"] and "Beschreibung" in tag.get_text())
        description = ""
        if desc_section:
            for sib in desc_section.find_next_siblings():
                if sib.name == "p":
                    description += sib.get_text(strip=True) + "\n"
                else:
                    break
        description = description.strip()

        # Bild-URLs extrahieren (alle <img>)
        image_urls = []
        image_tags = soup.find_all('img')
        for img_tag in image_tags:
            # Oft ist das Hauptbild das erste große Bild im Listing
            src = img_tag.get('src')
            if src and "placeholder" not in src:  # Optional: Filtere Platzhalter aus
                image_urls.append(src)

        # Kontaktinformationen extrahieren
        contact_info = {}

        # Verkäufername (sofern vorhanden)
        seller_tag = soup.find(lambda tag: tag.name in ['span', 'div'] and 'verkäufer' in tag.get_text().lower())
        if seller_tag:
            name_text = seller_tag.get_text(strip=True)
            name_parts = name_text.split(" ", 1)
            contact_info['vorname'] = name_parts[0]
            if len(name_parts) > 1:
                contact_info['nachname'] = name_parts[1]

        # Telefonnummer (direkt oder versteckt im Text)
        all_text = soup.get_text(separator="\n")
        phone_regex = re.compile(r'\b(\+?\d{1,3}[-.\s]?)?(\(?\d{2,5}\)?[-.\s]?)?\d{3,}([-.\s]?\d{2,})?\b')
        phone_match = phone_regex.findall(all_text)
        # Filter nach realistischen Nummern (mind. 8 Ziffern)
        phones = ["".join(p) for p in phone_match if len("".join(p)) >= 8]
        if phones:
            contact_info['telefon'] = phones[0]

        # Adresse mit Regex (Straße, Hausnummer, PLZ, Stadt)
        address_regex = re.compile(
            r'(?P<strasse>[A-Za-zäöüÄÖÜß\s\-]+)\s+(?P<hausnummer>\d+[a-zA-Z]?)\,?\s*(?P<plz>\d{5})\s(?P<stadt>[A-Za-zäöüÄÖÜß\s\-]+)'
        )
        address_match = address_regex.search(all_text)
        if address_match:
            contact_info['straße'] = address_match.group('strasse').strip()
            contact_info['hausnummer'] = address_match.group('hausnummer').strip()
            contact_info['plz'] = address_match.group('plz').strip()
            contact_info['stadt'] = address_match.group('stadt').strip()
        else:
            # Alternative: Einzelne Felder suchen
            plz_stadt = re.search(r'(\d{5})\s([A-Za-zäöüÄÖÜß\s\-]+)', all_text)
            if plz_stadt:
                contact_info['plz'] = plz_stadt.group(1)
                contact_info['stadt'] = plz_stadt.group(2).strip()

        # Land (optional, meist "Deutschland" oder nicht vorhanden)
        if 'deutschland' in all_text.lower():
            contact_info['land'] = "Deutschland"

        # Rückgabe der extrahierten Daten als Dictionary
        data = {
            'title': title,
            'price': price,
            'description': description,
            'image_urls': image_urls,
            'contact_info': contact_info,
            'url': url  # Für Referenz
        }
        return data

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der URL: {e}")
        return None
    except Exception as e:
        print(f"Fehler bei der Datenextraktion: {e}")
        return None
        
def fetch_listing(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Fehler beim Abrufen der Seite. Statuscode: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Seite: {str(e)}")
        return None

def parse_ad(url: str) -> AdInfo:
    """
    Ruft die Kleinanzeigen-Seite unter der gegebenen URL ab und extrahiert Titel, Preis, Ort und Beschreibung.
    Gibt ein AdInfo-Objekt mit diesen Informationen zurück (oder ein leeres dict bei Fehler).
    """
    html = fetch_listing(url)
    if not html:
        return {}

    soup = BeautifulSoup(html, 'html.parser')

    # Titel extrahieren
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Preis extrahieren
    price_tag = soup.find('span', class_=re.compile(r'Price|price'))
    price = price_tag.get_text(strip=True) if price_tag else ""

    # Ort extrahieren
    location_tag = soup.find('span', class_=re.compile(r'Location|location'))
    location = location_tag.get_text(strip=True) if location_tag else ""

    # Beschreibung extrahieren
    description_tag = soup.find('div', class_=re.compile(r'Description|description'))
    description = description_tag.get_text(strip=True) if description_tag else ""

    ad_info = AdInfo(
        title=title,
        price=price,
        location=location,
        description=description,
        image_urls=image_urls,
        contact_info=contact_info,
        url=url
    )
    return ad_info
