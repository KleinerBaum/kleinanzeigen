import requests
from bs4 import BeautifulSoup
import re

def parse_ad(url: str) -> dict:
    """
    Lädt die Kleinanzeigen-Seite von 'url', parst Titel, Preis, Beschreibung
    und gibt ein Dict mit {"title", "price", "description"} zurück.
    Kann Exception werfen, wenn Request fehlschlägt.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; KleinanzeigenBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()  # bei HTTP-Fehlern Exception

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Title
    title = ""
    meta_title = soup.find("meta", property="og:title")
    if meta_title and meta_title.get("content"):
        title = meta_title["content"].strip()

    # alt: h1
    if not title:
        h1_tag = soup.find("h1")
        if h1_tag:
            title = h1_tag.get_text().strip()

    # price
    price = ""
    # Versuche es mit einer class, in der "price" steht
    price_span = soup.find(attrs={"class": re.compile(r"price|Price|preis|PREIS")})
    if price_span:
        price = price_span.get_text().strip()
    else:
        # fallback: irgendeine Stelle mit '€'
        price_text = soup.find(text=lambda t: "€" in t if t else False)
        if price_text:
            price = price_text.strip()

    # description
    description = ""
    desc_par = soup.find("p", attrs={"class": re.compile(r"description|Description")})
    if desc_par:
        description = desc_par.get_text().strip()
    else:
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

    return {
        "title": title,
        "price": price,
        "description": description
    }
