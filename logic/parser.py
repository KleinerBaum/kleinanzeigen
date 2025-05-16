import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from data.models import AdInfo  # Datenklasse für Anzeigeninformationen


def fetch_listing(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to fetch page. Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {str(e)}")
        return None

def extract_data(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Extract title
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else None

    # Extract price
    price = None
    price_tag = soup.find(lambda tag: tag.name in ['h2', 'span'] and tag.get_text() and '€' in tag.get_text())
    if price_tag:
        price = price_tag.get_text(strip=True)

    # Extract location and date
    location = None
    date_posted = None
    date_match = soup.find(string=re.compile(r'\d{2}\.\d{2}\.\d{4}'))
    if date_match:
        date_posted = date_match.strip()
        parent = date_match.find_parent()
        if parent:
            parent_text = parent.get_text(' ', strip=True)
            if date_posted in parent_text:
                location_text = parent_text.replace(date_posted, '').strip()
                if location_text:
                    location = location_text

    # Extract attributes
    attributes = {}
    for li in soup.find_all('li'):
        text = li.get_text(' ', strip=True)
        if text.count(' ') > 0:
            label, value = text.split(' ', 1)
            attributes[label.rstrip(':')] = value

    # Extract description
    description = ''
    desc_header = soup.find(lambda tag: tag.name and 'Beschreibung' in tag.get_text())
    if desc_header:
        for elem in desc_header.find_all_next():
            if elem.name and elem.name.startswith(('h1', 'h2', 'h3')) and 'Beschreibung' not in elem.get_text():
                break
            if elem.name in ['p', 'br', 'li'] or isinstance(elem, str):
                description += elem.get_text(' ', strip=True) if hasattr(elem, 'get_text') else str(elem)
                description += '\n'
    description = description.strip()

    # Return extracted data
    return {
        'title': title,
        'price': price,
        'location': location,
        'date_posted': date_posted,
        'attributes': attributes,
        'description': description
    }

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
