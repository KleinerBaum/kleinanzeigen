import re
import requests
from bs4 import BeautifulSoup
from data.models import AdInfo  # Datenklasse für Anzeigeninformationen

import requests
from bs4 import BeautifulSoup

def extract_data_from_url(url):
    try:
        # HTTP-Anfrage an die URL senden und den HTML-Inhalt abrufen
        response = requests.get(url)
        response.raise_for_status()  # Wirft eine Ausnahme bei Fehlerstatuscodes (z.B. 404)
        
        # HTML-Inhalt mit BeautifulSoup parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Titel extrahieren
        title = soup.find('h1', class_='title').text.strip()
        
        # Preis extrahieren
        price = soup.find('span', class_='price').text.strip()
        
        # Beschreibung extrahieren
        description = soup.find('div', class_='description').text.strip()
        
        # Bild-URLs extrahieren (falls vorhanden)
        image_urls = []
        image_tags = soup.find_all('img', class_='gallery-image')
        for img_tag in image_tags:
            image_urls.append(img_tag['src'])
        
        # Kontaktinformationen extrahieren (Beispiel: Verkäufername und Telefonnummer)
        contact_info = {}
        seller_name = soup.find('span', class_='seller-name')
        if seller_name:
            contact_info['seller_name'] = seller_name.text.strip()
        
        phone_number = soup.find('span', class_='phone-number')
        if phone_number:
            contact_info['phone_number'] = phone_number.text.strip()
        
        # Weitere Extraktionen je nach Bedarf hinzufügen
        
        # Rückgabe der extrahierten Daten als Dictionary oder JSON-Objekt
        data = {
            'title': title,
            'price': price,
            'description': description,
            'image_urls': image_urls,
            'contact_info': contact_info,
            'url': url  # Hinzufügen der URL für Referenzzwecke
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

def parse_ad(url: str):
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

    return AdInfo(title=title, price=price, location=location, description=description)
